include("shared.lua")
include("pmx_static_importer/sh_core.lua")
include("pmx_static_importer/cl_runtime.lua")

function ENT:Initialize()
    self:UpdateClientRenderBounds()
end

function ENT:UpdateClientRenderBounds()
    local modelID = self:GetPMXModelID()
    if not modelID then return end
    
    local manifest = PMXStaticImporter.LoadManifest(modelID)
    if not manifest then return end
    
    local mins, maxs = PMXStaticImporter.GetBoundsFromManifest(manifest)
    local scale = math.max(self:GetPMXScale() or 1, 0.0001)
    
    mins = mins * scale
    maxs = maxs * scale
    
    self:SetRenderBounds(mins, maxs)
end

function ENT:Think()
    -- Update render bounds and shadow when model data changes
    if self._lastModelID ~= self:GetPMXModelID() or self._lastScale ~= self:GetPMXScale() then
        self._lastModelID = self:GetPMXModelID()
        self._lastScale = self:GetPMXScale()
        self:UpdateClientRenderBounds()
        self:MarkShadowAsDirty()
    end

    -- Follow bone binding
    local target = self:GetPMXBindTarget()
    if IsValid(target) then
        target:SetupBones(BONE_USED_BY_ANYTHING, CurTime())
        local boneIdx = self:GetPMXBindBone() or 0
        local matrix = target:GetBoneMatrix(boneIdx)
        if matrix then
            local bonePos = matrix:GetTranslation()
            local boneAng = matrix:GetAngles()
            local offset = self:GetPMXBindPos() or Vector(0, 0, 0)
            local offsetAng = self:GetPMXBindAng() or Angle(0, 0, 0)
            local finalPos, finalAng = LocalToWorld(offset, offsetAng, bonePos, boneAng)
            self:SetPos(finalPos)
            self:SetAngles(finalAng)
        end
    end
end

function ENT:Draw()
    local modelID = self:GetPMXModelID()
    if not modelID or modelID == "" then return end

    local renderable = PMXStaticImporter.GetRenderable(modelID)
    if not renderable then return end

    PMXStaticImporter.DrawRenderableOpaque(self, renderable)
    self:CreateShadow()
end

function ENT:DrawTranslucent()
    local modelID = self:GetPMXModelID()
    if not modelID or modelID == "" then return end

    local renderable = PMXStaticImporter.GetRenderable(modelID)
    if not renderable then return end

    PMXStaticImporter.DrawRenderableTranslucent(self, renderable)
end
