# -*- coding: utf-8 -*-
"""淘宝搜索：万邦 Onebound API。"""
from __future__ import annotations

import threading

from store import filter_products, normalize_locations, save_raw_and_products
from onebound_client import normalize_platform, onebound_configured, search_items

_search_lock = threading.Lock()

DEFAULT_LIMIT = 100
MAX_LIMIT = 200


def _filter_summary(filters: dict) -> str:
    parts = []
    locs = normalize_locations(filters.get("locations") or filters.get("location"))
    if locs:
        parts.append(f"发货地={'/'.join(locs)}")
    if filters.get("ship_time"):
        parts.append(f"发货时间={filters['ship_time']}")
    if filters.get("price_min") is not None:
        parts.append(f"最低价={filters['price_min']}")
    if filters.get("price_max") is not None:
        parts.append(f"最高价={filters['price_max']}")
    return "，".join(parts)


def _build_filters(
    location: str | list[str] | None,
    locations: list[str] | None,
    ship_time: str | None,
    price_min: float | None,
    price_max: float | None,
) -> dict:
    filters: dict = {}
    locs = normalize_locations(locations if locations is not None else location)
    if locs:
        filters["locations"] = locs
        filters["location"] = ",".join(locs)
    st = (ship_time or "").strip()
    if st:
        filters["ship_time"] = st
    if price_min is not None:
        filters["price_min"] = price_min
    if price_max is not None:
        filters["price_max"] = price_max
    if (
        filters.get("price_min") is not None
        and filters.get("price_max") is not None
        and float(filters["price_min"]) > float(filters["price_max"])
    ):
        raise ValueError("价格下限不能大于上限")
    return filters


def _finalize(
    keyword: str,
    limit: int,
    filters: dict,
    raw: list[dict],
    *,
    source: str,
) -> dict:
    before = len(raw or [])
    raw = filter_products(raw or [], filters)
    print(f"[search/{source}] 筛选 {before} → {len(raw)}")

    summary = _filter_summary(filters)
    if not raw:
        save_raw_and_products([], keyword=keyword, filters=filters, limit=limit)
        tip = f"（条件：{summary}）" if summary else ""
        return {
            "keyword": keyword,
            "filters": filters,
            "limit": limit,
            "count": 0,
            "items": [],
            "source": source,
            "message": (
                f"未找到符合条件的商品{tip}。"
                "发货地/发货时间在 API 结果中常缺失，可先去掉这些条件再试。"
            ),
        }

    for p in raw:
        if p.get("total_sales"):
            p["monthly_sales"] = p["total_sales"] / 12

    items = save_raw_and_products(raw, keyword=keyword, filters=filters, limit=limit)
    msg = f"搜索完成，共 {len(items)} 个商品（{source}）"
    if summary:
        msg += f"（已筛选：{summary}）"
    return {
        "keyword": keyword,
        "filters": filters,
        "limit": limit,
        "count": len(items),
        "items": items,
        "source": source,
        "message": msg,
    }


def _run_onebound(keyword: str, limit: int, filters: dict, *, platform: str) -> dict:
    if not onebound_configured():
        raise RuntimeError(
            "未配置万邦 API：请在 server/.env 填写 ONEBOUND_API_KEY / ONEBOUND_API_SECRET"
        )

    fetch_limit = limit
    if filters.get("locations") or filters.get("ship_time"):
        fetch_limit = min(MAX_LIMIT, max(limit * 2, limit + 40))

    print(
        f"[search/onebound/{platform}] keyword={keyword!r} limit={limit} "
        f"fetch={fetch_limit} filters={filters}"
    )
    raw = search_items(
        keyword,
        limit=fetch_limit,
        start_price=filters.get("price_min"),
        end_price=filters.get("price_max"),
        platform=platform,
    )
    return _finalize(keyword, limit, filters, raw, source=f"onebound:{platform}")


def run_taobao_search(
    keyword: str,
    pages: int | None = None,
    *,
    limit: int | None = None,
    location: str | list[str] | None = None,
    locations: list[str] | None = None,
    ship_time: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    platform: str | None = None,
) -> dict:
    """阻塞执行搜索；同一时间只允许一个任务。默认拉取约 50 条。

    pages 参数保留以兼容旧调用方，万邦模式下忽略。
    platform: taobao | 1688
    """
    del pages  # 兼容旧 API，不再使用翻页爬取
    plat = normalize_platform(platform)
    keyword = (keyword or "").strip()
    if not keyword:
        raise ValueError("关键词不能为空")

    if limit is None:
        limit = DEFAULT_LIMIT
    limit = max(1, min(int(limit), MAX_LIMIT))
    filters = _build_filters(location, locations, ship_time, price_min, price_max)

    if not _search_lock.acquire(blocking=False):
        raise RuntimeError("已有搜索任务在进行，请稍后再试")

    try:
        return _run_onebound(keyword, limit, filters, platform=plat)
    finally:
        _search_lock.release()
