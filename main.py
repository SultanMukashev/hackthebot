import logging
import asyncio
import sqlite3
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from decouple import config
from ver import verify

TOKEN = config('BOT_TOKEN')
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


bot = Bot(token=TOKEN)
dp = Dispatcher()

class RegistrationState(StatesGroup):
    waiting_for_registration = State()
    waiting_for_member = State()

@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("water_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET telegram_id = ? WHERE phone = ?", (user_id, str(user_id)))
    conn.commit()
    conn.close()
    await message.answer("Welcome! Use /register to enter your address and details.")

@dp.message(Command("register"))
async def register(message: Message, state: FSMContext):
    await state.set_state(RegistrationState.waiting_for_registration)
    await message.answer("Please send your details in format: Name, iin, Address, Phone, tag")

@dp.message(RegistrationState.waiting_for_registration)
async def save_registration(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.split(",")
    if len(text) != 3:
        await message.answer("Invalid format. Use: Name, iin, Address, Phone, tag")
        return
    name, iin, address, phone, tag = map(str.strip, text)
    conn = sqlite3.connect("water_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM households WHERE address = ?", (address,))
    household = cursor.fetchone()
    if not household:
        cursor.execute("INSERT INTO households (address, bottle_balance) VALUES (?, ?)", (address, 5))
        conn.commit()
        household_id = cursor.lastrowid
    else:
        household_id = household[0]
    try:
        cursor.execute("INSERT INTO users (telegram_id, name, iin, tag, phone, household_id, verified) VALUES (?, ?, ?, ?, ?)",
                       (user_id, name, iin, tag, phone, household_id, 1))
        conn.commit()
        await message.answer("Registration successful! Now add household members using /add_member.")
        await state.clear()
    except sqlite3.IntegrityError:
        await message.answer("You're already registered!")
    conn.close()

@dp.message(Command("add_member"))
async def add_member(message: Message, state: FSMContext):
    await state.set_state(RegistrationState.waiting_for_member)
    await message.answer("Send member details in format: Telegram Tag 1, Telegram Tag 2 etc.")

@dp.message(RegistrationState.waiting_for_member)
async def save_member(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.split(",")
    if len(text) != 2:
        await message.answer("Invalid format. Use: Telegram Tag 1, Telegram Tag 2 etc.")
        return
    tags = map(str.strip, text)
    conn = sqlite3.connect("water_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT household_id FROM users WHERE telegram_id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        household_id = result[0]
        cursor.execute("SELECT address FROM households WHERE id = ?",(household_id,))
        address = cursor.fetchone()[0]
        for tag in tags:
           await verify(tag, address)
        await message.answer(f"Отправили подтверждение всем сожителям:{", ".join(tags)}")
        await state.clear()
    else:
        await message.answer("You must register first using /register.")
    conn.close()

@dp.message(Command("verify"))
async def verify_member(message: Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("water_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET verified = 1 WHERE telegram_id = ?", (user_id,))
    cursor.execute("UPDATE households SET bottle_balance = bottle_balance + 5 WHERE id = (SELECT household_id FROM users WHERE telegram_id = ?)", (user_id,))
    conn.commit()
    conn.close()
    await message.answer("You have been verified as a household member!")

@dp.message(Command("balance"))
async def check_balance(message: Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("water_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT bottle_balance FROM households WHERE id = (SELECT household_id FROM users WHERE telegram_id = ?)", (user_id,))
    result = cursor.fetchone()
    if result:
        await message.answer(f"Your household has {result[0]} bottles available.")
    else:
        await message.answer("You're not registered. Use /register.")
    conn.close()

@dp.message(Command("collect"))
async def collect_water(message: Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("water_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT bottle_balance, id FROM households WHERE id = (SELECT household_id FROM users WHERE telegram_id = ?)", (user_id,))
    result = cursor.fetchone()
    if result and result[0] > 0:
        new_balance = max(0, result[0] - 5)
        cursor.execute("UPDATE households SET bottle_balance = ? WHERE id = ?", (new_balance, result[1]))
        cursor.execute("INSERT INTO transactions (household_id, bottles_collected) VALUES (?, ?)", (result[1], min(5, result[0])))
        conn.commit()
        await message.answer(f"You have collected {min(5, result[0])} bottles. Remaining for household: {new_balance}.")
    else:
        await message.answer("Your household has no bottles available.")
    conn.close()

async def main():
    logging.basicConfig(level=logging.INFO)
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
