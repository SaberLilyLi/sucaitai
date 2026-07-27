# -*- coding: utf-8 -*-
"""通过万邦 API 拉取商品素材（主图 / SKU / 详情图 / 视频）并落盘。"""
from __future__ import annotations

import mimetypes
import re
import threading
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse, unquote
from urllib.request import Request, urlopen

from PIL import Image as PILImage

from store import DATA_DIR, load_products, normalize_product, update_product
from onebound_client import fetch_item_media, normalize_platform, onebound_configured

OUT_DIR = DATA_DIR / "product_media"
_lock = threading.Lock()


def item_id_from_url(url: str) -> str:
    try:
        q = parse_qs(urlparse(url).query)
        if q.get("id"):
            return q["id"][0]
    except Exception:
        pass
    m = re.search(r"id=(\d+)", url or "")
    if m:
        return m.group(1)
    m = re.search(r"/offer/(\d+)\.html", url or "")
    return m.group(1) if m else ""


def _http_get(url: str, timeout: int = 40) -> tuple[bytes, str]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ),
        "Referer": "https://item.taobao.com/",
    }
    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
    return data, ctype


def download_image(url: str, dest: Path, *, max_side: int = 1200) -> Path | None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        data, _ = _http_get(url, timeout=30)
        img = PILImage.open(BytesIO(data))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail((max_side, max_side))
        dest = dest.with_suffix(".jpg")
        img.save(dest, format="JPEG", quality=88)
        return dest
    except Exception as e:
        print(f"图片下载失败: {url[:80]} ({e})")
        return None


def download_video(url: str, dest: Path) -> Path | None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        data, ctype = _http_get(url, timeout=90)
        if len(data) < 1024:
            raise ValueError("文件过小，可能不是视频")
        if b"#EXTM3U" in data[:64] or "mpegurl" in (ctype or "").lower():
            print(f"跳过 m3u8 流媒体: {url[:80]}")
            return None
        ext = ".mp4"
        path_ext = Path(unquote(urlparse(url).path)).suffix.lower()
        if path_ext in {".mp4", ".webm", ".mov"}:
            ext = path_ext
        elif ctype:
            guess = mimetypes.guess_extension(ctype.split(";")[0].strip()) or ""
            if guess in {".mp4", ".webm", ".mov", ".bin"}:
                ext = guess if guess != ".bin" else ".mp4"
        dest = dest.with_suffix(ext)
        dest.write_bytes(data)
        return dest
    except Exception as e:
        print(f"视频下载失败: {url[:80]} ({e})")
        return None


def _merge_updated_product(
    product_id: str,
    url: str,
    *,
    detail_title: str,
    detail_price: str,
    detail_url: str,
    detail_location: str = "",
    base_product: dict | None = None,
) -> dict:
    products = load_products()
    existing = next((p for p in products if p.get("id") == product_id), None)
    snapshot = base_product if isinstance(base_product, dict) else None
    if snapshot:
        snapshot = {**snapshot, "id": product_id}
    base_row = {**(existing or {}), **(snapshot or {})}
    keep_title = (
        (snapshot or {}).get("title") or (existing or {}).get("title") or ""
    ).strip()
    keep_price = (
        (snapshot or {}).get("price") or (existing or {}).get("price") or ""
    ).strip()
    keep_loc = (
        detail_location
        or (snapshot or {}).get("location")
        or (existing or {}).get("location")
        or ""
    ).strip()
    raw = {
        **base_row,
        "id": product_id,
        "title": detail_title or keep_title,
        "url": detail_url or url,
        "price": detail_price or keep_price,
        "location": keep_loc,
    }
    updated = normalize_product(raw)
    if not updated:
        raise RuntimeError("规范化商品失败")
    from store import _media_images

    updated["images"] = _media_images(product_id)
    if updated["images"].get("main"):
        updated["cover"] = updated["images"]["main"][0]["src"]
    if not (updated.get("title") or "").strip() and keep_title:
        updated["title"] = keep_title
    update_product(updated)
    return updated


def _download_media_bundle(
    product_id: str,
    data: dict,
    *,
    main_limit: int,
    sku_limit: int,
    detail_limit: int,
    video_limit: int,
) -> tuple[int, int, int, int]:
    base = OUT_DIR / product_id
    saved_main = saved_sku = saved_detail = saved_video = 0

    for i, img in enumerate((data.get("main") or [])[:main_limit], 1):
        dest = base / "1比1主图" / f"1比1主图_{i}.jpg"
        if download_image(img.get("url") or "", dest, max_side=1000):
            saved_main += 1

    for i, img in enumerate((data.get("sku") or [])[:sku_limit], 1):
        label = re.sub(r'[\\/:*?"<>|]', "_", (img.get("label") or "").strip())[:30]
        name = f"SKU图_{i}_{label}.jpg" if label else f"SKU图_{i}.jpg"
        dest = base / "SKU图" / name
        if download_image(img.get("url") or "", dest, max_side=1000):
            saved_sku += 1

    for i, img in enumerate((data.get("detail") or [])[:detail_limit], 1):
        dest = base / "详情图" / f"详情图_{i:02d}.jpg"
        if download_image(img.get("url") or "", dest, max_side=1400):
            saved_detail += 1

    for i, vid in enumerate((data.get("video") or [])[:video_limit], 1):
        dest = base / "视频" / f"视频_{i}"
        if download_video(vid.get("url") or "", dest):
            saved_video += 1

    return saved_main, saved_sku, saved_detail, saved_video


def fetch_product_media(
    product_id: str,
    url: str,
    *,
    main_limit: int = 8,
    sku_limit: int = 12,
    detail_limit: int = 40,
    video_limit: int = 3,
    base_product: dict | None = None,
    platform: str | None = None,
) -> dict:
    """拉取主图/SKU/详情图/视频（万邦 item_get）。"""
    if not onebound_configured():
        raise RuntimeError(
            "未配置万邦 API：请在 server/.env 填写 ONEBOUND_API_KEY / ONEBOUND_API_SECRET"
        )

    plat = normalize_platform(
        platform
        or (base_product or {}).get("platform")
        or ("1688" if "1688.com" in (url or "") else "taobao")
    )
    product_id = (product_id or item_id_from_url(url) or "").strip()
    url = (url or "").strip()
    if not url and not product_id:
        raise ValueError("缺少商品链接或 ID")
    if not product_id:
        product_id = item_id_from_url(url) or "unknown"
    if not url:
        if plat == "1688":
            url = f"https://detail.1688.com/offer/{product_id}.html"
        else:
            url = f"https://item.taobao.com/item.htm?id={product_id}"

    if not _lock.acquire(blocking=False):
        raise RuntimeError("已有详情拉取任务在进行，请稍后再试")

    try:
        media = fetch_item_media(product_id, platform=plat)
        saved_main, saved_sku, saved_detail, saved_video = _download_media_bundle(
            product_id,
            media,
            main_limit=main_limit,
            sku_limit=sku_limit,
            detail_limit=detail_limit,
            video_limit=video_limit,
        )
        updated = _merge_updated_product(
            product_id,
            url,
            detail_title=(media.get("title") or "").strip(),
            detail_price=(media.get("price") or "").strip(),
            detail_url=(media.get("url") or url).strip(),
            detail_location=(media.get("location") or "").strip(),
            base_product={**(base_product or {}), "platform": plat},
        )
        updated["platform"] = plat
        total = saved_main + saved_sku + saved_detail + saved_video
        return {
            "product": updated,
            "saved_main": saved_main,
            "saved_sku": saved_sku,
            "saved_detail": saved_detail,
            "saved_video": saved_video,
            "source": f"onebound:{plat}",
            "message": (
                f"已拉取主图 {saved_main} / SKU {saved_sku} / "
                f"详情图 {saved_detail} / 视频 {saved_video}（{plat}）"
                if total
                else "万邦接口未返回可下载素材"
            ),
        }
    finally:
        _lock.release()
