import asyncio
import pandas as pd
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from decouple import config
from db_handler import DBHandler  # Assuming DBHandler is in db_handler.py

# Load bot token from environment variables
TOKEN = config('ADMIN_BOT_TOKEN')  # Change token for admin bot
bot = Bot(token=TOKEN)
dp = Dispatcher()

db = DBHandler()

# Admins' Telegram IDs (replace with actual IDs)
ADMIN_IDS = {704415982}  # Replace with real admin Telegram IDs

def upsert_employee(employee_id, name, employed_date, phone_number):
    """Insert a new employee or update an existing one."""
    existing_employee = db.fetch_one("employees", {"employee_id": employee_id})
    
    if existing_employee:
        db.update("employees", {"name": name, "employed_date": employed_date, "phone_number": phone_number}, {"employee_id": employee_id})
        return f"🔄 Updated existing employee: {name}"
    else:
        db.insert("employees", {"employee_id": employee_id, "name": name, "employed_date": employed_date, "phone_number": phone_number})
        return f"✅ Added new employee: {name}"

async def process_employee_file(file_path):
    """Reads an Excel file and upserts employee records."""
    try:
        df = pd.read_excel(file_path)
        if not {'name', 'employee_id', 'employed_date', "phone_number"}.issubset(df.columns):
            return "❌ Error: Excel file must contain 'name', 'employee_id','phone_number' and 'employed_date' columns."
        
        results = [upsert_employee(row['employee_id'], row['name'], row['employed_date'], row["phone_number"]) for _, row in df.iterrows()]
        return "\n".join(results)
    except Exception as e:
        return f"❌ Unexpected error: {str(e)}"

@dp.message(CommandStart())
async def start_handler(message: Message):
    """Only allows admins to use the bot."""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ You are not authorized to use this bot.")
        return
    await message.answer("👋 Welcome, Admin! Send me an Excel file with employee details.")

@dp.message(lambda message: message.document)
async def handle_excel_upload(message: Message):
    """Handles document uploads and processes employee data."""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ You are not authorized to use this bot.")
        return
    
    document = message.document
    file_path = f"temp_{document.file_name}"

    file = await bot.download(document)
    with open(file_path, "wb") as f:
        f.write(file.read())

    result = await process_employee_file(file_path)
    await message.answer(result)

async def main():
    """Start the bot."""
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
