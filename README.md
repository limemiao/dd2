# Dragon’s Dogma 2 工具集

面向《龙之信条 2》的本地图鉴和随从配置工具。可以单独浏览装备与技能，也可以通过两个编辑器管理 The Pawn Controller 的配置与预设。

## 查看图鉴

浏览器打开以下任一页面，图标、JSON 和 CSV 数据位于相邻目录。

- [综合图鉴](catalogs/dd2_compendium/index.html)
- [装备图鉴](catalogs/dd2_equipment_catalog/index.html)
- [技能图鉴](catalogs/dd2_skill_catalog/index.html)

## 编辑随从配置

需要 Windows、Python 3 和已安装的 The Pawn Controller。先退出游戏，并在 PowerShell 中将 `DD2_GAME_DIR` 设为包含 `DD2.exe` 的安装目录。

```powershell
$env:DD2_GAME_DIR = 'C:\Games\Dragons Dogma 2'
python apps\dd2_character_manager\app.py
```

浏览器访问 <http://127.0.0.1:8791>。管理器支持查看当前随从、导入预设、按区块应用配置，以及恢复暂时删除的预设。写入时会在 `game_config_backups/` 留下备份。

需要直接编辑完整配置时，可以打开 Pawn Studio，系统 Python 需要 Tkinter。

```powershell
python apps\DD2_Pawn_Studio\pawn_studio.py
```

也可以在窗口内选择配置文件。两套工具都以 `reframework/data/ThePawnController/config.json` 为主要输入，保存后由游戏里的 MOD 应用设定。更多细节见 [角色管理器](apps/dd2_character_manager/README.md) 和 [Pawn Studio](apps/DD2_Pawn_Studio/README.md)。

## 目录与工具

| 路径 | 内容 |
| --- | --- |
| `apps/` | 本地 Web 角色管理器、Tkinter 桌面编辑器 |
| `catalogs/` | 装备、技能、综合图鉴及关联数据 |
| `mods/`、`mod_configs/` | REFramework 模组与配置样例 |
| `research/` | 随从 AI、控制器研究和实验源码 |
| `tools/`、`tests/` | 图鉴生成工具与图标映射回归测试 |

图鉴生成需要相应的本地游戏资源与 Pillow。查看生成参数和运行图标测试：

```powershell
python -m pip install Pillow
python tools\build_dd2_equipment_catalog.py --help
python -m unittest discover -s tests -v
```

角色管理器的 `selftest.py` 需要通过 `DD2_GAME_DIR` 找到真实 MOD 配置，并在临时副本上测试。原有预设如位于旧的根目录 `dd2_character_manager/profiles/`，可迁入 `apps/dd2_character_manager/profiles/`。

这是非官方项目。游戏内容和图标归原权利人，第三方 MOD 源码遵循其各自的许可条款。
