"""
Модуль для работы с API сайта Samal (добавление в корзину и оформление заказа)
"""
import requests
import logging
from typing import Dict, Optional
from config import SAMAL_BASE_URL, SAMAL_SHOP_URL, SAMAL_CHECKOUT_URL

# Настройка логирования
logger = logging.getLogger(__name__)


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
            logger.info(f"Добавление товара в корзину: product_id={product_id}, quantity={quantity}")
            
            # Сначала получаем главную страницу для установки cookies
            logger.debug(f"Получение главной страницы: {SAMAL_SHOP_URL}")
            init_response = self.session.get(SAMAL_SHOP_URL)
            logger.debug(f"Статус ответ: {init_response.status_code}")
            logger.debug(f"Cookies после инициализации: {self.session.cookies.get_dict()}")
            
            # Добавляем товар в корзину
            url = f"{SAMAL_SHOP_URL}?add-to-cart={product_id}&quantity={quantity}"
            logger.debug(f"URL добавления в корзину: {url}")
            response = self.session.get(url, allow_redirects=True)
            
            logger.info(f"Статус добавления в корзину: {response.status_code}")
            logger.debug(f"Cookies после добавления: {self.session.cookies.get_dict()}")
            
            success = response.status_code == 200
            if success:
                logger.info("✅ Товар успешно добавлен в корзину")
            else:
                logger.error(f"❌ Ошибка добавления в корзину. Статус: {response.status_code}")
            
            return success
        except Exception as e:
            logger.error(f"❌ Ошибка при добавлении в корзину: {e}", exc_info=True)
            return False
    
    def get_checkout_page(self) -> Optional[str]:
        """
        Получает HTML страницы оформления заказа
        
        Returns:
            HTML содержимое страницы или None
        """
        try:
            logger.info(f"Получение страницы checkout: {SAMAL_CHECKOUT_URL}")
            response = self.session.get(SAMAL_CHECKOUT_URL)
            
            logger.debug(f"Статус ответ checkout: {response.status_code}")
            logger.debug(f"Размер HTML: {len(response.text)} байт")
            
            if response.status_code == 200:
                logger.info("✅ Страница checkout получена успешно")
                return response.text
            else:
                logger.error(f"❌ Ошибка получения checkout. Статус: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ Ошибка при получении страницы checkout: {e}", exc_info=True)
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
            logger.debug("Извлечение nonce из HTML")
            # Ищем woocommerce-process-checkout-nonce
            import re
            match = re.search(r'name="woocommerce-process-checkout-nonce"\s+value="([^"]+)"', html)
            if match:
                nonce = match.group(1)
                logger.info(f"✅ Nonce извлечен: {nonce}")
                return nonce
            else:
                logger.error("❌ Не удалось найти nonce в HTML")
                # Попробуем другой шаблон
                match2 = re.search(r'woocommerce-process-checkout-nonce.*?value=["\']([^"\']+)["\']', html)
                if match2:
                    nonce = match2.group(1)
                    logger.info(f"✅ Nonce извлечен (альтернативный шаблон): {nonce}")
                    return nonce
                return None
        except Exception as e:
            logger.error(f"❌ Ошибка при извлечении nonce: {e}", exc_info=True)
            return None
    
    def place_order(self, user_data: Dict) -> Dict:
        """
        Оформляет заказ на сайте
        
        Args:
            user_data: Словарь с данными пользователя:
                - first_name: Имя
                - phone: Телефон
                - address: Адрес
                - comment: Комментарий
                
        Returns:
            Словарь с результатом: {'success': bool, 'message': str, 'order_id': int или None}
        """
        try:
            logger.info("Начало оформления заказа")
            logger.debug(f"Данные пользователя: {user_data}")
            # Получаем страницу checkout для получения nonce
            logger.debug("Шаг 1: Получение страницы checkout")
            checkout_html = self.get_checkout_page()
            if not checkout_html:
                logger.error("Не удалось загрузить страницу checkout")
                return {'success': False, 'message': 'Не удалось загрузить страницу оформления заказа', 'order_id': None}
            
            # Извлекаем nonce
            logger.debug("Шаг 2: Извлечение nonce")
            nonce = self.extract_nonce(checkout_html)
            if not nonce:
                logger.error("Не удалось извлечь nonce")
                return {'success': False, 'message': 'Не удалось получить nonce для оформления заказа', 'order_id': None}
            
            # Подготавливаем данные формы
            logger.debug("Шаг 3: Формирование данных заказа")
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
                '_wp_http_referer': '/?wc-ajax=update_order_review',
                'woocommerce_checkout_place_order': 'Place order',
            }
            
            # Отправляем заказ
            logger.debug("Шаг 4: Отправка заказа")
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': SAMAL_BASE_URL,
                'Referer': SAMAL_CHECKOUT_URL,
            }
            
            logger.debug(f"Headers: {headers}")
            logger.debug(f"Form data keys: {list(form_data.keys())}")
            
            response = self.session.post(
                SAMAL_CHECKOUT_URL,
                data=form_data,
                headers=headers,
                allow_redirects=False
            )
            
            logger.info(f"Статус ответ после отправки заказа: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            # Проверяем результат
            if response.status_code in [200, 302, 303]:
                # Пытаемся найти order ID в редиректе или ответе
                order_id = None
                if 'Location' in response.headers:
                    import re
                    location = response.headers['Location']
                    logger.debug(f"Redirect Location: {location}")
                    match = re.search(r'order-received/(\d+)', location)
                    if match:
                        order_id = int(match.group(1))
                        logger.info(f"Order ID найден: {order_id}")
                
                logger.info("✅ Заказ успешно оформлен!")
                return {
                    'success': True,
                    'message': 'Заказ успешно оформлен!',
                    'order_id': order_id
                }
            else:
                logger.error(f"❌ Ошибка оформления заказа. Статус: {response.status_code}")
                logger.debug(f"Response text (first 500 chars): {response.text[:500]}")
                return {
                    'success': False,
                    'message': f'Ошибка при оформлении заказа. Код ответа: {response.status_code}',
                    'order_id': None
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка при оформлении заказа: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'Произошла ошибка: {str(e)}',
                'order_id': None
            }
    
    def create_order(self, product_id: int, quantity: int, user_data: Dict) -> Dict:
        """
        Полный цикл создания заказа: добавление в корзину + оформление
        
        Args:
            product_id: ID товара
            quantity: Количество
            user_data: Данные пользователя
            
        Returns:
            Результат оформления заказа
        """
        logger.info(f"=== Создание заказа: product_id={product_id}, quantity={quantity} ===")
        
        # Добавляем товар в корзину
        logger.info("Этап 1/2: Добавление в корзину")
        if not self.add_to_cart(product_id, quantity):
            logger.error("Не удалось добавить товар в корзину")
            return {
                'success': False,
                'message': 'Не удалось добавить товар в корзину',
                'order_id': None
            }
        
        # Оформляем заказ
        logger.info("Этап 2/2: Оформление заказа")
        result = self.place_order(user_data)
        
        logger.info(f"=== Результат: {'SUCCESS' if result['success'] else 'FAILED'} ===")
        return result

