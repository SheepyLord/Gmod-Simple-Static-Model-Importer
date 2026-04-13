if SERVER then return end

PMXStaticImporter = PMXStaticImporter or {}
PMXStaticImporter.RenderableCache = PMXStaticImporter.RenderableCache or {}
PMXStaticImporter.MaterialCache = PMXStaticImporter.MaterialCache or {}
PMXStaticImporter.LastModelList = PMXStaticImporter.LastModelList or {}
PMXStaticImporter.DebugWhite = PMXStaticImporter.DebugWhite or Material("models/debug/debugwhite")
PMXStaticImporter.MaxVertsPerMesh = PMXStaticImporter.MaxVertsPerMesh or 60000
PMXStaticImporter.MaterialOverrides = PMXStaticImporter.MaterialOverrides or {}

PMXStaticImporter.ShaderDefaults = {
    bumpmap = "models/sheepylord/shared/normal",
    lightwarptexture = "models/sheepylord/shared/lightwarptexture",
    halflambert = false,
    selfillum = false,
    selfillummask = "",
    selfillumtint = {0.5, 0.5, 0.5},
    phong = true,
    phongboost = 24,
    phongalbedotint = true,
    phongalbedoboost = 1,
    phongexponenttexture = "models/sheepylord/shared/phong_exp",
    phongfresnelranges = {0, 0, 1},
    rimlight = true,
    rimlightexponent = 2,
    rimlightboost = 2,
    alphatestreference = 0.5,
    allowalphatocoverage = true,
}

local function make_cache_key(modelID, buildID)
    return tostring(modelID or "") .. "::" .. tostring(buildID or "")
end

local function clamp01(value)
    value = tonumber(value) or 0
    if value < 0 then return 0 end
    if value > 1 then return 1 end
    return value
end

local function is_png_path(path)
    local ext = tostring(path or ""):match("%.([^./]+)$")
    if not ext then return false end
    return string.lower(ext) == "png"
end

PMXStaticImporter.IsPngPath = is_png_path

function PMXStaticImporter.GetOverridesPath(modelID)
    modelID = PMXStaticImporter.NormalizeModelID(modelID)
    if not modelID then return nil end
    return "pmx_static_importer/overrides/" .. modelID:gsub("/", "_") .. ".json"
end

function PMXStaticImporter.LoadMaterialOverrides(modelID)
    modelID = PMXStaticImporter.NormalizeModelID(modelID)
    if not modelID then return {} end

    if PMXStaticImporter.MaterialOverrides[modelID] then
        return PMXStaticImporter.MaterialOverrides[modelID]
    end

    local path = PMXStaticImporter.GetOverridesPath(modelID)
    if not path then return {} end

    local raw = file.Read(path, "DATA")
    if not raw then
        PMXStaticImporter.MaterialOverrides[modelID] = {}
        return {}
    end

    local parsed = util.JSONToTable(raw)
    PMXStaticImporter.MaterialOverrides[modelID] = istable(parsed) and parsed or {}
    return PMXStaticImporter.MaterialOverrides[modelID]
end

function PMXStaticImporter.SaveMaterialOverrides(modelID, overrides)
    modelID = PMXStaticImporter.NormalizeModelID(modelID)
    if not modelID then return end

    PMXStaticImporter.MaterialOverrides[modelID] = overrides or {}

    file.CreateDir("pmx_static_importer/overrides")
    local path = PMXStaticImporter.GetOverridesPath(modelID)
    if path then
        file.Write(path, util.TableToJSON(overrides or {}, true))
    end
end

function PMXStaticImporter.GetSubmeshOverrides(modelID, submeshIndex)
    local all = PMXStaticImporter.LoadMaterialOverrides(modelID)
    return all[tostring(submeshIndex)] or {}
end

function PMXStaticImporter.ApplyMaterialOverrides(modelID)
    modelID = PMXStaticImporter.NormalizeModelID(modelID)
    PMXStaticImporter.ClearCache(modelID)
end

local function destroy_renderable(renderable)
    if not renderable or not renderable.drawItems then return end

    for _, item in ipairs(renderable.drawItems) do
        if item and item.mesh and item.mesh.Destroy then
            pcall(function()
                item.mesh:Destroy()
            end)
        end
    end
end

function PMXStaticImporter.ClearCache(modelID)
    if not modelID or modelID == "" then
        for key, renderable in pairs(PMXStaticImporter.RenderableCache) do
            destroy_renderable(renderable)
            PMXStaticImporter.RenderableCache[key] = nil
        end
        PMXStaticImporter.MaterialCache = {}
        PMXStaticImporter.MaterialOverrides = {}
        return
    end

    modelID = PMXStaticImporter.NormalizeModelID(modelID)
    if not modelID then return end

    for key, renderable in pairs(PMXStaticImporter.RenderableCache) do
        if string.StartWith(key, modelID .. "::") then
            destroy_renderable(renderable)
            PMXStaticImporter.RenderableCache[key] = nil
        end
    end

    for key, material in pairs(PMXStaticImporter.MaterialCache) do
        if string.StartWith(key, modelID .. "|") then
            PMXStaticImporter.MaterialCache[key] = nil
        end
    end
end

local function get_image_material(imagePath)
    if not imagePath or imagePath == "" then
        return PMXStaticImporter.DebugWhite
    end

    local loaded = Material(imagePath, "vertexlitgeneric noclamp smooth")
    if not loaded or loaded:IsError() then
        return PMXStaticImporter.DebugWhite
    end

    return loaded
end

local function get_render_material(modelID, submesh, submeshIndex)
    local imagePath = tostring(submesh.image_path or "")
    local overrides = PMXStaticImporter.GetSubmeshOverrides(modelID, submeshIndex)
    local defs = PMXStaticImporter.ShaderDefaults

    local function ov(key)
        if overrides[key] ~= nil then return overrides[key] end
        return defs[key]
    end

    -- Effective rendering flags (submesh-derived, overrideable)
    local noCull
    if overrides.nocull ~= nil then
        noCull = tobool(overrides.nocull)
    else
        noCull = (submesh.no_cull == nil) or tobool(submesh.no_cull) or tobool(submesh.double_sided)
    end

    local alpha = clamp01(submesh.alpha or 1)
    local translucent
    if overrides.translucent ~= nil then
        translucent = tobool(overrides.translucent)
    else
        translucent = tobool(submesh.translucent) or alpha < 0.999
    end

    local cacheKey = table.concat({
        tostring(modelID or ""),
        tostring(submeshIndex or 0),
        imagePath,
    }, "|")

    local cached = PMXStaticImporter.MaterialCache[cacheKey]
    if cached and not cached:IsError() then
        return cached, noCull, translucent
    end

    local loadedImageMaterial = get_image_material(imagePath)
    local materialName = "pmx_static_importer_" .. util.CRC(cacheKey)

    local fresnel = ov("phongfresnelranges")
    if not istable(fresnel) then fresnel = {0, 0, 1} end

    local params = {
        ["$basetexture"] = loadedImageMaterial:GetName(),
        ["$bumpmap"] = ov("bumpmap") or "models/sheepylord/shared/normal",
        ["$lightwarptexture"] = ov("lightwarptexture") or "models/sheepylord/shared/lightwarptexture",

        ["$phong"] = ov("phong") and 1 or 0,
        ["$phongboost"] = tonumber(ov("phongboost")) or 24,
        ["$phongalbedotint"] = ov("phongalbedotint") and 1 or 0,
        ["$phongexponenttexture"] = ov("phongexponenttexture") or "models/sheepylord/shared/phong_exp",
        ["$phongfresnelranges"] = string.format("[%s %s %s]",
            tonumber(fresnel[1]) or 0, tonumber(fresnel[2]) or 0, tonumber(fresnel[3]) or 1),

        ["$rimlight"] = ov("rimlight") and 1 or 0,
        ["$rimlightexponent"] = tonumber(ov("rimlightexponent")) or 2,
        ["$rimlightboost"] = tonumber(ov("rimlightboost")) or 2,
    }

    if ov("halflambert") then
        params["$halflambert"] = 1
    end

    local pab = tonumber(ov("phongalbedoboost"))
    if pab and pab > 0 then
        params["$phongalbedoboost"] = pab
    end

    if ov("selfillum") then
        params["$selfillum"] = 1
        local mask = ov("selfillummask")
        if mask and mask ~= "" then
            params["$selfillummask"] = mask
        end
        local tint = ov("selfillumtint")
        if istable(tint) then
            params["$selfillumtint"] = string.format("[%s %s %s]",
                tonumber(tint[1]) or 0.5, tonumber(tint[2]) or 0.5, tonumber(tint[3]) or 0.5)
        end
    end

    if noCull then
        params["$nocull"] = 1
    end

    if translucent then
        params["$translucent"] = 1
        params["$vertexalpha"] = 1
        params["$vertexcolor"] = 1
    else
        local useAlphatest
        if overrides.alphatest ~= nil then
            useAlphatest = tobool(overrides.alphatest)
        else
            useAlphatest = is_png_path(imagePath)
        end
        if useAlphatest then
            params["$alphatest"] = 1
            params["$alphatestreference"] = tonumber(ov("alphatestreference")) or 0.5
            local useAtoc
            if overrides.allowalphatocoverage ~= nil then
                useAtoc = tobool(overrides.allowalphatocoverage)
            else
                useAtoc = true
            end
            if useAtoc then
                params["$allowalphatocoverage"] = 1
            end
        end
    end

    local renderMaterial = CreateMaterial(materialName, "VertexLitGeneric", params)
    if not renderMaterial or renderMaterial:IsError() then
        renderMaterial = PMXStaticImporter.DebugWhite
    end

    PMXStaticImporter.MaterialCache[cacheKey] = renderMaterial
    return renderMaterial, noCull, translucent
end

local function build_chunk_mesh(material, verts)
    if not verts or #verts < 3 then return nil end

    local remainder = #verts % 3
    if remainder ~= 0 then
        for _ = 1, remainder do
            verts[#verts] = nil
        end
        if #verts < 3 then
            return nil
        end
    end

    local meshObject = Mesh(material or PMXStaticImporter.DebugWhite)
    meshObject:BuildFromTriangles(verts)
    return meshObject
end

local function read_mesh_file(meshPath, manifest)
    -- Try DATA first (user imports), then GAME data_static (workshop addons)
    local f = file.Open(meshPath, "rb", "DATA")
    if not f then
        local gameRelPath = "data_static/" .. meshPath
        f = file.Open(gameRelPath, "rb", "GAME")
    end
    if not f then
        return nil, PMXStaticImporter.TF("error_could_not_open_mesh_file", nil, tostring(meshPath))
    end

    local ok, resultOrErr = xpcall(function()
        local magic = f:Read(8)
        if magic ~= "PMXSM01\0" then
            error(PMXStaticImporter.TF("error_unexpected_mesh_magic", nil, tostring(meshPath)))
        end

        local submeshCount = f:ReadULong()
        local submeshes = manifest.submeshes or {}
        if submeshCount ~= #submeshes then
            error(PMXStaticImporter.TF("error_mesh_submesh_count_mismatch", nil, tostring(manifest.model_id or "unknown")))
        end

        local drawItems = {}
        for i = 1, submeshCount do
            local entry = submeshes[i] or {}
            local vertexCount = f:ReadULong()

            local subOverrides = PMXStaticImporter.GetSubmeshOverrides(manifest.model_id or "", i)
            if tobool(subOverrides.disabled) then
                if vertexCount > 0 then
                    f:Seek(f:Tell() + vertexCount * 32)
                end
            else
            local diffuse = entry.diffuse or {1, 1, 1, 1}
            local alpha = clamp01(entry.alpha or diffuse[4] or 1)
            local material, noCull, translucent = get_render_material(manifest.model_id or "", entry, i)
            local chunkVerts = {}

            local function flush_chunk()
                local meshObject = build_chunk_mesh(material, chunkVerts)
                if not meshObject then
                    chunkVerts = {}
                    return
                end

                drawItems[#drawItems + 1] = {
                    mesh = meshObject,
                    material = material,
                    diffuseR = clamp01(diffuse[1] or 1),
                    diffuseG = clamp01(diffuse[2] or 1),
                    diffuseB = clamp01(diffuse[3] or 1),
                    alpha = alpha,
                    noCull = noCull,
                    translucent = translucent,
                    meta = entry,
                }
                chunkVerts = {}
            end

            for vertexIndex = 1, vertexCount do
                local px = f:ReadFloat()
                local py = f:ReadFloat()
                local pz = f:ReadFloat()
                local nx = f:ReadFloat()
                local ny = f:ReadFloat()
                local nz = f:ReadFloat()
                local u = f:ReadFloat()
                local v = f:ReadFloat()

                chunkVerts[#chunkVerts + 1] = {
                    pos = Vector(px, py, pz),
                    normal = Vector(nx, ny, nz),
                    u = u,
                    v = v,
                }

                if #chunkVerts >= PMXStaticImporter.MaxVertsPerMesh then
                    flush_chunk()
                end
            end

            flush_chunk()
            end -- if not disabled
        end

        return drawItems
    end, debug.traceback)

    f:Close()

    if not ok then
        return nil, resultOrErr
    end

    return resultOrErr
end

function PMXStaticImporter.GetRenderable(modelID)
    local manifest, err = PMXStaticImporter.LoadManifest(modelID)
    if not manifest then
        return nil, err
    end

    local cacheKey = make_cache_key(manifest.model_id or modelID, manifest.build_id or "")
    local cached = PMXStaticImporter.RenderableCache[cacheKey]
    if cached then
        return cached
    end

    local drawItems, meshErr = read_mesh_file(manifest.mesh_file, manifest)
    if not drawItems then
        return nil, meshErr
    end

    local mins, maxs = PMXStaticImporter.GetBoundsFromManifest(manifest)
    local renderable = {
        manifest = manifest,
        drawItems = drawItems,
        mins = mins,
        maxs = maxs,
    }

    PMXStaticImporter.RenderableCache[cacheKey] = renderable
    return renderable
end

local function draw_renderable_pass(ent, renderable, wantTranslucent)
    if not IsValid(ent) or not renderable then return end

    local scale = math.max(ent.GetPMXScale and (ent:GetPMXScale() or 1) or 1, 0.0001)
    local mins = renderable.mins * scale
    local maxs = renderable.maxs * scale
    ent:SetRenderBounds(mins, maxs)

    local entColor = ent.GetPMXColor and ent:GetPMXColor() or Vector(1, 1, 1)
    local tintR = entColor.x or 1
    local tintG = entColor.y or 1
    local tintB = entColor.z or 1

    local matrix = Matrix()
    matrix:Translate(ent:GetPos())
    matrix:Rotate(ent:GetAngles())
    matrix:Scale(Vector(scale, scale, scale))

    cam.PushModelMatrix(matrix)
        for _, item in ipairs(renderable.drawItems or {}) do
            if item.translucent == wantTranslucent then
                render.SetMaterial(item.material or PMXStaticImporter.DebugWhite)
                render.SetColorModulation(
                    (item.diffuseR or 1) * tintR,
                    (item.diffuseG or 1) * tintG,
                    (item.diffuseB or 1) * tintB
                )
                render.SetBlend(item.alpha or 1)
                render.CullMode(item.noCull and MATERIAL_CULLMODE_NONE or MATERIAL_CULLMODE_CCW)
                if item.mesh then
                    item.mesh:Draw()
                end
            end
        end
    cam.PopModelMatrix()
end

local function renderable_has_pass(renderable, wantTranslucent)
    for _, item in ipairs(renderable and renderable.drawItems or {}) do
        if item.translucent == wantTranslucent then
            return true
        end
    end

    return false
end

local function get_renderable_lighting_origin(ent, renderable)
    local scale = math.max(ent.GetPMXScale and (ent:GetPMXScale() or 1) or 1, 0.0001)
    local localCenter = (renderable.mins + renderable.maxs) * (0.5 * scale)
    return ent:LocalToWorld(localCenter)
end

local renderableLightSamples = {
    {box = BOX_FRONT, normal = Vector(1, 0, 0)},
    {box = BOX_BACK, normal = Vector(-1, 0, 0)},
    {box = BOX_RIGHT, normal = Vector(0, -1, 0)},
    {box = BOX_LEFT, normal = Vector(0, 1, 0)},
    {box = BOX_TOP, normal = Vector(0, 0, 1)},
    {box = BOX_BOTTOM, normal = Vector(0, 0, -1)},
}

local function apply_renderable_map_lighting(ent, renderable)
    if not IsValid(ent) or not renderable then return end

    -- IMesh:Draw with VertexLitGeneric can consume lighting supplied through
    -- the render library, so explicitly build the ambient cube from the map
    -- lighting at the imported mesh center instead of relying on DrawModel().
    local lightingOrigin = get_renderable_lighting_origin(ent, renderable)
    render.SetLocalModelLights()
    render.ResetModelLighting(0, 0, 0)

    for _, sample in ipairs(renderableLightSamples) do
        local lightColor = render.ComputeLighting(lightingOrigin, sample.normal)
        render.SetModelLighting(sample.box, lightColor.x, lightColor.y, lightColor.z)
    end
end

local function draw_lit_renderable_pass(ent, renderable, wantTranslucent)
    if not renderable_has_pass(renderable, wantTranslucent) then return end

    apply_renderable_map_lighting(ent, renderable)
    draw_renderable_pass(ent, renderable, wantTranslucent)

    render.RenderFlashlights(function()
        apply_renderable_map_lighting(ent, renderable)
        draw_renderable_pass(ent, renderable, wantTranslucent)
    end)
end

function PMXStaticImporter.DrawRenderable(ent, renderable)
    draw_lit_renderable_pass(ent, renderable, false)
    draw_lit_renderable_pass(ent, renderable, true)

    render.CullMode(MATERIAL_CULLMODE_CCW)
    render.SetBlend(1)
    render.SetColorModulation(1, 1, 1)
end

function PMXStaticImporter.DrawRenderableOpaque(ent, renderable)
    draw_lit_renderable_pass(ent, renderable, false)

    render.CullMode(MATERIAL_CULLMODE_CCW)
    render.SetBlend(1)
    render.SetColorModulation(1, 1, 1)
end

function PMXStaticImporter.DrawRenderableTranslucent(ent, renderable)
    draw_lit_renderable_pass(ent, renderable, true)

    render.CullMode(MATERIAL_CULLMODE_CCW)
    render.SetBlend(1)
    render.SetColorModulation(1, 1, 1)
end

-- Entity rendering is handled by ENT:Draw() and ENT:DrawTranslucent()
-- in cl_init.lua so the shadow system can see the geometry.
