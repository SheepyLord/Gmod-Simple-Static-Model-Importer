if SERVER then return end

local function L(key)
    return PMXStaticImporter.T(key)
end

local function LF(key, ...)
    return PMXStaticImporter.TF(key, nil, ...)
end

local function getSubmeshName(submesh, index)
    if submesh.name and submesh.name ~= "" then
        return submesh.name
    end
    local path = tostring(submesh.image_path or "")
    if path ~= "" then
        return string.GetFileFromFilename(path) or path
    end
    return LF("ui_material_default_name", index)
end

local function clamp01(v)
    v = tonumber(v) or 0
    if v < 0 then return 0 end
    if v > 1 then return 1 end
    return v
end

function PMXStaticImporter.OpenMaterialEditor(modelID)
    modelID = PMXStaticImporter.NormalizeModelID(modelID)
    if not modelID then
        Derma_Message(L("chat_no_imported_model_selected"), L("ui_material_editor"), L("dialog_ok"))
        return
    end

    local manifest = PMXStaticImporter.LoadManifest(modelID)
    if not manifest then
        Derma_Message(LF("error_could_not_load_manifest_for", modelID), L("ui_material_editor"), L("dialog_ok"))
        return
    end

    local submeshes = manifest.submeshes or {}
    if #submeshes == 0 then
        Derma_Message(L("error_no_materials_found_in_model"), L("ui_material_editor"), L("dialog_ok"))
        return
    end

    local allOverrides = table.Copy(PMXStaticImporter.LoadMaterialOverrides(modelID))
    local defs = PMXStaticImporter.ShaderDefaults

    -- === Helpers ===

    local function getOv(idx, key)
        local ov = allOverrides[tostring(idx)]
        if ov and ov[key] ~= nil then return ov[key] end
        return nil
    end

    local function setOv(idx, key, value)
        local k = tostring(idx)
        if not allOverrides[k] then allOverrides[k] = {} end
        allOverrides[k][key] = value
    end

    local function getEffective(idx, key, sub)
        local v = getOv(idx, key)
        if v ~= nil then return v end

        -- Submesh-derived defaults
        if key == "nocull" then
            return (sub.no_cull == nil) or tobool(sub.no_cull) or tobool(sub.double_sided)
        elseif key == "translucent" then
            local a = clamp01(sub.alpha or 1)
            return tobool(sub.translucent) or a < 0.999
        elseif key == "alphatest" then
            return PMXStaticImporter.IsPngPath(tostring(sub.image_path or ""))
        end

        return defs[key]
    end

    -- === Frame ===

    local frame = vgui.Create("DFrame")
    frame:SetTitle(LF("ui_material_editor_title", manifest.display_name or modelID))
    frame:SetSize(940, 680)
    frame:Center()
    frame:MakePopup()
    frame:SetDeleteOnClose(true)
    frame:SetSizable(true)
    frame:SetMinWidth(700)
    frame:SetMinHeight(400)

    -- === Left: material list ===

    local leftPanel = vgui.Create("DPanel", frame)
    leftPanel:Dock(LEFT)
    leftPanel:SetWide(230)
    leftPanel:DockMargin(0, 0, 4, 0)
    leftPanel.Paint = function(_, w, h)
        draw.RoundedBox(0, 0, 0, w, h, Color(240, 240, 240))
    end

    local listLabel = vgui.Create("DLabel", leftPanel)
    listLabel:Dock(TOP)
    listLabel:SetText(LF("ui_materials_count", #submeshes))
    listLabel:SetDark(true)
    listLabel:SetFont("DermaDefaultBold")
    listLabel:DockMargin(4, 4, 4, 2)
    listLabel:SizeToContents()

    local matList = vgui.Create("DListView", leftPanel)
    matList:Dock(FILL)
    matList:DockMargin(2, 2, 2, 2)
    matList:SetMultiSelect(false)
    local colCheck = matList:AddColumn("")
    colCheck:SetFixedWidth(20)
    local colIdx = matList:AddColumn("#")
    colIdx:SetFixedWidth(28)
    matList:AddColumn(L("ui_name"))

    local matLines = {}
    for i, sub in ipairs(submeshes) do
        local isDisabled = tobool(getOv(i, "disabled"))
        local line = matList:AddLine(isDisabled and "✗" or "✓", i, getSubmeshName(sub, i))
        line._submeshIndex = i
        matLines[i] = line
    end

    -- === Right: editor area ===

    local rightPanel = vgui.Create("DPanel", frame)
    rightPanel:Dock(FILL)
    rightPanel.Paint = function() end

    -- === Bottom button bar (fixed, outside scroll) ===

    local currentSubmeshIndex = 1
    local buildEditor -- forward declaration

    local buttonBar = vgui.Create("DPanel", rightPanel)
    buttonBar:Dock(BOTTOM)
    buttonBar:SetTall(36)
    buttonBar:DockMargin(0, 2, 0, 0)
    buttonBar.Paint = function(_, w, h)
        draw.RoundedBox(0, 0, 0, w, h, Color(230, 230, 230))
    end

    local saveBtn = vgui.Create("DButton", buttonBar)
    saveBtn:Dock(LEFT)
    saveBtn:DockMargin(4, 3, 0, 3)
    saveBtn:SetWide(120)
    saveBtn:SetText(L("button_save_apply"))
    saveBtn.DoClick = function()
        PMXStaticImporter.SaveMaterialOverrides(modelID, allOverrides)
        PMXStaticImporter.ApplyMaterialOverrides(modelID)
        surface.PlaySound("buttons/button14.wav")
    end

    local resetBtn = vgui.Create("DButton", buttonBar)
    resetBtn:Dock(LEFT)
    resetBtn:DockMargin(4, 3, 0, 3)
    resetBtn:SetWide(140)
    resetBtn:SetText(L("button_reset_this_material"))
    resetBtn.DoClick = function()
        allOverrides[tostring(currentSubmeshIndex)] = nil
        PMXStaticImporter.SaveMaterialOverrides(modelID, allOverrides)
        PMXStaticImporter.ApplyMaterialOverrides(modelID)
        buildEditor(currentSubmeshIndex)
        surface.PlaySound("buttons/button14.wav")
    end

    local onlyThisBtn = vgui.Create("DButton", buttonBar)
    onlyThisBtn:Dock(LEFT)
    onlyThisBtn:DockMargin(4, 3, 0, 3)
    onlyThisBtn:SetWide(120)
    onlyThisBtn:SetText(L("button_only_this"))
    onlyThisBtn.DoClick = function()
        for i = 1, #submeshes do
            local k = tostring(i)
            if not allOverrides[k] then allOverrides[k] = {} end
            allOverrides[k].disabled = (i ~= currentSubmeshIndex)
        end
        PMXStaticImporter.SaveMaterialOverrides(modelID, allOverrides)
        PMXStaticImporter.ApplyMaterialOverrides(modelID)
        for i, line in pairs(matLines) do
            if IsValid(line) then
                line:SetColumnText(1, (i == currentSubmeshIndex) and "✓" or "✗")
            end
        end
        buildEditor(currentSubmeshIndex)
        surface.PlaySound("buttons/button14.wav")
    end

    local enableAllBtn = vgui.Create("DButton", buttonBar)
    enableAllBtn:Dock(LEFT)
    enableAllBtn:DockMargin(4, 3, 0, 3)
    enableAllBtn:SetWide(90)
    enableAllBtn:SetText(L("button_enable_all"))
    enableAllBtn.DoClick = function()
        for i = 1, #submeshes do
            local k = tostring(i)
            if allOverrides[k] then allOverrides[k].disabled = nil end
        end
        PMXStaticImporter.SaveMaterialOverrides(modelID, allOverrides)
        PMXStaticImporter.ApplyMaterialOverrides(modelID)
        for _, line in pairs(matLines) do
            if IsValid(line) then
                line:SetColumnText(1, "✓")
            end
        end
        buildEditor(currentSubmeshIndex)
        surface.PlaySound("buttons/button14.wav")
    end

    local disableAllBtn = vgui.Create("DButton", buttonBar)
    disableAllBtn:Dock(LEFT)
    disableAllBtn:DockMargin(4, 3, 0, 3)
    disableAllBtn:SetWide(90)
    disableAllBtn:SetText(L("button_disable_all"))
    disableAllBtn.DoClick = function()
        for i = 1, #submeshes do
            local k = tostring(i)
            if not allOverrides[k] then allOverrides[k] = {} end
            allOverrides[k].disabled = true
        end
        PMXStaticImporter.SaveMaterialOverrides(modelID, allOverrides)
        PMXStaticImporter.ApplyMaterialOverrides(modelID)
        for _, line in pairs(matLines) do
            if IsValid(line) then
                line:SetColumnText(1, "✗")
            end
        end
        buildEditor(currentSubmeshIndex)
        surface.PlaySound("buttons/button14.wav")
    end

    local resetAllBtn = vgui.Create("DButton", buttonBar)
    resetAllBtn:Dock(LEFT)
    resetAllBtn:DockMargin(4, 3, 0, 3)
    resetAllBtn:SetWide(130)
    resetAllBtn:SetText(L("button_reset_all_materials"))
    resetAllBtn.DoClick = function()
        Derma_Query(L("dialog_confirm_reset_text"), L("dialog_confirm_reset"),
            L("dialog_yes"), function()
                allOverrides = {}
                PMXStaticImporter.SaveMaterialOverrides(modelID, allOverrides)
                PMXStaticImporter.ApplyMaterialOverrides(modelID)
                buildEditor(currentSubmeshIndex)
                surface.PlaySound("buttons/button14.wav")
            end,
            L("dialog_no"), function() end
        )
    end

    local editorScroll = nil

    -- === UI builder helpers ===

    local function addSectionHeader(parent, text)
        local lbl = vgui.Create("DLabel", parent)
        lbl:Dock(TOP)
        lbl:DockMargin(4, 10, 4, 2)
        lbl:SetText(text)
        lbl:SetDark(true)
        lbl:SetFont("DermaDefaultBold")
        lbl:SizeToContents()
        lbl:SetTall(20)
        return lbl
    end

    local function addTextEntry(parent, label, key, idx, sub)
        local row = vgui.Create("DPanel", parent)
        row:Dock(TOP)
        row:SetTall(24)
        row:DockMargin(8, 2, 8, 0)
        row.Paint = function() end

        local lbl = vgui.Create("DLabel", row)
        lbl:Dock(LEFT)
        lbl:SetWide(150)
        lbl:SetText(label)
        lbl:SetDark(true)

        local entry = vgui.Create("DTextEntry", row)
        entry:Dock(FILL)
        entry:SetText(tostring(getEffective(idx, key, sub) or ""))
        entry.OnEnter = function(self) setOv(idx, key, self:GetText()) end
        entry.OnLoseFocus = function(self) setOv(idx, key, self:GetText()) end
        return entry
    end

    local function addCheckbox(parent, label, key, idx, sub)
        local cb = vgui.Create("DCheckBoxLabel", parent)
        cb:Dock(TOP)
        cb:DockMargin(8, 4, 8, 0)
        cb:SetText(label)
        cb:SetDark(true)
        cb:SetTall(20)
        cb:SetChecked(tobool(getEffective(idx, key, sub)))
        cb.OnChange = function(_, val) setOv(idx, key, val) end
        return cb
    end

    local function addSlider(parent, label, key, min, max, decimals, idx, sub)
        local slider = vgui.Create("DNumSlider", parent)
        slider:Dock(TOP)
        slider:DockMargin(8, 2, 8, 0)
        slider:SetTall(32)
        slider:SetText(label)
        slider:SetDark(true)
        slider:SetMin(min)
        slider:SetMax(max)
        slider:SetDecimals(decimals)
        slider:SetValue(tonumber(getEffective(idx, key, sub)) or 0)
        slider.OnValueChanged = function(_, val)
            setOv(idx, key, math.Round(tonumber(val) or 0, decimals))
        end
        return slider
    end

    local function addVectorSliders(parent, label, key, componentNames, min, max, decimals, idx, sub)
        addSectionHeader(parent, label)
        local vec = getEffective(idx, key, sub)
        if not istable(vec) then vec = {0, 0, 0} end

        local sliders = {}
        for ci, cname in ipairs(componentNames) do
            local s = vgui.Create("DNumSlider", parent)
            s:Dock(TOP)
            s:DockMargin(16, 0, 8, 0)
            s:SetTall(28)
            s:SetText(cname)
            s:SetDark(true)
            s:SetMin(min)
            s:SetMax(max)
            s:SetDecimals(decimals)
            s:SetValue(tonumber(vec[ci]) or 0)
            sliders[ci] = s
        end

        local function updateVec()
            local newVec = {}
            for ci, s in ipairs(sliders) do
                newVec[ci] = math.Round(tonumber(s:GetValue()) or 0, decimals)
            end
            setOv(idx, key, newVec)
        end

        for _, s in ipairs(sliders) do
            s.OnValueChanged = function() updateVec() end
        end

        return sliders
    end

    -- === Build editor for a submesh ===

    buildEditor = function(submeshIndex)
        currentSubmeshIndex = submeshIndex
        if IsValid(editorScroll) then editorScroll:Remove() end
        editorScroll = vgui.Create("DScrollPanel", rightPanel)
        editorScroll:Dock(FILL)

        local sub = submeshes[submeshIndex]
        if not sub then return end
        local imagePath = tostring(sub.image_path or "")

        -- ===== MATERIAL PREVIEW =====
        addSectionHeader(editorScroll, LF("ui_preview", getSubmeshName(sub, submeshIndex)))

        if imagePath ~= "" then
            local texMat = Material(imagePath, "noclamp smooth")
            if texMat and not texMat:IsError() then
                local tex = texMat:GetTexture("$basetexture")
                local texW, texH = 256, 256
                if tex then
                    texW = tex:Width()
                    texH = tex:Height()
                end

                local previewContainer = vgui.Create("DPanel", editorScroll)
                previewContainer:Dock(TOP)
                previewContainer:DockMargin(8, 2, 8, 4)
                previewContainer:SetTall(204)
                previewContainer.Paint = function(_, w, h)
                    draw.RoundedBox(2, 0, 0, w, h, Color(40, 40, 40))
                end

                local previewImage = vgui.Create("DImage", previewContainer)
                previewImage:Dock(FILL)
                previewImage:DockMargin(2, 2, 2, 2)
                previewImage:SetKeepAspect(true)
                previewImage:SetMaterial(texMat)
            else
                local noTex = vgui.Create("DLabel", editorScroll)
                noTex:Dock(TOP)
                noTex:DockMargin(8, 2, 8, 2)
                noTex:SetText(LF("ui_texture_not_found", imagePath))
                noTex:SetDark(true)
            end
        else
            local noTex = vgui.Create("DLabel", editorScroll)
            noTex:Dock(TOP)
            noTex:DockMargin(8, 2, 8, 2)
            noTex:SetText(L("ui_no_base_texture"))
            noTex:SetDark(true)
        end

        local baseInfo = vgui.Create("DLabel", editorScroll)
        baseInfo:Dock(TOP)
        baseInfo:DockMargin(8, 0, 8, 4)
        baseInfo:SetText(LF("ui_base_texture", (imagePath ~= "" and imagePath or L("ui_none"))))
        baseInfo:SetDark(true)
        baseInfo:SetWrap(true)
        baseInfo:SetAutoStretchVertical(true)

        -- ===== IMPORT TOGGLE =====
        addSectionHeader(editorScroll, L("ui_import"))
        local importCb = vgui.Create("DCheckBoxLabel", editorScroll)
        importCb:Dock(TOP)
        importCb:DockMargin(8, 4, 8, 0)
        importCb:SetText(L("label_include_mesh_when_importing"))
        importCb:SetDark(true)
        importCb:SetTall(20)
        importCb:SetChecked(not tobool(getOv(submeshIndex, "disabled")))
        importCb.OnChange = function(_, val)
            setOv(submeshIndex, "disabled", not val)
            PMXStaticImporter.SaveMaterialOverrides(modelID, allOverrides)
            PMXStaticImporter.ApplyMaterialOverrides(modelID)
            if matLines[submeshIndex] then
                matLines[submeshIndex]:SetColumnText(1, val and "✓" or "✗")
            end
        end

        -- ===== TEXTURE MAPS =====
        addSectionHeader(editorScroll, L("ui_texture_maps"))
        addTextEntry(editorScroll, L("label_bump_map"), "bumpmap", submeshIndex, sub)
        addTextEntry(editorScroll, L("label_light_warp"), "lightwarptexture", submeshIndex, sub)
        addTextEntry(editorScroll, L("label_self_illum_mask"), "selfillummask", submeshIndex, sub)
        addTextEntry(editorScroll, L("label_phong_exponent_tex"), "phongexponenttexture", submeshIndex, sub)

        -- ===== RENDERING =====
        addSectionHeader(editorScroll, L("ui_rendering"))
        addCheckbox(editorScroll, L("label_no_cull"), "nocull", submeshIndex, sub)
        addCheckbox(editorScroll, L("label_translucent"), "translucent", submeshIndex, sub)
        addCheckbox(editorScroll, L("label_alpha_test"), "alphatest", submeshIndex, sub)
        addSlider(editorScroll, L("label_alpha_test_reference"), "alphatestreference", 0, 1, 2, submeshIndex, sub)
        addCheckbox(editorScroll, L("label_alpha_to_coverage"), "allowalphatocoverage", submeshIndex, sub)

        -- ===== LIGHTING =====
        addSectionHeader(editorScroll, L("ui_lighting"))
        addCheckbox(editorScroll, L("label_half_lambert"), "halflambert", submeshIndex, sub)

        -- ===== SELF ILLUMINATION =====
        addSectionHeader(editorScroll, L("ui_self_illumination"))
        addCheckbox(editorScroll, L("label_enable_self_illum"), "selfillum", submeshIndex, sub)
        addVectorSliders(editorScroll, L("ui_self_illum_tint"), "selfillumtint",
            {"R", "G", "B"}, 0, 1, 2, submeshIndex, sub)

        -- ===== PHONG =====
        addSectionHeader(editorScroll, L("ui_phong_shading"))
        addCheckbox(editorScroll, L("label_enable_phong"), "phong", submeshIndex, sub)
        addSlider(editorScroll, L("label_phong_boost"), "phongboost", 0, 50, 1, submeshIndex, sub)
        addCheckbox(editorScroll, L("label_phong_albedo_tint"), "phongalbedotint", submeshIndex, sub)
        addSlider(editorScroll, L("label_phong_albedo_boost"), "phongalbedoboost", 0, 50, 1, submeshIndex, sub)
        addVectorSliders(editorScroll, L("ui_phong_fresnel_ranges"), "phongfresnelranges",
            {L("component_min"), L("component_mid"), L("component_max")}, 0, 10, 1, submeshIndex, sub)

        -- ===== RIM LIGHT =====
        addSectionHeader(editorScroll, L("ui_rim_light"))
        addCheckbox(editorScroll, L("label_enable_rim_light"), "rimlight", submeshIndex, sub)
        addSlider(editorScroll, L("label_rim_exponent"), "rimlightexponent", 0, 10, 1, submeshIndex, sub)
        addSlider(editorScroll, L("label_rim_boost"), "rimlightboost", 0, 10, 1, submeshIndex, sub)
    end

    -- === List selection ===

    matList.OnRowSelected = function(_, _, line)
        if line and line._submeshIndex then
            buildEditor(line._submeshIndex)
        end
    end

    -- Select first material
    if #submeshes > 0 then
        matList:SelectFirstItem()
    end
end
