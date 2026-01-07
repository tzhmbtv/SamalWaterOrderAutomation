"""
Модуль для работы с API сайта Samal (добавление в корзину и оформление заказа)
"""
import requests
import logging
import time
import json
import datetime
import re
import os
import subprocess
from typing import Dict, Optional
from config import SAMAL_BASE_URL, SAMAL_SHOP_URL, SAMAL_CHECKOUT_URL

# Импорты для Selenium (опционально, только если используется браузер)
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Настройка логирования (только для критичных ошибок)
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


class SamalAPI:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
    
    def add_to_cart(self, product_id: int, quantity: int = 2) -> bool:
        """
        Добавляет товар в корзину
        
        Args:
            product_id: ID товара на сайте
            quantity: Количество товара
            
        Returns:
            True если успешно, False если ошибка
        """
        try:
            # Получаем главную страницу для установки cookies
            init_response = self.session.get(SAMAL_SHOP_URL)
            
            # Добавляем товар в корзину
            url = f"{SAMAL_SHOP_URL}?add-to-cart={product_id}&quantity={quantity}"
            response = self.session.get(url, allow_redirects=True)
            
            success = response.status_code == 200
            if not success:
                logger.error(f"Ошибка добавления в корзину. Статус: {response.status_code}")
            
            return success
        except Exception as e:
            logger.error(f"Ошибка при добавлении в корзину: {str(e)}")
            return False
    
    def get_checkout_page(self) -> Optional[str]:
        """
        Получает HTML страницы оформления заказа
        
        Returns:
            HTML содержимое страницы или None
        """
        try:
            response = self.session.get(SAMAL_CHECKOUT_URL)
            
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"Ошибка получения checkout. Статус: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Ошибка при получении страницы checkout: {str(e)}")
            return None
    
    def extract_nonce(self, html: str) -> Optional[str]:
        """
        Извлекает nonce из HTML страницы checkout
        
        Args:
            html: HTML содержимое страницы
            
        Returns:
            Значение nonce или None
        """
        try:
            # Ищем woocommerce-process-checkout-nonce
            match = re.search(r'name="woocommerce-process-checkout-nonce"\s+value="([^"]+)"', html)
            if match:
                return match.group(1)
            else:
                # Попробуем другой шаблон
                match2 = re.search(r'woocommerce-process-checkout-nonce.*?value=["\']([^"\']+)["\']', html)
                if match2:
                    return match2.group(1)
                logger.error("Не удалось извлечь nonce из HTML")
                return None
        except Exception as e:
            logger.error(f"Ошибка при извлечении nonce: {str(e)}")
            return None
    
    def extract_payment_method(self, html: str) -> Optional[str]:
        """
        Извлекает способ оплаты из HTML страницы checkout
        
        Args:
            html: HTML содержимое страницы
            
        Returns:
            Значение способа оплаты (например, 'cheque') или None
        """
        # #region agent log
        import json
        log_data = {
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "A",
            "location": "samal_api.py:extract_payment_method",
            "message": "Начало извлечения payment_method",
            "data": {"html_length": len(html)},
            "timestamp": int(time.time() * 1000)
        }
        try:
            with open('/Users/elnurtazhimbetov/Desktop/Study/SamalTelegramBot/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
        except:
            pass
        # #endregion
        
        try:
            # Гипотеза A: Ищем скрытое поле с payment_method
            # Обычно это input type="radio" с name="payment_method" и checked атрибутом
            match = re.search(r'name=["\']payment_method["\'][^>]*value=["\']([^"\']+)["\'][^>]*checked', html, re.IGNORECASE)
            if match:
                payment_method = match.group(1)
                # #region agent log
                log_data = {
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A",
                    "location": "samal_api.py:extract_payment_method",
                    "message": "Найден payment_method через checked radio",
                    "data": {"payment_method": payment_method},
                    "timestamp": int(time.time() * 1000)
                }
                try:
                    with open('/Users/elnurtazhimbetov/Desktop/Study/SamalTelegramBot/.cursor/debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
                except:
                    pass
                # #endregion
                return payment_method
            
            # Гипотеза B: Ищем первый доступный способ оплаты (radio без checked)
            match = re.search(r'name=["\']payment_method["\'][^>]*value=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if match:
                payment_method = match.group(1)
                # #region agent log
                log_data = {
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "B",
                    "location": "samal_api.py:extract_payment_method",
                    "message": "Найден payment_method через первый radio",
                    "data": {"payment_method": payment_method},
                    "timestamp": int(time.time() * 1000)
                }
                try:
                    with open('/Users/elnurtazhimbetov/Desktop/Study/SamalTelegramBot/.cursor/debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
                except:
                    pass
                # #endregion
                return payment_method
            
            # Гипотеза C: Ищем в JavaScript данных (data-payment-method или в скриптах)
            match = re.search(r'payment[_-]?method["\']?\s*[:=]\s*["\']([^"\']+)["\']', html, re.IGNORECASE)
            if match:
                payment_method = match.group(1)
                # #region agent log
                log_data = {
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "C",
                    "location": "samal_api.py:extract_payment_method",
                    "message": "Найден payment_method через JavaScript",
                    "data": {"payment_method": payment_method},
                    "timestamp": int(time.time() * 1000)
                }
                try:
                    with open('/Users/elnurtazhimbetov/Desktop/Study/SamalTelegramBot/.cursor/debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
                except:
                    pass
                # #endregion
                return payment_method
            
            # Гипотеза D: По умолчанию используем 'cheque' (Чековые платежи)
            # Это стандартный способ оплаты для WooCommerce при доставке
            # #region agent log
            log_data = {
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "D",
                "location": "samal_api.py:extract_payment_method",
                "message": "Используем значение по умолчанию cheque",
                "data": {"payment_method": "cheque", "reason": "Не найден в HTML"},
                "timestamp": int(time.time() * 1000)
            }
            try:
                with open('/Users/elnurtazhimbetov/Desktop/Study/SamalTelegramBot/.cursor/debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
            except:
                pass
            # #endregion
            return 'cheque'  # Значение по умолчанию для "Чековые платежи"
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении payment_method: {str(e)}")
            # #region agent log
            log_data = {
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "E",
                "location": "samal_api.py:extract_payment_method",
                "message": "Ошибка при извлечении, используем cheque по умолчанию",
                "data": {"error": str(e), "payment_method": "cheque"},
                "timestamp": int(time.time() * 1000)
            }
            try:
                with open('/Users/elnurtazhimbetov/Desktop/Study/SamalTelegramBot/.cursor/debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
            except:
                pass
            # #endregion
            return 'cheque'  # Fallback значение
    
    def extract_order_id(self, html: str, location_header: Optional[str] = None) -> Optional[int]:
        """
        Извлекает ID заказа из HTML ответа или Location header
        
        Args:
            html: HTML содержимое страницы ответа
            location_header: Значение Location header (если есть редирект)
            
        Returns:
            ID заказа или None
        """
        # Сначала проверяем Location header
        if location_header:
            match = re.search(r'order-received/(\d+)', location_header)
            if match:
                order_id = int(match.group(1))
                print(f"✅ Order ID найден в Location header: {order_id}")
                return order_id
        
        # Ищем в HTML несколько способов:
        
        # 1. В URL в ссылках (order-received/189575/)
        match = re.search(r'order-received/(\d+)', html)
        if match:
            order_id = int(match.group(1))
            print(f"✅ Order ID найден в URL: {order_id}")
            return order_id
        
        # 2. В тексте "Номер заказа: <strong>189575</strong>"
        match = re.search(r'Номер заказа[^<]*<strong>(\d+)</strong>', html, re.IGNORECASE)
        if match:
            order_id = int(match.group(1))
            print(f"✅ Order ID найден в тексте 'Номер заказа': {order_id}")
            return order_id
        
        # 3. В JavaScript dataLayer (transaction_id:"189575")
        match = re.search(r'"transaction_id"\s*:\s*"(\d+)"', html)
        if match:
            order_id = int(match.group(1))
            print(f"✅ Order ID найден в transaction_id: {order_id}")
            return order_id
        
        # 4. В классе woocommerce-order-overview__order
        match = re.search(r'woocommerce-order-overview__order[^>]*>.*?<strong>(\d+)</strong>', html, re.DOTALL)
        if match:
            order_id = int(match.group(1))
            print(f"✅ Order ID найден в order-overview: {order_id}")
            return order_id
        
        print("❌ Order ID не найден в ответе")
        return None
    
    def place_order(self, user_data: Dict, use_browser: bool = False, product_id: Optional[int] = None, quantity: Optional[int] = None) -> Dict:
        """
        Оформляет заказ на сайте
        
        Args:
            user_data: Словарь с данными пользователя:
                - first_name: Имя
                - phone: Телефон
                - address: Адрес
                - comment: Комментарий
            use_browser: Если True, использует реальный браузер (Selenium), иначе HTTP-запросы
                
        Returns:
            Словарь с результатом: {'success': bool, 'message': str, 'order_id': int или None}
        """
        if use_browser and SELENIUM_AVAILABLE:
            return self._place_order_with_browser(user_data, product_id=product_id, quantity=quantity)
        else:
            if use_browser and not SELENIUM_AVAILABLE:
                print("⚠️  Selenium не установлен, использую HTTP-запросы")
            return self._place_order_with_requests(user_data)
    
    def _add_to_cart_with_browser(self, driver, product_id: int, quantity: int) -> bool:
        """
        Добавляет товар в корзину через браузер
        
        Args:
            driver: WebDriver экземпляр
            product_id: ID товара
            quantity: Количество
            
        Returns:
            True если успешно
        """
        try:
            # Открываем страницу товара или добавляем через URL
            add_to_cart_url = f"{SAMAL_SHOP_URL}?add-to-cart={product_id}&quantity={quantity}"
            print(f"🛒 Добавляю товар {product_id} в корзину (количество: {quantity})...")
            driver.get(add_to_cart_url)
            time.sleep(2)  # Даем время на добавление в корзину
            print("✅ Товар добавлен в корзину")
            return True
        except Exception as e:
            print(f"⚠️  Ошибка при добавлении товара в корзину: {str(e)}")
            return False
    
    def _place_order_with_browser(self, user_data: Dict, product_id: Optional[int] = None, quantity: Optional[int] = None) -> Dict:
        """
        Оформляет заказ используя реальный браузер (Selenium)
        Браузер будет видимым, чтобы можно было следить за процессом
        """
        driver = None
        try:
            print("🌐 Запускаю браузер для оформления заказа...")
            
            # Настройка Chrome с видимым окном
            chrome_options = Options()
            # НЕ используем headless режим - браузер будет видимым
            # chrome_options.add_argument('--headless')  # Закомментировано для видимости
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Создаем драйвер (webdriver-manager автоматически скачает нужный драйвер)
            driver = None
            try:
                # Сначала пробуем использовать системный ChromeDriver (если установлен через Homebrew)
                try:
                    result = subprocess.run(['which', 'chromedriver'], capture_output=True, text=True)
                    if result.returncode == 0:
                        chromedriver_path = result.stdout.strip()
                        print(f"✅ Найден системный ChromeDriver: {chromedriver_path}")
                        service = Service(chromedriver_path)
                        driver = webdriver.Chrome(service=service, options=chrome_options)
                    else:
                        raise FileNotFoundError("ChromeDriver не найден в PATH")
                except (FileNotFoundError, Exception) as e:
                    # Если системный не найден, пробуем webdriver-manager
                    try:
                        from webdriver_manager.chrome import ChromeDriverManager  # type: ignore
                        driver_path = ChromeDriverManager().install()
                        # Проверяем, что это файл, а не директория
                        if os.path.isdir(driver_path):
                            # Ищем chromedriver внутри директории
                            chromedriver_executable = os.path.join(driver_path, 'chromedriver')
                            if not os.path.exists(chromedriver_executable):
                                # Пробуем найти в поддиректориях
                                for root, dirs, files in os.walk(driver_path):
                                    if 'chromedriver' in files:
                                        chromedriver_executable = os.path.join(root, 'chromedriver')
                                        break
                            if os.path.exists(chromedriver_executable):
                                # Делаем файл исполняемым (на macOS/Linux)
                                os.chmod(chromedriver_executable, 0o755)
                                service = Service(chromedriver_executable)
                                driver = webdriver.Chrome(service=service, options=chrome_options)
                            else:
                                raise FileNotFoundError(f"Исполняемый файл chromedriver не найден в {driver_path}")
                        else:
                            # Это уже файл
                            os.chmod(driver_path, 0o755)
                            service = Service(driver_path)
                            driver = webdriver.Chrome(service=service, options=chrome_options)
                    except ImportError:
                        # Если webdriver-manager не установлен, пробуем без указания пути
                        print("⚠️  webdriver-manager не установлен, пробую использовать ChromeDriver из PATH")
                        driver = webdriver.Chrome(options=chrome_options)
            except Exception as e:
                error_msg = str(e)
                print(f"⚠️  Ошибка при создании драйвера: {error_msg}")
                print("\n💡 Решения:")
                print("   1. Установите ChromeDriver через Homebrew: brew install chromedriver")
                print("   2. Или установите webdriver-manager: pip install webdriver-manager")
                print("   3. Или скачайте ChromeDriver вручную с https://chromedriver.chromium.org/")
                raise Exception(f"Не удалось создать WebDriver: {error_msg}")
            
            driver.maximize_window()
            print("✅ Браузер запущен и готов к работе")
            
            # Шаг 1: Добавляем товар в корзину (если указаны product_id и quantity)
            if product_id and quantity:
                if not self._add_to_cart_with_browser(driver, product_id, quantity):
                    return {
                        'success': False,
                        'message': 'Не удалось добавить товар в корзину через браузер',
                        'order_id': None
                    }
            
            # Шаг 2: Открываем страницу checkout
            print(f"📄 Открываю страницу оформления заказа: {SAMAL_CHECKOUT_URL}")
            driver.get(SAMAL_CHECKOUT_URL)
            
            # Ждем загрузки страницы
            wait = WebDriverWait(driver, 30)
            print("⏳ Ожидаю загрузки формы...")
            
            # Ждем появления формы checkout
            wait.until(EC.presence_of_element_located((By.ID, "billing_first_name")))
            print("✅ Форма загружена")
            
            # Шаг 3: Заполняем форму
            print("📝 Заполняю форму заказа...")
            
            # Имя
            name_field = driver.find_element(By.ID, "billing_first_name")
            name_field.clear()
            name_field.send_keys(user_data.get('first_name', ''))
            print(f"   ✓ Имя: {user_data.get('first_name', '')}")
            
            # Адрес
            address_field = driver.find_element(By.ID, "billing_address_1")
            address_field.clear()
            address_field.send_keys(user_data.get('address', ''))
            print(f"   ✓ Адрес: {user_data.get('address', '')}")
            
            # Телефон
            phone_field = driver.find_element(By.ID, "billing_phone")
            phone_field.clear()
            phone_field.send_keys(user_data.get('phone', ''))
            print(f"   ✓ Телефон: {user_data.get('phone', '')}")
            
            # Комментарий (если есть поле)
            try:
                comment_field = driver.find_element(By.ID, "order_comments")
                comment_field.clear()
                comment_text = user_data.get('comment', '')
                if comment_text:
                    comment_field.send_keys(comment_text)
                    print(f"   ✓ Комментарий: {comment_text}")
            except NoSuchElementException:
                print("   ⚠️  Поле комментария не найдено, пропускаю")
            
            # Небольшая задержка для визуализации
            time.sleep(1)
            
            # Шаг 4: Нажимаем кнопку "Подтвердить заказ"
            print("🔘 Нажимаю кнопку 'Подтвердить заказ'...")
            submit_button = wait.until(EC.element_to_be_clickable((By.ID, "place_order")))
            submit_button.click()
            print("✅ Кнопка нажата, ожидаю обработку заказа...")
            
            # Шаг 5: Ждем редиректа на страницу подтверждения или появления результата
            # WooCommerce обычно редиректит на order-received страницу
            print("⏳ Ожидаю редирект на страницу подтверждения...")
            
            # Ждем либо изменения URL (редирект), либо появления сообщения об ошибке
            max_wait_time = 30
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                current_url = driver.current_url
                
                # Проверяем, произошел ли редирект на страницу подтверждения
                if 'order-received' in current_url or 'order-received' in driver.page_source:
                    print(f"✅ Редирект на страницу подтверждения: {current_url}")
                    break
                
                # Проверяем наличие ошибок
                try:
                    error_elements = driver.find_elements(By.CSS_SELECTOR, ".woocommerce-error, .woocommerce-notice--error")
                    if error_elements:
                        error_text = error_elements[0].text
                        print(f"❌ Обнаружена ошибка: {error_text}")
                        # Сохраняем HTML для анализа
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"order_error_{timestamp}.html"
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(driver.page_source)
                        return {
                            'success': False,
                            'message': f'Ошибка при оформлении заказа: {error_text}\nHTML сохранен в {filename}',
                            'order_id': None
                        }
                except:
                    pass
                
                time.sleep(0.5)
            else:
                print("⚠️  Превышено время ожидания редиректа")
            
            # Шаг 6: Извлекаем order_id из URL или HTML
            final_url = driver.current_url
            page_source = driver.page_source
            
            print(f"📄 Финальный URL: {final_url}")
            print(f"📄 Размер HTML: {len(page_source)} символов")
            
            # Сохраняем HTML в файл
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"order_response_{timestamp}.html"
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"<!-- Response от {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -->\n")
                    f.write(f"<!-- URL: {final_url} -->\n\n")
                    f.write(page_source)
                print(f"💾 HTML ответ сохранен в файл: {filename}")
            except Exception as e:
                print(f"⚠️  Не удалось сохранить HTML ответ: {str(e)}")
                filename = None
            
            # Извлекаем order_id
            order_id = self.extract_order_id(page_source, final_url)
            
            # Формируем ответ
            response_info = f"\n📡 Информация о заказе:\n"
            response_info += f"URL: {final_url}\n"
            if filename:
                response_info += f"💾 HTML сохранен в файл: {filename}\n"
            
            if order_id:
                message = f'✅ Заказ успешно оформлен!\nНомер заказа: {order_id}\n' + response_info
                return {
                    'success': True,
                    'message': message,
                    'order_id': order_id
                }
            else:
                message = f'❌ Не удалось получить номер заказа.\n'
                message += f'URL: {final_url}\n'
                message += f'Проверьте файл {filename if filename else "браузер"} для деталей.\n'
                message += response_info
                return {
                    'success': False,
                    'message': message,
                    'order_id': None
                }
                
        except TimeoutException as e:
            error_msg = f"Превышено время ожидания: {str(e)}"
            print(f"❌ {error_msg}")
            if driver:
                # Сохраняем текущее состояние страницы
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"order_timeout_{timestamp}.html"
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(driver.page_source)
                    error_msg += f"\n💾 HTML сохранен в файл: {filename}"
                except:
                    pass
            return {
                'success': False,
                'message': error_msg,
                'order_id': None
            }
        except Exception as e:
            error_msg = f"Ошибка при оформлении заказа через браузер: {str(e)}"
            print(f"❌ {error_msg}")
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'message': error_msg,
                'order_id': None
            }
        finally:
            # НЕ закрываем браузер автоматически, чтобы пользователь мог видеть результат
            # Пользователь может закрыть его вручную или мы можем добавить опцию для этого
            print("ℹ️  Браузер остается открытым для просмотра результата.")
            print("   Закройте его вручную когда закончите просмотр.")
            # Если нужно автоматически закрывать, раскомментируйте:
            # if driver:
            #     input("Нажмите Enter чтобы закрыть браузер...")
            #     driver.quit()
    
    def _place_order_with_requests(self, user_data: Dict) -> Dict:
        """
        Оформляет заказ используя HTTP-запросы (старый метод)
        """
        try:
            # Получаем страницу checkout для получения nonce
            checkout_html = self.get_checkout_page()
            if not checkout_html:
                return {'success': False, 'message': 'Не удалось загрузить страницу оформления заказа', 'order_id': None}
            
            # Извлекаем nonce
            nonce = self.extract_nonce(checkout_html)
            if not nonce:
                return {'success': False, 'message': 'Не удалось получить nonce для оформления заказа', 'order_id': None}
            
            # Извлекаем способ оплаты
            payment_method = self.extract_payment_method(checkout_html)
            # #region agent log
            import json
            log_data = {
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A",
                "location": "samal_api.py:_place_order_with_requests",
                "message": "Извлечен payment_method из HTML",
                "data": {"payment_method": payment_method, "nonce": nonce[:10] + "..." if nonce else None},
                "timestamp": int(time.time() * 1000)
            }
            try:
                with open('/Users/elnurtazhimbetov/Desktop/Study/SamalTelegramBot/.cursor/debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
            except:
                pass
            # #endregion
            
            # Подготавливаем данные формы
            form_data = {
                # WooCommerce Order Attribution (скрытые поля)
                'wc_order_attribution_source_type': 'organic',
                'wc_order_attribution_referrer': 'https://www.google.com/',
                'wc_order_attribution_utm_campaign': '(none)',
                'wc_order_attribution_utm_source': 'google',
                'wc_order_attribution_utm_medium': 'organic',
                'wc_order_attribution_utm_content': '(none)',
                'wc_order_attribution_utm_id': '(none)',
                'wc_order_attribution_utm_term': '(none)',
                'wc_order_attribution_utm_source_platform': '(none)',
                'wc_order_attribution_utm_creative_format': '(none)',
                'wc_order_attribution_utm_marketing_tactic': '(none)',
                'wc_order_attribution_session_entry': 'https://samal.kz/',
                'wc_order_attribution_session_start_time': '2025-10-20 20:11:05',
                'wc_order_attribution_session_pages': '11',
                'wc_order_attribution_session_count': '1',
                'wc_order_attribution_user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
                
                # Основные данные
                'billing_first_name': user_data.get('first_name', ''),
                'billing_address_1': user_data.get('address', ''),
                'billing_phone': user_data.get('phone', ''),
                'comments': user_data.get('comment', ''),
                'delivery': '',  # Пустое поле согласно форме
                'order_comments': 'Доставка осуществляется только по г. Алматы',
                
                # WooCommerce данные
                'woocommerce-process-checkout-nonce': nonce,
                '_wp_http_referer': '/checkout/',
                'woocommerce_checkout_place_order': '1',  # Значение кнопки "Подтвердить заказ"
                'payment_method': payment_method if payment_method else 'cheque',  # Способ оплаты
            }
            
            # #region agent log
            log_data = {
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A",
                "location": "samal_api.py:_place_order_with_requests",
                "message": "Данные формы перед отправкой",
                "data": {
                    "form_keys": list(form_data.keys()),
                    "payment_method": form_data.get('payment_method'),
                    "has_payment_method": 'payment_method' in form_data
                },
                "timestamp": int(time.time() * 1000)
            }
            try:
                with open('/Users/elnurtazhimbetov/Desktop/Study/SamalTelegramBot/.cursor/debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
            except:
                pass
            # #endregion
            
            # Эмулируем AJAX-запрос браузера на кнопку "Подтвердить заказ"
            # WooCommerce использует AJAX endpoint для обработки checkout
            ajax_url = f"{SAMAL_BASE_URL}/?wc-ajax=checkout"
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': SAMAL_BASE_URL,
                'Referer': SAMAL_CHECKOUT_URL,
                'X-Requested-With': 'XMLHttpRequest',  # Важно: указываем, что это AJAX-запрос
                'Accept': 'application/json, text/javascript, */*; q=0.01',
            }
            
            print(f"📤 Отправляю AJAX-запрос на: {ajax_url}")
            print(f"   Эмулирую нажатие кнопки 'Подтвердить заказ' (id=place_order)")
            
            response = self.session.post(
                ajax_url,
                data=form_data,
                headers=headers,
                allow_redirects=False
            )
            
            print(f"📡 Ответ получен. Status: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('Content-Type', 'не указан')}")
            
            # WooCommerce AJAX endpoint возвращает JSON с redirect URL или ошибками
            final_url = None
            redirect_from_json = None
            
            # Проверяем, является ли ответ JSON
            content_type = response.headers.get('Content-Type', '').lower()
            response_text = response.text
            
            if 'application/json' in content_type or response_text.strip().startswith('{'):
                print("📄 Ответ в формате JSON, парсю...")
                try:
                    json_response = json.loads(response_text)
                    print(f"   JSON ответ: {json.dumps(json_response, ensure_ascii=False, indent=2)[:500]}")
                    
                    # WooCommerce возвращает redirect в поле 'redirect' или 'data.redirect'
                    if 'redirect' in json_response:
                        redirect_from_json = json_response['redirect']
                    elif 'data' in json_response and isinstance(json_response['data'], dict) and 'redirect' in json_response['data']:
                        redirect_from_json = json_response['data']['redirect']
                    elif 'messages' in json_response or 'fragments' in json_response:
                        # Возможно, есть ошибки валидации
                        print("⚠️  Возможны ошибки валидации в ответе")
                        if 'messages' in json_response:
                            print(f"   Сообщения: {json_response['messages']}")
                except json.JSONDecodeError as e:
                    print(f"⚠️  Не удалось распарсить JSON: {str(e)}")
                    print(f"   Текст ответа (первые 500 символов): {response_text[:500]}")
            
            # Определяем финальный URL для редиректа
            # Приоритет: 1) JSON redirect, 2) Location header, 3) текущий URL
            if redirect_from_json:
                final_url = redirect_from_json
                print(f"📍 Редирект из JSON: {final_url}")
            elif 'Location' in response.headers:
                location = response.headers['Location']
                # Если относительный URL, делаем его абсолютным
                if location.startswith('/'):
                    final_url = f"{SAMAL_BASE_URL}{location}"
                elif location.startswith('http'):
                    final_url = location
                else:
                    final_url = f"{SAMAL_BASE_URL}/{location}"
                print(f"📍 Редирект из Location header: {final_url}")
            
            # Ждем небольшую задержку для обработки на сервере
            if final_url:
                print("⏳ Ожидаю обработку заказа на сервере (2 секунды)...")
                time.sleep(2)
            
            # Делаем запрос на финальную страницу подтверждения заказа
            final_response = response
            if final_url:
                print(f"🔄 Запрашиваю финальную страницу подтверждения: {final_url}")
                try:
                    final_response = self.session.get(final_url, allow_redirects=True, timeout=30)
                    print(f"✅ Финальная страница получена. Status: {final_response.status_code}")
                    print(f"   URL: {final_response.url}")
                except Exception as e:
                    print(f"⚠️  Ошибка при запросе финальной страницы: {str(e)}")
                    print(f"   Использую первый ответ")
            else:
                print("⚠️  Редирект не найден в ответе. Возможно, заказ не был создан или есть ошибки.")
            
            # Сохраняем полный HTML ответ в файл
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"order_response_{timestamp}.html"
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"<!-- Response от {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -->\n")
                    f.write(f"<!-- Первый Status Code: {response.status_code} -->\n")
                    f.write(f"<!-- Финальный Status Code: {final_response.status_code} -->\n")
                    f.write(f"<!-- Первый URL: {response.url} -->\n")
                    f.write(f"<!-- Финальный URL: {final_response.url} -->\n")
                    f.write(f"<!-- Headers:\n")
                    for key, value in final_response.headers.items():
                        f.write(f"  {key}: {value}\n")
                    f.write(f"-->\n\n")
                    f.write(final_response.text)
                print(f"💾 HTML ответ сохранен в файл: {filename}")
            except Exception as e:
                print(f"⚠️  Не удалось сохранить HTML ответ: {str(e)}")
                filename = None  # Если не удалось сохранить, устанавливаем None
            
            # Выводим полный response в терминал
            print("\n" + "="*80)
            print("📡 ПОЛНЫЙ RESPONSE ОТ СЕРВЕРА:")
            print("="*80)
            print(f"Первый Status Code: {response.status_code}")
            print(f"Финальный Status Code: {final_response.status_code}")
            print(f"\nПервый URL: {response.url}")
            print(f"Финальный URL: {final_response.url}")
            print(f"\nHeaders финального ответа:")
            for key, value in final_response.headers.items():
                print(f"  {key}: {value}")
            print(f"\nResponse Text (первые 2000 символов):")
            print("-"*80)
            response_text_preview = final_response.text[:2000] if len(final_response.text) > 2000 else final_response.text
            print(response_text_preview)
            if len(final_response.text) > 2000:
                print(f"\n... (еще {len(final_response.text) - 2000} символов)")
            print("="*80 + "\n")
            
            # Формируем детальную информацию о response для пользователя
            response_info = f"\n📡 Ответ сервера:\n"
            response_info += f"Первый статус: {response.status_code}\n"
            response_info += f"Финальный статус: {final_response.status_code}\n"
            response_info += f"Финальный URL: {final_response.url}\n"
            
            if 'Location' in response.headers:
                response_info += f"Редирект: {response.headers['Location']}\n"
            
            if filename:
                response_info += f"\n💾 Полный HTML ответ сохранен в файл: {filename}\n"
            response_info += f"Размер ответа: {len(final_response.text)} символов"
            
            # Берем первые 500 символов текста для сообщения пользователю
            response_text_short = final_response.text[:500] if len(final_response.text) > 500 else final_response.text
            response_info += f"\n\nТекст ответа (первые 500 символов):\n{response_text_short}"
            if len(final_response.text) > 500:
                response_info += f"\n... (полный ответ в файле {filename})"
            
            # Извлекаем order ID из финального ответа
            location_header = final_response.headers.get('Location', None) or response.headers.get('Location', None)
            order_id = self.extract_order_id(final_response.text, location_header)
            
            # Заказ считается успешным ТОЛЬКО если найден order_id
            if order_id:
                message = f'✅ Заказ успешно оформлен!\nНомер заказа: {order_id}\n' + response_info
                return {
                    'success': True,
                    'message': message,
                    'order_id': order_id
                }
            else:
                # Даже если статус код 200/302/303, но order_id не найден - это ошибка
                logger.error(f"Order ID не найден в ответе. Статус: {response.status_code}")
                message = f'❌ Не удалось получить номер заказа.\n'
                message += f'Статус ответа: {response.status_code}\n'
                message += f'Возможно заказ не был создан. Проверьте файл {filename if filename else "ответ"} для деталей.\n'
                message += response_info
                return {
                    'success': False,
                    'message': message,
                    'order_id': None
                }
                
        except Exception as e:
            logger.error(f"Ошибка при оформлении заказа: {str(e)}")
            return {
                'success': False,
                'message': f'Произошла ошибка: {str(e)}',
                'order_id': None
            }
    
    def create_order(self, product_id: int, quantity: int, user_data: Dict, use_browser: bool = False) -> Dict:
        """
        Полный цикл создания заказа: добавление в корзину + оформление
        
        Args:
            product_id: ID товара
            quantity: Количество
            user_data: Данные пользователя
            use_browser: Если True, использует реальный браузер для оформления заказа
            
        Returns:
            Результат оформления заказа
        """
        if use_browser and SELENIUM_AVAILABLE:
            # Если используем браузер, добавляем товар в корзину тоже через браузер
            # (внутри place_order)
            return self.place_order(user_data, use_browser=True, product_id=product_id, quantity=quantity)
        else:
            # Если используем HTTP, добавляем товар в корзину через HTTP
            if not self.add_to_cart(product_id, quantity):
                return {
                    'success': False,
                    'message': 'Не удалось добавить товар в корзину',
                    'order_id': None
                }
            # Оформляем заказ через HTTP
            return self.place_order(user_data, use_browser=False)

