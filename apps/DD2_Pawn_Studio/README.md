# 追随者工作台 / Pawn Studio

独立的 Python 桌面界面，用于编辑 **The Pawn Controller 2.2.0** 的配置。

- 不修改原作者的 `ThePawnController.lua`
- 不直接编辑 `.bin` 存档
- 直接读写 `reframework/data/ThePawnController/config.json`
- 保存配置后，重新启动游戏，由原版 Lua MOD 应用设置

## 启动

双击 `启动追随者工作台.bat`，或运行：

```powershell
python pawn_studio.py
```

默认配置路径：

```text
<Dragons Dogma 2 install>\reframework\data\ThePawnController\config.json
```

默认按 Steam 常见安装目录查找；如果游戏装在别处，设置环境变量
`DD2_GAME_DIR` 指向游戏根目录即可。

## 功能

- 主追随者和两名雇佣追随者独立编辑
- 姓名、职业、职业等级、角色等级
- 6 个武器技能、7 个被动技能、核心技能
- 装备、强化、龙铸和装备特殊技能 ID
- 装备资料库：基础数值、物品等级、职业限制
- 当前装备详情：强化等级、特殊技能 ID、鉴定词条和修正
- 性格、专长、语音、说话频率
- 知识和追随者 QoL
- 全局设置、玩家 QoL、诊断日志
- 预设保存、载入和删除
- 人物档案按区段导入
- 完整追随者配置导入/导出
- 原始 JSON 高级编辑
- 保存前自动备份到 `backups`

## 游戏数据目录

如果技能、性格、语音下拉框只显示“当前值”，可把 `export_catalog.lua`
临时放入：

```text
<Dragons Dogma 2 install>\reframework\autorun
```

重新启动游戏一次。脚本会生成：

```text
reframework\data\ThePawnController\pawn_studio_catalog.json
```

生成后即可从 `autorun` 移走 `export_catalog.lua`。它不会修改原版 MOD。

## 使用顺序

1. 关闭游戏。
2. 打开本程序，选择或确认 `config.json`。
3. 完成修改并点击“保存 / Save”。
4. 启动游戏。
5. 关闭并重新进入游戏后，原版 MOD 会把保存的覆盖设置应用到追随者。

修改主追随者后，建议继续使用原版 MOD 的 **Validate Pawn** 做一次在线校验。

## 限制 / Limitations

Python 版本是离线配置编辑器。以下依赖游戏运行内存的操作仍需使用原版 MOD 的游戏内 UI：

- 实时治疗、传送、杀死追随者
- 立即感染或即时清除龙瘟
- 在线追随者上传验证
- 实时切换装备后的即时视觉反馈

The Python app edits the original MOD configuration and leaves the Lua MOD
untouched. Live memory actions remain available in the in-game MOD UI.
