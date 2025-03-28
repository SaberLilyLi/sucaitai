from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import re
import random
import json

class TaobaoScraper:
    def __init__(self):
        # 设置Chrome选项
        chrome_options = webdriver.ChromeOptions()
        
        # 添加更多反爬虫检测的规避措施
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 添加用户代理
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        ]
        chrome_options.add_argument(f'--user-agent={random.choice(user_agents)}')
        
        # 禁用图片加载，提高速度
        chrome_options.add_argument('--blink-settings=imagesEnabled=false')
        
        # 初始化浏览器
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # 伪装WebDriver
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.navigator.chrome = {
                    runtime: {}
                };
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en']
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            '''
        })
        
        # 设置窗口大小以模拟正常浏览器行为
        self.driver.set_window_size(1920, 1080)
        
        self.wait = WebDriverWait(self.driver, 20)
    
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
            time.sleep(8)
            
            # 滚动页面以加载所有内容
            self._scroll_page()
            
            # 保存页面源码以供调试
            with open('page_source.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print("已保存页面源码到 page_source.html")

            # 尝试从页面脚本中提取数据
            try:
                products = self._extract_from_json()
                if products:
                    print(f"从JSON数据中提取到 {len(products)} 个商品")
                    return products
            except Exception as e:
                print(f"从JSON提取数据失败: {str(e)}")
            
            # 如果JSON提取失败，尝试从DOM提取
            return self._extract_from_dom()
            
        except Exception as e:
            print(f"获取销量数据时出错: {str(e)}")
            return []
    
    def _scroll_page(self):
        """滚动页面以加载所有内容"""
        print("滚动页面加载更多内容...")
        
        # 获取页面高度
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        # 滚动三次，每次停顿随机时间
        for _ in range(3):
            # 滚动到页面底部
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # 等待随机时间让页面加载
            time.sleep(random.uniform(2, 4))
            
            # 计算新的滚动高度
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            
            # 随机鼠标移动，模拟人类行为
            action = ActionChains(self.driver)
            action.move_by_offset(random.randint(-100, 100), random.randint(-100, 100))
            action.perform()
    
    def _extract_from_json(self):
        """尝试从页面内嵌的JSON数据中提取商品信息"""
        scripts = self.driver.find_elements(By.TAG_NAME, 'script')
        for script in scripts:
            content = script.get_attribute('innerHTML')
            if 'g_page_config' in content:
                # 提取JSON数据
                json_str = re.search(r'g_page_config\s*=\s*(\{.*?\});\s*', content, re.DOTALL)
                if json_str:
                    try:
                        json_data = json.loads(json_str.group(1))
                        items = json_data.get('mods', {}).get('itemlist', {}).get('data', {}).get('auctions', [])
                        
                        products = []
                        for item in items:
                            title = item.get('title', '无标题')
                            # 移除HTML标签
                            title = re.sub(r'<[^>]+>', '', title)
                            
                            # 提取销量数据
                            sales_text = item.get('view_sales', '0人付款')
                            sales_match = re.search(r'(\d+)', sales_text)
                            sales_number = int(sales_match.group(1)) if sales_match else 0
                            
                            # 月均销量
                            monthly_sales = sales_number / 30
                            
                            products.append({
                                'title': title,
                                'total_sales': sales_number,
                                'monthly_sales': monthly_sales,
                                'price': item.get('view_price', '0'),
                                'shop_name': item.get('nick', ''),
                                'location': item.get('item_loc', '')
                            })
                        
                        return products
                    except Exception as e:
                        print(f"解析JSON数据时出错: {str(e)}")
        
        return []
    
    def _extract_from_dom(self):
        """从DOM元素中提取商品信息"""
        print("尝试从DOM中提取商品信息...")
        
        # 尝试多种可能的选择器来查找商品列表
        selectors = [
            ".doubleCardWrapperAdapt--mEcC7olq",  # 从页面源码中观察到的新选择器
            ".item.J_MouserOnverReq",
            ".item",
            "[data-index]"  # 更通用的选择器
        ]
        
        items = []
        for selector in selectors:
            try:
                items = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if items:
                    print(f"使用选择器 '{selector}' 找到 {len(items)} 个商品")
                    break
            except Exception:
                continue
        
        if not items:
            print("无法找到商品列表，请检查页面结构")
            return []
        
        products = []
        for item in items:
            try:
                # 提取标题
                try:
                    title_element = item.find_element(By.CSS_SELECTOR, ".title a, .doubleTitle--VZLUYN_W, [class*='Title']")
                    title = title_element.text.strip()
                except:
                    try:
                        title = item.get_attribute('data-title')
                    except:
                        title = "无法获取标题"
                
                # 提取销量
                try:
                    # 尝试多种可能的销量选择器
                    sales_element = item.find_element(By.CSS_SELECTOR, ".deal-cnt, .realSales--XZJiepmt, [class*='Sales']")
                    sales_text = sales_element.text.strip()
                except:
                    try:
                        # 尝试从属性中获取
                        sales_text = item.get_attribute('data-sales')
                    except:
                        sales_text = "0人付款"
                
                # 提取数字
                sales_match = re.search(r'(\d+)', sales_text)
                sales_number = int(sales_match.group(1)) if sales_match else 0
                
                # 计算月均销量
                monthly_sales = sales_number / 30
                
                # 提取价格
                try:
                    price_element = item.find_element(By.CSS_SELECTOR, ".price, .priceInt--yqqZMJ5a, [class*='Price']")
                    price = price_element.text.strip()
                except:
                    price = "无法获取价格"
                
                products.append({
                    'title': title,
                    'total_sales': sales_number,
                    'monthly_sales': monthly_sales,
                    'price': price
                })
                
            except Exception as e:
                print(f"提取单个商品数据时出错: {str(e)}")
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
        
        if not products:
            print("未能获取到任何商品信息")
            return
            
        # 打印结果
        for i, product in enumerate(products, 1):
            print(f"\n商品 {i}:")
            print(f"标题: {product['title']}")
            print(f"总销量: {product['total_sales']}人付款")
            print(f"月均销量: {product['monthly_sales']:.2f}")
            if 'price' in product:
                print(f"价格: {product['price']}")
            if 'shop_name' in product:
                print(f"店铺: {product['shop_name']}")
            if 'location' in product:
                print(f"地点: {product['location']}")
        
        # 保存结果到文件
        with open('taobao_results.json', 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        print(f"\n已将结果保存到 taobao_results.json 文件")
            
    except Exception as e:
        print(f"程序运行出错: {str(e)}")
    finally:
        scraper.close()

if __name__ == "__main__":
    main() 