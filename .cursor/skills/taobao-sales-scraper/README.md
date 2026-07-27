# 素材台（Taobao Sales Scraper）

淘宝选品 / 素材拉取工具：通过 **万邦 Onebound API** 搜索商品、下载主图 / SKU / 详情图 / 视频，并提供 Web 界面与本地 JSON 素材库。

> 本项目 **不依赖 Chrome / Selenium**，无需登录淘宝账号。  
> 仅用于合规的业务对接与研究；请遵守淘宝与万邦服务条款，控制调用频率。

---

## 功能概览

| 能力 | 说明 |
|------|------|
| 关键词搜索 | 万邦 `item_search`，支持价格区间；发货地 / 发货时间在本地二次筛选 |
| 自然语言意图 | 可选 DeepSeek，把一句话解析成关键词 + 筛选条件 |
| 详情素材 | 万邦 `item_get` / `item_get_pro`，下载并落盘到 `data/product_media/` |
| 素材库 | 本地 `data/library.json`，无需数据库 |
| 桌面绿色包 | Windows 下可打成双击即用的文件夹（见下文） |

---

## 目录结构

```
taobao-sales-scraper/
├── README.md                 # 本文件
├── frontend/                 # React + Vite + TypeScript 界面
├── server/                   # FastAPI 后端
│   ├── app.py                # HTTP API + 静态前端托管
│   ├── desktop_main.py       # 桌面 / 一体化启动入口
│   ├── onebound_client.py    # 万邦 API 客户端
│   ├── search_runner.py      # 搜索编排
│   ├── detail_runner.py      # 详情素材下载
│   ├── intent_parser.py      # 自然语言意图（DeepSeek 可选）
│   ├── store.py              # JSON 本地库
│   ├── .env.example          # 配置模板
│   └── requirements.txt
├── desktop/                  # Windows 打包脚本
│   ├── build.ps1
│   └── sucaitai.spec
├── scripts/                  # 可选离线工具（Excel / 图表，不依赖 Chrome）
└── data/                     # 运行时数据（自动创建，勿提交密钥）
```

---

## 环境要求

- **Python** 3.10+
- **Node.js** 18+（仅前端开发 / 构建需要）
- 万邦 Onebound 账号与 API Key（[open.onebound.cn](https://open.onebound.cn/)）
- 无需安装 Chrome

---

## 快速启动（开发）

### 1. 配置密钥

```bash
cd server
copy .env.example .env
# 编辑 .env，填写：
#   ONEBOUND_API_KEY=...
#   ONEBOUND_API_SECRET=...
# 可选：
#   DEEPSEEK_API_KEY=...
```

### 2. 启动后端

```bash
cd server
pip install -r requirements.txt
python app.py
```

服务默认：`http://127.0.0.1:8787`

健康检查：`GET http://127.0.0.1:8787/api/health` → `{"ok":true}`

### 3. 启动前端

另开终端：

```bash
cd frontend
npm install
npm run dev
```

开发地址一般为 `http://127.0.0.1:5174`，已将 `/api` 代理到 `8787`。

### 一体化启动（后端托管已构建前端）

```bash
cd frontend
npm install
npm run build

cd ../server
python desktop_main.py
```

会启动 `8787` 并自动打开浏览器。此时由 FastAPI 同时提供 API 与静态页面。

---

## 配置说明（`server/.env`）

| 变量 | 必填 | 说明 |
|------|------|------|
| `ONEBOUND_API_KEY` | 是 | 万邦 Key |
| `ONEBOUND_API_SECRET` | 是 | 万邦 Secret |
| `ONEBOUND_API_URL` | 否 | 搜索接口，有默认值 |
| `ONEBOUND_ITEM_GET_URL` | 否 | 详情接口，有默认值 |
| `DEEPSEEK_API_KEY` | 否 | 未配置时，意图解析走本地规则 |

**请勿把含真实密钥的 `.env` 提交到 Git 或发到公开渠道。**

---

## HTTP API（接入系统）

Base URL：`http://127.0.0.1:8787`（或你们部署后的地址）

CORS 已放开，可直接从前端或其它服务调用。

### `GET /api/health`

```json
{ "ok": true }
```

### `POST /api/search`

实时搜索（阻塞；同时只允许一个搜索任务）。

```json
{
  "keyword": "夏季女装",
  "limit": 50,
  "locations": ["广东", "浙江"],
  "ship_time": "24小时内发货",
  "price_min": 50,
  "price_max": 200
}
```

成功时返回 `items`、`count`、`source`（`onebound`）、`message` 等。

### `POST /api/parse-intent`

自然语言 → 搜索条件（可选 DeepSeek）。

```json
{ "text": "帮我找广东发的夏季连衣裙，一百块以内" }
```

### `GET /api/products`

当前会话搜索结果列表（进程内内存；重启后清空）。

### `GET /api/products/{id}`

单条商品。

### `POST /api/products/fetch-detail`

拉取并下载素材到 `data/product_media/{id}/`。

```json
{
  "id": "1234567890",
  "url": "https://item.taobao.com/item.htm?id=1234567890",
  "product": { }
}
```

`product` 为可选前端快照，用于保留标题等字段。

### `GET /api/library` / `POST /api/library`

本地素材库读写。`POST` body：`{ "product": { ... } }`。

### 静态资源

- 媒体文件：`/product_media/...`
- 生产构建后的前端：`/`（需先 `npm run build` 或使用桌面包）

---

## 接入你们系统的建议

1. **当独立微服务**  
   部署 `server/`，业务系统用 HTTP 调 `/api/search`、`/api/products/fetch-detail`。数据目录 `data/` 挂到持久卷。

2. **只复用客户端逻辑**  
   可参考 `server/onebound_client.py`，自行封装万邦调用；注意密钥不要下发到浏览器。

3. **嵌套现有前端**  
   可继续用本仓库 `frontend/`，或按上述 API 自研 UI。开发时把请求代理到本服务即可。

4. **桌面交付给业务同事**  
   使用下方 Windows 打包，对方无需装 Python / Node。

搜索结果默认只存在服务进程内存；入库请走 `/api/library`。素材文件在 `data/product_media/`。

---

## Windows 桌面绿色包

在已配置好 `server/.env` 的机器上：

```powershell
cd desktop
.\build.ps1
```

产出：`desktop/dist/素材台/`（含 `素材台.exe`）。  
将整个文件夹打成 zip 发给使用者，双击 exe 即可；关闭控制台窗口即退出。

构建需要：本机 Python、Node、一次性安装 PyInstaller（脚本会处理依赖）。

---

## 可选离线脚本

`scripts/` 下保留与 Chrome 无关的辅助脚本（如销量可视化、Excel），按需使用；**主流程不依赖它们**。

---

## 常见问题

| 现象 | 处理 |
|------|------|
| 搜索报未配置万邦 | 检查 `server/.env` 中 Key / Secret |
| 端口 8787 被占用 | 关掉占用进程，或改 `app.py` / `desktop_main.py` 中的端口 |
| 发货地筛选结果为空 | API 字段常缺失，可先去掉发货地 / 发货时间再搜 |
| 天猫部分商品素材为空 | 与万邦数据源有关，可换淘宝链接或稍后重试 |

---

## 明确不做

- Chrome 登录 / Selenium 爬取  
- 数据库（当前为 JSON 文件）  
- 未授权的高频抓取  

---

## License / 使用注意

请确保你们具备万邦 API 的合法使用权，并遵守平台规则。本仓库代码按内部协作交付使用。
