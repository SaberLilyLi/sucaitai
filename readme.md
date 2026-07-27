# 素材台

面向电商选品与素材归档的本地工具。通过万邦 Onebound API 搜索淘宝、1688 商品，按条件筛选，拉取商品素材并保存到本地素材库；支持导出到腾讯文档和 Windows 绿色版交付。

> 本项目不使用 Chrome 登录或 Selenium 抓取。请确保具备 Onebound API 的合法使用权，并遵守相关平台和数据服务的使用条款。

## 核心能力

- 淘宝与 1688 商品关键词搜索
- 价格、发货地、发货时效筛选
- 自然语言选品需求解析（配置 DeepSeek 后可用；未配置时使用本地规则）
- 拉取并按商品归档主图、SKU 图、详情图和视频
- 本地 JSON 素材库：支持项目、标签与备注，无需额外数据库
- 勾选 2–4 个商品横向对比价格、销量、发货、素材和归档信息
- 将已拉取素材按商品批量打包为 ZIP 下载
- 导出选中商品至腾讯文档在线表格
- 打包为 Windows 双击即用的绿色文件夹

## 项目结构

```text
.
├── .cursor/skills/taobao-sales-scraper/  # 主应用源码
│   ├── frontend/                         # React + Vite + TypeScript 前端
│   ├── server/                           # FastAPI 服务与数据处理
│   ├── desktop/                          # Windows 打包脚本
│   ├── scripts/                          # 离线分析辅助脚本
│   └── data/                             # 本地运行时数据（不提交）
├── docs/                                 # 设计与打包文档
└── taobao_scraper.py                     # 兼容旧入口，转发至应用脚本
```

## 开发环境

- Python 3.10+
- Node.js 18+（前端开发或构建时需要）
- Onebound API Key 与 Secret

## 快速启动

### 1. 配置环境变量

```powershell
cd .cursor/skills/taobao-sales-scraper/server
Copy-Item .env.example .env
```

编辑 `.env`，填写以下配置：

```env
ONEBOUND_API_KEY=你的_API_Key
ONEBOUND_API_SECRET=你的_API_Secret
```

`DEEPSEEK_API_KEY` 为可选项，用于更准确地解析自然语言搜索需求。

### 2. 启动后端

```powershell
cd .cursor/skills/taobao-sales-scraper/server
pip install -r requirements.txt
python app.py
```

服务默认地址为 `http://127.0.0.1:8787`，健康检查接口为 `GET /api/health`。

### 3. 启动前端（开发模式）

另开一个终端：

```powershell
cd .cursor/skills/taobao-sales-scraper/frontend
npm install
npm run dev
```

开发服务器通常运行在 `http://127.0.0.1:5174`，并已代理 `/api` 请求至后端。

### 4. 一体化运行

先构建前端，再由 FastAPI 同时托管页面与 API：

```powershell
cd .cursor/skills/taobao-sales-scraper/frontend
npm install
npm run build

cd ../server
python desktop_main.py
```

## 工作流程

1. 输入关键词或一句自然语言选品需求。
2. 选择淘宝或 1688，并设置价格、发货地、发货时效等条件。
3. 从搜索结果中挑选商品并查看详情。
4. 拉取主图、SKU 图、详情图、视频等素材；文件保存于 `data/product_media/`。
5. 将有价值的商品加入本地素材库，或导出选中项到腾讯文档。

## Windows 绿色版打包

在已配置 `server/.env` 的开发机执行：

```powershell
cd .cursor/skills/taobao-sales-scraper/desktop
.\build.ps1
```

产物位于 `desktop/dist/素材台/`。将整个文件夹压缩后交付，使用者双击 `素材台.exe` 即可启动。

请勿打包或提交以下本地文件：

- `server/.env` 中的真实 API 密钥
- `.chrome-profile/` 等个人浏览器数据
- `data/` 中的客户素材和本地库

## API 摘要

| 接口 | 用途 |
| --- | --- |
| `GET /api/health` | 健康检查 |
| `POST /api/search` | 搜索淘宝或 1688 商品 |
| `POST /api/parse-intent` | 解析自然语言搜索条件 |
| `POST /api/products/fetch-detail` | 拉取并保存商品素材 |
| `POST /api/products/export-media` | 将选中商品的本地素材打包为 ZIP |
| `GET` / `POST /api/library` | 查询或保存本地素材库 |
| `POST /api/tencent-docs/export` | 导出商品至腾讯文档 |

完整接口说明和实现位置见 [.cursor/skills/taobao-sales-scraper/README.md](.cursor/skills/taobao-sales-scraper/README.md)。

## 数据与合规

搜索结果仅保存在当前服务会话中；加入素材库后会写入本地 `data/library.json`。商品素材会下载到 `data/product_media/`。

请合理控制 API 调用频率，确保数据使用、导出和分发符合 Onebound 及相关平台的服务条款与法律法规。
