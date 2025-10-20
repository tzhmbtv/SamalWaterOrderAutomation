"""
Telegram бот для заказа воды Samal
"""
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, PRODUCTS, DEFAULT_PRODUCT_ID, DEFAULT_QUANTITY
from database import Database
from samal_api import SamalAPI

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния разговора
(CHOOSING_ACTION, CHOOSING_PRODUCT, CHOOSING_QUANTITY, ENTERING_NAME, ENTERING_PHONE, 
 ENTERING_ADDRESS, ENTERING_COMMENT, CONFIRMING_ORDER) = range(8)

# Инициализация базы данных
db = Database()


def get_main_menu_keyboard(has_user_data=False):
    """Создает главное меню с кнопками"""
    keyboard = []
    
    if has_user_data:
        # Если есть сохраненные данные - показываем кнопку быстрого заказа
        keyboard.append([KeyboardButton("🚰 Быстрый заказ")])
    
    keyboard.append([KeyboardButton("📦 Новый заказ")])
    keyboard.append([KeyboardButton("👤 Мой профиль"), KeyboardButton("📜 История заказов")])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /start"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Проверяем есть ли пользователь в базе
    user_data = db.get_user(chat_id)
    has_data = user_data and user_data.get('phone')
    
    welcome_text = f"👋 Здравствуйте, {user.first_name}!\n\n"
    welcome_text += "🚰 Добро пожаловать в бот заказа воды Samal!\n\n"
    
    if has_data:
        welcome_text += "✅ Ваши данные уже сохранены.\n"
        welcome_text += "Используйте кнопку '🚰 Быстрый заказ' для мгновенного заказа!\n\n"
    else:
        welcome_text += "Для первого заказа мне понадобятся ваши данные.\n"
        welcome_text += "После этого вы сможете заказывать одной кнопкой! 🚀\n\n"
    
    # Показываем главное меню
    keyboard = get_main_menu_keyboard(has_data)
    
    await update.message.reply_text(welcome_text, reply_markup=keyboard)
    return ConversationHandler.END


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик главного меню"""
    text = update.message.text
    chat_id = update.effective_chat.id
    user_data = db.get_user(chat_id)
    has_data = user_data and user_data.get('phone')
    
    if text == "🚰 Быстрый заказ":
        if not has_data:
            await update.message.reply_text(
                "❌ Сначала нужно оформить первый заказ и сохранить данные.\n"
                "Нажмите '📦 Новый заказ'"
            )
            return ConversationHandler.END
        
        # Показываем последний заказ или стандартный продукт
        recent_orders = db.get_user_orders(chat_id, limit=1)
        
        if recent_orders and len(recent_orders) > 0:
            last_order = recent_orders[0]
            # Находим продукт по имени
            selected_product = None
            for key, product in PRODUCTS.items():
                if product['name'] == last_order['product_name']:
                    selected_product = product
                    context.user_data['product'] = product
                    context.user_data['product_key'] = key
                    context.user_data['quantity'] = last_order['quantity']
                    break
        
        if not selected_product:
            # Используем продукт по умолчанию
            context.user_data['product'] = PRODUCTS['18.9л']
            context.user_data['product_key'] = '18.9л'
            context.user_data['quantity'] = DEFAULT_QUANTITY
        
        # Сразу показываем подтверждение
        return await show_order_confirmation(update, context, user_data)
    
    elif text == "📦 Новый заказ":
        return await order_start(update, context)
    
    elif text == "👤 Мой профиль":
        await profile(update, context)
        return ConversationHandler.END
    
    elif text == "📜 История заказов":
        await history(update, context)
        return ConversationHandler.END
    
    else:
        # Неизвестная команда
        keyboard = get_main_menu_keyboard(has_data)
        await update.message.reply_text(
            "Выберите действие из меню:",
            reply_markup=keyboard
        )
        return ConversationHandler.END


async def order_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса заказа"""
    chat_id = update.effective_chat.id
    user_data = db.get_user(chat_id)
    
    # Создаем клавиатуру с продуктами
    keyboard = []
    for key, product in PRODUCTS.items():
        button_text = f"{product['name']} - {product['price']}₸"
        keyboard.append([KeyboardButton(button_text)])
    
    keyboard.append([KeyboardButton("❌ Отменить")])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "🚰 Выберите продукт для заказа:",
        reply_markup=reply_markup
    )
    
    return CHOOSING_PRODUCT


async def product_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора продукта"""
    user_choice = update.message.text
    
    if user_choice == "❌ Отменить":
        return await cancel(update, context)
    
    # Находим выбранный продукт
    selected_product = None
    for key, product in PRODUCTS.items():
        if product['name'] in user_choice:
            selected_product = product
            context.user_data['product'] = product
            context.user_data['product_key'] = key
            break
    
    if not selected_product:
        await update.message.reply_text(
            "❌ Не удалось распознать продукт. Попробуйте еще раз или /cancel для отмены."
        )
        return CHOOSING_PRODUCT
    
    # Запрашиваем количество
    min_qty = selected_product.get('min_qty', 2)
    pack_size = selected_product.get('pack_size', None)
    
    qty_text = f"📦 Вы выбрали: {selected_product['name']}\n\n"
    
    if pack_size:
        qty_text += f"Минимальный заказ - 2 упаковки (1 упаковка = {pack_size} ед.)\n"
        qty_text += f"Введите количество упаковок (минимум 2):"
    else:
        qty_text += f"Минимальный заказ - {min_qty} бутыли\n"
        qty_text += f"Введите количество бутылей:"
    
    await update.message.reply_text(qty_text, reply_markup=ReplyKeyboardRemove())
    
    return CHOOSING_QUANTITY


async def quantity_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода количества"""
    try:
        quantity = int(update.message.text)
        product = context.user_data['product']
        
        min_qty = product.get('min_qty', 2)
        
        if quantity < min_qty:
            await update.message.reply_text(
                f"❌ Минимальное количество для заказа - {min_qty}. Попробуйте снова:"
            )
            return CHOOSING_QUANTITY
        
        context.user_data['quantity'] = quantity
        
        # Проверяем есть ли данные пользователя
        chat_id = update.effective_chat.id
        user_data = db.get_user(chat_id)
        
        if user_data and user_data.get('phone') and user_data.get('address'):
            # Данные есть, показываем подтверждение
            return await show_order_confirmation(update, context, user_data)
        else:
            # Данных нет, запрашиваем
            await update.message.reply_text(
                "👤 Введите ваше имя:"
            )
            return ENTERING_NAME
            
    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите корректное число:"
        )
        return CHOOSING_QUANTITY


async def name_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода имени"""
    context.user_data['first_name'] = update.message.text
    
    await update.message.reply_text(
        "📱 Введите ваш телефон для связи (например: +77011234567):"
    )
    
    return ENTERING_PHONE


async def phone_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода телефона"""
    phone = update.message.text
    context.user_data['phone'] = phone
    
    await update.message.reply_text(
        "🏠 Введите адрес доставки:\n"
        "(например: Маркова 61/1, 1 подъезд, 13 этаж, 28 квартира, ЖК Алатау)"
    )
    
    return ENTERING_ADDRESS


async def address_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода адреса"""
    address = update.message.text
    context.user_data['address'] = address
    
    keyboard = [
        [KeyboardButton("Без комментария")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "💬 Введите комментарий к заказу (или нажмите 'Без комментария'):",
        reply_markup=reply_markup
    )
    
    return ENTERING_COMMENT


async def comment_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода комментария"""
    comment = update.message.text
    if comment == "Без комментария":
        comment = ""
    
    context.user_data['comment'] = comment
    
    # Сохраняем данные пользователя
    chat_id = update.effective_chat.id
    db.save_user(
        chat_id,
        first_name=context.user_data.get('first_name', ''),
        phone=context.user_data.get('phone', ''),
        address=context.user_data.get('address', ''),
        comment=comment
    )
    
    # Показываем подтверждение
    user_data = {
        'first_name': context.user_data.get('first_name', ''),
        'phone': context.user_data.get('phone', ''),
        'address': context.user_data.get('address', ''),
        'comment': comment
    }
    
    return await show_order_confirmation(update, context, user_data)


async def show_order_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict) -> int:
    """Показывает подтверждение заказа"""
    product = context.user_data['product']
    quantity = context.user_data['quantity']
    
    # Рассчитываем стоимость
    pack_size = product.get('pack_size', 1)
    total_items = quantity * pack_size if pack_size > 1 else quantity
    total_price = product['price'] * quantity
    
    confirmation_text = "📋 Подтверждение заказа:\n\n"
    confirmation_text += f"🚰 Товар: {product['name']}\n"
    confirmation_text += f"📦 Количество: {quantity}"
    if pack_size > 1:
        confirmation_text += f" упаковок ({total_items} ед.)"
    else:
        confirmation_text += " бутылей"
    confirmation_text += f"\n💰 Сумма: {total_price}₸\n\n"
    
    confirmation_text += f"👤 Имя: {user_data.get('first_name', '')}\n"
    confirmation_text += f"📱 Телефон: {user_data.get('phone', '')}\n"
    confirmation_text += f"🏠 Адрес: {user_data.get('address', '')}\n"
    if user_data.get('comment'):
        confirmation_text += f"💬 Комментарий: {user_data.get('comment', '')}\n"
    
    confirmation_text += "\n✅ Всё верно? Подтвердите заказ."
    
    keyboard = [
        [KeyboardButton("✅ Подтвердить заказ")],
        [KeyboardButton("❌ Отменить")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(confirmation_text, reply_markup=reply_markup)
    
    return CONFIRMING_ORDER


async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Подтверждение и отправка заказа"""
    choice = update.message.text
    chat_id = update.effective_chat.id
    user_data_db = db.get_user(chat_id)
    has_data = user_data_db and user_data_db.get('phone')
    
    if choice == "❌ Отменить":
        keyboard = get_main_menu_keyboard(has_data)
        await update.message.reply_text(
            "❌ Заказ отменен.",
            reply_markup=keyboard
        )
        return ConversationHandler.END
    
    if choice == "✅ Подтвердить заказ":
        # Отправляем заказ
        await update.message.reply_text(
            "⏳ Обрабатываю заказ...",
            reply_markup=ReplyKeyboardRemove()
        )
        
        chat_id = update.effective_chat.id
        product = context.user_data['product']
        quantity = context.user_data['quantity']
        
        # Получаем данные пользователя из БД
        user_data = db.get_user(chat_id)
        
        # Создаем API клиент и отправляем заказ
        api = SamalAPI()
        
        # Получаем product_id из конфига PRODUCTS
        product_id = None
        for key, prod in PRODUCTS.items():
            if prod['name'] == product['name']:
                product_id = prod['id']
                break
        
        if not product_id:
            product_id = DEFAULT_PRODUCT_ID
        
        result = api.create_order(
            product_id=product_id,
            quantity=quantity,
            user_data={
                'first_name': user_data.get('first_name', ''),
                'phone': user_data.get('phone', ''),
                'address': user_data.get('address', ''),
                'comment': user_data.get('comment', '')
            }
        )
        
        # Сохраняем заказ в БД
        pack_size = product.get('pack_size', 1)
        total_price = product['price'] * quantity
        order_status = 'success' if result['success'] else 'failed'
        
        order_id = db.save_order(
            chat_id=chat_id,
            product_id=product_id,
            product_name=product['name'],
            quantity=quantity,
            total_price=total_price,
            status=order_status
        )
        
        # Отправляем результат пользователю
        user_data_final = db.get_user(chat_id)
        has_data = user_data_final and user_data_final.get('phone')
        keyboard = get_main_menu_keyboard(has_data)
        
        if result['success']:
            success_text = "✅ Заказ успешно оформлен!\n\n"
            success_text += f"🚰 {product['name']}\n"
            success_text += f"📦 Количество: {quantity}\n"
            success_text += f"💰 Сумма: {total_price}₸\n\n"
            success_text += "📞 С вами свяжется оператор для подтверждения доставки.\n\n"
            success_text += "Спасибо за заказ! 💙\n\n"
            success_text += "💡 Теперь вы можете использовать кнопку '🚰 Быстрый заказ' для повторных заказов!"
            
            await update.message.reply_text(success_text, reply_markup=keyboard)
        else:
            error_text = f"❌ Ошибка при оформлении заказа:\n{result['message']}\n\n"
            error_text += "Пожалуйста, попробуйте позже или свяжитесь с нами напрямую."
            
            await update.message.reply_text(error_text, reply_markup=keyboard)
        
        return ConversationHandler.END
    
    await update.message.reply_text(
        "❌ Пожалуйста, выберите действие с помощью кнопок."
    )
    return CONFIRMING_ORDER


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает профиль пользователя"""
    chat_id = update.effective_chat.id
    user_data = db.get_user(chat_id)
    has_data = user_data and user_data.get('phone')
    
    keyboard = get_main_menu_keyboard(has_data)
    
    if not has_data:
        await update.message.reply_text(
            "📝 У вас еще нет сохраненных данных.\n"
            "Нажмите '📦 Новый заказ' для оформления заказа и сохранения информации.",
            reply_markup=keyboard
        )
        return
    
    profile_text = "👤 Ваш профиль:\n\n"
    profile_text += f"Имя: {user_data.get('first_name', 'Не указано')}\n"
    profile_text += f"📱 Телефон: {user_data.get('phone', 'Не указан')}\n"
    profile_text += f"🏠 Адрес: {user_data.get('address', 'Не указан')}\n"
    if user_data.get('comment'):
        profile_text += f"💬 Комментарий: {user_data.get('comment', '')}\n"
    
    await update.message.reply_text(profile_text, reply_markup=keyboard)


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает историю заказов"""
    chat_id = update.effective_chat.id
    orders = db.get_user_orders(chat_id, limit=10)
    user_data = db.get_user(chat_id)
    has_data = user_data and user_data.get('phone')
    
    keyboard = get_main_menu_keyboard(has_data)
    
    if not orders:
        await update.message.reply_text(
            "📜 У вас пока нет заказов.\n"
            "Нажмите '📦 Новый заказ' для оформления заказа.",
            reply_markup=keyboard
        )
        return
    
    history_text = "📜 История ваших заказов:\n\n"
    
    for i, order in enumerate(orders, 1):
        status_emoji = "✅" if order['status'] == 'success' else "❌"
        history_text += f"{i}. {status_emoji} {order['product_name']}\n"
        history_text += f"   Количество: {order['quantity']}\n"
        history_text += f"   Сумма: {order['total_price']}₸\n"
        history_text += f"   Дата: {order['created_at']}\n\n"
    
    await update.message.reply_text(history_text, reply_markup=keyboard)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена текущего действия"""
    chat_id = update.effective_chat.id
    user_data = db.get_user(chat_id)
    has_data = user_data and user_data.get('phone')
    
    keyboard = get_main_menu_keyboard(has_data)
    
    await update.message.reply_text(
        "❌ Действие отменено.",
        reply_markup=keyboard
    )
    
    return ConversationHandler.END


def main():
    """Запуск бота"""
    # Проверяем наличие токена
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не установлен! Создайте .env файл с токеном.")
        return
    
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Обработчик диалога заказа
    order_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('order', order_start),
            MessageHandler(filters.Regex('^(🚰 Быстрый заказ|📦 Новый заказ|👤 Мой профиль|📜 История заказов)$'), main_menu)
        ],
        states={
            CHOOSING_PRODUCT: [MessageHandler(filters.TEXT & ~filters.COMMAND, product_chosen)],
            CHOOSING_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, quantity_chosen)],
            ENTERING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name_entered)],
            ENTERING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_entered)],
            ENTERING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, address_entered)],
            ENTERING_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, comment_entered)],
            CONFIRMING_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_order)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Добавляем обработчики
    application.add_handler(CommandHandler('start', start))
    application.add_handler(order_conv_handler)
    application.add_handler(CommandHandler('profile', profile))
    application.add_handler(CommandHandler('history', history))
    application.add_handler(CommandHandler('cancel', cancel))
    
    # Запускаем бота
    logger.info("Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

