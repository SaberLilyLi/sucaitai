from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

class TaobaoScraper:
    def __init__(self):
        # 初始化浏览器
        self.driver = webdriver.Chrome()
        self.wait = WebDriverWait(self.driver, 10)
    
    def login(self):
        # 打开淘宝登录页
        self.driver.get("https://login.taobao.com/")
        print("请在30秒内完成手动登录")
        time.sleep(30)
    
    def get_sales_data(self, keyword):
        # 搜索商品
        search_url = f"https://s.taobao.com/search?q={keyword}"
        self.driver.get(search_url)
        time.sleep(3)
        
        products = []
        
        # 获取商品列表
        items = self.wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, ".item.J_MouserOnverReq")
        ))
        
        for item in items:
            try:
                # 获取商品标题
                title = item.find_element(By.CSS_SELECTOR, ".title").text
                
                # 获取销量数据
                sales = item.find_element(By.CSS_SELECTOR, ".deal-cnt").text
                sales_number = int(re.search(r'\d+', sales).group())
                
                # 计算月均销量（假设总销量数据是过去30天的）
                monthly_sales = sales_number / 30
                
                products.append({
                    'title': title,
                    'total_sales': sales_number,
                    'monthly_sales': monthly_sales
                })
                
            except Exception as e:
                print(f"提取数据时出错: {e}")
                continue
        
        return products
    
    def close(self):
        self.driver.quit()

def main():
    scraper = TaobaoScraper()
    try:
        # 登录淘宝
        scraper.login()
        
        # 输入要搜索的商品关键词
        keyword = input("请输入要搜索的商品关键词：")
        
        # 获取销量数据
        products = scraper.get_sales_data(keyword)
        
        # 打印结果
        for product in products:
            print("\n商品信息：")
            print(f"标题: {product['title']}")
            print(f"总销量: {product['total_sales']}")
            print(f"月均销量: {product['monthly_sales']:.2f}")
            
    finally:
        scraper.close()

if __name__ == "__main__":
    main() 