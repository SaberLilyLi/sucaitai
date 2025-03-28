import json
import pandas as pd
from tabulate import tabulate
import re

def load_and_display_data():
    # 加载JSON数据
    with open('taobao_results.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 提取价格中的数字并修正月销量计算
    for item in data:
        # 处理价格字段，提取数字部分
        if 'price' in item:
            price_text = item['price']
            price_match = re.search(r'¥\s*(\d+(\.\d+)?)', price_text)
            if price_match:
                item['price_value'] = float(price_match.group(1))
            else:
                item['price_value'] = 0
        
        # 修正月销量计算 (总销量 ÷ 12，而不是 ÷ 30)
        if 'total_sales' in item:
            item['monthly_sales'] = item['total_sales'] / 12
    
    # 创建DataFrame
    df = pd.DataFrame(data)
    
    # 按总销量排序
    df_sorted = df.sort_values(by='total_sales', ascending=False)
    
    # 打印排序后的前20个商品
    print("\n按销量排序的前20个商品:")
    print(tabulate(df_sorted[['total_sales', 'monthly_sales', 'price']].head(20), headers='keys', tablefmt='pretty'))
    
    # 计算统计信息
    print("\n销量统计信息:")
    print(f"总商品数: {len(data)}")
    print(f"总销量大于100的商品数: {len(df[df['total_sales'] > 100])}")
    print(f"所有商品总销量之和: {df['total_sales'].sum()}")
    print(f"平均总销量: {df['total_sales'].mean():.2f}")
    print(f"平均月销量: {df['monthly_sales'].mean():.2f}")
    
    # 导出到Excel便于进一步分析
    df_sorted.to_excel('taobao_sales_analysis.xlsx', index=False)
    print("\n已将排序后的数据导出到 taobao_sales_analysis.xlsx")

if __name__ == "__main__":
    load_and_display_data() 