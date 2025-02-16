import asyncio
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from aiogram.fsm.state import StatesGroup, State
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from decouple import config

from db_handler import DBHandler  # Assuming DBHandler is in db_handler.py
from generator import generate_qr_code


# Load bot token from environment variables
TOKEN = config('ADMIN_BOT_TOKEN')  # Change token for admin bot
bot = Bot(token=TOKEN)
dp = Dispatcher()

db = DBHandler()

class RegistrationState(StatesGroup):
    get_xlsx = State()
    generate_qr = State()

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

@dp.message(Command("generate_qr"))
async def generate_qr_handler(message: Message):
    """Handles the /generate_qr command."""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ You are not authorized to use this bot.")
        return

    text = "https://t.me/water_collect_bot?start="+message.text.replace("/generate_qr", "").strip()
    if not text:
        await message.answer("❌ Please provide text to generate a QR code.\nExample: `/generate_qr https://example.com`")
        return

    file_path = generate_qr_code(text)
    qr_image = FSInputFile(file_path)

    await message.answer_photo(photo=qr_image, caption="✅ Here is your QR code.")

# Load Data
users_df = pd.read_csv(r"db_files\users.csv")
household_df = pd.read_csv(r"db_files\households.csv")
merged_df = users_df.merge(household_df, left_on='household_id', right_on='id', suffixes=('_user', '_household'))
users_df['timestamp'] = pd.to_datetime(users_df['timestamp'])

def create_keyboard():
    """Create an inline keyboard with proper analysis names in a vertical layout."""
    buttons = [
        [InlineKeyboardButton(text="Household Distribution", callback_data="household_distribution")],
        [InlineKeyboardButton(text="Water Consumption Analysis", callback_data="water_consumption")],
        [InlineKeyboardButton(text="Average Bottles Per Person", callback_data="avg_bottles")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

@dp.message(Command("analytics"))
async def analytics(message: Message):
    """Handle the /analytics command to show analysis options."""
    await message.answer("Choose an analysis option:", reply_markup=create_keyboard())

@dp.callback_query()
async def handle_callback(callback_query: types.CallbackQuery):
    """Handle button presses."""
    analysis_type = callback_query.data
    if analysis_type == "household_distribution":
        await analysis1(callback_query)
    elif analysis_type == "water_consumption":
        await analysis2(callback_query)
    elif analysis_type == "avg_bottles":
        await analysis3(callback_query)
    else:
        await callback_query.message.answer("Invalid selection.")
    await callback_query.answer()

async def analysis1(callback_query: types.CallbackQuery):
    """Perform Household Distribution analysis and send the result."""
    household_counts = merged_df.groupby('household_id')['id_user'].count()
    household_counts_df = household_counts.value_counts().sort_index()
    
    plt.figure(figsize=(8, 5))
    plt.bar(household_counts_df.index, household_counts_df.values)
    plt.xlabel('Number of People in Household')
    plt.ylabel('Count of Households')
    plt.title('Distribution of People per Household')
    plt.grid()
    
    image_path = "household_distribution.png"
    plt.savefig(image_path)
    plt.close()
    
    # Use FSInputFile for sending the photo
    photo = FSInputFile(image_path)
    await callback_query.message.answer_photo(photo=photo, caption="Household Distribution Analysis")

async def analysis2(callback_query: types.CallbackQuery):
    """Perform Water Consumption Analysis and send the result."""
    household_water_usage = merged_df.groupby('household_id').agg(
        household_size=('id_user', 'count'),  # Count of users in household
        total_bottles=('bottle_balance', 'sum')  # Total bottle usage
    )
    
    # Group by household size to find average water consumption per size
    household_avg_usage = household_water_usage.groupby('household_size')['total_bottles'].mean()
    
    # Plot bar chart for household size vs. average water consumption
    plt.figure(figsize=(10, 5))
    household_avg_usage.plot(kind='bar', color='blue')
    plt.xlabel('Household Size')
    plt.ylabel('Average Bottles Used')
    plt.title('Household Size vs Average Water Consumption')
    plt.grid(axis='y')
    
    image_path = "water_consumption.png"
    plt.savefig(image_path)
    plt.close()
    
    # Use FSInputFile for sending the photo
    photo = FSInputFile(image_path)
    await callback_query.message.answer_photo(photo=photo, caption="Water Consumption Analysis")

async def analysis3(callback_query: types.CallbackQuery):
    """Perform Average Bottles Per Person analysis and send the result."""
    avg_bottles_per_person = household_df['bottle_balance'].sum() / len(users_df)
    result_text = f"Average Bottles Per Person: {avg_bottles_per_person:.2f}"
    await callback_query.message.answer(result_text)


async def main():
    """Start the bot."""
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
