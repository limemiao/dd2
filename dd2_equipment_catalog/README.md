# 龙之信条 2 装备图鉴

本目录由游戏 PAK 数据直接生成，不包含生成式图片。

## 文件

- `index.html`：可搜索，并可按职业、武器／防具和装备部位筛选的离线图鉴。
- `catalog.csv`：可用 Excel 打开的表格，含名称、职业、数值和说明。
- `catalog.json`：完整结构化数据。
- `icons/`：直接从游戏 UI 图集裁剪的逐件图标。
- `preview.png`：图鉴首页预览图。
- `summary.json`：生成统计。

## 数据口径

- 数据源：`itemweapondata`、`exitemweapondata`、`itemarmordata`、`exitemarmordata`。
- 名称和说明：`itemname`、`itemdetail` 及其扩展资料 `appraisalitemname_tu_end`、`appraisalitemdetail_tu_end`。
- 图标：`natives/stm/gui/ui01/common/item/c00` 和 `c01` 的 `iam` 图集。
- 职业：解析装备记录中的 `_Job` 位掩码。显示“龙选者”表示该装备可被龙选者使用。
- 职业筛选会显示该职业实际可装备的物品；“全职业”装备也会计入任意职业的结果。
- 武器类型按 `_WeaponName` 模型前缀识别，避免扩展装备编号造成类型误判。
- 数值：保存游戏原始字段，不在工具内套用强化等级或角色面板修正。

## 图标映射

- `12000–14999` 段图标编号在游戏截图中使用前一个 UI 图集序号，例如 `13084` 对应文件
  `tex_ui01c00_12_iam.png` 的第 84 格。
- 名称相同但图标编号在源数据中为 `0` 的变体，会复用同名装备的原图标；`0` 不会被误当成第 0 图集第 0 格。
- 当前 1091 件装备均使用游戏 UI 图集原图。
