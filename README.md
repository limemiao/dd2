# Dragon's Dogma 2 Project

《龙之信条 2》随从配置、装备/技能图鉴、Pawn Studio 和 REFramework MOD 源码的
工作区。

## 功能

- **角色配置管理器**：本地 Web 界面，查看和编辑随从的体型、面部、造型、声音、
  职业、技能、装备、行为，支持角色档案导入/导出与整份配置备份。
- **装备图鉴**：基础数值、物品等级、职业限制、强化和特殊技能 ID，带图标搜索。
- **技能图鉴**：技能 ID、职业、学习条件、描述，带图标搜索。
- **合并图鉴**：装备与技能放在同一个可搜索页面。
- **Pawn Studio**：独立桌面编辑器，直接读写 The Pawn Controller 的 `config.json`。
- **MOD 源码**：The Pawn Controller 的开发版本与 MorePawnsV4 的 Lua 源码。
- **游戏数据提取**：随从 AI 决策包、目录数据和装备图标的整理脚本。

## 环境要求

- Windows 10 / 11。
- Python 3.10 或更高版本。
- 角色管理器只用标准库；Pawn Studio 需要 `Pillow`，并使用 Tkinter。
- 运行时需要《龙之信条 2》、REFramework 和 The Pawn Controller MOD。
- 图鉴 HTML 可直接用浏览器打开，不需要安装额外依赖。

```powershell
python -m pip install pillow
```

## 使用

### 角色配置管理器

```powershell
python dd2_character_manager\app.py
```

浏览器打开 <http://127.0.0.1:8791/>。应用配置前请关闭 `DD2.exe`；服务只监听
本机回环地址。首次创建或删除档案时会自动生成 `profiles/` 和 `trash/`。

### Pawn Studio

```powershell
python DD2_Pawn_Studio\pawn_studio.py
```

也可以双击 `DD2_Pawn_Studio\启动追随者工作台.bat`。程序会直接读写
`reframework/data/ThePawnController/config.json`，保存前自动备份到 `backups/`。

### 图鉴

直接打开以下文件，或由任意静态服务器托管：

- `dd2_equipment_catalog/index.html`
- `dd2_skill_catalog/index.html`
- `dd2_compendium/index.html`

## 目录结构

```text
dd2/
├─ dd2_character_manager/   # 角色配置管理器（app.py + index.html）
├─ DD2_Pawn_Studio/          # 桌面端随从编辑器
├─ dd2_equipment_catalog/    # 装备数据、图标与搜索页
├─ dd2_skill_catalog/        # 技能数据与搜索页
├─ dd2_compendium/           # 装备 + 技能合并图鉴
├─ analysis_ai/              # 提取的随从 AI / 目录数据
├─ Modding/                  # The Pawn Controller 开发文件（Lua）
├─ mods/MorePawnsV4/         # MorePawnsV4 MOD 源码
├─ mod_configs/              # MOD 配置示例
├─ tools/                    # 图鉴构建与资源解析脚本
├─ research/                 # 研究笔记
├─ tests/                    # 回归测试
└─ README.md
```

`tools/` 中保留了图鉴构建所需的三个不依赖游戏本体的脚本：

- `build_dd2_equipment_catalog.py`
- `ree_msg_dump.py`
- `ree_user_rsz_dump.py`

## 游戏数据说明

仓库不包含游戏本体、存档、个人角色档案、配置备份或提取出的原始资源。运行时请使用
自己的游戏安装目录和 `reframework/data/ThePawnController/config.json`。

默认按 Steam 常见安装目录查找配置；如果游戏装在别处，设置环境变量
`DD2_GAME_DIR` 指向游戏根目录：

```powershell
$env:DD2_GAME_DIR = "D:\SteamLibrary\steamapps\common\Dragons Dogma 2"
```

图鉴中的装备/技能图标和数值来自《龙之信条 2》，版权归 Capcom 所有，仅用于本地
图鉴、Mod 开发和研究。The Pawn Controller 原 MOD 的版权归其作者所有。

## 测试

```powershell
# 图标映射测试，自带数据，可直接运行
python tests\test_dd2_icon_mapping.py -v

# 角色管理器端到端自测；需要本机已有 ThePawnController/config.json
python dd2_character_manager\selftest.py
```

## 许可

本仓库未附带开源许可证。游戏素材和第三方 MOD 的使用请遵守各自条款。
