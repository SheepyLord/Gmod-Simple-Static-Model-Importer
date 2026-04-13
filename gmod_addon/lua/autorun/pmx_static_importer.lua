if SERVER then
    AddCSLuaFile("pmx_static_importer/sh_core.lua")
    AddCSLuaFile("pmx_static_importer/cl_runtime.lua")
    AddCSLuaFile("pmx_static_importer/cl_material_editor.lua")
    util.AddNetworkString("pmx_static_importer_request_list")
    util.AddNetworkString("pmx_static_importer_send_list")
end

include("pmx_static_importer/sh_core.lua")
if CLIENT then
    include("pmx_static_importer/cl_runtime.lua")
    include("pmx_static_importer/cl_material_editor.lua")
end

local function send_model_list(ply)
    local list = PMXStaticImporter.ListAvailableModels()

    net.Start("pmx_static_importer_send_list")
        net.WriteUInt(#list, 16)
        for _, entry in ipairs(list) do
            net.WriteString(tostring(entry.model_id or ""))
            net.WriteString(tostring(entry.display_name or entry.model_id or ""))
            net.WriteUInt(math.max(0, math.floor(tonumber(entry.triangle_count) or 0)), 32)
            net.WriteUInt(math.max(0, math.floor(tonumber(entry.material_count) or 0)), 16)
            net.WriteString(tostring(entry.build_id or ""))
        end
    if SERVER then
        net.Send(ply)
    end
end

if SERVER then
    net.Receive("pmx_static_importer_request_list", function(_, ply)
        send_model_list(ply)
    end)
else
    net.Receive("pmx_static_importer_send_list", function()
        local count = net.ReadUInt(16)
        local list = {}

        for i = 1, count do
            list[i] = {
                model_id = net.ReadString(),
                display_name = net.ReadString(),
                triangle_count = net.ReadUInt(32),
                material_count = net.ReadUInt(16),
                build_id = net.ReadString(),
            }
        end

        PMXStaticImporter.LastModelList = list
        hook.Run("PMXStaticImporterModelListUpdated", list)
    end)

    concommand.Add("pmx_static_importer_refresh", function()
        net.Start("pmx_static_importer_request_list")
        net.SendToServer()
    end)

    concommand.Add("pmx_static_importer_clear_cache", function(_, _, args)
        if args and args[1] then
            PMXStaticImporter.ClearCache(args[1])
        else
            PMXStaticImporter.ClearCache()
        end
    end)
end
