# -*- coding: utf-8 -*-
"""根据已下载的 product_media + taobao_results.json 重建 Excel（无需再开浏览器）。"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fetch_classified_images import (
    DATA_DIR,
    EXCEL_PATH,
    OUT_DIR,
    build_excel,
    clean_price,
    item_id_from_url,
    unique_products,
)


def main():
    items = json.loads((DATA_DIR / "taobao_results.json").read_text(encoding="utf-8"))
    products = unique_products(items, limit=10)

    product_rows = []
    image_rows = []

    for product in products:
        url = product["url"]
        iid = item_id_from_url(url)
        title = (product.get("title") or "").strip()
        price = clean_price(product.get("price") or "")
        base = OUT_DIR / iid
        if not base.exists():
            print(f"跳过（无本地图）: {title[:40]}")
            continue

        main_path = ""
        for category in ("1比1主图", "SKU图"):
            folder = base / category
            if not folder.exists():
                continue
            for path in sorted(folder.glob("*.jpg")):
                if category == "1比1主图" and not main_path:
                    main_path = str(path)
                image_rows.append(
                    {
                        "category": category,
                        "path": str(path),
                        "filename": path.name,
                        "price": price,
                        "url": url,
                        "title": title,
                    }
                )

        if not main_path and image_rows:
            for r in reversed(image_rows):
                if item_id_from_url(r["url"]) == iid:
                    main_path = r["path"]
                    break

        product_rows.append(
            {
                "price": price,
                "url": url,
                "title": title,
                "main_path": main_path,
            }
        )

    if not product_rows:
        raise SystemExit("没有可导出的商品图片")

    build_excel(product_rows, image_rows, EXCEL_PATH)
    print(f"商品 {len(product_rows)} 个，图片明细 {len(image_rows)} 张")


if __name__ == "__main__":
    main()
