import logging
import mysql.connector
import os
from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes
)

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

load_dotenv()                        

conn = mysql.connector.connect(
    host=os.environ["MYSQLHOST"],
    port=int(os.environ["MYSQLPORT"]),
    user=os.environ["MYSQLUSER"],
    password=os.environ["MYSQLPASSWORD"],
    database=os.environ["MYSQLDATABASE"],
    ssl_disabled=False                
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

ROLE_IDS = [
    'prod',      # 1. Продажі
    'horeca',    # 2. HoReCa
    'smm',       # 3. Маркетолог / SMM  ← вот оно!
    'it',        # 4. ІТ / Технології
    'office',
    'realty',
    'construct',
    'beauty',
    'logistics',
    'freelance'
]
ROLE_LABELS = {
    'prod': 'Продажі, Торгівля, Продавець 💼',
    'horeca': 'HoReCa (кафе, ресторани) 🍽️',
    'smm': ' Маркетолог / SMM 📲',
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id

    try:
        member = await context.bot.get_chat_member(GROUP_USERNAME, user_id)
        if member.status in ('left', 'kicked'):
            await update.message.reply_text(
                '🚫 Спочатку підпишись на групу, потім запускай! https://t.me/Rabota_Kiev_hub',
                reply_markup=INLINE_BACK
            )
            return ConversationHandler.END
    except Exception as e:
        logger.warning(f'Помилка перевірки підписки: {e}')
        await update.message.reply_text(
            '⚠️ Не можу перевірити підписку. Можливо, бот не в групі або не має прав.',
            reply_markup=INLINE_BACK
        )
        return ConversationHandler.END

    menu = get_main_menu(user_id)
    if menu:
        await update.message.reply_text('Головне меню:', reply_markup=menu)
        return MAIN_MENU

    keyboard = [
        [InlineKeyboardButton(ROLE_LABELS[rid], callback_data=f'role_{rid}')]
        for rid in ROLE_IDS
    ]
    keyboard.append([InlineKeyboardButton('🔙 Скасувати', callback_data='back_main')])
    await update.message.reply_photo(
        photo='https://i.imgur.com/MnFdRwx.png',
        caption='Заповніть резюме для зв\'язку:',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECT_ROLE


async def select_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    rid = query.data.replace('role_', '')
    if rid not in ROLE_LABELS:
        await query.edit_message_text('❌ Невірний напрямок.', reply_markup=INLINE_BACK)
        return SELECT_ROLE

    context.user_data['role'] = ROLE_LABELS[rid]
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            f"Ви обрали: <b>{ROLE_LABELS[rid]}</b>\n"
            "Введіть імʼя, телефон і @username:\n"
            "Приклад:\n"
            "Микола Миколайович, +380XXXXXXXXX, @username"
        ),
        parse_mode='HTML'
    )
    return NAME_PHONE


async def name_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name_phone'] = update.message.text
    await update.message.reply_text(
        '📋 Введіть досвід роботи або пройдені курси:',
        reply_markup=INLINE_BACK
    )
    return EXPERIENCE


async def experience(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['experience'] = update.message.text
    await update.message.reply_text(
        '💡 Введіть ключові навички (3-5 пунктів), розділяючи комами:',
        reply_markup=INLINE_BACK
    )
    return SKILLS


async def skills(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['skills'] = update.message.text
    await update.message.reply_text(
        '📷 Прикріпіть вашу фотографію:',
        reply_markup=INLINE_BACK
    )
    return ASK_PHOTO


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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

    await update.message.reply_text(
        '✅ Дякую, ваше резюме надіслано на розгляд.',
        reply_markup=get_main_menu(update.effective_user.id)
    )
    return MAIN_MENU

async def view_resumes_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    buttons = [
        [InlineKeyboardButton(ROLE_LABELS[rid], callback_data=f'view_{rid}')]
        for rid in ROLE_IDS
    ]
    buttons.append([InlineKeyboardButton('🔙 Назад', callback_data='back_main')])
    await query.edit_message_text('Оберіть категорію резюме:', reply_markup=InlineKeyboardMarkup(buttons))
    return VIEW_CAT


async def handle_view_direction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    rid = query.data.replace('view_', '')
    category = ROLE_LABELS.get(rid)

    cursor.execute(
        'SELECT name_phone, experience, skills, photo_file_id FROM resumes WHERE role=%s ORDER BY id',
        (category,)
    )
    rows = cursor.fetchall()
    if not rows:
        await query.edit_message_text(
            '📂 У цьому розділі ще немає резюме.',
            reply_markup=get_main_menu(query.from_user.id)
        )
        return MAIN_MENU

    context.user_data['view_list'] = rows
    context.user_data['view_index'] = 0
    return await view_nav(update, context)


async def view_nav(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
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

    await query.edit_message_media(
        media=InputMediaPhoto(media=photo_id, caption=caption),
        reply_markup=InlineKeyboardMarkup([nav_buttons])
    )
    return VIEW_NAV


async def next_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['view_index'] += 1
    return await view_nav(update, context)


async def prev_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['view_index'] -= 1
    return await view_nav(update, context)


async def add_subscriber_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        'Введіть ID для додавання підписника:',
        reply_markup=INLINE_BACK
    )
    return ADD_SUB


async def add_subscriber_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        uid = int(text)
        cursor.execute('INSERT IGNORE INTO subscribers(user_id) VALUES (%s)', (uid,))
        conn.commit()
        await update.message.reply_text(
            f'✅ Користувач {uid} доданий.',
            reply_markup=get_main_menu(update.effective_user.id)
        )
    except ValueError:
        await update.message.reply_text(
            '❌ Помилка: введіть числовий ID.',
            reply_markup=get_main_menu(update.effective_user.id)
        )
    return MAIN_MENU


async def remove_subscriber_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    cursor.execute('SELECT user_id FROM subscribers')
    subs = cursor.fetchall()
    if not subs:
        await query.edit_message_text(
            'Список підписників порожній.',
            reply_markup=get_main_menu(query.from_user.id)
        )
        return MAIN_MENU
    buttons = [[InlineKeyboardButton(str(u[0]), callback_data=f'remove_{u[0]}')] for u in subs]
    buttons.append([InlineKeyboardButton('🔙 Назад', callback_data='back_main')])
    await query.edit_message_text(
        'Оберіть ID для видалення:',
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return REMOVE_SUB


async def remove_subscriber_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    uid = int(query.data.replace('remove_', ''))
    context.user_data['remove_uid'] = uid
    buttons = [
        [InlineKeyboardButton('Так, видалити', callback_data='confirm_remove')],
        [InlineKeyboardButton('🔙 Скасувати', callback_data='back_main')]
    ]
    await query.edit_message_text(
        f'Видалити користувача {uid}?',
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return CONFIRM_REMOVE


async def confirm_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    uid = context.user_data.get('remove_uid')
    cursor.execute('DELETE FROM subscribers WHERE user_id=%s', (uid,))
    conn.commit()
    await query.edit_message_text(
        f'✅ Користувач {uid} вилучений.',
        reply_markup=get_main_menu(query.from_user.id)
    )
    return MAIN_MENU


async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    try:
        await query.message.delete()
    except:
        pass
    menu = get_main_menu(user_id)
    if menu:
        await context.bot.send_message(chat_id=chat_id, text='Головне меню:', reply_markup=menu)
        return MAIN_MENU
    keyboard = [[InlineKeyboardButton(ROLE_LABELS[rid], callback_data=f'role_{rid}')] for rid in ROLE_IDS]
    keyboard.append([InlineKeyboardButton('🔙 Скасувати', callback_data='back_main')])
    await context.bot.send_photo(
        chat_id=chat_id,
        photo='https://i.imgur.com/MnFdRwx.png',
        caption='Заповніть резюме для зв\'язку:',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECT_ROLE


# === MAIN ===
load_dotenv()
def main():
    application = (
        Application.builder()
        .token(os.getenv("BOT_TOKEN")) 
        .build()
    )
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(view_resumes_start, pattern='^view_resumes$'),
                CallbackQueryHandler(add_subscriber_start, pattern='^btn_add_sub$'),
                CallbackQueryHandler(remove_subscriber_start, pattern='^btn_remove_sub$'),
            ],
            SELECT_ROLE: [
                CallbackQueryHandler(select_role, pattern='^role_'),
                CallbackQueryHandler(back_main, pattern='^back_main$'),
            ],
            NAME_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, name_phone),
                CallbackQueryHandler(back_main, pattern='^back_main$'),
            ],
            EXPERIENCE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, experience),
                CallbackQueryHandler(back_main, pattern='^back_main$'),
            ],
            SKILLS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, skills),
                CallbackQueryHandler(back_main, pattern='^back_main$'),
            ],
            ASK_PHOTO: [
                MessageHandler(filters.PHOTO, photo_handler),
                CallbackQueryHandler(back_main, pattern='^back_main$'),
            ],
            VIEW_CAT: [
                CallbackQueryHandler(handle_view_direction, pattern='^view_'),
                CallbackQueryHandler(back_main, pattern='^back_main$'),
            ],
            VIEW_NAV: [
                CallbackQueryHandler(next_resume, pattern='^next_resume$'),
                CallbackQueryHandler(prev_resume, pattern='^prev_resume$'),
                CallbackQueryHandler(back_main, pattern='^back_main$'),
            ],
            ADD_SUB: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_subscriber_save),
                CallbackQueryHandler(back_main, pattern='^back_main$'),
            ],
            REMOVE_SUB: [
                CallbackQueryHandler(remove_subscriber_confirm, pattern='^remove_'),
                CallbackQueryHandler(back_main, pattern='^back_main$'),
            ],
            CONFIRM_REMOVE: [
                CallbackQueryHandler(confirm_remove, pattern='^confirm_remove$'),
                CallbackQueryHandler(back_main, pattern='^back_main$'),
            ],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    application.add_handler(conv_handler)
    application.run_polling()


if __name__ == '__main__':
    main()
