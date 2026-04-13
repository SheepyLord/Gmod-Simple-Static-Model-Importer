PMXStaticImporter = PMXStaticImporter or {}
PMXStaticImporter.DataRoot = "pmx_static_importer/models"
PMXStaticImporter.GameDataRoot = "data_static/pmx_static_importer/models"
PMXStaticImporter.ManifestName = "manifest.json"

PMXStaticImporter.Translations = PMXStaticImporter.Translations or {
    en = {
        category_animation = "Model Importer",
        tool_name = "Static Model Importer",
        tool_desc = "Spawn imported static PMX meshes from garrysmod/data and garrysmod/materials.",
        tool_help = "Select an imported PMX in the panel, then left-click to place it.",
        entity_name = "PMX Imported Static Object",

        ui_material_editor = "Material Editor",
        ui_material_editor_title = "Material Editor — %s",
        ui_materials_count = "Materials (%d)",
        ui_name = "Name",
        ui_preview = "Preview — %s",
        ui_import = "Import",
        ui_texture_maps = "Texture Maps",
        ui_rendering = "Rendering",
        ui_lighting = "Lighting",
        ui_self_illumination = "Self Illumination",
        ui_self_illum_tint = "Self Illum Tint",
        ui_phong_shading = "Phong Shading",
        ui_phong_fresnel_ranges = "Phong Fresnel Ranges",
        ui_rim_light = "Rim Light",
        ui_material_default_name = "Material %d",
        ui_texture_not_found = "Texture not found: %s",
        ui_no_base_texture = "No base texture",
        ui_base_texture = "Base texture: %s",
        ui_none = "(none)",

        dialog_ok = "OK",
        dialog_yes = "Yes",
        dialog_no = "No",
        dialog_confirm_reset = "Confirm Reset",
        dialog_confirm_reset_text = "Reset ALL material overrides for this model?",

        button_save_apply = "Save & Apply",
        button_reset_this_material = "Reset This Material",
        button_only_this = "Only This",
        button_enable_all = "Enable All",
        button_disable_all = "Disable All",
        button_reset_all_materials = "Reset All Materials",
        button_refresh_imported_model_list = "Refresh imported model list",
        button_clear_client_cache = "Clear client mesh/material cache",
        button_edit_materials = "Edit Materials...",

        label_include_mesh_when_importing = "Include this mesh when importing",
        label_bump_map = "Bump Map",
        label_light_warp = "Light Warp",
        label_self_illum_mask = "Self Illum Mask",
        label_phong_exponent_tex = "Phong Exponent Tex",
        label_no_cull = "No Cull (double-sided)",
        label_translucent = "Translucent",
        label_alpha_test = "Alpha Test",
        label_alpha_test_reference = "Alpha Test Reference",
        label_alpha_to_coverage = "Alpha To Coverage",
        label_half_lambert = "Half Lambert",
        label_enable_self_illum = "Enable Self Illum",
        label_enable_phong = "Enable Phong",
        label_phong_boost = "Phong Boost",
        label_phong_albedo_tint = "Phong Albedo Tint",
        label_phong_albedo_boost = "Phong Albedo Boost",
        label_enable_rim_light = "Enable Rim Light",
        label_rim_exponent = "Rim Exponent",
        label_rim_boost = "Rim Boost",

        panel_description = "List imported PMX models from garrysmod/data/pmx_static_importer/models, then left-click to place them.\nRight-click copies the model id from an existing imported entity. Reload removes one.",
        panel_display_name = "Display Name",
        panel_model_id = "Model ID",
        panel_triangles = "Triangles",
        panel_materials = "Materials",
        panel_selected_model_id = "Selected model id",
        panel_scale = "Scale",
        panel_yaw = "Yaw",
        panel_physics_properties = "Physics Properties",
        panel_disable_collision = "Disable Collision",
        panel_disable_gravity = "Disable Gravity",
        panel_color_modulation = "Color Modulation",
        panel_tip_refresh = "Tip: if you re-import a model while the map is open, use Refresh + Clear Cache before spawning it again.",

        chat_no_imported_model_selected = "No imported model is selected.",
        chat_failed_create_entity = "Failed to create entity.",
        chat_spawned = "Spawned '%s'",
        chat_copied_model_id_and_scale = "Copied model id and scale from the selected entity.",
        chat_removed_imported_entity = "Removed imported PMX entity.",

        error_invalid_model_id = "Invalid model id.",
        error_manifest_not_found = "Manifest not found: %s",
        error_manifest_parse_failed = "Manifest JSON could not be parsed: %s",
        error_manifest_could_not_be_loaded = "Manifest could not be loaded.",
        error_could_not_load_manifest_for = "Could not load manifest for: %s",
        error_no_materials_found_in_model = "No materials found in model.",
        error_failed_to_apply_imported_model = "Failed to apply imported model.",
        error_could_not_open_mesh_file = "Could not open mesh file: %s",
        error_unexpected_mesh_magic = "Unexpected mesh file magic in %s",
        error_mesh_submesh_count_mismatch = "Mesh file submesh count does not match manifest for %s",

        component_min = "Min",
        component_mid = "Mid",
        component_max = "Max",
    },
    ["zh-CN"] = {
        category_animation = "模型导入器",
        tool_name = "静态模型导入器",
        tool_desc = "从 garrysmod/data 和 garrysmod/materials 中生成已导入的静态 PMX 网格。",
        tool_help = "在面板中选择一个已导入的 PMX，然后左键放置。",
        entity_name = "PMX 导入静态对象",

        ui_material_editor = "材质编辑器",
        ui_material_editor_title = "材质编辑器 — %s",
        ui_materials_count = "材质 (%d)",
        ui_name = "名称",
        ui_preview = "预览 — %s",
        ui_import = "导入",
        ui_texture_maps = "纹理贴图",
        ui_rendering = "渲染",
        ui_lighting = "光照",
        ui_self_illumination = "自发光",
        ui_self_illum_tint = "自发光颜色",
        ui_phong_shading = "Phong 着色",
        ui_phong_fresnel_ranges = "Phong 菲涅耳范围",
        ui_rim_light = "边缘光",
        ui_material_default_name = "材质 %d",
        ui_texture_not_found = "未找到纹理：%s",
        ui_no_base_texture = "没有基础纹理",
        ui_base_texture = "基础纹理：%s",
        ui_none = "(无)",

        dialog_ok = "确定",
        dialog_yes = "是",
        dialog_no = "否",
        dialog_confirm_reset = "确认重置",
        dialog_confirm_reset_text = "要重置此模型的所有材质覆盖设置吗？",

        button_save_apply = "保存并应用",
        button_reset_this_material = "重置当前材质",
        button_only_this = "仅保留当前",
        button_enable_all = "全部启用",
        button_disable_all = "全部禁用",
        button_reset_all_materials = "重置全部材质",
        button_refresh_imported_model_list = "刷新已导入模型列表",
        button_clear_client_cache = "清除客户端网格/材质缓存",
        button_edit_materials = "编辑材质...",

        label_include_mesh_when_importing = "导入时包含此网格",
        label_bump_map = "凹凸贴图",
        label_light_warp = "光照渐变贴图",
        label_self_illum_mask = "自发光遮罩",
        label_phong_exponent_tex = "Phong 指数贴图",
        label_no_cull = "不剔除（双面）",
        label_translucent = "半透明",
        label_alpha_test = "Alpha 测试",
        label_alpha_test_reference = "Alpha 测试阈值",
        label_alpha_to_coverage = "Alpha To Coverage",
        label_half_lambert = "半 Lambert",
        label_enable_self_illum = "启用自发光",
        label_enable_phong = "启用 Phong",
        label_phong_boost = "Phong 强度",
        label_phong_albedo_tint = "Phong 反照率着色",
        label_phong_albedo_boost = "Phong 反照率增强",
        label_enable_rim_light = "启用边缘光",
        label_rim_exponent = "边缘光指数",
        label_rim_boost = "边缘光增强",

        panel_description = "列出 garrysmod/data/pmx_static_importer/models 中已导入的 PMX 模型，然后左键放置它们。\n右键可从现有已导入实体复制模型 ID。按 R 键可删除一个。",
        panel_display_name = "显示名称",
        panel_model_id = "模型 ID",
        panel_triangles = "三角形数",
        panel_materials = "材质数",
        panel_selected_model_id = "已选择的模型 ID",
        panel_scale = "缩放",
        panel_yaw = "偏航",
        panel_physics_properties = "物理属性",
        panel_disable_collision = "禁用碰撞",
        panel_disable_gravity = "禁用重力",
        panel_color_modulation = "颜色调制",
        panel_tip_refresh = "提示：如果在地图打开时重新导入了模型，请在再次生成前先使用“刷新”与“清除缓存”。",

        chat_no_imported_model_selected = "未选择已导入模型。",
        chat_failed_create_entity = "创建实体失败。",
        chat_spawned = "已生成“%s”",
        chat_copied_model_id_and_scale = "已从所选实体复制模型 ID 和缩放值。",
        chat_removed_imported_entity = "已删除导入的 PMX 实体。",

        error_invalid_model_id = "无效的模型 ID。",
        error_manifest_not_found = "未找到清单：%s",
        error_manifest_parse_failed = "无法解析清单 JSON：%s",
        error_manifest_could_not_be_loaded = "无法加载清单。",
        error_could_not_load_manifest_for = "无法加载以下模型的清单：%s",
        error_no_materials_found_in_model = "模型中未找到材质。",
        error_failed_to_apply_imported_model = "应用导入模型失败。",
        error_could_not_open_mesh_file = "无法打开网格文件：%s",
        error_unexpected_mesh_magic = "%s 中的网格文件标识不正确",
        error_mesh_submesh_count_mismatch = "%s 的网格文件子网格数量与清单不匹配",

        component_min = "最小",
        component_mid = "中间",
        component_max = "最大",
    },
    fr = {
        category_animation = "Importateur de modèles",
        tool_name = "Importateur de modèles statiques",
        tool_desc = "Fait apparaître des maillages PMX statiques importés depuis garrysmod/data et garrysmod/materials.",
        tool_help = "Sélectionnez un PMX importé dans le panneau, puis cliquez gauche pour le placer.",
        entity_name = "Objet statique PMX importé",

        ui_material_editor = "Éditeur de matériaux",
        ui_material_editor_title = "Éditeur de matériaux — %s",
        ui_materials_count = "Matériaux (%d)",
        ui_name = "Nom",
        ui_preview = "Aperçu — %s",
        ui_import = "Importation",
        ui_texture_maps = "Textures",
        ui_rendering = "Rendu",
        ui_lighting = "Éclairage",
        ui_self_illumination = "Auto-illumination",
        ui_self_illum_tint = "Teinte d’auto-illumination",
        ui_phong_shading = "Ombrage Phong",
        ui_phong_fresnel_ranges = "Plages de Fresnel Phong",
        ui_rim_light = "Lumière de contour",
        ui_material_default_name = "Matériau %d",
        ui_texture_not_found = "Texture introuvable : %s",
        ui_no_base_texture = "Aucune texture de base",
        ui_base_texture = "Texture de base : %s",
        ui_none = "(aucune)",

        dialog_ok = "OK",
        dialog_yes = "Oui",
        dialog_no = "Non",
        dialog_confirm_reset = "Confirmer la réinitialisation",
        dialog_confirm_reset_text = "Réinitialiser TOUS les remplacements de matériaux pour ce modèle ?",

        button_save_apply = "Enregistrer et appliquer",
        button_reset_this_material = "Réinitialiser ce matériau",
        button_only_this = "Seulement celui-ci",
        button_enable_all = "Tout activer",
        button_disable_all = "Tout désactiver",
        button_reset_all_materials = "Réinitialiser tous les matériaux",
        button_refresh_imported_model_list = "Actualiser la liste des modèles importés",
        button_clear_client_cache = "Vider le cache client des maillages/matériaux",
        button_edit_materials = "Modifier les matériaux...",

        label_include_mesh_when_importing = "Inclure ce maillage lors de l’import",
        label_bump_map = "Bump map",
        label_light_warp = "Light Warp",
        label_self_illum_mask = "Masque d’auto-illumination",
        label_phong_exponent_tex = "Texture d’exposant Phong",
        label_no_cull = "Pas de culling (double face)",
        label_translucent = "Translucide",
        label_alpha_test = "Test alpha",
        label_alpha_test_reference = "Seuil du test alpha",
        label_alpha_to_coverage = "Alpha To Coverage",
        label_half_lambert = "Half-Lambert",
        label_enable_self_illum = "Activer l’auto-illumination",
        label_enable_phong = "Activer Phong",
        label_phong_boost = "Gain Phong",
        label_phong_albedo_tint = "Teinte d’albédo Phong",
        label_phong_albedo_boost = "Gain d’albédo Phong",
        label_enable_rim_light = "Activer la lumière de contour",
        label_rim_exponent = "Exposant du contour",
        label_rim_boost = "Gain du contour",

        panel_description = "Liste les modèles PMX importés depuis garrysmod/data/pmx_static_importer/models, puis permet de les placer avec un clic gauche.\nUn clic droit copie l’ID du modèle depuis une entité importée existante. Recharger en supprime une.",
        panel_display_name = "Nom affiché",
        panel_model_id = "ID du modèle",
        panel_triangles = "Triangles",
        panel_materials = "Matériaux",
        panel_selected_model_id = "ID du modèle sélectionné",
        panel_scale = "Échelle",
        panel_yaw = "Lacet",
        panel_physics_properties = "Propriétés physiques",
        panel_disable_collision = "Désactiver les collisions",
        panel_disable_gravity = "Désactiver la gravité",
        panel_color_modulation = "Modulation de couleur",
        panel_tip_refresh = "Astuce : si vous réimportez un modèle pendant que la carte est ouverte, utilisez Actualiser + Vider le cache avant de le replacer.",

        chat_no_imported_model_selected = "Aucun modèle importé n’est sélectionné.",
        chat_failed_create_entity = "Échec de la création de l’entité.",
        chat_spawned = "« %s » a été créé",
        chat_copied_model_id_and_scale = "L’ID du modèle et l’échelle ont été copiés depuis l’entité sélectionnée.",
        chat_removed_imported_entity = "L’entité PMX importée a été supprimée.",

        error_invalid_model_id = "ID de modèle invalide.",
        error_manifest_not_found = "Manifeste introuvable : %s",
        error_manifest_parse_failed = "Impossible d’analyser le JSON du manifeste : %s",
        error_manifest_could_not_be_loaded = "Le manifeste n’a pas pu être chargé.",
        error_could_not_load_manifest_for = "Impossible de charger le manifeste pour : %s",
        error_no_materials_found_in_model = "Aucun matériau trouvé dans le modèle.",
        error_failed_to_apply_imported_model = "Échec de l’application du modèle importé.",
        error_could_not_open_mesh_file = "Impossible d’ouvrir le fichier mesh : %s",
        error_unexpected_mesh_magic = "Signature de fichier mesh inattendue dans %s",
        error_mesh_submesh_count_mismatch = "Le nombre de sous-maillages du fichier mesh ne correspond pas au manifeste pour %s",

        component_min = "Min",
        component_mid = "Milieu",
        component_max = "Max",
    },
    ja = {
        category_animation = "モデルインポーター",
        tool_name = "静的モデルインポーター",
        tool_desc = "garrysmod/data と garrysmod/materials からインポート済みの静的 PMX メッシュをスポーンします。",
        tool_help = "パネルでインポート済み PMX を選択し、左クリックで配置します。",
        entity_name = "PMX インポート済み静的オブジェクト",

        ui_material_editor = "マテリアルエディター",
        ui_material_editor_title = "マテリアルエディター — %s",
        ui_materials_count = "マテリアル (%d)",
        ui_name = "名前",
        ui_preview = "プレビュー — %s",
        ui_import = "インポート",
        ui_texture_maps = "テクスチャマップ",
        ui_rendering = "レンダリング",
        ui_lighting = "ライティング",
        ui_self_illumination = "自己発光",
        ui_self_illum_tint = "自己発光色",
        ui_phong_shading = "Phong シェーディング",
        ui_phong_fresnel_ranges = "Phong フレネル範囲",
        ui_rim_light = "リムライト",
        ui_material_default_name = "マテリアル %d",
        ui_texture_not_found = "テクスチャが見つかりません: %s",
        ui_no_base_texture = "ベーステクスチャなし",
        ui_base_texture = "ベーステクスチャ: %s",
        ui_none = "(なし)",

        dialog_ok = "OK",
        dialog_yes = "はい",
        dialog_no = "いいえ",
        dialog_confirm_reset = "リセットの確認",
        dialog_confirm_reset_text = "このモデルのすべてのマテリアル上書きをリセットしますか？",

        button_save_apply = "保存して適用",
        button_reset_this_material = "このマテリアルをリセット",
        button_only_this = "これのみ",
        button_enable_all = "すべて有効",
        button_disable_all = "すべて無効",
        button_reset_all_materials = "すべてのマテリアルをリセット",
        button_refresh_imported_model_list = "インポート済みモデル一覧を更新",
        button_clear_client_cache = "クライアントのメッシュ/マテリアルキャッシュを消去",
        button_edit_materials = "マテリアルを編集...",

        label_include_mesh_when_importing = "インポート時にこのメッシュを含める",
        label_bump_map = "バンプマップ",
        label_light_warp = "ライトワープ",
        label_self_illum_mask = "自己発光マスク",
        label_phong_exponent_tex = "Phong 指数テクスチャ",
        label_no_cull = "カリングなし（両面）",
        label_translucent = "半透明",
        label_alpha_test = "アルファテスト",
        label_alpha_test_reference = "アルファテスト基準値",
        label_alpha_to_coverage = "Alpha To Coverage",
        label_half_lambert = "ハーフランバート",
        label_enable_self_illum = "自己発光を有効化",
        label_enable_phong = "Phong を有効化",
        label_phong_boost = "Phong ブースト",
        label_phong_albedo_tint = "Phong アルベドティント",
        label_phong_albedo_boost = "Phong アルベドブースト",
        label_enable_rim_light = "リムライトを有効化",
        label_rim_exponent = "リム指数",
        label_rim_boost = "リムブースト",

        panel_description = "garrysmod/data/pmx_static_importer/models 内のインポート済み PMX モデルを一覧表示し、左クリックで配置します。\n右クリックで既存のインポート済みエンティティからモデル ID をコピーします。Reload で削除します。",
        panel_display_name = "表示名",
        panel_model_id = "モデル ID",
        panel_triangles = "三角形数",
        panel_materials = "マテリアル",
        panel_selected_model_id = "選択中のモデル ID",
        panel_scale = "スケール",
        panel_yaw = "ヨー",
        panel_physics_properties = "物理プロパティ",
        panel_disable_collision = "衝突を無効化",
        panel_disable_gravity = "重力を無効化",
        panel_color_modulation = "カラー変調",
        panel_tip_refresh = "ヒント: マップを開いたままモデルを再インポートした場合は、再配置する前に「更新」と「キャッシュ消去」を実行してください。",

        chat_no_imported_model_selected = "インポート済みモデルが選択されていません。",
        chat_failed_create_entity = "エンティティの作成に失敗しました。",
        chat_spawned = "「%s」をスポーンしました",
        chat_copied_model_id_and_scale = "選択したエンティティからモデル ID とスケールをコピーしました。",
        chat_removed_imported_entity = "インポート済み PMX エンティティを削除しました。",

        error_invalid_model_id = "無効なモデル ID です。",
        error_manifest_not_found = "マニフェストが見つかりません: %s",
        error_manifest_parse_failed = "マニフェスト JSON を解析できませんでした: %s",
        error_manifest_could_not_be_loaded = "マニフェストを読み込めませんでした。",
        error_could_not_load_manifest_for = "%s のマニフェストを読み込めませんでした",
        error_no_materials_found_in_model = "モデルにマテリアルが見つかりませんでした。",
        error_failed_to_apply_imported_model = "インポート済みモデルの適用に失敗しました。",
        error_could_not_open_mesh_file = "メッシュファイルを開けませんでした: %s",
        error_unexpected_mesh_magic = "%s 内のメッシュファイル識別子が不正です",
        error_mesh_submesh_count_mismatch = "%s のメッシュファイル内サブメッシュ数がマニフェストと一致しません",

        component_min = "最小",
        component_mid = "中間",
        component_max = "最大",
    },
    ko = {
        category_animation = "모델 임포터",
        tool_name = "정적 모델 임포터",
        tool_desc = "garrysmod/data 및 garrysmod/materials 에서 가져온 정적 PMX 메시를 생성합니다.",
        tool_help = "패널에서 가져온 PMX를 선택한 뒤, 왼쪽 클릭으로 배치하세요.",
        entity_name = "가져온 PMX 정적 오브젝트",

        ui_material_editor = "재질 편집기",
        ui_material_editor_title = "재질 편집기 — %s",
        ui_materials_count = "재질 (%d)",
        ui_name = "이름",
        ui_preview = "미리보기 — %s",
        ui_import = "가져오기",
        ui_texture_maps = "텍스처 맵",
        ui_rendering = "렌더링",
        ui_lighting = "조명",
        ui_self_illumination = "자체 발광",
        ui_self_illum_tint = "자체 발광 색조",
        ui_phong_shading = "Phong 셰이딩",
        ui_phong_fresnel_ranges = "Phong 프레넬 범위",
        ui_rim_light = "림 라이트",
        ui_material_default_name = "재질 %d",
        ui_texture_not_found = "텍스처를 찾을 수 없음: %s",
        ui_no_base_texture = "기본 텍스처 없음",
        ui_base_texture = "기본 텍스처: %s",
        ui_none = "(없음)",

        dialog_ok = "확인",
        dialog_yes = "예",
        dialog_no = "아니요",
        dialog_confirm_reset = "초기화 확인",
        dialog_confirm_reset_text = "이 모델의 모든 재질 오버라이드를 초기화하시겠습니까?",

        button_save_apply = "저장 및 적용",
        button_reset_this_material = "이 재질 초기화",
        button_only_this = "이것만",
        button_enable_all = "모두 활성화",
        button_disable_all = "모두 비활성화",
        button_reset_all_materials = "모든 재질 초기화",
        button_refresh_imported_model_list = "가져온 모델 목록 새로고침",
        button_clear_client_cache = "클라이언트 메시/재질 캐시 비우기",
        button_edit_materials = "재질 편집...",

        label_include_mesh_when_importing = "가져올 때 이 메시 포함",
        label_bump_map = "범프 맵",
        label_light_warp = "라이트 워프",
        label_self_illum_mask = "자체 발광 마스크",
        label_phong_exponent_tex = "Phong 지수 텍스처",
        label_no_cull = "컬링 없음(양면)",
        label_translucent = "반투명",
        label_alpha_test = "알파 테스트",
        label_alpha_test_reference = "알파 테스트 기준값",
        label_alpha_to_coverage = "Alpha To Coverage",
        label_half_lambert = "Half Lambert",
        label_enable_self_illum = "자체 발광 활성화",
        label_enable_phong = "Phong 활성화",
        label_phong_boost = "Phong 강도",
        label_phong_albedo_tint = "Phong 알베도 틴트",
        label_phong_albedo_boost = "Phong 알베도 부스트",
        label_enable_rim_light = "림 라이트 활성화",
        label_rim_exponent = "림 지수",
        label_rim_boost = "림 부스트",

        panel_description = "garrysmod/data/pmx_static_importer/models 에서 가져온 PMX 모델 목록을 표시한 뒤, 왼쪽 클릭으로 배치합니다。\n오른쪽 클릭은 기존 가져온 엔티티의 모델 ID를 복사합니다. Reload는 하나를 제거합니다.",
        panel_display_name = "표시 이름",
        panel_model_id = "모델 ID",
        panel_triangles = "삼각형 수",
        panel_materials = "재질",
        panel_selected_model_id = "선택된 모델 ID",
        panel_scale = "크기",
        panel_yaw = "요",
        panel_physics_properties = "물리 속성",
        panel_disable_collision = "충돌 비활성화",
        panel_disable_gravity = "중력 비활성화",
        panel_color_modulation = "색상 조절",
        panel_tip_refresh = "팁: 맵이 열린 상태에서 모델을 다시 가져왔다면, 다시 배치하기 전에 새로고침과 캐시 비우기를 사용하세요.",

        chat_no_imported_model_selected = "선택된 가져온 모델이 없습니다.",
        chat_failed_create_entity = "엔티티 생성에 실패했습니다.",
        chat_spawned = "“%s” 생성 완료",
        chat_copied_model_id_and_scale = "선택한 엔티티에서 모델 ID와 크기를 복사했습니다.",
        chat_removed_imported_entity = "가져온 PMX 엔티티를 제거했습니다.",

        error_invalid_model_id = "잘못된 모델 ID입니다.",
        error_manifest_not_found = "매니페스트를 찾을 수 없음: %s",
        error_manifest_parse_failed = "매니페스트 JSON을 해석할 수 없음: %s",
        error_manifest_could_not_be_loaded = "매니페스트를 불러올 수 없습니다.",
        error_could_not_load_manifest_for = "%s 의 매니페스트를 불러올 수 없습니다",
        error_no_materials_found_in_model = "모델에서 재질을 찾을 수 없습니다.",
        error_failed_to_apply_imported_model = "가져온 모델 적용에 실패했습니다.",
        error_could_not_open_mesh_file = "메시 파일을 열 수 없음: %s",
        error_unexpected_mesh_magic = "%s 의 메시 파일 식별자가 올바르지 않습니다",
        error_mesh_submesh_count_mismatch = "%s 의 메시 파일 서브메시 수가 매니페스트와 일치하지 않습니다",

        component_min = "최소",
        component_mid = "중간",
        component_max = "최대",
    },
    ru = {
        category_animation = "Импортёр моделей",
        tool_name = "Импортёр статических моделей",
        tool_desc = "Создаёт импортированные статические PMX-меши из garrysmod/data и garrysmod/materials.",
        tool_help = "Выберите импортированный PMX в панели, затем щёлкните ЛКМ, чтобы разместить его.",
        entity_name = "Импортированный статический объект PMX",

        ui_material_editor = "Редактор материалов",
        ui_material_editor_title = "Редактор материалов — %s",
        ui_materials_count = "Материалы (%d)",
        ui_name = "Имя",
        ui_preview = "Предпросмотр — %s",
        ui_import = "Импорт",
        ui_texture_maps = "Карты текстур",
        ui_rendering = "Рендеринг",
        ui_lighting = "Освещение",
        ui_self_illumination = "Самосвечение",
        ui_self_illum_tint = "Оттенок самосвечения",
        ui_phong_shading = "Затенение Phong",
        ui_phong_fresnel_ranges = "Диапазоны Френеля Phong",
        ui_rim_light = "Контурный свет",
        ui_material_default_name = "Материал %d",
        ui_texture_not_found = "Текстура не найдена: %s",
        ui_no_base_texture = "Базовая текстура отсутствует",
        ui_base_texture = "Базовая текстура: %s",
        ui_none = "(нет)",

        dialog_ok = "OK",
        dialog_yes = "Да",
        dialog_no = "Нет",
        dialog_confirm_reset = "Подтвердите сброс",
        dialog_confirm_reset_text = "Сбросить ВСЕ переопределения материалов для этой модели?",

        button_save_apply = "Сохранить и применить",
        button_reset_this_material = "Сбросить этот материал",
        button_only_this = "Только этот",
        button_enable_all = "Включить всё",
        button_disable_all = "Отключить всё",
        button_reset_all_materials = "Сбросить все материалы",
        button_refresh_imported_model_list = "Обновить список импортированных моделей",
        button_clear_client_cache = "Очистить клиентский кэш мешей/материалов",
        button_edit_materials = "Редактировать материалы...",

        label_include_mesh_when_importing = "Включать этот меш при импорте",
        label_bump_map = "Bump-карта",
        label_light_warp = "Light Warp",
        label_self_illum_mask = "Маска самосвечения",
        label_phong_exponent_tex = "Текстура показателя Phong",
        label_no_cull = "Без отсечения (двусторонний)",
        label_translucent = "Полупрозрачность",
        label_alpha_test = "Alpha test",
        label_alpha_test_reference = "Порог alpha test",
        label_alpha_to_coverage = "Alpha To Coverage",
        label_half_lambert = "Half Lambert",
        label_enable_self_illum = "Включить самосвечение",
        label_enable_phong = "Включить Phong",
        label_phong_boost = "Усиление Phong",
        label_phong_albedo_tint = "Тонирование альбедо Phong",
        label_phong_albedo_boost = "Усиление альбедо Phong",
        label_enable_rim_light = "Включить контурный свет",
        label_rim_exponent = "Показатель контурного света",
        label_rim_boost = "Усиление контурного света",

        panel_description = "Показывает список импортированных PMX-моделей из garrysmod/data/pmx_static_importer/models, после чего их можно размещать ЛКМ.\nПКМ копирует ID модели из уже существующей импортированной сущности. Reload удаляет одну.",
        panel_display_name = "Отображаемое имя",
        panel_model_id = "ID модели",
        panel_triangles = "Треугольники",
        panel_materials = "Материалы",
        panel_selected_model_id = "Выбранный ID модели",
        panel_scale = "Масштаб",
        panel_yaw = "Угол поворота",
        panel_physics_properties = "Физические свойства",
        panel_disable_collision = "Отключить столкновения",
        panel_disable_gravity = "Отключить гравитацию",
        panel_color_modulation = "Цветовая модуляция",
        panel_tip_refresh = "Совет: если вы заново импортировали модель при открытой карте, перед повторным размещением используйте «Обновить» и «Очистить кэш».",

        chat_no_imported_model_selected = "Импортированная модель не выбрана.",
        chat_failed_create_entity = "Не удалось создать сущность.",
        chat_spawned = "Создано: «%s»",
        chat_copied_model_id_and_scale = "ID модели и масштаб скопированы из выбранной сущности.",
        chat_removed_imported_entity = "Импортированная PMX-сущность удалена.",

        error_invalid_model_id = "Некорректный ID модели.",
        error_manifest_not_found = "Манифест не найден: %s",
        error_manifest_parse_failed = "Не удалось разобрать JSON манифеста: %s",
        error_manifest_could_not_be_loaded = "Не удалось загрузить манифест.",
        error_could_not_load_manifest_for = "Не удалось загрузить манифест для: %s",
        error_no_materials_found_in_model = "В модели не найдено материалов.",
        error_failed_to_apply_imported_model = "Не удалось применить импортированную модель.",
        error_could_not_open_mesh_file = "Не удалось открыть файл меша: %s",
        error_unexpected_mesh_magic = "Неожиданная сигнатура файла меша в %s",
        error_mesh_submesh_count_mismatch = "Количество субмешей в файле меша не совпадает с манифестом для %s",

        component_min = "Мин",
        component_mid = "Сер",
        component_max = "Макс",
    },
}

PMXStaticImporter.LanguageAliases = PMXStaticImporter.LanguageAliases or {
    ["en"] = "en",
    ["english"] = "en",
    ["fr"] = "fr",
    ["fr-fr"] = "fr",
    ["french"] = "fr",
    ["ja"] = "ja",
    ["jp"] = "ja",
    ["ja-jp"] = "ja",
    ["japanese"] = "ja",
    ["ko"] = "ko",
    ["ko-kr"] = "ko",
    ["kr"] = "ko",
    ["korean"] = "ko",
    ["ru"] = "ru",
    ["ru-ru"] = "ru",
    ["russian"] = "ru",
    ["zh"] = "zh-CN",
    ["zh-cn"] = "zh-CN",
    ["zh-hans"] = "zh-CN",
    ["schinese"] = "zh-CN",
    ["chinese"] = "zh-CN",
    ["zh-tw"] = "zh-CN",
    ["zh-hant"] = "zh-CN",
    ["tchinese"] = "zh-CN",
}

local function resolve_language(langOrPly)
    local lang = langOrPly

    if type(langOrPly) == "Player" or (IsValid and IsValid(langOrPly) and langOrPly.GetInfo) then
        lang = langOrPly:GetInfo("gmod_language")
    elseif langOrPly == nil and CLIENT then
        local cvar = GetConVar and GetConVar("gmod_language")
        lang = cvar and cvar:GetString() or "en"
    end

    lang = string.lower(tostring(lang or "en"))
    local direct = PMXStaticImporter.LanguageAliases[lang]
    if direct and PMXStaticImporter.Translations[direct] then
        return direct
    end

    local short = lang:match("^([a-z][a-z])")
    if short == "zh" then
        return "zh-CN"
    end
    if short and PMXStaticImporter.Translations[short] then
        return short
    end

    return "en"
end

function PMXStaticImporter.ResolveLanguage(langOrPly)
    return resolve_language(langOrPly)
end

function PMXStaticImporter.T(key, langOrPly)
    local lang = resolve_language(langOrPly)
    local tbl = PMXStaticImporter.Translations[lang] or PMXStaticImporter.Translations.en or {}
    return tbl[key] or PMXStaticImporter.Translations.en[key] or tostring(key)
end

function PMXStaticImporter.TF(key, langOrPly, ...)
    local phrase = PMXStaticImporter.T(key, langOrPly)
    if select("#", ...) <= 0 then return phrase end

    local ok, formatted = pcall(string.format, phrase, ...)
    if ok then
        return formatted
    end
    return phrase
end

function PMXStaticImporter.ToolPrefix(langOrPly)
    return string.format("[%s]", PMXStaticImporter.T("tool_name", langOrPly))
end

if CLIENT then
    function PMXStaticImporter.RegisterLanguagePhrases()
        language.Add("pmx_static_importer.category", PMXStaticImporter.T("category_animation"))
        language.Add("pmx_static_importer.entity_name", PMXStaticImporter.T("entity_name"))
        language.Add("tool.pmx_static_importer.name", PMXStaticImporter.T("tool_name"))
        language.Add("tool.pmx_static_importer.desc", PMXStaticImporter.T("tool_desc"))
        language.Add("tool.pmx_static_importer.0", PMXStaticImporter.T("tool_help"))
    end

    PMXStaticImporter.RegisterLanguagePhrases()

    if cvars and cvars.AddChangeCallback and not PMXStaticImporter._LanguageCallbackInstalled then
        cvars.AddChangeCallback("gmod_language", function()
            timer.Simple(0, function()
                if PMXStaticImporter and PMXStaticImporter.RegisterLanguagePhrases then
                    PMXStaticImporter.RegisterLanguagePhrases()
                end
            end)
        end, "PMXStaticImporterLanguage")
        PMXStaticImporter._LanguageCallbackInstalled = true
    end
end

local function normalize_model_id(raw)
    raw = tostring(raw or "")
    raw = string.lower(raw)
    raw = raw:gsub("\\", "/")
    raw = raw:gsub("^/+", "")
    raw = raw:gsub("/+$", "")
    raw = raw:gsub("[^a-z0-9_%-/]", "")

    if raw == "" then return nil end
    if string.find(raw, "../", 1, true) then return nil end
    if string.find(raw, "..\\", 1, true) then return nil end
    if string.find(raw, "//", 1, true) then return nil end

    return raw
end

function PMXStaticImporter.NormalizeModelID(raw)
    return normalize_model_id(raw)
end

--- Read a file checking DATA first, then workshop-mounted data_static (GAME).
--- @param rel string  path relative to the models root (e.g. "mymodel/manifest.json")
--- @return string|nil content
--- @return string searchPath  "DATA" or "GAME"
function PMXStaticImporter.ReadFileAny(rel)
    if not rel or rel == "" then return nil end
    -- Prefer garrysmod/data/ (user imports)
    local dataPath = PMXStaticImporter.DataRoot .. "/" .. rel
    if file.Exists(dataPath, "DATA") then
        return file.Read(dataPath, "DATA"), "DATA"
    end
    -- Fallback to workshop / addon shipped data_static/
    local gamePath = PMXStaticImporter.GameDataRoot .. "/" .. rel
    if file.Exists(gamePath, "GAME") then
        return file.Read(gamePath, "GAME"), "GAME"
    end
    return nil
end

--- Open a binary file checking DATA first, then workshop-mounted data_static (GAME).
--- @param rel string  path relative to the models root (e.g. "mymodel/mesh.json")
--- @param mode string  file open mode, typically "rb"
--- @return file_class|nil handle
function PMXStaticImporter.OpenFileAny(rel, mode)
    if not rel or rel == "" then return nil end
    mode = mode or "rb"
    -- Prefer garrysmod/data/ (user imports)
    local dataPath = PMXStaticImporter.DataRoot .. "/" .. rel
    if file.Exists(dataPath, "DATA") then
        return file.Open(dataPath, mode, "DATA")
    end
    -- Fallback to workshop / addon shipped data_static/
    local gamePath = PMXStaticImporter.GameDataRoot .. "/" .. rel
    if file.Exists(gamePath, "GAME") then
        return file.Open(gamePath, mode, "GAME")
    end
    return nil
end

function PMXStaticImporter.GetManifestPath(modelID)
    local safeID = normalize_model_id(modelID)
    if not safeID then return nil end
    return PMXStaticImporter.DataRoot .. "/" .. safeID .. "/" .. PMXStaticImporter.ManifestName
end

function PMXStaticImporter.LoadManifest(modelID, langOrPly)
    local safeID = normalize_model_id(modelID)
    if not safeID then
        return nil, PMXStaticImporter.T("error_invalid_model_id", langOrPly)
    end

    local relPath = safeID .. "/" .. PMXStaticImporter.ManifestName
    local raw, searchPath = PMXStaticImporter.ReadFileAny(relPath)
    if not raw then
        local manifestPath = PMXStaticImporter.DataRoot .. "/" .. relPath
        return nil, PMXStaticImporter.TF("error_manifest_not_found", langOrPly, manifestPath)
    end

    local parsed = util.JSONToTable(raw, true, true)
    if not istable(parsed) then
        return nil, PMXStaticImporter.TF("error_manifest_parse_failed", langOrPly, relPath)
    end

    parsed.model_id = normalize_model_id(parsed.model_id or modelID) or modelID
    parsed.mesh_file = tostring(parsed.mesh_file or (PMXStaticImporter.DataRoot .. "/" .. parsed.model_id .. "/mesh.json"))
    parsed.display_name = tostring(parsed.display_name or parsed.model_id)
    parsed.build_id = tostring(parsed.build_id or "")
    parsed._searchPath = searchPath

    return parsed
end

function PMXStaticImporter.GetBoundsFromManifest(manifest)
    if not istable(manifest) or not istable(manifest.bounds) then
        return Vector(-1, -1, -1), Vector(1, 1, 1)
    end

    local minsData = manifest.bounds.mins or {-1, -1, -1}
    local maxsData = manifest.bounds.maxs or {1, 1, 1}

    local mins = Vector(
        tonumber(minsData[1]) or -1,
        tonumber(minsData[2]) or -1,
        tonumber(minsData[3]) or -1
    )

    local maxs = Vector(
        tonumber(maxsData[1]) or 1,
        tonumber(maxsData[2]) or 1,
        tonumber(maxsData[3]) or 1
    )

    return mins, maxs
end

function PMXStaticImporter.ListAvailableModels()
    local seen = {}
    local results = {}

    -- Scan garrysmod/data/ (user imports)
    local _, dataDirs = file.Find(PMXStaticImporter.DataRoot .. "/*", "DATA", "nameasc")
    for _, dirName in ipairs(dataDirs or {}) do
        if not seen[dirName] then
            local manifest = PMXStaticImporter.LoadManifest(dirName)
            if manifest then
                seen[dirName] = true
                results[#results + 1] = {
                    model_id = dirName,
                    display_name = tostring(manifest.display_name or dirName),
                    triangle_count = tonumber(manifest.triangle_count) or 0,
                    material_count = tonumber(manifest.material_count) or #(manifest.submeshes or {}),
                    source_file = tostring(manifest.source_file or ""),
                    build_id = tostring(manifest.build_id or ""),
                }
            end
        end
    end

    -- Scan workshop / addon shipped data_static/ (GAME path)
    local _, gameDirs = file.Find(PMXStaticImporter.GameDataRoot .. "/*", "GAME", "nameasc")
    for _, dirName in ipairs(gameDirs or {}) do
        if not seen[dirName] then
            local manifest = PMXStaticImporter.LoadManifest(dirName)
            if manifest then
                seen[dirName] = true
                results[#results + 1] = {
                    model_id = dirName,
                    display_name = tostring(manifest.display_name or dirName),
                    triangle_count = tonumber(manifest.triangle_count) or 0,
                    material_count = tonumber(manifest.material_count) or #(manifest.submeshes or {}),
                    source_file = tostring(manifest.source_file or ""),
                    build_id = tostring(manifest.build_id or ""),
                }
            end
        end
    end

    table.sort(results, function(a, b)
        local aName = string.lower(a.display_name or a.model_id or "")
        local bName = string.lower(b.display_name or b.model_id or "")
        if aName == bName then
            return (a.model_id or "") < (b.model_id or "")
        end
        return aName < bName
    end)

    return results
end
