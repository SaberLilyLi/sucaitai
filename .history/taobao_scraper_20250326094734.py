from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

class TaobaoScraper:
    def __init__(self):
        # 设置Chrome选项
        chrome_options = webdriver.ChromeOptions()
        
        # 添加一些反爬虫检测的规避措施
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 初始化浏览器
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })
        
        self.wait = WebDriverWait(self.driver, 15)  # 增加等待时间到15秒
    
    def login(self):
        # 打开淘宝登录页
        self.driver.get("https://login.taobao.com/")
        print("请在30秒内完成手动登录")
        time.sleep(30)
    
    def get_sales_data(self, keyword):
        try:
            # 搜索商品
            search_url = f"https://s.taobao.com/search?q={keyword}"
            print(f"正在访问搜索页面: {search_url}")
            self.driver.get(search_url)
            
            # 保存页面源码以供调试
            with open('page_source.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print("已保存页面源码到 page_source.html")
            
            # 增加等待时间，确保页面完全加载
            time.sleep(5)
            
            # 更新选择器以适应淘宝最新的页面结构
            self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".m-itemlist")
            ))
            
            # 获取商品列表
            items = self.driver.find_elements(By.CSS_SELECTOR, ".item")
            
            products = []
            for item in items:
                try:
                    # 更新选择器
                    title = item.find_element(By.CSS_SELECTOR, ".title a").text.strip()
                    sales = item.find_element(By.CSS_SELECTOR, ".deal-cnt").text.strip()
                    
                    # 提取数字
                    sales_number = int(re.search(r'\d+', sales).group()) if sales else 0
                    
                    # 计算月均销量
                    monthly_sales = sales_number / 30
                    
                    products.append({
                        'title': title,
                        'total_sales': sales_number,
                        'monthly_sales': monthly_sales
                    })
                    
                except Exception as e:
                    print(f"提取单个商品数据时出错: {str(e)}")
                    continue
                
            return products
            
        except Exception as e:
            print(f"详细错误信息: {str(e)}")
            return []
    
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