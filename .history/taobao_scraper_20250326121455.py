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
            
            # 检查是否需要验证
            if "验证码" in self.driver.title or "verify" in self.driver.current_url.lower():
                print("遇到验证码，请手动完成验证...")
                time.sleep(20)  # 给用户时间手动验证
            
            # 增加等待时间，确保页面完全加载
            time.sleep(8)
            
            # 安全地滚动页面
            try:
                self._scroll_page()
            except Exception as e:
                print(f"滚动页面时出错 (忽略并继续): {str(e)}")
            
            # 保存页面源码以供调试
            with open('page_source.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print("已保存页面源码到 page_source.html")

            # 尝试多种提取方法，按优先级排序
            extraction_methods = [
                ("JSON数据", self._extract_from_json),
                ("DOM元素", self._extract_from_dom),
                ("XPath查询", self._extract_from_xpath)
            ]
            
            for method_name, method_func in extraction_methods:
                try:
                    print(f"尝试从{method_name}中提取商品信息...")
                    products = method_func()
                    if products:
                        print(f"成功从{method_name}中提取到 {len(products)} 个商品")
                        return products
                except Exception as e:
                    print(f"{method_name}提取失败: {str(e)}")
            
            print("所有提取方法均失败，无法获取商品数据")
            return []
            
        except Exception as e:
            print(f"获取销量数据时出错: {str(e)}")
            return []
    
    def _scroll_page(self):
        """滚动页面以加载所有内容"""
        print("滚动页面加载更多内容...")
        
        try:
            # 获取页面高度
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # 滚动三次，每次停顿随机时间
            for i in range(3):
                # 滚动到页面的一部分，而不是完全滚动到底部
                scroll_position = (i+1) * last_height / 4  # 分成四部分滚动
                self.driver.execute_script(f"window.scrollTo(0, {scroll_position});")
                
                # 等待随机时间让页面加载
                time.sleep(random.uniform(2, 4))
                
                # 获取窗口大小，确保鼠标移动在窗口内
                window_size = self.driver.get_window_size()
                width = window_size['width']
                height = window_size['height']
                
                # 安全的随机鼠标移动，确保在窗口范围内
                try:
                    action = ActionChains(self.driver)
                    # 限制移动范围，避免超出窗口边界
                    x_offset = random.randint(10, max(11, width-100))
                    y_offset = random.randint(10, max(11, height-100))
                    action.move_by_offset(x_offset, y_offset).perform()
                    # 重置鼠标位置到原点，防止累积偏移
                    action.move_to_element(self.driver.find_element(By.TAG_NAME, 'body')).perform()
                except Exception as e:
                    print(f"鼠标移动时出错 (忽略并继续): {str(e)}")
        except Exception as e:
            print(f"页面滚动时出错 (继续执行): {str(e)}")
            # 继续执行，不要因为滚动失败而中断整个过程
    
    def _extract_from_json(self):
        """尝试从页面内嵌的JSON数据中提取商品信息"""
        print("尝试从页面内嵌JSON数据提取商品信息...")
        
        try:
            # 查找所有脚本标签
            scripts = self.driver.find_elements(By.TAG_NAME, 'script')
            
            # 查找包含商品数据的脚本
            for script in scripts:
                try:
                    content = script.get_attribute('innerHTML') or ''
                    
                    # 尝试多种可能的数据模式
                    data_patterns = [
                        r'g_page_config\s*=\s*(\{.*?\});\s*',
                        r'window\.g_srp_loadCss\s*=\s*(\{.*?\});\s*',
                        r'window\.__INIT_DATA__\s*=\s*(\{.*?\});\s*'
                    ]
                    
                    # 尝试每种模式
                    for pattern in data_patterns:
                        json_match = re.search(pattern, content, re.DOTALL)
                        if json_match:
                            try:
                                json_data = json.loads(json_match.group(1))
                                
                                # 尝试多种数据路径
                                item_paths = [
                                    lambda d: d.get('mods', {}).get('itemlist', {}).get('data', {}).get('auctions', []),
                                    lambda d: d.get('props', {}).get('pageProps', {}).get('listItems', []),
                                    lambda d: d.get('data', {}).get('items', [])
                                ]
                                
                                for path_func in item_paths:
                                    try:
                                        items = path_func(json_data)
                                        if items and isinstance(items, list) and len(items) > 0:
                                            # 写入完整JSON以便调试
                                            with open('json_data_found.json', 'w', encoding='utf-8') as f:
                                                json.dump(json_data, f, ensure_ascii=False, indent=2)
                                            
                                            products = []
                                            for item in items:
                                                # 尝试多种可能的字段名
                                                title = self._get_first_valid_value(item, ['title', 'raw_title', 'name', 'itemName', 'item_name'], '无标题')
                                                # 移除HTML标签
                                                title = re.sub(r'<[^>]+>', '', title)
                                                
                                                # 尝试多种可能的销量字段
                                                sales_text = self._get_first_valid_value(item, ['view_sales', 'sales', 'saleCount', 'sellCount', 'realSales', 'deal_cnt'], '0人付款')
                                                sales_match = re.search(r'(\d+)', str(sales_text))
                                                sales_number = int(sales_match.group(1)) if sales_match else 0
                                                
                                                # 月均销量
                                                monthly_sales = sales_number / 12
                                                
                                                # 提取价格
                                                price = self._get_first_valid_value(item, ['view_price', 'price', 'currentPrice', 'priceInt'], '0')
                                                
                                                products.append({
                                                    'title': title,
                                                    'total_sales': sales_number,
                                                    'monthly_sales': monthly_sales,
                                                    'price': price,
                                                    'shop_name': self._get_first_valid_value(item, ['nick', 'shopName', 'shop_name'], ''),
                                                    'location': self._get_first_valid_value(item, ['item_loc', 'location', 'itemLocation'], '')
                                                })
                                            
                                            if products:
                                                return products
                                    except Exception as e:
                                        pass  # 尝试下一个路径
                            except json.JSONDecodeError:
                                pass  # 尝试下一个模式
                except Exception:
                    continue  # 尝试下一个脚本标签
            
            # 尝试直接查找页面中的数据
            try:
                page_source = self.driver.page_source
                # 搜索页面中可能包含的数据模式
                all_json_matches = re.findall(r'<script[^>]*>([^<]*?g_page_config\s*=\s*\{.*?\};)[^<]*?</script>', 
                                            page_source, re.DOTALL)
                
                for match in all_json_matches:
                    try:
                        json_str = re.search(r'g_page_config\s*=\s*(\{.*?\});', match, re.DOTALL)
                        if json_str:
                            # 保存找到的JSON字符串供调试
                            with open('json_match.txt', 'w', encoding='utf-8') as f:
                                f.write(json_str.group(1))
                                
                            # 尝试解析
                            try:
                                json_data = json.loads(json_str.group(1))
                                # 继续提取项目...
                                # (这里可以复用上面的代码)
                            except json.JSONDecodeError:
                                pass
                    except Exception:
                        continue
            except Exception as e:
                print(f"尝试直接提取JSON时出错: {str(e)}")
        
        except Exception as e:
            print(f"从JSON提取过程中出错: {str(e)}")
        
        print("未能从JSON提取到商品数据")
        return []
    
    def _get_first_valid_value(self, dictionary, keys, default=''):
        """从字典中尝试多个键，返回第一个找到的值"""
        if not dictionary or not isinstance(dictionary, dict):
            return default
        
        for key in keys:
            if key in dictionary and dictionary[key]:
                return dictionary[key]
        
        return default
    
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
            print("无法找到商品列表，尝试获取商品链接...")
            
            # 尝试找到所有商品链接
            try:
                # 获取所有链接
                links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'item.taobao.com') or contains(@href, 'detail.tmall.com')]")
                
                # 从链接遍历获取商品信息
                products = []
                for link in links[:40]:  # 限制数量避免过长时间
                    try:
                        # 提取父元素中可能包含的销量信息
                        parent = link.find_element(By.XPATH, "./ancestor::div[contains(@class, 'doubleCardWrapperAdapt')]")
                        
                        # 获取标题
                        title = link.get_attribute('title') or link.text or "未知标题"
                        title = title.strip()
                        
                        # 提取销量
                        sales_text = "0人付款"
                        for sales_class in ['realSales--XZJiepmt', 'deal-cnt', 'sale-num']:
                            try:
                                sales_elem = parent.find_element(By.CSS_SELECTOR, f"[class*='{sales_class}']")
                                sales_text = sales_elem.text
                                if sales_text and re.search(r'\d+', sales_text):
                                    break
                            except:
                                pass
                        
                        sales_match = re.search(r'(\d+)', sales_text)
                        sales_number = int(sales_match.group(1)) if sales_match else 0
                        
                        # 获取价格
                        price_text = "价格未知"
                        for price_class in ['priceWrapper', 'price', 'Price']:
                            try:
                                price_elem = parent.find_element(By.CSS_SELECTOR, f"[class*='{price_class}']")
                                price_text = price_elem.text
                                if price_text and '¥' in price_text:
                                    break
                            except:
                                pass
                        
                        products.append({
                            'title': title,
                            'total_sales': sales_number,
                            'monthly_sales': sales_number / 12,
                            'price': price_text,
                            'url': link.get_attribute('href')
                        })
                        
                    except Exception as e:
                        print(f"处理链接数据时出错: {str(e)}")
                
                if products:
                    return products
            except Exception as e:
                print(f"尝试获取链接失败: {str(e)}")
            
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
                monthly_sales = sales_number / 12
                
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
    
    def _extract_from_xpath(self):
        """使用XPath提取商品信息，这是最后的备选方案"""
        print("尝试使用XPath提取商品信息...")
        
        try:
            # 基于观察到的页面结构提取商品
            items = self.driver.find_elements(By.XPATH, "//a[contains(@class, 'doubleCardWrapperAdapt') or contains(@class, 'pc-search-item-card')]")
            
            if not items:
                # 尝试更通用的选择器
                items = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'items')]/div")
            
            if not items:
                return []
            
            print(f"使用XPath找到 {len(items)} 个商品")
            
            products = []
            for item in items:
                try:
                    # 使用XPath提取信息
                    title = item.find_element(By.XPATH, ".//*[contains(@class, 'Title') or contains(@class, 'title')]").text.strip()
                    if not title:
                        continue
                    
                    # 提取销量
                    sales_element = None
                    try:
                        sales_element = item.find_element(By.XPATH, ".//*[contains(@class, 'Sales') or contains(@class, 'sales') or contains(text(), '人付款')]")
                    except:
                        pass
                    
                    sales_text = sales_element.text if sales_element else "0人付款"
                    sales_match = re.search(r'(\d+)', sales_text)
                    sales_number = int(sales_match.group(1)) if sales_match else 0
                    
                    # 提取价格
                    price_text = ""
                    try:
                        price_element = item.find_element(By.XPATH, ".//*[contains(@class, 'Price') or contains(@class, 'price')]")
                        price_text = price_element.text.strip()
                    except:
                        price_text = "价格不可见"
                    
                    products.append({
                        'title': title,
                        'total_sales': sales_number,
                        'monthly_sales': sales_number / 12,
                        'price': price_text
                    })
                    
                except Exception as e:
                    print(f"提取单个商品XPath数据时出错: {str(e)}")
                    continue
                
            return products
            
        except Exception as e:
            print(f"XPath提取过程出错: {str(e)}")
            return []
    
    def extract_full_data(self, keyword, max_pages=3):
        """提取多页完整数据"""
        all_products = []
        
        for page in range(1, max_pages + 1):
            try:
                # 构建带页码的URL
                search_url = f"https://s.taobao.com/search?q={keyword}&s={(page-1)*44}"
                print(f"正在访问第{page}页: {search_url}")
                self.driver.get(search_url)
                
                # 等待页面加载 - 增加等待时间
                time.sleep(8)
                
                # 滚动页面
                self._scroll_page()
                
                # 保存页面源码以便调试
                with open(f'page_source_page{page}.html', 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                print(f"已保存第{page}页源码到 page_source_page{page}.html")
                
                # 初始化页面产品计数器
                page_products_count = 0
                
                # 尝试更多的选择器组合查找商品卡片
                card_selectors = [
                    "//a[contains(@class, 'Card--doubleCardWrapperAdapt')]",
                    "//a[contains(@class, 'doubleCardWrapperAdapt')]",
                    "//div[contains(@class, 'doubleCardWrapperAdapt')]",
                    "//div[contains(@class, 'Card--doubleCardWrapperAdapt')]",
                    "//div[contains(@class, 'common-card')]",
                    "//div[contains(@class, 'Card--pc-search-item-card')]",
                    # 淘宝现在可能使用的是更通用的选择器
                    "//div[contains(@class, 'items')]//div[@data-index]",
                    "//div[contains(@data-spm, 'item')]",
                    # 尝试更通用的链接选择器
                    "//a[contains(@href, 'item.taobao.com')]",
                    "//a[contains(@href, 'detail.tmall.com')]"
                ]
                
                cards = []
                
                # 依次尝试不同的选择器
                for selector in card_selectors:
                    try:
                        print(f"尝试使用选择器: {selector}")
                        cards = self.driver.find_elements(By.XPATH, selector)
                        if cards:
                            print(f"使用选择器 '{selector}' 找到 {len(cards)} 个商品卡片")
                            break
                    except Exception as e:
                        print(f"选择器 {selector} 失败: {str(e)}")
                
                # 如果所有选择器都失败，尝试使用更通用的方法：提取所有商品链接
                if not cards:
                    print("常规选择器未找到商品，尝试使用备用方法提取数据...")
                    # 尝试使用另一种方法提取商品信息
                    products = self._extract_alternative(keyword, page)
                    if products:
                        all_products.extend(products)
                        page_products_count = len(products)
                        print(f"备用方法在第{page}页成功提取到 {page_products_count} 个商品")
                        continue
                
                # 处理找到的卡片
                for card in cards:
                    try:
                        # 获取商品标题
                        title = None
                        
                        # 尝试多种方式获取标题
                        try:
                            title_element = card.find_element(By.XPATH, ".//*[contains(@class, 'Title') or contains(@class, 'title')]")
                            title = title_element.text
                        except:
                            try:
                                title = card.get_attribute('title')
                            except:
                                try:
                                    # 尝试使用链接的文本作为标题
                                    link_elements = card.find_elements(By.TAG_NAME, 'a')
                                    for link in link_elements:
                                        possible_title = link.text
                                        if possible_title and len(possible_title) > 5:  # 标题通常较长
                                            title = possible_title
                                            break
                                except:
                                    pass
                        
                        if not title:
                            print("跳过无标题商品")
                            continue
                        
                        # 获取销量
                        sales_text = "0人付款"
                        try:
                            # 尝试多种销量选择器
                            for sales_xpath in [
                                ".//*[contains(@class, 'Sales')]", 
                                ".//*[contains(@class, 'sales')]", 
                                ".//*[contains(text(), '人付款')]",
                                ".//*[contains(text(), '付款')]",
                                ".//*[contains(text(), '已售')]"
                            ]:
                                try:
                                    sales_element = card.find_element(By.XPATH, sales_xpath)
                                    sales_text = sales_element.text
                                    if sales_text and re.search(r'\d+', sales_text):
                                        break
                                except:
                                    pass
                        except:
                            pass
                        
                        # 提取销量数字
                        sales_match = re.search(r'(\d+)', sales_text)
                        sales_number = int(sales_match.group(1)) if sales_match else 0
                        
                        # 获取价格
                        price_text = "价格未知"
                        try:
                            # 尝试多种价格选择器
                            for price_xpath in [
                                ".//*[contains(@class, 'Price')]", 
                                ".//*[contains(@class, 'price')]",
                                ".//*[contains(text(), '¥')]"
                            ]:
                                try:
                                    price_element = card.find_element(By.XPATH, price_xpath)
                                    price_text = price_element.text
                                    if price_text and ('¥' in price_text or '￥' in price_text):
                                        break
                                except:
                                    pass
                        except:
                            pass
                        
                        # 获取商品链接
                        item_url = ""
                        try:
                            if card.tag_name == 'a':
                                item_url = card.get_attribute('href')
                            else:
                                link = card.find_element(By.TAG_NAME, 'a')
                                item_url = link.get_attribute('href')
                        except:
                            pass
                        
                        # 添加商品
                        product_data = {
                            'title': title.strip(),
                            'total_sales': sales_number,
                            'monthly_sales': sales_number / 12,
                            'price': price_text,
                        }
                        
                        if item_url:
                            product_data['url'] = item_url
                        
                        all_products.append(product_data)
                        page_products_count += 1
                        print(f"成功提取商品: {title[:20]}...")
                            
                    except Exception as e:
                        print(f"处理商品卡片时出错: {str(e)}")
                
                # 如果这一页没有找到任何商品，尝试使用另一种方法
                if page_products_count == 0:
                    print("通过卡片提取未获取商品，尝试使用传统方法提取数据...")
                    try:
                        # 尝试使用之前的方法提取数据
                        extraction_methods = [
                            ("JSON数据", self._extract_from_json),
                            ("DOM元素", self._extract_from_dom),
                            ("XPath查询", self._extract_from_xpath)
                        ]
                        
                        for method_name, method_func in extraction_methods:
                            try:
                                print(f"尝试从{method_name}中提取商品信息...")
                                page_products = method_func()
                                if page_products:
                                    print(f"成功从{method_name}中提取到 {len(page_products)} 个商品")
                                    all_products.extend(page_products)
                                    page_products_count = len(page_products)
                                    break
                            except Exception as e:
                                print(f"{method_name}提取失败: {str(e)}")
                    except Exception as e:
                        print(f"备用提取方法失败: {str(e)}")
                
                # 添加随机延迟避免被检测
                time.sleep(random.uniform(3, 6))
                
            except Exception as e:
                print(f"处理第{page}页时出错: {str(e)}")
        
        return all_products
    
    def _extract_alternative(self, keyword, page):
        """备用数据提取方法，直接从搜索结果页面提取信息"""
        try:
            # 重新加载页面
            search_url = f"https://s.taobao.com/search?q={keyword}&s={(page-1)*44}"
            self.driver.get(search_url)
            time.sleep(5)
            
            # 执行JavaScript来获取页面上所有产品数据
            js_script = """
            // 尝试收集页面上的商品数据
            var products = [];
            
            // 查找所有可能的商品卡片
            var cards = document.querySelectorAll('div[data-index], a[href*="item.taobao.com"], a[href*="detail.tmall.com"]');
            
            for (var i = 0; i < cards.length; i++) {
                var card = cards[i];
                
                // 尝试提取标题
                var title = "";
                var titleElem = card.querySelector('*[class*="Title"], *[class*="title"]');
                if (titleElem) {
                    title = titleElem.textContent.trim();
                } else if (card.title) {
                    title = card.title;
                }
                
                // 如果没有标题，跳过这个卡片
                if (!title) continue;
                
                // 尝试提取销量
                var sales = "0";
                var salesElem = card.querySelector('*[class*="Sales"], *[class*="sales"], *:contains("人付款")');
                if (salesElem) {
                    var salesText = salesElem.textContent;
                    var salesMatch = salesText.match(/\\d+/);
                    if (salesMatch) {
                        sales = salesMatch[0];
                    }
                }
                
                // 尝试提取价格
                var price = "";
                var priceElem = card.querySelector('*[class*="Price"], *[class*="price"], *:contains("¥")');
                if (priceElem) {
                    price = priceElem.textContent.trim();
                }
                
                // 尝试提取链接
                var url = "";
                if (card.tagName === 'A') {
                    url = card.href;
                } else {
                    var link = card.querySelector('a');
                    if (link) {
                        url = link.href;
                    }
                }
                
                // 添加到产品列表
                products.push({
                    title: title,
                    sales: sales,
                    price: price,
                    url: url
                });
            }
            
            return products;
            """
            
            # 执行JavaScript获取数据
            try:
                js_results = self.driver.execute_script(js_script)
                print(f"JavaScript提取到 {len(js_results)} 个商品")
                
                # 转换为我们的格式
                products = []
                for item in js_results:
                    if 'title' in item and item['title']:
                        sales_number = int(item.get('sales', '0'))
                        products.append({
                            'title': item['title'],
                            'total_sales': sales_number,
                            'monthly_sales': sales_number / 12,
                            'price': item.get('price', '价格未知'),
                            'url': item.get('url', '')
                        })
                
                return products
            except Exception as e:
                print(f"JavaScript提取失败: {str(e)}")
        
        except Exception as e:
            print(f"备用方法出错: {str(e)}")
        
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
        
        # 获取前三页的销量数据
        print("开始爬取前三页商品数据...")
        products = scraper.extract_full_data(keyword, max_pages=3)
        
        if not products:
            print("未能获取到任何商品信息")
            return
            
        # 修正月销量计算（改为除以12而非30）
        for product in products:
            if 'monthly_sales' in product:
                product['monthly_sales'] = product['total_sales'] / 12
            
        # 打印结果
        for i, product in enumerate(products, 1):
            print(f"\n商品 {i}:")
            print(f"标题: {product['title']}")
            print(f"总销量: {product['total_sales']}人付款")
            print(f"月均销量: {product['monthly_sales']:.2f}")
            if 'price' in product:
                print(f"价格: {product['price']}")
            if 'url' in product:
                print(f"链接: {product['url']}")
            if 'shop_name' in product:
                print(f"店铺: {product['shop_name']}")
            if 'location' in product:
                print(f"地点: {product['location']}")
        
        # 保存结果到文件
        with open('taobao_results.json', 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        print(f"\n已将结果保存到 taobao_results.json 文件")
        print(f"共获取到 {len(products)} 个商品数据")
            
    except Exception as e:
        print(f"程序运行出错: {str(e)}")
    finally:
        scraper.close()

if __name__ == "__main__":
    main() 