# 龙之信条 2 角色配置管理器

本页面用于管理《龙之信条 2》随从的完整配置：

- 查看当前三名随从的实际生效配置。
- 展开查看完整的体型、面部、造型 ID、颜色等外观参数和原始外观 JSON。
- 从当前随从创建完整角色配置。
- 导入角色 JSON、编辑配置、复制配置和删除配置。
- 将配置按身份、外观、声音、职业技能、装备、行为等区块应用到一名或多名随从。
- 应用前自动备份整份 `ThePawnController/config.json`。
- 删除的配置会移动到 `trash/`，不会直接永久删除。

## 启动

```powershell
python apps\dd2_character_manager\app.py
```

然后打开：

```text
http://127.0.0.1:8791/
```

应用配置时必须关闭 `DD2.exe`。页面只监听本机回环地址，不会向局域网开放。

## 文件

- `app.py`：本地 HTTP 服务、配置读写和备份。
- `index.html`：管理页面。
- `profiles/`：保存的完整角色配置（首次保存时自动创建）。
- `trash/`：删除配置后的可恢复文件（首次删除时自动创建）。

游戏配置路径：

```text
<Dragons Dogma 2 install>\reframework\data\ThePawnController\config.json
```

默认按 Steam 常见安装目录查找；如果游戏装在别处，设置环境变量
`DD2_GAME_DIR` 指向游戏根目录即可。
