from telethon import TelegramClient, events, Button
import asyncio
import sqlite3
import logging

from decouple import config
from aiogram import types, Bot, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.filters import Command

# Load API credentials
API_ID = config("API_ID")
API_HASH = config("API_HASH")
TOKEN = config("BOT_TOKEN")

# Initialize bot and dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Database setup
def init_db():
    conn = sqlite3.connect("water_bot.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS households (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      address TEXT UNIQUE,
                      bottle_balance INTEGER DEFAULT 5)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      telegram_id INTEGER UNIQUE,
                      iin INTEGER UNIQUE,
                      name TEXT,
                      phone TEXT UNIQUE,
                      tag TEXT UNIQUE,
                      household_id INTEGER,
                      verified INTEGER DEFAULT 0,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                      FOREIGN KEY(household_id) REFERENCES households(id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      household_id INTEGER,
                      bottles_collected INTEGER,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                      FOREIGN KEY(household_id) REFERENCES households(id))''')
    conn.commit()
    conn.close()



# Define FSM states
class RegistrationState(StatesGroup):
    waiting_for_member = State()
    waiting_for_registration = State()


async def get_household_address(user_id):
    """Retrieve the household address of a user from the database."""
    conn = sqlite3.connect("water_bot.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT household_id FROM users WHERE telegram_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return None
    
    household_id = result[0]
    cursor.execute("SELECT address FROM households WHERE id = ?", (household_id,))
    address = cursor.fetchone()[0]
    conn.close()

    return address, household_id


async def send_verification_message(client, tag, address):
    """Send a verification message with inline buttons."""
    try:
        user = await client.get_entity(tag)
        message_text = f"Вас хотят добавить в прописку по адресу {address}. Вы подтверждаете это действие?"
        buttons = [[Button.inline("✅ Подтверждаю", f"confirm:{tag}"), Button.inline("❌ Отменить", f"cancel:{tag}")]]
        
        sent_message = await client.send_message(user, message_text, buttons=buttons)
        return sent_message
    except Exception as e:
        print(f"Ошибка отправки сообщения {tag}: {e}")
        return None


async def handle_verification_response(event, verification_messages, household_id):
    """Process user's response to verification request."""
    data = event.data.decode()
    action, tag = data.split(":")

    if tag not in verification_messages:
        return

    response_text = "✅ Вы были успешно добавлены в базу данных!" if action == "confirm" else "❌ Спасибо за ответ. Ваше действие отменено."
    
    # Edit the original message to indicate response received
    sent_message = verification_messages[tag]
    await sent_message.edit(sent_message.text + "\n\n(Ответ получен ✅)", buttons=None)

    # Send a confirmation response
    await event.respond(response_text)

    # If confirmed, register the user
    if action == "confirm":
        await add_verified_user(tag, household_id)


async def add_verified_user(tag, household_id):
    """Register or update a verified user in the database."""
    conn = sqlite3.connect("water_bot.db")
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT telegram_id FROM users WHERE tag = ?", (tag,))
        existing_user = cursor.fetchone()

        if existing_user:
            cursor.execute("UPDATE users SET household_id = ?, verified = 1 WHERE tag = ?", (household_id, tag))
        else:
            cursor.execute("INSERT INTO users (tag, household_id, verified) VALUES (?, ?, 1)", (tag, household_id))

        conn.commit()
        print(f"Пользователь {tag} успешно добавлен в базу данных!")
    except sqlite3.IntegrityError:
        print(f"Ошибка: {tag} уже зарегистрирован!")
    finally:
        conn.close()


@dp.message(Command("add_member"))
async def add_member(message: Message, state: FSMContext):
    """Start the process of adding a new household member."""
    await state.set_state(RegistrationState.waiting_for_member)
    await message.answer("Send member details in format: Telegram Tag 1, Telegram Tag 2 etc.")


@dp.message(RegistrationState.waiting_for_member)
async def save_member(message: Message, state: FSMContext):
    """Process new member details and send verification messages."""
    user_id = message.from_user.id
    tags = [t.strip() for t in message.text.split(",")]

    # Get user's household address
    household_data = await get_household_address(user_id)
    if not household_data:
        await message.answer("You must register first using /register.")
        return
    
    address, household_id = household_data

    # Initialize Telegram Client
    async with TelegramClient("session_name", API_ID, API_HASH) as client:
        verification_messages = {}

        for tag in tags:
            msg = await send_verification_message(client, tag, address)
            if msg:
                verification_messages[tag] = msg

        # Set up event listener for button clicks
        @client.on(events.CallbackQuery)
        async def handle_callback(event):
            await handle_verification_response(event, verification_messages, household_id)

        print("Ожидание ответа пользователей...")
        await client.run_until_disconnected()  # Keep listening for responses

    await message.answer(f"Отправили подтверждение всем сожителям: {', '.join(tags)}")
    await state.clear()

async def main():
    logging.basicConfig(level=logging.INFO)
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())