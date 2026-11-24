-- More Pawns V4 for Dragon's Dogma 2 (TDB 83).
-- Supports the Arisen, main pawn, and up to four hired pawns.
-- Requires REFramework. Back up saves before installing any party-size mod.

local suspended = false
local suspension_mode, try_resume, schedule_resume = nil, nil, nil
local resume_state = {attempts = 0, last_reason = nil, last_refusal = nil}
-- A reload can assign ManualPlayer before PawnManager and its controllers have
-- finished rebuilding. Keep compatibility hooks suspended until later frames.
local resume_pending, resume_reason, resume_frame = false, nil, 0
local lifecycle_frame = 0
local quit_bridge = nil
local player_address, cached_quit_bridge
local auto_rental, replacing_at_cap = nil, false
local automatic_hooks = {hiring = false, lifecycle = false, suspensions = 0, resumes = 0}
local xp_copies_in_flight = 0
local VERSION = "4.0.4-test1"
-- Production release: diagnostics, telemetry, trace files, and probes are disabled.
local PRODUCTION_TELEMETRY = false
local checkout_repair = {ready = false, entries = 0, returns = 0, rows_expanded = 0,
    failures = 0, discovery = {}, candidate = true}
local inventory_exit_guard = {ready = false, prevented = 0, observed_normal = 0,
    candidate = true, field = "CompMockup", request_field = "RequestModel"}
local equipment_exit_guard = {ready = false, prevented = 0, observed_normal = 0,
    candidate = true, field = "CompMockup", request_field = "RequestModel"}
local MAX_PAWNS = 5 -- main pawn + four hires; Arisen is not in these lists
-- DD2's stock movement formation has only three PositioningData entries. With
-- five pawns, the two hires past the native cap otherwise resolve to fallback
-- targets and repeatedly collide while trying to catch the Arisen.
local formation_fix = {ready = false, applied = 0, failures = 0, last_error = nil,
    last_category = nil, next_check_frame = 0, retained = {}}
local menu_mockup_fix = {ready = false, repairs = 0, last_error = nil, next_check_frame = 0}
local party_talk_guard = {ready = false, skipped = 0, suspended_skips = 0,
    method = "app.PLPartyTalkController.update()", diagnostic = true}
local chatter_result_array_fix = {ready = false, applied = 0, failures = 0, candidate = true,
    field = "SpeakerResultListForEvaluateRequest", expected_slots = 4, required_slots = 5,
    static_max_party_num = 4, writer = "REFramework managed-array field assignment"}
local corrections_by_slot = {}
local MAX_EVENTS = 180
local status = "More Pawns active. Confirm the normal hire/replacement dialogue."
local events, installed, warnings = {}, {}, {}
local active, blocked, skip_count, hire_seen = false, false, 0, false
local armed, arm_deadline = false, 0
local finish_deadline, frame, pending_export = 0, 0, false
local SUB = "<SubPawnNum>k__BackingField"
local target_manager, baseline, scope, temporary, bridge_id
local bridge_enabled, corrections = false, 0
local bridge_source, auto_restores = "none", 0
local rental_calls, extended_hires, cap_blocks = {}, 0, 0
local xp_metadata, xp_snapshots = nil, {}
local xp_trace = {events = {}, hooks = {}, warnings = {}, dropped = 0}
local xp_tracing, xp_trace_installed, xp_trace_deadline = false, false, 0
local xp_fix = {ready = false, substitutions = 0, failures = 0, last_error = nil}
local last_live_party
local discarded_events, rental_scope = 0, nil
local rental_last_state, rent_types = {}, {}

local function safe(fn)
    local ok, result = pcall(fn)
    if ok then return result end
end

local function now()
    return safe(function() return os.time() end)
end

local function field(obj, name)
    return obj and safe(function()
        local f = obj:get_type_definition():get_field(name)
        if f and not f:is_static() then return f:get_data(obj) end
    end)
end

local function int(value)
    if type(value) == "number" then return value end
    local raw = value and safe(function() return value:get_field("value__") end)
    if type(raw) == "number" then return raw end
end

local function count(list)
    if not list then return nil end
    return int(field(list, "_size")) or safe(function() return list:get_size() end)
end

local function same(a, b)
    return a and b and safe(function() return a:get_address() == b:get_address() end)
end

local function receiver(args)
    return safe(function() return sdk.to_managed_object(args[2]) end)
end

local function u32(value)
    local n = int(value)
    if n then return n & 0xffffffff end
end

local function pawn_character_id(pawn)
    local character = field(pawn, "<CachedCharacter>k__BackingField")
    if not character then return nil end
    for _, name in ipairs({"CharaID", "CharacterID"}) do
        local value = u32(field(character, name)) or u32(field(character, "<" .. name .. ">k__BackingField"))
        if value then return value end
        value = u32(safe(function()
            local m = character:get_type_definition():get_method("get_" .. name)
            if m and m:get_num_params() == 0 then return m:call(character) end
        end))
        if value then return value end
    end
end

local function saved_ids(manager)
    local list = field(manager, "_SavedPartyPawnList")
    local n, items = count(list), field(list, "_items")
    if not n or n < 0 or n > MAX_PAWNS or not items then return nil end
    local ids = {}
    for i = 0, n - 1 do
        local id = u32(safe(function() return items:get_element(i) end))
        if id == nil then return nil end
        ids[#ids + 1] = id
    end
    return ids
end

local function party()
    local manager = safe(function() return sdk.get_managed_singleton("app.PawnManager") end)
    if not manager then return { available = false } end
    local list = field(manager, "_PartyPawnList")
    local n = count(list)
    local roster = {}
    local array = list and field(list, "_items")
    if type(n) == "number" and array then
        for i = 0, math.min(n, 8) - 1 do
            local pawn = safe(function() return array:get_element(i) end)
            roster[#roster + 1] = { index = i, pawn_id = int(field(pawn, "_PawnID")),
                character_id = pawn_character_id(pawn) }
        end
    end
    return {
        available = true,
        party_count = n,
        saved_count = count(field(manager, "_SavedPartyPawnList")),
        sub_count = int(field(manager, "<SubPawnNum>k__BackingField")),
        roster = roster,
        saved_character_ids = saved_ids(manager),
    }
end

local record

local function full_party()
    local p = party()
    local sub = p.sub_count
    if temporary and sub == 1 then sub = temporary.original end
    local n = p.party_count
    if n == 4 and not party_talk_guard.ready then return false end
    if not n or n < 3 or n >= MAX_PAWNS or p.saved_count ~= n or sub ~= n - 1
        or #p.roster ~= n or not p.saved_character_ids then return false end
    local seen, chars = {}, {}
    for _, pawn in ipairs(p.roster) do
        if pawn.pawn_id == nil or pawn.pawn_id < 0 or pawn.pawn_id >= n
            or seen[pawn.pawn_id] then return false end
        if pawn.character_id and p.saved_character_ids[pawn.pawn_id + 1] ~= pawn.character_id then
            return false
        end
        seen[pawn.pawn_id] = true
    end
    for _, id in ipairs(p.saved_character_ids) do
        if chars[id] then return false end
        chars[id] = true
    end
    return seen[0] and seen[1] and seen[2]
end

-- Give the two extra hires their own formation entries. Existing game-owned
-- entries are never modified: V4 creates a five-slot array, retains the three
-- original entries by identity, then appends two independent copies of the
-- native free-follow template with wider radii. Re-run only when the game
-- replaces its active formation category, never every frame.
local function ensure_extended_formation()
    if lifecycle_frame < formation_fix.next_check_frame then return end
    formation_fix.next_check_frame = lifecycle_frame + 120
    local p = party()
    if p.party_count ~= MAX_PAWNS or p.saved_count ~= MAX_PAWNS or p.sub_count ~= MAX_PAWNS - 1 then return end
    local ok, err = pcall(function()
        local manager = assert(sdk.get_managed_singleton("app.PawnManager"), "PawnManager unavailable")
        local controller = assert(field(manager, "<FormationController>k__BackingField"), "formation controller unavailable")
        local evaluation = assert(field(controller, "_CurrentFormationData"), "active formation data unavailable")
        local formation = assert(field(evaluation, "<FormationData>k__BackingField"), "formation data unavailable")
        local category = assert(field(formation, "_FormationCategory"), "formation category unavailable")
        local original = assert(field(category, "_PositionData"), "formation position array unavailable")
        local slots = count(original)
        local category_address = safe(function() return sdk.to_int64(sdk.to_ptr(category)) end)
        local key = category_address and tostring(category_address) or nil
        if slots == MAX_PAWNS then
            formation_fix.ready, formation_fix.last_category = true, key
            return
        end
        assert(slots == 3, "unexpected native formation slot count=" .. tostring(slots))
        local template = assert(original:get_element(2), "native free-follow template unavailable")
        local template_offset = assert(field(template, "_PositionData"), "native position offset unavailable")
        local created = {}
        local function retain(object)
            assert(object, "formation allocation failed")
            object:add_ref()
            created[#created + 1] = object
            return object
        end
        local function set_value(array, value, index)
            assert(index >= 0 and index < array:get_size(), "formation array index out of bounds")
            array[index] = value
            assert(same(array:get_element(index), value), "formation array assignment/read-back failed")
        end
        local function clone_offset(radius)
            local copy = retain(sdk.create_instance("app.formation.PositioningData.PositionOffsetData"))
            copy:set_field("_RangeX", field(template_offset, "_RangeX"))
            copy:set_field("_RangeZ", field(template_offset, "_RangeZ"))
            copy:set_field("_UseOppositeX", field(template_offset, "_UseOppositeX"))
            copy:set_field("_IsMoveForward", field(template_offset, "_IsMoveForward"))
            copy:set_field("_Radius", radius)
            assert(math.abs((field(copy, "_Radius") or 0) - radius) < 0.001,
                "formation radius write verification failed")
            return copy
        end
        local function clone_position(radius)
            local copy = retain(sdk.create_instance("app.formation.PositioningData"))
            copy:set_field("_PositionEvaluator", field(template, "_PositionEvaluator"))
            copy:set_field("_Conditions", field(template, "_Conditions"))
            copy:set_field("_FollowID", -1)
            copy:set_field("_IsUseOffsetData", true)
            copy:set_field("_PositionData", clone_offset(radius))
            assert(int(field(copy, "_FollowID")) == -1 and field(copy, "_IsUseOffsetData") == true,
                "formation entry initialization failed")
            return copy
        end
        local replacement = retain(sdk.create_managed_array("app.formation.PositioningData", MAX_PAWNS))
        for i = 0, 2 do
            local entry = assert(original:get_element(i), "native formation entry missing")
            set_value(replacement, entry, i)
        end
        -- Wider radii keep the new entries from competing with the native pair.
        set_value(replacement, clone_position(2.75), 3)
        set_value(replacement, clone_position(4.00), 4)
        assert(count(replacement) == MAX_PAWNS, "formation replacement size verification failed")
        category:set_field("_PositionData", replacement)
        assert(same(field(category, "_PositionData"), replacement), "formation array attachment failed")
        formation_fix.retained[#formation_fix.retained + 1] = {category = category, array = replacement, objects = created}
        formation_fix.ready, formation_fix.applied, formation_fix.last_category = true, formation_fix.applied + 1, key
        record({phase = "formation_slots_extended", original_slots = slots, extended_slots = MAX_PAWNS,
            extra_radii = {2.75, 4.00}})
        pending_export = true
    end)
    if not ok then
        formation_fix.failures = formation_fix.failures + 1
        formation_fix.last_error = tostring(err)
        warnings[#warnings + 1] = "Formation extension unavailable: " .. tostring(err)
        record({phase = "formation_slots_extension_failed", error = tostring(err)})
        pending_export = true
    end
end

local function restore_count(reason)
    if not temporary then return true end
    local pending = temporary
    local current = int(field(pending.manager, SUB))
    -- Only undo our value. Never overwrite a count already recomputed by native code.
    if current == 1 then
        local ok = pcall(function() pending.manager:set_field(SUB, pending.original) end)
        if not ok or int(field(pending.manager, SUB)) ~= pending.original then
            blocked = true
            warnings[#warnings + 1] = "COUNT RESTORE FAILED: quit and restore backup."
            return false
        end
    elseif current == nil then
        blocked = true
        warnings[#warnings + 1] = "Count unreadable during restoration."
        return false
    end
    temporary = nil
    record({ phase = "count_override_released", reason = reason, observed_count = current })
    return true
end

-- Resolve both extra slots from stable saved CharacterIDs. During hire the saved
-- list may have appended before all live pawns exist, so retain the pre-hire prefix.
-- Outside hire, restore_loaded_bridge binds only a consistent complete roster.
local function extra_id(manager, character_id)
    if not bridge_enabled or not same(manager, target_manager) then return nil end
    local ids = saved_ids(manager)
    if not ids or #ids < 4 or not baseline then return nil end
    if #ids ~= #baseline and not (scope and #ids == #baseline + 1) then return nil end
    local seen = {}
    for i, cid in ipairs(ids) do
        if seen[cid] or (baseline[i] ~= nil and baseline[i] ~= cid) then return nil end
        seen[cid] = true
    end
    local p, main = party(), false
    for _, pawn in ipairs(p.roster or {}) do
        if pawn.pawn_id == 0 and pawn.character_id == ids[1] then main = true end
    end
    if not main then return nil end
    local mappings = {}
    for i = 4, #ids do mappings[tostring(ids[i])] = i - 1 end
    bridge_id = ids[4] -- legacy diagnostic field; mappings contains all extra slots
    local address = safe(function() return sdk.to_int64(sdk.to_ptr(manager)) end)
    if address and address ~= 0 then
        cached_quit_bridge = {manager_address = tostring(address), mappings = mappings}
    end
    if character_id ~= nil then return mappings[tostring(character_id)] end
    return bridge_id
end

record = function(event)
    if #events >= MAX_EVENTS then
        table.remove(events, 1)
        discarded_events = discarded_events + 1
    end
    event.frame = frame
    -- Player destruction is a managed-object teardown boundary. Do not query
    -- PawnManager there; automatic_suspend supplies its cached snapshot.
    if event.party == nil and not event.no_party_snapshot then event.party = party() end
    event.no_party_snapshot = nil
    events[#events + 1] = event
end

-- Repair a compacted eligible roster at manual ARM or confirmed automatic hiring.
-- Match stable CharacterIDs to saved-list positions; never infer identity from
-- the stale PawnID or from the live list order. No list/save/count writes.
local function repair_compacted_ids()
    if blocked or active or scope or temporary then return false end
    local p = party()
    local n = p.party_count
    if n == 4 and not party_talk_guard.ready then return false end
    if not n or n < 3 or n >= MAX_PAWNS or p.saved_count ~= n or p.sub_count ~= n - 1
        or not p.saved_character_ids or #p.roster ~= n then return false end
    local positions, seen, changes = {}, {}, {}
    for i, cid in ipairs(p.saved_character_ids) do
        if positions[cid] ~= nil then return false end
        positions[cid] = i - 1
    end
    local m = safe(function() return sdk.get_managed_singleton("app.PawnManager") end)
    local items = field(field(m, "_PartyPawnList"), "_items")
    for _, entry in ipairs(p.roster) do
        local desired = positions[entry.character_id]
        local old = entry.pawn_id
        if desired == nil or seen[desired] or old == nil or old < 0 or old >= MAX_PAWNS
            or (desired == 0 and old ~= 0) or (desired ~= 0 and old == 0) then return false end
        seen[desired] = true
        local pawn = safe(function() return items:get_element(entry.index) end)
        if not pawn or pawn_character_id(pawn) ~= entry.character_id then return false end
        if old ~= desired then
            changes[#changes + 1] = {pawn = pawn, old = old, desired = desired, cid = entry.character_id}
        end
    end
    if #changes == 0 then return full_party() end
    record({phase = "slot_repair_begin", reason = "hire_preparation"})
    local written = {}
    for _, change in ipairs(changes) do
        written[#written + 1] = change
        local ok = pcall(function() change.pawn:set_field("_PawnID", change.desired) end)
        if not ok or int(field(change.pawn, "_PawnID")) ~= change.desired then
            for i = #written, 1, -1 do
                local c = written[i]
                pcall(function() c.pawn:set_field("_PawnID", c.old) end)
            end
            blocked = true
            warnings[#warnings + 1] = "Pawn slot repair failed; stop testing and reload your backup."
            record({phase = "slot_repair_failed"})
            pending_export = true
            return false
        end
    end
    if not full_party() then
        for i = #written, 1, -1 do
            local c = written[i]
            pcall(function() c.pawn:set_field("_PawnID", c.old) end)
        end
        blocked = true
        warnings[#warnings + 1] = "Pawn slot verification failed; stop testing and reload your backup."
        record({phase = "slot_repair_failed_validation"})
        pending_export = true
        return false
    end
    record({phase = "slot_repair_completed", repaired_pawns = #changes})
    pending_export = true
    return true
end

-- Reconstruct only Lua lookup state. Do not hire, dismiss, renumber, change
-- counts or write save data during loading. Wait for a consistent expanded roster.
local function restore_loaded_bridge(manager)
    if blocked or active or scope or temporary then return end
    if not same(manager, safe(function()
        return sdk.get_managed_singleton("app.PawnManager") end)) then return end
    local p = party()
    local n = p.party_count
    if not n or n < 4 or n > MAX_PAWNS or p.saved_count ~= n or p.sub_count ~= n - 1
        or #p.roster ~= n or not p.saved_character_ids then return end
    local seen, chars = {}, {}
    for _, pawn in ipairs(p.roster) do
        local id = pawn.pawn_id
        if id == nil or id < 0 or id >= n or seen[id] then return end
        if not pawn.character_id or p.saved_character_ids[id + 1] ~= pawn.character_id then return end
        seen[id] = true
    end
    for _, id in ipairs(p.saved_character_ids) do
        if chars[id] then return end
        chars[id] = true
    end
    local unchanged = bridge_enabled and same(manager, target_manager) and baseline and #baseline == n
    if unchanged then
        for i, cid in ipairs(p.saved_character_ids) do
            if baseline[i] ~= cid then unchanged = false; break end
        end
    end
    if unchanged then return end
    target_manager, baseline = manager, p.saved_character_ids
    bridge_id = p.saved_character_ids[4]
    bridge_enabled, bridge_source = true, "loaded_party"
    auto_restores = auto_restores + 1
    extra_id(manager) -- cache both primitive mappings before any world-unload hook
    record({ phase = "loaded_party_bridge_restored", character_ids = p.saved_character_ids })
    status = "Loaded-party ID correction restored. No ARM needed."
    pending_export = true
end

local function maintain_loaded_bridge()
    local manager = safe(function() return sdk.get_managed_singleton("app.PawnManager") end)
    -- Rebind after native dismissal/replacement only when the live roster matches
    -- the saved identities. Discard stale quit mappings during roster transitions.
    if bridge_enabled and not scope and not active and
        (not same(manager, target_manager) or
        (count(field(manager, "_SavedPartyPawnList")) or 0) < 4 or
        extra_id(manager) == nil) then
        bridge_enabled, bridge_source = false, "none"
        cached_quit_bridge = nil
        target_manager, baseline, bridge_id = nil, nil, nil
        record({ phase = "bridge_cleared_on_roster_change" })
        pending_export = true
    end
    restore_loaded_bridge(manager)
end

local function signature(name, params, result, owner)
    local td = safe(function() return sdk.find_type_definition(owner or "app.PawnManager") end)
    if not td then return nil end
    for _, m in ipairs(safe(function() return td:get_methods() end) or {}) do
        if m:get_name() == name and not m:is_static()
            and m:get_num_params() == #params
            and m:get_return_type():get_full_name() == result then
            local types, ok = m:get_param_types() or {}, true
            for i, expected in ipairs(params) do
                if not types[i] or types[i]:get_full_name() ~= expected then ok = false; break end
            end
            if ok then return m end
        end
    end
end

local function hook(name, params, result, pre, post, owner)
    local label = name .. "(" .. table.concat(params, ", ") .. ")"
    local m = safe(function() return signature(name, params, result, owner) end)
    if not m then
        warnings[#warnings + 1] = "Missing exact signature: " .. label
        return false
    end
    local is_id_lookup = name == "getPartyPawnID" and #params == 1 and params[1] == "app.CharacterID"
    local is_setup = name == "setupAsPartyPawn" and owner == nil
    local is_rental = owner == "app.TalkEventPlayer"
        and (name == "startPawnRentalNode" or name == "updatePawnRentalNode")
    local entry_key = "mp_suspended_entry:" .. (owner or "app.PawnManager") .. ":" .. label
    local ok, err = pcall(function()
        sdk.hook(m, function(args)
            -- Native rental activity is an event-based fallback if a reload
            -- bypassed set_ManualPlayer. Never poll managed objects at title.
            if suspended and suspension_mode == "automatic" and is_rental and try_resume then
                schedule_resume("rental_activity", 1)
            end
            thread.get_hook_storage()[entry_key] = suspended
            if suspended then
                if is_id_lookup then
                    local storage = thread.get_hook_storage()
                    storage.mp_quit_id_match = nil
                    if quit_bridge then
                        local receiver_address = safe(function() return sdk.to_int64(args[2]) end)
                        local cid = safe(function() return sdk.to_int64(args[3]) & 0xffffffff end)
                        if receiver_address and receiver_address ~= 0
                            and tostring(receiver_address) == quit_bridge.manager_address and cid then
                            storage.mp_quit_id_match = quit_bridge.mappings[tostring(cid)]
                        end
                    end
                end
                return
            end
            return pre(args)
        end, function(retval)
            local entry_storage = thread.get_hook_storage()
            local entered_suspended = entry_storage[entry_key]
            entry_storage[entry_key] = nil
            if suspended and suspension_mode == "automatic" and entered_suspended and is_setup
                and try_resume then
                local raw = safe(function() return sdk.to_int64(retval) end)
                if raw and raw ~= 0 then schedule_resume("party_pawn_setup_return", 1) end
            end
            -- A suspended pre-hook did not initialize the normal post-hook's
            -- state. Rebinding is done by try_resume, so do not run that post.
            if entered_suspended and not suspended then return retval end
            if suspended then
                if is_id_lookup then
                    local storage = thread.get_hook_storage()
                    local matches = storage.mp_quit_id_match
                    storage.mp_quit_id_match = nil
                    local raw = safe(function() return sdk.to_int64(retval) end)
                    if matches and raw and (raw & 0xffffffff) == 0xffffffff then
                        return sdk.to_ptr(matches)
                    end
                end
                return retval
            end
            return post(retval)
        end)
    end)
    if not ok then
        warnings[#warnings + 1] = "Cannot hook " .. label .. ": " .. tostring(err)
        return false
    end
    installed[#installed + 1] = label
    return true
end

local function export(cached)
    -- Retained as a call-site compatibility shim for lifecycle safeguards.
    -- Production builds deliberately perform no report collection or disk I/O.
    pending_export = false
end

-- Invoked only by explicit lifecycle/load/rental events or the recovery button.
-- Suspended frame/lookup/party-talk callbacks remain free of managed polling.
try_resume = function(reason, explicit)
    if not suspended then return true end
    if suspension_mode == "manual" and not explicit then return false end
    resume_state.attempts = resume_state.attempts + 1
    local function refuse(why)
        resume_state.last_refusal = why
        return false
    end
    if blocked or scope or temporary or xp_copies_in_flight ~= 0 then
        return refuse("mod blocked or native operation still active")
    end
    local cm = safe(function() return sdk.get_managed_singleton("app.CharacterManager") end)
    local pl = field(cm, "<ManualPlayer>k__BackingField")
    local address = pl and safe(function() return sdk.to_int64(sdk.to_ptr(pl)) end)
    if not address or address == 0 then return refuse("live ManualPlayer unavailable") end
    local p = party()
    local n = p.party_count
    if not n or n < 1 or n > MAX_PAWNS or p.saved_count ~= n or p.sub_count ~= n - 1
        or not p.saved_character_ids or #p.roster ~= n then
        return refuse("waiting for complete live/saved pawn roster")
    end
    local expected, seen, main = {}, {}, false
    for _, cid in ipairs(p.saved_character_ids) do
        if expected[cid] then return refuse("duplicate saved identity") end
        expected[cid] = true
    end
    for _, pawn in ipairs(p.roster) do
        local cid, id = pawn.character_id, pawn.pawn_id
        if not cid or not expected[cid] or seen[cid] or id == nil or id < 0 or id >= MAX_PAWNS then
            return refuse("live/saved identity mismatch")
        end
        seen[cid] = true
        if id == 0 then
            if cid ~= p.saved_character_ids[1] then return refuse("main pawn identity mismatch") end
            main = true
        end
    end
    if not main then return refuse("main pawn unavailable") end
    -- Stale non-main slot numbers may remain after dismissal. Resume without
    -- renumbering; the existing explicit hire-preparation repair owns that write.
    suspended, suspension_mode = false, nil
    player_address = tostring(address)
    quit_bridge, cached_quit_bridge = nil, nil
    target_manager, baseline, bridge_id, rental_scope = nil, nil, nil, nil
    bridge_enabled, bridge_source = false, "none"
    armed, active, replacing_at_cap, auto_rental = false, false, false, nil
    finish_deadline = 0
    last_live_party = p
    automatic_hooks.resumes = automatic_hooks.resumes + 1
    resume_state.last_reason, resume_state.last_refusal = reason, nil
    maintain_loaded_bridge()
    record({phase = "world_resumed", reason = reason})
    export()
    status = "Active after validated world load (" .. reason .. ")."
    return true
end

schedule_resume = function(reason, delay)
    if not suspended or suspension_mode ~= "automatic" then return end
    resume_pending, resume_reason = true, reason
    -- Never validate a roster inside set_ManualPlayer's native post-hook.
    resume_frame = lifecycle_frame + (delay or 12)
end

local game = safe(function() return reframework:get_game_name() end)
local tdb = safe(function() return sdk.get_tdb_version() end)
if game ~= "dd2" or tdb ~= 83 or not now() or not thread or not thread.get_hook_storage
    or not sdk.PreHookResult or not sdk.PreHookResult.SKIP_ORIGINAL then
    blocked = true
    status = "Recovery disabled: requires DD2 TDB 83 and REFramework hook storage/skip support."
else
    -- The crash log identifies this controller path, but does not supply a
    -- signature. Require one unique instance Void update() at runtime.
    -- This bypass is an isolation experiment, not a native data-layout repair.
    local talk_td = safe(function() return sdk.find_type_definition("app.PLPartyTalkController") end)
    local talk_method, talk_matches = nil, 0
    for _, m in ipairs(talk_td and safe(function() return talk_td:get_methods() end) or {}) do
        if m:get_name() == "update" and not m:is_static() and m:get_num_params() == 0
            and m:get_return_type():get_full_name() == "System.Void" then
            talk_method, talk_matches = m, talk_matches + 1
        end
    end
    party_talk_guard.signature_matches = talk_matches
    local retained_speaker_arrays = {}
    local function ensure_result_array(controller)
        local original = field(controller, chatter_result_array_fix.field)
        local original_slots = count(original)
        -- Controllers are destroyed and recreated across a title-screen load.
        -- A prior controller's repaired array cannot establish the capacity of
        -- the new controller. Validate the live field every time; once this
        -- particular controller has five slots, this is read-only.
        if original_slots == chatter_result_array_fix.required_slots then
            chatter_result_array_fix.ready = true
            chatter_result_array_fix.last_observed_slots = original_slots
            return true
        end
        if original_slots ~= chatter_result_array_fix.expected_slots then
            chatter_result_array_fix.failures = chatter_result_array_fix.failures + 1
            chatter_result_array_fix.last_error = "unexpected speaker result slot count=" .. tostring(original_slots)
            return false
        end
        local replacement
        local ok, err = pcall(function()
            -- SpeakerEvaluateResult is a value type. A fresh managed array
            -- supplies initialized default value slots without copying any
            -- transient references from a four-slot controller allocation.
            replacement = assert(sdk.create_managed_array(
                "app.PLPartyTalkController.SpeakerEvaluateResult", chatter_result_array_fix.required_slots),
                "speaker result array allocation failed"):add_ref()
            assert(count(replacement) == chatter_result_array_fix.required_slots,
                "speaker result replacement size verification failed")
            controller:set_field(chatter_result_array_fix.field, replacement)
            assert(count(field(controller, chatter_result_array_fix.field)) == chatter_result_array_fix.required_slots,
                "speaker result field write verification failed")
        end)
        if not ok then
            if original then safe(function() controller:set_field(chatter_result_array_fix.field, original) end) end
            if replacement then safe(function() replacement:release() end) end
            chatter_result_array_fix.failures = chatter_result_array_fix.failures + 1
            chatter_result_array_fix.last_error = tostring(err)
            return false
        end
        retained_speaker_arrays[#retained_speaker_arrays + 1] = replacement
        chatter_result_array_fix.ready = true
        chatter_result_array_fix.applied = chatter_result_array_fix.applied + 1
        chatter_result_array_fix.original_slots = original_slots
        chatter_result_array_fix.last_observed_slots = chatter_result_array_fix.required_slots
        record({method = "PLPartyTalkController speaker result array", phase = "applied",
            original_slots = original_slots, repaired_slots = chatter_result_array_fix.required_slots,
            static_max_party_num = chatter_result_array_fix.static_max_party_num})
        export()
        return true
    end
    if talk_matches == 1 then
        local ok, err = pcall(function()
            sdk.hook(talk_method, function(args)
                if suspended then
                    -- Never inspect managed objects during world teardown.
                    for _, id in pairs(quit_bridge and quit_bridge.mappings or {}) do
                        if id == 4 then
                            party_talk_guard.suspended_skips = party_talk_guard.suspended_skips + 1
                            return sdk.PreHookResult.SKIP_ORIGINAL
                        end
                    end
                    return
                end
                local manager = safe(function() return sdk.get_managed_singleton("app.PawnManager") end)
                local live = count(field(manager, "_PartyPawnList"))
                local saved = count(field(manager, "_SavedPartyPawnList"))
                -- Either list may lead during a Rift/scene transition. Do not
                -- change lists, IDs, counts, dialogue data or method arguments.
                if (live or 0) >= 5 or (saved or 0) >= 5 then
                    if ensure_result_array(receiver(args)) then return end
                    party_talk_guard.skipped = party_talk_guard.skipped + 1
                    if party_talk_guard.skipped == 1 then
                        record({method = party_talk_guard.method, phase = "party_talk_update_skipped",
                            live_count = live, saved_count = saved})
                        export()
                    end
                    return sdk.PreHookResult.SKIP_ORIGINAL
                end
            end, function(retval) return retval end)
        end)
        party_talk_guard.ready = ok
        if not ok then party_talk_guard.error = tostring(err) end
    end
    if not party_talk_guard.ready then
        warnings[#warnings + 1] = "Party-talk diagnostic hook unavailable: fourth hired pawn disabled."
    else
        installed[#installed + 1] = party_talk_guard.method .. " [five-pawn diagnostic bypass]"
    end
    local dismiss_ok = 0
    for _, param in ipairs({"app.CharacterID", "app.Character", "app.Pawn"}) do
        if hook("dismissPawn", {param}, "System.Void", function(args)
            local storage = thread.get_hook_storage()
            storage.dd2_third_hire_skipped = false
            local m = receiver(args)
            if automatic_hooks.hiring and not blocked and not active and not replacing_at_cap
                and auto_rental and auto_rental.phase == 2 and now() - auto_rental.time <= 5 then
                local p = party()
                auto_rental = nil -- consume one confirmed hire flow, including nested dismiss overloads
                if p.party_count == MAX_PAWNS and p.saved_count == MAX_PAWNS then
                    replacing_at_cap = true
                    finish_deadline = now() + 30
                elseif p.party_count and p.party_count >= 3 and p.party_count < MAX_PAWNS
                    and p.saved_count == p.party_count then
                    if not full_party() then repair_compacted_ids() end
                    if full_party() then
                        armed, arm_deadline = true, now() + 5
                        record({phase = "automatic_hire_armed"})
                    end
                end
            end
            if not armed or blocked or active or now() > arm_deadline then
                record({method = "dismissPawn(" .. param .. ")", phase = "native_dismiss_enter",
                    rental_context = rental_scope})
                return
            end
            if not full_party() or not same(m, safe(function()
                return sdk.get_managed_singleton("app.PawnManager") end)) then
                armed = false
                record({phase = "armed_dismissal_refused_changed_party"})
                return
            end
            -- At the explicitly armed replacement confirmation, preserve the old pawn.
            -- Ordinary dismissals while disarmed still execute normally.
            target_manager, baseline, bridge_id = m, party().saved_character_ids, nil
            armed, active = false, true
            storage.dd2_third_hire_skipped = true
            skip_count = skip_count + 1
            finish_deadline = now() + 30
            record({method = "dismissPawn(" .. param .. ")", phase = "original_skipped",
                rental_context = rental_scope})
            export()
            return sdk.PreHookResult.SKIP_ORIGINAL
        end, function(retval)
            local storage = thread.get_hook_storage()
            if storage.dd2_third_hire_skipped then
                storage.dd2_third_hire_skipped = false
                record({method = "dismissPawn(" .. param .. ")", phase = "skip_return"})
            else
                maintain_loaded_bridge()
                record({method = "dismissPawn(" .. param .. ")", phase = "native_dismiss_return"})
            end
            return retval
        end) then dismiss_ok = dismiss_ok + 1 end
    end

    -- Read-only observations; no rental count writes. Keep diagnostics bounded.
    local rent_td = safe(function() return sdk.find_type_definition("app.PawnRentalNode.DisplayType") end)
    for _, f in ipairs(rent_td and safe(function() return rent_td:get_fields() end) or {}) do
        if f:is_static() then rent_types[f:get_name()] = int(safe(function() return f:get_data(nil) end)) end
    end
    local rental_ok = 0
    for _, name in ipairs({"startPawnRentalNode", "updatePawnRentalNode"}) do
        local key = "mp_rental:" .. name
        if hook(name, {}, "System.Void", function(args)
            local storage = thread.get_hook_storage()
            storage[key] = rental_scope
            rental_calls[name] = (rental_calls[name] or 0) + 1
            local player = receiver(args)
            local node = field(player, "_CurrentNode")
            local node_type = node and safe(function() return node:get_type_definition():get_full_name() end)
            local rent_type = int(field(node, "_RentType"))
            local phase = int(field(player, "_PawnReplacementPhase"))
            if node_type == "app.PawnRentalNode" and rent_type == 0 then
                auto_rental = {phase = phase, time = now()}
            else
                auto_rental = nil
            end
            rental_scope = {method = name, node_type = node_type, rent_type = rent_type,
                replacement_phase = phase}
            local fingerprint = tostring(node_type) .. ":" .. tostring(rent_type) .. ":" .. tostring(phase)
            if name == "startPawnRentalNode" or rental_last_state[name] ~= fingerprint then
                rental_last_state[name] = fingerprint
                record({method = name, phase = "rental_observed", context = rental_scope})
            end
        end, function(retval)
            local storage = thread.get_hook_storage()
            rental_scope = storage[key]
            storage[key] = nil
            return retval
        end, "app.TalkEventPlayer") then rental_ok = rental_ok + 1 end
    end
    automatic_hooks.hiring = rental_ok == 2

    local hire_ok = hook("hirePawn", {"app.Character", "System.Boolean"}, "System.Boolean",
        function(args)
            local storage = thread.get_hook_storage()
            storage.dd2_third_hire_active = nil
            storage.dd2_third_hire_abort = false
            local m = receiver(args)
            if not same(m, safe(function() return sdk.get_managed_singleton("app.PawnManager") end)) then return end
            local p = party()
            if p.party_count == 4 and not party_talk_guard.ready then
                storage.dd2_third_hire_abort = true
                record({method = "hirePawn", phase = "fourth_hire_refused_no_party_talk_guard"})
                pending_export = true
                return sdk.PreHookResult.SKIP_ORIGINAL
            end
            -- A normal replacement may dismiss first; an append at five is refused.
            if (p.party_count or 0) >= MAX_PAWNS or (p.saved_count or 0) >= MAX_PAWNS or scope then
                cap_blocks = cap_blocks + 1
                storage.dd2_third_hire_abort = true
                record({method = "hirePawn", phase = "cap_or_overlapping_hire_refused"})
                return sdk.PreHookResult.SKIP_ORIGINAL
            end
            hire_seen = true
            record({method = "hirePawn", phase = "hire_enter"})
            if replacing_at_cap and not blocked then
                replacing_at_cap = false
                if not full_party() then repair_compacted_ids() end
                active = full_party() and true or false
            end
            if blocked or not active or not full_party() then
                armed = false
                return
            end
            target_manager, baseline, bridge_id = m, p.saved_character_ids, nil
            active, scope = true, {}
            storage.dd2_third_hire_active = scope
            if not temporary then
                record({method = "hirePawn", phase = "before_count_override"})
                export()
                temporary = {manager = m, original = p.sub_count}
                local ok = pcall(function() m:set_field(SUB, 1) end)
                if not ok or int(field(m, SUB)) ~= 1 then
                    restore_count("hire_write_failed")
                    active, scope = false, nil
                    storage.dd2_third_hire_active = nil
                    storage.dd2_third_hire_abort = true
                    blocked = true
                    warnings[#warnings + 1] = "Hire count override failed."
                    return sdk.PreHookResult.SKIP_ORIGINAL
                end
            end
            extended_hires = extended_hires + 1
            bridge_enabled, bridge_source = true, "armed_hire"
            record({method = "hirePawn", phase = "before_original"})
            export() -- persist the last Lua boundary before the native hire
        end, function(retval)
            local storage = thread.get_hook_storage()
            if storage.dd2_third_hire_abort then return sdk.to_ptr(0) end
            if storage.dd2_third_hire_active then
                restore_count("hire_return")
                active, scope = false, nil
                storage.dd2_third_hire_active = nil
                maintain_loaded_bridge()
            end
            local raw = safe(function() return sdk.to_int64(retval) end)
            local success
            if type(raw) == "number" then success = (raw & 0xff) ~= 0 end
            record({method = "hirePawn", phase = "after_original", result = success})
            export() -- do not wait for a frame if native code crashes after returning
            finish_deadline = now() + 2
            return retval
        end)

    local setup_ok = hook("setupAsPartyPawn", { "app.Character" }, "app.Pawn",
        function(args)
            local storage = thread.get_hook_storage()
            storage.dd2_third_hire_setup = active
            storage.dd2_setup_manager = receiver(args)
            if active then record({ method = "setupAsPartyPawn", phase = "before_original" }) end
        end, function(retval)
            local storage = thread.get_hook_storage()
            restore_loaded_bridge(storage.dd2_setup_manager)
            storage.dd2_setup_manager = nil
            if storage.dd2_third_hire_setup then
                record({ method = "setupAsPartyPawn", phase = "after_original",
                    returned_pawn = retval ~= nil and tostring(retval) ~= "0x0" })
                storage.dd2_third_hire_setup = false
            end
            return retval
        end)

    local update_ok = hook("updateSubPawnNum", {}, "System.Void",
        function(args)
            local storage = thread.get_hook_storage()
            storage.dd2_third_hire_sub = active or temporary ~= nil
            if temporary and same(receiver(args), temporary.manager) then
                restore_count("before_native_recount")
            end
            if storage.dd2_third_hire_sub then
                record({ method = "updateSubPawnNum", phase = "before_original" })
            end
        end, function(retval)
            local storage = thread.get_hook_storage()
            if storage.dd2_third_hire_sub then
                record({ method = "updateSubPawnNum", phase = "after_original" })
                storage.dd2_third_hire_sub = false
            end
            return retval
        end)

    local id_ok = hook("getPartyPawnID", { "app.CharacterID" }, "app.PawnManager.PawnID",
            function(args)
                local storage = thread.get_hook_storage()
                storage.dd2_third_hire_id = nil
                if not blocked then
                    storage.dd2_third_hire_id = {
                        manager = receiver(args),
                        character = safe(function() return sdk.to_int64(args[3]) & 0xffffffff end),
                    }
                end
            end, function(retval)
                local storage = thread.get_hook_storage()
                local context = storage.dd2_third_hire_id
                if context then
                    -- Handles the first lookup after either extra pawn is created,
                    -- even if the frame callback has not run yet.
                    local raw = safe(function() return sdk.to_int64(retval) end)
                    storage.dd2_third_hire_id = nil
                    if raw and (raw & 0xffffffff) == 0xffffffff then
                        restore_loaded_bridge(context.manager)
                    end
                    local corrected = raw and (raw & 0xffffffff) == 0xffffffff
                        and context.character ~= nil and extra_id(context.manager, context.character)
                    if raw and (raw & 0xffffffff) == 0xffffffff and corrected then
                        corrections = corrections + 1
                        local slot_key = tostring(corrected)
                        corrections_by_slot[slot_key] = (corrections_by_slot[slot_key] or 0) + 1
                        if corrections_by_slot[slot_key] <= 5 then
                            record({ method = "getPartyPawnID(CharacterID)", phase = "corrected",
                                original = -1, result = corrected, character_id = context.character })
                        end
                        return sdk.to_ptr(corrected)
                    end
                end
                return retval
            end)
    if dismiss_ok ~= 3 or not hire_ok or not setup_ok or not update_ok or not id_ok then
        blocked = true
        status = "Recovery disabled: missing a required hire/ID hook."
    end
end

re.on_frame(function()
    lifecycle_frame = lifecycle_frame + 1
    if suspended then
        if resume_pending and suspension_mode == "automatic" and lifecycle_frame >= resume_frame then
            -- Failure is expected while pawns are still streaming. Keep all
            -- compatibility hooks suspended, then retry outside native load.
            if try_resume(resume_reason or "deferred_world_load") then
                resume_pending, resume_reason = false, nil
            else
                resume_frame = lifecycle_frame + 12
            end
        end
        return
    end
    -- One-time bootstrap for the automatic world-unload hook. This stops as
    -- soon as the current Arisen is available; it is not a party monitor.
    if not player_address then
        local cm = safe(function() return sdk.get_managed_singleton("app.CharacterManager") end)
        local pl = field(cm, "<ManualPlayer>k__BackingField")
        local pa = pl and safe(function() return sdk.to_int64(sdk.to_ptr(pl)) end)
        if pa and pa ~= 0 then player_address = tostring(pa) end
    end
    ensure_extended_formation()
    menu_mockup_fix.repair()
    if xp_tracing then frame = frame + 1 end
    local time = (xp_tracing or armed or finish_deadline > 0) and now() or nil
    if xp_tracing and time >= xp_trace_deadline then
        xp_tracing = false
        pending_export = true
    end
    if armed and time > arm_deadline then
        armed = false
        record({phase = "arm_expired"})
        status = "ARM expired. No dismissal skipped."
    end
    if finish_deadline > 0 and now() >= finish_deadline then
        finish_deadline = 0
        replacing_at_cap = false
        if active then
            active = false
            record({ phase = "hire_observation_timeout" })
            status = "Hire observation timed out."
        end
        pending_export = true
    end
    if pending_export and not temporary and not scope then export() end
end)

-- On-demand read-only discovery: no XP methods invoked or hooked.
local function capture_xp()
    if active or scope or temporary then
        status = "Finish the hire before taking an XP snapshot."
        return
    end
    local function name(td) return td and safe(function() return td:get_full_name() end) end
    local function relevant(text)
        text = string.lower(text or "")
        return text:find("exp", 1, true) or text:find("level", 1, true)
            or text:find("status", 1, true) or text:find("param", 1, true)
    end
    if not xp_metadata then
        xp_metadata = {}
        local queue = {"app.ExpDispenser", "app.ExpDispenser.ExpGranter", "app.Character",
            "app.Player", "app.CharacterManager"}
        local visited, index = {}, 1
        while index <= #queue and index <= 40 do
            local type_name = queue[index]; index = index + 1
            if not visited[type_name] then
                visited[type_name] = true
                local td = safe(function() return sdk.find_type_definition(type_name) end)
                local row = {name = type_name, available = td ~= nil, fields = {}, methods = {}}
                xp_metadata[#xp_metadata + 1] = row
                if td then
                    for _, f in ipairs(safe(function() return td:get_fields() end) or {}) do
                        local ft, fn = name(safe(function() return f:get_type() end)), f:get_name()
                        row.fields[#row.fields + 1] = {name = fn, type = ft,
                            static = f:is_static(), offset = safe(function() return f:get_offset_from_base() end)}
                        if ft and ft:sub(1,4) == "app." and relevant(ft) and not visited[ft] then
                            queue[#queue + 1] = ft
                        end
                    end
                    for _, m in ipairs(safe(function() return td:get_methods() end) or {}) do
                        local params = {}
                        for _, t in ipairs(m:get_param_types() or {}) do params[#params + 1] = name(t) end
                        row.methods[#row.methods + 1] = {name = m:get_name(),
                            static = m:is_static(), parameters = params, returns = name(m:get_return_type())}
                    end
                end
            end
        end
    end
    local snap = {time = now(), party = party(), objects = {}, read_only = true}
    local cm = safe(function() return sdk.get_managed_singleton("app.CharacterManager") end)
    local queue = {{object = cm, path = "CharacterManager", depth = 0}}
    local seen, index = {}, 1
    while index <= #queue and index <= 48 do
        local item = queue[index]; index = index + 1
        local obj = item.object
        local address = obj and safe(function() return tostring(obj:get_address()) end)
        if address and not seen[address] then
            seen[address] = true
            local td = safe(function() return obj:get_type_definition() end)
            local row = {path = item.path, type = name(td), values = {}}
            snap.objects[#snap.objects + 1] = row
            for _, f in ipairs(td and safe(function() return td:get_fields() end) or {}) do
                if not f:is_static() then
                    local fn = f:get_name()
                    local ft = name(safe(function() return f:get_type() end))
                    local value = safe(function() return f:get_data(obj) end)
                    local kind = type(value)
                    if kind == "number" or kind == "boolean" or kind == "string" then
                        row.values[fn] = value
                    elseif value and item.depth < 4 and (relevant(fn) or relevant(ft)
                        or fn:find("ManualPlayer", 1, true)) then
                        queue[#queue + 1] = {object = value, path = item.path .. "." .. fn, depth = item.depth + 1}
                    end
                end
            end
        end
    end
    if #xp_snapshots >= 8 then table.remove(xp_snapshots, 1) end
    xp_snapshots[#xp_snapshots + 1] = snap
    pending_export = true
    status = "XP snapshot captured (" .. #xp_snapshots .. "/8). Exporting report."
end

-- Bounded observer hooks: original arguments, return values and XP are untouched.
local xp_specs = {
{owner = "app.ExpDispenser", name = "addExpOnDie", static = true, result = "System.Void", params = {"app.HitController.DamageInfo"}},
{owner = "app.ExpDispenser", name = "calcExp", static = true, result = "System.Int32", params = {"app.HitController.DamageInfo", "app.ExpDispenser.ExpGranter", "app.Character", "app.Character"}},
{owner = "app.ExpDispenser", name = "addExpToPlayer", static = true, result = "System.Void", params = {"app.Character", "System.Int32", "System.Collections.Generic.List`1<app.CharacterID>", "app.HitController.DamageInfo"}},
{owner = "app.ExpDispenser", name = "addExpAndJobPoint", static = true, result = "System.Void", params = {"app.CharacterID", "System.Int32", "System.Int32"}},
{owner = "app.ExpDispenser", name = "addExpAndJobPoint", static = true, result = "System.Void", params = {"app.CharacterID", "System.Int32", "app.Character", "app.HitController.DamageInfo"}},
{owner = "app.ExpDispenser", name = "addExpAndJobPoint", static = true, result = "System.Void", params = {"app.CharacterID", "System.Int32", "System.Int32", "app.Character"}},
{owner = "app.ExpDispenser", name = "addExpAndJobPoint", static = true, result = "System.Void", params = {"app.CharacterID", "app.HumanStatusContext", "app.JobContext", "System.Int32", "System.Int32", "System.Boolean", "app.DragonHermitContext"}},
{owner = "app.ExpDispenser", name = "isSubPawn", static = true, result = "System.Boolean", params = {"app.CharacterID"}},
{owner = "app.CharacterExperiencePointsTable", name = "getExpAdjustedForPlayer", static = false, result = "System.Int32", params = {"System.Int32", "System.Int32", "System.Int32", "System.Nullable`1<System.Int32>", "System.Nullable`1<System.Int32>"}}
}
local function trace_event(e)
    if #xp_trace.events >= 240 then
        table.remove(xp_trace.events, 1)
        xp_trace.dropped = xp_trace.dropped + 1
    end
    e.time, e.frame = now(), frame
    xp_trace.events[#xp_trace.events + 1] = e
end
local function trace_value(arg, kind)
    if kind == "System.Int32" or kind == "app.CharacterID" then
        local n = safe(function() return sdk.to_int64(arg) & 0xffffffff end)
        if n and kind == "System.Int32" and n >= 0x80000000 then n = n - 0x100000000 end
        return n
    elseif kind == "System.Boolean" then
        return safe(function() return (sdk.to_int64(arg) & 0xff) ~= 0 end)
    end
    if kind == "app.Character" or kind == "app.HumanStatusContext"
        or kind == "System.Collections.Generic.List`1<app.CharacterID>" then
        local obj = safe(function() return sdk.to_managed_object(arg) end)
        if kind == "app.Character" then
            return {character_id = u32(field(obj, "CharacterID")),
                xp_dispenser = field(obj, "IsEnableExpDispenser")}
        elseif kind == "app.HumanStatusContext" then
            return {exp = int(field(obj, "_Exp")), level = int(field(obj, "_Level"))}
        else
            local ids, items = {}, field(obj, "_items")
            local n = count(obj)
            if n and n >= 0 and n <= 8 then
                for i = 0, n - 1 do ids[#ids + 1] = u32(safe(function() return items:get_element(i) end)) end
            end
            return {count = n, ids = ids}
        end
    end
    return {type = kind, not_decoded = true}
end
local function xp_list_for_call(args)
    local player = safe(function() return sdk.to_managed_object(args[2]) end)
    local cm = safe(function() return sdk.get_managed_singleton("app.CharacterManager") end)
    if not same(player, field(cm, "<ManualPlayer>k__BackingField")) then return end
    local original = safe(function() return sdk.to_managed_object(args[4]) end)
    local n = count(original)
    if not n or n < 4 or n > MAX_PAWNS then return end
    local p = party()
    if p.party_count ~= n or p.saved_count ~= n or p.sub_count ~= n - 1
        or not p.saved_character_ids then return end
    local items, ids, seen = field(original, "_items"), {}, {}
    for i = 0, n - 1 do
        local id = u32(safe(function() return items:get_element(i) end))
        if not id or id ~= p.saved_character_ids[i + 1] or seen[id] then return end
        seen[id], ids[i + 1] = true, id
    end
    -- Preserve the v0.5 three-entry Arisen-only XP argument for either expanded size.
    -- This does not establish correct XP balancing for five pawns.
    -- New managed list, never a size edit on the game's live/saved lists.
    local copy
    local ok, err = pcall(function()
        local tn = "System.Collections.Generic.List`1<app.CharacterID>"
        local td = sdk.find_type_definition(tn)
        local ctor, add
        for _, m in ipairs(td:get_methods() or {}) do
            if not m:is_static() and m:get_name() == ".ctor" and m:get_num_params() == 0 then ctor = m end
            if not m:is_static() and m:get_name() == "Add" and m:get_num_params() == 1
                and m:get_param_types()[1]:get_full_name() == "app.CharacterID" then add = m end
        end
        assert(ctor and add, "XP list constructor/Add signature unavailable")
        copy = assert(sdk.create_instance(tn), "XP list allocation failed"):add_ref()
        ctor:call(copy)
        for i = 1, 3 do add:call(copy, ids[i]) end
        assert(count(copy) == 3, "XP list count verification failed")
        local copied_items = field(copy, "_items")
        for i = 0, 2 do
            assert(u32(copied_items:get_element(i)) == ids[i + 1], "XP list identity verification failed")
        end
        args[4] = sdk.to_ptr(copy)
    end)
    if not ok then
        if copy then safe(function() copy:release() end) end
        xp_fix.failures = xp_fix.failures + 1
        xp_fix.last_error = tostring(err)
        pending_export = true
        return
    end
    xp_copies_in_flight = xp_copies_in_flight + 1
    xp_fix.substitutions = xp_fix.substitutions + 1
    pending_export = true
    return copy
end

local function start_xp_trace(initialize_only)
    if active or scope or temporary then status = "Finish hiring before tracing XP."; return end
    if not xp_trace_installed then
        xp_trace_installed = true
        for index, spec in ipairs(xp_specs) do
            local td = safe(function() return sdk.find_type_definition(spec.owner) end)
            local found, matches = nil, 0
            for _, m in ipairs(td and safe(function() return td:get_methods() end) or {}) do
                if m:get_name() == spec.name and m:is_static() == spec.static
                    and m:get_num_params() == #spec.params
                    and m:get_return_type():get_full_name() == spec.result then
                    local matched = true
                    local types = m:get_param_types() or {}
                    for i, expected in ipairs(spec.params) do
                        if not types[i] or types[i]:get_full_name() ~= expected then matched = false end
                    end
                    if matched then found, matches = m, matches + 1 end
                end
            end
            local label = spec.owner .. "." .. spec.name .. "(" .. table.concat(spec.params, ",") .. ")"
            local key = "mp_xp_trace_" .. index
            local ok = matches == 1 and pcall(function()
                sdk.hook(found, function(args)
                    if suspended then return end
                    local storage = thread.get_hook_storage()
                    storage[key] = nil
                    storage[key .. "_copy"] = nil
                    if spec.owner == "app.ExpDispenser" and spec.name == "addExpToPlayer" then
                        storage[key .. "_copy"] = xp_list_for_call(args)
                    end
                    if not xp_tracing then return end
                    local values = {}
                    for i, kind in ipairs(spec.params) do
                        values[i] = trace_value(args[i + (spec.static and 1 or 2)], kind)
                    end
                    local e = {method = label, phase = "enter", args = values, party = party()}
                    trace_event(e)
                    storage[key] = e.frame
                end, function(retval)
                    if suspended then return retval end
                    local storage = thread.get_hook_storage()
                    local copy = storage[key .. "_copy"]
                    if copy then
                        storage[key .. "_copy"] = nil
                        safe(function() copy:release() end)
                        xp_copies_in_flight = xp_copies_in_flight - 1
                    end
                    if storage[key] ~= nil then
                        local result
                        if spec.result ~= "System.Void" then result = trace_value(retval, spec.result) end
                        trace_event({method = label, phase = "return", enter_frame = storage[key], result = result})
                        storage[key] = nil
                    end
                    return retval
                end)
            end)
            if ok then
                xp_trace.hooks[#xp_trace.hooks + 1] = label
                if spec.owner == "app.ExpDispenser" and spec.name == "addExpToPlayer" then xp_fix.ready = true end
            else xp_trace.warnings[#xp_trace.warnings + 1] = "Observer unavailable: " .. label end
        end
    end
    if initialize_only then return end
    xp_tracing, xp_trace_deadline = true, now() + 60
    trace_event({phase = "trace_started", party = party()})
    pending_export = true
    status = "XP trace active for 60 seconds. Kill one enemy, then Stop XP trace."
end

if game == "dd2" and tdb == 83 and not blocked then start_xp_trace(true) end

-- Actual player destruction / replacement delimit the loaded world.
-- These hooks remain active while suspended so returning from title can resume.
local function automatic_suspend(reason)
    if suspended then return end
    -- World teardown wins over an in-flight operation: its managed references
    -- may already be invalid, so neither restore nor inspect them here.
    if temporary or scope or xp_copies_in_flight ~= 0 then
        warnings[#warnings + 1] = "World unload interrupted a native operation; stale state was not touched."
    end
    quit_bridge = cached_quit_bridge
    suspension_mode = "automatic"
    suspended, armed, xp_tracing, active = true, false, false, false
    resume_pending, resume_reason, resume_frame = false, nil, 0
    replacing_at_cap, auto_rental = false, nil
    finish_deadline, pending_export = 0, false
    -- Drop Lua references without dereferencing them.  Retaining a manager or
    -- a native-operation scope across player destruction is unsafe and would
    -- make deferred recovery refuse forever.
    temporary, scope = nil, nil
    target_manager, baseline, bridge_id, rental_scope = nil, nil, nil, nil
    bridge_enabled = false
    automatic_hooks.suspensions = automatic_hooks.suspensions + 1
    record({phase = "automatic_suspend", reason = reason, party = last_live_party,
        no_party_snapshot = true})
    export(true)
    status = "Suspended for world unload; waiting for validated player/party load."
end
local function lifecycle_hook(name, params, owner, pre, post)
    local m = safe(function() return signature(name, params, "System.Void", owner) end)
    if not m then return false end
    return pcall(function() sdk.hook(m, pre, post) end)
end
if not blocked then
    local destroy_ok = lifecycle_hook("onDestroy", {}, "app.Character", function(args)
        local address = safe(function() return sdk.to_int64(args[2]) end)
        if address and tostring(address) == player_address then automatic_suspend("player_onDestroy") end
    end, function(retval) return retval end)
    local assign_ok = lifecycle_hook("set_ManualPlayer", {"app.Character"}, "app.CharacterManager", function(args)
        local address = safe(function() return sdk.to_int64(args[3]) end)
        local st = thread.get_hook_storage()
        st.mp_assigned_player = address and address ~= 0 and tostring(address) or nil
        if address == 0 and player_address then automatic_suspend("manual_player_cleared") end
    end, function(retval)
        local st = thread.get_hook_storage()
        if st.mp_assigned_player then
            player_address = st.mp_assigned_player
            if suspended then
                schedule_resume("manual_player_assigned")
            end
            st.mp_assigned_player = nil
        end
        return retval
    end)
    automatic_hooks.lifecycle = destroy_ok and assign_ok
    if not automatic_hooks.lifecycle then
        warnings[#warnings + 1] = "Automatic exit hooks unavailable; use manual suspension."
    end
end

local function suspend_for_quit()
    if active or scope or temporary or xp_copies_in_flight ~= 0 then
        status = "Cannot suspend during a hire or XP call. Finish the action and try again."
        return
    end
    local p = party()
    if (p.party_count or 0) >= 4 or (p.saved_count or 0) >= 4 then
        maintain_loaded_bridge()
        local cid = extra_id(target_manager)
        local address = target_manager and safe(function() return sdk.to_int64(sdk.to_ptr(target_manager)) end)
        if not cid or not address or address == 0 then
            status = "Cannot prepare expanded-party exit: ID bridge unavailable. Dismiss the last extra pawn first."
            return
        end
        -- Strings/numbers only: do not retain the manager or any pawn object.
        quit_bridge = cached_quit_bridge
    else
        quit_bridge = nil
    end
    armed, xp_tracing = false, false
    finish_deadline, pending_export = 0, false
    record({phase = "suspended_for_quit"})
    suspended, suspension_mode = true, "manual"
    -- Export the last live state once, before quitting begins.
    export()
    target_manager, baseline, bridge_id, rental_scope = nil, nil, nil, nil
    bridge_enabled = false
    status = "SUSPENDED. Return to the main menu and quit. Restart DD2 before playing again."
end

re.on_script_reset(function()
    if not suspended then restore_count("script_reset") end
    target_manager, baseline, bridge_id, rental_scope = nil, nil, nil, nil
end)

-- The portrait cache has four slots, independent of the shared model pool and
-- its two display controllers. Extra pawn preloads can fill all four before
-- the Arisen is registered. Reserve the player's portrait using the game's
-- own cache methods. NEVER clear/reinitialize the shared model pool: portraits
-- and Item/Equipment screens retain references to its model records.
do
    local add_chara = signature("addChara", {"app.CharacterID"}, "System.Void", "app.MockupFace")
    local remove_chara = signature("removeChara", {"app.CharacterID"}, "System.Void", "app.MockupFace")
    local reserving = false
    local function reserve_arisen(face)
        if reserving or suspended or not face then return end
        local gui = sdk.get_managed_singleton("app.GuiManager")
        if not same(face, field(gui, "MenuFace")) then return end
        local manager = sdk.get_managed_singleton("app.PawnManager")
        local ids = saved_ids(manager)
        if not ids or #ids <= 3 then return end
        local cm = sdk.get_managed_singleton("app.CharacterManager")
        local player = field(cm, "<ManualPlayer>k__BackingField")
        local player_id = u32(player and player:call("get_CharaID"))
        local entries = field(face, "DataList")
        if not player_id or not entries or count(entries) ~= 4 then return end
        local extra_id_to_remove
        for i = 0, 3 do
            local entry = entries:get_element(i)
            if not entry then return end
            local cid = u32(field(entry, "CharaId"))
            if cid == player_id then return end
            for j = 4, #ids do
                if cid == ids[j] then extra_id_to_remove = cid end
            end
        end
        reserving = true
        local ok, err = pcall(function()
            if extra_id_to_remove then remove_chara:call(face, extra_id_to_remove) end
            add_chara:call(face, player_id)
        end)
        reserving = false
        if not ok then error(err) end
        for i = 0, 3 do
            if u32(field(entries:get_element(i), "CharaId")) == player_id then
                menu_mockup_fix.repairs = menu_mockup_fix.repairs + 1
                return
            end
        end
        -- The cache may still be in initialize(); retry on its next request.
    end
    local function guarded_reserve(face)
        local ok, err = pcall(reserve_arisen, face)
        if not ok then menu_mockup_fix.last_error = tostring(err) end
    end
    if add_chara and remove_chara then
        local ok, err = pcall(function()
            sdk.hook(add_chara, function(args)
                guarded_reserve(receiver(args))
            end, function(retval) return retval end)
        end)
        menu_mockup_fix.ready = ok
        if not ok then menu_mockup_fix.last_error = tostring(err) end
    else
        menu_mockup_fix.last_error = "portrait cache method signature unavailable"
    end
    if not menu_mockup_fix.ready then
        warnings[#warnings + 1] = "Arisen portrait reservation unavailable: " .. tostring(menu_mockup_fix.last_error)
    end
    function menu_mockup_fix.repair()
        if not menu_mockup_fix.ready or lifecycle_frame < menu_mockup_fix.next_check_frame then return end
        menu_mockup_fix.next_check_frame = lifecycle_frame + 120
        local gui = safe(function() return sdk.get_managed_singleton("app.GuiManager") end)
        guarded_reserve(field(gui, "MenuFace"))
    end
end

-- The vocation guild creates a two-character panel but reads the active party
-- during setup. With five pawns that first visit can fail before its normal
-- character selection is established. Present the native three-pawn view only
-- while setupChara runs, then restore all authoritative values immediately.
do
    local function install_vocation_first_visit_repair()
        local setup_chara = assert(signature("setupChara", {}, "System.Void", "app.ui040101_00"),
            "vocation setupChara signature unavailable")
        local function restore(state)
            if not state then return end
            local ok = pcall(function()
                state.live:set_field("_size", state.live_size)
                state.saved:set_field("_size", state.saved_size)
                state.manager:set_field(SUB, state.sub_count)
                assert(count(state.live) == state.live_size and count(state.saved) == state.saved_size,
                    "vocation party sizes did not restore")
                assert(int(field(state.manager, SUB)) == state.sub_count,
                    "vocation hired-pawn count did not restore")
            end)
            if not ok then
                -- The original values are retained only for this synchronous
                -- setup call; best-effort restoration keeps a failed repair
                -- from leaving the party in its temporary view.
                safe(function() state.live:set_field("_size", state.live_size) end)
                safe(function() state.saved:set_field("_size", state.saved_size) end)
                safe(function() state.manager:set_field(SUB, state.sub_count) end)
            end
        end
        sdk.hook(setup_chara, function()
            local storage = thread.get_hook_storage()
            storage.mp_vocation_party_view = nil
            if suspended then return end
            local manager = safe(function() return sdk.get_managed_singleton("app.PawnManager") end)
            local live, saved = field(manager, "_PartyPawnList"), field(manager, "_SavedPartyPawnList")
            local live_size, saved_size, sub_count = count(live), count(saved), int(field(manager, SUB))
            if live_size ~= 5 or saved_size ~= 5 or sub_count ~= 4 then return end
            local state = {manager = manager, live = live, saved = saved, live_size = live_size,
                saved_size = saved_size, sub_count = sub_count}
            local ok = pcall(function()
                live:set_field("_size", 3)
                saved:set_field("_size", 3)
                manager:set_field(SUB, 2)
                assert(count(live) == 3 and count(saved) == 3 and int(field(manager, SUB)) == 2,
                    "vocation temporary party view verification failed")
            end)
            if ok then
                storage.mp_vocation_party_view = state
            else
                restore(state)
            end
        end, function(retval)
            local storage = thread.get_hook_storage()
            restore(storage.mp_vocation_party_view)
            storage.mp_vocation_party_view = nil
            return retval
        end)
    end
    pcall(install_vocation_first_visit_repair)
end

-- Checkout-only repair. No game code bytes, party lists, counts, gold, or
-- inventory records are changed. The native row ctor and payment logic run.
do
    local contexts = {} -- thread ID -> nested setupCheckOut context
    -- Counters are used only to limit internal repair work; never exported.
    local trace = {constructor_entries = 0, constructor_returns = 0}
    local function checkpoint(phase, detail)
        -- Compatibility no-op: checkout repair keeps no diagnostic breadcrumbs.
    end
    local function row_checkpoint(ctx, phase, detail)
        -- Detailed allocation tracing is bounded to the first four rows of
        -- each checkout. Every setup entry/return and repair error is recorded.
        if ctx and ctx.rows <= 4 then checkpoint(phase, detail) end
    end
    local function unique(td, name, params, result)
        local chosen, n = nil, 0
        for _, m in ipairs(td and td:get_methods() or {}) do
            if m:get_name() == name and not m:is_static() and m:get_num_params() == #params
                and m:get_return_type():get_full_name() == result then
                local matched, types = true, m:get_param_types() or {}
                for i, p in ipairs(params) do
                    if not types[i] or types[i]:get_full_name() ~= p then matched = false end
                end
                if matched then chosen, n = m, n + 1 end
            end
        end
        if n == 1 then return chosen end
    end
    local function install_checkout()
        assert(game == "dd2" and tdb == 83 and not blocked, "DD2/TDB or base mod unavailable")
        assert(thread.get_id and sdk.create_managed_array, "thread ID/managed array API unavailable")
        local ui_td = assert(sdk.find_type_definition("app.ui040601_00"))
        local setup = assert(unique(ui_td, "setupCheckOut", {}, "System.Void"), "checkout signature unavailable")
        local setup_address = sdk.to_int64(setup:get_function())
        -- Follow the precise display-list call observed at setup RVA 0x73a3a06.
        -- The call target is RVA 0x764e770. These hooks observe original calls;
        -- they neither skip rendering nor create unbound sixth-column controls.
        local repair_visual
        local function install_display_trace()
            local observed, hooked = {}, {}
            checkout_repair.display_trace = {methods = observed, hooks = {}, binding_ready = false}
            local info = checkout_repair.display_trace
            local function observe(m, label)
                local address = sdk.to_int64(m:get_function())
                if hooked[address] then return end
                sdk.hook(m, function(args)
                    local st = thread.get_hook_storage()
                    local ctx = contexts[tostring(thread.get_id())]
                    st.mp_display_trace = ctx ~= nil and not suspended
                    if st.mp_display_trace and label == "app.GUIBase.CheckOutRef.ChkOutItem.setup(0)" then
                        st.mp_visual_row = receiver(args)
                        st.mp_visual_required = ctx.required
                    end
                    if st.mp_display_trace then checkpoint("display_call_enter", label) end
                end, function(retval)
                    local st = thread.get_hook_storage()
                    if st.mp_visual_row and repair_visual then
                        local ok, err = pcall(repair_visual, st.mp_visual_row, st.mp_visual_required)
                        if not ok then
                            checkout_repair.visual_error = tostring(err)
                            checkout_repair.visual_failures = (checkout_repair.visual_failures or 0) + 1
                            checkpoint("visual_repair_error", tostring(err))
                        end
                    end
                    if thread.get_hook_storage().mp_display_trace then
                        checkpoint("display_call_return", label)
                    end
                    return retval
                end)
                hooked[address] = true
                info.hooks[#info.hooks + 1] = label
            end
            local ref = assert(sdk.find_type_definition("app.GUIBase.CheckOutRef"))
            local ctrl_field = assert(ref:get_field("ListCtrl"), "checkout ListCtrl field unavailable")
            assert(not ctrl_field:is_static() and ctrl_field:get_offset_from_base() == 0x60,
                "checkout ListCtrl layout differs")
            local ctrl = ctrl_field:get_type()
            local binding, matches = nil, 0
            local visited, matched_addresses = {}, {}
            local current = ctrl
            for depth = 0, 15 do
                if not current then break end
                local owner = current:get_full_name()
                assert(not visited[owner], "cycle in display controller inheritance")
                visited[owner] = true
                for _, m in ipairs(current:get_methods() or {}) do
                    local address = sdk.to_int64(m:get_function())
                    local delta = address - setup_address
                    observed[#observed + 1] = {owner = owner, depth = depth, name = m:get_name(),
                        delta = delta, parameters = m:get_num_params(), result = m:get_return_type():get_full_name()}
                    if delta == 0x764e770 - 0x73a33a0 and not m:is_static()
                        and not matched_addresses[address] then
                        matched_addresses[address] = true
                        binding, matches = m, matches + 1
                        info.binding_owner = owner
                    end
                end
                current = current:get_parent_type()
                assert(depth < 15 or not current, "display controller inheritance exceeds diagnostic limit")
            end
            assert(matches == 1, "cannot uniquely resolve native checkout display-list call")
            observe(binding, ctrl:get_full_name() .. "." .. binding:get_name())
            info.binding_ready = true
            for _, name in ipairs({"app.GUIBase.CheckOutRef.ChkOutItem", "app.GUIBase.CheckOutRef.NumItem"}) do
                local td = sdk.find_type_definition(name)
                local count = 0
                for _, m in ipairs(td and td:get_methods() or {}) do
                    observed[#observed + 1] = {owner = name, name = m:get_name(),
                        delta = sdk.to_int64(m:get_function()) - setup_address,
                        parameters = m:get_num_params(), result = m:get_return_type():get_full_name()}
                    if not m:is_static() and m:get_name() ~= ".ctor"
                        and m:get_return_type():get_full_name() == "System.Void" and count < 16 then
                        observe(m, name .. "." .. m:get_name() .. "(" .. m:get_num_params() .. ")")
                        count = count + 1
                    end
                end
            end
        end
        -- REFramework's SystemArray numeric __newindex sets managed elements
        -- directly. System.Array.SetValue is not exposed by this game's TDB.
        local function set_value(array, value, index)
            assert(index >= 0 and index < array:get_size(), "checkout array index out of bounds")
            array[index] = value
            assert(same(array:get_element(index), value), "managed array index assignment/read-back failed")
        end
        -- Discover nested row names from reflected CheckOutRef fields and method
        -- signatures. Seed names are hints only; native address/layout checks
        -- below are mandatory and do not depend on those names being correct.
        local queue = {"app.GUIBase.CheckOutRef", "app.GUIBase.CheckOutRef.ListInfo", "app.GUIBase.CheckOutRef.ItemInfo"}
        local seen, index, found = {}, 1, {}
        local function enqueue(name)
            for token in (name or ""):gmatch("app%.GUIBase%.CheckOutRef[%w_%.]*") do
                if not seen[token] then queue[#queue + 1] = token end
            end
        end
        while index <= #queue and index <= 96 do
            local name = queue[index]; index = index + 1
            if not seen[name] then
                seen[name] = true
                local td = sdk.find_type_definition(name)
                if td then
                    local row = {type = name, fields = {}}
                    checkout_repair.discovery[#checkout_repair.discovery + 1] = row
                    for _, f in ipairs(td:get_fields() or {}) do
                        local ft = f:get_type():get_full_name()
                        enqueue(ft)
                        row.fields[#row.fields + 1] = {name = f:get_name(), type = ft,
                            offset = f:get_offset_from_base(), static = f:is_static()}
                    end
                    for _, m in ipairs(td:get_methods() or {}) do
                        enqueue(m:get_return_type():get_full_name())
                        for _, p in ipairs(m:get_param_types() or {}) do enqueue(p:get_full_name()) end
                    end
                    local ctor = unique(td, ".ctor", {}, "System.Void")
                    if ctor then
                        local delta = sdk.to_int64(ctor:get_function()) - setup_address
                        row.constructor_delta = delta
                        -- From inspected executable: setup RVA 0x73a33a0,
                        -- called row ctor RVA 0x87fcda0. ASLR cancels out.
                        if delta == 0x1459a00 then found[#found + 1] = {td = td, ctor = ctor} end
                    end
                end
            end
        end
        assert(#found == 1, "cannot uniquely resolve the inspected checkout row constructor")
        local row_td, ctor = found[1].td, found[1].ctor
        local array_field
        for _, f in ipairs(row_td:get_fields() or {}) do
            if not f:is_static() and f:get_offset_from_base() == 0x30
                and f:get_type():get_full_name():sub(-2) == "[]" then
                assert(not array_field, "ambiguous row array field")
                array_field = f
            end
        end
        assert(array_field, "row array at reflected offset 0x30 unavailable")
        local array_name = array_field:get_name()
        local element_name = array_field:get_type():get_full_name():sub(1, -3)
        local element_td = assert(sdk.find_type_definition(element_name), "row entry type unavailable")
        local slots, slot_count = {}, 0
        local expected = {[0x10] = "app.GUIBase.ShopGoodsInfo", [0x18] = "app.Character",
            [0x20] = "app.CharacterID", [0x24] = "System.Boolean"}
        for _, f in ipairs(element_td:get_fields() or {}) do
            if not f:is_static() then
                local offset = f:get_offset_from_base()
                assert(expected[offset] == f:get_type():get_full_name() and not slots[offset],
                    "checkout entry layout differs from inspected initialization")
                slots[offset], slot_count = f:get_name(), slot_count + 1
            end
        end
        assert(slot_count == 4, "checkout entry fields incomplete")
        checkout_repair.row_type = row_td:get_full_name()
        checkout_repair.array_field = array_name
        checkout_repair.entry_type = element_name
        checkout_repair.array_writer = "REFramework SystemArray numeric index assignment"
        -- Verify the installed SDK's writer on fresh objects before registering
        -- repair hooks. This never attaches a scratch object to game state.
        local scratch_array, scratch_entry
        local tested, test_error = pcall(function()
            scratch_array = assert(sdk.create_managed_array(element_name, 1), "scratch array allocation failed"):add_ref()
            scratch_entry = assert(sdk.create_instance(element_name), "scratch entry allocation failed"):add_ref()
            set_value(scratch_array, scratch_entry, 0)
        end)
        if scratch_array then safe(function() scratch_array:release() end) end
        if scratch_entry then safe(function() scratch_entry:release() end) end
        checkout_repair.array_writer_verified = tested
        assert(tested, test_error)
        local function expand(row, ctx)
            row_checkpoint(ctx, "row_read_begin")
            local original = assert(field(row, array_name), "row array absent after native constructor")
            local size = original:get_size()
            row_checkpoint(ctx, "row_size", size)
            if size >= ctx.required then return end
            assert(size == 5, "unexpected native checkout array length")
            local template = assert(original:get_element(0), "native entry template absent")
            -- The native ctor makes empty entries with invalid CharaID and true
            -- selection. Require those defaults before constructing new entries.
            assert(field(template, slots[0x10]) == nil and field(template, slots[0x18]) == nil
                and u32(field(template, slots[0x20])) == 0x6ebc2f00
                and field(template, slots[0x24]) == true, "native entry defaults differ")
            local created, replacement = {}, nil
            local function retain(o)
                assert(o, "checkout allocation failed")
                o:add_ref(); created[#created + 1] = o
                return o
            end
            local ok, err = pcall(function()
                row_checkpoint(ctx, "replacement_allocate_begin", ctx.required)
                replacement = retain(sdk.create_managed_array(element_name, ctx.required))
                row_checkpoint(ctx, "replacement_allocated", replacement:get_size())
                for i = 0, 4 do
                    local entry = assert(original:get_element(i), "native checkout entry missing")
                    set_value(replacement, entry, i)
                    assert(same(replacement:get_element(i), entry), "native entry identity copy failed")
                end
                row_checkpoint(ctx, "existing_entries_copied")
                for i = 5, ctx.required - 1 do
                    -- Native constructor initializes these four fields directly;
                    -- reproduce only its verified empty-entry initialization.
                    row_checkpoint(ctx, "extra_entry_allocate_begin", i)
                    local entry = retain(sdk.create_instance(element_name))
                    row_checkpoint(ctx, "extra_entry_allocated", i)
                    entry:set_field(slots[0x10], nil)
                    entry:set_field(slots[0x18], nil)
                    entry:set_field(slots[0x20], 0x6ebc2f00)
                    entry:set_field(slots[0x24], true)
                    assert(u32(field(entry, slots[0x20])) == 0x6ebc2f00
                        and field(entry, slots[0x24]) == true, "new entry initialization failed")
                    row_checkpoint(ctx, "extra_entry_initialized", i)
                    set_value(replacement, entry, i)
                    assert(same(replacement:get_element(i), entry), "new entry assignment failed")
                    row_checkpoint(ctx, "extra_entry_attached", i)
                end
                assert(replacement:get_size() == ctx.required, "replacement size verification failed")
                row_checkpoint(ctx, "row_assignment_begin")
                row:set_field(array_name, replacement)
                assert(same(field(row, array_name), replacement), "row array assignment failed")
                row_checkpoint(ctx, "row_assignment_verified")
            end)
            if not ok and replacement and same(field(row, array_name), replacement) then
                safe(function() row:set_field(array_name, original) end)
            end
            row_checkpoint(ctx, "temporary_refs_release_begin")
            for i = #created, 1, -1 do safe(function() created[i]:release() end) end
            row_checkpoint(ctx, "temporary_refs_released")
            assert(ok, err)
            checkout_repair.rows_expanded = checkout_repair.rows_expanded + 1
            checkout_repair.last_size = ctx.required
            ctx.expanded = ctx.expanded + 1
            row_checkpoint(ctx, "row_expansion_complete", ctx.required)
        end
        sdk.hook(ctor, function(args)
            local st = thread.get_hook_storage()
            local ctx = contexts[tostring(thread.get_id())]
            trace.constructor_entries = trace.constructor_entries + 1
            st.mp_checkout_row, st.mp_checkout_ctx = nil, nil
            if not suspended and ctx then
                ctx.rows = ctx.rows + 1
                row_checkpoint(ctx, "constructor_enter", ctx.rows)
                if ctx.rows > 4 then checkpoint("later_constructor_enter", ctx.rows) end
                st.mp_checkout_row = receiver(args); st.mp_checkout_ctx = ctx
                row_checkpoint(ctx, "constructor_receiver", st.mp_checkout_row ~= nil)
            elseif trace.constructor_entries <= 4 then
                checkpoint("constructor_without_active_scope", suspended)
            end
        end, function(retval)
            local st = thread.get_hook_storage()
            trace.constructor_returns = trace.constructor_returns + 1
            row_checkpoint(st.mp_checkout_ctx, "constructor_return", st.mp_checkout_row ~= nil)
            if st.mp_checkout_ctx and st.mp_checkout_ctx.rows > 4 then
                checkpoint("later_constructor_return", st.mp_checkout_ctx.rows)
            end
            if st.mp_checkout_ctx and not st.mp_checkout_row then
                checkout_repair.failures = checkout_repair.failures + 1
                checkout_repair.last_error = "constructor receiver conversion failed"
                checkpoint("repair_error", checkout_repair.last_error)
            end
            if st.mp_checkout_row and st.mp_checkout_ctx then
                local ok, err = pcall(expand, st.mp_checkout_row, st.mp_checkout_ctx)
                if ok and st.mp_checkout_ctx.rows > 4 then
                    checkpoint("later_row_processed", st.mp_checkout_ctx.rows)
                end
                if not ok then
                    checkout_repair.failures = checkout_repair.failures + 1
                    checkout_repair.last_error = tostring(err)
                    checkpoint("repair_error", tostring(err))
                end
            end
            return retval
        end)
        sdk.hook(setup, function(args)
            checkpoint("setup_enter")
            local st = thread.get_hook_storage()
            local key = tostring(thread.get_id())
            st.mp_checkout_thread, st.mp_checkout_outer = key, contexts[key]
            contexts[key] = nil
            if suspended then return end
            local ui = receiver(args)
            local chars = field(ui, "CharaList")
            local n = chars and safe(function() return chars:get_size() end)
            if not n or n <= 5 then return end
            if n > 7 then
                checkout_repair.last_error = "checkout has more than seven recipients; unsupported"
                export(); return
            end
            -- CharaList is terminated by a CharaId 0xffff marker on the
            -- six-character path. It is a list sentinel, not a checkout
            -- recipient. Keep the native list untouched, but derive our row
            -- and visual repair size from actual character entries only.
            local required = n
            local tail = chars:get_element(n - 1)
            local tail_id = tail and u32(field(tail, "CharaId"))
            if tail_id == 0xffff then required = n - 1 end
            if required <= 5 then return end
            if required > 6 then
                checkout_repair.last_error = "checkout has more than six character recipients; unsupported"
                export(); return
            end
            local identities, seen_ids = {}, {}
            for i = 0, required - 1 do
                local entry = chars:get_element(i)
                local cid = u32(field(entry, "CharaId"))
                if not cid or cid == 0xffff or seen_ids[cid] then
                    checkout_repair.last_error = "checkout recipient identities are missing/duplicated"
                    export(); return
                end
                seen_ids[cid], identities[#identities + 1] = true, cid
            end
            contexts[key] = {required = required, expanded = 0, rows = 0}
            checkpoint("setup_scope_ready", required)
            checkout_repair.entries = checkout_repair.entries + 1
            checkout_repair.last_recipients = identities
            record({phase = "checkout_enter", recipients = identities})
            export()
            checkpoint("setup_native_begin", required)
        end, function(retval)
            checkpoint("setup_native_return")
            local st = thread.get_hook_storage()
            local key = st.mp_checkout_thread
            local ctx = key and contexts[key]
            -- Multi-item sales can construct further ChkOutItem rows after
            -- setupCheckOut returns. Keep this checkout's primitive context
            -- alive so those late rows receive the same six-recipient array
            -- repair. The next setupCheckOut entry replaces it; a nested outer
            -- context is still restored exactly as before.
            if key and st.mp_checkout_outer then contexts[key] = st.mp_checkout_outer end
            if ctx then
                checkout_repair.returns = checkout_repair.returns + 1
                record({phase = "checkout_return", expanded_rows = ctx.expanded})
                export()
            end
            return retval
        end)
        -- Native ChkOutItem.setup binds these five references from NumItem:
        -- visual offsets 30,20,28,38,40 <- grid-item offsets 38,40,48,50,18.
        -- Reuse a distinct, already constructed sixth grid item after setup.
        local function offset_field(td, offset, expected_type)
            local found, seen = nil, {}
            while td do
                local name = td:get_full_name()
                assert(not seen[name], "cyclic visual type ancestry")
                seen[name] = true
                for _, f in ipairs(td:get_fields() or {}) do
                    if not f:is_static() and f:get_offset_from_base() == offset then
                        assert(f:get_type():get_full_name() == expected_type, "visual field type differs at " .. offset .. ": " .. name .. "." .. f:get_name() .. " is " .. f:get_type():get_full_name() .. "; expected " .. expected_type)
                        assert(not found or found:get_name() == f:get_name(), "ambiguous visual field")
                        found = f
                    end
                end
                td = td:get_parent_type()
            end
            return assert(found, "visual field unavailable at " .. offset)
        end
        local function visual_install()
            local name = "app.GUIBase.CheckOutRef.ChkOutItem"
            local td = assert(sdk.find_type_definition(name))
            local setup_visual = assert(unique(td, "setup", {}, "System.Void"))
            assert(sdk.to_int64(setup_visual:get_function()) - setup_address == 0x85b1110 - 0x73a33a0,
                "visual setup address differs")
            local element = "app.GUIBase.CheckOutRef.ChkOutItemSub"
            local visual_array = offset_field(td, 0x58, element .. "[]")
            local grid_field = assert(td:get_field("NumGridCtrl"))
            assert(grid_field:get_offset_from_base() == 0x60, "number grid field differs")
            local grid_td = grid_field:get_type()
            -- Capture actual inherited layouts before imposing the candidate's
            -- assumptions. This is startup metadata only: no game instances read.
            checkout_repair.visual_schema = {}
            local function describe(start)
                local current, seen = start, {}
                for depth = 0, 15 do
                    if not current then return end
                    local owner = current:get_full_name()
                    if seen[owner] then return end
                    seen[owner] = true
                    local row = {owner = owner, depth = depth, fields = {}}
                    checkout_repair.visual_schema[#checkout_repair.visual_schema + 1] = row
                    for _, f in ipairs(current:get_fields() or {}) do
                        row.fields[#row.fields + 1] = {name = f:get_name(),
                            type = f:get_type():get_full_name(), offset = f:get_offset_from_base(),
                            static = f:is_static()}
                    end
                    current = current:get_parent_type()
                end
            end
            describe(grid_td)
            describe(td)
            describe(sdk.find_type_definition(element))
            describe(sdk.find_type_definition("app.GUIBase.CheckOutRef.NumItem"))

            local num_name = "app.GUIBase.CheckOutRef.NumItem"
            local grid_items = offset_field(grid_td, 0x20, num_name .. "[]")
            local grid_limit = offset_field(grid_td, 0x98, "System.UInt32")
            assert(grid_limit:get_name() == "DispNum", "grid display-count field name differs")
            local slot_td, num_td = sdk.find_type_definition(element), sdk.find_type_definition(num_name)
            local mappings = {}
            for _, spec in ipairs({{0x30,0x38,"app.GUIBase.NumInputRef"},
                {0x20,0x40,"via.gui.Panel"}, {0x28,0x48,"via.gui.Panel"},
                {0x38,0x50,"via.gui.Text"}, {0x40,0x18,"via.gui.Rect"}}) do
                mappings[#mappings + 1] = {target = offset_field(slot_td, spec[1], spec[3]),
                    source = offset_field(num_td, spec[2], spec[3])}
            end
            checkout_repair.visual_ready = true
            repair_visual = function(row, required)
                if required <= 5 then return end
                assert(required == 6, "visual candidate currently supports six checkout recipients")
                local original = assert(visual_array:get_data(row))
                if original:get_size() >= required then return end
                assert(original:get_size() == 5, "unexpected visual array length")
                local grid = assert(grid_field:get_data(row))
                local items = assert(grid_items:get_data(grid))
                assert(items:get_size() >= required, "sixth native number-grid item unavailable")
                local old_limit = grid_limit:get_data(grid)
                assert(old_limit == 5 or old_limit == required, "unexpected number-grid limit")
                -- Verify ordered native binding for all existing entries first.
                for i = 0, 4 do
                    local slot, item = assert(original:get_element(i)), assert(items:get_element(i))
                    for _, map in ipairs(mappings) do
                        local a, b = map.target:get_data(slot), map.source:get_data(item)
                        assert((a == nil and b == nil) or same(a,b), "native grid/visual ordering differs")
                    end
                end
                local sixth = assert(items:get_element(5))
                local values = {}
                for j, map in ipairs(mappings) do
                    values[j] = assert(map.source:get_data(sixth), "sixth control is unbound")
                    for i = 0, 4 do
                        assert(not same(values[j], map.source:get_data(items:get_element(i))),
                            "sixth control aliases an existing recipient")
                    end
                end
                checkpoint("visual_controls_verified", required)
                local replacement, extra
                local ok, err = pcall(function()
                    replacement = assert(sdk.create_managed_array(element, required)):add_ref()
                    extra = assert(sdk.create_instance(element)):add_ref()
                    for j, map in ipairs(mappings) do extra:set_field(map.target:get_name(), values[j]) end
                    for i = 0, 4 do set_value(replacement, original:get_element(i), i) end
                    set_value(replacement, extra, 5)
                    for j, map in ipairs(mappings) do
                        assert(same(map.target:get_data(extra), values[j]), "sixth binding read-back failed")
                    end
                    row:set_field(visual_array:get_name(), replacement)
                    assert(same(visual_array:get_data(row), replacement), "visual array attachment failed")
                    grid:set_field(grid_limit:get_name(), required)
                    assert(grid_limit:get_data(grid) == required, "number grid limit write failed")
                end)
                if not ok then
                    safe(function() grid:set_field(grid_limit:get_name(), old_limit) end)
                    if replacement and same(visual_array:get_data(row), replacement) then
                        safe(function() row:set_field(visual_array:get_name(), original) end)
                    end
                end
                if extra then safe(function() extra:release() end) end
                if replacement then safe(function() replacement:release() end) end
                assert(ok, err)
                checkout_repair.visual_rows = (checkout_repair.visual_rows or 0) + 1
                checkpoint("visual_binding_complete", required)
            end
            -- Production binding hook: this is the one native setup call that
            -- owns the checkout visual row.  It binds the sixth row after its
            -- native setup without collecting display traces or probing other
            -- UI methods.
            sdk.hook(setup_visual, function(args)
                local storage = thread.get_hook_storage()
                local context = contexts[tostring(thread.get_id())]
                storage.mp_checkout_visual_row = context and receiver(args) or nil
                storage.mp_checkout_visual_required = context and context.required or nil
            end, function(retval)
                local storage = thread.get_hook_storage()
                local row, required = storage.mp_checkout_visual_row, storage.mp_checkout_visual_required
                storage.mp_checkout_visual_row, storage.mp_checkout_visual_required = nil, nil
                if row and required and repair_visual then
                    local ok, err = pcall(repair_visual, row, required)
                    if not ok then
                        checkout_repair.visual_error = tostring(err)
                        checkout_repair.visual_failures = (checkout_repair.visual_failures or 0) + 1
                    end
                end
                return retval
            end)
        end
        local visual_ok, visual_error = pcall(visual_install)
        if not visual_ok then checkout_repair.visual_error = tostring(visual_error) end
        checkout_repair.ready = true
        if PRODUCTION_TELEMETRY then
            local display_ok, display_error = pcall(install_display_trace)
            if not display_ok then
                checkout_repair.display_trace_error = tostring(display_error)
                checkpoint("display_trace_unavailable", tostring(display_error))
            end
        end
        checkout_repair.trace_file = nil
        checkpoint("hooks_registered")
    end
    local ok, err = pcall(install_checkout)
    if not ok then
        checkout_repair.last_error = tostring(err)
        warnings[#warnings + 1] = "Checkout repair unavailable; do not attempt expanded-party purchases. Export report."
    end
    export()
end

-- Preserve V3's reproduced null-controller crash guard. Portrait registration
-- is repaired independently; the shared model pool must remain game-owned.
do
    local function install_equipment_exit_guard()
        assert(game == "dd2" and tdb == 83, "DD2/TDB unavailable")
        local ui = assert(sdk.find_type_definition("app.ui060401_00"))
        local mockup = assert(ui:get_field("CompMockup"), "CompMockup field unavailable")
        local request = assert(ui:get_field("RequestModel"), "RequestModel field unavailable")
        assert(not mockup:is_static() and mockup:get_type():get_full_name() == "app.MockupCtrl",
            "CompMockup layout differs")
        assert(not request:is_static() and request:get_type():get_full_name() == "System.Boolean",
            "RequestModel layout differs")
        local flow = assert(signature("updateFlow", {}, "System.Void", "app.ui060401_00"),
            "updateFlow signature unavailable")
        sdk.hook(flow, function(args)
            local ui_instance = safe(function() return sdk.to_managed_object(args[2]) end)
            if not ui_instance then return end
            local controller = safe(function() return mockup:get_data(ui_instance) end)
            local pending = safe(function() return request:get_data(ui_instance) end)
            if controller == nil and pending == true then
                ui_instance:set_field(request:get_name(), false)
                local cleared = safe(function() return request:get_data(ui_instance) end)
                assert(cleared == false, "Equipment RequestModel write verification failed")
                equipment_exit_guard.prevented = equipment_exit_guard.prevented + 1
                equipment_exit_guard.last_reason = "orphaned_request"
                equipment_exit_guard.last_time = now()
                export()
            else
                equipment_exit_guard.observed_normal = equipment_exit_guard.observed_normal + 1
            end
        end, function(retval) return retval end)
        equipment_exit_guard.ready = true
    end
    local ok, err = pcall(install_equipment_exit_guard)
    if not ok then
        equipment_exit_guard.last_error = tostring(err)
        warnings[#warnings + 1] = "Equipment exit guard unavailable: " .. tostring(err)
    end
    export()
end

-- Preserve the original inventory null-controller guard. A missing portrait
-- cache entry is not evidence that this crash guard caused the missing model.
do
    local function one_method(td, name, params, result)
        local chosen, matches = nil, 0
        for _, method in ipairs(td and td:get_methods() or {}) do
            if method:get_name() == name and not method:is_static()
                and method:get_num_params() == #params
                and method:get_return_type():get_full_name() == result then
                local valid, actual = true, method:get_param_types() or {}
                for i, expected in ipairs(params) do
                    if not actual[i] or actual[i]:get_full_name() ~= expected then valid = false end
                end
                if valid then chosen, matches = method, matches + 1 end
            end
        end
        if matches == 1 then return chosen end
    end
    local function install_inventory_exit_guard()
        assert(game == "dd2" and tdb == 83, "DD2/TDB unavailable")
        local ui = assert(sdk.find_type_definition("app.ui060301_00"))
        local mockup = assert(ui:get_field("CompMockup"), "CompMockup field unavailable")
        local request = assert(ui:get_field("RequestModel"), "RequestModel field unavailable")
        assert(not mockup:is_static() and mockup:get_offset_from_base() == 0x160
            and mockup:get_type():get_full_name() == "app.MockupCtrl", "CompMockup layout differs")
        assert(not request:is_static() and request:get_offset_from_base() == 0x3c9
            and request:get_type():get_full_name() == "System.Boolean", "RequestModel layout differs")
        local flow = assert(one_method(ui, "updateFlow", {}, "System.Void"), "updateFlow signature unavailable")
        sdk.hook(flow, function(args)
            local ui_instance = safe(function() return sdk.to_managed_object(args[2]) end)
            if not ui_instance then return end
            local controller = safe(function() return mockup:get_data(ui_instance) end)
            local pending = safe(function() return request:get_data(ui_instance) end)
            if controller == nil and pending == true then
                -- The request has no controller that can consume it. Clearing it
                -- skips only the known null dereference; transfer data is not read.
                ui_instance:set_field(request:get_name(), false)
                local cleared = safe(function() return request:get_data(ui_instance) end)
                assert(cleared == false, "RequestModel write verification failed")
                inventory_exit_guard.prevented = inventory_exit_guard.prevented + 1
                inventory_exit_guard.last_reason = "orphaned_request"
                inventory_exit_guard.last_time = now()
                export()
            else
                inventory_exit_guard.observed_normal = inventory_exit_guard.observed_normal + 1
            end
        end, function(retval) return retval end)
        inventory_exit_guard.ready = true
    end
    local ok, err = pcall(install_inventory_exit_guard)
    if not ok then
        inventory_exit_guard.last_error = tostring(err)
        warnings[#warnings + 1] = "Inventory exit guard unavailable: " .. tostring(err)
    end
    export()
end

-- Floating pawn-label accessibility controls. These use the confirmed live
-- world-label controller (app.ui022601): TxtName is the pawn name and
-- PnlJobIcon is the vocation crest. HpGauge is deliberately never read or
-- changed. Settings persist independently of gameplay state.
do
    local SETTINGS_FILE = "MorePawns_world_label_settings.json"
    local label_settings = json.load_file(SETTINGS_FILE) or {}
    label_settings.name_scale = tonumber(label_settings.name_scale) or 1.0
    label_settings.hide_crest = label_settings.hide_crest == true
    local label_originals = {}
    local label_pending_gauge = nil
    local function label_id(object)
        return safe(function() return tostring(object:get_address()) end) or tostring(object)
    end
    local function label_field(object, name)
        local direct = object and safe(function() return object:get_field(name) end)
        if direct ~= nil then return direct end
        local current = object and safe(function() return object:get_type_definition() end)
        while current do
            local f = safe(function() return current:get_field(name) end)
            local value = f and not safe(function() return f:is_static() end) and safe(function() return f:get_data(object) end)
            if value ~= nil then return value end
            current = safe(function() return current:get_parent_type() end)
        end
    end
    local function get_component(value, names)
        for _, name in ipairs(names) do
            local number = safe(function() return value:get_field(name) end)
            if type(number) == "number" then return number, name end
            number = safe(function() return value[name] end)
            if type(number) == "number" then return number, name end
        end
    end
    local function set_component(value, names, number)
        for _, name in ipairs(names) do
            if pcall(function() value:set_field(name, number) end) then return true end
            if pcall(function() value[name] = number end) then return true end
        end
        return false
    end
    local function apply_name(text)
        local size = safe(function() return text:call("get_FontSize") end)
        if not size then return end
        local width, width_name = get_component(size, {"w", "x", "Width"})
        local height, height_name = get_component(size, {"h", "y", "Height"})
        if not width or not height then return end
        local key = label_id(text)
        if not label_originals[key] then label_originals[key] = {width = width, height = height} end
        local original = label_originals[key]
        if set_component(size, {width_name}, original.width * label_settings.name_scale)
            and set_component(size, {height_name}, original.height * label_settings.name_scale) then
            pcall(function() text:call("set_FontSize", size) end)
        end
    end
    local function apply_crest(panel)
        pcall(function() panel:call("set_Visible", not label_settings.hide_crest) end)
    end
    local function apply_label(gauge)
        if not gauge then return end
        local text, crest = label_field(gauge, "TxtName"), label_field(gauge, "PnlJobIcon")
        if text then apply_name(text) end
        if crest then apply_crest(crest) end
    end
    local gauge_type = safe(function() return sdk.find_type_definition("app.ui022601") end)
    local gauge_update = gauge_type and signature("update", {}, "System.Void", "app.ui022601")
    if gauge_update then
        pcall(function()
            sdk.hook(gauge_update, function(args)
                label_pending_gauge = sdk.to_managed_object(args[2])
            end, function(retval)
                local gauge = label_pending_gauge
                label_pending_gauge = nil
                pcall(apply_label, gauge)
                return retval
            end)
        end)
    end
    re.on_draw_ui(function()
        if not imgui.tree_node("More Pawns V4") then return end
        if not suspended then
            local p = party()
            imgui.text("Party: Arisen + " .. tostring(p.party_count or 0) .. " Pawns (Hired: "
                .. tostring(p.sub_count or 0) .. ")")
        else
            imgui.text("Party controls are temporarily suspended during loading.")
        end
        imgui.separator()
        imgui.text("Formation slots: " .. (formation_fix.ready and "5 active" or "awaiting five-pawn formation"))
        if formation_fix.last_error then imgui.text("Formation warning: " .. formation_fix.last_error) end
        imgui.text("Arisen portrait reservation: " .. (menu_mockup_fix.ready and "hook active" or "unavailable"))
        imgui.text("Portrait reservations: " .. tostring(menu_mockup_fix.repairs))
        if menu_mockup_fix.last_error then imgui.text("Menu warning: " .. menu_mockup_fix.last_error) end
        imgui.separator()
        imgui.text("Pawn Labels")
        local changed, value = imgui.slider_float("Pawn name scale", label_settings.name_scale, 0.50, 1.00, "%.2fx")
        if changed then label_settings.name_scale = value; json.dump_file(SETTINGS_FILE, label_settings) end
        changed, value = imgui.checkbox("Hide pawn crest", label_settings.hide_crest)
        if changed then label_settings.hide_crest = value; json.dump_file(SETTINGS_FILE, label_settings) end
        if imgui.button("Reset label sizes") then
            label_settings.name_scale, label_settings.hide_crest = 1.0, false
            json.dump_file(SETTINGS_FILE, label_settings)
        end
        imgui.tree_pop()
    end)
end
