# -*- coding: utf-8 -*-
"""自然语言选品意图解析：优先 DeepSeek，失败时回退本地规则。"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from runtime_paths import env_path

ENV_PATH = env_path()

DEEPSEEK_URL = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")

PROVINCES = (
    "北京|天津|上海|重庆|河北|山西|辽宁|吉林|黑龙江|江苏|浙江|安徽|福建|"
    "江西|山东|河南|湖北|湖南|广东|海南|四川|贵州|云南|陕西|甘肃|青海|"
    "台湾|内蒙古|广西|西藏|宁夏|新疆|香港|澳门"
)

SHIP_ALLOWED = (
    "24小时内发货",
    "48小时内发货",
    "当天发货",
    "次日达",
    "隔日达",
    "极速发货",
)

SHIP_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"48\s*小时(?:内)?(?:发货)?"), "48小时内发货"),
    (re.compile(r"24\s*小时(?:内)?(?:发货)?"), "24小时内发货"),
    (re.compile(r"当天发货|当日发货"), "当天发货"),
    (re.compile(r"次日达|第二天到|隔天到"), "次日达"),
    (re.compile(r"隔日达"), "隔日达"),
    (re.compile(r"极速发货|小时达"), "极速发货"),
]

NOISE_RE = re.compile(
    r"(?:请帮我|帮我|我想|我要|找一下|找下|搜索|淘宝|天猫|看看|有没有|"
    r"发货地|发货时间|多久到达|多久到货|到达|到货|价格区间|价位区间|"
    r"左右|之间|以内|以下|以上|块钱|元钱|人民币|"
    r"的商品|的产品|商品|产品|要求|条件|筛选|过滤|"
    r"(?<![a-zA-Z\u4e00-\u9fff])(?:找|买|要|弄)(?![a-zA-Z\u4e00-\u9fff])|"
    r"发的|寄的|来的)"
)

SYSTEM_PROMPT = """你是淘宝选品助手。把用户的自然语言需求解析成 JSON，用于淘宝搜索。
只输出一个 JSON 对象，不要 markdown，不要解释。字段：
{
  "keyword": "淘宝搜索关键词，简洁商品名，去掉口语废话",
  "locations": ["发货省份数组，如浙江、广东；没有则 []"],
  "ship_time": "仅可为：24小时内发货|48小时内发货|当天发货|次日达|隔日达|极速发货；没有则 null",
  "price_min": 数字或 null,
  "price_max": 数字或 null
}
规则：
- keyword 必填，尽量短，适合淘宝搜索框
- locations 可为多个省/直辖市，不要带“省”“市”；未提及则为 []
- 兼容旧字段 location（字符串）也可以，但优先用 locations 数组
- 价格单位为元；“100以内”→ price_max=100；“大概150”→ 约 105~195
- 未提及的字段用 null 或 []
"""


def _load_dotenv() -> None:
    """从 .env 加载配置；文件中的值优先于已有环境变量。"""
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


def _to_float(s: str) -> float | None:
    try:
        return float(s)
    except ValueError:
        return None


def _extract_locations(text: str) -> tuple[list[str], str]:
    """抽取文中全部省份，返回 (locations, cleaned_text)。"""
    locs: list[str] = []
    cleaned = text
    while True:
        m = re.search(
            rf"(?:从|发货地|发货|寄自|产地|发自|或|和|与|、|,|，)?\s*({PROVINCES})(?:省|市)?(?:发货|寄出|发出)?",
            cleaned,
        )
        if not m:
            m = re.search(rf"({PROVINCES})(?:省|市)?", cleaned)
        if not m:
            break
        loc = m.group(1)
        if loc not in locs:
            locs.append(loc)
        cleaned = cleaned[: m.start()] + " " + cleaned[m.end() :]
    return locs, cleaned


def _extract_ship_time(text: str) -> tuple[str | None, str]:
    for pat, label in SHIP_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        cleaned = text[: m.start()] + " " + text[m.end() :]
        return label, cleaned
    return None, text


def _extract_price(text: str) -> tuple[float | None, float | None, str]:
    lo: float | None = None
    hi: float | None = None
    cleaned = text

    m = re.search(
        r"(?:价格|价位|售价)?\s*(\d+(?:\.\d+)?)\s*[-~～到至]\s*(\d+(?:\.\d+)?)\s*(?:元|块|块钱)?",
        cleaned,
    )
    if m:
        a, b = _to_float(m.group(1)), _to_float(m.group(2))
        if a is not None and b is not None:
            lo, hi = min(a, b), max(a, b)
            cleaned = cleaned[: m.start()] + " " + cleaned[m.end() :]
            return lo, hi, cleaned

    m = re.search(
        r"(?:价格|价位)?\s*(?:在)?\s*(\d+(?:\.\d+)?)\s*(?:元|块)?\s*(?:以内|以下|之内)|"
        r"(?:低于|不超过|小于)\s*(\d+(?:\.\d+)?)\s*(?:元|块)?",
        cleaned,
    )
    if m:
        hi = _to_float(m.group(1) or m.group(2))
        cleaned = cleaned[: m.start()] + " " + cleaned[m.end() :]
        return lo, hi, cleaned

    m = re.search(
        r"(?:价格|价位)?\s*(?:在)?\s*(\d+(?:\.\d+)?)\s*(?:元|块)?\s*(?:以上|起)|"
        r"(?:高于|不低于|大于)\s*(\d+(?:\.\d+)?)\s*(?:元|块)?",
        cleaned,
    )
    if m:
        lo = _to_float(m.group(1) or m.group(2))
        cleaned = cleaned[: m.start()] + " " + cleaned[m.end() :]
        return lo, hi, cleaned

    m = re.search(r"(?:大概|约|左右)?\s*(\d+(?:\.\d+)?)\s*(?:元|块)(?:左右|上下)?", cleaned)
    if m:
        mid = _to_float(m.group(1))
        if mid is not None:
            lo, hi = mid * 0.7, mid * 1.3
            cleaned = cleaned[: m.start()] + " " + cleaned[m.end() :]
        return lo, hi, cleaned

    return lo, hi, cleaned


def _clean_keyword(text: str) -> str:
    t = NOISE_RE.sub(" ", text)
    t = re.sub(r"(?:价格|价位|售价)", " ", t)
    t = re.sub(r"[，,。.!！？?\s]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" ，,。.")
    t = re.sub(r"(?<!\S)\d+(?:\.\d+)?(?!\S)", " ", t)
    t = re.sub(r"^(?:的|和|与|及|找|买|要|弄|搜)+", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _build_result(
    keyword: str,
    locations: list[str] | str | None,
    ship_time: str | None,
    price_min: float | None,
    price_max: float | None,
    *,
    source: str,
) -> dict[str, Any]:
    if ship_time and ship_time not in SHIP_ALLOWED:
        # 尝试归一
        for allowed in SHIP_ALLOWED:
            if allowed in ship_time or ship_time in allowed:
                ship_time = allowed
                break
        else:
            ship_time = None

    if isinstance(locations, str):
        loc_list = [re.sub(r"[省市]$", "", x.strip()) for x in re.split(r"[,，、/\s]+", locations) if x.strip()]
    elif isinstance(locations, list):
        loc_list = [re.sub(r"[省市]$", "", str(x).strip()) for x in locations if str(x).strip()]
    else:
        loc_list = []
    # 去重保序
    seen: set[str] = set()
    locs: list[str] = []
    for x in loc_list:
        if x and x not in seen:
            seen.add(x)
            locs.append(x)

    tags: list[dict[str, str]] = []
    if keyword:
        tags.append({"type": "keyword", "label": f"关键词：{keyword}"})
    if locs:
        tags.append({"type": "location", "label": f"发货地：{'/'.join(locs)}"})
    if ship_time:
        tags.append({"type": "ship_time", "label": f"发货：{ship_time}"})
    if price_min is not None or price_max is not None:
        lo_s = (
            f"{int(price_min) if price_min == int(price_min) else price_min}"
            if price_min is not None
            else "不限"
        )
        hi_s = (
            f"{int(price_max) if price_max == int(price_max) else price_max}"
            if price_max is not None
            else "不限"
        )
        tags.append({"type": "price", "label": f"价格：{lo_s}-{hi_s}"})

    parts = [t["label"] for t in tags]
    prefix = "DeepSeek 已识别" if source == "deepseek" else "本地规则已识别"
    return {
        "keyword": keyword,
        "location": locs[0] if len(locs) == 1 else (",".join(locs) if locs else None),
        "locations": locs,
        "ship_time": ship_time,
        "price_min": price_min,
        "price_max": price_max,
        "tags": tags,
        "source": source,
        "message": f"{prefix}：" + "；".join(parts) if parts else "未能识别有效条件",
    }


def parse_search_intent_rules(text: str) -> dict[str, Any]:
    """本地规则解析（DeepSeek 不可用时的回退）。"""
    raw = (text or "").strip()
    if not raw:
        return _build_result("", [], None, None, None, source="rules")

    rest = raw
    locations, rest = _extract_locations(rest)
    ship_time, rest = _extract_ship_time(rest)
    price_min, price_max, rest = _extract_price(rest)
    keyword = _clean_keyword(rest) or _clean_keyword(raw)
    if len(keyword) < 2:
        keyword = re.sub(r"[，,。.\s]+", " ", raw).strip()
    return _build_result(keyword, locations, ship_time, price_min, price_max, source="rules")


def _extract_json_object(content: str) -> dict[str, Any]:
    content = (content or "").strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", content)
    if not m:
        raise ValueError("DeepSeek 未返回 JSON")
    data = json.loads(m.group(0))
    if not isinstance(data, dict):
        raise ValueError("DeepSeek JSON 格式错误")
    return data


def _normalize_ai_payload(data: dict[str, Any]) -> dict[str, Any]:
    keyword = str(data.get("keyword") or "").strip()
    locs_raw = data.get("locations")
    if locs_raw is None:
        locs_raw = data.get("location")
    if isinstance(locs_raw, list):
        locations = [str(x).strip() for x in locs_raw if str(x).strip()]
    elif locs_raw not in (None, "", "null"):
        locations = [str(locs_raw).strip()]
    else:
        locations = []

    ship_time = data.get("ship_time")
    ship_time = str(ship_time).strip() if ship_time not in (None, "", "null") else None

    def num(v: Any) -> float | None:
        if v is None or v == "" or v == "null":
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    return _build_result(
        keyword,
        locations,
        ship_time,
        num(data.get("price_min")),
        num(data.get("price_max")),
        source="deepseek",
    )


def parse_search_intent_deepseek(text: str, api_key: str) -> dict[str, Any]:
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "temperature": 0.1,
        "thinking": {"type": "disabled"},
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    content = (
        ((body.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    )
    data = _extract_json_object(content)
    result = _normalize_ai_payload(data)
    if not result.get("keyword"):
        raise ValueError("DeepSeek 未识别出关键词")
    return result


def parse_search_intent(text: str) -> dict[str, Any]:
    """优先 DeepSeek；无 Key / 调用失败则回退本地规则。"""
    raw = (text or "").strip()
    if not raw:
        return {
            "keyword": "",
            "location": None,
            "locations": [],
            "ship_time": None,
            "price_min": None,
            "price_max": None,
            "tags": [],
            "source": "none",
            "message": "请输入一段选品描述",
        }

    api_key = (os.environ.get("DEEPSEEK_API_KEY") or "").strip()
    if api_key:
        try:
            return parse_search_intent_deepseek(raw, api_key)
        except Exception as e:
            print(f"[intent] DeepSeek 失败，回退规则解析: {e}")
            fallback = parse_search_intent_rules(raw)
            fallback["message"] = (
                f"{fallback.get('message') or ''}（DeepSeek 暂不可用：{e}）"
            ).strip()
            fallback["deepseek_error"] = str(e)
            return fallback

    result = parse_search_intent_rules(raw)
    result["message"] = (result.get("message") or "") + "（未配置 DEEPSEEK_API_KEY，已用本地规则）"
    return result
