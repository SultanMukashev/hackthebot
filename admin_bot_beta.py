import asyncio
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

TOKEN = "7983345195:AAGlRA4sErIanYp8HykUQ_EOVV4AceTRBk4"
bot = Bot(token=TOKEN)
dp = Dispatcher()

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
