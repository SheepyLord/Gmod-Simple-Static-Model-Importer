if SERVER then return end

local function L(key)
    return PMXStaticImporter.T(key)
end

local function LF(key, ...)
    return PMXStaticImporter.TF(key, nil, ...)
end

local function decimalsForExponent(exp)
    if exp <= -3 then return 4
    elseif exp <= -2 then return 3
    elseif exp <= -1 then return 2
    elseif exp <= 0 then return 1
    else return 0 end
end

local function addRangeSlider(parent, posSliders, initialExp)
    initialExp = initialExp or 1
    local rangeSlider = vgui.Create("DNumSlider", parent)
    rangeSlider:Dock(TOP)
    rangeSlider:DockMargin(8, 2, 8, 0)
    rangeSlider:SetTall(28)
    rangeSlider:SetText(L("bone_range"))
    rangeSlider:SetMin(-3)
    rangeSlider:SetMax(3)
    rangeSlider:SetDecimals(1)
    rangeSlider:SetValue(initialExp)
    rangeSlider:SetDark(true)

    local function applyRange(exp)
        local range = math.pow(10, exp)
        local dec = decimalsForExponent(exp)
        for _, s in ipairs(posSliders) do
            local cur = s:GetValue()
            s:SetMin(-range)
            s:SetMax(range)
            s:SetDecimals(dec)
            s:SetValue(math.Clamp(cur, -range, range))
        end
    end

    rangeSlider.OnValueChanged = function(_, val)
        applyRange(tonumber(val) or 1)
    end

    -- Apply initial range
    applyRange(initialExp)

    return rangeSlider
end

function PMXStaticImporter.OpenBonePicker(targetEnt)
    if not IsValid(targetEnt) then return end

    targetEnt:SetupBones(BONE_USED_BY_ANYTHING, CurTime())

    local boneCount = targetEnt:GetBoneCount() or 0
    if boneCount <= 0 then return end

    local bones = {}
    for i = 0, boneCount - 1 do
        local name = targetEnt:GetBoneName(i)
        if name and name ~= "" and name ~= "__INVALIDBONE__" then
            bones[#bones + 1] = {index = i, name = name}
        end
    end

    if #bones == 0 then return end

    local selectedBone = bones[1].index

    -- === Frame ===

    local frame = vgui.Create("DFrame")
    frame:SetTitle(LF("bone_title", tostring(targetEnt:GetClass())))
    frame:SetSize(500, 640)
    frame:Center()
    frame:MakePopup()
    frame:SetDeleteOnClose(true)
    frame:SetSizable(true)
    frame:SetMinWidth(400)
    frame:SetMinHeight(400)

    -- === Bone list header ===

    local listLabel = vgui.Create("DLabel", frame)
    listLabel:Dock(TOP)
    listLabel:SetText(LF("bone_count", #bones))
    listLabel:SetDark(true)
    listLabel:SetFont("DermaDefaultBold")
    listLabel:DockMargin(4, 4, 4, 2)
    listLabel:SizeToContents()

    -- === Search ===

    local searchEntry = vgui.Create("DTextEntry", frame)
    searchEntry:Dock(TOP)
    searchEntry:DockMargin(4, 0, 4, 2)
    searchEntry:SetPlaceholderText(L("bone_search"))

    -- === Bone list ===

    local boneList = vgui.Create("DListView", frame)
    boneList:Dock(TOP)
    boneList:SetTall(220)
    boneList:DockMargin(4, 0, 4, 4)
    boneList:SetMultiSelect(false)
    local colIdx = boneList:AddColumn("#")
    colIdx:SetFixedWidth(40)
    boneList:AddColumn(L("bone_name"))

    local function populateList(filter)
        boneList:Clear()
        for _, b in ipairs(bones) do
            if not filter or filter == "" or string.find(string.lower(b.name), string.lower(filter), 1, true) then
                local line = boneList:AddLine(b.index, b.name)
                line._boneIndex = b.index
            end
        end
    end
    populateList()

    searchEntry.OnChange = function(self)
        populateList(self:GetText())
    end

    boneList.OnRowSelected = function(_, _, line)
        if line and line._boneIndex ~= nil then
            selectedBone = line._boneIndex
        end
    end

    -- === Position Offset ===

    local posLabel = vgui.Create("DLabel", frame)
    posLabel:Dock(TOP)
    posLabel:SetText(L("bone_offset_pos"))
    posLabel:SetDark(true)
    posLabel:SetFont("DermaDefaultBold")
    posLabel:DockMargin(4, 6, 4, 0)
    posLabel:SizeToContents()

    local offX = vgui.Create("DNumSlider", frame)
    offX:Dock(TOP)
    offX:DockMargin(8, 0, 8, 0)
    offX:SetTall(28)
    offX:SetText("X")
    offX:SetMin(-1)
    offX:SetMax(1)
    offX:SetDecimals(1)
    offX:SetValue(0)
    offX:SetDark(true)

    local offY = vgui.Create("DNumSlider", frame)
    offY:Dock(TOP)
    offY:DockMargin(8, 0, 8, 0)
    offY:SetTall(28)
    offY:SetText("Y")
    offY:SetMin(-1)
    offY:SetMax(1)
    offY:SetDecimals(1)
    offY:SetValue(0)
    offY:SetDark(true)

    local offZ = vgui.Create("DNumSlider", frame)
    offZ:Dock(TOP)
    offZ:DockMargin(8, 0, 8, 0)
    offZ:SetTall(28)
    offZ:SetText("Z")
    offZ:SetMin(-1)
    offZ:SetMax(1)
    offZ:SetDecimals(1)
    offZ:SetValue(0)
    offZ:SetDark(true)

    addRangeSlider(frame, {offX, offY, offZ})

    -- === Rotation Offset ===

    local rotLabel = vgui.Create("DLabel", frame)
    rotLabel:Dock(TOP)
    rotLabel:SetText(L("bone_offset_ang"))
    rotLabel:SetDark(true)
    rotLabel:SetFont("DermaDefaultBold")
    rotLabel:DockMargin(4, 6, 4, 0)
    rotLabel:SizeToContents()

    local rotP = vgui.Create("DNumSlider", frame)
    rotP:Dock(TOP)
    rotP:DockMargin(8, 0, 8, 0)
    rotP:SetTall(28)
    rotP:SetText("Pitch")
    rotP:SetMin(-180)
    rotP:SetMax(180)
    rotP:SetDecimals(1)
    rotP:SetValue(0)
    rotP:SetDark(true)

    local rotYaw = vgui.Create("DNumSlider", frame)
    rotYaw:Dock(TOP)
    rotYaw:DockMargin(8, 0, 8, 0)
    rotYaw:SetTall(28)
    rotYaw:SetText("Yaw")
    rotYaw:SetMin(-180)
    rotYaw:SetMax(180)
    rotYaw:SetDecimals(1)
    rotYaw:SetValue(0)
    rotYaw:SetDark(true)

    local rotR = vgui.Create("DNumSlider", frame)
    rotR:Dock(TOP)
    rotR:DockMargin(8, 0, 8, 0)
    rotR:SetTall(28)
    rotR:SetText("Roll")
    rotR:SetMin(-180)
    rotR:SetMax(180)
    rotR:SetDecimals(1)
    rotR:SetValue(0)
    rotR:SetDark(true)

    -- === Scale ===

    local scaleLabel = vgui.Create("DLabel", frame)
    scaleLabel:Dock(TOP)
    scaleLabel:SetText(L("panel_scale"))
    scaleLabel:SetDark(true)
    scaleLabel:SetFont("DermaDefaultBold")
    scaleLabel:DockMargin(4, 6, 4, 0)
    scaleLabel:SizeToContents()

    local scaleSlider = vgui.Create("DNumSlider", frame)
    scaleSlider:Dock(TOP)
    scaleSlider:DockMargin(8, 0, 8, 0)
    scaleSlider:SetTall(28)
    scaleSlider:SetText(L("panel_scale"))
    scaleSlider:SetMin(0.001)
    scaleSlider:SetMax(20)
    scaleSlider:SetDecimals(3)
    scaleSlider:SetValue(GetConVar("pmx_static_importer_scale"):GetFloat())
    scaleSlider:SetDark(true)

    -- === Collision Checkbox ===

    local collisionCb = vgui.Create("DCheckBoxLabel", frame)
    collisionCb:Dock(TOP)
    collisionCb:DockMargin(8, 6, 8, 0)
    collisionCb:SetText(L("bone_collision"))
    collisionCb:SetDark(true)
    collisionCb:SetTall(20)
    collisionCb:SetChecked(false)

    -- === Bind Button ===

    local bindBtn = vgui.Create("DButton", frame)
    bindBtn:Dock(BOTTOM)
    bindBtn:DockMargin(4, 4, 4, 4)
    bindBtn:SetTall(30)
    bindBtn:SetText(L("bone_confirm"))
    bindBtn.DoClick = function()
        net.Start("pmx_bone_bind")
            net.WriteEntity(targetEnt)
            net.WriteUInt(selectedBone, 10)
            net.WriteVector(Vector(offX:GetValue(), offY:GetValue(), offZ:GetValue()))
            net.WriteAngle(Angle(rotP:GetValue(), rotYaw:GetValue(), rotR:GetValue()))
            net.WriteString(GetConVar("pmx_static_importer_modelid"):GetString())
            net.WriteFloat(math.max(scaleSlider:GetValue(), 0.0001))
            net.WriteUInt(math.Clamp(GetConVar("pmx_static_importer_color_r"):GetInt(), 0, 255), 8)
            net.WriteUInt(math.Clamp(GetConVar("pmx_static_importer_color_g"):GetInt(), 0, 255), 8)
            net.WriteUInt(math.Clamp(GetConVar("pmx_static_importer_color_b"):GetInt(), 0, 255), 8)
            net.WriteBool(collisionCb:GetChecked())
        net.SendToServer()
        frame:Close()
    end

    boneList:SelectFirstItem()

    -- === Ghost preview ===

    local hookID = "PMXBonePickerGhost_" .. tostring(frame)

    hook.Add("PostDrawTranslucentRenderables", hookID, function(_, _, skybox)
        if skybox then return end
        if not IsValid(frame) then
            hook.Remove("PostDrawTranslucentRenderables", hookID)
            return
        end
        if not IsValid(targetEnt) then return end

        local modelID = PMXStaticImporter.NormalizeModelID(GetConVar("pmx_static_importer_modelid"):GetString())
        if not modelID then return end

        local renderable = PMXStaticImporter.GetRenderable(modelID)
        if not renderable then return end

        targetEnt:SetupBones(BONE_USED_BY_ANYTHING, CurTime())
        local boneMatrix = targetEnt:GetBoneMatrix(selectedBone)
        if not boneMatrix then return end

        local bonePos = boneMatrix:GetTranslation()
        local boneAng = boneMatrix:GetAngles()
        local offset = Vector(offX:GetValue(), offY:GetValue(), offZ:GetValue())
        local offsetAng = Angle(rotP:GetValue(), rotYaw:GetValue(), rotR:GetValue())
        local finalPos, finalAng = LocalToWorld(offset, offsetAng, bonePos, boneAng)

        local scale = math.max(scaleSlider:GetValue(), 0.0001)
        PMXStaticImporter.DrawRenderableGhost(renderable, finalPos, finalAng, scale, 0.4)
    end)

    frame.OnRemove = function()
        hook.Remove("PostDrawTranslucentRenderables", hookID)
    end
end

function PMXStaticImporter.OpenBoneEditor(targetEnt, boundEnts)
    if not IsValid(targetEnt) then return end
    if not boundEnts or #boundEnts == 0 then return end

    local currentEnt = nil
    local editorScroll = nil

    -- === Frame ===

    local frame = vgui.Create("DFrame")
    frame:SetTitle(LF("bone_edit_title", tostring(targetEnt:GetClass())))
    frame:SetSize(520, 600)
    frame:Center()
    frame:MakePopup()
    frame:SetDeleteOnClose(true)
    frame:SetSizable(true)
    frame:SetMinWidth(400)
    frame:SetMinHeight(350)

    -- === Model list ===

    local listLabel = vgui.Create("DLabel", frame)
    listLabel:Dock(TOP)
    listLabel:SetText(LF("bone_edit_count", #boundEnts))
    listLabel:SetDark(true)
    listLabel:SetFont("DermaDefaultBold")
    listLabel:DockMargin(4, 4, 4, 2)
    listLabel:SizeToContents()

    local modelList = vgui.Create("DListView", frame)
    modelList:Dock(TOP)
    modelList:SetTall(140)
    modelList:DockMargin(4, 0, 4, 4)
    modelList:SetMultiSelect(false)
    local colIdx = modelList:AddColumn("#")
    colIdx:SetFixedWidth(30)
    modelList:AddColumn(L("bone_edit_model"))
    modelList:AddColumn(L("bone_name"))

    for i, ent in ipairs(boundEnts) do
        if IsValid(ent) then
            local modelID = ent:GetPMXModelID() or ""
            local boneIdx = ent:GetPMXBindBone() or 0
            local boneName = targetEnt:GetBoneName(boneIdx) or tostring(boneIdx)
            local line = modelList:AddLine(i, modelID, boneName)
            line._boundEnt = ent
        end
    end

    -- === Editor area ===

    local editorPanel = vgui.Create("DPanel", frame)
    editorPanel:Dock(FILL)
    editorPanel:DockMargin(0, 0, 0, 0)
    editorPanel.Paint = function() end

    local sendTimer = nil
    local function sendUpdate()
        if not IsValid(currentEnt) then return end
        -- Debounce: cancel pending send, schedule new one
        if sendTimer then timer.Remove(sendTimer) end
        sendTimer = "pmx_bone_edit_send_" .. tostring(frame)
        timer.Create(sendTimer, 0.05, 1, function()
            if not IsValid(currentEnt) then return end
            net.Start("pmx_bone_edit")
                net.WriteEntity(currentEnt)
                net.WriteVector(currentEnt:GetPMXBindPos())
                net.WriteAngle(currentEnt:GetPMXBindAng())
                net.WriteFloat(currentEnt:GetPMXScale())
            net.SendToServer()
        end)
    end

    local function buildEditor(ent)
        currentEnt = ent
        if IsValid(editorScroll) then editorScroll:Remove() end
        if not IsValid(ent) then return end

        editorScroll = vgui.Create("DScrollPanel", editorPanel)
        editorScroll:Dock(FILL)

        local bindPos = ent:GetPMXBindPos() or Vector(0, 0, 0)
        local bindAng = ent:GetPMXBindAng() or Angle(0, 0, 0)
        local entScale = math.max(ent:GetPMXScale() or 1, 0.0001)

        -- Position
        local posHeader = vgui.Create("DLabel", editorScroll)
        posHeader:Dock(TOP)
        posHeader:SetText(L("bone_offset_pos"))
        posHeader:SetDark(true)
        posHeader:SetFont("DermaDefaultBold")
        posHeader:DockMargin(4, 6, 4, 0)
        posHeader:SizeToContents()

        local function makeSlider(parent, text, min, max, decimals, value, onChange)
            local s = vgui.Create("DNumSlider", parent)
            s:Dock(TOP)
            s:DockMargin(8, 0, 8, 0)
            s:SetTall(28)
            s:SetText(text)
            s:SetMin(min)
            s:SetMax(max)
            s:SetDecimals(decimals)
            s:SetValue(value)
            s:SetDark(true)
            s.OnValueChanged = function(_, val) onChange(tonumber(val) or 0) end
            return s
        end

        local sliderX = makeSlider(editorScroll, "X", -1, 1, 1, bindPos.x, function(v)
            local pos = ent:GetPMXBindPos() or Vector(0, 0, 0)
            ent:SetPMXBindPos(Vector(v, pos.y, pos.z))
            sendUpdate()
        end)
        local sliderY = makeSlider(editorScroll, "Y", -1, 1, 1, bindPos.y, function(v)
            local pos = ent:GetPMXBindPos() or Vector(0, 0, 0)
            ent:SetPMXBindPos(Vector(pos.x, v, pos.z))
            sendUpdate()
        end)
        local sliderZ = makeSlider(editorScroll, "Z", -1, 1, 1, bindPos.z, function(v)
            local pos = ent:GetPMXBindPos() or Vector(0, 0, 0)
            ent:SetPMXBindPos(Vector(pos.x, pos.y, v))
            sendUpdate()
        end)

        addRangeSlider(editorScroll, {sliderX, sliderY, sliderZ},
            math.max(1, math.ceil(math.log10(math.max(
                math.abs(bindPos.x), math.abs(bindPos.y), math.abs(bindPos.z), 1
            )))))

        -- Rotation
        local rotHeader = vgui.Create("DLabel", editorScroll)
        rotHeader:Dock(TOP)
        rotHeader:SetText(L("bone_offset_ang"))
        rotHeader:SetDark(true)
        rotHeader:SetFont("DermaDefaultBold")
        rotHeader:DockMargin(4, 6, 4, 0)
        rotHeader:SizeToContents()

        makeSlider(editorScroll, "Pitch", -180, 180, 1, bindAng.p, function(v)
            local ang = ent:GetPMXBindAng() or Angle(0, 0, 0)
            ent:SetPMXBindAng(Angle(v, ang.y, ang.r))
            sendUpdate()
        end)
        makeSlider(editorScroll, "Yaw", -180, 180, 1, bindAng.y, function(v)
            local ang = ent:GetPMXBindAng() or Angle(0, 0, 0)
            ent:SetPMXBindAng(Angle(ang.p, v, ang.r))
            sendUpdate()
        end)
        makeSlider(editorScroll, "Roll", -180, 180, 1, bindAng.r, function(v)
            local ang = ent:GetPMXBindAng() or Angle(0, 0, 0)
            ent:SetPMXBindAng(Angle(ang.p, ang.y, v))
            sendUpdate()
        end)

        -- Scale
        local scaleHeader = vgui.Create("DLabel", editorScroll)
        scaleHeader:Dock(TOP)
        scaleHeader:SetText(L("panel_scale"))
        scaleHeader:SetDark(true)
        scaleHeader:SetFont("DermaDefaultBold")
        scaleHeader:DockMargin(4, 6, 4, 0)
        scaleHeader:SizeToContents()

        makeSlider(editorScroll, L("panel_scale"), 0.001, 20, 3, entScale, function(v)
            ent:SetPMXScale(math.max(v, 0.0001))
            sendUpdate()
        end)
    end

    modelList.OnRowSelected = function(_, _, line)
        if line and IsValid(line._boundEnt) then
            buildEditor(line._boundEnt)
        end
    end

    modelList:SelectFirstItem()

    frame.OnRemove = function()
        local timerName = "pmx_bone_edit_send_" .. tostring(frame)
        if timer.Exists(timerName) then timer.Remove(timerName) end
    end
end
