if SERVER then return end

local L = PMXStaticImporter.T

function PMXStaticImporter.GetClipPath(modelID)
    modelID = PMXStaticImporter.NormalizeModelID(modelID)
    if not modelID then return nil end
    return "pmx_static_importer/overrides/" .. modelID:gsub("/", "_") .. "_clip.json"
end

function PMXStaticImporter.LoadClipBounds(modelID)
    modelID = PMXStaticImporter.NormalizeModelID(modelID)
    if not modelID then return {} end

    local path = PMXStaticImporter.GetClipPath(modelID)
    if not path then return {} end

    local raw = file.Read(path, "DATA")
    if not raw then return {} end

    local parsed = util.JSONToTable(raw)
    return istable(parsed) and parsed or {}
end

function PMXStaticImporter.SaveClipBounds(modelID, clip)
    modelID = PMXStaticImporter.NormalizeModelID(modelID)
    if not modelID then return end

    file.CreateDir("pmx_static_importer/overrides")
    local path = PMXStaticImporter.GetClipPath(modelID)
    if path then
        file.Write(path, util.TableToJSON(clip or {}, true))
    end
end

-- Build a preview renderable with clip bounds applied (no caching)
local function build_clipped_preview(modelID, clip)
    local manifest, err = PMXStaticImporter.LoadManifest(modelID)
    if not manifest then return nil, err end

    local renderable = PMXStaticImporter.ReadMeshFileClipped(manifest, clip)
    if not renderable then return nil, "Failed to build clipped mesh" end

    return renderable
end

local function destroy_preview(renderable)
    if not renderable or not renderable.drawItems then return end
    for _, item in ipairs(renderable.drawItems) do
        if item and item.mesh and item.mesh.Destroy then
            pcall(function() item.mesh:Destroy() end)
        end
    end
end

function PMXStaticImporter.OpenMeshEditor(modelID)
    modelID = PMXStaticImporter.NormalizeModelID(modelID)
    if not modelID then
        Derma_Message(L("chat_no_imported_model_selected"), L("mesh_edit_title_short"), L("dialog_ok"))
        return
    end

    local manifest, err = PMXStaticImporter.LoadManifest(modelID)
    if not manifest then
        Derma_Message(tostring(err), L("mesh_edit_title_short"), L("dialog_ok"))
        return
    end

    local mins, maxs = PMXStaticImporter.GetBoundsFromManifest(manifest)
    local saved = PMXStaticImporter.LoadClipBounds(modelID)

    -- Current clip state
    local clip = {
        xmin_on = saved.xmin_on or false,
        xmax_on = saved.xmax_on or false,
        ymin_on = saved.ymin_on or false,
        ymax_on = saved.ymax_on or false,
        zmin_on = saved.zmin_on or false,
        zmax_on = saved.zmax_on or false,
        xmin = saved.xmin or mins.x,
        xmax = saved.xmax or maxs.x,
        ymin = saved.ymin or mins.y,
        ymax = saved.ymax or maxs.y,
        zmin = saved.zmin or mins.z,
        zmax = saved.zmax or maxs.z,
    }

    -- Build initial preview
    local previewRenderable = build_clipped_preview(modelID, clip)

    -- Frame
    local frame = vgui.Create("DFrame")
    frame:SetTitle(PMXStaticImporter.TF("mesh_edit_title", nil, manifest.display_name or modelID))
    frame:SetSize(780, 620)
    frame:Center()
    frame:MakePopup()
    frame:SetDeleteOnClose(true)
    frame.OnClose = function()
        destroy_preview(previewRenderable)
        hook.Remove("PostDrawTranslucentRenderables", "PMXMeshEditorPreview")
    end

    -- Split: left = 3D preview, right = controls
    local leftPanel = vgui.Create("DPanel", frame)
    leftPanel:Dock(LEFT)
    leftPanel:SetWide(400)
    leftPanel:DockMargin(0, 0, 4, 0)

    local rightPanel = vgui.Create("DPanel", frame)
    rightPanel:Dock(FILL)
    rightPanel:SetPaintBackground(false)

    -- 3D preview panel
    local previewPanel = vgui.Create("DPanel", leftPanel)
    previewPanel:Dock(FILL)

    local camDist = math.max(maxs.x - mins.x, maxs.y - mins.y, maxs.z - mins.z) * 2
    if camDist < 10 then camDist = 100 end
    local camYaw = 30
    local camPitch = 20
    local camCenter = (mins + maxs) * 0.5

    local dragging = false
    local lastX, lastY = 0, 0

    previewPanel.OnMousePressed = function(_, code)
        if code == MOUSE_LEFT then
            dragging = true
            lastX, lastY = gui.MousePos()
            previewPanel:MouseCapture(true)
        end
    end

    previewPanel.OnMouseReleased = function(_, code)
        if code == MOUSE_LEFT then
            dragging = false
            previewPanel:MouseCapture(false)
        end
    end

    previewPanel.OnCursorMoved = function()
        if not dragging then return end
        local mx, my = gui.MousePos()
        local dx = mx - lastX
        local dy = my - lastY
        lastX, lastY = mx, my
        camYaw = camYaw - dx * 0.5
        camPitch = math.Clamp(camPitch + dy * 0.5, -89, 89)
    end

    previewPanel.OnMouseWheeled = function(_, delta)
        camDist = math.Clamp(camDist - delta * camDist * 0.1, 1, 100000)
    end

    previewPanel.Paint = function(self, w, h)
        surface.SetDrawColor(40, 40, 40, 255)
        surface.DrawRect(0, 0, w, h)

        local x, y = self:LocalToScreen(0, 0)

        local radYaw = math.rad(camYaw)
        local radPitch = math.rad(camPitch)
        local camPos = camCenter + Vector(
            math.cos(radPitch) * math.cos(radYaw) * camDist,
            math.cos(radPitch) * math.sin(radYaw) * camDist,
            math.sin(radPitch) * camDist
        )

        cam.Start3D(camPos, (camCenter - camPos):Angle(), 70, x, y, w, h)
            render.SuppressEngineLighting(true)
            render.SetLocalModelLights()
            render.ResetModelLighting(0.3, 0.3, 0.3)
            render.SetModelLighting(BOX_TOP, 1, 1, 1)
            render.SetModelLighting(BOX_FRONT, 0.6, 0.6, 0.6)

            if previewRenderable then
                for _, item in ipairs(previewRenderable.drawItems or {}) do
                    render.SetMaterial(item.material or PMXStaticImporter.DebugWhite)
                    render.SetColorModulation(item.diffuseR or 1, item.diffuseG or 1, item.diffuseB or 1)
                    render.SetBlend(item.alpha or 1)
                    render.CullMode(item.noCull and MATERIAL_CULLMODE_NONE or MATERIAL_CULLMODE_CCW)
                    if item.mesh then
                        item.mesh:Draw()
                    end
                end
            end

            render.CullMode(MATERIAL_CULLMODE_CCW)
            render.SetBlend(1)
            render.SetColorModulation(1, 1, 1)
            render.SuppressEngineLighting(false)
        cam.End3D()
    end

    -- Debounced rebuild
    local rebuildTimer = "PMXMeshEditorRebuild"
    local function scheduleRebuild()
        timer.Remove(rebuildTimer)
        timer.Create(rebuildTimer, 0.15, 1, function()
            if not IsValid(frame) then return end
            local old = previewRenderable
            previewRenderable = build_clipped_preview(modelID, clip)
            destroy_preview(old)
        end)
    end

    -- Right panel: scrollable controls
    local scroll = vgui.Create("DScrollPanel", rightPanel)
    scroll:Dock(FILL)

    local function addAxisClip(axis, minKey, maxKey, minOnKey, maxOnKey, boundsMin, boundsMax)
        local axisLabel = vgui.Create("DLabel", scroll)
        axisLabel:Dock(TOP)
        axisLabel:DockMargin(4, 8, 4, 2)
        axisLabel:SetText(string.upper(axis) .. " " .. L("mesh_edit_axis"))
        axisLabel:SetDark(true)
        axisLabel:SetFont("DermaDefaultBold")
        axisLabel:SizeToContents()

        -- Range for slider: expand by 10% on each side
        local span = boundsMax - boundsMin
        if span < 0.001 then span = 2 end
        local sliderMin = boundsMin - span * 0.1
        local sliderMax = boundsMax + span * 0.1
        local decimals = 2

        -- Min checkbox + slider
        local minCheck = vgui.Create("DCheckBoxLabel", scroll)
        minCheck:Dock(TOP)
        minCheck:DockMargin(4, 2, 4, 0)
        minCheck:SetText(string.upper(axis) .. " " .. L("mesh_edit_min"))
        minCheck:SetChecked(clip[minOnKey])

        local minSlider = vgui.Create("DNumSlider", scroll)
        minSlider:Dock(TOP)
        minSlider:DockMargin(4, 0, 4, 0)
        minSlider:SetText("")
        minSlider:SetMin(sliderMin)
        minSlider:SetMax(sliderMax)
        minSlider:SetDecimals(decimals)
        minSlider:SetValue(clip[minKey])
        minSlider:SetEnabled(clip[minOnKey])

        minCheck.OnChange = function(_, val)
            clip[minOnKey] = val
            minSlider:SetEnabled(val)
            scheduleRebuild()
        end

        minSlider.OnValueChanged = function(_, val)
            clip[minKey] = val
            scheduleRebuild()
        end

        -- Max checkbox + slider
        local maxCheck = vgui.Create("DCheckBoxLabel", scroll)
        maxCheck:Dock(TOP)
        maxCheck:DockMargin(4, 4, 4, 0)
        maxCheck:SetText(string.upper(axis) .. " " .. L("mesh_edit_max"))
        maxCheck:SetChecked(clip[maxOnKey])

        local maxSlider = vgui.Create("DNumSlider", scroll)
        maxSlider:Dock(TOP)
        maxSlider:DockMargin(4, 0, 4, 0)
        maxSlider:SetText("")
        maxSlider:SetMin(sliderMin)
        maxSlider:SetMax(sliderMax)
        maxSlider:SetDecimals(decimals)
        maxSlider:SetValue(clip[maxKey])
        maxSlider:SetEnabled(clip[maxOnKey])

        maxCheck.OnChange = function(_, val)
            clip[maxOnKey] = val
            maxSlider:SetEnabled(val)
            scheduleRebuild()
        end

        maxSlider.OnValueChanged = function(_, val)
            clip[maxKey] = val
            scheduleRebuild()
        end
    end

    addAxisClip("x", "xmin", "xmax", "xmin_on", "xmax_on", mins.x, maxs.x)
    addAxisClip("y", "ymin", "ymax", "ymin_on", "ymax_on", mins.y, maxs.y)
    addAxisClip("z", "zmin", "zmax", "zmin_on", "zmax_on", mins.z, maxs.z)

    -- Buttons
    local buttonPanel = vgui.Create("DPanel", rightPanel)
    buttonPanel:Dock(BOTTOM)
    buttonPanel:SetTall(70)
    buttonPanel:SetPaintBackground(false)
    buttonPanel:DockMargin(4, 4, 4, 4)

    local saveButton = vgui.Create("DButton", buttonPanel)
    saveButton:Dock(TOP)
    saveButton:DockMargin(0, 2, 0, 2)
    saveButton:SetTall(30)
    saveButton:SetText(L("mesh_edit_save"))
    saveButton.DoClick = function()
        PMXStaticImporter.SaveClipBounds(modelID, clip)
        PMXStaticImporter.ClearCache(modelID)
        frame:Close()
    end

    local resetButton = vgui.Create("DButton", buttonPanel)
    resetButton:Dock(TOP)
    resetButton:DockMargin(0, 2, 0, 2)
    resetButton:SetTall(30)
    resetButton:SetText(L("mesh_edit_reset"))
    resetButton.DoClick = function()
        PMXStaticImporter.SaveClipBounds(modelID, {})
        PMXStaticImporter.ClearCache(modelID)
        frame:Close()
    end
end
