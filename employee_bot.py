import asyncio
import psycopg2
from db_handler import DBHandler
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from decouple import config

TOKEN = config('EMP_TOKEN')
print(TOKEN)
bot = Bot(token=TOKEN)
dp = Dispatcher()
db = DBHandler()

class RegistrationState(StatesGroup):
    waiting_for_amount = State()

async def fill_point(bottle_amount, point,employee_id ):
    try:
        result = db.call_function("refill_bottle_point",(employee_id, point, bottle_amount,))
        print(result)

        if "✅" in result:  # If transaction is successful, commit
            db.conn.commit()
        else:
            db.conn.rollback()  # Rollback if failed (bottles not enough)

    except Exception as e:
        conn.rollback()  # Rollback in case of unexpected errors
        print(f"❌ Unexpected error: {e}")

def get_amount(point_id):
    bottle_amount = db.fetch_column("bottle_points", "bottle_amount",{"point_id": point_id})[0][0]
    return bottle_amount

@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    """Handles /start with an optional parameter"""
    args = message.text.split()  # Get full command text
    print(args)
    if len(args) > 1:  # Check if a parameter exists
        point_id = args[1]
        await message.answer(f"Welcome! You are at Bottle Point: {point_id}")

        # Example: If the parameter is 'register_12345', handle it separately
        user_id = message.from_user.id
        await message.answer(f"Working with user with ID: {user_id}")
        await state.update_data(point=point_id, user_id=user_id)
        await state.set_state(RegistrationState.waiting_for_amount)
        await message.answer("Send how many bottles you filled.")
        return
    else:
        await message.answer("Hello! Use /help to see available commands.")

@dp.message(RegistrationState.waiting_for_amount)
async def send_verification_to_members(message: Message, state: FSMContext):
    amount = message.text.strip()
    data = await state.get_data()
    point_id = data['point']
    user_id = data['user_id']

    if not amount.isdigit():
        await message.answer("❌ Invalid Amount. Please enter a number")
        return
    await fill_point(int(amount), int(point_id), int(user_id))
    overall = get_amount(str(point_id))
    await message.answer(f"✅ Bottle point filled successfully. Current amount {overall}")
    

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())