# -*- coding: utf-8 -*-
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

SKILL_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = SKILL_ROOT / "data"

json_path = DATA_DIR / "taobao_results.json"
if not json_path.exists():
    raise FileNotFoundError(f"未找到 {json_path}，请先运行 taobao_scraper.py")

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

for item in data:
    if "price" in item:
        price_text = item["price"]
        price_match = re.search(r"¥\s*(\d+(\.\d+)?)", price_text)
        item["price_value"] = float(price_match.group(1)) if price_match else 0
    if "total_sales" in item and "monthly_sales" not in item:
        item["monthly_sales"] = item["total_sales"] / 12

df = pd.DataFrame(data)

plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

plt.figure(figsize=(15, 12))

plt.subplot(2, 2, 1)
plt.bar(range(len(df)), sorted(df["total_sales"], reverse=True))
plt.title("商品销量排序分布")
plt.xlabel("商品排名")
plt.ylabel("总销量(件)")

plt.subplot(2, 2, 2)
plt.scatter(df["price_value"], df["total_sales"], alpha=0.6)
plt.title("价格与销量关系")
plt.xlabel("价格(元)")
plt.ylabel("总销量(件)")

plt.subplot(2, 2, 3)
sales_bins = [0, 10, 30, 50, 100, 200, 500, max(df["total_sales"]) + 1]
plt.hist(df["total_sales"], bins=sales_bins)
plt.title("销量范围分布")
plt.xlabel("销量范围")
plt.ylabel("商品数量")
plt.xticks(sales_bins)

plt.subplot(2, 2, 4)
top10 = df.nlargest(10, "monthly_sales")
plt.bar(range(len(top10)), top10["monthly_sales"])
plt.title("月均销量前10商品")
plt.xlabel("商品排名")
plt.ylabel("月均销量")

plt.tight_layout()
DATA_DIR.mkdir(parents=True, exist_ok=True)
out_png = DATA_DIR / "taobao_sales_analysis.png"
plt.savefig(out_png)
plt.show()

print(f"数据分析图表已保存为 {out_png}")
