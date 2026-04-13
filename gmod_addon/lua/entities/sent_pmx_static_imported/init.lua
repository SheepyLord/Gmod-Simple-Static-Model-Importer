AddCSLuaFile("shared.lua")
AddCSLuaFile("cl_init.lua")
AddCSLuaFile("pmx_static_importer/sh_core.lua")
AddCSLuaFile("pmx_static_importer/cl_runtime.lua")

include("shared.lua")
include("pmx_static_importer/sh_core.lua")

local DEFAULT_PLACEHOLDER_MODEL = "models/hunter/blocks/cube025x025x025.mdl"

local function freeze_physics(ent)
    local phys = ent:GetPhysicsObject()
    if IsValid(phys) then
        phys:Wake()
        phys:EnableMotion(false)
    end
end

function ENT:Initialize()
    self:SetModel(DEFAULT_PLACEHOLDER_MODEL)
    self:DrawShadow(true)

    self:SetMoveType(MOVETYPE_VPHYSICS)
    self:SetSolid(SOLID_VPHYSICS)
    self:SetUseType(SIMPLE_USE)

    self:RebuildPhysics()
end

function ENT:UpdateImportedBounds(manifest)
    local mins, maxs = PMXStaticImporter.GetBoundsFromManifest(manifest)
    local scale = math.max(self:GetPMXScale() or 1, 0.0001)

    mins = mins * scale
    maxs = maxs * scale

    self:SetCollisionBounds(mins, maxs)
    -- SetRenderBounds is client-side only, handled in cl_init.lua

    return mins, maxs
end

function ENT:RebuildPhysics()
    local manifest = PMXStaticImporter.LoadManifest(self:GetPMXModelID())
    local mins, maxs = self:UpdateImportedBounds(manifest)

    self:PhysicsInitBox(mins, maxs)
    freeze_physics(self)
end

function ENT:ApplyImportedModel(modelID, scale, langOrPly)
    modelID = PMXStaticImporter.NormalizeModelID(modelID)
    if not modelID then return false, PMXStaticImporter.T("error_invalid_model_id", langOrPly) end

    local manifest, err = PMXStaticImporter.LoadManifest(modelID, langOrPly)
    if not manifest then
        return false, err or PMXStaticImporter.T("error_manifest_could_not_be_loaded", langOrPly)
    end

    self:SetPMXModelID(modelID)
    self:SetPMXScale(math.max(tonumber(scale) or 1, 0.0001))
    self:RebuildPhysics()

    return true
end

function ENT:OnDuplicated(entTable)
    entTable.PMXModelID = self:GetPMXModelID()
    entTable.PMXScale = self:GetPMXScale()
end

function ENT:PostEntityPaste(ply, ent, createdEntities)
    self:RebuildPhysics()
end
