# Windows 绿色桌面包设计

日期：2026-07-25  
状态：待用户审阅  
范围：将「素材台」（taobao-sales-scraper 前端 + FastAPI）打成 Windows 可双击使用的绿色文件夹

## 1. 目标

客户拿到一个文件夹，**双击 `素材台.exe` 即可使用**，无需安装 Python、Node、Chrome，也无需自行配置环境变量。

## 2. 已确认约束

| 项 | 决定 |
|---|---|
| 平台 | 仅 Windows |
| 数据源 | 仅万邦 Onebound API（不打包 Selenium / Chrome） |
| 交付形态 | 绿色文件夹（非安装包、非单文件超大 exe） |
| UI 承载 | 系统默认浏览器打开本地页面（方案 1） |

## 3. 客户体验

1. 解压收到的 zip / 文件夹  
2. 双击 `素材台.exe`  
3. 控制台短暂出现；自动打开浏览器访问 `http://127.0.0.1:8787`  
4. 正常使用搜索、详情素材、本地库  
5. 关闭控制台窗口即停止后台服务  

## 4. 分发目录

```
素材台/
├── 素材台.exe          # 入口
├── _internal/          # PyInstaller 运行时与依赖（勿删）
├── data/               # 本地数据（library、product_media 等；可空）
├── .env                # 预置万邦凭据与 SEARCH/DETAIL=onebound
└── 使用说明.txt
```

**不要打进包：** `.chrome-profile/`、开发用 `node_modules/`、源码仓库的个人 Cookie、未脱敏密钥样例以外的调试产物。

## 5. 运行时架构

```
素材台.exe
  ├─ 解析可执行文件旁路径（工作目录 / data / .env）
  ├─ 固定环境：SEARCH_PROVIDER=onebound, DETAIL_PROVIDER=onebound
  ├─ 加载旁路 .env（ONEBOUND_API_KEY / SECRET 等）
  ├─ 启动 uvicorn：127.0.0.1:8787
  │     FastAPI
  │       /api/*          → 现有业务接口
  │       /product_media  → data/product_media
  │       /*              → 内置前端静态资源（SPA fallback）
  └─ webbrowser.open("http://127.0.0.1:8787")
```

前端生产构建后 API 仍用相对路径 `/api`（现有 `client.ts` 已满足），无需改代理。

## 6. 代码改动要点

### 6.1 后端可打包入口

新增（或扩展）启动模块，例如 `server/desktop_main.py`：

- 兼容 `sys.frozen`（PyInstaller）：资源根目录为 exe 所在目录  
- 未冻结时：行为与开发一致（Skill 包内路径）  
- `DATA_DIR` / `.env` 解析改为「exe 旁优先」，保证客户数据与配置可写、可备份  
- 挂载前端 `dist`（打包进 `_internal` 或作为数据文件），对非 API 路由做 SPA `index.html` 回退  
- 启动后打开浏览器；端口占用时给出明确中文提示  

### 6.2 路径与 store

`store.DATA_DIR`（及 onebound / intent 的 `ENV_PATH`）在桌面模式下指向 **exe 同级 `data/` 与 `.env`**，避免写到只读的 `_internal`。

### 6.3 前端构建

- `vite build` 产出静态文件  
- `base: '/'`（由本机同端口托管即可）  
- 不依赖 Vite 开发代理  

### 6.4 剔除 Selenium 路径（分发配置层）

- 分发 `.env` 强制 `SEARCH_PROVIDER=onebound`、`DETAIL_PROVIDER=onebound`  
- PyInstaller 可不收集 `selenium`、不打包 `chromedriver.exe`（减小体积；开发环境仍可保留 selenium 依赖供调试）  
- 若未配置万邦 Key：API 返回清晰错误，引导检查 `.env`（客户侧通常已预置）

### 6.5 构建流水线

新增脚本（建议 PowerShell）：`scripts/build_windows_desktop.ps1`（或 Skill 包内 `desktop/build.ps1`）：

1. `frontend`: `npm ci` + `npm run build`  
2. 将 `frontend/dist` 拷到打包资源目录  
3. 准备旁路 `.env` 模板（构建机注入真实 Key，**产物 .env 不提交 git**）  
4. PyInstaller onedir：`--name 素材台`，入口 `desktop_main`  
5. 复制 `使用说明.txt`、空 `data/`  
6. 输出目录：`dist/素材台/`，再可选 zip  

开发者本机需：Python 3.10+、Node 18+、一次性安装 PyInstaller。

## 7. 密钥与安全

- 客户包内 `.env` 含万邦 Key：由你方在**构建/发货前**写入，不进入公开 git  
- 文档提醒：Key 泄露风险由发货方控制；勿把客户包回传到公开仓库  
- DeepSeek Key 可选；未配置时意图解析走本地规则（与现网一致）

## 8. 验收标准

- [ ] 干净 Windows 机器（无 Python/Node）解压后双击可打开界面  
- [ ] 搜索、拉详情、入库在仅万邦模式下可用  
- [ ] 关闭控制台后服务停止，再次双击可重启  
- [ ] `data/` 中素材与库文件可在重启后保留（库）/ 符合现有会话语义（搜索）  
- [ ] 端口 8787 被占用时有可读提示，不静默失败  

## 9. 非目标

- macOS / Linux 包  
- Electron / 安装向导 / 开机自启  
- 打包 Chrome 或 Selenium 回退  
- 自动更新  

## 10. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 杀软误报 PyInstaller | onedir 分发；必要时加说明或签名（后续可选） |
| 端口占用 | 检测 8787，失败时提示并退出 |
| Key 写进包 | 仅私发客户；构建脚本从本机私密 env 注入 |
| WebView 无独立窗 | 已接受：用系统浏览器 |

## 11. 实现落点（文件级预览）

| 路径 | 作用 |
|---|---|
| `server/desktop_main.py` | 冻结入口：路径、静态托管、开浏览器、起 uvicorn |
| `server/store.py` 等 | 桌面模式下 DATA/ENV 锚定 exe 目录 |
| `server/app.py` | 挂载前端静态 + SPA fallback（或由 desktop_main 组装） |
| `desktop/素材台.spec` 或 pyinstaller 参数 | onedir 打包配置 |
| `desktop/build.ps1` | 一键构建 |
| `desktop/使用说明.txt` | 客户说明 |
| 本设计文档 | 规格来源 |
