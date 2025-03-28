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
            
            # 增加等待时间，确保页面完全加载
            time.sleep(10)  # 增加到10秒
            
            # 保存页面源码以供调试
            with open('page_source.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print("已保存页面源码到 page_source.html")

            # 检查是否被重定向到登录页面
            current_url = self.driver.current_url
            if 'login' in current_url:
                print("检测到重定向到登录页面，请确保已登录")
                # 等待手动登录
                time.sleep(30)
                # 重新访问搜索页面
                self.driver.get(search_url)
                time.sleep(10)
            
            # 先检查页面是否含有商品列表
            page_source = self.driver.page_source
            if 'J_ItemList' in page_source or '.item' in page_source or '.m-itemlist' in page_source:
                print("发现商品列表标记，尝试提取...")
            else:
                print("未发现商品列表标记，可能是反爬机制触发或页面结构变化")
                # 检查robots内容，分析反爬机制
                return []
            
            # 尝试多种可能的选择器
            try:
                # 方法1: 使用旧的选择器
                items = self.driver.find_elements(By.CSS_SELECTOR, ".J_MouserOnverReq")
                if not items:
                    # 方法2: 使用新的选择器
                    items = self.driver.find_elements(By.CSS_SELECTOR, ".item.J_MouserOnverReq")
                if not items:
                    # 方法3: 使用更通用的选择器
                    items = self.driver.find_elements(By.CSS_SELECTOR, ".item")
                
                print(f"找到 {len(items)} 个商品项")
            except Exception as e:
                print(f"查找商品列表时出错: {str(e)}")
                items = []
            
            products = []
            for item in items:
                try:
                    # 尝试多种可能的标题选择器
                    try:
                        title = item.find_element(By.CSS_SELECTOR, ".title a").text.strip()
                    except:
                        try:
                            title = item.find_element(By.CSS_SELECTOR, ".title").text.strip()
                        except:
                            title = "无法获取标题"
                    
                    # 尝试多种可能的销量选择器
                    try:
                        sales = item.find_element(By.CSS_SELECTOR, ".deal-cnt").text.strip()
                    except:
                        try:
                            sales = item.find_element(By.CSS_SELECTOR, ".transaction-count").text.strip()
                        except:
                            sales = "0人付款"
                    
                    # 提取数字
                    sales_match = re.search(r'\d+', sales)
                    sales_number = int(sales_match.group()) if sales_match else 0
                    
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