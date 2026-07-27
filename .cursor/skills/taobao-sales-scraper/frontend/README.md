# 素材台 Frontend

React + Vite + TypeScript 管理端。

## 启动

```bash
cd .cursor/skills/taobao-sales-scraper/frontend
npm install
npm run dev
```

浏览器打开 http://localhost:5174

## 目录

```
src/
  components/   Layout, ProductTable, ImageGallery
  pages/        ProductListPage, ProductDetailPage
  context/      Toast
  api/          对接 FastAPI
  lib/          library.ts（localStorage，后续改 library.json API）
  types/
```

列表数据来自后端 `/api/products`，无内置 mock。
