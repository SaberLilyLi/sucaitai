import json
import matplotlib.pyplot as plt
import pandas as pd
import re
import numpy as np

# 加载数据
with open('taobao_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 提取销量和价格数据
for item in data:
    # 处理价格字段，提取数字部分
    if 'price' in item:
        price_text = item['price']
        price_match = re.search(r'¥\s*(\d+(\.\d+)?)', price_text)
        if price_match:
            item['price_value'] = float(price_match.group(1))
        else:
            item['price_value'] = 0

# 转换为DataFrame
df = pd.DataFrame(data)

# 配置中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 创建图形窗口
plt.figure(figsize=(15, 12))

# 销量分布柱状图
plt.subplot(2, 2, 1)
plt.bar(range(len(df)), sorted(df['total_sales'], reverse=True))
plt.title('商品销量排序分布')
plt.xlabel('商品排名')
plt.ylabel('总销量(件)')

# 销量价格散点图
plt.subplot(2, 2, 2)
plt.scatter(df['price_value'], df['total_sales'], alpha=0.6)
plt.title('价格与销量关系')
plt.xlabel('价格(元)')
plt.ylabel('总销量(件)')

# 销量分布直方图
plt.subplot(2, 2, 3)
sales_bins = [0, 10, 30, 50, 100, 200, 500, max(df['total_sales'])+1]
plt.hist(df['total_sales'], bins=sales_bins)
plt.title('销量范围分布')
plt.xlabel('销量范围')
plt.ylabel('商品数量')
plt.xticks(sales_bins)

# 月销量前10商品
plt.subplot(2, 2, 4)
top10 = df.nlargest(10, 'monthly_sales')
plt.bar(range(len(top10)), top10['monthly_sales'])
plt.title('月均销量前10商品')
plt.xlabel('商品排名')
plt.ylabel('月均销量')

plt.tight_layout()
plt.savefig('taobao_sales_analysis.png')
plt.show()

print("数据分析图表已保存为 taobao_sales_analysis.png") 