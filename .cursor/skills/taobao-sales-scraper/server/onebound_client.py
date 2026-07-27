# -*- coding: utf-8 -*-
"""万邦 Onebound API 客户端（淘宝 + 1688 搜索 / 详情）。"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Literal

from runtime_paths import env_path

ENV_PATH = env_path()

Platform = Literal["taobao", "1688"]
DEFAULT_PAGE_SIZE = 40
MAX_PAGES = 5


def _load_dotenv() -> None:
    """从 .env 加载配置；文件中的值优先于已有环境变量（避免旧终端变量干扰）。"""
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key:
            os.environ[key] = val


_load_dotenv()


def normalize_platform(platform: str | None) -> Platform:
    raw = (platform or "taobao").strip().lower()
    if raw in ("1688", "alibaba", "ali", "alibaba1688"):
        return "1688"
    return "taobao"


def gateway_base(platform: str | None = None) -> str:
    p = normalize_platform(platform)
    if p == "1688":
        base = os.environ.get("ONEBOUND_1688_API_BASE", "https://api-gw.onebound.cn/1688/")
    else:
        base = os.environ.get("ONEBOUND_API_BASE", "https://api-gw.onebound.cn/taobao/")
    return base.rstrip("/") + "/"


def search_url(platform: str | None = None) -> str:
    p = normalize_platform(platform)
    if p == "1688":
        return (
            os.environ.get("ONEBOUND_1688_API_URL")
            or gateway_base("1688") + "item_search/"
        )
    return (
        os.environ.get("ONEBOUND_API_URL")
        or gateway_base("taobao") + "item_search/"
    )


def item_get_url(platform: str | None = None) -> str:
    p = normalize_platform(platform)
    if p == "1688":
        return (
            os.environ.get("ONEBOUND_1688_ITEM_GET_URL")
            or gateway_base("1688") + "item_get/"
        )
    return (
        os.environ.get("ONEBOUND_ITEM_GET_URL")
        or gateway_base("taobao") + "item_get/"
    )


def item_get_pro_url(platform: str | None = None) -> str:
    p = normalize_platform(platform)
    if p == "1688":
        return (
            os.environ.get("ONEBOUND_1688_ITEM_GET_PRO_URL")
            or gateway_base("1688") + "item_get_pro/"
        )
    return (
        os.environ.get("ONEBOUND_ITEM_GET_PRO_URL")
        or gateway_base("taobao") + "item_get_pro/"
    )


def item_desc_url(platform: str | None = None) -> str:
    p = normalize_platform(platform)
    if p == "1688":
        return (
            os.environ.get("ONEBOUND_1688_ITEM_DESC_URL")
            or gateway_base("1688") + "item_get_desc/"
        )
    return (
        os.environ.get("ONEBOUND_ITEM_DESC_URL")
        or gateway_base("taobao") + "item_get_desc/"
    )


# 兼容旧代码对常量的引用（默认淘宝）
ONEBOUND_BASE = gateway_base("taobao")
ONEBOUND_SEARCH_URL = search_url("taobao")
ONEBOUND_ITEM_GET_URL = item_get_url("taobao")
ONEBOUND_ITEM_GET_PRO_URL = item_get_pro_url("taobao")
ONEBOUND_ITEM_DESC_URL = item_desc_url("taobao")


def onebound_configured() -> bool:
    key = (os.environ.get("ONEBOUND_API_KEY") or "").strip()
    secret = (os.environ.get("ONEBOUND_API_SECRET") or "").strip()
    return bool(key and secret)


def _credentials() -> tuple[str, str]:
    key = (os.environ.get("ONEBOUND_API_KEY") or "").strip()
    secret = (os.environ.get("ONEBOUND_API_SECRET") or "").strip()
    if not key or not secret:
        raise RuntimeError("未配置 ONEBOUND_API_KEY / ONEBOUND_API_SECRET")
    return key, secret


def abs_url(u: object) -> str:
    s = str(u or "").strip().replace("&amp;", "&")
    if not s:
        return ""
    if s.startswith("//"):
        s = "https:" + s
    if not s.startswith("http"):
        return ""
    s = re.sub(r"_\d+x\d+[qQ]?\d*\.(jpg|jpeg|png|webp)", r".\1", s, flags=re.I)
    return s


def _parse_sales(val: object) -> int:
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).strip().replace(",", "").replace("，", "")
    if not s:
        return 0
    m = re.search(r"([\d.]+)\s*万", s)
    if m:
        try:
            return int(float(m.group(1)) * 10000)
        except ValueError:
            return 0
    m = re.search(r"(\d+)", s)
    return int(m.group(1)) if m else 0


def format_onebound_error(
    code: object = "",
    reason: object = "",
    *,
    api: str = "item_get",
) -> str:
    """把万邦错误码转成用户可读提示（天猫详情异常等）。"""
    code_s = str(code or "").strip()
    reason_s = str(reason or "").strip()
    blob = f"{code_s} {reason_s}".lower()

    if code_s == "5000" or "error5" in blob:
        return (
            "该商品详情暂时查不到（多为天猫商品，数据服务商接口异常，正在修复中）。"
            "请先换淘宝商品试试，或稍后再拉取。"
        )
    if code_s == "2000" or "item-not-found" in blob or "not found" in blob:
        return (
            "未找到该商品详情，可能已下架，或为天猫商品暂不支持。"
            "请换一个商品再试。"
        )
    # 4005 在万邦可能是「超量/超限」或「无权」：优先看文案
    if (
        "超量" in reason_s
        or "超限" in reason_s
        or "rate limit" in blob
        or "quota" in blob
        or code_s in ("4008", "4013")
    ):
        return (
            f"万邦接口调用已超量/超限（{api}）。"
            "请稍后再试，或到开放平台查看今日额度 / 联系客服加配额。"
        )
    if code_s == "4012" or "add api" in blob or "请先添加" in reason_s:
        return f"万邦账号尚未开通 {api} 接口，请到开放平台开通后再试。"
    if code_s == "4016" or "balance" in blob or "余额" in reason_s:
        return "万邦接口余额不足，请充值后再试。"
    if (
        code_s == "4005"
        or "无权" in reason_s
        or "无权限" in reason_s
        or ("auth" in blob and "超限" not in reason_s)
    ):
        return f"当前 Key 无 {api} 访问权限，请确认已开通对应接口。"
    if code_s in ("4001", "4002", "4017") or "timeout" in blob or "network" in blob:
        return "数据服务网络异常或超时，请稍后再试。"

    tip = reason_s or "未知错误"
    return (
        f"数据服务暂时异常（{code_s or '—'}：{tip}）。"
        "天猫商品可能受影响，服务商修复中，请稍后重试或换淘宝商品。"
    )


def _api_get(
    url: str,
    params: dict[str, str],
    *,
    timeout: int = 60,
    cache: str = "yes",
) -> dict[str, Any]:
    key, secret = _credentials()
    q = {
        "key": key,
        "secret": secret,
        "cache": cache if cache in ("yes", "no") else "yes",
        "result_type": "json",
        "lang": "cn",
    }
    q.update({k: str(v) for k, v in params.items() if v is not None and k != "cache"})
    if "cache" in params and params["cache"] in ("yes", "no"):
        q["cache"] = params["cache"]
    if url.endswith("/"):
        full = url + "?" + urllib.parse.urlencode(q)
    else:
        full = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(q)

    api_name = url.rstrip("/").split("/")[-1] or "onebound"
    req = urllib.request.Request(
        full,
        headers={
            "Accept-Encoding": "gzip",
            "User-Agent": "taobao-sales-scraper/onebound",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(
            format_onebound_error(str(e.code), body, api=api_name)
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            format_onebound_error("4001", str(e.reason), api=api_name)
        ) from e

    text = ""
    try:
        text = raw.decode("utf-8")
        data = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError):
        try:
            import gzip

            text = gzip.decompress(raw).decode("utf-8", errors="replace")
            data = json.loads(text)
        except Exception as e:
            preview = text[:200] if text else repr(raw[:200])
            raise RuntimeError(f"数据服务返回异常，请稍后再试（非 JSON：{preview}）") from e

    err = (data.get("error") or "").strip()
    code = str(data.get("error_code") or "")
    reason = str(data.get("reason") or err or "")
    if err and err.lower() not in ("", "ok") and code not in ("", "0000"):
        raise RuntimeError(format_onebound_error(code, reason or err, api=api_name))
    if code and code not in ("0000", "0") and data.get("success") == 0:
        raise RuntimeError(format_onebound_error(code, reason or err, api=api_name))
    return data


def map_onebound_item(item: dict, *, platform: str | None = None) -> dict | None:
    """映射为项目内部原始商品字段。"""
    if not isinstance(item, dict):
        return None
    p = normalize_platform(platform)
    num_iid = str(
        item.get("num_iid")
        or item.get("num_id")
        or item.get("offer_id")
        or item.get("item_id")
        or ""
    ).strip()
    title = re.sub(r"\s+", " ", str(item.get("title") or "").strip())
    if not title and not num_iid:
        return None

    price = item.get("promotion_price") or item.get("price") or item.get("orginal_price") or ""
    if isinstance(price, (int, float)):
        price = f"¥{price}"
    else:
        price = str(price).strip()
        if price and not price.startswith(("¥", "￥")):
            price = f"¥{price}"

    pic = abs_url(item.get("pic_url") or item.get("pic") or "")
    url = str(item.get("detail_url") or item.get("item_url") or "").strip()
    if url.startswith("//"):
        url = "https:" + url
    if not url and num_iid:
        if p == "1688":
            url = f"https://detail.1688.com/offer/{num_iid}.html"
        else:
            url = f"https://item.taobao.com/item.htm?id={num_iid}"

    sales = _parse_sales(
        item.get("sales")
        or item.get("sold")
        or item.get("volume")
        or item.get("total_sold")
    )
    location = str(
        item.get("area")
        or item.get("location")
        or item.get("provcity")
        or item.get("item_loc")
        or ""
    ).strip()

    return {
        "id": num_iid,
        "title": title,
        "url": url,
        "price": price,
        "image": pic,
        "location": location,
        "ship_time": str(item.get("ship_time") or "").strip(),
        "total_sales": sales,
        "monthly_sales": sales / 12 if sales else 0,
        "shop_name": str(item.get("nick") or item.get("seller_nick") or "").strip(),
        "platform": p,
    }


def _push_unique(arr: list[dict], url: str, label: str = "") -> None:
    u = abs_url(url)
    if not u:
        return
    key = u.split("?")[0]
    if any((x.get("url") or "").split("?")[0] == key for x in arr):
        return
    arr.append({"url": u, "label": label or ""})


def _prop_label_map(item: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for field in ("property_alias", "props_name"):
        raw = str(item.get(field) or "")
        for part in raw.split(";"):
            bits = [b for b in part.split(":") if b != ""]
            if len(bits) >= 3:
                out[f"{bits[0]}:{bits[1]}"] = bits[-1]
    return out


def extract_item_media(item: dict) -> dict[str, Any]:
    """从 item_get 结果抽出主图 / SKU / 详情图 / 视频。"""
    main: list[dict] = []
    sku: list[dict] = []
    detail: list[dict] = []
    video: list[dict] = []
    labels = _prop_label_map(item)

    imgs = item.get("item_imgs") or []
    if isinstance(imgs, dict):
        imgs = imgs.get("item_img") or imgs.get("url") or []
    if isinstance(imgs, list):
        for i, row in enumerate(imgs, 1):
            if isinstance(row, dict):
                _push_unique(main, row.get("url") or "", f"主图_{i}")
            else:
                _push_unique(main, row, f"主图_{i}")
    if not main:
        _push_unique(main, item.get("pic_url") or "", "主图_1")

    prop_imgs = item.get("prop_imgs") or {}
    if isinstance(prop_imgs, dict):
        rows = prop_imgs.get("prop_img") or []
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                props = str(row.get("properties") or "").strip()
                label = labels.get(props) or props
                _push_unique(sku, row.get("url") or "", label)

    props_img = item.get("props_img") or {}
    if isinstance(props_img, dict):
        for props, url in props_img.items():
            if props in ("prop_img",):
                continue
            label = labels.get(str(props)) or str(props)
            _push_unique(sku, url, label)

    desc_img = item.get("desc_img") or item.get("desc_imgs") or []
    if isinstance(desc_img, dict):
        desc_img = list(desc_img.values())
    if isinstance(desc_img, list):
        for i, row in enumerate(desc_img, 1):
            if isinstance(row, dict):
                _push_unique(detail, row.get("url") or row.get("src") or "", f"详情_{i}")
            else:
                _push_unique(detail, row, f"详情_{i}")

    vids = item.get("video") or []
    if isinstance(vids, dict):
        vids = [vids]
    if isinstance(vids, list):
        for i, row in enumerate(vids, 1):
            if isinstance(row, dict):
                u = row.get("url") or row.get("video_url") or row.get("src") or ""
                _push_unique(video, u, row.get("label") or f"视频_{i}")
            else:
                _push_unique(video, row, f"视频_{i}")

    price = item.get("price") or item.get("orginal_price") or ""
    if isinstance(price, (int, float)):
        price_s = f"¥{price}"
    else:
        price_s = str(price).strip()
        if price_s and not price_s.startswith(("¥", "￥")):
            price_s = f"¥{price_s}"

    num_iid = str(item.get("num_iid") or item.get("num_id") or "").strip()
    detail_url = str(item.get("detail_url") or "").strip()
    if detail_url.startswith("//"):
        detail_url = "https:" + detail_url
    if not detail_url and num_iid:
        detail_url = f"https://item.taobao.com/item.htm?id={num_iid}"

    return {
        "id": num_iid,
        "title": re.sub(r"\s+", " ", str(item.get("title") or "").strip()),
        "price": price_s,
        "location": str(item.get("location") or "").strip(),
        "url": detail_url,
        "main": main,
        "sku": sku,
        "detail": detail,
        "video": video,
    }


def _item_has_media(item: dict) -> bool:
    if not isinstance(item, dict):
        return False
    if (item.get("title") or item.get("pic_url") or "").strip():
        return True
    imgs = item.get("item_imgs") or []
    if isinstance(imgs, list) and imgs:
        return True
    if isinstance(imgs, dict) and (imgs.get("item_img") or imgs.get("url")):
        return True
    return False


def item_get(
    num_iid: str,
    *,
    is_promotion: bool = True,
    platform: str | None = None,
) -> dict[str, Any]:
    """商品详情：优先 item_get；部分商品会 error5，再回退 item_get_pro。"""
    p = normalize_platform(platform)
    num_iid = str(num_iid or "").strip()
    if not num_iid:
        raise ValueError("缺少商品 ID")

    promo = "1" if is_promotion else "0"
    first_err = ""
    get_url = item_get_url(p)
    pro_url = item_get_pro_url(p)
    # 1) 用户指定的主接口
    try:
        data = _api_get(
            get_url,
            {"num_iid": num_iid, "is_promotion": promo},
            cache="yes",
        )
        item = data.get("item")
        if isinstance(item, dict) and _item_has_media(item):
            data["_detail_api"] = "item_get"
            data["_platform"] = p
            return data
        print(f"[onebound/{p}] item_get 无有效素材 id={num_iid}，尝试 item_get_pro")
        first_err = "item_get 无有效素材"
    except Exception as e:
        first_err = str(e)
        print(f"[onebound/{p}] item_get 失败 id={num_iid}: {first_err}；尝试 item_get_pro")

    # 2) 兜底：同一商品用 item_get_pro + num_iid
    try:
        data = _api_get(
            pro_url,
            {"num_iid": num_iid},
            cache="yes",
        )
        item = data.get("item")
        if isinstance(item, dict) and _item_has_media(item):
            data["_detail_api"] = "item_get_pro"
            data["_platform"] = p
            return data
    except Exception as e:
        raise RuntimeError(
            format_onebound_error("5000", "error5", api="item_get")
            if ("error5" in first_err or "5000" in first_err or "天猫" in first_err)
            else (
                first_err
                or format_onebound_error("", str(e), api="item_get_pro")
            )
        ) from e

    raise RuntimeError(
        "该商品详情暂时查不到（数据服务商接口异常或商品不支持）。"
        "请换一个商品试试，或稍后再拉取。"
    )


def item_get_desc_images(num_iid: str, *, platform: str | None = None) -> list[dict]:
    """尝试 item_get_desc 拉详情图；失败则返回空列表。"""
    p = normalize_platform(platform)
    num_iid = str(num_iid or "").strip()
    if not num_iid:
        return []
    try:
        data = _api_get(
            item_desc_url(p),
            {"num_iid": num_iid},
            timeout=45,
            cache="yes",
        )
    except Exception as e:
        print(f"[onebound/{p}] item_get_desc 跳过: {e}")
        return []

    out: list[dict] = []
    item = data.get("item") if isinstance(data.get("item"), dict) else data
    candidates = []
    if isinstance(item, dict):
        for key in ("desc_img", "desc_imgs", "images", "img", "item_imgs"):
            val = item.get(key)
            if val:
                candidates.append(val)
        desc = item.get("desc") or ""
        if isinstance(desc, str) and "http" in desc:
            candidates.append(
                re.findall(
                    r'(?:https?:)?//[^"\'\s<>]+\.(?:jpg|jpeg|png|webp)[^"\'\s<>]*',
                    desc,
                    re.I,
                )
            )
    for block in candidates:
        if isinstance(block, dict):
            block = list(block.values())
        if not isinstance(block, list):
            continue
        for i, row in enumerate(block, 1):
            if isinstance(row, dict):
                _push_unique(out, row.get("url") or row.get("src") or "", f"详情_{i}")
            else:
                _push_unique(out, row, f"详情_{len(out) + 1}")
    return out


def fetch_item_media(num_iid: str, *, platform: str | None = None) -> dict[str, Any]:
    """详情素材：优先 item_get，失败则 item_get_pro；详情图不足时补 item_get_desc。"""
    p = normalize_platform(platform)
    data = item_get(num_iid, platform=p)
    media = extract_item_media(data["item"])
    if len(media.get("detail") or []) < 3:
        extra = item_get_desc_images(num_iid, platform=p)
        if extra:
            media["detail"] = extra
    if not media["main"] and not media["sku"] and not media["detail"] and not media["video"]:
        raise RuntimeError(
            "该商品详情暂时查不到可用素材（数据服务商接口异常或商品不支持）。"
            "请换一个商品试试，或稍后再拉取。"
        )
    api_name = data.get("_detail_api") or "item_get"
    print(
        f"[onebound/{p}/{api_name}] id={media.get('id')} "
        f"main={len(media['main'])} sku={len(media['sku'])} "
        f"detail={len(media['detail'])} video={len(media['video'])}"
    )
    media["_detail_api"] = api_name
    media["platform"] = p
    return media


def item_search_page(
    keyword: str,
    *,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    start_price: float | None = None,
    end_price: float | None = None,
    sort: str = "",
    platform: str | None = None,
) -> dict[str, Any]:
    p = normalize_platform(platform)
    params: dict[str, str] = {
        "q": keyword,
        "page": str(max(1, int(page))),
        "page_size": str(max(1, min(int(page_size), 100))),
        "cat": "0",
        "sort": sort or "",
        "discount_only": "",
        "seller_info": "",
        "nick": "",
        "ppath": "",
        "imgid": "",
        "filter": "",
        "start_price": (
            str(start_price) if start_price is not None and float(start_price) > 0 else "0"
        ),
        "end_price": (
            str(end_price) if end_price is not None and float(end_price) > 0 else "0"
        ),
    }
    return _api_get(search_url(p), params, cache="no")


def search_items(
    keyword: str,
    *,
    limit: int = 100,
    start_price: float | None = None,
    end_price: float | None = None,
    sort: str = "",
    platform: str | None = None,
) -> list[dict]:
    """分页拉取并映射为内部商品列表。"""
    p = normalize_platform(platform)
    keyword = (keyword or "").strip()
    if not keyword:
        raise ValueError("关键词不能为空")
    limit = max(1, int(limit))
    page_size = min(DEFAULT_PAGE_SIZE, limit)
    out: list[dict] = []
    seen: set[str] = set()
    max_pages = min(MAX_PAGES, max(1, (limit + page_size - 1) // page_size))

    for page in range(1, max_pages + 1):
        data = item_search_page(
            keyword,
            page=page,
            page_size=page_size,
            start_price=start_price,
            end_price=end_price,
            sort=sort,
            platform=p,
        )
        block = data.get("items") or {}
        rows = block.get("item") if isinstance(block, dict) else None
        if rows is None and isinstance(data.get("item"), list):
            rows = data["item"]
        if not isinstance(rows, list):
            rows = []

        print(
            f"[onebound/{p}] page={page} got={len(rows)} "
            f"error_code={data.get('error_code')} reason={data.get('reason')}"
        )
        if not rows:
            break

        for row in rows:
            mapped = map_onebound_item(row, platform=p)
            if not mapped:
                continue
            key = mapped.get("id") or mapped.get("title") or ""
            if key in seen:
                continue
            seen.add(key)
            out.append(mapped)
            if len(out) >= limit:
                return out[:limit]

        pagecount = 0
        try:
            pagecount = int((block or {}).get("pagecount") or 0)
        except (TypeError, ValueError):
            pagecount = 0
        if pagecount and page >= pagecount:
            break

    return out[:limit]
