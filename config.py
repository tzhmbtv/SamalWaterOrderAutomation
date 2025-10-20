"""
Конфигурация для Telegram бота заказа воды Samal
"""
import os
import logging
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Настройка уровня логирования
LOG_LEVEL = os.getenv('LOG_LEVEL', 'ERROR')  # По умолчанию только ошибки
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

# Настройки для Samal API
SAMAL_BASE_URL = 'https://samal.kz'
SAMAL_SHOP_URL = f'{SAMAL_BASE_URL}/shop/'
SAMAL_CHECKOUT_URL = f'{SAMAL_BASE_URL}/checkout/'

# Настройки продуктов
DEFAULT_PRODUCT_ID = int(os.getenv('DEFAULT_PRODUCT_ID', '224'))  # Вода Samal 18,9 л
DEFAULT_QUANTITY = int(os.getenv('DEFAULT_QUANTITY', '2'))

# Доступные продукты
PRODUCTS = {
    '18.9л': {'id': 224, 'name': 'Вода Samal 18,9 л', 'price': 1700, 'min_qty': 2},
    '6л': {'id': 230, 'name': 'Вода Samal 6 л', 'price': 620, 'min_qty': 2},
    '2л': {'id': 225, 'name': 'Вода Samal 2,0 л негазированная', 'price': 325, 'pack_size': 6},
    '1.5л': {'id': 231, 'name': 'Вода Samal 1,5 л негазированная', 'price': 320, 'pack_size': 6},
    '1л': {'id': 232, 'name': 'Вода Samal 1 л негазированная', 'price': 275, 'pack_size': 6},
    '0.5л': {'id': 226, 'name': 'Вода Samal 0,5 л негазированная', 'price': 220, 'pack_size': 12},
}

# База данных
DATABASE_PATH = 'samal_bot.db'
