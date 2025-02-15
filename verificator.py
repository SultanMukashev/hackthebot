from telethon import TelegramClient
import random
import asyncio
from decouple import config
# Replace with your actual API credentials from https://my.telegram.org/apps
API_ID = config("API_ID")
API_HASH = config("API_HASH")

async def send_verification(tag, address):
    async with TelegramClient("session_name", API_ID, API_HASH) as client:
        
        try:
            # Get user entity from phone number
            user = await client.get_entity(tag)

            # Send the verification message
            message = f"Вас хотят добавить в прописку по адресу {address}. Вы подтверждаете это действие?"
            await client.send_message(user, message)
            # print(f"Код {verification_code} отправлен на {tag}")

        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")


