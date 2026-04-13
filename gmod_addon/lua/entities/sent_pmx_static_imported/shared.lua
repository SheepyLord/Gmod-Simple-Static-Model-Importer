ENT.Type = "anim"
ENT.Base = "base_anim"
ENT.PrintName = "#pmx_static_importer.entity_name"
ENT.Author = "SheepyLord"
ENT.Category = "#pmx_static_importer.category"
ENT.Spawnable = false
ENT.AdminOnly = false
ENT.RenderGroup = RENDERGROUP_BOTH

function ENT:SetupDataTables()
    self:NetworkVar("String", 0, "PMXModelID")
    self:NetworkVar("Float", 0, "PMXScale")
    self:NetworkVar("Vector", 0, "PMXColor")

    if SERVER then
        self:SetPMXModelID(self:GetPMXModelID() or "")
        if (self:GetPMXScale() or 0) <= 0 then
            self:SetPMXScale(1)
        end
        if not self:GetPMXColor() or self:GetPMXColor() == Vector(0, 0, 0) then
            self:SetPMXColor(Vector(1, 1, 1))
        end
    end
end
