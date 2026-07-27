# -*- coding: utf-8 -*-
"""素材台 API：淘宝实时搜索 + JSON 本地库。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from detail_runner import fetch_product_media
from intent_parser import parse_search_intent
from runtime_paths import frontend_dist
from search_runner import run_taobao_search
from store import (
    DATA_DIR,
    library_ids,
    load_library,
    load_products,
    save_to_library,
)
from tencent_docs_client import create_and_fill_spreadsheet, create_spreadsheet

app = FastAPI(title="素材台 API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

media_dir = DATA_DIR / "product_media"
media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/product_media", StaticFiles(directory=str(media_dir)), name="product_media")


class SearchBody(BaseModel):
    keyword: str = Field(..., min_length=1, description="淘宝搜索关键词")
    limit: int = Field(100, ge=1, le=132, description="拉取条数，默认 100")
    pages: int | None = Field(None, ge=1, le=5, description="可选：指定翻页数；不传则按 limit 自动计算")
    platform: str | None = Field(
        "taobao", description="平台：taobao | 1688"
    )
    location: str | list[str] | None = Field(
        None, description="发货地，支持单个字符串、逗号分隔或多选数组"
    )
    locations: list[str] | None = Field(None, description="发货地多选，如：[\"浙江\",\"广东\"]")
    ship_time: str | None = Field(None, description="发货时间，如：24小时内发货、次日达")
    price_min: float | None = Field(None, ge=0, description="价格下限")
    price_max: float | None = Field(None, ge=0, description="价格上限")


class SaveBody(BaseModel):
    product: dict[str, Any]


class TencentDocsExportBody(BaseModel):
    ids: list[str] = Field(..., min_length=1, description="需要导出的商品 ID")


class MediaExportBody(BaseModel):
    ids: list[str] = Field(..., min_length=1, description="需要打包素材的商品 ID")


class DetailFetchBody(BaseModel):
    id: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    # 前端当前行快照：搜索仅会话内存，重启后可能丢；用此保留标题等字段
    product: dict[str, Any] | None = None
    platform: str | None = Field(None, description="平台：taobao | 1688")


class IntentBody(BaseModel):
    text: str = Field(..., min_length=1, description="自然语言选品描述")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/tencent-docs/test")
def test_tencent_docs_connection():
    """Create one harmless spreadsheet to verify local Tencent Docs credentials."""
    try:
        result = create_spreadsheet("淘宝素材台 - 腾讯文档连接测试")
        data = result.get("data") or {}
        return {
            "ok": True,
            "message": "连接成功，已创建测试在线表格。",
            "file": {
                "id": data.get("ID") or data.get("id"),
                "title": data.get("title"),
                "url": data.get("url"),
                "type": data.get("type"),
            },
        }
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/api/tencent-docs/export")
def export_to_tencent_docs(body: TencentDocsExportBody):
    products_by_id = {str(product.get("id")): product for product in load_products()}
    selected = [products_by_id[product_id] for product_id in body.ids if product_id in products_by_id]
    if not selected:
        raise HTTPException(status_code=404, detail="选中的商品已失效，请重新搜索后再导出。")

    from datetime import datetime

    rows = [["商品ID", "商品标题", "价格", "销量", "发货地", "发货时间", "商品链接", "主图链接"]]
    for product in selected:
        rows.append([
            str(product.get("id") or ""),
            str(product.get("title") or ""),
            str(product.get("price") or ""),
            str(product.get("total_sales") or 0),
            str(product.get("location") or ""),
            str(product.get("ship_time") or ""),
            str(product.get("url") or ""),
            str(product.get("cover") or ""),
        ])
    try:
        result = create_and_fill_spreadsheet(
            f"淘宝选品 - {datetime.now():%Y%m%d-%H%M%S}", rows
        )
        return {"ok": True, "message": f"已同步 {result['rows']} 个商品。", "file": result}
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/api/products/export-media")
def export_product_media(body: MediaExportBody):
    """把已下载的本地素材按商品打成一个 ZIP，供运营/设计批量交付。"""
    from datetime import datetime
    import json
    import re
    import zipfile

    products = {str(p.get("id")): p for p in load_products()}
    products.update({str(p.get("id")): p for p in load_library() if p.get("id")})
    selected = [products[item_id] for item_id in body.ids if item_id in products]
    if not selected:
        raise HTTPException(status_code=404, detail="选中的商品已失效，请重新搜索后再试。")

    exports_dir = DATA_DIR / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive = exports_dir / f"素材台-批量素材-{stamp}.zip"
    manifest: list[dict[str, Any]] = []
    file_count = 0
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for product in selected:
            product_id = str(product.get("id") or "")
            source_dir = media_dir / product_id
            if not source_dir.is_dir():
                continue
            title = re.sub(r'[\\/:*?"<>|]', "_", str(product.get("title") or "商品"))[:40]
            folder = f"{product_id}_{title}" if title else product_id
            count = 0
            for file in source_dir.rglob("*"):
                if file.is_file():
                    zf.write(file, arcname=str(Path(folder) / file.relative_to(source_dir)))
                    count += 1
                    file_count += 1
            if count:
                manifest.append(
                    {
                        "id": product_id,
                        "title": product.get("title") or "",
                        "url": product.get("url") or "",
                        "project": product.get("project") or "",
                        "tags": product.get("tags") or [],
                        "files": count,
                    }
                )
        if manifest:
            zf.writestr("素材清单.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    if not file_count:
        archive.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="所选商品没有已拉取的本地素材，请先拉取详情素材。")
    return FileResponse(
        archive,
        media_type="application/zip",
        filename=archive.name,
        headers={"X-Exported-Products": str(len(manifest))},
    )


@app.post("/api/parse-intent")
def parse_intent(body: IntentBody):
    """把一段话解析成关键词标签 + 搜索条件（优先 DeepSeek）。"""
    result = parse_search_intent(body.text)
    if not result.get("keyword"):
        raise HTTPException(status_code=400, detail=result.get("message") or "未能识别关键词")
    return result


@app.get("/api/products")
def get_products():
    items = load_products()
    return {"count": len(items), "items": items, "libraryIds": library_ids()}


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    items = load_products()
    for p in items:
        if p.get("id") == product_id:
            return {"product": p}
    raise HTTPException(status_code=404, detail="商品不存在")


@app.post("/api/products/fetch-detail")
def fetch_detail(body: DetailFetchBody):
    """拉取商品素材（万邦 item_get）。"""
    try:
        result = fetch_product_media(
            body.id,
            body.url,
            base_product=body.product,
            platform=body.platform,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"详情拉取失败: {e}") from e


@app.post("/api/search")
def search(body: SearchBody):
    """实时搜索（万邦 Onebound：taobao / 1688）。"""
    try:
        result = run_taobao_search(
            body.keyword,
            body.pages,
            limit=body.limit,
            location=body.location,
            locations=body.locations,
            ship_time=body.ship_time,
            price_min=body.price_min,
            price_max=body.price_max,
            platform=body.platform,
        )
        result["libraryIds"] = library_ids()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {e}") from e


@app.get("/api/library")
def get_library():
    items = load_library()
    return {"count": len(items), "items": items}


@app.post("/api/library")
def post_library(body: SaveBody):
    if not body.product:
        raise HTTPException(status_code=400, detail="缺少 product")
    items = save_to_library(body.product)
    product_id = body.product.get("id")
    saved_product = next((x for x in items if x.get("id") == product_id), body.product)
    return {
        "count": len(items),
        "items": items,
        "product": saved_product,
        "libraryIds": [x.get("id") for x in items if x.get("id")],
    }


def _mount_frontend() -> None:
    """生产/桌面包：托管 Vite dist；开发无 dist 时跳过。"""
    dist = frontend_dist()
    index = dist / "index.html"
    if not index.is_file():
        return

    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="frontend_assets")

    @app.get("/")
    def spa_index():
        return FileResponse(index)

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        if full_path.startswith(("api/", "product_media/", "assets/")):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = dist / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)


_mount_frontend()


def main():
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8787, reload=False)


if __name__ == "__main__":
    main()
