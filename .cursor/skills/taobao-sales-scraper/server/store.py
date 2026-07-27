# -*- coding: utf-8 -*-
"""JSON 本地库读写 + 商品字段规范化。"""
from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from runtime_paths import app_root, data_dir

SKILL_ROOT = app_root()
DATA_DIR = data_dir()
LIBRARY_PATH = DATA_DIR / "library.json"

_lock = threading.Lock()

# 搜索结果仅会话内存，不落盘；再次搜索覆盖，进程重启即清空
_session_products: list[dict] = []

_PROVINCE_RE = re.compile(
    r"(北京|天津|上海|重庆|河北|山西|辽宁|吉林|黑龙江|江苏|浙江|安徽|福建|"
    r"江西|山东|河南|湖北|湖南|广东|海南|四川|贵州|云南|陕西|甘肃|青海|"
    r"台湾|内蒙古|广西|西藏|宁夏|新疆|香港|澳门)"
    r"(?:[\u4e00-\u9fff]{0,3})?"
)
_PRICE_RE = re.compile(r"¥\s*(\d+(?:\.\d+)?)")

# 发货时间筛选项 → 可匹配的子串（卡片文案不完全一致）
_SHIP_MATCHERS: dict[str, tuple[str, ...]] = {
    "24小时": ("24小时", "24 小时"),
    "24小时内发货": ("24小时", "24 小时"),
    "48小时": ("48小时", "48 小时"),
    "48小时内发货": ("48小时", "48 小时"),
    "当天发货": ("当天发货", "当日发货"),
    "次日达": ("次日达",),
    "隔日达": ("隔日达",),
    "极速发货": ("极速发货", "小时达"),
}


def clean_price(text: object) -> str:
    s = str(text or "").replace("\n", " ")
    m = _PRICE_RE.search(s)
    if not m:
        m2 = re.search(r"(\d+(?:\.\d+)?)", s)
        return f"¥{m2.group(1)}" if m2 else ""
    whole = m.group(1)
    rest = s[m.end() :]
    dec = re.match(r"\s*\.(\d+)", rest)
    if dec and "." not in whole:
        whole = f"{whole}.{dec.group(1)}"
    return f"¥{whole}"


def item_id_from_url(url: str) -> str:
    try:
        q = parse_qs(urlparse(url).query)
        if q.get("id"):
            return q["id"][0]
    except Exception:
        pass
    m = re.search(r"id=(\d+)", url or "")
    return m.group(1) if m else ""


def _location(item: dict) -> str:
    for key in ("location", "发货地"):
        val = (item.get(key) or "").strip()
        if val:
            return re.sub(r"\s+", "", val)
    blob = " ".join(str(item.get(k) or "") for k in ("price", "title", "location"))
    m = _PROVINCE_RE.search(blob.replace("\n", ""))
    return m.group(0) if m else ""


def _media_images(item_id: str) -> dict:
    main, sku, detail, video = [], [], [], []
    if not item_id:
        return {"main": main, "sku": sku, "detail": detail, "video": video}
    base = DATA_DIR / "product_media" / item_id
    main_dir = base / "1比1主图"
    sku_dir = base / "SKU图"
    detail_dir = base / "详情图"
    video_dir = base / "视频"
    if main_dir.exists():
        main = [
            {"name": p.name, "src": f"/product_media/{item_id}/1比1主图/{p.name}"}
            for p in sorted(main_dir.glob("*.jpg"))
        ]
    if sku_dir.exists():
        sku = [
            {"name": p.name, "src": f"/product_media/{item_id}/SKU图/{p.name}"}
            for p in sorted(sku_dir.glob("*.jpg"))
        ]
    if detail_dir.exists():
        detail = [
            {"name": p.name, "src": f"/product_media/{item_id}/详情图/{p.name}"}
            for p in sorted(detail_dir.glob("*.jpg"))
        ]
    if video_dir.exists():
        video = [
            {"name": p.name, "src": f"/product_media/{item_id}/视频/{p.name}"}
            for p in sorted(video_dir.iterdir())
            if p.is_file() and p.suffix.lower() in {".mp4", ".webm", ".mov", ".m4v"}
        ]
    return {"main": main, "sku": sku, "detail": detail, "video": video}


def normalize_product(raw: dict) -> dict | None:
    title = re.sub(r"\s+", " ", (raw.get("title") or "").strip())
    url = (raw.get("url") or "").strip()
    iid = item_id_from_url(url) or raw.get("id") or ""
    if not title and not iid:
        return None

    price = clean_price(raw.get("price") or raw.get("price_value"))
    location = _location(raw)
    image = (raw.get("image") or raw.get("cover") or "").strip()
    if image.startswith("//"):
        image = "https:" + image

    images = _media_images(iid)
    # 搜索页封面：无本地分类图时，用列表缩略图顶上
    if not images["main"] and image:
        images["main"] = [{"name": "cover.jpg", "src": image}]

    cover = images["main"][0]["src"] if images["main"] else image

    tags = raw.get("tags") or []
    if isinstance(tags, str):
        tags = [x.strip() for x in re.split(r"[,，、]", tags) if x.strip()]
    elif isinstance(tags, (list, tuple, set)):
        tags = [str(x).strip() for x in tags if str(x).strip()]
    else:
        tags = []

    product = {
        "id": iid or title[:16],
        "title": title,
        "url": url,
        "price": price,
        "location": location,
        "cover": cover,
        "ship_time": (raw.get("ship_time") or "").strip(),
        "total_sales": raw.get("total_sales") or 0,
        "images": images,
    }
    # 素材库的业务字段：搜索、详情拉取时也要保留，避免覆盖用户的归档信息。
    for key in ("project", "note", "savedAt"):
        value = raw.get(key)
        if value:
            product[key] = str(value).strip()
    if tags:
        product["tags"] = list(dict.fromkeys(tags))
    return product


def parse_price_num(price: object) -> float | None:
    s = str(price or "").replace(",", "").replace("¥", "").replace("￥", "").strip()
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def location_matches(product_loc: str, want: str) -> bool:
    """发货地匹配：要求商品发货地包含所选省份/城市。"""
    want = re.sub(r"\s+", "", (want or "").strip())
    ploc = re.sub(r"\s+", "", (product_loc or "").strip())
    if not want:
        return True
    if not ploc:
        return False
    want_n = want.replace("省", "").replace("市", "")
    ploc_n = ploc.replace("省", "").replace("市", "")
    return want_n in ploc_n or ploc_n in want_n


def normalize_locations(value: object) -> list[str]:
    """把发货地统一成去重后的省份列表（支持 str / list / 逗号分隔）。"""
    if value is None:
        return []
    raw: list[str] = []
    if isinstance(value, (list, tuple, set)):
        for item in value:
            raw.extend(normalize_locations(item))
        seen: set[str] = set()
        out: list[str] = []
        for x in raw:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    s = str(value).strip()
    if not s or s.lower() == "null":
        return []
    parts = re.split(r"[,，、/\s]+", s)
    out = []
    seen = set()
    for p in parts:
        loc = re.sub(r"[省市]$", "", p.strip())
        if loc and loc not in seen:
            seen.add(loc)
            out.append(loc)
    return out


def locations_match(product_loc: str, wants: list[str] | str | None) -> bool:
    """多选发货地：命中任一即可。"""
    want_list = normalize_locations(wants)
    if not want_list:
        return True
    return any(location_matches(product_loc, w) for w in want_list)


def ship_time_matches(product_ship: str, want: str) -> bool:
    """发货时间匹配：无时效文案视为不满足；按别名表或子串匹配。"""
    want = (want or "").strip()
    pship = re.sub(r"\s+", "", (product_ship or "").strip())
    if not want:
        return True
    if not pship:
        return False
    keys = _SHIP_MATCHERS.get(want) or _SHIP_MATCHERS.get(want.replace(" ", ""))
    if keys:
        return any(k.replace(" ", "") in pship for k in keys)
    return re.sub(r"\s+", "", want) in pship


def filter_products(items: list[dict], filters: dict | None = None) -> list[dict]:
    """对已规范化或原始商品做发货地/发货时间/价格筛选（保存前强制调用）。"""
    filters = filters or {}
    locs = normalize_locations(
        filters.get("locations")
        if filters.get("locations") is not None
        else filters.get("location") or filters.get("loc")
    )
    ship = (filters.get("ship_time") or "").strip()
    try:
        lo = (
            float(filters["price_min"])
            if filters.get("price_min") is not None and str(filters.get("price_min")) != ""
            else None
        )
    except (TypeError, ValueError):
        lo = None
    try:
        hi = (
            float(filters["price_max"])
            if filters.get("price_max") is not None and str(filters.get("price_max")) != ""
            else None
        )
    except (TypeError, ValueError):
        hi = None

    if not locs and not ship and lo is None and hi is None:
        return items

    out: list[dict] = []
    for p in items:
        ploc = str(p.get("location") or p.get("发货地") or "")
        if locs and not locations_match(ploc, locs):
            continue
        pship = str(p.get("ship_time") or p.get("发货时间多久") or "")
        if ship and not ship_time_matches(pship, ship):
            continue
        if lo is not None or hi is not None:
            num = parse_price_num(p.get("price"))
            if num is None:
                continue
            if lo is not None and num < lo:
                continue
            if hi is not None and num > hi:
                continue
        out.append(p)
    return out


def dedupe_products(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for raw in items:
        p = normalize_product(raw)
        if not p:
            continue
        key = p["id"] or p["title"]
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, data) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_products() -> list[dict]:
    with _lock:
        saved = _read_json(LIBRARY_PATH, [])
        metadata = {
            str(item.get("id")): item
            for item in saved
            if isinstance(item, dict) and item.get("id")
        }
        items = []
        for product in _session_products:
            library_item = metadata.get(str(product.get("id")), {})
            items.append(
                {
                    **product,
                    **{
                        key: library_item[key]
                        for key in ("project", "tags", "note", "savedAt")
                        if library_item.get(key)
                    },
                }
            )
        return items


def save_raw_and_products(
    raw_items: list[dict],
    keyword: str = "",
    filters: dict | None = None,
    limit: int | None = None,
) -> list[dict]:
    """规范化并写入会话内存（覆盖上次搜索），不写 products.json。"""
    global _session_products
    products = dedupe_products(raw_items)
    products = filter_products(products, filters)
    if limit is not None:
        products = products[: max(0, int(limit))]
    # 销量高的靠前
    products.sort(key=lambda x: x.get("total_sales") or 0, reverse=True)
    with _lock:
        _session_products = products
    return products


def load_library() -> list[dict]:
    with _lock:
        data = _read_json(LIBRARY_PATH, [])
        return data if isinstance(data, list) else []


def save_to_library(product: dict) -> list[dict]:
    with _lock:
        lib = _read_json(LIBRARY_PATH, [])
        if not isinstance(lib, list):
            lib = []
        normalized = normalize_product(product) or product
        pid = normalized.get("id")
        if not pid:
            return lib
        from datetime import datetime

        index = next((i for i, item in enumerate(lib) if item.get("id") == pid), None)
        if index is None:
            lib.append({**normalized, "savedAt": datetime.now().isoformat(timespec="seconds")})
        else:
            # 入库可反复编辑标签、项目和备注，同时保留首次归档时间。
            updated = {
                **lib[index],
                **normalized,
                "savedAt": lib[index].get("savedAt")
                or datetime.now().isoformat(timespec="seconds"),
            }
            # 前端明确传空值时，视为清空该归档字段，而非沿用旧值。
            for key in ("project", "tags", "note"):
                if key not in product:
                    continue
                value = product.get(key)
                if value is None or value == "" or value == []:
                    updated.pop(key, None)
                else:
                    updated[key] = value
            lib[index] = updated
        _write_json(LIBRARY_PATH, lib)
        return lib


def library_ids() -> list[str]:
    return [x.get("id") for x in load_library() if x.get("id")]


def update_product(product: dict) -> list[dict]:
    """按 id 更新会话中的一条搜索结果（不落盘）。"""
    global _session_products
    with _lock:
        items = list(_session_products)
        pid = product.get("id")
        found = False
        for i, row in enumerate(items):
            if row.get("id") == pid:
                items[i] = product
                found = True
                break
        if not found:
            items.insert(0, product)
        _session_products = items
        return items
