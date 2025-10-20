# 🐛 Руководство по отладке Samal Telegram Bot

## Быстрый старт отладки

### 1️⃣ Используйте тестовый скрипт

Самый простой способ проверить работу API:

```bash
python test_api.py
```

Этот скрипт покажет:
- ✅ Удалось ли добавить товар в корзину
- ✅ Получена ли страница checkout
- ✅ Извлечен ли nonce
- ✅ Какие cookies установлены
- ✅ Сохранит HTML страницу для анализа

### 2️⃣ Проверьте логи

Все модули используют детальное логирование. Вы увидите:
- Каждый HTTP запрос
- Статус коды ответов
- Cookies и headers
- Ошибки с полным traceback

## 📊 Уровни логирования

### Базовый уровень (INFO)

```python
import logging
logging.basicConfig(level=logging.INFO)

from samal_api import SamalAPI
api = SamalAPI()
```

Увидите основные события:
```
INFO - Добавление товара в корзину: product_id=224, quantity=2
INFO - ✅ Товар успешно добавлен в корзину
```

### Детальный уровень (DEBUG)

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from samal_api import SamalAPI
api = SamalAPI()
```

Увидите ВСЕ детали:
```
DEBUG - Получение главной страницы: https://samal.kz/shop/
DEBUG - Статус ответ: 200
DEBUG - Cookies после инициализации: {'session_id': 'abc123...'}
DEBUG - URL добавления в корзину: https://samal.kz/shop/?add-to-cart=224&quantity=2
```

## 🔍 Пошаговая отладка

### Проверка 1: Добавление в корзину

```python
from samal_api import SamalAPI
import logging

logging.basicConfig(level=logging.DEBUG)

api = SamalAPI()
result = api.add_to_cart(224, 2)  # Вода 18,9л, 2 шт

print(f"Результат: {result}")
print(f"Cookies: {api.session.cookies.get_dict()}")
```

**Что проверять:**
- Статус код должен быть 200
- Cookies должны установиться (PHPSESSID, woocommerce_items_in_cart и др.)

### Проверка 2: Получение страницы checkout

```python
html = api.get_checkout_page()

if html:
    # Сохраняем для анализа
    with open('checkout_debug.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    # Проверяем наличие ключевых полей
    print("billing_first_name найден:", "billing_first_name" in html)
    print("billing_phone найден:", "billing_phone" in html)
    print("billing_address_1 найден:", "billing_address_1" in html)
    print("nonce найден:", "woocommerce-process-checkout-nonce" in html)
```

**Что проверять:**
- HTML содержит форму с нужными полями
- Nonce присутствует в HTML

### Проверка 3: Извлечение nonce

```python
nonce = api.extract_nonce(html)
print(f"Nonce: {nonce}")
```

**Что проверять:**
- Nonce это строка из букв и цифр (обычно 10 символов)

### Проверка 4: Полный тест заказа (DRY RUN)

```python
# ТЕСТОВЫЕ данные - НЕ будет реального заказа
test_data = {
    'first_name': 'Test User',
    'phone': '+77771234567',
    'address': 'Test Address 1',
    'comment': 'TEST ORDER - DO NOT PROCESS'
}

# Формируем данные но НЕ отправляем
api.add_to_cart(224, 2)
html = api.get_checkout_page()
nonce = api.extract_nonce(html)

print("Всё готово к отправке!")
print(f"Nonce: {nonce}")
print(f"Данные: {test_data}")

# Раскомментируйте только когда готовы к РЕАЛЬНОМУ заказу:
# result = api.place_order(test_data)
```

## 🛠 Частые проблемы и решения

### ❌ Проблема: "Не удалось добавить товар в корзину"

**Возможные причины:**
1. Неверный product_id
2. Сайт недоступен
3. Изменилась структура URL

**Решение:**
```python
# Проверьте доступность сайта
import requests
response = requests.get("https://samal.kz/shop/")
print(f"Статус: {response.status_code}")  # Должен быть 200

# Проверьте product_id вручную на сайте
# Откройте https://samal.kz/shop/
# Найдите кнопку "В корзину" и посмотрите атрибут data-product_id
```

### ❌ Проблема: "Не удалось извлечь nonce"

**Возможные причины:**
1. Изменилась структура HTML
2. Пустая корзина (некоторые сайты не показывают checkout с пустой корзиной)

**Решение:**
```python
# Сохраните HTML для анализа
html = api.get_checkout_page()
with open('debug_checkout.html', 'w', encoding='utf-8') as f:
    f.write(html)

# Откройте файл и найдите поле nonce вручную
# Поищите: woocommerce-process-checkout-nonce
```

### ❌ Проблема: "Cookies не сохраняются"

**Решение:**
```python
# Используйте один экземпляр SamalAPI для всей сессии
api = SamalAPI()  # Создайте ОДИН раз

# НЕ создавайте новый экземпляр для каждого запроса!
# Плохо:
# api1 = SamalAPI()
# api1.add_to_cart(...)
# api2 = SamalAPI()  # Потеряны cookies!
# api2.get_checkout_page()
```

### ❌ Проблема: "Заказ не отправляется"

**Решение:**
```python
# Включите максимальное логирование
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Включите логи для requests
logging.getLogger("urllib3").setLevel(logging.DEBUG)

# Теперь запустите заказ и изучите логи
```

## 📝 Сохранение логов в файл

```python
import logging

# Настройка логирования в файл
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('samal_bot_debug.log', encoding='utf-8'),
        logging.StreamHandler()  # Также выводить в консоль
    ]
)

from samal_api import SamalAPI
# Теперь все логи сохранятся в samal_bot_debug.log
```

## 🔬 Продвинутая отладка

### Просмотр всех HTTP запросов

```python
import requests
import logging
from http.client import HTTPConnection

# Включаем debug для HTTP
HTTPConnection.debuglevel = 1

# Настраиваем логирование
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

# Теперь вы увидите ВСЕ HTTP запросы и ответы
from samal_api import SamalAPI
api = SamalAPI()
api.add_to_cart(224, 2)
```

### Использование прокси для просмотра трафика

```python
from samal_api import SamalAPI

# Используйте Burp Suite, Charles Proxy или mitmproxy
api = SamalAPI()
api.session.proxies = {
    'http': 'http://localhost:8080',
    'https': 'http://localhost:8080',
}

# Теперь весь трафик пойдет через прокси
api.add_to_cart(224, 2)
```

### Сохранение полного response

```python
api = SamalAPI()
response = api.session.get("https://samal.kz/shop/?add-to-cart=224&quantity=2")

# Сохраняем всё
with open('response_debug.txt', 'w', encoding='utf-8') as f:
    f.write(f"Status: {response.status_code}\n")
    f.write(f"Headers: {dict(response.headers)}\n")
    f.write(f"Cookies: {response.cookies.get_dict()}\n")
    f.write(f"\nBody:\n{response.text}")
```

## 🎯 Чек-лист перед запуском бота

- [ ] Токен бота добавлен в .env
- [ ] Зависимости установлены: `pip install -r requirements.txt`
- [ ] Тест добавления в корзину проходит: `python test_api.py`
- [ ] HTML страница checkout корректна
- [ ] Nonce извлекается успешно
- [ ] Cookies сохраняются между запросами

## 💡 Полезные команды

```bash
# Запуск тестов
python test_api.py

# Запуск бота с логированием в файл
python bot.py > bot.log 2>&1

# Просмотр логов в реальном времени
tail -f bot.log

# Поиск ошибок в логах
grep ERROR bot.log
grep "❌" bot.log
```

## 📞 Получить помощь

Если ничего не помогает:

1. Запустите `python test_api.py`
2. Сохраните вывод
3. Сохраните файл `checkout_page.html`
4. Сохраните логи: `samal_bot_debug.log`
5. Опишите что именно не работает

---

**Удачной отладки! 🚀**

