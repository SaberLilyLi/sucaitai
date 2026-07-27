---
name: taobao-sales-scraper
description: >-
  Taobao product search and media download via Onebound API, with a React UI
  and optional Windows desktop package. Use when integrating or running 素材台.
---

# Taobao Sales Scraper（素材台）

自包含项目：FastAPI + React，数据源为 **万邦 Onebound**（无 Chrome / Selenium）。

> 仅用于合规业务对接与学习研究。遵守淘宝与万邦服务条款。

完整说明见包内 **[README.md](./README.md)**。

## 布局

```
taobao-sales-scraper/
├── README.md
├── frontend/
├── server/
├── desktop/          # Windows 绿色包构建
├── scripts/          # 可选离线工具
└── data/             # 运行时（gitignore）
```

## 开发启动

```bash
cd server
copy .env.example .env   # 填写 ONEBOUND_API_KEY / SECRET
pip install -r requirements.txt
python app.py
```

```bash
cd frontend
npm install
npm run dev
```

## 桌面打包

```powershell
cd desktop
.\build.ps1
```

## 注意

- 不要提交 `server/.env` 或含 Cookie 的个人数据
- 已移除 Chrome 登录抓取路径；勿再依赖 `chromedriver` / `.chrome-profile`
