# -*- coding: utf-8 -*-
"""商品字段清洗与 Excel 导出（中文列）。"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
from tabulate import tabulate

SKILL_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = SKILL_ROOT / "data"

EXPORT_COLUMNS = ["标题", "正文", "价格", "发货地", "发货时间多久", "图片链接"]

_PROVINCE_RE = re.compile(
    r"(北京|天津|上海|重庆|河北|山西|辽宁|吉林|黑龙江|江苏|浙江|安徽|福建|"
    r"江西|山东|河南|湖北|湖南|广东|海南|四川|贵州|云南|陕西|甘肃|青海|"
    r"台湾|内蒙古|广西|西藏|宁夏|新疆|香港|澳门)"
    r"(?:[\u4e00-\u9fff]{0,3})?"
)

_PRICE_PATTERN = re.compile(r"¥\s*(\d+(?:\.\d+)?)")
_SHIP_PATTERN = re.compile(
    r"(\d+\s*小时内发货|当天发货|隔日达|次日达|24小时内发货|48小时内发货|"
    r"付款后\d+天内发货|极速发货|现货|包邮|"
    r"\d+天内发货)"
)


def clean_price(text: Any) -> str:
    if text is None:
        return ""
    s = str(text).replace("\n", " ")
    m = _PRICE_PATTERN.search(s)
    if not m:
        m2 = re.search(r"(\d+(?:\.\d+)?)", s)
        return f"¥{m2.group(1)}" if m2 else ""
    # 尝试拼上小数点后半段，如 "¥\n61\n.6"
    whole = m.group(1)
    rest = s[m.end() :]
    dec = re.match(r"\s*\.(\d+)", rest)
    if dec and "." not in whole:
        whole = f"{whole}.{dec.group(1)}"
    return f"¥{whole}"


def clean_location(item: dict) -> str:
    for key in ("location", "发货地", "item_loc"):
        val = (item.get(key) or "").strip()
        if val and "人付款" not in val and "¥" not in val:
            # 压缩换行
            return re.sub(r"\s+", "", val)
    blob = " ".join(str(item.get(k) or "") for k in ("price", "title", "location"))
    m = _PROVINCE_RE.search(blob.replace("\n", ""))
    return m.group(0) if m else ""


def clean_ship_time(item: dict) -> str:
    for key in ("ship_time", "发货时间多久", "delivery"):
        val = (item.get(key) or "").strip()
        if val:
            return val
    blob = " ".join(str(item.get(k) or "") for k in ("price", "title", "body", "正文"))
    m = _SHIP_PATTERN.search(blob.replace("\n", ""))
    return m.group(1).replace(" ", "") if m else ""


def clean_image(item: dict) -> str:
    for key in ("image", "image_url", "图片链接", "pic_url", "pic"):
        val = (item.get(key) or "").strip()
        if val:
            if val.startswith("//"):
                return "https:" + val
            return val
    return ""


def clean_body(item: dict) -> str:
    for key in ("body", "正文", "desc", "description", "subtitle"):
        val = (item.get(key) or "").strip()
        if val:
            return re.sub(r"\s+", " ", val)
    # 搜索页通常无独立正文，用标题充当卖点文案
    return re.sub(r"\s+", " ", (item.get("title") or "").strip())


def to_export_row(item: dict) -> dict:
    title = re.sub(r"\s+", " ", (item.get("title") or item.get("标题") or "").strip())
    return {
        "标题": title,
        "正文": clean_body(item),
        "价格": clean_price(item.get("price") or item.get("价格") or item.get("price_value")),
        "发货地": clean_location(item) or (item.get("发货地") or ""),
        "发货时间多久": clean_ship_time(item) or (item.get("发货时间多久") or ""),
        "图片链接": clean_image(item) or (item.get("图片链接") or ""),
    }


def load_and_display_data():
    json_path = DATA_DIR / "taobao_results.json"
    if not json_path.exists():
        raise FileNotFoundError(f"未找到 {json_path}，请先运行 taobao_scraper.py")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = [to_export_row(item) for item in data]
    # 按原 total_sales 排序（若有）
    sales = [item.get("total_sales") or 0 for item in data]
    paired = sorted(zip(sales, rows), key=lambda x: x[0], reverse=True)
    rows_sorted = [r for _, r in paired]

    df = pd.DataFrame(rows_sorted, columns=EXPORT_COLUMNS)

    print("\n导出预览（前10条）:")
    print(tabulate(df.head(10), headers="keys", tablefmt="pretty", showindex=False))

    print("\n统计:")
    print(f"总商品数: {len(df)}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    xlsx_path = DATA_DIR / "taobao_sales_analysis.xlsx"
    try:
        df.to_excel(xlsx_path, index=False)
    except PermissionError:
        xlsx_path = DATA_DIR / "taobao_sales_analysis_new.xlsx"
        df.to_excel(xlsx_path, index=False)
        print("原 Excel 被占用，已另存为新文件")
    print(f"\n已导出: {xlsx_path}")
    print(f"列名: {', '.join(EXPORT_COLUMNS)}")


if __name__ == "__main__":
    load_and_display_data()
