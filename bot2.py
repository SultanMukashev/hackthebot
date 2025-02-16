from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from decouple import config
from geocoder import geocode_address 
import asyncio

from db_handler import DBHandler

TOKEN = config("BOT_TOKEN")
print(TOKEN)

bot = Bot(token=TOKEN)
dp = Dispatcher()
db = DBHandler()

class RegistrationState(StatesGroup):
    waiting_for_iin = State()
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_address_ft = State()


@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    user = db.fetch_one("users", {"tg_id": message.from_user.id})
    if user:
        await message.answer("✅ You are already registered! Want to /invite your neighbours?")
    else:
        args = message.text.split()

        if(len(args)>1 and args[1].startswith("invite_")):
            household_id = args[1][6:]
            print(household_id)
            await state.update_data(address=household_id)
            await message.answer("Invitation was approved. Please enter your IIN to start registration:")
            await state.set_state(RegistrationState.waiting_for_iin)

        await message.answer("Welcome! Please enter your Address to start your Registration:")
        await state.set_state(RegistrationState.waiting_for_address_ft)

@dp.message(Command("help"))
async def help_handler(message: Message):
    commands = [
        ("/register", "Register as a new user"),
        ("/invite", "Invite others to register"),
        ("/status", "Check your registration status")
    ]
    text = "Available commands:\n" + "\n".join(f"{cmd} - {desc}" for cmd, desc in commands)
    await message.answer(text)

@dp.message(RegistrationState.waiting_for_address_ft)
async def process_name(message: Message, state: FSMContext):
    address = message.text
    data = geocode_address(address)
    lng = data["longitude"]
    lat = data["latitude"]
    db.insert('households',{"address": address, "longitude": lng, "latitude": lat, "bottle_balance": 5})
    household_id = db.fetch_column("households","id",{"address": address})[0][0]
    print(household_id, address)
    await state.update_data(address=household_id)
    await message.answer("Please enter your IIN:")
    await state.set_state(RegistrationState.waiting_for_iin)

@dp.message(RegistrationState.waiting_for_iin)
async def process_iin(message: Message, state: FSMContext):
    if not message.text.isdigit() or len(message.text) != 12:
        await message.answer("Invalid IIN. Please enter a 12-digit number:")
        return
    await state.update_data(iin=message.text)
    await message.answer("Enter your full name:")
    await state.set_state(RegistrationState.waiting_for_name)

@dp.message(RegistrationState.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Enter your Phone Number:")
    await state.set_state(RegistrationState.waiting_for_phone)


@dp.message(RegistrationState.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    user_data = {
        "iin": data["iin"],
        "name": data["name"],
        "household_id": data["address"],
        "phone": message.text,
        "verified": 1,
        "tg_id": user_id
    }
    
    db.insert("users", user_data)
    await message.answer("✅ Registration successful!")
    await state.clear()

@dp.message(Command("invite"))
async def invite_users(message: Message):
    await message.answer("Send a list of @usernames to invite (comma-separated):")

@dp.message()
async def process_invites(message: Message):
    user_id = message.from_user.id
    usernames = [u.strip() for u in message.text.split(",")]
    household_id = db.fetch_column("users","household_id",{"tg_id": user_id})[0][0]
    invite_link = f"https://t.me/water_collect_bot?start=invite_{household_id}"
    await message.answer(f"Share these invite links:\n{invite_link}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
