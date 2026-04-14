if SERVER then
    AddCSLuaFile()
    AddCSLuaFile("pmx_static_importer/sh_core.lua")
    AddCSLuaFile("pmx_static_importer/cl_runtime.lua")
    AddCSLuaFile("pmx_static_importer/cl_material_editor.lua")
    AddCSLuaFile("pmx_static_importer/cl_bone_picker.lua")
    AddCSLuaFile("pmx_static_importer/cl_mesh_editor.lua")
    util.AddNetworkString("pmx_bone_bind")
    util.AddNetworkString("pmx_bone_pick")
    util.AddNetworkString("pmx_bone_edit")
    util.AddNetworkString("pmx_bone_edit_pick")
end

include("pmx_static_importer/sh_core.lua")
if CLIENT then
    include("pmx_static_importer/cl_runtime.lua")
    include("pmx_static_importer/cl_material_editor.lua")
    include("pmx_static_importer/cl_bone_picker.lua")
    include("pmx_static_importer/cl_mesh_editor.lua")
    PMXStaticImporter.RegisterLanguagePhrases()
end

TOOL.Category = "#pmx_static_importer.category"
TOOL.Name = "#tool.pmx_static_importer.name"
TOOL.Command = nil
TOOL.ConfigName = ""

TOOL.ClientConVar = {
    modelid = "",
    scale = "1.0",
    yaw = "0",
    physprop = "default",
    nocollide = "1",
    nogravity = "0",
    color_r = "255",
    color_g = "255",
    color_b = "255",
}

local function is_imported_entity(ent)
    return IsValid(ent) and ent:GetClass() == "sent_pmx_static_imported"
end

local function get_selected_model_id(tool)
    local raw = tool:GetClientInfo("modelid")
    return PMXStaticImporter.NormalizeModelID(raw)
end

local function get_tool_scale(tool)
    return math.max(tonumber(tool:GetClientInfo("scale")) or 1, 0.0001)
end

local function get_tool_yaw(tool)
    return tonumber(tool:GetClientInfo("yaw")) or 0
end

local function tool_msg(ply, key, ...)
    return PMXStaticImporter.ToolPrefix(ply) .. " " .. PMXStaticImporter.TF(key, ply, ...)
end

if CLIENT then
    language.Add("tool.pmx_static_importer.name", PMXStaticImporter.T("tool_name"))
    language.Add("tool.pmx_static_importer.desc", PMXStaticImporter.T("tool_desc"))
    language.Add("tool.pmx_static_importer.0", PMXStaticImporter.T("tool_help"))
end

function TOOL:LeftClick(trace)
    if CLIENT then return true end

    local modelID = get_selected_model_id(self)
    if not modelID then
        self:GetOwner():ChatPrint(tool_msg(self:GetOwner(), "chat_no_imported_model_selected"))
        return false
    end

    local manifest, err = PMXStaticImporter.LoadManifest(modelID, self:GetOwner())
    if not manifest then
        self:GetOwner():ChatPrint(PMXStaticImporter.ToolPrefix(self:GetOwner()) .. " " .. tostring(err or PMXStaticImporter.T("error_manifest_could_not_be_loaded", self:GetOwner())))
        return false
    end

    local mins = PMXStaticImporter.GetBoundsFromManifest(manifest)
    local minsVec = mins
    local lift = math.max(0, -(minsVec.z or 0) * get_tool_scale(self))

    local ent = ents.Create("sent_pmx_static_imported")
    if not IsValid(ent) then
        self:GetOwner():ChatPrint(tool_msg(self:GetOwner(), "chat_failed_create_entity"))
        return false
    end

    local pos = trace.HitPos + trace.HitNormal * lift
    local ang = Angle(0, self:GetOwner():EyeAngles().y + get_tool_yaw(self), 0)

    ent:SetPos(pos)
    ent:SetAngles(ang)
    ent:Spawn()
    ent:Activate()

    local ok, applyErr = ent:ApplyImportedModel(modelID, get_tool_scale(self), self:GetOwner())
    if not ok then
        ent:Remove()
        self:GetOwner():ChatPrint(PMXStaticImporter.ToolPrefix(self:GetOwner()) .. " " .. tostring(applyErr or PMXStaticImporter.T("error_failed_to_apply_imported_model", self:GetOwner())))
        return false
    end

    -- Apply physics properties
    local phys = ent:GetPhysicsObject()
    if IsValid(phys) then
        local physprop = self:GetClientInfo("physprop") or "default"
        if physprop ~= "" and physprop ~= "default" then
            phys:SetMaterial(physprop)
        end

        local noGravity = tobool(self:GetClientInfo("nogravity"))
        if noGravity then
            phys:EnableGravity(false)
        else
            phys:EnableGravity(true)
        end

        phys:Wake()
        phys:EnableMotion(false)
    end

    local noCollide = tobool(self:GetClientInfo("nocollide"))
    if noCollide then
        ent:SetCollisionGroup(COLLISION_GROUP_WORLD)
    end

    local cr = math.Clamp(tonumber(self:GetClientInfo("color_r")) or 255, 0, 255) / 255
    local cg = math.Clamp(tonumber(self:GetClientInfo("color_g")) or 255, 0, 255) / 255
    local cb = math.Clamp(tonumber(self:GetClientInfo("color_b")) or 255, 0, 255) / 255
    ent:SetPMXColor(Vector(cr, cg, cb))

    undo.Create(PMXStaticImporter.T("entity_name", self:GetOwner()))
        undo.AddEntity(ent)
        undo.SetPlayer(self:GetOwner())
    undo.Finish()

    cleanup.Add(self:GetOwner(), "props", ent)

    self:GetOwner():ChatPrint(tool_msg(self:GetOwner(), "chat_spawned", tostring(manifest.display_name or modelID)))
    return true
end

if SERVER then
    net.Receive("pmx_bone_bind", function(len, ply)
        if not IsValid(ply) then return end

        local targetEnt = net.ReadEntity()
        local boneIndex = net.ReadUInt(10)
        local offsetPos = net.ReadVector()
        local offsetAng = net.ReadAngle()
        local modelID = net.ReadString()
        local scale = net.ReadFloat()
        local cr = net.ReadUInt(8)
        local cg = net.ReadUInt(8)
        local cb = net.ReadUInt(8)
        local enableCollision = net.ReadBool()

        if not IsValid(targetEnt) then return end

        modelID = PMXStaticImporter.NormalizeModelID(modelID)
        if not modelID then
            ply:ChatPrint(PMXStaticImporter.ToolPrefix(ply) .. " " .. PMXStaticImporter.T("chat_no_imported_model_selected", ply))
            return
        end

        local manifest, err = PMXStaticImporter.LoadManifest(modelID, ply)
        if not manifest then
            ply:ChatPrint(PMXStaticImporter.ToolPrefix(ply) .. " " .. tostring(err or PMXStaticImporter.T("error_manifest_could_not_be_loaded", ply)))
            return
        end

        local boneCount = targetEnt:GetBoneCount() or 0
        if boneIndex < 0 or boneIndex >= boneCount then
            return
        end

        local ent = ents.Create("sent_pmx_static_imported")
        if not IsValid(ent) then
            ply:ChatPrint(PMXStaticImporter.ToolPrefix(ply) .. " " .. PMXStaticImporter.T("chat_failed_create_entity", ply))
            return
        end

        -- Initial position from bone
        local matrix = targetEnt:GetBoneMatrix(boneIndex)
        local bonePos = matrix and matrix:GetTranslation() or targetEnt:GetPos()
        local boneAng = matrix and matrix:GetAngles() or targetEnt:GetAngles()
        local finalPos, finalAng = LocalToWorld(offsetPos, offsetAng, bonePos, boneAng)

        ent:SetPos(finalPos)
        ent:SetAngles(finalAng)
        ent:Spawn()
        ent:Activate()

        scale = math.max(tonumber(scale) or 1, 0.0001)
        local ok, applyErr = ent:ApplyImportedModel(modelID, scale, ply)
        if not ok then
            ent:Remove()
            ply:ChatPrint(PMXStaticImporter.ToolPrefix(ply) .. " " .. tostring(applyErr or PMXStaticImporter.T("error_failed_to_apply_imported_model", ply)))
            return
        end

        -- Set bone binding
        ent:SetPMXBindTarget(targetEnt)
        ent:SetPMXBindBone(boneIndex)
        ent:SetPMXBindPos(offsetPos)
        ent:SetPMXBindAng(offsetAng)

        -- Set color
        ent:SetPMXColor(Vector(cr / 255, cg / 255, cb / 255))

        -- Disable physics for bone-bound entity unless collision enabled
        if not enableCollision then
            ent:SetMoveType(MOVETYPE_NONE)
            ent:SetSolid(SOLID_NONE)
            ent:SetCollisionGroup(COLLISION_GROUP_IN_VEHICLE)
            ent:PhysicsDestroy()
            ent:SetNotSolid(true)
        end

        undo.Create(PMXStaticImporter.T("entity_name", ply))
            undo.AddEntity(ent)
            undo.SetPlayer(ply)
        undo.Finish()

        cleanup.Add(ply, "props", ent)

        local boneName = targetEnt:GetBoneName(boneIndex) or tostring(boneIndex)
        ply:ChatPrint(PMXStaticImporter.ToolPrefix(ply) .. " " .. PMXStaticImporter.TF("chat_bone_bound", ply, boneName))
    end)

    net.Receive("pmx_bone_edit", function(len, ply)
        if not IsValid(ply) then return end

        local boundEnt = net.ReadEntity()
        local offsetPos = net.ReadVector()
        local offsetAng = net.ReadAngle()
        local scale = net.ReadFloat()

        if not IsValid(boundEnt) then return end
        if boundEnt:GetClass() ~= "sent_pmx_static_imported" then return end

        boundEnt:SetPMXBindPos(offsetPos)
        boundEnt:SetPMXBindAng(offsetAng)

        scale = math.max(tonumber(scale) or 1, 0.0001)
        boundEnt:SetPMXScale(scale)
        boundEnt:RebuildPhysics()
    end)
end

if CLIENT then
    net.Receive("pmx_bone_pick", function()
        local ent = net.ReadEntity()
        if not IsValid(ent) then return end
        PMXStaticImporter.OpenBonePicker(ent)
    end)

    net.Receive("pmx_bone_edit_pick", function()
        local ent = net.ReadEntity()
        local count = net.ReadUInt(8)
        local boundEnts = {}
        for i = 1, count do
            boundEnts[i] = net.ReadEntity()
        end
        if not IsValid(ent) then return end
        PMXStaticImporter.OpenBoneEditor(ent, boundEnts)
    end)
end

function TOOL:RightClick(trace)
    local ent = trace.Entity
    if not IsValid(ent) then return false end
    if CLIENT then return true end

    -- R + RightClick: remove all bone-bound models from this entity
    if self:GetOwner():KeyDown(IN_RELOAD) then
        local removed = 0
        for _, child in ipairs(ents.FindByClass("sent_pmx_static_imported")) do
            if IsValid(child) and child.GetPMXBindTarget and child:GetPMXBindTarget() == ent then
                child:Remove()
                removed = removed + 1
            end
        end
        self:GetOwner():ChatPrint(tool_msg(self:GetOwner(), "chat_bone_unbound_all", removed))
        return true
    end

    -- Shift + RightClick: edit existing bone-bound models on this entity
    if self:GetOwner():KeyDown(IN_SPEED) then
        local boundEnts = {}
        for _, child in ipairs(ents.FindByClass("sent_pmx_static_imported")) do
            if IsValid(child) and child.GetPMXBindTarget and child:GetPMXBindTarget() == ent then
                boundEnts[#boundEnts + 1] = child
            end
        end
        if #boundEnts == 0 then return false end

        net.Start("pmx_bone_edit_pick")
            net.WriteEntity(ent)
            net.WriteUInt(#boundEnts, 8)
            for _, child in ipairs(boundEnts) do
                net.WriteEntity(child)
            end
        net.Send(self:GetOwner())
        return true
    end

    local boneCount = ent:GetBoneCount() or 0
    if boneCount <= 0 then return false end

    net.Start("pmx_bone_pick")
        net.WriteEntity(ent)
    net.Send(self:GetOwner())

    return true
end

function TOOL:Reload(trace)
    if CLIENT then return true end

    local ent = trace.Entity
    if not is_imported_entity(ent) then
        return false
    end

    ent:Remove()
    self:GetOwner():ChatPrint(tool_msg(self:GetOwner(), "chat_removed_imported_entity"))
    return true
end

local function format_model_row(entry)
    return {
        entry.display_name or entry.model_id or "",
        entry.model_id or "",
        tostring(entry.triangle_count or 0),
        tostring(entry.material_count or 0),
    }
end

function TOOL.BuildCPanel(panel)
    local L = function(key)
        return PMXStaticImporter.T(key)
    end

    panel:AddControl("Header", {
        Description = L("panel_description")
    })

    local refreshButton = panel:Button(L("button_refresh_imported_model_list"))
    refreshButton.DoClick = function()
        RunConsoleCommand("pmx_static_importer_refresh")
    end

    local refreshMeshesButton = panel:Button(L("button_refresh_meshes"))
    refreshMeshesButton.DoClick = function()
        RunConsoleCommand("pmx_static_importer_clear_cache")
        RunConsoleCommand("pmx_static_importer_refresh")
    end

    local clearCacheButton = panel:Button(L("button_clear_client_cache"))
    clearCacheButton.DoClick = function()
        RunConsoleCommand("pmx_static_importer_clear_cache")
    end

    local removeAllButton = panel:Button(L("button_remove_all_spawned"))
    removeAllButton.DoClick = function()
        RunConsoleCommand("pmx_static_importer_remove_all")
    end

    local modelList = vgui.Create("DListView")
    modelList:SetTall(260)
    modelList:SetMultiSelect(false)
    modelList:AddColumn(L("panel_display_name"))
    modelList:AddColumn(L("panel_model_id"))
    modelList:AddColumn(L("panel_triangles"))
    modelList:AddColumn(L("panel_materials"))

    function modelList:Populate(entries)
        self:Clear()
        for _, entry in ipairs(entries or {}) do
            local line = self:AddLine(unpack(format_model_row(entry)))
            line.ModelID = entry.model_id
        end
    end

    modelList.OnRowSelected = function(_, _, line)
        if not IsValid(line) or not line.ModelID then return end
        RunConsoleCommand("pmx_static_importer_modelid", line.ModelID)
    end

    panel:AddItem(modelList)
    panel:TextEntry(L("panel_selected_model_id"), "pmx_static_importer_modelid")
    panel:NumSlider(L("panel_scale"), "pmx_static_importer_scale", 0.001, 20, 3)
    panel:NumSlider(L("panel_yaw"), "pmx_static_importer_yaw", -180, 180, 0)

    -- Physics properties
    panel:Help("")
    local physLabel = vgui.Create("DLabel")
    physLabel:SetText(L("panel_physics_properties"))
    physLabel:SetDark(true)
    physLabel:SetFont("DermaDefaultBold")
    physLabel:SizeToContents()
    panel:AddItem(physLabel)

    local physCombo = vgui.Create("DComboBox")
    physCombo:SetTall(22)
    physCombo:SetValue("default")
    physCombo:AddChoice("default", "default", true)
    local surfaceNames = {
        "metal", "metal_bouncy", "metal_box", "metal_computer",
        "wood", "wood_crate", "wood_plank", "wood_panel",
        "concrete", "concrete_block", "tile",
        "glass", "glass_sheet",
        "flesh", "bloodyflesh", "alienflesh",
        "plastic", "plastic_barrel", "plastic_box",
        "rubber", "rubbertire",
        "dirt", "grass", "gravel", "sand", "mud",
        "ice", "snow",
        "rock", "boulder",
        "paper", "cardboard", "plaster",
        "cloth", "carpet",
        "porcelain", "ceramic",
        "brick", "ceiling_tile",
        "water", "slime",
    }
    for _, name in ipairs(surfaceNames) do
        physCombo:AddChoice(name, name)
    end
    physCombo.OnSelect = function(_, _, val)
        RunConsoleCommand("pmx_static_importer_physprop", val)
    end
    panel:AddItem(physCombo)

    panel:CheckBox(L("panel_disable_collision"), "pmx_static_importer_nocollide")
    panel:CheckBox(L("panel_disable_gravity"), "pmx_static_importer_nogravity")

    -- Color modulation
    panel:Help("")
    local colorLabel = vgui.Create("DLabel")
    colorLabel:SetText(L("panel_color_modulation"))
    colorLabel:SetDark(true)
    colorLabel:SetFont("DermaDefaultBold")
    colorLabel:SizeToContents()
    panel:AddItem(colorLabel)

    local colorPicker = vgui.Create("DColorMixer")
    colorPicker:SetTall(150)
    colorPicker:SetPalette(true)
    colorPicker:SetAlphaBar(false)
    colorPicker:SetWangs(true)
    colorPicker:SetColor(Color(
        GetConVar("pmx_static_importer_color_r"):GetInt(),
        GetConVar("pmx_static_importer_color_g"):GetInt(),
        GetConVar("pmx_static_importer_color_b"):GetInt()
    ))
    colorPicker.ValueChanged = function(_, col)
        RunConsoleCommand("pmx_static_importer_color_r", tostring(col.r))
        RunConsoleCommand("pmx_static_importer_color_g", tostring(col.g))
        RunConsoleCommand("pmx_static_importer_color_b", tostring(col.b))
    end
    panel:AddItem(colorPicker)

    panel:Help(L("panel_tip_refresh"))

    local editMaterialsButton = panel:Button(L("button_edit_materials"))
    editMaterialsButton.DoClick = function()
        local mid = GetConVar("pmx_static_importer_modelid"):GetString()
        PMXStaticImporter.OpenMaterialEditor(mid)
    end

    local editMeshButton = panel:Button(L("button_edit_mesh"))
    editMeshButton.DoClick = function()
        local mid = GetConVar("pmx_static_importer_modelid"):GetString()
        PMXStaticImporter.OpenMeshEditor(mid)
    end

    local hookID = "PMXStaticImporterCPanel_" .. tostring(panel)
    hook.Add("PMXStaticImporterModelListUpdated", hookID, function(entries)
        if not IsValid(modelList) then return end
        modelList:Populate(entries)
    end)

    panel.OnRemove = function()
        hook.Remove("PMXStaticImporterModelListUpdated", hookID)
    end

    timer.Simple(0, function()
        if not IsValid(modelList) then return end
        modelList:Populate(PMXStaticImporter.LastModelList or {})
        RunConsoleCommand("pmx_static_importer_refresh")
    end)
end
