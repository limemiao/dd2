local TAG = "[PawnStudioCatalog] "
local done = false

local function enum_values(type_name, unsigned)
    local out = {}
    local type_def = sdk.find_type_definition(type_name)
    if not type_def then
        log.warn(TAG .. "Enum not found: " .. type_name)
        return out
    end
    for _, field in ipairs(type_def:get_fields()) do
        if field:is_static() then
            local ok, value = pcall(field.get_data, field, nil)
            if ok and type(value) == "number" then
                if unsigned and value < 0 then value = value + 4294967296 end
                table.insert(out, {id = value, name = field:get_name()})
            end
        end
    end
    table.sort(out, function(a, b) return a.id < b.id end)
    return out
end

local function split_camel(value)
    return (value:gsub("(%l)(%u)", "%1 %2"):gsub("(%u)(%u%l)", "%1 %2"))
end

local function build()
    local jobs, personality, spec, gender, tone = {}, {}, {}, {}, {}
    local skills, abilities, core, eq_skills = {}, {}, {}, {}

    for _, entry in ipairs(enum_values("app.Character.JobEnum")) do
        if entry.id > 0 then table.insert(jobs, entry) end
    end
    for _, entry in ipairs(enum_values("app.PersonalityDefine.PersonalityID", true)) do
        if entry.id ~= 0 then table.insert(personality, entry) end
    end
    for _, entry in ipairs(enum_values("app.PawnDefine.SubSkillID")) do
        table.insert(spec, entry)
    end
    for _, entry in ipairs(enum_values("app.Gender", true)) do
        if entry.id ~= 0 then table.insert(gender, entry) end
    end
    for _, entry in ipairs(enum_values("app.SoundVoiceManager.VoiceToneType")) do
        table.insert(tone, entry)
    end
    for _, entry in ipairs(enum_values("app.HumanCustomSkillID")) do
        local job, rest = entry.name:match("^Job(%d%d)_(.+)$")
        if job and entry.id > 0 then
            table.insert(skills, {id = entry.id, job = tonumber(job), name = split_camel(rest)})
        end
    end
    for _, entry in ipairs(enum_values("app.HumanAbilityID")) do
        if entry.id > 0 and not entry.name:find("^Dummy") then
            local job, number = entry.name:match("^Job(%d%d)_(%d%d)$")
            table.insert(abilities, {
                id = entry.id,
                job = job and tonumber(job) or 0,
                name = job and ("Job " .. job .. " augment " .. (tonumber(number) + 1)) or entry.name
            })
        end
    end
    for _, entry in ipairs(enum_values("app.HumanNormalSkillID")) do
        local job, rest = entry.name:match("^Job(%d%d)_(.+)$")
        if job then
            table.insert(core, {id = entry.id, job = tonumber(job), name = split_camel(rest)})
        end
    end
    for _, entry in ipairs(enum_values("app.EquipmentAbilityID")) do
        if entry.id ~= 0 and entry.name ~= "None" and entry.name ~= "Dummy" then
            table.insert(eq_skills, {id = entry.id, name = split_camel(entry.name)})
        end
    end

    return {
        format = "dd2-pawn-studio-catalog",
        version = 1,
        generated_at = os.date("%Y-%m-%dT%H:%M:%S"),
        jobs = jobs,
        personality = personality,
        spec = spec,
        gender = gender,
        tone = tone,
        skills = skills,
        abilities = abilities,
        core = core,
        eq_skills = eq_skills
    }
end

re.on_frame(function()
    if done then return end
    done = true
    local ok, data = pcall(build)
    if not ok then
        log.error(TAG .. "Catalog build failed: " .. tostring(data))
        return
    end
    local saved, err = pcall(json.dump_file, "ThePawnController\\pawn_studio_catalog.json", data)
    if saved then
        log.info(string.format(
            TAG .. "Saved jobs=%d personality=%d spec=%d gender=%d tone=%d skills=%d abilities=%d core=%d eq_skills=%d",
            #data.jobs, #data.personality, #data.spec, #data.gender, #data.tone,
            #data.skills, #data.abilities, #data.core, #data.eq_skills
        ))
    else
        log.error(TAG .. "Failed to save catalog: " .. tostring(err))
    end
end)
