# 弧梦数字中枢 · 星云中枢（大肥鱼版）

ArcDream Hub 0.1.2 的自用版本。程序本体取自公开的 v0.1.2 发布包，**页面里的数据已全部换成本机真实数据**，不含原作者的任何示例。

## 目录

- `app/` 中枢服务本体（Node 零依赖，`node:sqlite`）
  - `server.mjs` 服务端，默认 `127.0.0.1:8799`
  - `public/index.html` 星图页面（数据段已替换为本机真实数据：10 星团 / 42 节点 / 42 连边）
  - `启动.cmd` Windows 双击启动
  - `data-dir.txt` 数据目录指针
- `plugin/dsh-arc-hub/` DSH 插件（link 安装用），提供 `arc_hub_status / arc_hub_persona / arc_hub_mode / arc_hub_open_dir`
- `data-snapshot/` 数据快照（**不含任何 API Key**）
  - `memory/` 记忆库（`记忆库.jsonl` / `记忆库.md`）与三个素材脚本
  - `日记/` 2026-11-16 起的日记、写作守则、索引
  - `hub/config.json` 模式与工作区列表、`workspace-dirs.txt`

## 跑起来

```bash
node app/server.mjs
# 打开 http://127.0.0.1:8799
```

数据目录默认取 `app/data-dir.txt`，可用环境变量 `ARC_HUB_DATA` 覆盖，端口用 `ARC_HUB_PORT`。

模型配置要自己建 `model.json`（本仓库不含）：`{ "provider": "deepseek", "baseUrl": "https://api.deepseek.com/v1", "model": "deepseek-chat" }`，Key 通过页面填写。

## 星图数据

页面里的星图是静态数据段（`let uid = 0;` 到 `const S = {` 之间）：10 个星团、42 个节点、42 条连边，全部来自本机工作区扫描与记忆库，顶栏统计为 3,827 文件 / 137 条记忆 / 1 篇日记 / 1.18 GB。点顶栏「文件索引」可切到服务端从 SQLite 索引实时生成的图。

## 许可

程序本体沿用 ArcDream Hub 原许可；页面数据与 `data-snapshot/` 为本人自用内容。
