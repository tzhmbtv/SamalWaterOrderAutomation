"""
Скрипт для тестирования и отладки работы Samal API
"""
import logging
from samal_api import SamalAPI
from config import PRODUCTS

# Настройка детального логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Включаем логирование для requests
logging.getLogger("urllib3").setLevel(logging.DEBUG)


def test_add_to_cart():
    """Тест добавления товара в корзину"""
    print("\n" + "="*50)
    print("ТЕСТ 1: Добавление товара в корзину")
    print("="*50)
    
    api = SamalAPI()
    
    # Тестируем с водой 18,9л (product_id = 224)
    product_id = 224
    quantity = 2
    
    print(f"\n📦 Добавляем в корзину:")
    print(f"   Product ID: {product_id}")
    print(f"   Количество: {quantity}")
    
    result = api.add_to_cart(product_id, quantity)
    
    if result:
        print("✅ Товар успешно добавлен в корзину!")
        print(f"   Cookies: {api.session.cookies.get_dict()}")
    else:
        print("❌ Ошибка при добавлении товара в корзину")
    
    return api, result


def test_get_checkout_page(api):
    """Тест получения страницы checkout"""
    print("\n" + "="*50)
    print("ТЕСТ 2: Получение страницы оформления заказа")
    print("="*50)
    
    html = api.get_checkout_page()
    
    if html:
        print("✅ Страница checkout получена!")
        print(f"   Размер HTML: {len(html)} байт")
        
        # Сохраняем HTML для анализа
        with open('checkout_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("   💾 HTML сохранен в файл: checkout_page.html")
        
        # Проверяем наличие ключевых элементов
        checks = {
            'Форма checkout': 'woocommerce-checkout' in html,
            'Поле имени': 'billing_first_name' in html,
            'Поле адреса': 'billing_address_1' in html,
            'Поле телефона': 'billing_phone' in html,
            'Nonce поле': 'woocommerce-process-checkout-nonce' in html,
        }
        
        print("\n   Проверка элементов формы:")
        for check_name, check_result in checks.items():
            status = "✅" if check_result else "❌"
            print(f"   {status} {check_name}")
        
        return html
    else:
        print("❌ Не удалось получить страницу checkout")
        return None


def test_extract_nonce(api, html):
    """Тест извлечения nonce"""
    print("\n" + "="*50)
    print("ТЕСТ 3: Извлечение nonce из HTML")
    print("="*50)
    
    if not html:
        print("❌ HTML не предоставлен, пропускаем тест")
        return None
    
    nonce = api.extract_nonce(html)
    
    if nonce:
        print(f"✅ Nonce извлечен: {nonce}")
        return nonce
    else:
        print("❌ Не удалось извлечь nonce")
        return None


def test_full_order():
    """Тест полного цикла заказа (БЕЗ реальной отправки)"""
    print("\n" + "="*50)
    print("ТЕСТ 4: Полный цикл заказа (DRY RUN)")
    print("="*50)
    
    api = SamalAPI()
    
    # Тестовые данные
    product_id = 224  # Вода 18,9л
    quantity = 2
    test_user_data = {
        'first_name': 'Тестовый Пользователь',
        'phone': '+77771234567',
        'address': 'Тестовая улица 1, кв. 1',
        'comment': 'Тестовый заказ - НЕ ВЫПОЛНЯТЬ'
    }
    
    print(f"\n📋 Параметры заказа:")
    print(f"   Product ID: {product_id}")
    print(f"   Количество: {quantity}")
    print(f"   Имя: {test_user_data['first_name']}")
    print(f"   Телефон: {test_user_data['phone']}")
    print(f"   Адрес: {test_user_data['address']}")
    
    # Шаг 1: Добавляем в корзину
    print("\n🔄 Шаг 1: Добавление в корзину...")
    if not api.add_to_cart(product_id, quantity):
        print("❌ Не удалось добавить в корзину")
        return False
    print("✅ Товар добавлен в корзину")
    
    # Шаг 2: Получаем страницу checkout
    print("\n🔄 Шаг 2: Получение страницы checkout...")
    html = api.get_checkout_page()
    if not html:
        print("❌ Не удалось получить страницу checkout")
        return False
    print("✅ Страница checkout получена")
    
    # Шаг 3: Извлекаем nonce
    print("\n🔄 Шаг 3: Извлечение nonce...")
    nonce = api.extract_nonce(html)
    if not nonce:
        print("❌ Не удалось извлечь nonce")
        return False
    print(f"✅ Nonce извлечен: {nonce}")
    
    # Шаг 4: Формируем данные (БЕЗ отправки)
    print("\n🔄 Шаг 4: Формирование данных заказа...")
    form_data = {
        'billing_first_name': test_user_data['first_name'],
        'billing_address_1': test_user_data['address'],
        'billing_phone': test_user_data['phone'],
        'comments': test_user_data['comment'],
        'woocommerce-process-checkout-nonce': nonce,
    }
    
    print("✅ Данные сформированы:")
    for key, value in form_data.items():
        print(f"   {key}: {value}")
    
    print("\n⚠️  ВНИМАНИЕ: Реальная отправка НЕ выполнена!")
    print("   Для тестирования реальной отправки раскомментируйте")
    print("   строку result = api.place_order(test_user_data)")
    
    return True


def test_session_cookies():
    """Тест работы с cookies и сессией"""
    print("\n" + "="*50)
    print("ТЕСТ 5: Cookies и сессия")
    print("="*50)
    
    api = SamalAPI()
    
    # Получаем главную страницу
    print("\n🔄 Получение главной страницы...")
    response = api.session.get("https://samal.kz/shop/")
    
    print(f"✅ Статус код: {response.status_code}")
    print(f"✅ Cookies получены: {len(api.session.cookies)} шт.")
    
    for cookie in api.session.cookies:
        print(f"   🍪 {cookie.name}: {cookie.value[:50]}...")
    
    print(f"\n✅ Headers запроса:")
    for key, value in api.session.headers.items():
        print(f"   {key}: {value}")


def main():
    """Главная функция для запуска всех тестов"""
    print("\n" + "🚰"*25)
    print("ОТЛАДКА SAMAL API")
    print("🚰"*25)
    
    try:
        # Тест 1: Добавление в корзину
        api, cart_result = test_add_to_cart()
        
        if not cart_result:
            print("\n⚠️  Остановка: не удалось добавить товар в корзину")
            return
        
        # Тест 2: Получение checkout
        html = test_get_checkout_page(api)
        
        # Тест 3: Извлечение nonce
        if html:
            test_extract_nonce(api, html)
        
        # Тест 4: Полный цикл
        print("\n")
        input("Нажмите Enter для запуска теста полного цикла заказа...")
        test_full_order()
        
        # Тест 5: Сессия и cookies
        print("\n")
        input("Нажмите Enter для проверки cookies и сессии...")
        test_session_cookies()
        
        print("\n" + "="*50)
        print("✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ!")
        print("="*50)
        print("\n💡 Советы по отладке:")
        print("   1. Проверьте файл checkout_page.html на наличие всех полей")
        print("   2. Убедитесь что cookies сохраняются между запросами")
        print("   3. Проверьте что nonce извлекается корректно")
        print("   4. Логи запросов помогут найти проблемы с API")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

