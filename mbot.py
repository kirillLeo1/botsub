import logging
import mysql.connector
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto
)
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext
)
from telegram.error import TelegramError

# ============================================
#            Налаштування бота і БД
# ============================================

ADMIN_IDS = [7060952414]
GROUP_USERNAME = '@Rabota_Kiev_hub'

INLINE_BACK = InlineKeyboardMarkup(
    [[InlineKeyboardButton('🔙 Назад', callback_data='back_main')]]
)

(
    MAIN_MENU,
    SELECT_ROLE,
    NAME_PHONE,
    EXPERIENCE,
    SKILLS,
    ASK_PHOTO,
    ADD_SUB,
    REMOVE_SUB,
    VIEW_CAT,
    VIEW_NAV,
    CONFIRM_REMOVE
) = range(11)

# Підключення до MySQL
conn = mysql.connector.connect(
    host='switchyard.proxy.rlwy.net',
    port=18288,
    user='root',
    password='rWbyTQgrPnRASYtWxDjziJwupnVDdlrz',  # 🔐 заміни на свій пароль
    database='railway'
)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS resumes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT,
        role VARCHAR(255),
        name_phone VARCHAR(255),
        experience TEXT,
        skills TEXT,
        photo_file_id VARCHAR(255)
    );
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS subscribers (
        user_id BIGINT PRIMARY KEY
    );
''')
conn.commit()

# Логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Напрямки
ROLE_IDS = ['prod', 'horeca', 'it', 'office', 'realty', 'construct', 'beauty', 'logistics', 'freelance']
ROLE_LABELS = {
    'prod': 'Продажі, Торгівля, Продавець 💼',
    'horeca': 'HoReCa (кафе, ресторани) 🍽️',
    'it': 'ІТ / Технології 💻',
    'office': 'Офіс-менеджер, Адміністратор, Асистент 🏢',
    'realty': 'Рієлтор / Нерухомість 🗝️',
    'construct': 'Будівництво / Архітектура-Дизайн 🏡',
    'beauty': 'Краса / Здоровʼя 💆‍♀️',
    'logistics': 'Логістика / Склад 🚚',
    'freelance': 'Фриланс / Віддалена робота 🌍'
}

def is_subscriber(user_id: int) -> bool:
    cursor.execute('SELECT 1 FROM subscribers WHERE user_id=%s', (user_id,))
    return bool(cursor.fetchone())

def get_main_menu(user_id: int):
    if user_id in ADMIN_IDS:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton('📄 Переглянути резюме', callback_data='view_resumes')],
            [InlineKeyboardButton('➕ Додати підписника', callback_data='btn_add_sub')],
            [InlineKeyboardButton('➖ Видалити підписника', callback_data='btn_remove_sub')]
        ])
    elif is_subscriber(user_id):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton('📄 Переглянути резюме', callback_data='view_resumes')]
        ])
    return None

# === Команди ===

def start(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id

    if not GROUP_USERNAME.startswith('@'):
        update.message.reply_text('❗️ Не вказано @username групи в GROUP_USERNAME!')
        return ConversationHandler.END

    try:
        member = context.bot.get_chat_member(GROUP_USERNAME, user_id)
        if member.status in ('left', 'kicked'):
            update.message.reply_text(
                '🚫 Спочатку підпишись на групу, потім запускай! https://t.me/Rabota_Kiev_hub',
                reply_markup=INLINE_BACK
            )
            return ConversationHandler.END
    except TelegramError as e:
        logger.warning(f'Помилка перевірки підписки: {e}')
        update.message.reply_text(
            '⚠️ Не можу перевірити підписку. Бот не в групі або не має прав.',
            reply_markup=INLINE_BACK
        )
        return ConversationHandler.END

    menu = get_main_menu(user_id)
    if menu:
        update.message.reply_text('Головне меню:', reply_markup=menu)
        return MAIN_MENU

    keyboard = [[InlineKeyboardButton(ROLE_LABELS[rid], callback_data=f'role_{rid}')] for rid in ROLE_IDS]
    keyboard.append([InlineKeyboardButton('🔙 Скасувати', callback_data='back_main')])
    update.message.reply_photo(
        photo='https://i.imgur.com/MnFdRwx.png',
        caption='Виберіть напрямок роботи:',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECT_ROLE

def select_role(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    rid = query.data.replace('role_', '')
    if rid not in ROLE_LABELS:
        return query.edit_message_text('❌ Невірний напрямок.', reply_markup=INLINE_BACK)

    context.user_data['role'] = ROLE_LABELS[rid]
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            f"Ви обрали: <b>{ROLE_LABELS[rid]}</b>\n"
            "Введіть імʼя, телефон і @username:\n"
            "Микола Миколайович, +380XXXXXXXXX, @username"
        ),
        parse_mode='HTML'
    )
    return NAME_PHONE

def name_phone(update: Update, context: CallbackContext) -> int:
    context.user_data['name_phone'] = update.message.text
    update.message.reply_text(
        '📋 Введіть досвід роботи або пройдені курси:',
        reply_markup=INLINE_BACK
    )
    return EXPERIENCE
 
def experience(update: Update, context: CallbackContext) -> int:
    context.user_data['experience'] = update.message.text
    update.message.reply_text(
        '💡 Введіть ключові навички (3-5 пунктів), розділяючи комами:',
        reply_markup=INLINE_BACK
    )
    return SKILLS

def skills(update: Update, context: CallbackContext) -> int:
    context.user_data['skills'] = update.message.text
    update.message.reply_text(
        '📷 Прикріпіть вашу фотографію:',
        reply_markup=INLINE_BACK
    )
    return ASK_PHOTO

def photo_handler(update: Update, context: CallbackContext) -> int:
    photo = update.message.photo[-1]
    file_id = photo.file_id
    data = context.user_data

    cursor.execute(
        'INSERT INTO resumes (user_id, role, name_phone, experience, skills, photo_file_id) VALUES (%s, %s, %s, %s, %s, %s)',
        (
            update.effective_user.id,
            data['role'],
            data['name_phone'],
            data['experience'],
            data['skills'],
            file_id
        )
    )
    conn.commit()

    update.message.reply_text(
        '✅ Дякую, ваше резюме надіслано на розгляд.',
        reply_markup=get_main_menu(update.effective_user.id)
    )
    return MAIN_MENU

def view_resumes_start(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    buttons = [
        [InlineKeyboardButton(ROLE_LABELS[rid], callback_data=f'view_{rid}')]
        for rid in ROLE_IDS
    ]
    buttons.append([InlineKeyboardButton('🔙 Назад', callback_data='back_main')])
    query.edit_message_text(
        'Оберіть категорію резюме:',
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return VIEW_CAT

def handle_view_direction(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    rid = query.data.replace('view_', '')
    category = ROLE_LABELS.get(rid)

    cursor.execute(
        'SELECT name_phone, experience, skills, photo_file_id FROM resumes WHERE role=%s ORDER BY id',
        (category,)
    )
    rows = cursor.fetchall()
    if not rows:
        query.edit_message_text(
            '📂 У цьому розділі ще немає резюме.',
            reply_markup=get_main_menu(query.from_user.id)
        )
        return MAIN_MENU

    context.user_data['view_list'] = rows
    context.user_data['view_index'] = 0
    return view_nav(update, context)

def view_nav(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    rows = context.user_data['view_list']
    idx = context.user_data['view_index']
    idx = max(0, min(idx, len(rows) - 1))
    context.user_data['view_index'] = idx

    name, exp, skills, photo_id = rows[idx]
    caption = f"Резюме ({idx + 1}/{len(rows)}):\n{name}\nДосвід: {exp}\nНавички: {skills}"

    nav_buttons = []
    if idx > 0:
        nav_buttons.append(InlineKeyboardButton('← Попереднє', callback_data='prev_resume'))
    if idx < len(rows) - 1:
        nav_buttons.append(InlineKeyboardButton('Наступне →', callback_data='next_resume'))
    nav_buttons.append(InlineKeyboardButton('🔙 Назад', callback_data='back_main'))

    query.edit_message_media(
        media=InputMediaPhoto(media=photo_id, caption=caption),
        reply_markup=InlineKeyboardMarkup([nav_buttons])
    )
    return VIEW_NAV

def next_resume(update: Update, context: CallbackContext) -> int:
    context.user_data['view_index'] += 1
    return view_nav(update, context)

def prev_resume(update: Update, context: CallbackContext) -> int:
    context.user_data['view_index'] -= 1
    return view_nav(update, context)

def add_subscriber_start(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        'Введіть ID для додавання підписника:',
        reply_markup=INLINE_BACK
    )
    return ADD_SUB

def add_subscriber_save(update: Update, context: CallbackContext) -> int:
    text = update.message.text.strip()
    try:
        uid = int(text)
        cursor.execute('INSERT IGNORE INTO subscribers(user_id) VALUES (%s)', (uid,))
        conn.commit()
        update.message.reply_text(
            f'✅ Користувач {uid} доданий.',
            reply_markup=get_main_menu(update.effective_user.id)
        )
    except ValueError:
        update.message.reply_text(
            '❌ Помилка: введіть числовий ID.',
            reply_markup=get_main_menu(update.effective_user.id)
        )
    return MAIN_MENU

def remove_subscriber_start(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    cursor.execute('SELECT user_id FROM subscribers')
    subs = cursor.fetchall()
    if not subs:
        query.edit_message_text(
            'Список підписників порожній.',
            reply_markup=get_main_menu(query.from_user.id)
        )
        return MAIN_MENU
    buttons = [[InlineKeyboardButton(str(u[0]), callback_data=f'remove_{u[0]}')] for u in subs]
    buttons.append([InlineKeyboardButton('🔙 Назад', callback_data='back_main')])
    query.edit_message_text(
        'Оберіть ID для видалення:',
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return REMOVE_SUB

def remove_subscriber_confirm(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    uid = int(query.data.replace('remove_', ''))
    context.user_data['remove_uid'] = uid
    buttons = [
        [InlineKeyboardButton('Так, видалити', callback_data='confirm_remove')],
        [InlineKeyboardButton('🔙 Скасувати', callback_data='back_main')]
    ]
    query.edit_message_text(
        f'Видалити користувача {uid}?',
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return CONFIRM_REMOVE

def confirm_remove(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    uid = context.user_data.get('remove_uid')
    cursor.execute('DELETE FROM subscribers WHERE user_id=%s', (uid,))
    conn.commit()
    query.edit_message_text(
        f'✅ Користувач {uid} вилучений.',
        reply_markup=get_main_menu(query.from_user.id)
    )
    return MAIN_MENU

def back_main(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    try:
        query.message.delete()
    except:
        pass
    menu = get_main_menu(user_id)
    if menu:
        context.bot.send_message(chat_id=chat_id, text='Головне меню:', reply_markup=menu)
        return MAIN_MENU
    keyboard = [[InlineKeyboardButton(ROLE_LABELS[rid], callback_data=f'role_{rid}')] for rid in ROLE_IDS]
    keyboard.append([InlineKeyboardButton('🔙 Скасувати', callback_data='back_main')])
    context.bot.send_photo(
        chat_id=chat_id,
        photo='https://i.imgur.com/MnFdRwx.png',
        caption='Оберіть напрям роботи:',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECT_ROLE

# 🚀 Головна точка входу
def main():
    updater = Updater('7485109824:AAGj7HXh1QT3G-fo5qWEOMesaBYydtw7oD4')  # 🔐 встав свій токен
    dp = updater.dispatcher

    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(view_resumes_start, pattern='^view_resumes$'),
                CallbackQueryHandler(add_subscriber_start, pattern='^btn_add_sub$'),
                CallbackQueryHandler(remove_subscriber_start, pattern='^btn_remove_sub$')
            ],
            SELECT_ROLE: [
                CallbackQueryHandler(select_role, pattern='^role_'),
                CallbackQueryHandler(back_main, pattern='^back_main$')
            ],
            NAME_PHONE: [
                MessageHandler(Filters.text & ~Filters.command, name_phone),
                CallbackQueryHandler(back_main, pattern='^back_main$')
            ],
            EXPERIENCE: [
                MessageHandler(Filters.text & ~Filters.command, experience),
                CallbackQueryHandler(back_main, pattern='^back_main$')
            ],
            SKILLS: [
                MessageHandler(Filters.text & ~Filters.command, skills),
                CallbackQueryHandler(back_main, pattern='^back_main$')
            ],
            ASK_PHOTO: [
                MessageHandler(Filters.photo, photo_handler),
                CallbackQueryHandler(back_main, pattern='^back_main$')
            ],
            VIEW_CAT: [
                CallbackQueryHandler(handle_view_direction, pattern='^view_'),
                CallbackQueryHandler(back_main, pattern='^back_main$')
            ],
            VIEW_NAV: [
                CallbackQueryHandler(next_resume, pattern='^next_resume$'),
                CallbackQueryHandler(prev_resume, pattern='^prev_resume$'),
                CallbackQueryHandler(back_main, pattern='^back_main$')
            ],
            ADD_SUB: [
                MessageHandler(Filters.text & ~Filters.command, add_subscriber_save),
                CallbackQueryHandler(back_main, pattern='^back_main$')
            ],
            REMOVE_SUB: [
                CallbackQueryHandler(remove_subscriber_confirm, pattern='^remove_'),
                CallbackQueryHandler(back_main, pattern='^back_main$')
            ],
            CONFIRM_REMOVE: [
                CallbackQueryHandler(confirm_remove, pattern='^confirm_remove$'),
                CallbackQueryHandler(back_main, pattern='^back_main$')
            ],
        },
        fallbacks=[CommandHandler('start', start)]
    )
    dp.add_handler(conv)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
