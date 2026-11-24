local modname = "ThePawnController"
local SLOT_IDS = {0, 1, 2}
local SLOT_NAMES = {[0] = "Main Pawn", [1] = "Hired Pawn 1", [2] = "Hired Pawn 2"}
local function slot_label(i) return SLOT_NAMES[i] or ("Slot " .. tostring(i)) end
local version = "2.2.0"
local TAG = "[ThePawnController] "

local configFile = modname .. "\\config.json"
local presetFile = modname .. "\\presets.json"
local legacyConfigFile = "HiredPawnEquipmentOverride\\HiredPawnEquipmentOverride.json"

local function Log(msg) log.info(TAG .. tostring(msg)) end

local SLOTS = {'Main', 'Sub', 'Head', 'Upper', 'Lower', 'Mantle', 'Jewelry_00', 'Jewelry_01', 'Visual'}
local ENHANCE_SLOTS = {'Main', 'Sub', 'Head', 'Upper', 'Lower', 'Mantle'}
local UI = {CHANGED = 0xFF66E6FF}
function UI.cb(label, value, default)
    local hl = (value == true) ~= (default == true)
    if hl then imgui.push_style_color(0, UI.CHANGED) end
    local c, v = imgui.checkbox(label, value)
    if hl then imgui.pop_style_color(1) end
    return c, v
end
function UI.slider(label, value, lo, hi, fmt, default)
    local hl = math.abs((value or default) - default) > 0.001
    if hl then imgui.push_style_color(0, UI.CHANGED) end
    local c, v = imgui.slider_float(label, value, lo, hi, fmt)
    if hl then imgui.pop_style_color(1) end
    return c, v
end
function UI.islider(label, value, lo, hi, default)
    local hl = default ~= nil and value ~= default
    if hl then imgui.push_style_color(0, UI.CHANGED) end
    local c, v = imgui.slider_int(label, value, lo, hi)
    if hl then imgui.pop_style_color(1) end
    return c, v
end
local SlotEnum = {Main = 0, Sub = 1, Head = 2, Upper = 3, Lower = 4, Mantle = 5, Jewelry_00 = 6, Jewelry_01 = 7, Visual = 8}
local SKILL_SLOTS = 6
local ABILITY_SLOTS = 7
local MAX_ENHANCE = 4

local function default_pawn_config()
    local c = {
        enabled = false,
        equipment = {}, enhance = {},
        job = 0, job_rank = 0, level = 0, skills = {}, abilities = {}, core = {},
        personality = 0, specialization = -1, voice_gender = 0, voice_tone = -1,
        plague_immune = false, name = "", chatter = 1,
        qol = {godmode = false, inf_stamina = false, cannot_die = false, instant_revive = false, damage_mult = 1.0,
            light_load = false, lantern = false, scale = 1.0, return_after_rest = false},
        knowledge = {quest = 0, way = 0, shortcut = 0, gimmick = 0}
    }
    for _, s in ipairs(SLOTS) do c.equipment[s] = 0 end
    for _, s in ipairs(ENHANCE_SLOTS) do c.enhance[s] = {enabled = false, steps = {0, 0, 0}, dragon = false} end
    c.eq_skills = {}
    for _, s in ipairs(ENHANCE_SLOTS) do c.eq_skills[s] = {enabled = false, ids = {0, 0, 0, 0}} end
    for i = 1, SKILL_SLOTS do c.skills[i] = 0 end
    for i = 1, ABILITY_SLOTS do c.abilities[i] = 0 end
    return c
end

local function fill_defaults(dst, defaults)
    for k, v in pairs(defaults) do
        if dst[k] == nil then
            dst[k] = type(v) == "table" and fill_defaults({}, v) or v
        elseif type(v) == "table" and type(dst[k]) == "table" then
            fill_defaults(dst[k], v)
        end
    end
    return dst
end

local function deep_copy(t)
    if type(t) ~= "table" then return t end
    local r = {}
    for k, v in pairs(t) do r[k] = deep_copy(v) end
    return r
end

local function migrate_pawn(p)
    if p.personality == nil then p.personality = 0 end
    if p.specialization == nil then p.specialization = -1 end
    if type(p.core) ~= "table" then p.core = {} end
    if type(p.skills) ~= "table" then p.skills = {} end
    for n = 1, SKILL_SLOTS do if p.skills[n] == nil then p.skills[n] = 0 end end
    if type(p.abilities) ~= "table" then p.abilities = {} end
    for n = 1, ABILITY_SLOTS do if p.abilities[n] == nil then p.abilities[n] = 0 end end
    if p.voice_gender == nil then p.voice_gender = 0 end
    if p.voice_tone == nil then p.voice_tone = -1 end
    if p.voice_tone == 6 then p.voice_tone = 0 end
    p.max_skill_level = nil
    p.learned_only = nil
    p.appearance = nil
    p.made = nil
    if type(p.qol) == "table" and p.qol.no_down ~= nil then
        p.qol.cannot_die = p.qol.no_down
        p.qol.instant_revive = p.qol.no_down
        p.qol.no_down = nil
    end
    if type(p.enhance) == "table" then
        for s, v in pairs(p.enhance) do
            if type(v) == "number" then
                local steps = {0, 0, 0}
                for n = 1, math.min(v, 3) do steps[n] = 1 end
                p.enhance[s] = {enabled = v > 0, steps = steps, dragon = v >= 4}
            end
        end
    end
    return fill_defaults(p, default_pawn_config())
end

local cfg = json.load_file(configFile)
local config_changed = false
local imported_legacy = false
if cfg == nil then
    cfg = json.load_file("HiredPawnControl\\config.json")
    if cfg then Log("Imported settings from Hired Pawn Control") config_changed = true imported_legacy = true end
end
if cfg == nil then
    cfg = {}
    local legacy = json.load_file(legacyConfigFile)
    if legacy then
        cfg.pawn1, cfg.pawn2, cfg.debug = legacy.pawn1, legacy.pawn2, legacy.debug
        Log("Imported settings from Hired Pawn Equipment Override")
        config_changed = true
        imported_legacy = true
    end
end
cfg.pawn0 = migrate_pawn(cfg.pawn0 or {})
cfg.pawn1 = migrate_pawn(cfg.pawn1 or {})
cfg.pawn2 = migrate_pawn(cfg.pawn2 or {})
if imported_legacy then
    for _, k in ipairs({"pawn1", "pawn2"}) do
        if cfg[k].enabled and not cfg[k].owner then cfg[k].preconfigured = true end
    end
end
cfg.debug = fill_defaults(cfg.debug or {}, {
    enable_startup_logs = false, enable_search_logs = false,
    enable_equipment_logs = false, enable_attribute_logs = false
})
local MAX_PAWN_JOB = 6
cfg.show_arisen_jobs = nil
if cfg.show_all_items == nil then cfg.show_all_items = false end
if cfg.allow_empty_slots == nil then cfg.allow_empty_slots = false end
if cfg.player_qol and cfg.player_qol.no_down ~= nil then cfg.player_qol.cannot_die = cfg.player_qol.no_down cfg.player_qol.no_down = nil end
cfg.player_qol = fill_defaults(cfg.player_qol or {}, {godmode = false, inf_stamina = false, cannot_die = false,
    damage_mult = 1.0, light_load = false, lantern = false, scale = 1.0})
cfg.original_names = nil
cfg.player_gear = type(cfg.player_gear) == "table" and cfg.player_gear or {}
cfg.player_gear.orig = type(cfg.player_gear.orig) == "table" and cfg.player_gear.orig or {}
cfg.player_gear.odata = type(cfg.player_gear.odata) == "table" and cfg.player_gear.odata or {}
-- removed from public release: main pawn stats
cfg.originals = cfg.originals or {}
for _, k in ipairs({"pawn0", "pawn1", "pawn2"}) do
    if cfg[k].job > MAX_PAWN_JOB then cfg[k].job = 0 config_changed = true end
end

local presets = json.load_file(presetFile) or json.load_file("HiredPawnControl\\presets.json") or {}
for _, p in pairs(presets) do
    if type(p) == "table" and (p.job or 0) > MAX_PAWN_JOB then p.job = 0 end
end

local function save_config()
    json.dump_file(configFile, cfg)
    config_changed = false
end
local function save_presets() json.dump_file(presetFile, presets) end

local function DebugLog(cat, msg)
    local d = cfg.debug
    if (cat == "startup" and d.enable_startup_logs) or (cat == "search" and d.enable_search_logs)
        or (cat == "equipment" and d.enable_equipment_logs) or (cat == "attribute" and d.enable_attribute_logs) then
        Log("[DEBUG-" .. cat:upper() .. "] " .. tostring(msg))
    end
end

local PawnManager = sdk.get_managed_singleton('app.PawnManager')
local ItemManager = sdk.get_managed_singleton('app.ItemManager')
local GUIBase = sdk.find_type_definition("app.GUIBase")
local MessageType = sdk.find_type_definition("via.gui.message")
local EnhanceParamType = sdk.find_type_definition("app.ItemDefine.EnhanceParam")
local GetItemOptionType = sdk.find_type_definition("app.ItemDefine.GetItemOption")

local function method(td, sig) return td and td:get_method(sig) or nil end
local msgGet = method(MessageType, "get(System.Guid)")

local function clean_text(s)
    if type(s) ~= "string" or s == "" or s:find("Rejected", 1, true) then return nil end
    s = s:gsub("<[^>]->", ""):gsub("^%s+", ""):gsub("%s+$", "")
    return s ~= "" and s or nil
end

local function msg_text(guid_method, id)
    if not (guid_method and msgGet) then return nil end
    local ok, s = pcall(function() return msgGet:call(nil, guid_method:call(nil, id)) end)
    return ok and clean_text(s) or nil
end

local function str_text(str_method, ...)
    if not str_method then return nil end
    local args = {...}
    local ok, s = pcall(function() return str_method:call(nil, table.unpack(args)) end)
    return ok and clean_text(s) or nil
end

local function enum_values(type_name, unsigned)
    local out = {}
    local td = sdk.find_type_definition(type_name)
    if not td then Log("Enum type not found: " .. type_name) return out end
    for _, f in ipairs(td:get_fields()) do
        if f:is_static() then
            local ok, v = pcall(f.get_data, f, nil)
            if ok and type(v) == "number" then
                if unsigned and v < 0 then v = v + 4294967296 end
                table.insert(out, {name = f:get_name(), id = v})
            end
        end
    end
    table.sort(out, function(a, b) return a.id < b.id end)
    return out
end

local function split_camel(s)
    return (s:gsub("(%l)(%u)", "%1 %2"):gsub("(%u)(%u%l)", "%1 %2"))
end

local Lists = {jobs = {}, personality = {}, spec = {}, gender = {}, tone = {}, skills = {}, abilities = {}, core = {}}
local SkillJob = {}

do
local JobFallback = {"Fighter", "Archer", "Mage", "Thief", "Warrior", "Sorcerer",
    "Mystic Spearhand", "Magick Archer", "Trickster", "Warfarer"}
local PersonalityFallback = {Kind = "Kindhearted", Cool = "Calm", Simple = "Simple", Frank = "Straightforward"}
local SpecFallback = {[0] = "None", "Woodland Wordsmith", "Chirurgeon", "Logistician", "Hawker", "Forager", "Aphonite"}


for _, e in ipairs(enum_values("app.Character.JobEnum")) do
    if e.id > 0 then table.insert(Lists.jobs, {id = e.id, name = JobFallback[e.id] or e.name}) end
end
for _, e in ipairs(enum_values("app.PersonalityDefine.PersonalityID", true)) do
    if e.id ~= 0 then table.insert(Lists.personality, {id = e.id, name = PersonalityFallback[e.name] or e.name}) end
end
for _, e in ipairs(enum_values("app.PawnDefine.SubSkillID")) do
    table.insert(Lists.spec, {id = e.id, name = SpecFallback[e.id] or ("Specialization " .. e.id)})
end
for _, e in ipairs(enum_values("app.Gender", true)) do
    if e.id ~= 0 then table.insert(Lists.gender, {id = e.id, name = e.name}) end
end
for _, e in ipairs(enum_values("app.SoundVoiceManager.VoiceToneType")) do
    table.insert(Lists.tone, {id = e.id, name = e.name})
end
for _, e in ipairs(enum_values("app.HumanCustomSkillID")) do
    local job, rest = e.name:match("^Job(%d%d)_(.+)$")
    if job and e.id > 0 then
        job = tonumber(job)
        local name = split_camel(rest)
        SkillJob[e.id] = job
        table.insert(Lists.skills, {id = e.id, name = name, job = job})
    end
end
for _, e in ipairs(enum_values("app.HumanNormalSkillID")) do
    local job, rest = e.name:match("^Job(%d%d)_(.+)$")
    if job then table.insert(Lists.core, {id = e.id, name = split_camel(rest), job = tonumber(job)}) end
end
for _, e in ipairs(enum_values("app.HumanAbilityID")) do
    if e.id > 0 and not e.name:find("^Dummy") then
        local job, n = e.name:match("^Job(%d%d)_(%d%d)$")
        local label = job and ((JobFallback[tonumber(job)] or ("Job " .. job)) .. " augment " .. (tonumber(n) + 1)) or e.name
        table.insert(Lists.abilities, {id = e.id, name = label, job = job and tonumber(job) or 0})
    end
end
Log(string.format("Loaded %d jobs, %d personalities, %d specializations, %d skills, %d augments",
    #Lists.jobs, #Lists.personality, #Lists.spec, #Lists.skills, #Lists.abilities))

end

local function name_of(list, id)
    for _, it in ipairs(list) do if it.id == id then return it.name end end
    return nil
end

local names_state = {done = false, tries = 0, v = 0}
local function resolve_names()
    if names_state.done then return end
    names_state.tries = names_state.tries + 1
    if names_state.tries > 600 then names_state.done = true return end

    local jobMsg = method(GUIBase, "getJobNameMsgID(app.Character.JobEnum)")
    local persMsg = method(GUIBase, "getPersonalityMsgId(app.PersonalityDefine.PersonalityID)")
    local specMsg = method(GUIBase, "getSubSkillMsgId(app.PawnDefine.SubSkillID)")
    local skillName = method(GUIBase, "getCustomSkillName(app.HumanCustomSkillID, app.HumanCustomSkillLevelNo)")
    local abilityName = method(GUIBase, "getAbilityName(app.HumanAbilityID)")
    local coreName = method(GUIBase, "getNormalSkillName(app.HumanNormalSkillID)")

    local resolved = 0
    local function upgrade(list, fn, keep_suffix)
        for _, it in ipairs(list) do
            local n = fn(it.id)
            if n then
                it.name = n
                it.lname = nil
                resolved = resolved + 1
            end
        end
    end
    upgrade(Lists.jobs, function(id) return msg_text(jobMsg, id) end)
    upgrade(Lists.personality, function(id) return msg_text(persMsg, id) end)
    upgrade(Lists.spec, function(id) return id ~= 0 and msg_text(specMsg, id) or nil end)
    local skillNameJob = method(GUIBase, "getCustomSkillName(app.Character.JobEnum, app.HumanCustomSkillID, app.HumanCustomSkillLevelNo)")
    local GuiMgr = sdk.get_managed_singleton("app.GuiManager")
    local gmSkillMsg = GuiMgr and method(GuiMgr:get_type_definition(),
        "getCustomSkillName(app.HumanCustomSkillID, app.HumanCustomSkillLevelNo)")
    local function skill_text(id)
        for _, lv in ipairs({1, 0, 2}) do
            local n = str_text(skillName, id, lv)
                or (SkillJob[id] and str_text(skillNameJob, SkillJob[id], id, lv))
            if not n and gmSkillMsg and msgGet then
                local ok, s = pcall(function() return msgGet:call(nil, gmSkillMsg:call(GuiMgr, id, lv)) end)
                n = ok and clean_text(s) or nil
            end
            if n then return n end
        end
        return nil
    end
    local before = resolved
    upgrade(Lists.skills, skill_text, true)
    Log("Skill names resolved: " .. (resolved - before) .. "/" .. #Lists.skills)
    upgrade(Lists.abilities, function(id) return str_text(abilityName, id) end)
    upgrade(Lists.core, function(id) return str_text(coreName, id) end)

    if resolved > 0 then
        names_state.done = true
        names_state.v = names_state.v + 1
        for _, l in ipairs({Lists.skills, Lists.abilities}) do
            table.sort(l, function(a, b) return a.name < b.name end)
        end
        Log("Resolved " .. resolved .. " names from game text")
    end
end

local itemLists = {}
local items_live = false
local items_source = "none"
local build_live_items

do
local EquipCategoryToSlots = {
    [0] = {'Main'}, [1] = {'Sub'}, [2] = {'Head'}, [3] = {'Upper'}, [4] = {'Lower'},
    [5] = {'Mantle'}, [6] = {'Jewelry_00', 'Jewelry_01'}, [7] = {'Visual'}
}

local function reset_item_lists()
    itemLists = {}
    for _, s in ipairs(SLOTS) do itemLists[s] = {} end
end

local function sort_item_lists()
    for _, l in pairs(itemLists) do table.sort(l, function(a, b) return a.name < b.name end) end
end

local function load_item_json()
    local data = json.load_file(modname .. "\\itemData.json")
        or json.load_file("HiredPawnControl\\itemData.json")
        or json.load_file("HiredPawnEquipmentOverride\\itemData.json")
    if not data then return 0 end
    local cat_to_slots = {
        Weapon = {'Main'}, Shield = {'Sub'}, Head = {'Head'}, Chest = {'Upper'}, Legs = {'Lower'},
        Mantle = {'Mantle'}, Jewelry = {'Jewelry_00', 'Jewelry_01'}, Visual = {'Visual'}
    }
    reset_item_lists()
    local count = 0
    for id_str, item in pairs(data) do
        local id = tonumber(id_str)
        local slots = item.category and cat_to_slots[item.category]
        if id and item.name and slots then
            for _, s in ipairs(slots) do
                table.insert(itemLists[s], {id = id, name = item.name .. " (ID: " .. id .. ")"})
            end
            count = count + 1
        end
    end
    sort_item_lists()
    return count
end

local function add_live_item(param)
    if not param or not param:call("get_IsEquip") then return false end
    local id = param:call("get_Id")
    local name = clean_text(param:call("get_Name"))
    local ep = param:call("get_EquipParam")
    if not (id and name and ep) then return false end
    local slots = EquipCategoryToSlots[ep:call("get_EquipCategory")]
    if not slots then return false end
    local jobs, any = {}, false
    for j = 1, 10 do
        local ok, can = pcall(function() return ep:call("IsJob", 1 << j) end)
        if ok and can then jobs[j] = true any = true end
    end
    local entry = {id = id, name = name .. " (ID: " .. id .. ")", jobs = any and jobs or nil}
    for _, s in ipairs(slots) do table.insert(itemLists[s], entry) end
    return true
end

function build_live_items()
    if not ItemManager then return false end
    local dict = ItemManager._ItemDataDict
    if not dict or (dict:call("get_Count") or 0) == 0 then return false end
    reset_item_lists()
    local count = 0
    local ok = pcall(function()
        local entries = dict._entries or dict.entries
        for n = 0, entries:get_size() - 1 do
            local e = entries:get_element(n)
            local v = e and (e.value or e.Value)
            if v and add_live_item(v) then count = count + 1 end
        end
    end)
    if not ok or count == 0 then
        reset_item_lists()
        count = 0
        for id = 1, 32000 do
            local okp, param = pcall(function() return ItemManager:getItemData(id) end)
            if okp and param and add_live_item(param) then count = count + 1 end
        end
    end
    if count == 0 then return false end
    sort_item_lists()
    items_source = "game (" .. count .. " items)"
    Log("Built equipment lists live from game data: " .. count .. " items")
    return true
end

do
    local n = load_item_json()
    items_source = n > 0 and ("itemData.json (" .. n .. " items)") or "none"
    if n == 0 then reset_item_lists() end
end
end

local game_jobs = {}

local lazy_hooks = {}
local lazy_done = {}
local function need_hooks(name)
    if lazy_done[name] then return end
    lazy_done[name] = true
    local fn = lazy_hooks[name]
    local ok, n = pcall(function() return fn and fn() or 0 end)
    Log(ok and ("Hooks for " .. name .. " installed: " .. tostring(n)) or ("Hooks for " .. name .. " failed: " .. tostring(n)))
end

local frame_no = 0
local party_frame = -1
local party_cache = {}

local function get_hired_pawn(index)
    if not PawnManager then return nil end
    if party_frame ~= frame_no then
        party_frame = frame_no
        party_cache = {}
        local ok, mp = pcall(function() return PawnManager:call("get_MainPawn") end)
        party_cache[0] = ok and mp or nil
        pcall(function()
            local list = PawnManager:get_PartyPawnList()
            for n = 0, list:get_Count() - 1 do
                local pawn = list:get_Item(n)
                local id = pawn and tonumber(PawnManager:getPartyPawnID(pawn))
                if id and id > 0 and party_cache[id] == nil then
                    party_cache[id] = pawn
                    if id > (party_cache.max_id or 0) then party_cache.max_id = id end
                end
            end
        end)
    end
    return party_cache[index]
end

local function get_character(pawn) return pawn and pawn['<CachedCharacter>k__BackingField'] or nil end

local bound_cid = {}
local function bound_pawn(i)
    local pawn = get_hired_pawn(i)
    local c = get_character(pawn)
    if c and bound_cid[i] == c.CharacterID then return pawn end
    return nil
end

local function get_human(pawn)
    local h = pawn and pawn['<CachedHuman>k__BackingField']
    if h then return h end
    local c = get_character(pawn)
    return c and c:call("get_Human") or nil
end

local function is_ready(character)
    return character ~= nil and character:get_Valid() and character['<HumanPartSwapper>k__BackingField'] ~= nil
end

local function get_data_context(character)
    local ps = character and character['<HumanPartSwapper>k__BackingField']
    return ps and ps._PawnDataContext or nil
end

local function current_job(human)
    local ok, j = pcall(function() return human:call("get_JobContext"):call("get_Job") end)
    return ok and j or nil
end

local getItemWithOption = ItemManager and method(ItemManager:get_type_definition(),
    "getItem(System.Int32, System.Int32, app.Character, app.ItemDefine.GetItemOption)")
local getItemPlain = ItemManager and method(ItemManager:get_type_definition(),
    "getItem(System.Int32, System.Int32, app.Character)")
local getItemFailLogged = false

local function make_get_item_option()
    if not GetItemOptionType then return nil end
    local ok, opt = pcall(function()
        local f = GetItemOptionType:get_field("Default")
        local o = f and f:get_data(nil)
        if o == nil then o = ValueType.new(GetItemOptionType) end
        o:set_field("EventType", 1)
        o:set_field("IsNotice", false)
        o:set_field("IsNewMark", false)
        o:set_field("IsHistory", false)
        o:set_field("IsRecord", false)
        return o
    end)
    return ok and opt or nil
end

local function give_item(item_id, character)
    local ok, err = pcall(function()
        local opt = getItemWithOption and make_get_item_option()
        if opt then
            getItemWithOption:call(ItemManager, item_id, 1, character, opt)
        elseif getItemPlain then
            getItemPlain:call(ItemManager, item_id, 1, character)
        else
            error("no usable ItemManager.getItem overload")
        end
    end)
    if not ok and not getItemFailLogged then
        Log("getItem failed: " .. tostring(err))
        getItemFailLogged = true
    end
    return ok
end

local function get_slot_item(character, slot_enum)
    local equipData = ItemManager:getEquipData(character.CharacterID)
    return equipData and equipData:call('get(app.EquipData.SlotEnum)', slot_enum) or nil
end

local ENHANCE_STEP_NAMES = {"None", "Vernworth", "Battahl", "Elven"}
local filled_steps, apply_enhance, apply_equipment, relock_items
local PlayerGear = {dev = false}
pcall(function()
    for _, pat in ipairs({[[ThePawnController\\dev\.txt]], [[ThePawnController/dev\.txt]]}) do
        local ok, res = pcall(fs.glob, pat)
        if ok and type(res) == "table" and #res > 0 then PlayerGear.dev = true end
    end
end)

do

local function same_types(a, b, num)
    for n = 1, math.min(num or 0, 3) do
        if (a[n] or 0) ~= (b[n] or 0) then return false end
    end
    return true
end

local function wearable(character, item_id)
    local ok, can = pcall(function()
        local job = character:call("get_Human"):call("get_JobContext"):call("get_Job")
        return ItemManager:getItemData(item_id):call("get_EquipParam"):call("IsJob", 1 << job)
    end)
    return ok and can == true
end

local job_orig = {}
local function unlock_item(item_id)
    if job_orig[item_id] ~= nil then return end
    pcall(function()
        local p = ItemManager:getItemData(item_id)
        local j = p:get_field("_Job")
        if j ~= nil and j ~= 65535 then
            job_orig[item_id] = {p = p, j = j}
            Lists.item_job = Lists.item_job or {}
            if Lists.item_job[item_id] == nil then Lists.item_job[item_id] = j end
            p:set_field("_Job", 65535)
            Log("Item " .. item_id .. " can now be worn by any vocation")
        end
    end)
end

function relock_items()
    local n = 0
    for _, o in pairs(job_orig) do
        if pcall(function() o.p:set_field("_Job", o.j) end) then n = n + 1 end
    end
    job_orig = {}
    if n > 0 then Log("Put the vocation limits back on " .. n .. " item(s)") end
end
if re.on_script_reset then re.on_script_reset(relock_items) end

local function cid32(v) return math.tointeger(v) & 0xFFFFFFFF end

local session_made = {}
local give_failed = {}
local charaid_logged = false

local function key_of(character)
    local ok, k = pcall(function() return tostring(cid32(character.CharacterID)) .. "@" .. tostring(character:get_address()) end)
    return ok and k or nil
end

local function track_of(character)
    local k = key_of(character)
    if not k then return nil end
    session_made[k] = session_made[k] or {}
    return session_made[k]
end

local function entries_of(character, item_id)
    local out = {}
    local ok = pcall(function()
        local list = ItemManager:call("getStorageMasterList(app.CharacterID)", character.CharacterID)
        for n = 0, list:call("get_Count") - 1 do
            local m = list:call("get_Item", n)
            local sd = m and m._Param
            if sd and sd._ItemId == item_id then table.insert(out, sd) end
        end
    end)
    return out, ok
end

local function sid_of(sd)
    local ok, v = pcall(function() return sd:call("get_StorageId") end)
    return ok and v or nil
end

local function enh_of(sd)
    local ok, v = pcall(function() return sd:call("get_EnhanceNum") end)
    return ok and v or 0
end

local function new_entry(character, item_id, give)
    local before, ok1 = entries_of(character, item_id)
    if not ok1 then return nil end
    local seen = {}
    for _, sd in ipairs(before) do
        local s = sid_of(sd)
        if not s then return nil end
        seen[s] = true
    end
    if not give() then return nil end
    local after, ok2 = entries_of(character, item_id)
    if not ok2 then return nil end
    local found, fs
    for _, sd in ipairs(after) do
        local s = sid_of(sd)
        if s and not seen[s] then
            if found then return nil end
            found, fs = sd, s
        end
    end
    local one = false
    pcall(function() one = found and found._Num == 1 end)
    if one then return found, fs end
    return nil
end

local function remember(track, slot, sid, item_id, num, types)
    if not (track and sid) then return end
    track[slot] = track[slot] or {}
    table.insert(track[slot], {sid = sid, item = item_id, num = num, types = types})
end

local function worn_sids(character)
    local set = {}
    for _, s in ipairs(SLOTS) do
        pcall(function()
            local sd = get_slot_item(character, SlotEnum[s])
            local sid = sd and sd._ItemId ~= 0 and sid_of(sd)
            if sid then set[sid] = true end
        end)
    end
    return set
end

local function settle(character, track, slot, keep_sid)
    local recs = track and track[slot]
    if not recs then return end
    local worn = worn_sids(character)
    local left, removed = {}, 0
    for _, rec in ipairs(recs) do
        if rec.sid == keep_sid or worn[rec.sid] then
            table.insert(left, rec)
        else
            local okc, verdict, sd = pcall(function()
                local d = ItemManager:call("getStorageDataByStorageId", rec.sid)
                if not d or d._ItemId ~= rec.item or enh_of(d) ~= (rec.num or 0) then return "gone" end
                if rec.types then
                    local e = d._Enhance
                    if not same_types({e._Type0, e._Type1, e._Type2}, rec.types, rec.num or 0) then return "gone" end
                end
                if cid32(d._CharaId) ~= cid32(character.CharacterID) then
                    if not charaid_logged then
                        charaid_logged = true
                        Log("Cleanup skipped: storage entry belongs to character " .. tostring(cid32(d._CharaId))
                            .. ", this pawn is " .. tostring(cid32(character.CharacterID)))
                    end
                    return "foreign"
                end
                if d._IsEquipped then return "worn" end
                return "mine", d
            end)
            if okc and verdict == "mine" then
                pcall(function() ItemManager:call("deleteItem(app.ItemDefine.StorageData, System.Int32)", sd, 1) end)
                local okv, still = pcall(function()
                    local d = ItemManager:call("getStorageDataByStorageId", rec.sid)
                    return d ~= nil and d._ItemId == rec.item
                end)
                if okv and not still then removed = removed + 1 else table.insert(left, rec) end
            elseif okc and verdict == "worn" then
                table.insert(left, rec)
            end
        end
    end
    track[slot] = #left > 0 and left or nil
    if removed > 0 then Log("Cleaned up " .. removed .. " spare " .. slot .. " item(s) the mod had made") end
end

local pending_swap = {}
re.on_pre_application_entry("UpdateBehavior", function()
    if not next(pending_swap) then return end
    local now = os.clock()
    for k, p in pairs(pending_swap) do
        if now >= p.at then
            pending_swap[k] = nil
            pcall(function()
                local ps = p.chara["<HumanPartSwapper>k__BackingField"]
                if ps:call("get_EquipmentBeingSwapping") and p.tries < 10 then
                    pending_swap[k] = {chara = p.chara, at = now + 0.3, tries = p.tries + 1, second = p.second}
                    return
                end
                ps:call("swap()")
                if not p.second then pending_swap[k] = {chara = p.chara, at = now + 0.7, tries = 0, second = true} end
            end)
        end
    end
end)

local function equip(character, sd, slot_name, item_id, num)
    local slot_enum = SlotEnum[slot_name]
    local can = true
    pcall(function() can = sd:call("canEquip", character.CharacterID, false) end)
    pcall(function()
        sd._IsEquipped = false
        sd._IsNew = false
    end)
    local ok, err = pcall(function() ItemManager:setEquip(sd, character, slot_enum, true, true) end)
    local now = get_slot_item(character, slot_enum)
    local landed = now and now._ItemId == item_id and (num == nil or enh_of(now) == num)
    if landed and slot_enum >= 0 and slot_enum <= 5 then
        pcall(function()
            local prm = ItemManager:getItemData(item_id)
            ItemManager:call("setEquipModel(app.ItemCommonParam, app.ItemCommonParam, System.Boolean, System.Boolean, app.Character, System.Boolean, System.Boolean)",
                prm, prm, false, false, character, false, false)
        end)
        if slot_enum >= 2 then
            pcall(function() pending_swap[character:get_address()] = {chara = character, at = os.clock() + 0.3, tries = 0} end)
        end
    end
    if not landed then
        Log("Couldn't equip item " .. item_id .. " in " .. slot_name .. (can and "" or " (the game says this vocation can't wear it)")
            .. (ok and "" or (": " .. tostring(err))))
    end
    return landed, now
end

function apply_equipment(character, equipment)
    local track = track_of(character)
    local success = true
    for _, slot_name in ipairs(SLOTS) do
        local item_id = equipment[slot_name] or 0
        if item_id > 0 then
            local current = get_slot_item(character, SlotEnum[slot_name])
            if (current and current._ItemId or 0) ~= item_id then
                if not ItemManager:getItemData(item_id) then
                    Log("Invalid item ID: " .. item_id)
                    success = false
                else
                    if cfg.force_equip and not wearable(character, item_id) then unlock_item(item_id) end
                    local pick, made
                    local worn = worn_sids(character)
                    for _, sd in ipairs(entries_of(character, item_id)) do
                        if not sd._IsEquipped and not worn[sid_of(sd) or -1] then pick = sd break end
                    end
                    if not pick then
                        local fk = tostring(key_of(character)) .. ":" .. slot_name .. ":" .. item_id .. ":0"
                        if not give_failed[fk] then
                            pick, made = new_entry(character, item_id, function() return give_item(item_id, character) end)
                            if made then
                                remember(track, slot_name, made, item_id, 0)
                            else
                                give_failed[fk] = true
                                Log("Couldn't add item " .. item_id .. " for " .. slot_name .. " (full bag?), not retrying until scripts reset")
                            end
                        end
                    end
                    if pick then
                        local landed, now = equip(character, pick, slot_name, item_id, nil)
                        if landed then
                            DebugLog("equipment", "Equipped " .. item_id .. " to " .. slot_name)
                            settle(character, track, slot_name, sid_of(now))
                        else
                            settle(character, track, slot_name, sid_of(pick))
                            success = false
                        end
                    else
                        success = false
                    end
                end
            end
        end
    end
    return success
end

function filled_steps(ecfg)
    local k = 0
    for n = 1, 3 do
        if (ecfg.steps[n] or 0) > 0 then k = n else break end
    end
    return k
end

local function build_enhance(ecfg, cur_num, cur_types)
    local k = filled_steps(ecfg)
    if k > 0 then
        local types = {}
        for n = 1, 3 do types[n] = n <= k and (ecfg.steps[n] - 1) or 0 end
        return (ecfg.dragon and k == 3) and 4 or k, types
    elseif ecfg.dragon and cur_num >= 3 then
        return 4, cur_types
    elseif ecfg.exact then
        return 0, {0, 0, 0}
    end
    return nil
end

local function find_storage_copy(character, item_id, num, types)
    local found
    for _, sd in ipairs(entries_of(character, item_id)) do
        if enh_of(sd) == num then
            local e = sd._Enhance
            if same_types({e._Type0, e._Type1, e._Type2}, types, num) then
                if not found or not sd._IsEquipped then found = sd end
            end
        end
    end
    return found
end

function apply_enhance(character, enhance, equipment)
    if not (EnhanceParamType and GetItemOptionType) then return end
    local track = track_of(character)
    for _, slot_name in ipairs(ENHANCE_SLOTS) do
        local ecfg = enhance[slot_name]
        if type(ecfg) == "table" and ecfg.enabled then
            local ok, err = pcall(function()
                local slot_enum = SlotEnum[slot_name]
                local sd = get_slot_item(character, slot_enum)
                local item_id = (equipment[slot_name] or 0) > 0 and equipment[slot_name] or (sd and sd._ItemId or 0)
                if item_id == 0 then return end
                local cur = sd and sd._Enhance
                local cur_num = (sd and sd._ItemId == item_id) and enh_of(sd) or 0
                local cur_types = cur and {cur._Type0, cur._Type1, cur._Type2} or {0, 0, 0}

                local num, types = build_enhance(ecfg, cur_num, cur_types)
                if not num then return end
                if sd and sd._ItemId == item_id and cur_num == num and same_types(cur_types, types, num) then return end

                local copy = find_storage_copy(character, item_id, num, types)
                local fresh = false
                local fk = tostring(key_of(character)) .. ":" .. slot_name .. ":" .. item_id .. ":" .. num
                if not copy and give_failed[fk] then return end
                if not copy then
                    local p = ValueType.new(EnhanceParamType)
                    p:call("set_Num", num)
                    p:call("set_Type0", types[1])
                    p:call("set_Type1", types[2])
                    p:call("set_Type2", types[3])
                    local ability = sd and sd._ItemId == item_id and sd._Ability
                        or sdk.find_type_definition("app.ItemDefine.EquipmentAbilityParam"):get_field("None"):get_data(nil)
                    local opt = make_get_item_option()
                    opt:call("setEquipmentOption", p, ability, 0)
                    local made
                    copy, made = new_entry(character, item_id, function()
                        return (pcall(function() getItemWithOption:call(ItemManager, item_id, 1, character, opt) end))
                    end)
                    if made then remember(track, slot_name, made, item_id, num, types) fresh = true end
                end
                if not copy then
                    give_failed[fk] = true
                    error("couldn't create the enhanced copy (full bag?), not retrying until scripts reset")
                end

                local landed, now = equip(character, copy, slot_name, item_id, num)
                settle(character, track, slot_name, landed and sid_of(now) or sid_of(copy))
                if landed then Log(string.format("Enhanced %s: put on %s item %d at +%d", slot_name, fresh and "a new copy of" or "an existing", item_id, num)) end
            end)
            if not ok then Log("Enhance failed on " .. slot_name .. ": " .. tostring(err)) end
        end
    end
end

local function plus_text(num)
    num = num or 0
    return num >= 4 and " +3 Dragonforged" or (num > 0 and (" +" .. num) or "")
end
PlayerGear.plus_text = plus_text

function PlayerGear.enhance(character, slot_name, ecfg, store, odata)
    local sd = get_slot_item(character, SlotEnum[slot_name])
    if not sd or sd._ItemId == 0 then return "Nothing equipped in " .. slot_name end
    local before = sid_of(sd)
    if not before then return "Couldn't read your " .. slot_name .. " item" end
    local track = track_of(character)
    local made_by_mod = false
    for _, r in ipairs(track and track[slot_name] or {}) do
        if r.sid == before then made_by_mod = true end
    end
    local o = store[slot_name]
    local keep = false
    if o and o.item == sd._ItemId then
        pcall(function()
            local d = ItemManager:call("getStorageDataByStorageId", o.sid)
            keep = d ~= nil and d._ItemId == o.item
        end)
    end
    if not keep and not made_by_mod then
        local nm
        pcall(function() nm = clean_text(ItemManager:getItemData(sd._ItemId):call("get_Name")) end)
        store[slot_name] = {sid = before, item = sd._ItemId, num = enh_of(sd), name = nm}
        save_config()
    end
    local prefix = tostring(key_of(character)) .. ":" .. slot_name .. ":"
    for k in pairs(give_failed) do
        if k:sub(1, #prefix) == prefix then give_failed[k] = nil end
    end
    apply_enhance(character, {[slot_name] = ecfg}, {})
    local now = get_slot_item(character, SlotEnum[slot_name])
    local after = now and now._ItemId ~= 0 and sid_of(now)
    if not after or after == before then
        return "Your " .. slot_name .. " didn't change (already like that, or the bag is full, see the log)"
    end
    if odata and odata.eq_written and odata.eq_sid then
        local ok_, nk = tostring(before), tostring(after)
        if odata.eq_written[ok_] and odata.eq_sid[ok_] and not odata.eq_written[nk] then
            local rec = deep_copy(odata.eq_sid[ok_])
            rec.sid, rec.first = after, nil
            odata.eq_sid[nk] = rec
            odata.eq_written[nk] = deep_copy(odata.eq_written[ok_])
            save_config()
        end
    end
    return "Your " .. slot_name .. " is now" .. (plus_text(enh_of(now)) ~= "" and plus_text(enh_of(now)) or " +0")
end

function PlayerGear.restore(character, slot_name, store)
    local o = store[slot_name]
    if not o then return nil end
    local d
    pcall(function() d = ItemManager:call("getStorageDataByStorageId", o.sid) end)
    if not d or d._ItemId ~= o.item then
        store[slot_name] = nil
        save_config()
        return "Your original " .. slot_name .. " item isn't in your storage any more"
    end
    local okc, mine = pcall(function() return cid32(d._CharaId) == cid32(character.CharacterID) end)
    if not (okc and mine) then
        return "Your original " .. slot_name .. " isn't in your own inventory right now (given to a pawn, or in storage?)"
    end
    if d._IsEquipped and not worn_sids(character)[o.sid] then
        return "Your original " .. slot_name .. " is being worn by someone else right now"
    end
    local landed = equip(character, d, slot_name, o.item, nil)
    if not landed then return "Couldn't put your original " .. slot_name .. " back on (see log)" end
    settle(character, track_of(character), slot_name, o.sid)
    store[slot_name] = nil
    save_config()
    return "Put your original " .. slot_name .. " back on"
end

end

local EqSkill = {}

do
local info = {loaded = false, list = {}, by_id = {}, rank = {}, appraisal = {}, max_slots = 4, from_game = false}
local ability_of
local none_id
local function get_none()
    if none_id == nil then
        none_id = 0
        for _, e in ipairs(enum_values("app.EquipmentAbilityID")) do
            if e.name == "None" then none_id = e.id end
        end
    end
    return none_id
end

local function num_of(v)
    if type(v) == "number" then return math.tointeger(v) or v end
    local ok, n = pcall(function() return v:get_field("value__") end)
    return ok and n or nil
end

local function arr_get(arr, n)
    local ok, v = pcall(function() return arr:call("Get", n) end)
    if ok and v ~= nil then return v end
    ok, v = pcall(function() return arr:get_element(n) end)
    return ok and v or nil
end

function EqSkill.load()
    if info.loaded and (info.from_game or os.clock() < (info.retry or 0)) then return info end
    local first = not info.loaded
    info.loaded = true
    info.retry = os.clock() + 5
    info.list, info.by_id, info.rank, info.appraisal = {}, {}, {}, {}
    info.pool_list = nil
    for _, e in ipairs(enum_values("app.EquipmentAbilityID")) do
        if e.id ~= get_none() and e.name ~= "None" and e.name ~= "Dummy" then
            local it = {id = e.id, base = (split_camel(e.name):gsub("_", " "))}
            table.insert(info.list, it)
            info.by_id[e.id] = it
        end
    end
    local rank_lv = {}
    for _, e in ipairs(enum_values("app.GUIAppraisalDefine.AppraiseSkillRank")) do
        local r = e.name:match("^Rank(%d)$")
        if r then rank_lv[e.id] = tonumber(r) + 1 end
    end
    pcall(function()
        local v = sdk.find_type_definition("app.PawnRentalValidator"):get_field("_MaxAbilitySlot"):get_data(nil)
        if type(v) == "number" and v > 0 then info.max_slots = math.min(v, 4) end
    end)
    pcall(function()
        local scene = sdk.call_native_func(sdk.get_native_singleton("via.SceneManager"), sdk.find_type_definition("via.SceneManager"), "get_CurrentScene()")
        local comps = scene:call("findComponents(System.Type)", sdk.typeof("app.GuiManagerBehavior"))
        local data = arr_get(comps, 0):get_field("EquipmentAbilityInfomationData")
        local params = data:get_field("_Params")
        for n = 0, params:get_size() - 1 do
            local p = arr_get(params, n)
            local it = p and info.by_id[num_of(p:get_field("_AbilityID"))]
            if it then
                pcall(function() it.game_name = clean_text(p:get_field("_NameMsgData"):call("getMessage()")) end)
                pcall(function() it.desc = clean_text(p:get_field("_DescriptionData"):call("getMessage()")) end)
                pcall(function() it.cost = p:get_field("_Cost") end)
                info.from_game = true
            end
        end
        local ranks = data:get_field("_RankParams")
        for n = 0, ranks:get_size() - 1 do
            local r = arr_get(ranks, n)
            local lv = rank_lv[num_of(r:get_field("_Rank"))]
            local ids = r:get_field("_IdList")
            for m = 0, ids:get_size() - 1 do
                local id = num_of(arr_get(ids, m))
                if id then
                    info.appraisal[id] = true
                    if lv and (not info.rank[id] or lv > info.rank[id]) then info.rank[id] = lv end
                end
            end
        end
    end)
    local seen = {}
    for _, it in ipairs(info.list) do
        it.name = (it.game_name or it.base) .. (info.rank[it.id] and (" (Lv" .. info.rank[it.id] .. ")") or "")
        seen[it.name] = (seen[it.name] or 0) + 1
    end
    for _, it in ipairs(info.list) do
        if seen[it.name] > 1 then it.name = it.name .. " [" .. it.base .. "]" end
        it.lname = nil
    end
    table.sort(info.list, function(a, b) return a.name < b.name end)
    info.version = (info.version or 0) + 1
    info.filtered = {}
    if first or info.from_game then
        Log("Special skills loaded: " .. #info.list .. (info.from_game and " with game names" or " (game names not ready yet, retrying)")
            .. ", max " .. info.max_slots .. " per item")
    end
    return info
end

local allowed_cache = {}
local appraisal_to_eq, appraisal_name
local result_map, result_retry = nil, 0

local function build_result_map(mgr)
    local map = {}
    local entries = mgr:get_field("ItemSettingDict"):get_field("_entries")
    for n = 0, entries:get_size() - 1 do
        pcall(function()
            local e = entries:get_element(n)
            local st = e and (e.value or e.Value)
            if not st then return end
            local atype = num_of(st:get_field("type"))
            local data = st:get_field("data")
            local level = num_of(data:get_field("levelType"))
            local fmt = num_of(data:get_field("formatType"))
            local fixed = {}
            pcall(function()
                local fx = data:get_field("SlotFixDatas")
                for m = 0, fx:get_size() - 1 do
                    local fd = arr_get(fx, m)
                    local aid = fd and num_of(fd:get_field("abilityID"))
                    if aid then table.insert(fixed, aid) end
                end
            end)
            local src_id = num_of(e.key or e.Key)
            local res = data:get_field("ResultItemDatas")
            for m = 0, res:get_size() - 1 do
                local r = arr_get(res, m)
                local rid = r and num_of(r:get_field("itemId"))
                if rid then
                    map[rid] = map[rid] or {}
                    table.insert(map[rid], {atype, level, fixed, src_id, fmt})
                end
            end
        end)
    end
    return map
end

local diag = {}
local ex_hit = {}
local function add_skills(mgr, atype, level, set)
    local bytype_all = mgr:get_field("AppraisalLevelSettingDict")
    if not bytype_all:call("ContainsKey", atype) then return end
    local bytype = bytype_all:call("get_Item", atype)
    local levels = {level}
    for _, e in ipairs(enum_values("app.AppraisalSetting.LevelType")) do
        if e.name == "All" and e.id ~= level then table.insert(levels, e.id) end
    end
    for _, lv in ipairs(levels) do
        if bytype:call("ContainsKey", lv) then
            local list = bytype:call("get_Item", lv):get_field("abilityDataList")
            for n = 0, list:call("get_Count") - 1 do
                local ads = list:call("get_Item", n):get_field("AbilityDatas")
                for m = 0, ads:call("get_Count") - 1 do
                    local ard = ads:call("get_Item", m)
                    local raw = num_of(ard:get_field("abilityID"))
                    local rate = ard:get_field("rate") or 0
                    local an = appraisal_name and appraisal_name[raw]
                    local ex = an and an:match("^ExSkill(%d)$")
                    if rate > 0 then
                        local eq = appraisal_to_eq[raw]
                        if eq then set[eq] = true end
                        if ex then ex_hit[tonumber(ex)] = (ex_hit[tonumber(ex)] or 0) + rate end
                    end
                    if not appraisal_to_eq[raw] and #diag < 40 then table.insert(diag, tostring(an or raw) .. " r" .. tostring(rate)) end
                end
            end
        end
    end
end

function EqSkill.allowed(item_id)
    if not item_id or item_id == 0 then return nil end
    local c = allowed_cache[item_id]
    if c ~= nil then return c or nil end
    local set
    pcall(function()
        if not appraisal_to_eq then
            local by_name = {}
            for _, e in ipairs(enum_values("app.EquipmentAbilityID")) do by_name[e.name] = e.id end
            appraisal_to_eq = {}
            appraisal_name = {}
            local alias = {BlowResistUp_S = "StrikeResistUp_S", BlowResistUp_L = "StrikeResistUp_L"}
            for _, e in ipairs(enum_values("app.AppraisalSetting.AppraisalAbilityID")) do
                appraisal_name[e.id] = e.name
                local target = by_name[e.name] or (alias[e.name] and by_name[alias[e.name]])
                if target then appraisal_to_eq[e.id] = target end
            end
        end
        local mgr = sdk.get_managed_singleton("app.ItemAppraisalManager")
        if (not result_map or not next(result_map)) and os.clock() >= result_retry then
            result_retry = os.clock() + 5
            local ok, map = pcall(build_result_map, mgr)
            if ok then result_map = map end
            if result_map and next(result_map) then
                local n = 0
                for _ in pairs(result_map) do n = n + 1 end
                Log("Appraisal tables mapped for " .. n .. " items")
            end
        end
        local sources = {}
        local items = mgr:get_field("ItemSettingDict")
        if items:call("ContainsKey", item_id) then
            local st = items:call("get_Item", item_id)
            table.insert(sources, {num_of(st:get_field("type")), num_of(st:get_field("data"):get_field("levelType"))})
        end
        for _, src in ipairs(result_map and result_map[item_id] or {}) do table.insert(sources, src) end
        set = {}
        diag = {}
        ex_hit = {}
        local fixed_names = {}
        local function add_fixed(aid)
            local eq = appraisal_to_eq[aid]
            if eq then set[eq] = true end
            table.insert(fixed_names, tostring(appraisal_name[aid] or aid))
        end
        local src_ids = {[item_id] = true}
        for _, src in ipairs(sources) do
            add_skills(mgr, src[1], src[2], set)
            for _, aid in ipairs(src[3] or {}) do add_fixed(aid) end
            if src[4] then src_ids[src[4]] = true end
        end
        pcall(function()
            local fentries = mgr:get_field("FixedItemSettingDict"):get_field("_entries")
            for n = 0, fentries:get_size() - 1 do
                pcall(function()
                    local fe = fentries:get_element(n)
                    local fs = fe and (fe.value or fe.Value)
                    if not fs then return end
                    local hit = src_ids[num_of(fe.key or fe.Key)]
                    if not hit then
                        local ids = fs:get_field("ItemIds")
                        for m = 0, ids:get_size() - 1 do
                            if src_ids[num_of(arr_get(ids, m))] then hit = true end
                        end
                    end
                    if hit then
                        local fl = fs:get_field("FixedSlotList")
                        for m = 0, fl:call("get_Count") - 1 do add_fixed(num_of(fl:call("get_Item", m):get_field("AbilityID"))) end
                    end
                end)
            end
        end)
        if next(ex_hit) then
            for id in pairs(info.appraisal) do set[id] = true end
        end
        local exs = {}
        for n, w in pairs(ex_hit) do table.insert(exs, "ExSkill" .. n .. " w" .. w) end
        local srcs = {}
        for _, src in ipairs(sources) do table.insert(srcs, tostring(src[1]) .. "/" .. tostring(src[2])) end
        local names = {}
        for id in pairs(set) do if #names < 25 then table.insert(names, EqSkill.name(id) .. "(" .. id .. ")") end end
        DebugLog("equipment", "[skills] item " .. item_id .. " sources(type/level) " .. table.concat(srcs, " ") .. " | unmapped " .. table.concat(diag, " ") .. " | ex pools: " .. table.concat(exs, " ") .. " | fixed: " .. table.concat(fixed_names, " "))
        DebugLog("equipment", "[skills] item " .. item_id .. " allowed: " .. table.concat(names, ", "))
        if not next(set) then set = nil end
    end)
    if set or (result_map and next(result_map)) then allowed_cache[item_id] = set or false end
    return set
end

EqSkill.STATS = {{"phys", "Physical"}, {"magic", "Magick"}, {"blow", "Knockdown"}, {"weight", "Weight (lower is lighter)"}}
EqSkill.row_cache = {}

function EqSkill.rows(item_id)
    if not item_id or item_id == 0 then return nil end
    local c = EqSkill.row_cache[item_id]
    if c ~= nil then return c or nil end
    EqSkill.allowed(item_id)
    if not (result_map and next(result_map)) then return nil end
    local rows, failed = {}, false
    local mask = Lists.item_job and Lists.item_job[item_id]
    if mask == nil then pcall(function() mask = ItemManager:call("getItemData(System.Int32)", item_id):get_field("_Job") or 0 end) end
    local m = math.tointeger(tonumber(mask) or 0) or 0
    local function int(v) return math.tointeger(math.floor((tonumber(v) or 0) + 0.5)) or 0 end
    local all
    if not pcall(function() all = sdk.get_managed_singleton("app.ItemAppraisalManager"):get_field("AppraisalLevelSettingDict") end) or not all then return nil end
    for _, src in ipairs(result_map[item_id] or {}) do
        local ok = pcall(function()
            local atype, level, fmt = src[1], src[2], src[5]
            if not (fmt and all:call("ContainsKey", atype)) then return end
            local bytype = all:call("get_Item", atype)
            if not bytype:call("ContainsKey", level) then return end
            local jl = bytype:call("get_Item", level):get_field("JobParamSettingList")
            for j = 0, jl:call("get_Count") - 1 do
                local jd = jl:call("get_Item", j)
                local job = num_of(jd:get_field("job"))
                if job and (m == 0 or (m & (1 << job)) ~= 0) then
                    local pl = jd:get_field("ParamLimitDataList")
                    for k = 0, pl:call("get_Count") - 1 do
                        local p = pl:call("get_Item", k)
                        if num_of(p:get_field("slotFormat")) == fmt then
                            local function r(f) local v = p:get_field(f) return {int(v.x), int(v.y)} end
                            table.insert(rows, {phys = r("physicalParamValue"), magic = r("magicParamValue"),
                                blow = r("blowParamValue"), weight = r("weightParamValue"), level = level, job = job})
                        end
                    end
                end
            end
        end)
        if not ok then failed = true end
    end
    if not failed then EqSkill.row_cache[item_id] = #rows > 0 and rows or false end
    return #rows > 0 and rows or nil
end

EqSkill.BONUS_NAMES = {[0] = "No bonus", [1] = "Boost special skill 1", [2] = "Boost special skill 2", [4] = "Boost special skill 3",
    [8] = "Boost special skill 4", [16] = "Fire element", [32] = "Ice element", [64] = "Thunder element", [128] = "Light element",
    [256] = "Physical bonus", [512] = "Magick bonus", [1024] = "Knockdown bonus", [2048] = "Slash resist bonus", [4096] = "Strike resist bonus"}
EqSkill.pool_cache = {}

function EqSkill.bonus_pool(item_id)
    if not item_id or item_id == 0 then return nil end
    local c = EqSkill.pool_cache[item_id]
    if c ~= nil then return c or nil end
    EqSkill.allowed(item_id)
    if not (result_map and next(result_map)) then return nil end
    local set, failed = {}, false
    local all
    if not pcall(function() all = sdk.get_managed_singleton("app.ItemAppraisalManager"):get_field("AppraisalLevelSettingDict") end) or not all then return nil end
    for _, src in ipairs(result_map[item_id] or {}) do
        local ok = pcall(function()
            if not all:call("ContainsKey", src[1]) then return end
            local bytype = all:call("get_Item", src[1])
            if not bytype:call("ContainsKey", src[2]) then return end
            local bl = bytype:call("get_Item", src[2]):get_field("BonusSettingList")
            for n = 0, bl:call("get_Count") - 1 do
                local bsd = bl:call("get_Item", n)
                if (bsd:get_field("Weight") or 0) > 0 then
                    if num_of(bsd:get_field("BonusType")) == 0 then set[1], set[2], set[4], set[8] = true, true, true, true end
                    for _, lname in ipairs({"ParamSettingList", "ElementSettingList"}) do
                        local l = bsd:get_field(lname)
                        for m = 0, l:call("get_Count") - 1 do
                            local p = l:call("get_Item", m)
                            local t = math.tointeger(num_of(p:get_field("type")) or 0) or 0
                            if (p:get_field("rate") or 0) > 0 then
                                for b = 0, 12 do if (t & (1 << b)) ~= 0 then set[1 << b] = true end end
                            end
                        end
                    end
                end
            end
        end)
        if not ok then failed = true end
    end
    local list = {}
    if next(set) then
        set[0] = true
        for id in pairs(set) do table.insert(list, {id = id, name = EqSkill.BONUS_NAMES[id] or ("bonus " .. id)}) end
        table.sort(list, function(a, b) return a.id < b.id end)
    end
    if not failed then EqSkill.pool_cache[item_id] = #list > 0 and list or false end
    return #list > 0 and list or nil
end

function EqSkill.bonus_ok(item_id, bonus)
    local pool = EqSkill.bonus_pool(item_id)
    if not pool or bonus == nil then return true end
    for _, b in ipairs(pool) do if b.id == bonus then return true end end
    return false
end

function EqSkill.limits(item_id, prefer_job)
    local best, score
    for _, row in ipairs(EqSkill.rows(item_id) or {}) do
        local s = row.level * 100000 + (row.job == prefer_job and 50000 or 0) + row.phys[2] + row.magic[2] + row.blow[2] - row.weight[1]
        if not score or s > score then best, score = row, s end
    end
    return best
end

function EqSkill.stats_fit(item_id, st)
    local rows = EqSkill.rows(item_id)
    if not rows or not st then return true end
    for _, row in ipairs(rows) do
        local ok = true
        for _, f in ipairs(EqSkill.STATS) do
            local v = st[f[1]] or 0
            if v < row[f[1]][1] or v > row[f[1]][2] then ok = false end
        end
        if ok then return true end
    end
    return false
end

function EqSkill.stats_of(sd)
    local ok, st = pcall(function()
        local a = sd._Ability
        return {phys = a.PhysicalParameter, magic = a.MagicParameter, blow = a.BlowParameter, weight = a.WeightParameter, bonus = num_of(a.Bonus) or 0}
    end)
    return ok and st or nil
end

function EqSkill.stat_ui(id, stats, lim, orig, pool, item)
    local changed = false
    local legit = item and EqSkill.stats_fit(item, stats)
    for _, f in ipairs(EqSkill.STATS) do
        local k, lo, hi = f[1], lim[f[1]][1], lim[f[1]][2]
        local v = math.tointeger(stats[k] or 0) or 0
        if legit then
            lo, hi = math.min(lo, v), math.max(hi, v)
        else
            v = math.max(lo, math.min(hi, v))
        end
        if v ~= stats[k] then stats[k] = v changed = true end
        if lo == hi then
            imgui.text(f[2] .. ": " .. lo .. " (fixed on this item)")
        else
            imgui.set_next_item_width(200)
            local c, nv = UI.islider(f[2] .. id .. k, v, lo, hi, orig and orig[k])
            if c then stats[k] = nv changed = true end
            imgui.same_line()
            imgui.text_colored((orig and ("Original: " .. tostring(orig[k]) .. ", ") or "") .. "range " .. lo .. " to " .. hi, 0xFF888888)
        end
    end
    if pool then
        local names, sel = {}, 1
        if stats.bonus == nil then stats.bonus = orig and orig.bonus or 0 end
        local found = false
        for n, b in ipairs(pool) do
            names[n] = b.name .. ((orig and orig.bonus == b.id) and " (original)" or "")
            if b.id == stats.bonus then sel = n found = true end
        end
        if not found then
            table.insert(names, (EqSkill.BONUS_NAMES[stats.bonus] or ("bonus " .. tostring(stats.bonus))) .. " (can't roll on this item)")
            sel = #names
        end
        local hl = orig and orig.bonus ~= nil and stats.bonus ~= orig.bonus
        if hl then imgui.push_style_color(0, UI.CHANGED) end
        imgui.set_next_item_width(200)
        local c, nv = imgui.combo("Bonus" .. id .. "bonus", sel, names)
        if hl then imgui.pop_style_color(1) end
        if c and pool[nv] then stats.bonus = pool[nv].id changed = true end
        local b = stats.bonus or 0
        local note = (b >= 1 and b <= 8) and "Upgrades the special skill in that slot to its bonus version (stronger effect, shorter cooldown)."
            or (b >= 16 and b <= 128) and "Adds the element and its buildup to the weapon."
            or (b >= 256) and "A flat boost to that stat on top of the roll." or nil
        if note then imgui.text_colored(note, 0xFF888888) end
    end
    if imgui.button("Best roll" .. id .. "best") then
        stats.phys, stats.magic, stats.blow, stats.weight = lim.phys[2], lim.magic[2], lim.blow[2], lim.weight[1]
        changed = true
    end
    if orig then
        imgui.same_line()
        if imgui.button("Original roll" .. id .. "orig") then
            for _, f in ipairs(EqSkill.STATS) do stats[f[1]] = orig[f[1]] end
            if orig.bonus ~= nil then stats.bonus = orig.bonus end
            changed = true
        end
    end
    local jn = "vocation " .. tostring(lim.job)
    pcall(function() jn = name_of(Lists.jobs, lim.job) or jn end)
    imgui.text_colored("Limits from the game's level " .. tostring(lim.level) .. " appraisal table for " .. jn .. ", so any roll here is one a real drop can get.", 0xFF888888)
    return changed
end

local cur_logged = {}
function EqSkill.debug_current(sd, slot_name)
    if not sd then return end
    local k = tostring(sd._ItemId) .. slot_name .. tostring(sd._StorageId)
    if cur_logged[k] then return end
    cur_logged[k] = true
    pcall(function()
        local _, ids = ability_of(sd)
        local set = EqSkill.allowed(sd._ItemId) or {}
        local parts = {}
        for _, id in ipairs(ids) do
            if id ~= 0 then table.insert(parts, EqSkill.name(id) .. "(" .. id .. " " .. tostring(info.by_id[id] and info.by_id[id].base) .. ") " .. (set[id] and "in set" or "NOT in set")) end
        end
        DebugLog("equipment", "[skills] " .. slot_name .. " item " .. sd._ItemId .. " current skills: " .. table.concat(parts, ", "))
    end)
end

function EqSkill.list_for(item_id)
    EqSkill.load()
    local set = EqSkill.allowed(item_id)
    if not set then
        if not next(info.appraisal) then return info.list, false end
        if not info.pool_list then
            info.pool_list = {}
            for _, it in ipairs(info.list) do if info.appraisal[it.id] then table.insert(info.pool_list, it) end end
        end
        return info.pool_list, false
    end
    local f = info.filtered[item_id]
    if not f then
        f = {}
        for _, it in ipairs(info.list) do if set[it.id] then table.insert(f, it) end end
        info.filtered[item_id] = f
    end
    return f, true
end

function EqSkill.name(id)
    local it = info.by_id[id]
    return it and (it.name or it.base) or ("skill " .. tostring(id))
end

function EqSkill.check(ids, is_main, item_id)
    EqSkill.load()
    local pool = EqSkill.allowed(item_id)
    local warns, filled, seen = {}, 0, {}
    for n = 1, 4 do
        local id = ids[n] or 0
        if id ~= 0 then
            filled = filled + 1
            if seen[id] then table.insert(warns, EqSkill.name(id) .. " is in there twice") end
            seen[id] = true
            if pool and not pool[id] then
                table.insert(warns, EqSkill.name(id) .. " can't roll on this item")
            elseif not pool and next(info.appraisal) and not info.appraisal[id] then
                table.insert(warns, EqSkill.name(id) .. " is not a skill appraisal can roll")
            end
        end
    end
    if filled > info.max_slots then table.insert(warns, "the game only allows " .. info.max_slots .. " skills per item") end
    return warns
end

function ability_of(sd)
    local a = sd._Ability
    local nid = get_none()
    local ids = {}
    for n, v in ipairs({a.Slot1, a.Slot2, a.Slot3, a.Slot4}) do
        local id = num_of(v) or 0
        ids[n] = (id == nid) and 0 or id
    end
    return a, ids
end

local function sid_of(sd)
    local ok, v = pcall(function() return sd:call("get_StorageId") end)
    return ok and v or nil
end

local function same_set(a, b)
    local x, y = {}, {}
    for n = 1, 4 do x[n] = a[n] or 0 y[n] = b[n] or 0 end
    table.sort(x) table.sort(y)
    for n = 1, 4 do if x[n] ~= y[n] then return false end end
    return true
end

function EqSkill.capture(sd, slot_name)
    local ok, rec = pcall(function()
        local a, ids = ability_of(sd)
        return {sid = sid_of(sd), slot = slot_name, item = sd._ItemId, ids = ids, phys = a.PhysicalParameter, magic = a.MagicParameter,
            blow = a.BlowParameter, weight = a.WeightParameter, bonus = num_of(a.Bonus) or 0, appraised = a.IsAppraised == true}
    end)
    return ok and rec and rec.sid and rec or nil
end

function EqSkill.snapshot(character)
    local out = {}
    for _, slot_name in ipairs(ENHANCE_SLOTS) do
        pcall(function()
            local sd = get_slot_item(character, SlotEnum[slot_name])
            if sd and sd._ItemId ~= 0 then
                local rec = EqSkill.capture(sd, slot_name)
                if rec then
                    rec.first = true
                    out[tostring(rec.sid)] = rec
                end
            end
        end)
    end
    return out
end

local function write(character, slot_name, sd, ids, rec, on_done, stats)
    local a = sd._Ability
    local st = rec and rec.phys ~= nil and rec or stats
    local function pick(k, cur) return st and st[k] ~= nil and st[k] or cur end
    a:call("setup(app.EquipmentAbilityID, app.EquipmentAbilityID, app.EquipmentAbilityID, app.EquipmentAbilityID, System.Int16, System.Int16, System.Int16, System.Int16, app.EquipmentAbilityBonus)",
        (ids[1] or 0) ~= 0 and ids[1] or get_none(), (ids[2] or 0) ~= 0 and ids[2] or get_none(),
        (ids[3] or 0) ~= 0 and ids[3] or get_none(), (ids[4] or 0) ~= 0 and ids[4] or get_none(),
        pick("phys", a.PhysicalParameter), pick("magic", a.MagicParameter), pick("blow", a.BlowParameter), pick("weight", a.WeightParameter),
        pick("bonus", num_of(a.Bonus) or 0))
    local appraised = true
    if rec then appraised = rec.appraised end
    pcall(function() a:set_field("IsAppraised", appraised) end)
    table.insert(game_jobs, function()
        ItemManager:call("updateEquipAbility(app.ItemDefine.StorageData, app.ItemDefine.EquipmentAbilityParam)", sd, a)
        local now = ItemManager:call("getStorageDataByStorageId", sid_of(sd))
        local _, got = ability_of(now)
        local s = EqSkill.stats_of(now) or {}
        Log(string.format("Special skills on %s %s: %s | stats P %s M %s B %s W %s bonus %s", slot_name, rec and "restored to" or "now", table.concat(got, ", "),
            tostring(s.phys), tostring(s.magic), tostring(s.blow), tostring(s.weight), tostring(s.bonus)))
        if on_done and same_set(got, ids) then on_done() end
    end)
end

local function stats_same(sd, stats)
    if not stats then return true end
    local s = EqSkill.stats_of(sd)
    if not s then return true end
    for _, f in ipairs(EqSkill.STATS) do
        if stats[f[1]] ~= nil and stats[f[1]] ~= s[f[1]] then return false end
    end
    if stats.bonus ~= nil and stats.bonus ~= s.bonus then return false end
    return true
end

function EqSkill.apply(character, eqs, equipment, odata)
    if not odata then return end
    for _, slot_name in ipairs(ENHANCE_SLOTS) do
        local c = eqs and eqs[slot_name]
        local use_ids = type(c) == "table" and c.enabled and type(c.ids) == "table"
        local use_stats = type(c) == "table" and c.stats_on and type(c.stats) == "table"
        if slot_name ~= "Mantle" and (use_ids or use_stats) then
            local ok, err = pcall(function()
                local sd = get_slot_item(character, SlotEnum[slot_name])
                if not sd or sd._ItemId == 0 then return end
                local want_item = equipment and equipment[slot_name] or 0
                if want_item > 0 and sd._ItemId ~= want_item then return end
                local _, cur = ability_of(sd)
                local ids = use_ids and c.ids or cur
                local stats = nil
                if use_stats then
                    local lim = EqSkill.limits(sd._ItemId)
                    if lim then
                        stats = {}
                        for _, f in ipairs(EqSkill.STATS) do stats[f[1]] = math.tointeger(c.stats[f[1]] or 0) or 0 end
                        if not EqSkill.stats_fit(sd._ItemId, stats) then
                            for _, f in ipairs(EqSkill.STATS) do stats[f[1]] = math.max(lim[f[1]][1], math.min(lim[f[1]][2], stats[f[1]])) end
                            Log("Appraisal roll on " .. slot_name .. " was outside the game's limits, clamped")
                        end
                        local bn = math.tointeger(c.stats.bonus or -1)
                        if bn and bn >= 0 and EqSkill.bonus_ok(sd._ItemId, bn) then stats.bonus = bn end
                    end
                end
                if same_set(cur, ids) and stats_same(sd, stats) then return end
                local sid = sid_of(sd)
                if not sid then return end
                local k = tostring(sid)
                odata.eq_sid = odata.eq_sid or {}
                odata.eq_written = odata.eq_written or {}
                if not odata.eq_written[k] then
                    local rec = EqSkill.capture(sd, slot_name)
                    if not rec then return end
                    rec.first = odata.eq_sid[k] and odata.eq_sid[k].first or nil
                    odata.eq_sid[k] = rec
                end
                odata.eq_written[k] = {slot = slot_name, ids = deep_copy(ids)}
                save_config()
                write(character, slot_name, sd, ids, nil, nil, stats)
            end)
            if not ok then Log("Special skills failed on " .. slot_name .. ": " .. tostring(err)) end
        end
    end
end

function EqSkill.as_overrides(eq_sid)
    local out = {}
    for pass = 1, 2 do
        for _, rec in pairs(eq_sid or {}) do
            local any = false
            for n = 1, 4 do if (rec.ids[n] or 0) ~= 0 then any = true end end
            if any and rec.slot and (pass == 2 or rec.first) and not out[rec.slot] then
                out[rec.slot] = {enabled = true, ids = deep_copy(rec.ids)}
            end
        end
    end
    return out
end

function EqSkill.audit(character)
    local out = {}
    for _, slot_name in ipairs(ENHANCE_SLOTS) do
        pcall(function()
            local sd = get_slot_item(character, SlotEnum[slot_name])
            if not sd or sd._ItemId == 0 then return end
            local _, ids = ability_of(sd)
            if slot_name == "Mantle" then
                for n = 1, 4 do
                    if (ids[n] or 0) ~= 0 then table.insert(out, "Special skills detected on mantle, these have no effect") break end
                end
                return
            end
            for _, w in ipairs(EqSkill.check(ids, false, sd._ItemId)) do table.insert(out, slot_name .. ": " .. w) end
            local st = EqSkill.stats_of(sd)
            if st and EqSkill.rows(sd._ItemId) and not EqSkill.stats_fit(sd._ItemId, st) then
                table.insert(out, string.format("%s: appraisal stats (P %d M %d B %d W %d) are outside anything a real drop can roll",
                    slot_name, st.phys, st.magic, st.blow, st.weight))
            end
            if st and not EqSkill.bonus_ok(sd._ItemId, st.bonus) then
                table.insert(out, slot_name .. ": the " .. (EqSkill.BONUS_NAMES[st.bonus] or ("bonus " .. tostring(st.bonus))) .. " can't roll on this item")
            end
        end)
    end
    return out
end

function EqSkill.restore(character, odata, only_slot, only_key)
    if not (odata and odata.eq_written and odata.eq_sid) then return end
    for k, w in pairs(odata.eq_written) do
        if type(w) ~= "table" then w = {slot = w} end
        if (not only_slot or w.slot == only_slot) and (not only_key or k == only_key) then
            local rec = odata.eq_sid[k]
            local ok, gone = pcall(function()
                local sd = rec and ItemManager:call("getStorageDataByStorageId", rec.sid)
                if not sd or sd._ItemId ~= rec.item then return true end
                local _, cur = ability_of(sd)
                if same_set(cur, rec.ids) and (rec.phys == nil or stats_same(sd, rec)) then return true end
                if w.ids and not same_set(cur, w.ids) then
                    Log("Special skills on " .. tostring(w.slot) .. " were changed outside the mod, leaving them as they are")
                    return true
                end
                write(character, w.slot, sd, rec.ids, rec, function() odata.eq_written[k] = nil config_changed = true end)
                return false
            end)
            if ok and gone then odata.eq_written[k] = nil end
        end
    end
    config_changed = true
end

end

local PawnCheck = {result = {}}

do
local function server_ctrl()
    local ok, psc = pcall(function()
        return sdk.get_managed_singleton("app.NetworkManager"):call("getPawnServerModeController()")
    end)
    return ok and psc or nil
end

local style_names = {}
local function style_name(enum_type, v)
    local m = style_names[enum_type]
    if not m then
        m = {}
        for _, e in ipairs(enum_values(enum_type)) do m[e.id] = e.name end
        style_names[enum_type] = m
    end
    return m[v]
end

local VISUAL_SLOTS = {
    {"Head", "_HelmStyle", "app.HelmStyle"}, {"Upper", "_TopsStyle", "app.TopsStyle"},
    {"Lower", "_PantsStyle", "app.PantsStyle"}, {"Mantle", "_MantleStyle", "app.MantleStyle"},
}

local function visual_check(chara)
    local bad, notes = {}, {}
    local meta = chara["<HumanPartSwapper>k__BackingField"]:call("get_Meta")
    local visual_item = 0
    pcall(function() visual_item = get_slot_item(chara, SlotEnum.Visual)._ItemId or 0 end)
    for _, v in ipairs(VISUAL_SLOTS) do
        pcall(function()
            local sd = get_slot_item(chara, SlotEnum[v[1]])
            if not sd or sd._ItemId == 0 then return end
            local style_no = ItemManager:getItemData(sd._ItemId):call("get_StyleNo")
            local raw = meta:get_field(v[2])
            raw = type(raw) == "number" and raw or raw:get_field("value__")
            local have = style_name(v[3], raw) or tostring(raw)
            local want_num = tonumber(have:match("(%d+)$") or "")
            local ok = want_num ~= nil and want_num == style_no
            table.insert(notes, string.format("%s item %d style %s, look %s %s", v[1], sd._ItemId, tostring(style_no), have, ok and "match" or "MISMATCH"))
            if not ok then table.insert(bad, v[1]) end
        end)
    end
    Log("[visual check] " .. table.concat(notes, " | ") .. (visual_item ~= 0 and (" | Visual slot item " .. visual_item) or ""))
    return bad
end

function PawnCheck.rank_audit(chara)
    local out = {}
    local function n_of(v) if type(v) == "number" then return v end return tonumber(v:get_field("value__")) or 0 end
    local h = chara:call("get_Human")
    local job = current_job(h)
    if not job then return out end
    local rank = tonumber(h:call("get_JobContext"):call("calcJobRank", job)) or 0
    local sc = h:call("get_SkillContext")
    local gm = sdk.get_managed_singleton("app.GuiManager")
    for s = 0, SKILL_SLOTS - 1 do
        pcall(function()
            local id = n_of(sc:call("getSkillID", job, s))
            if id <= 0 then return end
            local nm = name_of(Lists.skills, id) or ("Skill " .. id)
            local need = Lists.unlock_rank("skill", job, id)
            if type(need) == "number" and need <= 9 and need > rank then
                table.insert(out, nm .. " needs vocation rank " .. need .. " (this pawn is rank " .. rank .. ")")
            end
            if n_of(sc:call("getCustomSkillLevel", id)) >= 2 then
                if not Lists.lv2_has_text(job, id) then
                    table.insert(out, nm .. " is on a level 2 the game never shipped")
                else
                    local need2 = gm:call("getCustomSkillDefine(app.Character.JobEnum, app.HumanCustomSkillID, app.HumanCustomSkillLevelNo)", job, id, 2):get_field("_UnlockRank")
                    if type(need2) == "number" and need2 <= 9 and need2 > rank then
                        table.insert(out, "Upgraded " .. nm .. " needs vocation rank " .. need2 .. " (this pawn is rank " .. rank .. ")")
                    end
                end
            end
        end)
    end
    for _, it in ipairs(Lists.core_for(job)) do
        pcall(function()
            if not sc:call("isNormalSkillEnable", it.id) then return end
            local need = Lists.unlock_rank("core", job, it.id)
            if type(need) == "number" and need <= 9 and need > rank then
                table.insert(out, "Core skill " .. it.name .. " needs vocation rank " .. need .. " (this pawn is rank " .. rank .. ")")
            end
        end)
    end
    return out
end

function PawnCheck.validate(i, chara, after)
    PawnCheck.result[i] = {busy = true, text = "Checking..."}
    table.insert(game_jobs, function()
        local res = {}
        local ok, err = pcall(function()
            local psc = server_ctrl()
            if not psc then error("the game's online pawn service isn't running (offline?)") end
            local fmt = psc:get_field("OnlinePawnDataFormatter")
            local val = psc:call("get_Validator")
            if not (fmt and val) then error("validator not set up yet (offline?)") end
            local step = "create"
            local function run(name, fn)
                step = name
                local okR, errR = pcall(fn)
                if not okR then error(name .. ": " .. tostring(errR)) end
            end
            local pd
            run("create playdata", function()
                pd = sdk.create_instance("app.PawnApiUserdata.Playdata")
                pcall(function() pd:call(".ctor()") end)
                pd = pd:add_ref()
            end)
            run("look", function() fmt:call("updatePlaydataFromCharaEditData(via.GameObject, app.PawnApiUserdata.Playdata)", chara:call("get_GameObject"), pd) end)
            run("pawn data", function() fmt:call("updatePlaydataFromPawnData(app.Character, app.PawnApiUserdata.Playdata)", chara, pd) end)
            run("system data", function() fmt:call("updatePlaydataFromSystemData(app.Character, app.PawnApiUserdata.Playdata)", chara, pd) end)
            run("owner data", function() fmt:call("updatePlaydataFromOwnerData", pd) end)
            local writer
            run("upload work", function() writer = fmt:call("makeToUploadValidationWork", pd) end)
            run("validate", function() res.all = val:call("isValidationMyPawnUploadData", pd, writer) end)
            local parts = {}
            local function sub(label, fn)
                local okS, v = pcall(fn)
                if okS and v == false then table.insert(parts, label) end
            end
            sub("vocation rank", function() return val:call("isValidationJobRank(app.ContextWriterOnline)", writer) end)
            sub("gear not allowed for the vocation", function()
                local job = chara:call("get_Human"):call("get_JobContext"):call("get_Job")
                return val:call("isValidationCanEquip", job, writer)
            end)
            sub("equipped gear doesn't match the pawn's visual styles", function() return val:call("isValidationEquipEqualWeponAndMeta", writer) end)
            res.parts = parts
        end)
        local skills = {}
        pcall(function() skills = EqSkill.audit(chara) end)
        pcall(function() for _, w in ipairs(PawnCheck.rank_audit(chara)) do table.insert(skills, w) end end)
        local vis_bad = {}
        pcall(function() vis_bad = visual_check(chara) end)
        local skill_text = #skills > 0 and ("\n" .. table.concat(skills, "\n")) or ""
        local status = "fail"
        if not ok then
            status = "error"
            PawnCheck.result[i] = {text = "Couldn't check: " .. tostring(err) .. skill_text, col = 0xFF33AAFF}
            Log("Validate " .. slot_label(i) .. " failed to run: " .. tostring(err))
        elseif res.all and #skills == 0 then
            status = "valid"
            PawnCheck.result[i] = {text = "Pawn valid", col = 0xFF66DD66}
            Log("Validate " .. slot_label(i) .. ": valid")
        elseif res.all then
            PawnCheck.result[i] = {text = "Game check passed, but:" .. skill_text, col = 0xFF33AAFF}
            Log("Validate " .. slot_label(i) .. ": game check passed, skill issues: " .. table.concat(skills, "; "))
        elseif #res.parts == 1 and res.parts[1]:find("visual styles", 1, true) then
            local where = #vis_bad > 0 and table.concat(vis_bad, ", ") or "gear"
            PawnCheck.result[i] = {text = "Passed main checks, but the look hasn't caught up with the " .. where .. " yet.\nRest, reload, or re-equip it in the game's menu, then validate again." .. skill_text, col = 0xFF33AAFF}
            Log("Validate " .. slot_label(i) .. ": only the visual-style check failed" .. where)
        else
            local why = #res.parts > 0 and (" (" .. table.concat(res.parts, ", ") .. ")") or ""
            PawnCheck.result[i] = {text = "Pawn failed validation" .. why .. skill_text, col = 0xFF4444FF}
            Log("Validate " .. slot_label(i) .. ": FAILED" .. why)
        end
        if after then pcall(after, status) end
    end)
end

local upload_until = 0
local net_hooks = cfg.log_uploads ~= false
local function quiet_path(path)
    return path:lower():find("login") or path:lower():find("auth") or path:lower():find("token")
end
if net_hooks then pcall(function()
    local td = sdk.find_type_definition("app.PawnServerController")
    local m = td and td:get_method("requestMyPawnUpload")
    if m then
        sdk.hook(m, function(args)
            upload_until = os.time() + 180
            Log("[upload trace] main pawn upload started")
        end, nil)
    end
    local rt = sdk.find_type_definition("app.network.PawnApiRequester.PawnApiRequest")
    if not rt then return end
    local function path_of(args)
        local ok, path = pcall(function() return sdk.to_managed_object(args[2]):get_field("<PathStr>k__BackingField") end)
        return ok and type(path) == "string" and path or "?"
    end
    local ok_m = rt:get_method("onSuccessAction")
    if ok_m then
        sdk.hook(ok_m, function(args)
            if os.time() > upload_until then return end
            local path = path_of(args)
            local body = ""
            if not quiet_path(path) then
                pcall(function()
                    local str = sdk.to_managed_object(args[3]):call("ToString()")
                    if type(str) ~= "string" then return end
                    local pid, at = str:match('"PawnId":"([^"]+)"'), str:match('"updateAt":(%d+)')
                    -- removed from public release: pawn info from server
                    if pid then body = " | pawn " .. pid .. (at and (", server time " .. os.date("%H:%M:%S", tonumber(at))) or "") end
                end)
            end
            Log("[upload trace] server OK: " .. path .. body)
        end, nil)
    end
    local fail_m = rt:get_method("onFailureAction")
    if fail_m then
        sdk.hook(fail_m, function(args)
            local cause = "?"
            pcall(function()
                local v = sdk.to_int64(args[3]) & 0xFFFFFFFF
                cause = style_name("app.network.NetworkError.ErrorCause", v) or tostring(v)
            end)
            local tag = os.time() <= upload_until and "after upload" or "pawn server"
            Log("[upload trace] " .. tag .. " request FAILED: " .. path_of(args) .. " (" .. cause .. ")")
        end, nil)
    end
end) end

-- removed from public release: main pawn stats
-- removed from public release: trace hooks

end

local job_wait = {[0] = 0, [1] = 0, [2] = 0}

local function apply_job(index, human, job)
    if not job or job <= 0 then return "done" end
    if job > MAX_PAWN_JOB then return "failed" end
    local cur = current_job(human)
    if cur == job then job_wait[index] = 0 return "done" end
    if job_wait[index] == 0 then
        local ok, err = pcall(function()
            local jc = human:call("get_JobContext")
            if not jc:call("isJobQualified", job) then jc:call("setJobQualified", job) end
            human:call("get_JobChanger"):call("requestChangeJob", job)
        end)
        if not ok then Log("Vocation change failed: " .. tostring(err)) return "failed" end
        Log(slot_label(index) .. ": requested vocation change to " .. (name_of(Lists.jobs, job) or job))
    end
    job_wait[index] = job_wait[index] + 1
    if job_wait[index] > 300 then
        Log(slot_label(index) .. ": vocation change did not apply (still " .. tostring(cur) .. ")")
        job_wait[index] = 0
        return "failed"
    end
    return "pending"
end

local MAX_JOB_RANK = 9

local status_ctx, max_level, apply_level, reset_level, snapshot_status, restore_status

do
local INCREASE_FIELDS = {"_HitPoint", "_Stamina", "_Attack", "_Defence", "_MagicAttack", "_MagicDefence", "_Blow", "_Weight"}

function status_ctx(human)
    local ok, sc = pcall(function() return human:call("get_StatusContext") end)
    return ok and sc or nil
end

function max_level(human)
    local ok, m = pcall(function() return human:call("get_Param"):call("get_LVupInfo"):call("get_MaxLevel") end)
    return (ok and type(m) == "number" and m > 0) and m or 999
end

local function refresh_hp_stamina(human)
    pcall(function() human:call("updateMaxHPAndStamina", false, 1) end)
end

function apply_level(human, target)
    if not target or target <= 0 then return end
    local ok, err = pcall(function()
        local sc = status_ctx(human)
        if not sc then error("no status context") end
        target = math.min(target, max_level(human))
        local cur = sc:call("get_Level")
        if cur >= target then return end
        local job = current_job(human) or 1
        local function hp() return tostring(sc:get_field("_IncreaseParams"):get_field("_HitPoint")) end
        local progress = sc:call("get_Exp") or 0
        local before = "exp " .. tostring(progress) .. " hp+" .. hp()
        local spent = 0
        pcall(function() spent = human:call("get_Param"):call("get_LVupInfo"):call("getRequiredEXP", cur, target) or 0 end)
        if spent < 0 then spent = 0 end
        sc:call("set_Exp", progress + spent)
        sc:call("levelup(System.Int32, System.Int32, app.Character.JobEnum, System.Single)", target, spent, job, 0.0)
        if sc:call("get_Exp") ~= progress then sc:call("set_Exp", progress) end
        refresh_hp_stamina(human)
        Log("Level " .. cur .. " -> " .. tostring(sc:call("get_Level")) .. " (target " .. target .. ") | before " .. before
            .. " | after exp " .. tostring(sc:call("get_Exp")) .. " hp+" .. hp())
    end)
    if not ok then Log("Level change failed: " .. tostring(err)) end
end

function reset_level(human)
    local ok, err = pcall(function()
        local sc = status_ctx(human)
        local function state()
            return "level " .. tostring(sc:call("get_Level")) .. ", exp " .. tostring(sc:call("get_Exp"))
                .. ", hp+" .. tostring(sc:get_field("_IncreaseParams"):get_field("_HitPoint"))
        end
        local before = state()
        human:call("resetLevel")
        refresh_hp_stamina(human)
        Log("Level reset: " .. before .. " -> " .. state())
    end)
    if not ok then Log("Level reset failed: " .. tostring(err)) end
end

function snapshot_status(human)
    local sc = status_ctx(human)
    if not sc then return nil end
    local s = {}
    local ok = pcall(function()
        s.level = sc:call("get_Level")
        s.exp = sc:call("get_Exp")
        local inc = sc._IncreaseParams
        s.inc = {}
        for _, f in ipairs(INCREASE_FIELDS) do s.inc[f] = inc[f] end
    end)
    return ok and s or nil
end

function restore_status(human, s)
    if not s then return end
    local ok, err = pcall(function()
        local sc = status_ctx(human)
        sc:call("set_Level", s.level)
        sc:call("set_Exp", s.exp)
        local inc = sc._IncreaseParams
        for f, v in pairs(s.inc or {}) do inc[f] = v end
        refresh_hp_stamina(human)
    end)
    Log(ok and ("Restored level " .. tostring(s.level)) or ("Level restore failed: " .. tostring(err)))
end

end

local function apply_job_rank(human, job, rank)
    if not rank or rank <= 0 then return end
    local ok, err = pcall(function()
        local jc = human:call("get_JobContext")
        if jc:call("calcJobRank", job) == rank then return end
        jc:call("setJobExpWithJobRank", job, rank)
        Log("Vocation rank set to " .. tostring(jc:call("calcJobRank", job)))
    end)
    if not ok then Log("Vocation rank failed: " .. tostring(err)) end
end

local SlotBase = {}

function SlotBase.plan(row, is_over, N, locked)
    local desired, used, pool = {}, {}, {}
    for s = 1, N do if is_over[s] then desired[s] = is_over[s] used[is_over[s]] = true end end
    for s = 1, N do
        local b = row[s] or 0
        if is_over[s] and b ~= 0 and not used[b] then pool[#pool + 1] = b end
    end
    for s = 1, N do
        if not is_over[s] then
            local b = row[s] or 0
            if b ~= 0 and used[b] and not (locked and locked[s]) then desired[s] = table.remove(pool, 1) or 0
            else desired[s] = b end
        end
    end
    return desired
end

function SlotBase.write(read, write, want, N, locked)
    local cur, changed = {}, {}
    for s = 1, N do cur[s] = read(s) end
    for s = 1, N do
        if want[s] ~= nil and cur[s] ~= want[s] and not (locked and locked[s]) then
            changed[#changed + 1] = s
            if cur[s] ~= 0 then pcall(write, s, 0) end
        end
    end
    for _, s in ipairs(changed) do
        if want[s] ~= 0 then pcall(write, s, want[s]) end
    end
    local after = {}
    for s = 1, N do after[s] = read(s) end
    return after, changed
end

function SlotBase.run(pcfg, key, legacy, job, N, read, write, is_over, locked)
    local B = pcfg[key]
    if type(B) ~= "table" or type(B.row) ~= "table" or type(B.last) ~= "table" then B = nil end
    if B and B.job ~= job then
        local oj = B.job
        for s = 1, N do
            local c = read(oj, s)
            if B.row[s] == nil or c ~= B.last[s] then B.row[s] = c end
        end
        SlotBase.write(function(s) return read(oj, s) end, function(s, id) write(oj, s, id) end, B.row, N, locked)
        B = nil
        pcfg[key] = nil
        config_changed = true
    end
    local any = next(is_over) ~= nil
    local old = type(pcfg[legacy]) == "table" and pcfg[legacy] or nil
    if not B and (any or old) then
        B = {job = job, row = {}, last = {}}
        for s = 1, N do local c = read(job, s) B.row[s] = c B.last[s] = c end
        for k, rec in pairs(old or {}) do
            local s = tonumber(k)
            if s and type(rec) == "table" and rec.job == job and B.last[s] == rec.id then
                B.row[s] = rec.prev or 0
                if rec.swap_t and B.last[rec.swap_t] == (rec.prev or 0) then B.row[rec.swap_t] = rec.id end
            end
        end
        pcfg[key] = B
        config_changed = true
    elseif B then
        for s = 1, N do
            local c = read(job, s)
            if B.row[s] == nil or B.last[s] == nil then B.row[s], B.last[s] = c, c config_changed = true
            elseif c ~= B.last[s] then B.row[s] = c config_changed = true end
        end
    end
    if old then pcfg[legacy] = nil config_changed = true end
    if not B then return nil end
    local want = any and SlotBase.plan(B.row, is_over, N, locked) or B.row
    local after, changed = SlotBase.write(function(s) return read(job, s) end, function(s, id) write(job, s, id) end, want, N, locked)
    if any then
        for s = 1, N do if B.last[s] ~= after[s] then B.last[s] = after[s] config_changed = true end end
    else
        pcfg[key] = nil
        config_changed = true
    end
    return changed, not any, want
end

function SlotBase.report(what, list, changed, undone, want)
    if not changed or #changed == 0 then return end
    local parts = {}
    for _, s in ipairs(changed) do
        local id = want[s] or 0
        parts[#parts + 1] = s .. ": " .. (id > 0 and (name_of(list, id) or tostring(id)) or "empty")
    end
    Log((undone and (what .. " overrides removed, originals put back (") or (what .. " slots set (")) .. table.concat(parts, ", ") .. ")")
end

local function apply_skills(human, job, pcfg, restrict, exact)
    local sc = human:call("get_SkillContext")
    if not sc then return end
    local SET = "setSkill(app.Character.JobEnum, app.HumanCustomSkillID, app.HumanSkillContext.SkillSlot)"
    local function read(j, slot)
        local ok, v = pcall(function()
            local r = sc:call("getSkillID", j, slot - 1)
            if type(r) == "number" then return r end
            return tonumber(r:get_field("value__")) or 0
        end)
        return ok and v or 0
    end
    local function write(j, slot, id) sc:call(SET, j, id, slot - 1) end
    if exact then
        local j = (pcfg.job or 0) > 0 and pcfg.job or job
        local want = {}
        for s = 1, SKILL_SLOTS do
            local id = type(pcfg.skills) == "table" and pcfg.skills[s] or nil
            if id and (id == 0 or SkillJob[id] == j) then want[s] = id end
        end
        local _, changed = SlotBase.write(function(s) return read(j, s) end, function(s, id) write(j, s, id) end, want, SKILL_SLOTS)
        SlotBase.report("Skill", Lists.skills, changed, true, want)
        return
    end
    local function set_level(id, lv)
        local done = false
        pcall(function()
            local list = sc:get_field("EnabledCustomSkills")
            for n = 0, list:call("get_Count") - 1 do
                local it = list:call("get_Item", n)
                local cid = it:get_field("CustomSkillID")
                if type(cid) ~= "number" then cid = tonumber(cid:get_field("value__")) end
                if cid == id then it:set_field("Level", lv) done = true break end
            end
        end)
        return done
    end
    local is_over, claimed = {}, {}
    for slot = 1, SKILL_SLOTS do
        local id = pcfg.skills[slot] or 0
        if id == -1 then
            is_over[slot] = 0
        elseif id > 0 and claimed[id] then
            DebugLog("attribute", "Skill " .. id .. " is already in an earlier slot, skipped")
        elseif id > 0 and SkillJob[id] ~= job then
            DebugLog("attribute", "Skill " .. id .. " belongs to another vocation, skipped")
        elseif id > 0 then
            claimed[id] = true
            local ok, err = pcall(function()
                local max_up = cfg.skill_max_level ~= false and Lists.lv2_real(job, id)
                if not sc:call("isCustomSkillEnable", id) then
                    if restrict then
                        DebugLog("attribute", "Skill " .. id .. " not learned, skipped (learned-only)")
                        return
                    end
                    sc:call("setCustomSkillEnable(app.HumanCustomSkillID, app.HumanCustomSkillLevelNo)", id, max_up and 2 or 1)
                    Log("Skill " .. (name_of(Lists.skills, id) or id) .. " unlocked" .. (max_up and " as the upgraded variant" or ""))
                end
                if max_up and not sc:call("isCustomSkillReachLevel", id, 2) then
                    for _ = 1, 2 do
                        if sc:call("isCustomSkillReachLevel", id, 2) then break end
                        sc:call("setCustomSkillLevelUp", id)
                    end
                    local forced = not sc:call("isCustomSkillReachLevel", id, 2) and set_level(id, 2)
                    Log("Skill " .. (name_of(Lists.skills, id) or id) .. " upgraded to level " .. tostring(sc:call("getCustomSkillLevel", id))
                        .. (forced and " (set directly, the game's level-up refused)" or ""))
                end
                if not max_up and not Lists.lv2_has_text(job, id) and sc:call("isCustomSkillReachLevel", id, 2) then
                    set_level(id, 1)
                    Log("Skill " .. (name_of(Lists.skills, id) or id) .. " back to level 1 (its level 2 was never shipped)")
                end
                is_over[slot] = id
            end)
            if not ok then Log("Skill slot " .. slot .. " failed: " .. tostring(err)) end
        end
    end
    local changed, undone, want = SlotBase.run(pcfg, "skills_base", "skills_set", job, SKILL_SLOTS, read, write, is_over)
    SlotBase.report("Skill", Lists.skills, changed, undone, want)
end

local function unlocked_abilities(human)
    local set = {}
    pcall(function()
        local list = human:call("get_AbilityContext"):get_field("EnableAbilities")
        for n = 0, list:call("get_Count") - 1 do
            local e = list:call("get_Item", n)
            if e and e:get_field("IsEnable") ~= false then set[e:get_field("AbilityID")] = true end
        end
    end)
    return set
end

local function aug_num(v)
    if type(v) == "number" then return v end
    local ok, n = pcall(function() return v:get_field("value__") end)
    return ok and tonumber(n) or 0
end

local function apply_abilities(human, job, pcfg, restrict, orig_job, exact)
    local ac = human:call("get_AbilityContext")
    if not ac then return end
    if not exact and cfg.keep_augments ~= false then
        local any = false
        for slot = 1, ABILITY_SLOTS do
            if (pcfg.abilities[slot] or 0) > 0 then any = true end
            local okA, v = pcall(function() return ac:call("getAbility", job, slot - 1) end)
            if okA and aug_num(v) > 0 then any = true end
        end
        if not any then
            local order = {}
            if orig_job and orig_job > 0 and orig_job ~= job then table.insert(order, orig_job) end
            for j = 1, 10 do if j ~= job and j ~= orig_job then table.insert(order, j) end end
            for _, j in ipairs(order) do
                local got, n = {}, 0
                for slot = 1, ABILITY_SLOTS do
                    local okA, v = pcall(function() return ac:call("getAbility", j, slot - 1) end)
                    local id = okA and aug_num(v) or 0
                    if id > 0 then got[slot] = id n = n + 1 end
                end
                if n > 0 then
                    local placed = 0
                    for slot, id in pairs(got) do
                        if pcall(function() ac:call("setAbility", job, id, slot - 1) end) then placed = placed + 1 end
                    end
                    Log("Kept augments: copied " .. placed .. "/" .. n .. " from "
                        .. (name_of(Lists.jobs, j) or ("job " .. j)) .. " to " .. (name_of(Lists.jobs, job) or ("job " .. job)))
                    break
                end
            end
        end
    end
    local unlocked = restrict and unlocked_abilities(human) or nil
    local base_slots, extra_open = 6, false
    pcall(function() base_slots = ac:get_field("DefaultNumSlots") or 6 end)
    pcall(function() extra_open = ac:get_field("IsAdditionalSlotUnlocked") == true end)
    if pcfg.extra_aug and not extra_open then
        pcall(function() ac:call("unlockAdditionalSlot") end)
        pcall(function() extra_open = ac:get_field("IsAdditionalSlotUnlocked") == true end)
        Log("Extra augment slot " .. (extra_open and "unlocked" or "couldn't be unlocked"))
    end
    local function read(j, slot)
        local ok, v = pcall(function() return aug_num(ac:call("getAbility", j, slot - 1)) end)
        return ok and v or 0
    end
    local function write(j, slot, id) ac:call("setAbility", j, id, slot - 1) end
    local locked = {}
    for s = 1, ABILITY_SLOTS do if s > base_slots and not extra_open then locked[s] = true end end
    if exact then
        local j = (pcfg.job or 0) > 0 and pcfg.job or job
        local want = {}
        for s = 1, ABILITY_SLOTS do
            local id = type(pcfg.abilities) == "table" and pcfg.abilities[s] or nil
            if id then want[s] = id end
        end
        local _, changed = SlotBase.write(function(s) return read(j, s) end, function(s, id) write(j, s, id) end, want, ABILITY_SLOTS, locked)
        SlotBase.report("Augment", Lists.abilities, changed, true, want)
        return
    end
    local is_over, claimed = {}, {}
    for slot = 1, ABILITY_SLOTS do
        local id = pcfg.abilities[slot] or 0
        if id > 0 and claimed[id] then
            DebugLog("attribute", "Augment " .. id .. " is already in an earlier slot, skipped")
        elseif id > 0 and locked[slot] then
            DebugLog("attribute", "Augment slot " .. slot .. " is locked, skipped")
        elseif id > 0 then
            claimed[id] = true
            if unlocked and not unlocked[id] then
                DebugLog("attribute", "Augment " .. id .. " not unlocked, skipped (unlocked-only)")
            else
                if read(job, slot) ~= id then pcall(function() ac:call("setAbilityEnable", id) end) end
                is_over[slot] = id
            end
        end
    end
    local changed, undone, want = SlotBase.run(pcfg, "abilities_base", "abilities_set", job, ABILITY_SLOTS, read, write, is_over, locked)
    SlotBase.report("Augment", Lists.abilities, changed, undone, want)
end

local function ctx_name(ctx)
    local ok, n = pcall(function() return ctx:call("get_Name") end)
    return ok and type(n) == "string" and n or nil
end

local function slot_original(i)
    local o = cfg.originals["slot" .. i]
    return o and o.data or nil
end

local function pref_get(i, name, default)
    local o = cfg.originals["slot" .. i]
    if o and o.prefs and o.prefs[name] ~= nil then return o.prefs[name] end
    return default
end

local function pref_set(i, name, v)
    local o = cfg.originals["slot" .. i]
    if not o then return end
    o.prefs = o.prefs or {}
    o.prefs[name] = v
    config_changed = true
end

local function learned_only(i) return pref_get(i, "learned_only", true) end
local function unlocked_aug_only(i) return pref_get(i, "unlocked_augments_only", true) end

local function set_learned_only(i, v)
    local o = cfg.originals["slot" .. i]
    if not o then return end
    o.prefs = o.prefs or {}
    o.prefs.learned_only = v
    config_changed = true
end

local function relax_filters(i, human)
    local pcfg = cfg["pawn" .. i]
    if not (pcfg and human) then return end
    pcall(function()
        local sc = human:call("get_SkillContext")
        for _, id in ipairs(pcfg.skills or {}) do
            if (id or 0) > 0 and not sc:call("isCustomSkillEnable", id) then
                if learned_only(i) then set_learned_only(i, false) Log(slot_label(i) .. ": turned off 'learned only' so the loaded skills can apply") end
                break
            end
        end
    end)
    pcall(function()
        local have = unlocked_abilities(human)
        for _, id in ipairs(pcfg.abilities or {}) do
            if (id or 0) > 0 and not have[id] then
                if unlocked_aug_only(i) then pref_set(i, "unlocked_augments_only", false) Log(slot_label(i) .. ": turned off 'unlocked augments only' so the loaded augments can apply") end
                break
            end
        end
    end)
end

local function apply_name(ctx, pcfg, orig_name, orig_nick)
    local cur = ctx_name(ctx)
    if not cur then return end
    local target = (pcfg.name ~= "" and pcfg.name) or orig_name
    if target and target ~= "" and cur ~= target then
        if not pcall(function() ctx:call("setName", target) end) then Log("Failed to rename pawn") end
    end
    local want = (pcfg.name_moniker and (pcfg.name or "") ~= "" and pcfg.name) or orig_nick
    if want and want ~= "" then
        local now = nil
        pcall(function() now = ctx:call("get_Nickname") end)
        if now ~= want and not pcall(function() ctx:call("setNickName(System.String)", want) end) then Log("Failed to set the moniker") end
    end
end

local function apply_attributes(character, pcfg, orig_name, orig_nick)
    local ctx = get_data_context(character)
    if not ctx then return false end
    local ok_all = true
    apply_name(ctx, pcfg, orig_name, orig_nick)

    if pcfg.personality ~= 0 then
        if not pcall(function() ctx:setPersonarity(pcfg.personality) end) then
            Log("Failed to set personality") ok_all = false
        end
    end

    if pcfg.voice_gender ~= 0 or pcfg.voice_tone >= 0 then
        local g = pcfg.voice_gender ~= 0 and pcfg.voice_gender or ctx:get_VoiceGender()
        local t = pcfg.voice_tone >= 0 and pcfg.voice_tone or ctx:get_VoiceToneType()
        if not pcall(function() ctx:setVoiceGender(g) ctx:setVoiceToneType(t) end) then
            Log("Failed to set voice") ok_all = false
        end
    end

    if pcfg.specialization >= 0 then
        local want = pcfg.specialization
        local function cur()
            local okC, v = pcall(function() return ctx:call("get_SubSkill") end)
            return okC and v or nil
        end
        if cur() ~= want then
            pcall(function() ctx:call("setSubSkill(app.PawnDefine.SubSkillID, app.CharacterID)", want, character.CharacterID) end)
            local how = "setSubSkill"
            if cur() ~= want then
                pcall(function() ctx._SubSkill = want end)
                pcall(function() ItemManager:call("requestCheckPawnSubSkill(app.CharacterID)", character.CharacterID) end)
                how = "direct write"
            end
            if cur() == want then
                Log("Specialization set to " .. tostring(want) .. " (" .. how .. ")")
            else
                Log("Failed to set specialization (still " .. tostring(cur()) .. ")")
                ok_all = false
            end
        end
    end

    DebugLog("attribute", "Attributes applied")
    return ok_all
end

local immune_ctx = {}

do
    local td = sdk.find_type_definition("app.PawnDataContext")
    local function guard(sig, mode)
        local m = method(td, sig)
        if not m then Log("Plague hook unavailable: " .. sig) return end
        sdk.hook(m, function(args)
            if immune_ctx[sdk.to_int64(args[2])] then
                if mode == "skip" then return sdk.PreHookResult.SKIP_ORIGINAL end
                args[3] = sdk.to_ptr(0)
            end
        end, nil)
    end
    guard("setPossessionLv(System.Int32)", "zero")
    guard("setPossessionProgressPoint(System.Int32)", "zero")
    guard("addPossessionProgressPoint(System.Int32)", "skip")
end

local CHATTER_NAMES = {"Normal", "Less", "Rare", "Silent"}
local CHATTER_GAPS = {0, 45, 180, math.huge}
local talk_gap = {}
local last_spoke = {}

lazy_hooks.chatter = function()
    local td = sdk.find_type_definition("app.PLPartyTalkController")
    if not td then return 0 end
    local SPEAK_ERR_SLEEP = 8
    local function blocked(addr)
        local gap = addr and talk_gap[addr]
        if not gap then return false end
        if gap == math.huge then return true end
        return gap > 0 and last_spoke[addr] ~= nil and os.clock() - last_spoke[addr] < gap
    end
    local wanted = {preCheckCanPawnSpeak = true, evaluateSpeaker = true, canPawnSpeak = true, requestPawnTalk = true}
    local n = 0
    for _, m in ipairs(td:get_methods()) do
        local name = m:get_name()
        local idx
        if wanted[name] then
            for k, pt in ipairs(m:get_param_types()) do
                if pt:get_full_name() == "app.Character" then idx = k break end
            end
        end
        if idx then
            sdk.hook(m, function(args)
                local addr = sdk.to_int64(args[idx + 2])
                local s = thread.get_hook_storage()
                s.tpc_talk = s.tpc_talk or {}
                local blk = blocked(addr)
                table.insert(s.tpc_talk, {addr = addr, blk = blk})
                if blk and name == "requestPawnTalk" then return sdk.PreHookResult.SKIP_ORIGINAL end
            end, function(retval)
                local s = thread.get_hook_storage()
                local e = s.tpc_talk and table.remove(s.tpc_talk)
                if not e then return retval end
                if e.blk then
                    if name == "preCheckCanPawnSpeak" then return sdk.to_ptr(SPEAK_ERR_SLEEP) end
                    return sdk.to_ptr(0)
                end
                if name == "requestPawnTalk" and talk_gap[e.addr] and (sdk.to_int64(retval) & 1) == 1 then
                    last_spoke[e.addr] = os.clock()
                end
                return retval
            end)
            n = n + 1
        end
    end
    return n
end

local function update_chatter()
    talk_gap = {}
    for _, i in ipairs(SLOT_IDS) do
        local pcfg = cfg["pawn" .. i]
        local level = pcfg.chatter or 1
        if pcfg.enabled and level > 1 then
            local c = get_character(bound_pawn(i))
            if c then
                need_hooks("chatter")
                talk_gap[c:get_address()] = CHATTER_GAPS[level]
            end
        end
    end
end

local function cure_plague(pawn, ctx)
    table.insert(game_jobs, function()
        pcall(function() ctx:call("setPossessionProgressPoint", 0) end)
        pcall(function() ctx:call("setPossessionLv", 0) end)
        pcall(function() ctx:call("setDragonPossessionReinfoceAccmulationValue", 0.0) end)
        pcall(function() pawn:call("stopDragonPossessionReinforce") end)
    end)
end

local last_plague_check = 0
local function update_plague()
    local now = os.clock()
    if now - last_plague_check < 1.0 then return end
    last_plague_check = now

    update_chatter()
    immune_ctx = {}
    for _, i in ipairs(SLOT_IDS) do
        local pcfg = cfg["pawn" .. i]
        if pcfg.enabled and pcfg.plague_immune then
            local pawn = bound_pawn(i)
            local ctx = get_data_context(get_character(pawn))
            if ctx then
                immune_ctx[ctx:get_address()] = true
                local lv = ctx:call("get_PossessionLv") or 0
                local pts = ctx:call("get_PossessionProgressPoint") or 0
                if lv > 0 or pts > 0 then
                    immune_ctx[ctx:get_address()] = nil
                    cure_plague(pawn, ctx)
                    immune_ctx[ctx:get_address()] = true
                    Log(slot_label(i) .. ": cleared dragonsplague (was stage " .. lv .. ")")
                end
            end
        end
    end
end

local capture_clone, apply_clone

do
local function swapper(character)
    return character and character['<HumanPartSwapper>k__BackingField'] or nil
end

local CLONE_META_SKIP = {
    _BackpackStyle = true, _FacewearStyle = true, _FacewearVariationStyle = true,
    _HelmStyle = true, _HelmVariationStyle = true, _MantleStyle = true, _MantleVariationStyle = true,
    _PantsStyle = true, _PantsVariationStyle = true, _TopsStyle = true, _TopsVariationStyle = true,
    _UnderwearStyle = true, _UnderwearVariationStyle = true, _Gender = true, _Species = true, _Locked = true
}

local function instance_fields(obj)
    local out = {}
    local ok, td = pcall(function() return obj:get_type_definition() end)
    while ok and td do
        local name = td:get_full_name()
        if name == "app.Context" or name:match("^System%.") then break end
        for _, f in ipairs(td:get_fields()) do
            if not f:is_static() then table.insert(out, f:get_name()) end
        end
        td = td:get_parent_type()
    end
    return out
end

local function getf(obj, name)
    local ok, v = pcall(function() return obj:get_field(name) end)
    if ok then return v end
    ok, v = pcall(function() return obj[name] end)
    return ok and v or nil
end

local function serialize(v, depth)
    if type(v) ~= "userdata" then return v end
    if depth > 6 then return nil end
    local ok, td = pcall(function() return v:get_type_definition() end)
    if not ok or not td then return nil end
    if td:get_full_name() == "via.Color" then return {rgba = getf(v, "rgba")} end
    local t = {}
    for _, name in ipairs(instance_fields(v)) do
        local s = serialize(getf(v, name), depth + 1)
        if s ~= nil then t[name] = s end
    end
    return t
end

local function deserialize(target, t, depth)
    if depth > 6 or type(t) ~= "table" then return end
    for name, val in pairs(t) do
        local cur = getf(target, name)
        if type(val) ~= "table" then
            pcall(function() target:set_field(name, val) end)
        elseif type(cur) == "userdata" then
            local is_vt = false
            pcall(function() is_vt = cur:get_type_definition():is_value_type() end)
            deserialize(cur, val, depth + 1)
            if is_vt then pcall(function() target:set_field(name, cur) end) end
        end
    end
end

local function edit_values(ctx)
    local out = {}
    local arr = ctx:call("get_EditValues")
    for n = 0, arr:get_size() - 1 do
        local e = arr:get_element(n)
        if e then table.insert(out, {getf(e, "_EditKeyHash"), getf(e, "_Value")}) end
    end
    return out
end

function capture_clone(character, ps_override)
    local ps = ps_override or swapper(character)
    if not ps then return nil end
    local ok, c = pcall(function()
        local meta = ps:call("get_Meta")
        local m = {}
        for _, name in ipairs(instance_fields(meta)) do
            if not CLONE_META_SKIP[name] then m[name] = getf(meta, name) end
        end
        local bde = ps:call("get_BodyDetailEditor")
        local dctx = getf(bde, "_Context")
        pcall(function() dctx:call("copyFrom(app.BodyDetailEditor)", bde) end)
        return {
            gender = getf(meta, "_Gender"), species = getf(meta, "_Species"), meta = m,
            detail = serialize(dctx, 0),
            body = edit_values(getf(getf(ps, "_BodyEditor"), "_BodyEditContext")),
            face = edit_values(getf(getf(ps, "_FaceEditor"), "_Context")),
            pretender = serialize(getf(getf(ps, "_BodyEditor"), "_PretenderContext"), 0),
        }
    end)
    if not ok then Log("Clone capture failed: " .. tostring(c)) return nil end
    return c
end

local clone_hair_fix = {}

do
    local td = sdk.find_type_definition("app.PartSwapper")
    local m = td and td:get_method("set_HairObj")
    if m then
        sdk.hook(m, function(args)
            local q = clone_hair_fix[sdk.to_int64(args[2])]
            if q and not q.landed then q.landed = true q.at = os.clock() + 0.15 end
        end, nil)
    end
    re.on_pre_application_entry("UpdateBehavior", function()
        if not next(clone_hair_fix) then return end
        local now = os.clock()
        for addr, q in pairs(clone_hair_fix) do
            if now >= q.at then
                clone_hair_fix[addr] = nil
                local steps = {}
                pcall(function()
                    local bde = q.ps:call("get_BodyDetailEditor")
                    local dctx = bde:get_field("_Context")
                    for _, p in ipairs({{"_Hair", "HairContext"}, {"_Beard", "BeardContext"}, {"_Eyebrows", "EyebrowsContext"}}) do
                        local okc = pcall(function()
                            bde:get_field(p[1]):call("restore(app.BodyDetailContext." .. p[2] .. ")", dctx:get_field(p[1]))
                            bde:get_field(p[1]):call("requestApplyProperties")
                        end)
                        table.insert(steps, p[1] .. (okc and "" or "!"))
                    end
                end)
                Log("Clone hair colour re-applied after swap (" .. (q.landed and "hair landed" or "timeout") .. "): " .. table.concat(steps, ","))
            end
        end
    end)
end

function apply_clone(character, c)
    if type(c) ~= "table" or type(c.meta) ~= "table" then return "No clone data" end
    local ps = swapper(character)
    if not ps then return "No pawn" end
    local meta = ps:call("get_Meta")
    if getf(meta, "_Gender") ~= c.gender or getf(meta, "_Species") ~= c.species then
        Log("Clone skipped: gender/species differ from this pawn")
        return "Clone needs the same gender and species"
    end
    pcall(function()
        local hc = getf(getf(ps, "_HumanContext"), "_Meta")
        Log(string.format("Clone meta BEFORE write: live head %s skin %s muscle %s | saved-context head %s | target head %s",
            tostring(getf(meta, "_HeadStyle")), tostring(getf(meta, "_SkinStyle")), tostring(getf(meta, "_MuscleStyle")),
            tostring(getf(hc, "_HeadStyle")), tostring(c.meta._HeadStyle)))
    end)
    local ok, err = pcall(function()
        for name, v in pairs(c.meta) do pcall(function() meta:set_field(name, v) end) end
        pcall(function()
            getf(getf(ps, "_HumanContext"), "_Meta"):call("copyFrom(app.CharacterEditDefine.MetaData, app.CharacterEditDefine.MetaData.MetaFlags)", meta, 0xFFFFFFFF)
        end)
        local bde = ps:call("get_BodyDetailEditor")
        local dctx = getf(bde, "_Context")
        if c.detail then
            deserialize(dctx, c.detail, 0)
            local typed = {
                {"_Skin", "SkinContext"}, {"_Hair", "HairContext"}, {"_Beard", "BeardContext"}, {"_BodyHair", "BodyHairContext"},
                {"_Eyes", "EyesContext"}, {"_Eyelashes", "EyelashesContext"}, {"_Eyebrows", "EyebrowsContext"},
                {"_Freckles", "FrecklesContext"},
            }
            local dn, failed = 0, {}
            for _, p in ipairs(typed) do
                local okc = pcall(function()
                    getf(bde, p[1]):call("restore(app.BodyDetailContext." .. p[2] .. ")", getf(dctx, p[1]))
                end)
                if okc then dn = dn + 1 else table.insert(failed, p[1]) end
            end
            local mk = pcall(function()
                getf(bde, "_Makeup"):call("restore(app.BodyDetailContext.EyelinerContext, app.BodyDetailContext.EyeshadowContext, app.BodyDetailContext.CheekContext, app.BodyDetailContext.LipsContext)",
                    getf(dctx, "_Eyeliner"), getf(dctx, "_Eyeshadow"), getf(dctx, "_Cheek"), getf(dctx, "_Lips"))
            end)
            Log("Clone colour components restored: " .. dn .. "/" .. #typed .. ", makeup " .. (mk and "ok" or "failed")
                .. (#failed > 0 and (" (failed: " .. table.concat(failed, ",") .. ")") or ""))
        end

        local function count_matching(arr_owner, list, getter)
            if not arr_owner or not list then return "n/a" end
            local want = {}
            for _, kv in ipairs(list) do if kv[1] then want[kv[1]] = kv[2] end end
            local same, total = 0, 0
            local ok = pcall(function()
                local arr = arr_owner:call(getter)
                for n = 0, arr:get_size() - 1 do
                    local e = arr:get_element(n)
                    local v = e and want[getf(e, "_EditKeyHash")]
                    if v ~= nil then
                        total = total + 1
                        if math.abs((getf(e, "_Value") or 0) - v) < 0.0005 then same = same + 1 end
                    end
                end
            end)
            return ok and (same .. "/" .. total) or "unreadable"
        end
        local function write_edit_values(ctx, list)
            if not ctx or not list then return 0, 0 end
            local want = {}
            for _, kv in ipairs(list) do if kv[1] then want[kv[1]] = kv[2] end end
            local arr = ctx:call("get_EditValues")
            local hit, total = 0, 0
            for n = 0, arr:get_size() - 1 do
                local e = arr:get_element(n)
                if e then
                    total = total + 1
                    local v = want[getf(e, "_EditKeyHash")]
                    if v ~= nil then
                        pcall(function() e:call("set_Value", v) end)
                        if getf(e, "_Value") ~= v then pcall(function() e:set_field("_Value", v) end) end
                        hit = hit + 1
                    end
                end
            end
            return hit, total
        end
        local pctx = getf(getf(ps, "_BodyEditor"), "_PretenderContext")
        local function pdesc(t)
            if type(t) ~= "table" then return "none" end
            local parts = {}
            for k, v in pairs(t) do if type(v) ~= "table" then table.insert(parts, k .. "=" .. tostring(v)) end end
            table.sort(parts)
            return table.concat(parts, " ")
        end
        Log("Clone pretender BEFORE: " .. pdesc(serialize(pctx, 0)) .. " | target: " .. pdesc(c.pretender))
        if c.pretender and pctx then deserialize(pctx, c.pretender, 0) end
        local bh, bt = write_edit_values(getf(getf(ps, "_BodyEditor"), "_BodyEditContext"), c.body)
        local fh, ft = write_edit_values(getf(getf(ps, "_FaceEditor"), "_Context"), c.face)
        Log(string.format("Clone sculpt: body %d/%d values matched, face %d/%d", bh, bt, fh, ft))
        local head_hits = "no head"
        pcall(function()
            local hgo = character:call("get_GameObject"):call("getComponent(System.Type)", sdk.typeof("via.Transform")):call("find", "head"):call("get_GameObject")
            local hfe = hgo:call("getComponent(System.Type)", sdk.typeof("app.FaceEditor"))
            Log("Clone face BEFORE write: head context " .. count_matching(getf(hfe, "_Context"), c.face, "get_EditValues")
                .. ", head live editor " .. count_matching(hfe, c.face, "getEditValues()")
                .. ", swapper context " .. count_matching(getf(getf(ps, "_FaceEditor"), "_Context"), c.face, "get_EditValues"))
        end)
        pcall(function()
            local head_go = character:call("get_GameObject"):call("getComponent(System.Type)", sdk.typeof("via.Transform")):call("find", "head"):call("get_GameObject")
            local head_fe = head_go:call("getComponent(System.Type)", sdk.typeof("app.FaceEditor"))
            local hh, ht = write_edit_values(getf(head_fe, "_Context"), c.face)
            head_hits = hh .. "/" .. ht
        end)
        Log("Clone head face context: " .. head_hits .. " values written (shows after a reload)")

        ps:call("requestSwap(app.PartSwapper.Parts)", 0x200000 | 0x400000 | 0x800000 | 0x2 | 0x8 | 2093056)
        clone_hair_fix[ps:get_address()] = {ps = ps, at = os.clock() + 4.0, landed = false}
    end)    if not ok then Log("Clone apply failed: " .. tostring(err)) return "Clone failed: " .. tostring(err) end
    Log("Applied full appearance clone (full look shows after a reload)")
    return "Clone applied"
end

end

local confirm_state = nil

local function ask_confirm(title, text, fn, note)
    confirm_state = {title = title, text = text, fn = fn, note = note}
end

re.on_frame(function()
    if not confirm_state then return end
    local still = imgui.begin_window(confirm_state.title .. "###tpc_confirm", true, 64)
    imgui.text_colored("This can't be undone in-game.", 0xFF3399FF)
    imgui.spacing()
    imgui.text(confirm_state.text)
    if confirm_state.note then
        imgui.spacing()
        imgui.text_colored(confirm_state.note, 0xFF33AAFF)
    end
    imgui.spacing()
    if imgui.button("Confirm##tpcc") then
        local fn = confirm_state.fn
        confirm_state = nil
        local ok, err = pcall(fn)
        if not ok then Log("Confirmed action failed: " .. tostring(err)) end
    end
    imgui.same_line()
    if imgui.button("Cancel##tpcx") then confirm_state = nil end
    imgui.end_window()
    if still == false then confirm_state = nil end
end)

local function default_qol()
    return {godmode = false, inf_stamina = false, cannot_die = false, instant_revive = false, damage_mult = 1.0,
        light_load = false, lantern = false, scale = 1.0, return_after_rest = false}
end

local qol_sets = {god = {}, dmg = {}, stamina = {}, light = {}, light_chara = {}, light_cid = {}, lantern = {}, keep = {}, keep_id = {}}
local lost_kept = {}
local tp_queue = {}

local function hook_named(type_name, method_name, pre, post)
    local td = sdk.find_type_definition(type_name)
    if not td then return 0 end
    local n = 0
    for _, m in ipairs(td:get_methods()) do
        if m:get_name() == method_name then
            sdk.hook(m, pre, post)
            n = n + 1
        end
    end
    return n
end

local function hit_of(chara)
    local ok, hc = pcall(function() return chara:call("get_Hit") end)
    return ok and hc or nil
end

local function full_heal(chara)
    pcall(function() hit_of(chara):call("recoverHpAndMaxHpCompletely", false) end)
    pcall(function() chara:call("get_StatusConditionCtrl"):call("reqStatusConditionCureAll()") end)
    pcall(function() chara:call("get_StaminaManager"):call("recoverRemainingAmountAndMaxValueCompletely") end)
end


lazy_hooks.god = function()
    return hook_named("app.HitController", "damageProc", function(args)
        local st = thread.get_hook_storage()
        st.god = qol_sets.god[sdk.to_int64(args[2])] == true
        if st.god then return sdk.PreHookResult.SKIP_ORIGINAL end
    end, function(retval)
        if thread.get_hook_storage().god then return sdk.to_ptr(0) end
        return retval
    end)
end

lazy_hooks.dmg = function()
    return hook_named("app.HitController", "calcDamageValue", function(args)
        thread.get_hook_storage().info = args[3]
    end, function(retval)
        local p = thread.get_hook_storage().info
        if p and next(qol_sets.dmg) then
            pcall(function()
                local info = sdk.to_managed_object(p)
                local atk = info:call("get_AttackOwnerHitController")
                local mult = atk and qol_sets.dmg[atk:get_address()]
                if mult then info:set_field("Damage", (info:get_field("Damage") or 0) * mult) end
            end)
        end
        return retval
    end)
end

lazy_hooks.stamina = function()
    return hook_named("app.StaminaManager", "add", function(args)
        if qol_sets.stamina[sdk.to_int64(args[2])] and sdk.to_float(args[3]) < 0 then
            return sdk.PreHookResult.SKIP_ORIGINAL
        end
    end, nil)
end

lazy_hooks.light = function()
    local n = hook_named("app.Human", "calcWeightRank", function(args)
        thread.get_hook_storage().light = qol_sets.light[sdk.to_int64(args[2])] == true
    end, function(retval)
        if thread.get_hook_storage().light then return sdk.to_ptr(1) end
        return retval
    end)
    n = n + hook_named("app.Human", "isWeightOver", function(args)
        thread.get_hook_storage().light = qol_sets.light[sdk.to_int64(args[2])] == true
    end, function(retval)
        if thread.get_hook_storage().light then return sdk.to_ptr(0) end
        return retval
    end)
    local im = sdk.find_type_definition("app.ItemManager")
    local function rank_hook(sig, is_light)
        local m = im and im:get_method(sig)
        if not m then return 0 end
        sdk.hook(m, function(args)
            local ok, l = pcall(is_light, args)
            thread.get_hook_storage().light = ok and l == true
        end, function(retval)
            if thread.get_hook_storage().light then
                local cur = sdk.to_int64(retval) & 0xFF
                if cur > 1 then return sdk.to_ptr(1) end
            end
            return retval
        end)
        return 1
    end
    n = n + rank_hook("getWeightRank(System.Single, System.Single, app.Character)", function(args)
        return qol_sets.light_chara[sdk.to_int64(args[5])] == true
    end)
    n = n + rank_hook("getWeightRank(System.Single, System.Single, app.CharacterID, app.IEquipStorageDataGetter)", function(args)
        return qol_sets.light_cid[sdk.to_int64(args[5]) & 0xFFFFFFFF] == true
    end)
    return n
end

lazy_hooks.lantern = function()
    return hook_named("app.HumanLanternController", "consumeOil", function(args)
        if qol_sets.lantern[sdk.to_int64(args[2])] then return sdk.PreHookResult.SKIP_ORIGINAL end
    end, nil)
end

do
    local hooks = 0
    hooks = hooks + hook_named("app.PawnManager", "lost", function(args)
        local id = tostring(sdk.to_int64(args[3]) & 0xFFFFFFFF)
        local k = lost_kept[id]
        if k then
            if k.pass then
                lost_kept[id] = nil
                return
            end
            if os.clock() - k.at < (k.window or 10) then
                k.repeats = (k.repeats or 0) + 1
                if k.repeats == 1 then Log("Lost: " .. id .. " is being revived, swallowing the game's repeat calls") end
                return sdk.PreHookResult.SKIP_ORIGINAL
            end
            lost_kept[id] = nil
        end
        if not qol_sets.keep_id[id] then return end
        local chara, slot
        for _, j in ipairs(SLOT_IDS) do
            if j > 0 then pcall(function()
                local c = get_character(get_hired_pawn(j))
                if c and tostring(math.tointeger(c.CharacterID) & 0xFFFFFFFF) == id then chara, slot = c, j end
            end) end
        end
        if not chara then return end
        local dead_now = false
        pcall(function() dead_now = chara:call("get_IsDead") == true end)
        if not dead_now then return end
        lost_kept[id] = {at = os.clock()}
        table.insert(game_jobs, function()
            pcall(function() PawnManager:call("resetPawnLostTimer(app.Character)", chara) end)
            pcall(function() chara:call("reviveFromFallDead(System.Boolean)", true) end)
            local still = true
            pcall(function() still = chara:call("get_IsDead") == true end)
            if still then
                pcall(function()
                    local pawn = PawnManager:call("getPartyPawn(app.Character, System.Boolean)", chara, false)
                    pawn:call("set_IsReviveWithoutTalk", true)
                    pawn:call("setPawnRevive(System.Single, System.Boolean, System.Boolean)", 1.0, true, false)
                end)
                pcall(function() still = chara:call("get_IsDead") == true end)
            end
            full_heal(chara)
            Log(slot_label(slot) .. " (" .. id .. ") " .. (still and "could not be revived, letting the game handle it next time" or "revived instead of going back to the Rift"))
            if still then lost_kept[id] = {at = os.clock(), pass = true}
            else lost_kept[id] = {at = os.clock(), window = 3} end
        end)
        return sdk.PreHookResult.SKIP_ORIGINAL
    end, nil)
    Log("QoL hooks installed: " .. hooks)
end

local KNOWLEDGE = {
    {key = "quest", label = "Quest Guidance", methods = {"checkQuestKnowledge"}},
    {key = "way", label = "Route Directions",
        methods = {"checkWayKnowledge", "checkKeyLocationKnowledge", "checkNRDKeyLocationKnowledge", "checkContents014Knowledge"}},
    {key = "shortcut", label = "Route Shortcuts", methods = {"checkShortcutWayKnowledge"}},
    {key = "gimmick", label = "Gimmicks", tip = "chest, lever, door locations etc", methods = {"checkGimmickKnowledge", "checkNRDGimmickKnowledge"}},
}
local KNOW_MODES = {"Default", "Always", "Never"}
local knowledge_map = {}
local ptr_true, ptr_false = sdk.to_ptr(1), sdk.to_ptr(0)

lazy_hooks.knowledge = function()
    local n = 0
    for _, k in ipairs(KNOWLEDGE) do
        for _, mname in ipairs(k.methods) do
            n = n + hook_named("app.PawnKnowledgeContext", mname, function(args)
                local st = thread.get_hook_storage()
                local cfgk = knowledge_map[sdk.to_int64(args[2])]
                st.know = cfgk and cfgk[k.key] or 0
            end, function(retval)
                local mode = thread.get_hook_storage().know
                if mode == 1 then return ptr_true end
                if mode == 2 then return ptr_false end
                return retval
            end)
        end
    end
    return n
end

local KnowledgeType = sdk.typeof("app.PawnKnowledgeContext")
local function knowledge_ctx(chara)
    local ok, ctx = pcall(function()
        return chara:call("get_Context"):get_field("Contexts")[KnowledgeType]:call("get_CurrentContext")
    end)
    return ok and ctx or nil
end

local KNOW_FIELDS = {
    quest = {"_QuestKnowledge01", "_QuestKnowledge02", "_QuestKnowledge03", "_QuestKnowledge04"},
    way = {"_KeyLocationFlag01", "_KeyLocationFlag02", "_KeyLocationFlag03", "_KeyLocationFlag04"},
    shortcut = {"_ShortcutFlag01"},
    gimmick = {"_GimmickFlag01", "_GimmickFlag02", "_GimmickFlag03"},
}

local function norm_flag(v)
    if math.type(v) == "integer" and v < 0 and v >= -2147483648 then return v & 0xFFFFFFFF end
    return v
end

local know_members = {}
local function flag_members(ctx, fname)
    if know_members[fname] then return know_members[fname] end
    local list = {}
    pcall(function()
        local ft = ctx:get_type_definition():get_field(fname):get_type()
        for _, fld in ipairs(ft:get_fields()) do
            if fld:is_static() then
                local ok, v = pcall(function() return fld:get_data(nil) end)
                v = ok and norm_flag(v) or nil
                if math.type(v) == "integer" and v ~= 0 and (v & (v - 1)) == 0 then
                    table.insert(list, {name = fld:get_name(), value = v})
                end
            end
        end
    end)
    if #list > 0 then know_members[fname] = list end
    return list
end

local function know_raw(ctx)
    local out = {}
    if not ctx then return nil end
    for _, list in pairs(KNOW_FIELDS) do
        for _, fname in ipairs(list) do
            pcall(function() out[fname] = norm_flag(ctx:get_field(fname)) end)
        end
    end
    return out
end

local function know_count(ctx, key)
    local have, total = 0, 0
    for _, fname in ipairs(KNOW_FIELDS[key]) do
        local cur = norm_flag(ctx:get_field(fname)) or 0
        for _, m in ipairs(flag_members(ctx, fname)) do
            total = total + 1
            if cur & m.value ~= 0 then have = have + 1 end
        end
    end
    return have, total
end

local function know_set_all(ctx, key, on)
    for _, fname in ipairs(KNOW_FIELDS[key]) do
        local v = 0
        if on then for _, m in ipairs(flag_members(ctx, fname)) do v = v | m.value end end
        pcall(function() ctx:set_field(fname, v) end)
    end
end

local pending_posture = {}
re.on_frame(function()
    if not next(pending_posture) then return end
    local now = os.clock()
    for addr, q in pairs(pending_posture) do
        if now >= q.at then
            pending_posture[addr] = nil
            local dead = false
            pcall(function() dead = q.chara:call("get_IsDead") or q.chara:call("get_IsFallDead") end)
            Log("Kill: requestFallDead sent, dead now: " .. tostring(dead))
        end
    end
end)

local function kill_character(chara)
    local ok, err = pcall(function()
        local hc = chara:call("get_Hit")
        pcall(function() hc:call("set_IsNoDie", false) hc:call("set_IsInvincible", false) end)
        chara:call("requestFallDead")
    end)
    if not ok then Log("Kill failed: " .. tostring(err)) return end
    pending_posture[chara:get_address()] = {chara = chara, at = os.clock() + 0.1}
end

local function run_teleport(chara, entry)
    local ok, err = pcall(function()
        local player = sdk.get_managed_singleton("app.CharacterManager"):call("get_ManualPlayer")
        local tf = player:call("get_GameObject"):call("get_Transform")
        local rot = tf:call("get_Rotation")
        local p = tf:call("get_Position")
        local dx, dz = 0, 0
        pcall(function()
            local fwd = tf:call("get_AxisZ")
            dx, dz = -fwd.x * 1.5, -fwd.z * 1.5
        end)
        local dest = Vector3f.new(p.x + dx, p.y, p.z + dz)
        local function vstr(v)
            local ok2, s = pcall(function() return string.format("%.1f,%.1f,%.1f", v.x, v.y, v.z) end)
            return ok2 and s or "?"
        end
        local ptf = chara:call("get_GameObject"):call("get_Transform")
        local before = ptf:call("get_Position")
        local opt, opt_src = nil, "static"
        pcall(function() opt = sdk.find_type_definition("app.CharacterWarpOption"):get_field("ResetPosRotContext"):get_data(nil) end)
        if not opt then
            opt_src = "new"
            opt = sdk.create_instance("app.CharacterWarpOption")
            pcall(function() opt:call(".ctor") end)
            opt = opt:add_ref()
        end
        local pre = {}
        local rbs = 0
        pcall(function()
            local list = chara:get_field("AllRagdollForPushRigidBody")
            local n = list:call("get_Count")
            for i = 0, n - 1 do
                if pcall(function() list:call("get_Item", i):call("onCharacterTeleportBeforeStart") end) then rbs = rbs + 1 end
            end
        end)
        if rbs == 0 then
            if pcall(function() chara:call("get_RagdollForPushRigidBody"):call("onCharacterTeleportBeforeStart") end) then rbs = 1 end
        end
        table.insert(pre, "ragdoll x" .. rbs)
        table.insert(pre, pcall(function()
            chara:call("get_AnimationController"):get_field("AnimationController"):call("onWarp")
        end) and "anim" or "anim!")
        local warped, werr = pcall(function()
            chara:call("warp(via.vec3, via.Quaternion, app.CharacterWarpOption)", dest, rot, opt)
        end)
        Log("Teleport[" .. entry .. "]: pre " .. table.concat(pre, ",") .. ", Character.warp " .. (warped and "ok" or ("failed " .. tostring(werr)))
            .. " (option " .. opt_src .. ") | body before " .. vstr(before) .. " after " .. vstr(ptf:call("get_Position"))
            .. " dest " .. vstr(dest))
    end)
    if not ok then Log("Teleport failed: " .. tostring(err)) end
end

local function drain_tp_queue(entry)
    if #game_jobs > 0 then
        local jobs = game_jobs
        game_jobs = {}
        for _, fn in ipairs(jobs) do
            local okJ, errJ = pcall(fn)
            if not okJ then Log("Game thread job failed: " .. tostring(errJ)) end
        end
    end
    if #tp_queue == 0 then return end
    local q = tp_queue
    tp_queue = {}
    for _, chara in ipairs(q) do run_teleport(chara, entry) end
end

re.on_pre_application_entry("UpdateBehavior", function() drain_tp_queue("UpdateBehavior") end)
re.on_pre_application_entry("LateUpdateBehavior", function() drain_tp_queue("LateUpdateBehavior") end)

local function teleport_to_player(chara)
    for _, c in ipairs(tp_queue) do if c == chara then return end end
    table.insert(tp_queue, chara)
    Log("Teleport queued for the game thread")
end
local qol_prev = {}
local qol_cool = {}

local function apply_qol_to(key, chara, human, pawn, q, is_player)
    if not (chara and q) then return end
    local hc = hit_of(chara)
    local prev = qol_prev[key] or {}
    local now = os.clock()
    local cool = qol_cool[key] or {}
    qol_cool[key] = cool

    if hc then
        if q.godmode then
            need_hooks("god")
            qol_sets.god[hc:get_address()] = true
            pcall(function() hc:call("set_IsInvincible", true) hc:call("set_IsNoDie", true) end)
            pcall(function() chara:call("set_IsImmortality", true) end)
            if (cool.heal or 0) < now then
                cool.heal = now + 1.0
                pcall(function() hc:call("recoverHpAndMaxHpCompletely", false) end)
            end
        elseif prev.godmode then
            pcall(function() hc:call("set_IsInvincible", false) end)
            pcall(function() chara:call("set_IsImmortality", false) end)
            if not q.cannot_die then pcall(function() hc:call("set_IsNoDie", false) end) end
        end

        if q.cannot_die then
            pcall(function() hc:call("set_IsNoDie", true) end)
        elseif prev.cannot_die and not q.godmode then
            pcall(function() hc:call("set_IsNoDie", false) end)
        end

        if q.instant_revive then
            if pawn and (cool.revive or 0) < now then
                local dead = false
                pcall(function() dead = pawn:get_field("DeadStatus") == true or chara:call("get_IsDead") == true end)
                if dead then
                    cool.revive = now + 3.0
                    pcall(function() chara:call("reviveFromFallDead(System.Boolean)", true) end)
                    local still = true
                    pcall(function() still = chara:call("get_IsDead") == true end)
                    if still then
                        pcall(function() pawn:call("set_IsReviveWithoutTalk", true) end)
                        pcall(function() pawn:call("setPawnRevive(System.Single, System.Boolean, System.Boolean)", 1.0, true, false) end)
                    end
                    full_heal(chara)
                    local up = false
                    pcall(function() up = chara:call("get_IsDead") ~= true end)
                    Log("Instant revive: " .. (up and "back on their feet" or "still down, revive fallback used") .. " (" .. key .. ")")
                end
            end
        end

        local mult = q.damage_mult or 1.0
        if math.abs(mult - 1.0) > 0.001 then
            need_hooks("dmg")
            qol_sets.dmg[hc:get_address()] = mult
        end
    end

    if q.inf_stamina then
        pcall(function()
            local sm = chara:call("get_StaminaManager")
            need_hooks("stamina")
            qol_sets.stamina[sm:get_address()] = true
            sm:call("recoverRemainingAmountAndMaxValueCompletely")
        end)
    end

    if q.light_load and human then
        need_hooks("light")
        qol_sets.light[human:get_address()] = true
        qol_sets.light_chara[chara:get_address()] = true
        pcall(function() qol_sets.light_cid[math.tointeger(chara.CharacterID) & 0xFFFFFFFF] = true end)
    end

    local slot_no = tonumber((key:match("^slot(%d+)$")))
    if q.return_after_rest and slot_no and slot_no > 0 then
        qol_sets.keep[chara:get_address()] = slot_no
        pcall(function() qol_sets.keep_id[tostring(chara.CharacterID & 0xFFFFFFFF)] = slot_no end)
    end

    if q.lantern and human then
        pcall(function()
            local lc = human:call("get_LanternCtrl")
            need_hooks("lantern")
            qol_sets.lantern[lc:get_address()] = true
            if (cool.lantern or 0) < now and lc:call("hasEnableLantern") and not lc:call("get_IsLanternOn") then
                cool.lantern = now + 2.0
                if is_player then
                    human:call("get_HumanActionSelector"):call("requestToggleLanternAction")
                else
                    PawnManager:call("useLantern", chara)
                end
            end
        end)
    end

    local scale = q.scale or 1.0
    if math.abs(scale - 1.0) > 0.001 or (prev.scale and math.abs(prev.scale - 1.0) > 0.001) then
        pcall(function()
            local sm = chara:call("get_ScaleMediator")
            sm:call("setLocalScale", 2, Vector3f.new(scale, scale, scale))
            sm:call("applyLocalScale")
        end)
    end

    qol_prev[key] = deep_copy(q)
end

local last_qol = 0
local function update_qol(get_pawn, get_player_fn)
    local now = os.clock()
    if now - last_qol < 0.25 then return end
    last_qol = now
    qol_sets = {god = {}, dmg = {}, stamina = {}, light = {}, light_chara = {}, light_cid = {}, lantern = {}, keep = {}, keep_id = {}}
    knowledge_map = {}
    for _, i in ipairs(SLOT_IDS) do
        local pcfg = cfg["pawn" .. i]
        if pcfg.enabled then
            local pawn = get_pawn(i)
            local chara = get_character(pawn)
            local kctx = chara and knowledge_ctx(chara)
            if kctx then
                for _, mode in pairs(pcfg.knowledge) do
                    if mode ~= 0 then need_hooks("knowledge") break end
                end
                knowledge_map[kctx:get_address()] = pcfg.knowledge
            end
            if chara then apply_qol_to("slot" .. i, chara, get_human(pawn), pawn, pcfg.qol, false) end
        end
    end
    local player = get_player_fn()
    if player then
        local human
        pcall(function() human = player:call("get_Human") end)
        apply_qol_to("player", player, human, nil, cfg.player_qol, true)
    end
end

local function draw_qol(key, q, chara, allow_pawn_actions, confirm_fn, is_hired, parked_slot)
    local c, v
    imgui.set_next_item_width(220)
    c, v = UI.slider((allow_pawn_actions and "Pawn" or "Arisen") .. " size multiplier##scale" .. key, q.scale or 1.0, 0.25, 3.0, "%.2fx", 1.0)
    if c then q.scale = v config_changed = true end
    imgui.same_line()
    if imgui.button("Reset##scr" .. key) then q.scale = 1.0 config_changed = true end
    imgui.separator()

    imgui.text("Survival")
    c, v = UI.cb("Godmode (ignores damage)##god" .. key, q.godmode) if c then q.godmode = v config_changed = true end
    c, v = UI.cb("Cannot die##cd" .. key, q.cannot_die) if c then q.cannot_die = v config_changed = true end
    if allow_pawn_actions then
        c, v = UI.cb("Instant revive##ir" .. key, q.instant_revive) if c then q.instant_revive = v config_changed = true end
    end
    c, v = UI.cb("Infinite stamina##stam" .. key, q.inf_stamina) if c then q.inf_stamina = v config_changed = true end
    c, v = UI.cb("Infinite carry weight##light" .. key, q.light_load) if c then q.light_load = v config_changed = true end
    if is_hired then
        c, v = UI.cb("Respawn pawn shortly after death##rar" .. key, q.return_after_rest)
        if c then q.return_after_rest = v config_changed = true end
    end

    imgui.spacing()
    imgui.text("Power")
    imgui.set_next_item_width(220)
    c, v = UI.slider("Damage multiplier##dmg" .. key, q.damage_mult or 1.0, 0.0, 100.0, "%.1fx", 1.0)
    if c then q.damage_mult = v config_changed = true end
    if imgui.button("Fish 0x##f" .. key) then q.damage_mult = 0.0 config_changed = true end
    imgui.same_line()
    if imgui.button("Normal 1x##n" .. key) then q.damage_mult = 1.0 config_changed = true end
    imgui.same_line()
    if imgui.button("Comet 100x##c" .. key) then q.damage_mult = 100.0 config_changed = true end

    imgui.spacing()
    imgui.text("Utility")
    c, v = UI.cb("Lantern always lit (no oil used)##lan" .. key, q.lantern) if c then q.lantern = v config_changed = true end
    if chara then
        if imgui.button("Full heal##heal" .. key) then full_heal(chara) end
        if allow_pawn_actions then
            imgui.same_line()
            if imgui.button("Teleport to me##tp" .. key) then teleport_to_player(chara) end
            imgui.same_line()
            if imgui.button("Kill##kill" .. key) then
                if confirm_fn then confirm_fn(function() kill_character(chara) end) else kill_character(chara) end
            end
        end
    end
end

local function snapshot_pawn(pawn)
    local character = get_character(pawn)
    local human = get_human(pawn)
    if not (character and human) then return nil end

    local snap = default_pawn_config()
    snap.enabled = true
    for _, s in ipairs(SLOTS) do
        local sd = get_slot_item(character, SlotEnum[s])
        snap.equipment[s] = sd and sd._ItemId or 0
        if snap.equipment[s] > 0 then
            snap.names = snap.names or {}
            pcall(function() snap.names[s] = clean_text(ItemManager:getItemData(snap.equipment[s]):call("get_Name")) end)
        end
    end
    for _, s in ipairs(ENHANCE_SLOTS) do
        local sd = get_slot_item(character, SlotEnum[s])
        pcall(function()
            if not sd or sd._ItemId == 0 then return end
            local n = sd:call("get_EnhanceNum") or 0
            local e = sd._Enhance
            local t = {e._Type0, e._Type1, e._Type2}
            local steps = {0, 0, 0}
            for k = 1, math.min(n, 3) do steps[k] = (t[k] or 0) + 1 end
            snap.enhance[s] = {enabled = true, steps = steps, dragon = n >= 4, exact = true}
        end)
    end
    local job = current_job(human)
    if job then
        snap.job = job
        pcall(function() snap.job_rank = human:call("get_JobContext"):call("calcJobRank", job) or 0 end)
        pcall(function()
            local sc = human:call("get_SkillContext")
            for slot = 1, SKILL_SLOTS do snap.skills[slot] = sc:call("getSkillID", job, slot - 1) or 0 end
        end)
        pcall(function()
            local ac = human:call("get_AbilityContext")
            for slot = 1, ABILITY_SLOTS do snap.abilities[slot] = ac:call("getAbility", job, slot - 1) or 0 end
            snap.extra_aug = ac:get_field("IsAdditionalSlotUnlocked") == true or nil
        end)
    end
    pcall(function()
        local sc = human:call("get_SkillContext")
        for _, it in ipairs(Lists.core) do
            if sc:call("isNormalSkillEnable", it.id) then snap.core[tostring(it.id)] = true end
        end
    end)
    local ctx = get_data_context(character)
    if not ctx then pcall(function() ctx = human:call("get_PawnDataContext") end) end
    if ctx then
        pcall(function()
            snap.personality = ctx:get_Personality()
            snap.specialization = ctx:call("get_SubSkill")
            snap.voice_gender = ctx:get_VoiceGender()
            snap.voice_tone = ctx:get_VoiceToneType()
        end)
        snap.name = ctx_name(ctx) or ""
        pcall(function() snap.nickname = ctx:call("get_Nickname") end)
        pcall(function()
            snap.possession = {lv = ctx:call("get_PossessionLv") or 0, pts = ctx:call("get_PossessionProgressPoint") or 0}
        end)
    end
    snap.eq_sid = EqSkill.snapshot(character)
    snap.status = snapshot_status(human)
    snap.clone = capture_clone(character)
    snap.knowledge_raw = know_raw(knowledge_ctx(character))
    return snap, ctx
end

local function id_key(id)
    local ok, k = pcall(function() return tostring(math.tointeger(id) & 0xFFFFFFFF) end)
    return ok and k or nil
end

local function search_id(character)
    local ok, sid = pcall(function() return get_data_context(character):call("get_SearchId") end)
    return (ok and type(sid) == "string" and sid ~= "") and sid or nil
end

local snap_checked = {}
local snap_retry = {}
local function ensure_original(i, pawn)
    if snap_checked[i] or os.clock() < (snap_retry[i] or 0) then return end
    local character = get_character(pawn)
    if not (is_ready(character) and get_data_context(character)) then return end
    local k = id_key(character.CharacterID)
    if not k then return end
    local o = cfg.originals["slot" .. i]
    if o and o.key == k then
        if o.chara_id ~= k then o.chara_id = k config_changed = true end
        snap_checked[i] = true
        pcall(function()
            local d, pcfg, human = o.data, cfg["pawn" .. i], get_human(pawn)
            if d and d.nickname == nil and not pcfg.name_moniker then
                pcall(function() d.nickname = get_data_context(get_character(pawn)):call("get_Nickname") end)
                if d.nickname then config_changed = true end
            end
            if d and type(d.core) ~= "table" and human then
                pcall(function()
                    local list = human:call("get_SkillContext"):get_field("EnableNormalSkills")
                    local ticked = type(pcfg.core) == "table" and pcfg.core or {}
                    local core = {}
                    for n = 0, list:call("get_Count") - 1 do
                        local it = list:call("get_Item", n)
                        local id = it:get_field("NormalSkillID")
                        if type(id) ~= "number" then id = tonumber(id:get_field("value__")) end
                        if id and it:get_field("IsEnable") == true and not ticked[tostring(id)] then core[tostring(id)] = true end
                    end
                    d.core = core
                    config_changed = true
                end)
            end
            local job = human and current_job(human)
            if not (d and job and d.job == job) then return end
            local function n_of(v) if type(v) == "number" then return v end return tonumber(v:get_field("value__")) or 0 end
            local filled = 0
            d.skills = type(d.skills) == "table" and d.skills or {}
            local sc = human:call("get_SkillContext")
            local sb = type(pcfg.skills_base) == "table" and pcfg.skills_base.job == job and type(pcfg.skills_base.row) == "table" and pcfg.skills_base.row or nil
            for s = 1, SKILL_SLOTS do
                if d.skills[s] == nil and sb and sb[s] ~= nil then
                    d.skills[s] = sb[s] filled = filled + 1
                elseif d.skills[s] == nil and not sb and (pcfg.skills[s] or 0) == 0 and not (pcfg.skills_set and pcfg.skills_set[tostring(s)]) then
                    d.skills[s] = n_of(sc:call("getSkillID", job, s - 1)) filled = filled + 1
                end
            end
            d.abilities = type(d.abilities) == "table" and d.abilities or {}
            local ac = human:call("get_AbilityContext")
            local ab = type(pcfg.abilities_base) == "table" and pcfg.abilities_base.job == job and type(pcfg.abilities_base.row) == "table" and pcfg.abilities_base.row or nil
            for s = 1, ABILITY_SLOTS do
                if d.abilities[s] == nil and ab and ab[s] ~= nil then
                    d.abilities[s] = ab[s] filled = filled + 1
                elseif d.abilities[s] == nil and not ab and (pcfg.abilities[s] or 0) == 0 and not (pcfg.abilities_set and pcfg.abilities_set[tostring(s)]) then
                    d.abilities[s] = n_of(ac:call("getAbility", job, s - 1)) filled = filled + 1
                end
            end
            if filled > 0 then
                config_changed = true
                Log(slot_label(i) .. ": filled in " .. filled .. " skill/augment slot(s) missing from an older original")
            end
        end)
        return
    end
    local ok, snap = pcall(snapshot_pawn, pawn)
    if ok and snap then
        cfg.originals["slot" .. i] = {key = k, chara_id = k, data = snap, prefs = Lists.pending_prefs[i]}
        Lists.pending_prefs[i] = nil
        snap_checked[i] = true
        save_config()
        Log("Saved original state of " .. tostring(snap.name) .. " (" .. slot_label(i) .. ")")
    else
        snap_retry[i] = os.clock() + 2.0
    end
end

local live_items_next_try = 0
local modified = {[0] = false, [1] = false, [2] = false}
local last_ids = {}

local restore_pending = {}
local empty_since = {}
local empty_check = {}
local cur_key = {}

local function saved_party_has(cid)
    if not cid then return nil end
    local found, count = false, nil
    local ok = pcall(function()
        local list = PawnManager:call("get_SavedPartyPawnList")
        count = list:call("get_Count")
        for n = 0, count - 1 do
            local v = list:call("get_Item", n)
            if type(v) ~= "number" then error("unexpected saved party entry " .. type(v)) end
            if tostring(math.tointeger(v) & 0xFFFFFFFF) == cid then found = true end
        end
    end)
    if not ok or not count then return nil end
    return found
end

local function is_held(id)
    if not id then return false end
    local k = lost_kept[tostring(id)]
    return k ~= nil and os.clock() - k.at < 10
end

local function present_slot(own)
    if not own then return nil end
    for _, j in ipairs(SLOT_IDS) do if cur_key[j] == own then return j end end
    return nil
end

local slot_reset = {}

local function owner_of(i)
    local o = cfg.originals["slot" .. i]
    return cfg["pawn" .. i].owner or (o and o.key)
end

local function owner_cid(i)
    local own = owner_of(i)
    if own and not tostring(own):match("^%d+$") then
        local o = cfg.originals["slot" .. i]
        return o and o.chara_id or own
    end
    return own
end

local parked_cfg = {}

Lists.pending_prefs = {}

function Lists.depart(i)
    local pc = cfg["pawn" .. i]
    local own = owner_of(i)
    if not own or pc.preconfigured or not pc.enabled then return end
    local o = cfg.originals["slot" .. i]
    cfg.departed = type(cfg.departed) == "table" and cfg.departed or {}
    cfg.departed[tostring(own)] = {pcfg = pc, prefs = o and o.prefs or nil, at = os.time()}
    local keys = {}
    for k in pairs(cfg.departed) do keys[#keys + 1] = k end
    if #keys > 12 then
        table.sort(keys, function(a, b) return (cfg.departed[a].at or 0) < (cfg.departed[b].at or 0) end)
        for n = 1, #keys - 12 do cfg.departed[keys[n]] = nil end
    end
    config_changed = true
    Log(slot_label(i) .. ": kept the settings of the pawn that left, they come back if it's hired again")
end

function Lists.return_departed(key, sid)
    local d = type(cfg.departed) == "table" and cfg.departed or nil
    if not d then return nil end
    local hit = nil
    local kv = d[tostring(key)]
    if type(kv) == "table" and not (sid and type(kv.pcfg) == "table" and kv.pcfg.sid and kv.pcfg.sid ~= sid) then hit = tostring(key) end
    if not hit and sid then
        for k, v in pairs(d) do
            if type(v) == "table" and type(v.pcfg) == "table" and v.pcfg.sid == sid then hit = k break end
        end
    end
    if not hit then return nil end
    local back = d[hit]
    d[hit] = nil
    config_changed = true
    return back
end

local function reset_slot_state(i)
    modified[i] = false
    job_wait[i] = 0
    snap_checked[i] = false
    snap_retry[i] = nil
    restore_pending[i] = nil
    slot_reset[i] = true
end

function Lists.ensure_slots(upto)
    if not upto then
        upto = 2
        for n = 3, 8 do if type(cfg["pawn" .. n]) == "table" then upto = n end end
    end
    upto = math.min(math.tointeger(upto) or 2, 8)
    for n = 3, upto do
        if not SLOT_NAMES[n] then
            local k = "pawn" .. n
            local fresh = type(cfg[k]) ~= "table"
            cfg[k] = migrate_pawn(cfg[k] or {})
            if (cfg[k].job or 0) > MAX_PAWN_JOB then cfg[k].job = 0 end
            SLOT_NAMES[n] = "Hired Pawn " .. n
            modified[n], job_wait[n] = false, 0
            table.insert(SLOT_IDS, n)
            if fresh then
                config_changed = true
                Log("Party has a pawn in slot " .. n .. " (party size mod), added Hired Pawn " .. n)
            end
        end
    end
end
Lists.ensure_slots()

local function swap_slots(i, j)
    cfg["pawn" .. i], cfg["pawn" .. j] = cfg["pawn" .. j], cfg["pawn" .. i]
    cfg.originals["slot" .. i], cfg.originals["slot" .. j] = cfg.originals["slot" .. j], cfg.originals["slot" .. i]
    reset_slot_state(i)
    reset_slot_state(j)
    bound_cid[j] = nil
end

local function claim(i, key)
    local pk = "pawn" .. i
    cfg[pk].owner = key
    cfg[pk].preconfigured = nil
    local o = cfg.originals["slot" .. i]
    if o then o.key, o.chara_id = key, key end
    config_changed = true
end

local function bind_slot(i, key, sid, depth)
    depth = depth or 0
    local pk = "pawn" .. i
    local owner = owner_of(i)
    if owner == key or (sid and owner == sid) then
        local o = cfg.originals["slot" .. i]
        if cfg[pk].owner ~= key or (o and o.key ~= key) or cfg[pk].preconfigured then claim(i, key) end
        if sid and cfg[pk].sid ~= sid then cfg[pk].sid = sid config_changed = true end
        return
    end
    local oc = owner_cid(i)
    if i > 0 and depth < 3 then
        for _, j in ipairs(SLOT_IDS) do
            if j > 0 and j ~= i then
                local oj = owner_of(j)
                if oj == key or (sid and oj == sid) then
                    swap_slots(i, j)
                    claim(i, key)
                    save_config()
                    Log("Pawn moved from " .. slot_label(j) .. " to " .. slot_label(i) .. ", its settings moved with it")
                    return
                end
            end
        end
        local j = present_slot(oc)
        if j and j > 0 and j ~= i then
            swap_slots(i, j)
            save_config()
            Log(slot_label(i) .. "'s old settings belong to the pawn now in " .. slot_label(j) .. ", handed them over")
            return bind_slot(i, key, sid, depth + 1)
        end
    end
    if cfg[pk].preconfigured and (owner == nil or (not present_slot(oc) and not is_held(oc))) then
        if owner ~= nil then
            cfg.originals["slot" .. i] = nil
            reset_slot_state(i)
        end
        claim(i, key)
        cfg[pk].sid = sid
        Log(slot_label(i) .. ": settings made while the slot was empty now belong to this pawn")
        return
    end
    if i == 0 then
        if owner == nil then
            claim(0, key)
            Log("Main Pawn settings are now tied to this Main Pawn")
            return
        end
        cfg.main_stash = cfg.main_stash or {}
        cfg.main_stash[owner] = {pcfg = cfg.pawn0, orig = cfg.originals.slot0}
        local st = cfg.main_stash[key]
        cfg.main_stash[key] = nil
        cfg.pawn0 = st and migrate_pawn(st.pcfg) or default_pawn_config()
        cfg.pawn0.owner = key
        cfg.originals.slot0 = st and st.orig or nil
    else
        local back = parked_cfg[key]
        parked_cfg[key] = nil
        local dep = Lists.return_departed(key, sid)
        local held = back ~= nil
        back = back or dep
        if oc and is_held(oc) then
            parked_cfg[oc] = {pcfg = cfg[pk], orig = cfg.originals["slot" .. i]}
            Log(slot_label(i) .. ": parked the respawning pawn's settings until it comes back")
        end
        Lists.depart(i)
        cfg[pk] = back and migrate_pawn(back.pcfg) or default_pawn_config()
        cfg[pk].owner = key
        cfg[pk].sid = sid
        if held then
            cfg.originals["slot" .. i] = back.orig
            if back.orig then back.orig.key, back.orig.chara_id = key, key end
        else
            cfg.originals["slot" .. i] = nil
            if back then
                Lists.pending_prefs[i] = back.prefs
                if (cfg[pk].level_keep or 0) > 0 then cfg[pk].level = cfg[pk].level_keep end
                if type(cfg[pk].clone_keep) == "table" then cfg[pk].clone = deep_copy(cfg[pk].clone_keep) end
            end
        end
        if back then
            reset_slot_state(i)
            save_config()
            Log(slot_label(i) .. ": this pawn was here before, its settings are back")
            return
        end
    end
    reset_slot_state(i)
    save_config()
    Log(slot_label(i) .. " has a different pawn now, "
        .. (i == 0 and "switched to that Main Pawn's settings" or "the previous pawn's settings were removed"))
end

local RESTORE_PARTS = {"vocation", "equipment", "skills", "augments", "attributes", "name", "plague", "appearance", "knowledge"}

local function clear_override(pcfg, part)
    local d = default_pawn_config()
    if part == "vocation" then
        pcfg.job, pcfg.job_rank, pcfg.level = 0, 0, 0
    elseif part == "equipment" then
        pcfg.equipment, pcfg.enhance, pcfg.eq_skills = d.equipment, d.enhance, d.eq_skills
    elseif part == "skills" then
        pcfg.skills = d.skills
    elseif part == "augments" then
        pcfg.abilities = d.abilities
    elseif part == "attributes" then
        pcfg.personality, pcfg.specialization = 0, -1
        pcfg.voice_gender, pcfg.voice_tone = 0, -1
    elseif part == "name" then
        pcfg.name = ""
    elseif part == "knowledge" then
        pcfg.knowledge = {quest = 0, way = 0, shortcut = 0, gimmick = 0}
    elseif part == "appearance" then
        pcfg.clone, pcfg.clone_keep = nil, nil
    elseif part == "plague" then
        pcfg.plague_immune = false
    elseif part:match("^equip:") then
        local slot = part:sub(7)
        pcfg.equipment[slot] = 0
        if d.enhance[slot] then pcfg.enhance[slot] = d.enhance[slot] end
        if d.eq_skills[slot] then pcfg.eq_skills[slot] = d.eq_skills[slot] end
    end
end

local function request_restore(i, parts)
    local pcfg = cfg["pawn" .. i]
    local set = restore_pending[i] or {}
    for _, p in ipairs(parts) do
        set[p] = true
        clear_override(pcfg, p)
    end
    restore_pending[i] = set
    job_wait[i] = 0
    config_changed = true
end

local function run_restore(i, pawn, character, human, parts)
    local snap = slot_original(i)
    if not snap then return true end
    if parts.vocation then
        if apply_job(i, human, snap.job) == "pending" then return false end
    end
    local job = current_job(human)
    if parts.equipment then
        apply_equipment(character, snap.equipment)
        apply_enhance(character, snap.enhance, snap.equipment)
        EqSkill.restore(character, snap, nil)
    end
    local eq, en, one_slot = {}, {}, false
    for _, s in ipairs(SLOTS) do
        if parts["equip:" .. s] then
            one_slot = true
            eq[s] = snap.equipment and snap.equipment[s] or 0
            if snap.enhance and snap.enhance[s] then en[s] = snap.enhance[s] end
        end
    end
    if one_slot then
        apply_equipment(character, eq)
        apply_enhance(character, en, eq)
        for s in pairs(eq) do EqSkill.restore(character, snap, s) end
    end
    if job then
        if parts.vocation then
            apply_job_rank(human, job, snap.job_rank)
            restore_status(human, snap.status)
            if i > 0 then Lists.lvl_next[i] = math.huge end
        end
        local pc = cfg["pawn" .. i]
        if parts.skills then apply_skills(human, job, snap, nil, true) pc.skills_base, pc.skills_set = nil, nil config_changed = true end
        if parts.augments then apply_abilities(human, job, snap, nil, nil, true) pc.abilities_base, pc.abilities_set = nil, nil config_changed = true end
    end
    local ctx = get_data_context(character)
    if ctx then
        if parts.attributes then
            local attrs = deep_copy(snap)
            attrs.name = ""
            apply_attributes(character, attrs, nil)
        end
        if parts.name then apply_name(ctx, {name = snap.name or ""}, nil, snap.nickname) end
        if parts.appearance and snap.clone then apply_clone(character, snap.clone) end
        if parts.knowledge and snap.knowledge_raw then
            local kctx = knowledge_ctx(character)
            if kctx then
                for fname, v in pairs(snap.knowledge_raw) do pcall(function() kctx:set_field(fname, v) end) end
            end
        end
        if parts.plague and snap.possession then
            pcall(function()
                ctx:call("setPossessionLv", snap.possession.lv)
                ctx:call("setPossessionProgressPoint", snap.possession.pts)
            end)
        end
    end
    local names = {}
    for _, p in ipairs(RESTORE_PARTS) do if parts[p] then table.insert(names, p) end end
    for _, s in ipairs(SLOTS) do if parts["equip:" .. s] then table.insert(names, s .. " slot") end end
    Log("Restored " .. table.concat(names, ", ") .. " for " .. slot_label(i))
    return true
end

local function apply_pawn(i)
    local pcfg = cfg["pawn" .. i]
    local parts = restore_pending[i]

    local pawn = get_hired_pawn(i)
    local character = get_character(pawn)
    if not is_ready(character) then return end
    local human = get_human(pawn)
    if not human then return end
    ensure_original(i, pawn)

    if parts then
        if run_restore(i, pawn, character, human, parts) then restore_pending[i] = nil end
        return
    end

    if not pcfg.enabled then modified[i] = false return end
    if modified[i] or not snap_checked[i] then return end

    local js = apply_job(i, human, pcfg.job)
    if js == "pending" then return end

    Log("Applying overrides to " .. slot_label(i))
    apply_equipment(character, pcfg.equipment)
    apply_enhance(character, pcfg.enhance, pcfg.equipment)
    EqSkill.apply(character, pcfg.eq_skills, pcfg.equipment, slot_original(i))
    local job = current_job(human)
    if job then
        apply_job_rank(human, job, pcfg.job_rank)
        if (pcfg.level or 0) > 0 then
            local target = pcfg.level
            local cur_now = 0
            pcall(function() cur_now = status_ctx(human):call("get_Level") or 0 end)
            if i > 0 and target < cur_now and target == pcfg.level_keep then
                Lists.lvl_next[i] = os.clock() + 5
                reset_level(human)
                table.insert(game_jobs, function() apply_level(human, target) end)
                Log(slot_label(i) .. ": level " .. cur_now .. " -> " .. target .. " (reset to 1, then levelled up)")
            else
                apply_level(human, target)
            end
            pcfg.level = 0
            config_changed = true
        end
        apply_skills(human, job, pcfg, learned_only(i))
        apply_abilities(human, job, pcfg, unlocked_aug_only(i), (slot_original(i) or {}).job)
    end
    if type(pcfg.core) == "table" and next(pcfg.core) then
        pcall(function()
            local sc = human:call("get_SkillContext")
            for k, on in pairs(pcfg.core) do
                local id = tonumber(k)
                if on and id and not sc:call("isNormalSkillEnable", id) then
                    sc:call("setNormalSkillEnable(app.HumanNormalSkillID)", id)
                    Log("Core skill " .. (name_of(Lists.core, id) or id) .. " unlocked on " .. slot_label(i)
                        .. (sc:call("isNormalSkillEnable", id) and "" or " (didn't stick)"))
                end
            end
        end)
    end
    local orig = slot_original(i)
    apply_attributes(character, pcfg, orig and orig.name, orig and orig.nickname)
    if pcfg.clone then
        local res = apply_clone(character, pcfg.clone)
        if res ~= "Clone needs the same gender and species" then
            if i > 0 then pcfg.clone_keep = pcfg.clone end
            pcfg.clone = nil
            config_changed = true
            save_config()
            Log("Clone applied once and cleared from overrides (the save keeps it)")
        end
    end
    modified[i] = true
end

Lists.lvl_next = {}
function Lists.hire_levelup(i, pawn)
    if os.clock() < (Lists.lvl_next[i] or 0) then return end
    Lists.lvl_next[i] = os.clock() + 1.0
    local h = get_human(pawn)
    local sc = h and status_ctx(h)
    if not sc then return end
    local ok, err = pcall(function()
        local lvi = h:call("get_Param"):call("get_LVupInfo")
        local lv, exp = sc:call("get_Level"), sc:call("get_Exp")
        if not (lv and exp) or lv <= 0 or exp <= 0 then return end
        local cap = max_level(h)
        local target, cost = lv, 0
        for _ = 1, 50 do
            if target >= cap then break end
            local need = lvi:call("getRequiredEXP", lv, target + 1) or 0
            if need <= 0 or need > exp then break end
            target, cost = target + 1, need
        end
        if target == lv then return end
        sc:call("levelup(System.Int32, System.Int32, app.Character.JobEnum, System.Single)", target, cost, current_job(h) or 1, 0.0)
        pcall(function() h:call("updateMaxHPAndStamina", false, 1) end)
        Log(slot_label(i) .. " levelled up from the EXP they earned: " .. lv .. " -> " .. tostring(sc:call("get_Level"))
            .. " (EXP left " .. tostring(sc:call("get_Exp")) .. ")")
    end)
    if not ok then Log(slot_label(i) .. ": level up from EXP failed: " .. tostring(err)) end
end

function Lists.exp_text(ss, cd)
    local chara = cd:get_field("_Chara")
    if not chara then return end
    local cid = chara.CharacterID
    local hire = false
    for _, j in ipairs(SLOT_IDS) do
        if j > 0 then
            local c = get_character(get_hired_pawn(j))
            if c and c.CharacterID == cid then hire = true end
        end
    end
    if not hire then return end
    local h = chara:call("get_Human")
    local sc = h and status_ctx(h)
    if not sc then return end
    local lv, exp = sc:call("get_Level"), sc:call("get_Exp")
    local cost = h:call("get_Param"):call("get_LVupInfo"):call("getRequiredEXP", lv, lv + 1)
    ss:get_field("TxtExpNow"):call("set_Message(System.String)", tostring(exp) .. "/")
    ss:get_field("TxtExpNext"):call("set_Message(System.String)", tostring(cost))
end
pcall(function()
    local m = sdk.find_type_definition("app.GUIBase.StatusInfoRef.StatusSet"):get_method("setup(app.GUIBase.CharaData)")
    sdk.hook(m, function(args)
        local s = thread.get_hook_storage()
        s.tpc_ss, s.tpc_cd = nil, nil
        if not cfg.hire_levelup then return end
        s.tpc_ss, s.tpc_cd = sdk.to_managed_object(args[2]), sdk.to_managed_object(args[3])
    end, function(retval)
        local s = thread.get_hook_storage()
        if s.tpc_ss and s.tpc_cd then pcall(Lists.exp_text, s.tpc_ss, s.tpc_cd) end
        s.tpc_ss, s.tpc_cd = nil, nil
        return retval
    end)
end)

local slot_p, slot_c, slot_id = {}, {}, {}

local Swap = {idle_since = {}, seen_at = {}, seen_key = {}, done = {}, party = {}}
function Swap.ready(i, c)
    local now = os.clock()
    local key = tostring(c:get_address())
    if Swap.seen_key[i] ~= key then
        Swap.seen_key[i], Swap.seen_at[i], Swap.idle_since[i], Swap.done[i] = key, now, nil, false
    end
    local busy = false
    pcall(function()
        local ps = c["<HumanPartSwapper>k__BackingField"]
        busy = ps:call("get_PartBeingSwapping") == true or ps:call("get_EquipmentBeingSwapping") == true
            or ps:call("get_BodyBeingSwapping") == true
    end)
    if busy then
        Swap.idle_since[i] = nil
        if not Swap.done[i] and now - Swap.seen_at[i] > 15 then
            Swap.done[i] = true
            Log(slot_label(i) .. ": parts still swapping after 15s, applying settings anyway")
            return true
        end
        return false
    end
    Swap.idle_since[i] = Swap.idle_since[i] or now
    if now - Swap.idle_since[i] < 1.0 then return false end
    Swap.done[i] = true
    return true
end

re.on_pre_application_entry("UpdateBehavior", function()
    frame_no = frame_no + 1
    get_hired_pawn(0)
    if (party_cache.max_id or 0) > #SLOT_IDS - 1 then Lists.ensure_slots(party_cache.max_id) end
    for _, i in ipairs(SLOT_IDS) do
        local pawn = get_hired_pawn(i)
        local c = get_character(pawn)
        local id = c and c.CharacterID or nil
        slot_p[i], slot_c[i], slot_id[i] = pawn, c, id
        if id ~= last_ids[i] then
            modified[i] = false
            job_wait[i] = 0
            snap_checked[i] = false
            bound_cid[i] = nil
            last_ids[i] = id
            Lists.lvl_next[i] = nil
            cur_key[i] = id and id_key(id) or nil
            if id then Log(slot_label(i) .. ": pawn loaded") end
        end
    end
    for _, i in ipairs(SLOT_IDS) do
        local pawn, c, id = slot_p[i], slot_c[i], slot_id[i]
        if pawn then
            if bound_cid[i] ~= id and cur_key[i] and is_ready(c) and get_data_context(c) then
                bind_slot(i, cur_key[i], search_id(c))
                bound_cid[i] = id
            end
            if bound_cid[i] == id then ensure_original(i, pawn) end
            empty_since[i] = nil
        elseif i > 0 and (cfg.originals["slot" .. i] or cfg["pawn" .. i].owner) and os.clock() >= (empty_check[i] or 0) then
            empty_check[i] = os.clock() + 1.0
            local in_game = false
            pcall(function() in_game = sdk.get_managed_singleton("app.CharacterManager"):call("get_ManualPlayer") ~= nil end)
            local own = owner_cid(i)
            if in_game and get_hired_pawn(0) ~= nil and saved_party_has(own) == false and not is_held(own) and not present_slot(own) then
                empty_since[i] = empty_since[i] or os.clock()
                if os.clock() - empty_since[i] > 10.0 then
                    Lists.depart(i)
                    cfg.originals["slot" .. i] = nil
                    if cfg["pawn" .. i].preconfigured then
                        cfg["pawn" .. i].owner = nil
                    else
                        cfg["pawn" .. i] = default_pawn_config()
                    end
                    reset_slot_state(i)
                    empty_since[i] = nil
                    save_config()
                    Log(slot_label(i) .. " is empty, cleared the slot")
                end
            else
                empty_since[i] = nil
            end
        end
        if pawn then pcall(function() Swap.party[c["<HumanPartSwapper>k__BackingField"]:get_address()] = slot_label(i) end) end
        if pawn and c and bound_cid[i] == id and Swap.ready(i, c) then apply_pawn(i) end
        if i > 0 and cfg.hire_levelup and pawn and c and bound_cid[i] == id and snap_checked[i] then Lists.hire_levelup(i, pawn) end
    end
    update_plague()

    if not items_live and os.clock() >= live_items_next_try then
        live_items_next_try = os.clock() + 2.0
        items_live = build_live_items()
    end
end)

local function unique_preset_name(base)
    if not presets[base] then return base end
    local n = 2
    while presets[base .. " (" .. n .. ")"] do n = n + 1 end
    return base .. " (" .. n .. ")"
end

local function preset_names()
    local names = {}
    for k in pairs(presets) do table.insert(names, k) end
    table.sort(names)
    return names
end

local CHAR_DIR = modname .. "\\characters\\"
local char_files = {list = {}, parsed = {}, at = -10}

local function scan_character_files(force)
    if not force and os.clock() - char_files.at < 1.0 then return char_files.list end
    char_files.at = os.clock()
    local list = {}
    local ok, paths = pcall(function()
        local all, seen = {}, {}
        for _, pat in ipairs({[[ThePawnController\\characters\\.*\.json]], [[ThePawnController/characters/.*\.json]],
            [[ThePawnController.characters.*\.json]], [[HiredPawnControl\\characters\\.*\.json]]}) do
            local okg, res = pcall(fs.glob, pat)
            for _, p in ipairs(okg and res or {}) do
                if not seen[p] then seen[p] = true table.insert(all, p) end
            end
        end
        if #all ~= char_files.last_count then
            char_files.last_count = #all
            Log("Character files found: " .. #all .. (all[1] and (" (e.g. " .. all[1] .. ")") or ""))
        end
        return all
    end)
    if ok and paths then
        for _, p in ipairs(paths) do
            local info = char_files.parsed[p]
            if not info then
                local d = json.load_file(p)
                if type(d) == "table" and type(d.data) == "table" then
                    info = {path = p, kind = d.type, sections = d.sections, name = p:match("([^\\/]+)%.json$") or p, data = d.data}
                    char_files.parsed[p] = info
                end
            end
            if info then table.insert(list, info) end
        end
    end
    table.sort(list, function(a, b) return a.name:lower() < b.name:lower() end)
    char_files.list = list
    return list
end

local function safe_filename(s)
    s = (s or ""):gsub("[^%w%s%-_]", ""):gsub("^%s+", ""):gsub("%s+$", "")
    return s ~= "" and s or "pawn"
end

local SECTIONS = {
    {key = "equipment", label = "Equipment", fields = {"equipment", "enhance", "eq_skills"}},
    {key = "vocation", label = "Vocation + Skills", fields = {"job", "job_rank", "level", "skills", "abilities", "core", "extra_aug"}},
    {key = "clone", label = "Appearance", fields = {"clone"}},
    {key = "identity", label = "Identity", fields = {"name", "name_moniker", "personality", "specialization", "voice_gender", "voice_tone"}},
    {key = "behaviour", label = "Behaviour", fields = {"chatter", "plague_immune"}},
    {key = "knowledge", label = "Knowledge Overrides", fields = {"knowledge"}},
    {key = "knowledge_perm", label = "Knowledge (permanent)", fields = {"knowledge_raw"}, direct = true},
}
local SOURCES = {"Original", "Current", "Overrides"}

local function source_data(i, source)
    local pawn = get_hired_pawn(i)
    if source == 1 then
        local o = slot_original(i)
        if not o then return nil, "No original saved for this slot yet" end
        local d = deep_copy(o)
        if d.status then d.level = d.status.level or 0 end
        d.eq_skills = EqSkill.as_overrides(d.eq_sid)
        return d
    elseif source == 2 then
        if not pawn then return nil, "No pawn in this slot" end
        local d = snapshot_pawn(pawn)
        if not d then return nil, "Could not read this pawn" end
        if d.status then d.level = d.status.level or 0 end
        d.eq_skills = EqSkill.as_overrides(d.eq_sid)
        return d
    end
    return deep_copy(cfg["pawn" .. i])
end

local function export_sections(i, source, picked, fname)
    local d, err = source_data(i, source)
    if not d then return err end
    local out, keys = {}, {}
    for _, s in ipairs(SECTIONS) do
        if picked[s.key] and not s.soon then
            for _, fld in ipairs(s.fields) do out[fld] = deep_copy(d[fld]) end
            table.insert(keys, s.key)
        end
    end
    if #keys == 0 then return "Pick at least one section" end
    local available = 0
    for _, s in ipairs(SECTIONS) do if not s.soon then available = available + 1 end end
    local tag = (#keys == available) and "all" or table.concat(keys, "+")
    local base = safe_filename(fname) .. "-" .. SOURCES[source]:lower() .. "-" .. tag
    local path = CHAR_DIR .. base .. ".json"
    json.dump_file(path, {format = "hpc2", version = version, source = SOURCES[source]:lower(), sections = keys, data = out})
    char_files.parsed[path] = nil
    scan_character_files(true)
    return "Exported characters\\" .. base .. ".json"
end

local function file_sections(info)
    if info.sections then return info.sections end
    if info.kind == "appearance" then return {} end
    return {"equipment", "vocation", "identity", "behaviour"}
end

local function import_sections(i, info, picked)
    local key = "pawn" .. i
    local pcfg = cfg[key]
    local n = 0
    for _, s in ipairs(SECTIONS) do
        if picked[s.key] and s.direct then
            local raw = info.data.knowledge_raw
            local kctx = raw and knowledge_ctx(get_character(get_hired_pawn(i)))
            if kctx then
                for fname, v in pairs(raw) do pcall(function() kctx:set_field(fname, v) end) end
                n = n + 1
            end
        elseif picked[s.key] then
            for _, fld in ipairs(s.fields) do
                if info.data[fld] ~= nil then pcfg[fld] = deep_copy(info.data[fld]) end
            end
            n = n + 1
        end
    end
    cfg[key] = migrate_pawn(pcfg)
    cfg[key].enabled = true
    config_changed = true
    modified[i] = false
    relax_filters(i, get_human(get_hired_pawn(i)))
    return "Imported " .. n .. " section(s) from " .. info.name .. ", 'Edit this pawn' turned on to apply them"
end

local function setup_ui()
local search_text = {}
local ui_state = {preset_name = "", preset_idx = {[0] = 1, [1] = 1, [2] = 1}, status = "",
    name_input = {}, infect_lv = {[0] = 1, [1] = 1, [2] = 1}, files = {}}

local combo_cache = {}
local item_names = {}
local equip_filter_cache = {}

local function search_combo(key, items, current_id, none_label, none_id, orig_id)
    imgui.set_next_item_width(160)
    local ch, txt = imgui.input_text("##s_" .. key, search_text[key] or "")
    if ch then search_text[key] = txt end
    local s = (search_text[key] or ""):lower()

    local cc = combo_cache[key]
    if not (cc and cc.items == items and cc.n == #items and cc.s == s and cc.cur_id == current_id and cc.v == names_state.v) then
        local disp = {{id = none_id, name = none_label}}
        local cur = 1
        local label = current_id == none_id and none_label or nil
        for _, it in ipairs(items) do
            if not label and it.id == current_id then label = it.name end
            if #disp < 200 then
                if not it.lname then it.lname = it.name:lower() end
                if s == "" or it.lname:find(s, 1, true) or tostring(it.id):find(s, 1, true) then
                    table.insert(disp, it)
                    if it.id == current_id then cur = #disp end
                end
            end
        end
        local names = {}
        for n, it in ipairs(disp) do names[n] = it.name .. "##" .. n end
        cc = {items = items, n = #items, s = s, cur_id = current_id, v = names_state.v, disp = disp, names = names, cur = cur,
            label = label or ("ID " .. tostring(current_id))}
        combo_cache[key] = cc
    end
    local disp = cc.disp

    imgui.same_line()
    imgui.set_next_item_width(320)
    local hl = current_id ~= none_id
    if hl then imgui.push_style_color(0, UI.CHANGED) end
    local c, idx = imgui.combo("##c_" .. key, cc.cur, cc.names)
    if hl then imgui.pop_style_color(1) end
    imgui.same_line()
    if orig_id ~= nil then
        if cc.orig_id ~= orig_id then
            cc.orig_id = orig_id
            cc.orig_name = nil
            for _, it in ipairs(items) do if it.id == orig_id then cc.orig_name = it.name break end end
            cc.orig_name = cc.orig_name or (orig_id == 0 and "None") or ("ID " .. tostring(orig_id))
        end
        imgui.text_colored("Original: " .. cc.orig_name, 0xFF888888)
    elseif cc.label ~= nil and not (cc.disp[cc.cur] and cc.disp[cc.cur].id == current_id) then
        imgui.text(cc.label)
    else
        imgui.text("")
    end
    if c and disp[idx] then
        search_text[key] = ""
        return true, disp[idx].id
    end
    return false, current_id
end

local function mark(i)
    config_changed = true
    modified[i] = false
    if i > 0 and not get_hired_pawn(i) then
        cfg["pawn" .. i].preconfigured = true
        local pc = cfg["pawn" .. i]
        pc.skills_set, pc.abilities_set, pc.skills_base, pc.abilities_base = nil, nil, nil, nil
    end
end

local skills_job_cache = {}
Lists.rank_cache = {}
function Lists.unlock_rank(kind, job, id)
    local k = kind .. job .. ":" .. id
    local v = Lists.rank_cache[k]
    if v ~= nil then return v end
    local ok, r = pcall(function()
        local gm = sdk.get_managed_singleton("app.GuiManager")
        if kind == "core" then
            local entries = gm:get_field("NormalSkillDefineDictionary"):get_field("_entries")
            local want = string.format("Job%02d", job)
            for n = 0, entries:get_size() - 1 do
                local e = entries:get_element(n)
                local okk, key = pcall(function() return e:get_field("key") end)
                if okk and key == want then
                    local ie = e:get_field("value"):get_field("_entries")
                    for m = 0, ie:get_size() - 1 do
                        local x = ie:get_element(m)
                        local okx, xk = pcall(function() return x:get_field("key") end)
                        local val = okx and x:get_field("value")
                        if val and aug_num(xk) == id then return val:get_field("_UnlockRank") end
                    end
                    return false
                end
            end
            return false
        end
        local prm = gm:call("getCustomSkillDefine(app.Character.JobEnum, app.HumanCustomSkillID, app.HumanCustomSkillLevelNo)", job, id, 1)
        return prm and prm:get_field("_UnlockRank") or false
    end)
    if ok then Lists.rank_cache[k] = r return r end
    return nil
end

Lists.core_cache = {}
function Lists.reset_core(i, human, full)
    local pcfg = cfg["pawn" .. i]
    local orig = slot_original(i)
    local orig_core = orig and type(orig.core) == "table" and orig.core or nil
    local ids = {}
    for k, on in pairs(type(pcfg.core) == "table" and pcfg.core or {}) do if on and tonumber(k) then ids[tonumber(k)] = true end end
    pcfg.core = {}
    config_changed = true
    local removed, added = {}, {}
    local ok, err = pcall(function()
        local sc = human:call("get_SkillContext")
        local job = current_job(human) or 0
        local rank = 0
        pcall(function() rank = human:call("get_JobContext"):call("calcJobRank", job) or 0 end)
        for _, it in ipairs(Lists.core_for(job)) do ids[it.id] = true end
        local list = sc:get_field("EnableNormalSkills")
        for n = 0, list:call("get_Count") - 1 do
            local it = list:call("get_Item", n)
            local id = it:get_field("NormalSkillID")
            if type(id) ~= "number" then id = tonumber(id:get_field("value__")) end
            if id and ids[id] then
                local on = it:get_field("IsEnable") == true
                local want
                if full then
                    want = false
                    for j = 1, 10 do
                        if j ~= job and on and not want then
                            for _, cj in ipairs(Lists.core_for(j)) do
                                if cj.id == id then
                                    local nj = Lists.unlock_rank("core", j, id)
                                    local rj = 0
                                    pcall(function() rj = human:call("get_JobContext"):call("calcJobRank", j) or 0 end)
                                    if type(nj) == "number" and nj <= rj then want = true end
                                end
                            end
                        end
                    end
                else
                    local need = Lists.unlock_rank("core", job, id)
                    want = (orig_core and orig_core[tostring(id)] == true)
                        or (type(need) == "number" and need <= rank)
                end
                if on and not want then
                    it:set_field("IsEnable", false)
                    removed[#removed + 1] = name_of(Lists.core, id) or tostring(id)
                elseif want and not on then
                    pcall(function() sc:call("setNormalSkillEnable(app.HumanNormalSkillID)", id) end)
                    if not sc:call("isNormalSkillEnable", id) then it:set_field("IsEnable", true) end
                    added[#added + 1] = name_of(Lists.core, id) or tostring(id)
                end
            end
        end
    end)
    if not ok then Log(slot_label(i) .. ": core skill " .. (full and "reset" or "restore") .. " failed: " .. tostring(err)) return end
    Log(slot_label(i) .. ": core skills " .. (full and "reset" or "restored") .. ", removed " .. (#removed > 0 and table.concat(removed, ", ") or "none")
        .. (#added > 0 and (", put back " .. table.concat(added, ", ")) or ""))
end

function Lists.core_for(job)
    local c = Lists.core_cache[job]
    if c then return c end
    local ids
    pcall(function()
        local entries = sdk.get_managed_singleton("app.GuiManager"):get_field("NormalSkillDefineDictionary"):get_field("_entries")
        local want = string.format("Job%02d", job)
        for n = 0, entries:get_size() - 1 do
            local e = entries:get_element(n)
            local okk, key = pcall(function() return e:get_field("key") end)
            if okk and key == want then
                ids = {}
                local ie = e:get_field("value"):get_field("_entries")
                for m = 0, ie:get_size() - 1 do
                    local x = ie:get_element(m)
                    local okx, xk = pcall(function() return x:get_field("key") end)
                    if okx and x:get_field("value") then ids[aug_num(xk)] = true end
                end
            end
        end
    end)
    local out = {}
    for _, it in ipairs(Lists.core) do
        if (ids and ids[it.id]) or (not ids and it.job == job) then table.insert(out, it) end
    end
    if ids then Lists.core_cache[job] = out end
    return out
end

Lists.lv2_cache = {}
function Lists.lv2_real(job, id)
    -- removed from public release: something capcom should've never left included
    return Lists.lv2_has_text(job, id)
end

function Lists.lv2_has_text(job, id)
    local v = Lists.lv2_cache[id]
    if v ~= nil then return v end
    local ok, real = pcall(function()
        local prm = sdk.get_managed_singleton("app.GuiManager"):call("getCustomSkillDefine(app.Character.JobEnum, app.HumanCustomSkillID, app.HumanCustomSkillLevelNo)", job, id, 2)
        if not prm then return false end
        local text = sdk.find_type_definition("via.gui.message"):get_method("get(System.Guid)"):call(nil, prm:get_field("_SkillText"))
        if type(text) ~= "string" or text == "" then return nil end
        return not text:find("Rejected", 1, true)
    end)
    if ok and real ~= nil then Lists.lv2_cache[id] = real return real end
    return true
end

Lists.keep_cache = {}
function Lists.with_current(ckey, list, cur, full, tag)
    if not cur or cur == 0 then return list end
    for _, it in ipairs(list) do if it.id == cur then return list end end
    local e = Lists.keep_cache[ckey]
    if e and e.src == list and e.cur == cur then return e.list end
    local out = {}
    for n, it in ipairs(list) do out[n] = it end
    table.insert(out, 1, {id = cur, name = (name_of(full, cur) or ("ID " .. tostring(cur))) .. tag})
    Lists.keep_cache[ckey] = {src = list, cur = cur, list = out}
    return out
end

Lists.noskill_cache = {}
function Lists.no_skill(ckey, list)
    local e = Lists.noskill_cache[ckey]
    if e and e.src == list and e.n == #list then return e.list end
    local out = {{id = -1, name = "No skill (empty slot)"}}
    for _, it in ipairs(list) do out[#out + 1] = it end
    Lists.noskill_cache[ckey] = {src = list, n = #list, list = out}
    return out
end

function Lists.skill_tag(job, id)
    local need = Lists.unlock_rank("skill", job, id)
    if type(need) ~= "number" then return "" end
    if need > MAX_JOB_RANK then return id >= 101 and " (DLC reward)" or " (Master)" end
    if need == 0 and id >= 101 then return " (DLC)" end
    return ""
end

local function skills_for_job(job)
    if not job or job <= 0 then return Lists.skills end
    local e = skills_job_cache[job]
    if e and e.v == names_state.v then return e.list end
    local out = {}
    for _, s in ipairs(Lists.skills) do if s.job == job then table.insert(out, s) end end
    skills_job_cache[job] = {v = names_state.v, list = out}
    return out
end

local ui_cache = {}
local function stable_list(ckey, sig, ttl, build)
    local e = ui_cache[ckey]
    local now = os.clock()
    if e and e.sig == sig and now - e.t < ttl then return e.val end
    local v = build()
    local ids = {}
    for n, it in ipairs(v) do ids[n] = it.id end
    local idsig = table.concat(ids, ",")
    if e and e.sig == sig and e.idsig == idsig then
        e.t = now
        return e.val
    end
    ui_cache[ckey] = {sig = sig, t = now, val = v, idsig = idsig}
    return v
end

local pawn_jobs_list
local function pawn_jobs()
    if not pawn_jobs_list then
        pawn_jobs_list = {}
        for _, j in ipairs(Lists.jobs) do
            if j.id <= MAX_PAWN_JOB then table.insert(pawn_jobs_list, j) end
        end
    end
    return pawn_jobs_list
end

local max_possession_cache
local function max_possession_lv()
    if max_possession_cache then return max_possession_cache end
    local ok, v = pcall(function()
        return sdk.find_type_definition("app.PawnDefine"):get_field("MaxPossessionLv"):get_data(nil)
    end)
    if ok and type(v) == "number" and v > 0 then max_possession_cache = v return v end
    return 3
end

local function restore_button(i, label, parts)
    if not (slot_original(i) and get_hired_pawn(i)) then return end
    imgui.spacing()
    if imgui.button("Restore original " .. label .. "##r" .. i .. label) then request_restore(i, parts) end
end

local function draw_permanent_knowledge(i, key, pawn)
    local chara = get_character(pawn)
    local kctx = chara and knowledge_ctx(chara)
    if not kctx then
        imgui.text("No pawn in this slot")
        return
    end
    local function guarded(title, text, fn)
        if i == 0 then ask_confirm(title, text, fn) else fn() end
    end
    ui_state.know_search = ui_state.know_search or {}
    for _, k in ipairs(KNOWLEDGE) do
        local have, total = know_count(kctx, k.key)
        imgui.text(string.format("%s: %d / %d", k.label, have, total))
        imgui.same_line()
        if imgui.button("Add all##pa" .. key .. k.key) then
            guarded("Add all " .. k.label, "Your Main Pawn will permanently know every " .. k.label .. " entry.", function() know_set_all(kctx, k.key, true) end)
        end
        imgui.same_line()
        if imgui.button("Remove all##pr" .. key .. k.key) then
            guarded("Remove all " .. k.label, "Your Main Pawn will permanently forget every " .. k.label .. " entry.", function() know_set_all(kctx, k.key, false) end)
        end
        if imgui.tree_node("Entries##pe" .. key .. k.key) then
            local sk = key .. k.key
            imgui.set_next_item_width(200)
            local sc, sv = imgui.input_text("Search##ps" .. sk, ui_state.know_search[sk] or "")
            if sc then ui_state.know_search[sk] = sv end
            local s = (ui_state.know_search[sk] or ""):lower()
            local shown = 0
            for _, fname in ipairs(KNOW_FIELDS[k.key]) do
                local cur = norm_flag(kctx:get_field(fname)) or 0
                for _, m in ipairs(flag_members(kctx, fname)) do
                    if shown < 200 and (s == "" or m.name:lower():find(s, 1, true)) then
                        shown = shown + 1
                        local on = (cur & m.value) ~= 0
                        local c, v = imgui.checkbox(m.name .. "##pk" .. sk .. fname .. m.name, on)
                        if c then
                            cur = v and (cur | m.value) or (cur & ~m.value)
                            pcall(function() kctx:set_field(fname, cur) end)
                        end
                    end
                end
            end
            if shown == 0 then imgui.text("Nothing matches") end
            imgui.tree_pop()
        end
    end
    local orig = slot_original(i)
    if orig and orig.knowledge_raw then
        imgui.spacing()
        if imgui.button("Reset to original knowledge##prs" .. key) then
            guarded("Reset knowledge", "Puts your Main Pawn's knowledge back to how it was when the mod first saw them.", function()
                request_restore(i, {"knowledge"})
            end)
        end
    end
    imgui.spacing()
    imgui.text_colored("All changes made are permanent and will modify your save", 0xFF8080FF)
end

local function draw_pawn(i)
    local key = "pawn" .. i
    local pcfg = cfg[key]
    local pawn = get_hired_pawn(i)
    local human = get_human(pawn)

    if imgui.tree_node("Name##" .. key) then
        imgui.text_colored("Reload your game for this change to fully apply", 0xFF8080FF)
        imgui.separator()
        local character = get_character(pawn)
        local ctx = get_data_context(character)
        if ctx then
            local orig = slot_original(i)
            imgui.text("Original name: " .. tostring(orig and orig.name or ctx_name(ctx)))
            imgui.text("Current name: " .. tostring(ctx_name(ctx)))
            local nick = "?"
            pcall(function() nick = ctx:call("get_Nickname") end)
            imgui.text("Moniker: " .. tostring(nick) .. ((orig and orig.nickname and orig.nickname ~= nick) and ("  (original: " .. orig.nickname .. ")") or ""))
        end
        if ui_state.name_input[i] == nil then ui_state.name_input[i] = pcfg.name end
        imgui.set_next_item_width(220)
        local nc, nv = imgui.input_text("##name" .. key, ui_state.name_input[i])
        if nc then ui_state.name_input[i] = nv end
        imgui.same_line()
        if imgui.button("Rename##" .. key) then
            pcfg.name = ui_state.name_input[i]:gsub("^%s+", ""):gsub("%s+$", "")
            mark(i)
        end
        imgui.same_line()
        if slot_original(i) and get_hired_pawn(i) then
            if imgui.button("Restore original name##rn" .. key) then
                request_restore(i, {"name"})
                ui_state.name_input[i] = ""
                pcfg.name_moniker = nil
            end
        end
        local mc, mv = UI.cb("Also use this name as the moniker##moniker" .. key, pcfg.name_moniker == true)
        if mc then pcfg.name_moniker = mv mark(i) end
        imgui.text_colored("The moniker is the name some menus and the party list show instead of the pawn's name.", 0xFF888888)
        imgui.tree_pop()
    end

    if imgui.tree_node("Equipment##" .. key) then
        local equip_job = (pcfg.job > 0 and pcfg.job) or (human and current_job(human)) or 0
        imgui.text("Item source: " .. items_source)
        if cfg.force_equip then
            imgui.text_colored("Ignoring vocation restrictions for equipment overrides\n(change it in Options + Debug)", 0xFF66DD66)
        else
            imgui.text_colored("To allow pawns to equip any gear from any vocation:\nEnable 'Ignore vocation restrictions for equipment overrides' in Options + Debug", 0xFF888888)
        end
        imgui.spacing()
        imgui.separator()
        imgui.spacing()
        local show_all = cfg.show_all_items or cfg.force_equip
        if not cfg.force_equip then
            local ac, av = UI.cb("Show items for all vocations##allitems" .. key, cfg.show_all_items)
            if ac then cfg.show_all_items = av config_changed = true end
        end
        if equip_job > 0 and not show_all then
            imgui.same_line()
            imgui.text("(showing " .. (name_of(Lists.jobs, equip_job) or "?") .. " gear)")
        end
        if i > 0 then
            imgui.text_colored("Hired pawns don't keep gear that gets replaced. Restore puts their original back.", 0xFF888888)
        end
        local orig = get_hired_pawn(i) and slot_original(i)
        local orig_eq = orig and orig.equipment
        for _, slot in ipairs(SLOTS) do
            imgui.text(slot .. ":")
            local list = itemLists[slot]
            if equip_job > 0 and not show_all then
                local fc = equip_filter_cache[slot]
                if not (fc and fc.src == itemLists[slot] and fc.job == equip_job) then
                    fc = {src = itemLists[slot], job = equip_job, list = {}}
                    for _, it in ipairs(itemLists[slot]) do
                        if not it.jobs or it.jobs[equip_job] then table.insert(fc.list, it) end
                    end
                    equip_filter_cache[slot] = fc
                end
                list = fc.list
            end
            local c, v = search_combo(key .. slot, list, pcfg.equipment[slot], "No Override", 0, orig_eq and orig_eq[slot] or nil)
            if c then pcfg.equipment[slot] = v mark(i) end
            local oid = orig_eq and orig_eq[slot] or 0
            if oid > 0 then
                local nm = orig.names and orig.names[slot]
                if not nm then
                    nm = item_names[oid]
                    if nm == nil then
                        pcall(function() nm = clean_text(ItemManager:getItemData(oid):call("get_Name")) end)
                        item_names[oid] = nm or false
                    end
                end
                local e = orig.enhance and orig.enhance[slot]
                local k = e and e.steps and filled_steps(e) or 0
                local plus = (e and e.dragon) and " +3 Dragonforged" or (k > 0 and (" +" .. k) or "")
                imgui.same_line()
                if imgui.button("Restore (" .. (nm or ("item " .. oid)) .. plus .. ")##rse" .. key .. slot) then
                    request_restore(i, {"equip:" .. slot})
                end
            end
        end
        imgui.spacing()
        imgui.text("Enhancement (applies to whatever is equipped in the slot):")
        local character = get_character(pawn)
        for _, slot in ipairs(ENHANCE_SLOTS) do
            local e = pcfg.enhance[slot]
            local id = "##enh" .. key .. slot
            local c, v = UI.cb("Override " .. slot .. " enhancement" .. id, e.enabled)
            if c then e.enabled = v mark(i) end
            if e.enabled then
                imgui.indent(20)
                for n = 1, 3 do
                    if n > 1 and (e.steps[n - 1] or 0) == 0 then break end
                    imgui.set_next_item_width(200)
                    local sc, sv = imgui.combo("Step " .. n .. id .. n, (e.steps[n] or 0) + 1, ENHANCE_STEP_NAMES)
                    if sc then
                        e.steps[n] = sv - 1
                        if sv == 1 then for m = n + 1, 3 do e.steps[m] = 0 end end
                        mark(i)
                    end
                end
                local k = filled_steps(e)
                local base_num = 0
                pcall(function()
                    base_num = get_slot_item(character, SlotEnum[slot]):call("get_EnhanceNum") or 0
                end)
                if k == 3 or (k == 0 and base_num >= 3) then
                    local dc, dv = UI.cb("Dragonforged" .. id .. "d", e.dragon)
                    if dc then e.dragon = dv mark(i) end
                elseif e.dragon and k > 0 then
                    e.dragon = false
                    mark(i)
                end
                imgui.unindent(20)
            end
        end
        imgui.spacing()
        imgui.text("Special skills (the appraisal skills on weapons and armour):")
        local sk = EqSkill.load()
        local rc_, rv_ = UI.cb("Only show skills that can roll on the item##eqsroll" .. key, cfg.skills_rollable_only ~= false, true)
        if rc_ then cfg.skills_rollable_only = rv_ config_changed = true end
        local character_ = get_character(pawn)
        for _, slot in ipairs(ENHANCE_SLOTS) do
            local e = pcfg.eq_skills[slot]
            local sid = "##eqs" .. key .. slot
            local c, v = false, e.enabled
            if slot ~= "Mantle" then
                c, v = UI.cb("Override " .. slot .. " skills" .. sid, e.enabled)
            end
            if c then e.enabled = v mark(i) end
            if slot ~= "Mantle" and e.enabled then
                imgui.indent(20)
                local target = (pcfg.equipment[slot] or 0) > 0 and pcfg.equipment[slot] or 0
                if target == 0 and character_ then
                    pcall(function() target = get_slot_item(character_, SlotEnum[slot])._ItemId or 0 end)
                end
                local list, filtered = sk.list, false
                if cfg.skills_rollable_only ~= false then list, filtered = EqSkill.list_for(target) end
                if character_ then pcall(function() EqSkill.debug_current(get_slot_item(character_, SlotEnum[slot]), slot) end) end
                if cfg.skills_rollable_only ~= false and not filtered then
                    imgui.text_colored("(this item has no roll table of its own, showing the general appraisal pool)", 0xFF888888)
                end
                for n = 1, 4 do
                    local c2, v2 = search_combo(key .. "eqs" .. slot .. n, list, e.ids[n] or 0, "No skill", 0)
                    if c2 then e.ids[n] = v2 mark(i) end
                end
                for _, w in ipairs(EqSkill.check(e.ids, i == 0, target)) do imgui.text_colored("! " .. w, 0xFF33AAFF) end
                imgui.unindent(20)
            end
            if slot ~= "Mantle" then
                local tgt = (pcfg.equipment[slot] or 0) > 0 and pcfg.equipment[slot] or 0
                local sd_ = nil
                if character_ then pcall(function() sd_ = get_slot_item(character_, SlotEnum[slot]) end) end
                if tgt == 0 and sd_ then tgt = sd_._ItemId or 0 end
                local lim = EqSkill.limits(tgt, human and current_job(human) or nil)
                if lim then
                    local same_item = sd_ and sd_._ItemId == tgt
                    local sc3, sv3 = UI.cb("Modify " .. slot .. " appraisal roll" .. sid .. "st", e.stats_on == true)
                    if sc3 then
                        e.stats_on = sv3
                        if sv3 and type(e.stats) ~= "table" then
                            e.stats = (same_item and EqSkill.stats_of(sd_)) or {phys = 0, magic = 0, blow = 0, weight = 0}
                        end
                        mark(i)
                    end
                    if e.stats_on and type(e.stats) == "table" then
                        imgui.indent(20)
                        local orig = nil
                        pcall(function()
                            local od = slot_original(i)
                            local rec = od and od.eq_sid and od.eq_sid[tostring(sd_:call("get_StorageId"))]
                            if rec and rec.phys ~= nil then orig = {phys = rec.phys, magic = rec.magic, blow = rec.blow, weight = rec.weight, bonus = rec.bonus}
                            elseif same_item and not (od and od.eq_written and od.eq_written[tostring(sd_:call("get_StorageId"))]) then orig = EqSkill.stats_of(sd_) end
                        end)
                        if EqSkill.stat_ui(sid .. "sl", e.stats, lim, orig, EqSkill.bonus_pool(tgt), tgt) then mark(i) end
                        imgui.unindent(20)
                    end
                end
            end
        end
        restore_button(i, "equipment + enhancement", {"equipment"})
        imgui.tree_pop()
    end

    if imgui.tree_node("Vocation + Skills##" .. key) then
        local jobs = pawn_jobs()

        imgui.text("Vocation:")
        local o_job = slot_original(i)
        local c, v = search_combo(key .. "job", jobs, pcfg.job, "No Override", 0, o_job and o_job.job or nil)
        if c then pcfg.job = v mark(i) end
        imgui.set_next_item_width(200)
        local rc, rv = imgui.slider_int("Vocation rank (0 = no override)##rank" .. key, pcfg.job_rank or 0, 0, MAX_JOB_RANK)
        if rc then pcfg.job_rank = rv mark(i) end

        local sc = human and status_ctx(human)
        local cur_lv = 0
        if sc then pcall(function() cur_lv = sc:call("get_Level") or 0 end) end
        ui_state.level_input = ui_state.level_input or {}
        imgui.text("Level:")
        imgui.same_line()
        imgui.set_next_item_width(70)
        local lc, lv = imgui.input_text("##lvl" .. key, ui_state.level_input[i] or "")
        if lc then ui_state.level_input[i] = lv end
        imgui.same_line()
        if imgui.button("Set level##setlvl" .. key) then
            local want = math.floor(tonumber(ui_state.level_input[i] or "") or 0)
            local cap = human and max_level(human) or 999
            if want >= 1 and want <= cap and want ~= cur_lv and (i > 0 or want > cur_lv) then
                local function go()
                    pcfg.level = want
                    pcfg.level_keep = want
                    mark(i)
                    ui_state.level_input[i] = ""
                    ui_state.level_msg = nil
                end
                if i == 0 then
                    ask_confirm("Raise Main Pawn level", "This permanently raises your Main Pawn from level " .. cur_lv .. " to " .. want .. ".", go)
                else
                    go()
                end
            else
                ui_state.level_msg = {i = i, text = i == 0 and ("Enter a level above " .. cur_lv .. " (max " .. cap .. ")")
                    or ("Enter a level from 1 to " .. cap .. " (currently " .. cur_lv .. ")")}
            end
        end
        imgui.same_line()
        imgui.text("current " .. (sc and tostring(cur_lv) or "?"))
        if human then
            imgui.same_line()
            if imgui.button("Reset to level 1##rstlvl" .. key) then
                local who = i == 0 and "your Main Pawn" or "this pawn"
                ask_confirm("Reset to level 1", "This permanently resets " .. who .. " from level " .. cur_lv .. " to level 1,\nalong with the stats they gained from levelling.\nUse Set level afterwards to raise them again.", function()
                    table.insert(game_jobs, function() reset_level(human) end)
                    pcfg.level = 0
                    pcfg.level_keep = nil
                end)
            end
            local orig = slot_original(i)
            local orig_lv = orig and orig.status and orig.status.level
            if orig_lv and orig_lv ~= cur_lv then
                imgui.same_line()
                if imgui.button("Restore original level (" .. orig_lv .. ")##orglvl" .. key) then
                    local status = deep_copy(orig.status)
                    ask_confirm("Restore original level", "This puts " .. (i == 0 and "your Main Pawn" or "this pawn") .. " back to level " .. orig_lv
                        .. ",\nwith the EXP and level-up stats they had when the mod first saw them.", function()
                        table.insert(game_jobs, function()
                            restore_status(human, status)
                            if i > 0 then Lists.lvl_next[i] = math.huge end
                        end)
                        pcfg.level = 0
                        pcfg.level_keep = nil
                    end)
                end
            end
        end
        if ui_state.level_msg and ui_state.level_msg.i == i then imgui.text_colored(ui_state.level_msg.text, 0xFF00FFFF) end

        local job = (pcfg.job > 0 and pcfg.job) or (human and current_job(human)) or 0
        local restrict = learned_only(i)
        local c3, v3 = UI.cb("Only show skills this pawn has learned (untick to unlock new ones)##" .. key, restrict, true)
        if c3 then set_learned_only(i, v3) restrict = v3 modified[i] = false end
        local rank_filter = cfg.skills_rank_filter ~= false
        local cr, vr = UI.cb("Hide skills above this pawn's vocation rank##rkf" .. key, rank_filter, true)
        if cr then cfg.skills_rank_filter = vr config_changed = true rank_filter = vr end
        if not rank_filter then
            imgui.text_colored("Skills above the pawn's vocation rank aren't something the pawn could have learned.\nThe game's check doesn't stop them, but Validate Pawn flags them.\nMaster and DLC skills unlock by item or quest, not rank.", 0xFF33AAFF)
        end
        local cu, vu = UI.cb("Apply skills as the upgraded variant##skup" .. key, cfg.skill_max_level ~= false, true)
        if cu then cfg.skill_max_level = vu config_changed = true modified[i] = false end
        local skills = skills_for_job(job)
        local eff_rank
        pcall(function()
            eff_rank = (pcfg.job_rank or 0) > 0 and pcfg.job_rank or tonumber(human:call("get_JobContext"):call("calcJobRank", job))
        end)
        if eff_rank and job > 0 then
            local base = skills
            skills = stable_list("rank" .. key, job .. ":" .. eff_rank .. ":" .. tostring(rank_filter) .. ":" .. names_state.v, 1.0, function()
                local out = {}
                for _, sk in ipairs(base) do
                    local need = Lists.unlock_rank("skill", job, sk.id)
                    local tag = Lists.skill_tag(job, sk.id)
                    -- removed from public release: something capcom should've never left included [tags]
                    if type(need) == "number" and need > eff_rank and need <= MAX_JOB_RANK then
                        if not rank_filter then table.insert(out, {id = sk.id, name = sk.name .. tag .. " (needs rank " .. need .. ")", job = sk.job}) end
                    else
                        table.insert(out, {id = sk.id, name = sk.name .. tag, job = sk.job})
                    end
                end
                return out
            end)
        end
        if restrict then
            local sc = human and human:call("get_SkillContext")
            local src = skills
            skills = stable_list("learned" .. key, tostring(sc and sc:get_address()) .. ":" .. job .. ":" .. names_state.v, 1.0, function()
                local learned = {}
                if sc then
                    for _, s in ipairs(src) do
                        local ok, has = pcall(function() return sc:call("isCustomSkillEnable", s.id) end)
                        if ok and has then table.insert(learned, s) end
                    end
                end
                return learned
            end)
            if #skills == 0 then
                imgui.text_colored(sc and "This pawn hasn't learned any skills for this vocation."
                    or "Hire a pawn in this slot to see their learned skills.", 0xFF00FFFF)
            end
        end
        imgui.text("Skills (" .. (name_of(Lists.jobs, job) or "any vocation") .. "):")
        local o_sk = slot_original(i)
        local o_same = o_sk and o_sk.job == job
        for s = 1, SKILL_SLOTS do
            local slist = Lists.with_current(key .. "skill" .. s, Lists.no_skill(key .. "skill" .. s, skills), pcfg.skills[s] or 0, Lists.skills, " (not learned)")
            local c2, v2 = search_combo(key .. "skill" .. s, slist, pcfg.skills[s] or 0, "No Override", 0, o_same and o_sk.skills and o_sk.skills[s] or nil)
            if c2 then pcfg.skills[s] = v2 mark(i) end
        end

        local ck, vk = UI.cb("Keep augments when changing vocation##keepaug" .. key, cfg.keep_augments ~= false, true)
        if ck then cfg.keep_augments = vk config_changed = true modified[i] = false end
        imgui.text_colored("If the current vocation has no augments, its set is copied from another vocation", 0xFF888888)
        local aug_restrict = unlocked_aug_only(i)
        local ca, va = UI.cb("Only show augments this pawn has unlocked##aug" .. key, aug_restrict, true)
        if ca then pref_set(i, "unlocked_augments_only", va) aug_restrict = va modified[i] = false end
        local aug_list = Lists.abilities
        if aug_restrict then
            aug_list = stable_list("aug" .. key, tostring(human and human:get_address()) .. ":" .. names_state.v, 1.0, function()
                local have = human and unlocked_abilities(human) or {}
                local out = {}
                for _, a in ipairs(Lists.abilities) do if have[a.id] then table.insert(out, a) end end
                return out
            end)
            if #aug_list == 0 then
                imgui.text_colored(human and "This pawn hasn't unlocked any augments." or "Hire a pawn in this slot to see their augments.", 0xFF00FFFF)
            end
        end
        local extra_open, base_slots = false, 6
        pcall(function()
            local ac = human:call("get_AbilityContext")
            extra_open = ac:get_field("IsAdditionalSlotUnlocked") == true
            base_slots = ac:get_field("DefaultNumSlots") or 6
        end)
        imgui.text("Augments:")
        for s = 1, ABILITY_SLOTS do
            if s > base_slots and not extra_open and not pcfg.extra_aug then
                imgui.text_colored("  Slot " .. s .. " is locked (tick 'Unlock the extra augment slot' to use it)", 0xFF888888)
            else
                local alist = Lists.with_current(key .. "aug" .. s, aug_list, pcfg.abilities[s] or 0, Lists.abilities, " (not unlocked)")
                local c4, v4 = search_combo(key .. "aug" .. s, alist, pcfg.abilities[s] or 0, "No Override", 0, o_same and o_sk.abilities and o_sk.abilities[s] or nil)
                if c4 then pcfg.abilities[s] = v4 mark(i) end
            end
        end
        if extra_open then
            imgui.text_colored("Extra augment slot unlocked", 0xFF66DD66)
        else
            local ce, ve = UI.cb("Unlock the extra augment slot##xaug" .. key, pcfg.extra_aug == true)
            if ce then pcfg.extra_aug = ve or nil mark(i) end
            if i == 0 then imgui.text_colored("Same as reading the book, permanent on your Main Pawn", 0xFF888888) end
        end
        imgui.spacing()
        imgui.text("Core skills:")
        if type(pcfg.core) ~= "table" then pcfg.core = {} end
        local csc = human and human:call("get_SkillContext")
        local any_core, hidden_core = false, 0
        for _, it in ipairs(Lists.core_for(job)) do
            do
                any_core = true
                local learned = false
                if csc then pcall(function() learned = csc:call("isNormalSkillEnable", it.id) == true end) end
                local need = Lists.unlock_rank("core", job, it.id)
                local locked = eff_rank and type(need) == "number" and need > eff_rank and need <= MAX_JOB_RANK
                if learned then
                    imgui.text_colored("  " .. it.name .. " (learned)", 0xFF66DD66)
                elseif locked and rank_filter then
                    hidden_core = hidden_core + 1
                else
                    local cc, cv = UI.cb(it.name .. (locked and (" (needs rank " .. need .. ")") or "") .. "##core" .. key .. it.id, pcfg.core[tostring(it.id)] == true)
                    if cc then pcfg.core[tostring(it.id)] = cv or nil mark(i) end
                end
            end
        end
        if not any_core then imgui.text("  (pick a vocation to see its core skills)") end
        if hidden_core > 0 then imgui.text_colored("  " .. hidden_core .. " more above this pawn's rank (untick the rank filter to see them)", 0xFF888888) end
        if human then
            local who = i == 0 and "your Main Pawn" or "this pawn"
            if imgui.button("Reset core skills##rstcore" .. key) then
                ask_confirm("Reset core skills", "This turns off every core skill of the current vocation on " .. who .. ",\nincluding the ones it learned itself. Ones another vocation has earned are kept." .. (i == 0 and "\nOn your Main Pawn this is permanent." or ""), function()
                    table.insert(game_jobs, function() Lists.reset_core(i, human, true) end)
                end)
            end
            if imgui.button("Restore core skills##orgcore" .. key) then
                ask_confirm("Restore core skills", "This puts " .. who .. "'s core skills back to what it had when the mod first saw it.\nCore skills the mod unlocked are removed.", function()
                    table.insert(game_jobs, function() Lists.reset_core(i, human, false) end)
                end)
            end
        end
        restore_button(i, "vocation, rank + level", {"vocation"})
        restore_button(i, "skills", {"skills"})
        restore_button(i, "augments", {"augments"})
        imgui.tree_pop()
    end

    if imgui.tree_node("Attributes##" .. key) then
        imgui.text("Personality:")
        local o_attr = slot_original(i)
        local c, v = search_combo(key .. "pers", Lists.personality, pcfg.personality, "No Override", 0, o_attr and o_attr.personality or nil)
        if c then pcfg.personality = v mark(i) end
        imgui.text("Specialization:")
        c, v = search_combo(key .. "spec", Lists.spec, pcfg.specialization, "No Override", -1, o_attr and o_attr.specialization or nil)
        if c then pcfg.specialization = v mark(i) end
        imgui.text_colored("Save and reload after changing voice/personality!", 0xED8585FF)
        imgui.text("Voice gender:")
        c, v = search_combo(key .. "vg", Lists.gender, pcfg.voice_gender, "No Override", 0, o_attr and o_attr.voice_gender or nil)
        if c then pcfg.voice_gender = v mark(i) end
        imgui.text("Voice tone:")
        c, v = search_combo(key .. "vt", Lists.tone, pcfg.voice_tone, "No Override", -1, o_attr and o_attr.voice_tone or nil)
        if c then pcfg.voice_tone = v mark(i) end
        restore_button(i, "personality, specialization + voice", {"attributes"})
        imgui.tree_pop()
    end

    if imgui.tree_node("Behaviour##" .. key) then
        imgui.set_next_item_width(160)
        local cc, cv = imgui.combo("Chatter##chat" .. key, pcfg.chatter or 1, CHATTER_NAMES)
        if cc then pcfg.chatter = cv config_changed = true end
        imgui.same_line()
        imgui.text(({"talks as normal", "45s minimum between lines", "3 min minimum between lines", "never speaks"})[pcfg.chatter or 1])
        imgui.tree_pop()
    end

    if imgui.tree_node("Knowledge##" .. key) then
        ui_state.know_mode = ui_state.know_mode or {}
        imgui.set_next_item_width(260)
        local mc, mv = imgui.combo("##kmode" .. key, ui_state.know_mode[i] or 1, {"Override Knowledge", "Permanent Changes"})
        if mc then ui_state.know_mode[i] = mv end
        if (ui_state.know_mode[i] or 1) == 2 then
            draw_permanent_knowledge(i, key, pawn)
            imgui.tree_pop()
        else
        local kn = pcfg.knowledge
        local function set_all(v) for _, k in ipairs(KNOWLEDGE) do kn[k.key] = v end config_changed = true end
        if imgui.button("Unlock all knowledge##ka" .. key) then set_all(1) end
        imgui.same_line()
        if imgui.button("Reset to default##kd" .. key) then set_all(0) end
        imgui.same_line()
        imgui.push_style_color(0, 0xFF8080FF)
        local wipe = imgui.button("Wipe all knowledge##kn" .. key)
        imgui.pop_style_color(1)
        if wipe then set_all(2) end
        local summary = {}
        for _, k in ipairs(KNOWLEDGE) do table.insert(summary, k.label .. ": " .. KNOW_MODES[(kn[k.key] or 0) + 1]) end
        imgui.text(table.concat(summary, "  |  "))
        if imgui.tree_node("Detail##kdet" .. key) then
            for _, k in ipairs(KNOWLEDGE) do
                imgui.set_next_item_width(120)
                local c, v = imgui.combo(k.label .. "##k" .. key .. k.key, (kn[k.key] or 0) + 1, KNOW_MODES)
                if c then kn[k.key] = v - 1 config_changed = true end
                if k.tip then
                    imgui.same_line()
                    imgui.text("(" .. k.tip .. ")")
                end
            end
            imgui.tree_pop()
        end
        imgui.text_colored("These only override what the pawn knows. Nothing is written to your save.", 0xFF888888)
        imgui.tree_pop()
        end
    end

    if imgui.tree_node("QoL + Testing##" .. key) then
        draw_qol(key, pcfg.qol, get_character(pawn), true, function(fn)
            if i == 0 then
                ask_confirm("Kill Main Pawn", "This kills your Main Pawn. Summon them back at any Riftstone.", fn)
            elseif pcfg.qol.return_after_rest then
                fn()
            else
                ask_confirm("Kill " .. slot_label(i), "Hired pawns who die go back to the Rift for good.\nTick 'Respawn pawn shortly after death' first if you want them back.", fn)
            end
        end, i > 0, i)
        local vchara = get_character(pawn)
        if vchara then
            imgui.spacing()
            if imgui.button("Validate Pawn##val" .. i) then PawnCheck.validate(i, vchara) end
            local r = PawnCheck.result[i]
            if r then
                imgui.same_line()
                imgui.text_colored(r.text, r.col or 0xFFAAAAAA)
            end

        end
        imgui.tree_pop()
    end

    if imgui.tree_node("Dragonsplague##" .. key) then
        local ctx = get_data_context(get_character(pawn))
        local max_lv = max_possession_lv()
        if ctx then
            local lv, pts = 0, 0
            pcall(function()
                lv = ctx:call("get_PossessionLv") or 0
                pts = ctx:call("get_PossessionProgressPoint") or 0
            end)
            local col = lv == 0 and 0xFF00FF00 or (lv >= max_lv and 0xFF0000FF or 0xFF00FFFF)
            imgui.text_colored(string.format("Current: stage %d / %d (progress %d)", lv, max_lv, pts), col)
        else
            imgui.text("Current: no pawn in this slot")
        end
        local c, v = UI.cb("Immune to dragonsplague##" .. key, pcfg.plague_immune)
        if c then pcfg.plague_immune = v config_changed = true end
        if ctx then
            if imgui.button("Cure now##" .. key) then cure_plague(pawn, ctx) end
            if pcfg.plague_immune then
                imgui.text("(untick immunity to infect)")
            else
                imgui.set_next_item_width(160)
                ui_state.infect_lv[i] = ui_state.infect_lv[i] or 1
                local ic, iv = imgui.slider_int("##infectlv" .. key, ui_state.infect_lv[i], 1, max_lv)
                if ic then ui_state.infect_lv[i] = iv end
                imgui.same_line()
                if imgui.button("Infect to stage##" .. key) then
                    local lv = ui_state.infect_lv[i]
                    table.insert(game_jobs, function() pcall(function() ctx:call("setPossessionLv", lv) end) end)
                    Log(slot_label(i) .. ": infected to stage " .. lv)
                end
            end
        end
        restore_button(i, "plague state", {"plague"})
        imgui.tree_pop()
    end

    if imgui.tree_node("Presets##pr" .. key) then
        imgui.text_colored("Presets allow saving and importing all settings currently applied to a pawn", 0xFF888888)
        imgui.text_colored("Copy settings allows you to quickly apply any settings applied to another pawn", 0xFF888888)
        if i == 0 then
            imgui.text_colored("Main pawn only applies knowledge, chatter, plague immunity and QoL", 0xFF8080FF)
        end
        imgui.spacing()

        local MAIN_SAFE = {"knowledge", "chatter", "plague_immune", "qol"}
        local function apply_preset(data)
            if i == 0 then
                for _, fld in ipairs(MAIN_SAFE) do
                    if data[fld] ~= nil then pcfg[fld] = deep_copy(data[fld]) end
                end
                pcfg.enabled = true
            else
                local d = deep_copy(data)
                if (d.level_keep or 0) > 0 then d.level = d.level_keep end
                d.knowledge_raw, d.possession, d.status = nil, nil, nil
                d.eq_sid, d.eq_written, d.eq_abil, d.names = nil, nil, nil, nil
                d.owner, d.preconfigured, d.sid, d.clone_keep = cfg[key].owner, cfg[key].preconfigured, cfg[key].sid, cfg[key].clone_keep
                local sp = d.slot_prefs
                d.slot_prefs = nil
                d.skills_set, d.abilities_set = cfg[key].skills_set, cfg[key].abilities_set
                d.skills_base, d.abilities_base = cfg[key].skills_base, cfg[key].abilities_base
                cfg[key] = migrate_pawn(d)
                cfg[key].enabled = true
                ui_state.name_input[i] = nil
                if type(sp) == "table" then
                    if sp.learned_only ~= nil then set_learned_only(i, sp.learned_only) end
                    if sp.unlocked_augments_only ~= nil then pref_set(i, "unlocked_augments_only", sp.unlocked_augments_only) end
                end
                relax_filters(i, human)
            end
            mark(i)
        end

        local any_copy = false
        for _, j in ipairs(SLOT_IDS) do
            local other = j ~= i and get_hired_pawn(j)
            local octx = other and get_data_context(get_character(other))
            if octx then
                any_copy = true
                local who = SLOT_NAMES[j] .. " [" .. (ctx_name(octx) or "?") .. "]"
                local label = i == 0 and ("Copy settings from " .. who) or ("Copy from " .. who)
                if imgui.button(label .. "##cp" .. key .. j) then
                    local data = deep_copy(cfg["pawn" .. j])
                    data.slot_prefs = {learned_only = learned_only(j), unlocked_augments_only = unlocked_aug_only(j)}
                    if data then
                        apply_preset(data)
                        ui_state.preset_status = "Copied " .. who .. ", 'Edit this pawn' turned on to apply it"
                    end
                end
            end
        end
        if not any_copy then imgui.text("No other pawns to copy from right now.") end

        imgui.spacing()
        imgui.separator()
        imgui.spacing()
        imgui.text("Save your settings as a preset")
        imgui.set_next_item_width(260)
        local nc, nv = imgui.input_text("##presetname" .. key, ui_state.preset_name)
        if nc then ui_state.preset_name = nv end
        imgui.same_line()
        if imgui.button("Save##ps" .. key) then
            local p = deep_copy(pcfg)
            p.level = p.level_keep or 0
            p.slot_prefs = {learned_only = learned_only(i), unlocked_augments_only = unlocked_aug_only(i)}
            p.skills_set, p.abilities_set, p.skills_base, p.abilities_base = nil, nil, nil, nil
            p.enabled, p.knowledge_raw, p.possession, p.status = nil, nil, nil, nil
            p.eq_sid, p.eq_written, p.eq_abil, p.names = nil, nil, nil, nil
            p.owner, p.preconfigured, p.sid, p.clone_keep = nil, nil, nil, nil
            local base = ui_state.preset_name ~= "" and ui_state.preset_name
                or (ctx_name(get_data_context(get_character(pawn))) or SLOT_NAMES[i])
            local final = unique_preset_name(base)
            presets[final] = p
            save_presets()
            ui_state.preset_status = "Saved preset '" .. final .. "'"
        end
        imgui.spacing()
        imgui.spacing()
        imgui.text("Saved presets")
        local names = preset_names()
        if #names > 0 then
            ui_state.preset_idx[i] = math.min(ui_state.preset_idx[i] or 1, #names)
            imgui.set_next_item_width(260)
            local pc, pidx = imgui.combo("##preset" .. key, ui_state.preset_idx[i], names)
            if pc then ui_state.preset_idx[i] = pidx end
            imgui.same_line()
            if imgui.button("Load##pl" .. key) then
                local pname = names[ui_state.preset_idx[i]]
                apply_preset(presets[pname])
                ui_state.preset_status = "Loaded '" .. pname .. "', 'Edit this pawn' turned on to apply it"
            end
            imgui.same_line()
            if imgui.button("Delete##pd" .. key) then
                presets[names[ui_state.preset_idx[i]]] = nil
                save_presets()
            end
        else
            imgui.text("No saved presets yet.")
        end
        if ui_state.preset_status then imgui.spacing() imgui.text(ui_state.preset_status) end
        imgui.tree_pop()
    end
end

local function get_player()
    local ok, p = pcall(function()
        return sdk.get_managed_singleton("app.CharacterManager"):call("get_ManualPlayer")
    end)
    return ok and p or nil
end

local function write_look_file(base, character)
    local data = {clone = capture_clone(character)}
    local path = CHAR_DIR .. safe_filename(base) .. ".json"
    json.dump_file(path, {format = "hpc2", version = version, source = "current",
        sections = {"clone"}, data = data})
    char_files.parsed[path] = nil
    scan_character_files(true)
    return safe_filename(base) .. ".json"
end

local player_state = {idx = 1}
local all_items_list = nil

re.on_pre_application_entry("UpdateBehavior", function() update_qol(bound_pawn, get_player) end)

function PlayerGear.draw(player)
    if not imgui.tree_node("Equipment: enhancement + special skills##argear") then return end
    local pg = cfg.player_gear
    local gs = player_state.gear or {}
    player_state.gear = gs
    imgui.text_colored("Changes apply to what you're wearing when you press Apply.\nEnhancing puts on an enhanced copy, your original stays in your bag.", 0xFF888888)
    local sk = EqSkill.load()
    local rc, rv = UI.cb("Only show skills that can roll on the item##argroll", cfg.skills_rollable_only ~= false, true)
    if rc then cfg.skills_rollable_only = rv config_changed = true end
    for _, slot in ipairs(ENHANCE_SLOTS) do
        local sd, item, sid = nil, 0, nil
        pcall(function()
            sd = get_slot_item(player, SlotEnum[slot])
            item = sd and sd._ItemId or 0
            sid = item ~= 0 and sd:call("get_StorageId") or nil
        end)
        local st = gs[slot]
        if st and st.stale_until and os.clock() > st.stale_until then st = nil end
        if item ~= 0 and sid then
            if not st or st.sid ~= sid then
                st = {sid = sid, item = item, steps = {0, 0, 0}, dragon = false, ids = {0, 0, 0, 0}, num = 0}
                pcall(function()
                    local e = sd._Enhance
                    local num = sd:call("get_EnhanceNum") or 0
                    local types = {e._Type0, e._Type1, e._Type2}
                    for n = 1, math.min(num, 3) do st.steps[n] = (types[n] or 0) + 1 end
                    st.dragon = num >= 4
                    st.num = num
                end)
                local rec = EqSkill.capture(sd, slot)
                if rec then st.ids = deep_copy(rec.ids) end
                pcall(function() st.name = clean_text(ItemManager:getItemData(item):call("get_Name")) end)
                gs[slot] = st
            end
            if imgui.tree_node(slot .. ": " .. (st.name or ("item " .. item)) .. PlayerGear.plus_text(st.num) .. "###argslot" .. slot) then
                local id = "##argenh" .. slot
                imgui.text("Enhancement")
                for n = 1, 3 do
                    if n > 1 and (st.steps[n - 1] or 0) == 0 then break end
                    imgui.set_next_item_width(200)
                    local c, v = imgui.combo("Step " .. n .. id .. n, (st.steps[n] or 0) + 1, ENHANCE_STEP_NAMES)
                    if c then
                        st.steps[n] = v - 1
                        if v == 1 then for m = n + 1, 3 do st.steps[m] = 0 end end
                    end
                end
                local k = filled_steps(st)
                if k == 3 then
                    local dc, dv = imgui.checkbox("Dragonforged" .. id .. "d", st.dragon)
                    if dc then st.dragon = dv end
                else
                    st.dragon = false
                end
                if k > 0 and imgui.button("Apply enhancement" .. id .. "a") then
                    local ecfg = {enabled = true, steps = deep_copy(st.steps), dragon = st.dragon}
                    table.insert(game_jobs, function() player_state.gear_msg = PlayerGear.enhance(player, slot, ecfg, pg.orig, pg.odata) end)
                end
                local o = pg.orig[slot]
                if o then
                    if k > 0 then imgui.same_line() end
                    if imgui.button("Restore original (" .. (o.name or ("item " .. tostring(o.item))) .. PlayerGear.plus_text(o.num) .. ")" .. id .. "r") then
                        table.insert(game_jobs, function() player_state.gear_msg = PlayerGear.restore(player, slot, pg.orig) end)
                    end
                end
                imgui.spacing()
                if slot ~= "Mantle" then
                imgui.text("Special skills")
                local list, filtered = sk.list, false
                if cfg.skills_rollable_only ~= false then list, filtered = EqSkill.list_for(item) end
                if cfg.skills_rollable_only ~= false and not filtered then
                    imgui.text_colored("(this item has no roll table of its own, showing the general appraisal pool)", 0xFF888888)
                end
                for n = 1, 4 do
                    local c2, v2 = search_combo("argeqs" .. slot .. n, list, st.ids[n] or 0, "No skill", 0)
                    if c2 then st.ids[n] = v2 end
                end
                for _, w in ipairs(EqSkill.check(st.ids, false, item)) do imgui.text_colored("! " .. w, 0xFF33AAFF) end
                if imgui.button("Apply skills##argsa" .. slot) then
                    local ids = deep_copy(st.ids)
                    table.insert(game_jobs, function()
                        EqSkill.apply(player, {[slot] = {enabled = true, ids = ids}}, nil, pg.odata)
                        player_state.gear_msg = "Special skills sent to your " .. slot .. " (the log confirms)"
                    end)
                end
                local pjob = nil
                pcall(function() pjob = current_job(player:call("get_Human")) end)
                local lim = EqSkill.limits(item, pjob)
                if lim then
                    imgui.spacing()
                    imgui.text("Appraisal roll")
                    if not st.stats then
                        st.stats = EqSkill.stats_of(sd) or {phys = 0, magic = 0, blow = 0, weight = 0}
                        st.seen_stats = deep_copy(st.stats)
                    end
                    local rec = pg.odata.eq_sid and pg.odata.eq_sid[tostring(st.sid)]
                    local orig = rec and rec.phys ~= nil and {phys = rec.phys, magic = rec.magic, blow = rec.blow, weight = rec.weight, bonus = rec.bonus} or st.seen_stats
                    EqSkill.stat_ui("##argst" .. slot, st.stats, lim, orig, EqSkill.bonus_pool(item), item)
                    if imgui.button("Apply roll##argstap" .. slot) then
                        local stats = deep_copy(st.stats)
                        table.insert(game_jobs, function()
                            EqSkill.apply(player, {[slot] = {stats_on = true, stats = stats}}, nil, pg.odata)
                            player_state.gear_msg = "Appraisal roll sent to your " .. slot .. " (the log confirms)"
                        end)
                    end
                end
                end
                local cur_key = tostring(st.sid)
                if pg.odata.eq_written and pg.odata.eq_written[cur_key] then
                    imgui.same_line()
                    if imgui.button("Restore original skills + roll##argsr" .. slot) then
                        table.insert(game_jobs, function()
                            EqSkill.restore(player, pg.odata, slot, cur_key)
                            st.stale_until = os.clock() + 0.5
                            player_state.gear_msg = "Original skills going back on your " .. slot
                        end)
                    end
                end
                imgui.tree_pop()
            end
        end
    end
    if player_state.gear_msg then imgui.text(player_state.gear_msg) end
    imgui.tree_pop()
end

function PlayerGear.count_drops(infos)
    local n, tracked = 0, 0
    pcall(function()
        local scene = sdk.call_native_func(sdk.get_native_singleton("via.SceneManager"), sdk.find_type_definition("via.SceneManager"), "get_CurrentScene()")
        local comps = scene:call("findComponents(System.Type)", sdk.typeof("app.Gm82_000_01"))
        for i = 0, comps:get_size() - 1 do
            local okg, g = pcall(function() return comps:get_element(i) end)
            if not (okg and g) then okg, g = pcall(function() return comps:call("Get", i) end) end
            if okg and g and not g:call("get_IsDeleted") then
                n = n + 1
                if infos then
                    pcall(function()
                        if infos:call("ContainsKey", g:get_field("<UniqId>k__BackingField")) then tracked = tracked + 1 end
                    end)
                end
            end
        end
    end)
    return n, tracked
end

local function dict_values(dict)
    local out = {}
    local entries = dict:get_field("_entries")
    for n = 0, entries:get_size() - 1 do
        local okE, e = pcall(function() return entries:get_element(n) end)
        if okE and e then
            local okK, k = pcall(function() return e:get_field("key") end)
            local okV, v = pcall(function() return e:get_field("value") end)
            if okV and v ~= nil then table.insert(out, {key = okK and k or nil, value = v}) end
        end
    end
    return out
end

function PlayerGear.clear_drops()
    if player_state.drops then return end
    player_state.drop_msg = "Clearing..."
    table.insert(game_jobs, function()
        local ok, err = pcall(function()
            local gm = sdk.get_managed_singleton("app.GenerateManager")
            local dlm = gm and gm:call("get_DropItemLostManager")
            local tm = sdk.get_managed_singleton("app.TimeManager")
            if not (dlm and tm) then error("the game's drop tracker isn't running yet") end
            local infos = dlm:get_field("_Infos")
            local before = infos:call("get_Count")
            local loaded, tracked = PlayerGear.count_drops(infos)
            local keys = {}
            for _, kv in ipairs(dict_values(infos)) do
                local okK, key = pcall(function() return kv.value:call("get_TimeCheckKey") end)
                if okK and type(key) == "string" and key ~= "" then keys[key] = true end
            end
            local armed = 0
            for _, kv in ipairs(dict_values(tm:get_field("_DetectionDict"))) do
                local okN, name = pcall(function() return kv.value:get_field("_Name") end)
                local key = (type(kv.key) == "string" and kv.key) or (okN and name) or nil
                if key and keys[key] then
                    if pcall(function()
                        kv.value:set_field("_TargetSecond", 0.0)
                        kv.value:set_field("_IsSatisfy", true)
                    end) then armed = armed + 1 end
                end
            end
            Log(string.format("[drops] before: %d tracked, %d timers found and set to expire now, %d on the ground nearby (%d of those tracked)", before, armed, loaded, tracked))
            local fresh = math.max(0, loaded - tracked)
            if armed == 0 then
                player_state.drop_msg = fresh > 0 and (fresh .. " item(s) near you were dropped this visit,\nthey can be cleared once you've left the area") or "No dropped items found"
                return
            end
            player_state.drops = {dlm = dlm, before = before, loaded = loaded, frames = 0, fresh = fresh}
        end)
        if not ok then
            player_state.drop_msg = "Couldn't clear (see log)"
            Log("[drops] failed: " .. tostring(err))
        end
    end)
end

re.on_frame(function()
    local d = player_state.drops
    if not d then return end
    d.frames = d.frames + 1
    local left = d.before
    pcall(function() left = d.dlm:get_field("_Infos"):call("get_Count") end)
    if d.frames == 120 and left == d.before and not d.kicked then
        d.kicked = true
        table.insert(game_jobs, function()
            local okU, errU = pcall(function() d.dlm:call("onUpdate") end)
            Log("[drops] nudged the game's lost-item check" .. (okU and "" or (": " .. tostring(errU))))
        end)
    end
    if left == 0 or d.frames >= 600 then
        player_state.drops = nil
        local loaded_after = PlayerGear.count_drops(nil)
        Log(string.format("[drops] after: %d tracked (was %d), %d on the ground nearby (was %d)", left, d.before, loaded_after, d.loaded))
        local cleared = d.before - left
        if cleared > 0 then
            player_state.drop_msg = "Cleared " .. cleared .. " dropped item(s)" .. ((d.fresh or 0) > 0 and (",\n" .. d.fresh .. " dropped this visit stay until you've left the area") or "")
        else
            player_state.drop_msg = "Timers expired, the game clears them on its next check (rest or travel)"
        end
    end
end)

local function draw_player_misc()
    local player = get_player()
    imgui.text("Player appearance")
    if not player then
        imgui.text("  (load into the game first)")
        return
    end
    if imgui.button("Export Arisen appearance") then
        player_state.status = "Saved " .. write_look_file("Player-current", player)
    end

    local files, names = {}, {}
    for _, f in ipairs(scan_character_files()) do
        local secs = {}
        for _, k in ipairs(file_sections(f)) do secs[k] = true end
        if secs.clone and f.data.clone ~= nil then
            table.insert(files, {info = f, clone = true})
            table.insert(names, f.name)
        end
    end
    if #files == 0 then
        imgui.text("No appearance files found (" .. #scan_character_files() .. " files scanned). Export one first.")
    else
        player_state.idx = math.min(player_state.idx, #files)
        imgui.set_next_item_width(300)
        local c, v = imgui.combo("Look file##plf", player_state.idx, names)
        if c then player_state.idx = v end
        local pick = files[player_state.idx]
        local function backup()
            return write_look_file("Player-backup-" .. os.date("%Y%m%d-%H%M%S"), player)
        end
        local warn = "\n\nA backup of your current appearance is exported to characters\\ first,\nso you can import it again to revert."
        if pick.clone and imgui.button("Import appearance to Arisen") then
            local data, fname = pick.info.data.clone, pick.info.name
            ask_confirm("Import full appearance", "This will completely overwrite the Arisen's appearance\nwith " .. fname .. ".json" .. warn, function()
                local b = backup()
                player_state.status = apply_clone(player, data) .. " (backup: " .. b .. ")"
            end)
        end
        imgui.text("Your current look is backed up to characters\\ before every import.")
    end
    if player_state.status then imgui.text(player_state.status) end

    imgui.spacing()
    imgui.separator()
    imgui.text("Item spawner")
    if not all_items_list then
        all_items_list = {}
        pcall(function()
            local entries = ItemManager._ItemDataDict._entries
            for n = 0, entries:get_size() - 1 do
                local e = entries:get_element(n)
                local p = e and (e.value or e.Value)
                if p then
                    local id = p:call("get_Id")
                    local nm = clean_text(p:call("get_Name"))
                    if id and id > 0 and nm then table.insert(all_items_list, {id = id, name = nm .. " (ID: " .. id .. ")"}) end
                end
            end
        end)
        table.sort(all_items_list, function(a, b) return a.name < b.name end)
        if #all_items_list == 0 then all_items_list = nil end
    end
    if all_items_list then
        local c, v = search_combo("spawnitem", all_items_list, player_state.spawn_id or 0, "Pick an item", 0)
        if c then player_state.spawn_id = v end
        imgui.set_next_item_width(120)
        local qc, qv = imgui.input_text("Quantity##spawnq", tostring(player_state.spawn_qty or 1))
        if qc then player_state.spawn_qty = math.max(1, math.min(999, tonumber(qv) or 1)) end
        imgui.same_line()
        if imgui.button("Add to inventory##spawn") and (player_state.spawn_id or 0) > 0 then
            local qty, item = player_state.spawn_qty or 1, player_state.spawn_id
            table.insert(game_jobs, function()
                local ok, err = pcall(function()
                    local opt = make_get_item_option()
                    if opt and getItemWithOption then
                        getItemWithOption:call(ItemManager, item, qty, player, opt)
                    else
                        getItemPlain:call(ItemManager, item, qty, player)
                    end
                end)
                player_state.status = ok and ("Added " .. qty .. "x " .. (name_of(all_items_list, item) or item))
                    or ("Spawn failed: " .. tostring(err))
            end)
        end
    else
        imgui.text("  (item list loads once you're in the game)")
    end
    imgui.spacing()
    imgui.separator()
    PlayerGear.draw(player)
    if imgui.tree_node("Arisen QoL + Testing") then
        draw_qol("player", cfg.player_qol, player, false, nil)
        imgui.spacing()
        if imgui.button("Remove all dropped items##drops") then
            ask_confirm("Remove dropped items", "Everything lying on the ground gets cleared,\nthe same way the game removes drops when they time out.", PlayerGear.clear_drops,
                "You must move or teleport away from the dropped items before running this.")
        end
        if player_state.drop_msg then imgui.text(player_state.drop_msg) end
        -- removed from public release: main pawn stats ui
        imgui.tree_pop()
    end
end

local function draw_files(i)
    local key = "pawn" .. i
    local pawn = get_hired_pawn(i)
    if not pawn then return end
    if not imgui.tree_node("Import/Export##files" .. key) then return end
    local st = ui_state.files[i]
    if not st then
        st = {source = 1, export_pick = {}, file_idx = 1, import_pick = {}, last_file = nil,
            name = ctx_name(get_data_context(get_character(pawn))) or ("Pawn " .. i)}
        for _, s in ipairs(SECTIONS) do st.export_pick[s.key] = not s.soon end
        ui_state.files[i] = st
    end

    if imgui.tree_node("Export##exp" .. key) then
        imgui.set_next_item_width(200)
        local nc, nv = imgui.input_text("File name##expn" .. key, st.name)
        if nc then st.name = nv end
        imgui.set_next_item_width(200)
        local sc, sv = imgui.combo("Source##exps" .. key, st.source, SOURCES)
        if sc then st.source = sv end
        imgui.same_line()
        imgui.text(({"as first hired", "as they are right now", "your override settings"})[st.source])
        for _, s in ipairs(SECTIONS) do
            if s.soon then
                imgui.text("  " .. s.label .. " (coming soon)")
            else
                local c, v = imgui.checkbox(s.label .. "##expc" .. key .. s.key, st.export_pick[s.key])
                if c then st.export_pick[s.key] = v end
            end
        end
        if imgui.button("All##expall" .. key) then
            for _, s in ipairs(SECTIONS) do st.export_pick[s.key] = not s.soon end
        end
        imgui.same_line()
        if imgui.button("None##expnone" .. key) then
            for _, s in ipairs(SECTIONS) do st.export_pick[s.key] = false end
        end
        imgui.same_line()
        if imgui.button("Export##expgo" .. key) then
            st.status = export_sections(i, st.source, st.export_pick, st.name)
        end
        imgui.tree_pop()
    end

    if imgui.tree_node("Import##imp" .. key) then
        local files = scan_character_files()
        if #files == 0 then
            imgui.text("No files in characters\\ yet")
        else
            local names = {}
            for n, f in ipairs(files) do names[n] = f.name end
            st.file_idx = math.min(st.file_idx, #files)
            imgui.set_next_item_width(300)
            local fc, fv = imgui.combo("File##impf" .. key, st.file_idx, names)
            if fc then st.file_idx = fv end
            local info = files[st.file_idx]
            local secs = file_sections(info)
            if st.last_file ~= info.path then
                st.last_file = info.path
                st.import_pick = {}
                for _, k in ipairs(secs) do st.import_pick[k] = true end
            end
            for _, k in ipairs(secs) do
                for _, s in ipairs(SECTIONS) do
                    if s.key == k then
                        local c, v = imgui.checkbox(s.label .. "##impc" .. key .. k, st.import_pick[k] or false)
                        if c then st.import_pick[k] = v end
                    end
                end
            end
            if imgui.button("Import##impgo" .. key) then
                local function go()
                    st.status = import_sections(i, info, st.import_pick)
                    ui_state.name_input[i] = nil
                end
                if i == 0 then
                    local picks = {}
                    for _, s in ipairs(SECTIONS) do if st.import_pick[s.key] then table.insert(picks, s.label) end end
                    ask_confirm("Import to Main Pawn", "This will overwrite your Main Pawn's " .. table.concat(picks, ", ")
                        .. "\nwith " .. info.name .. ".json\n\nTheir original state is saved, so Restore can put it back.", go)
                else
                    go()
                end
            end
        end
        imgui.tree_pop()
    end
    if st.status then imgui.text(st.status) end
    imgui.tree_pop()
end

local function draw_restore(i)
    local orig = slot_original(i)
    if not (orig and get_hired_pawn(i)) then return end
    imgui.spacing()
    imgui.text(string.format("Original: %s, %s rank %s, level %s", tostring(orig.name),
        tostring(name_of(Lists.jobs, orig.job) or "?"), tostring(orig.job_rank),
        tostring(orig.status and orig.status.level or "?")))
    if imgui.button("Restore original appearance##rapp" .. i) then request_restore(i, {"appearance"}) end
    if imgui.button("Restore everything##rall" .. i) then
        local function go()
            request_restore(i, RESTORE_PARTS)
            cfg["pawn" .. i].enabled = false
        end
        if i == 0 then
            ask_confirm("Restore Main Pawn", "This resets every section of your Main Pawn to the state\nthe mod first saw them in (" .. tostring(orig.name) .. "), and turns control off.", go)
        else
            go()
        end
    end
    imgui.same_line()
    imgui.text("(every section back to original, control off)")
end
do
    local pages = {
        {"Welcome", "The Pawn Controller allows you to edit various options for each pawn in your party:\n\n"
            .. "- Gear: <pawn> > Equipment\n"
            .. "- Enhancements: <pawn> > Equipment\n"
            .. "- Vocation: <pawn> > Vocation + Skills\n"
            .. "- Skills: <pawn> > Vocation + Skills\n"
            .. "- Augments: <pawn> > Vocation + Skills\n"
            .. "- Personality, Specialization and Voice: <pawn> > Attributes\n"
            .. "- Appearance: <pawn> > Import/Export\n"
            .. "- Chatter: <pawn> > Behaviour\n"
            .. "- Knowledge: <pawn> > Knowledge\n"
            .. "- QoL and testing tools: <pawn> > QoL + Testing\n"
            .. "- Presets: <pawn> > Presets\n"
            .. "- And more...\n\n"
            .. "You can skip this guide and re-open it from the 'How to use' section."},
        {"Pick a pawn", "Each party slot has its own section.\nEnable 'Edit this pawn' to start, and keep it enabled.\nThe options are applied to the pawn automatically when loading.\n\nSome options are saved, some are overrides,\nleaving it enabled will ensure every option gets applied."},
        {"Editing pawns", "Find the pawn you wish to edit in the list and enable 'Edit this pawn'.\nPick the category you want, such as Equipment.\n\nThe box on the left lets you search, the dropdown next to it\nis filtered by your search and lets you pick what the pawn should use.\nChanges apply within a second or two."},
        {"Undo - Restoring original values", "The mod saves each pawn's original state the first time you edit them.\nVarious 'Restore' buttons revert the setting back to the value the pawn had originally."},
        {"Main pawn warning!", "Any changes to your main pawn are permanent.\nThe game runs various verifications before uploading your pawn,\nand when other players' games show the pawn in-game.\n\nMaking changes which could fail verification may prevent your pawn being shareable.\n\nYou can validate your pawn using the 'Validate Pawn' option under Main Pawn > QoL + Testing.",
            "Make a save backup before editing your main pawn!"},
        {"Presets + extras", {
            "Presets save your mod settings so you can quickly apply them to another pawn.",
            {{"Import/Export can clone an entire pawn,"}, {"including the full appearance.", 0xFFFFDD55}},
            "Misc has the item spawner and tools for your Arisen.",
            "Options + Debug has the extra settings."}},
    }
    local function close_tour()
        ui_state.tour_open = false
        if not cfg.tutorial_seen then cfg.tutorial_seen = true config_changed = true end
    end
    re.on_frame(function()
        if not ui_state.tour_open then return end
        local p = math.max(1, math.min(ui_state.tour_page or 1, #pages))
        local still = imgui.begin_window("The Pawn Controller: first start guide###tpc_tour", true, 64)
        imgui.text_colored(pages[p][1] .. "   (" .. p .. "/" .. #pages .. ")", 0xFF33AAFF)
        imgui.spacing()
        local body = pages[p][2]
        if type(body) == "table" then
            for _, ln in ipairs(body) do
                if type(ln) == "string" then
                    imgui.text(ln)
                else
                    for k, seg in ipairs(ln) do
                        if k > 1 then imgui.same_line() end
                        if seg[2] then imgui.text_colored(seg[1], seg[2]) else imgui.text(seg[1]) end
                    end
                end
            end
        else
            imgui.text(body)
        end
        if pages[p][3] then
            imgui.spacing()
            imgui.text_colored(pages[p][3], 0xFF4C4CFF)
        end
        imgui.spacing()
        if p > 1 then
            if imgui.button("Back##tourb") then ui_state.tour_page = p - 1 end
            imgui.same_line()
        end
        if p < #pages then
            if imgui.button("Next##tourn") then ui_state.tour_page = p + 1 end
            local pad = 4
            pcall(function()
                local w = imgui.get_window_size().x
                local sp = imgui.calc_text_size(" ").x
                local used = imgui.calc_text_size("Next").x + 24 + (p > 1 and (imgui.calc_text_size("Back").x + 32) or 0)
                local skip_w = imgui.calc_text_size("Skip guide").x + 24
                if sp > 0 then pad = math.max(4, math.floor((w - used - skip_w - 24) / sp)) end
            end)
            imgui.same_line()
            imgui.text(string.rep(" ", pad))
            imgui.same_line()
            if imgui.button("Skip guide##tours") then close_tour() end
        elseif imgui.button("Finish guide##tourd") then
            close_tour()
        end
        imgui.end_window()
        if still == false then close_tour() end
    end)
end

re.on_draw_ui(function()
    if not imgui.tree_node("The Pawn Controller [v" .. version .. "]") then return end
    if not cfg.tutorial_seen and not ui_state.tour_open and not ui_state.tour_shown then
        ui_state.tour_open, ui_state.tour_page, ui_state.tour_shown = true, 1, true
    end
    if imgui.tree_node("How to use##howto") then
        imgui.text("1. Open a pawn's section and tick 'Edit this pawn'.")
        imgui.text("2. Change what you want in the categories below it.")
        imgui.text("3. Restore buttons put the pawn's originals back.")
        imgui.text("4. Keep 'Edit this pawn' ticked so your settings apply when you load.")
        imgui.text_colored("Anything shown in yellow has been changed from its default.", UI.CHANGED)
        imgui.text_colored("Main Pawn changes are permanent. Hired pawn changes only affect your copy.", 0xFF8080FF)
        if imgui.button("Show the first start guide##tourre") then ui_state.tour_open, ui_state.tour_page = true, 1 end
        imgui.tree_pop()
    end
    resolve_names()

    if items_source == "none" then imgui.text_colored("No item data yet (loads once in-game)", 0xFF0000FF) end

    for _, i in ipairs(SLOT_IDS) do
        if slot_reset[i] then
            slot_reset[i] = nil
            ui_state.name_input[i] = nil
            ui_state.files[i] = nil
        end
        local ctx = get_data_context(get_character(get_hired_pawn(i)))
        local label = ctx and ("[" .. (ctx_name(ctx) or "?") .. "]") or "[None]"
        local hidden = i > 2 and not ctx and not cfg["pawn" .. i].enabled
        if not hidden and imgui.tree_node(SLOT_NAMES[i] .. " " .. label .. "###slot" .. i) then
            if not ctx and not cfg.allow_empty_slots then
                imgui.text("No pawn hired in this slot.")
            else
                local c, v = UI.cb("Edit this pawn##pawn" .. i, cfg["pawn" .. i].enabled)
                if c then cfg["pawn" .. i].enabled = v mark(i) end
                if cfg["pawn" .. i].enabled then
                    imgui.same_line()
                    if imgui.button("Force Reapply##fr" .. i) then modified[i] = false job_wait[i] = 0 end
                end
                imgui.text_colored("Settings will be applied to this pawn, keep enabled to apply changes when loading", 0xFF888888)

                if cfg["pawn" .. i].enabled then draw_pawn(i) end
                draw_files(i)
                draw_restore(i)
            end
            imgui.tree_pop()
        end
    end

    if imgui.tree_node("Misc") then
        draw_player_misc()
        imgui.tree_pop()
    end

    if imgui.tree_node("Options + Debug") then
        local ec, ev = UI.cb("Allow setting up empty pawn slots (settings go to the next pawn hired into that slot)", cfg.allow_empty_slots)
        if ec then cfg.allow_empty_slots = ev config_changed = true end

        local hc, hv = UI.cb("Allow hired pawns to level from EXP##hirelvl", cfg.hire_levelup == true)
        if hc then cfg.hire_levelup = hv config_changed = true end
        imgui.text_colored("Allow hired pawns to level from EXP as your main pawn does.", 0xFF888888)
        imgui.text_colored("EXP already earned by hired pawns will be included, so hired pawns may jump in level after enabling.", 0xFF8080FF)

        local fc, fv = UI.cb("Ignore vocation restrictions for equipment overrides", cfg.force_equip == true)
        if fc then
            cfg.force_equip = fv
            config_changed = true
            if not fv then relock_items() end
            for _, j in ipairs(SLOT_IDS) do modified[j] = false end
        end
        imgui.text_colored("Only the items you pick in an equipment override are modified.\nEnabling this removes the limit from the item itself.", 0xFF888888)

        -- removed from public release: something capcom should've never left included [toggle]
        imgui.spacing()
        local lu, lv = UI.cb("Log pawn uploads (applies after Reset Scripts)##logup", cfg.log_uploads ~= false, true)
        if lu then cfg.log_uploads = lv config_changed = true end
        imgui.spacing()
        imgui.text("Debug logging")
        for _, d in ipairs({{"enable_startup_logs", "Startup (item and name loading)"}, {"enable_search_logs", "Search boxes"},
            {"enable_equipment_logs", "Equipment, enhancement + special skills"}, {"enable_attribute_logs", "Skills, attributes + vocation"}}) do
            local c2, v2 = UI.cb(d[2] .. "##dbg" .. d[1], cfg.debug[d[1]])
            if c2 then cfg.debug[d[1]] = v2 config_changed = true end
        end
        imgui.tree_pop()
    end

    imgui.separator()
    if imgui.button("Save Configuration") then save_config() end
    if config_changed then
        imgui.same_line()
        imgui.text_colored("(Unsaved changes)", 0xFF00FFFF)
    end
    imgui.tree_pop()
end)

re.on_config_save(function() if config_changed then save_config() end end)
end
setup_ui()
