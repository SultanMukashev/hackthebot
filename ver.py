from telethon import TelegramClient, events, Button
import asyncio

from decouple import config
# Replace with your actual API credentials from https://my.telegram.org/apps
API_ID = config("API_ID")
API_HASH = config("API_HASH")

async def send_verification(client, tag, address):
    try:
        # Get user entity from phone number or username
        user = await client.get_entity(tag)

        # Message text
        message = f"Вас хотят добавить в прописку по адресу {address}. Вы подтверждаете это действие?"

        # Inline buttons
        buttons = [
            [Button.inline("✅ Подтверждаю", b"confirm"), Button.inline("❌ Отменить", b"cancel")]
        ]

        # Send the message with buttons and save the sent message object
        sent_message = await client.send_message(user, message, buttons=buttons)

        return sent_message  # Return message object to track it later

    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")
        return None

async def verify(tag, address):
    # tag = input("Введите номер телефона в формате +123456789: ")
    # address = "Aqorda15"

    async with TelegramClient("session_name", API_ID, API_HASH) as client:
        
        # Send verification message and store the message object
        sent_message = await send_verification(client, tag, address)

        if not sent_message:
            return

        # Start listening for button clicks
        @client.on(events.CallbackQuery)
        async def handler(event):
            if event.data == b"confirm":
                response_text = "✅ Вы были успешно добавлены в базу данных!"
            elif event.data == b"cancel":
                response_text = "❌ Спасибо за ответ. Ваше действие отменено."

            # Edit the original message to remove buttons
            await sent_message.edit(sent_message.text + "\n\n(Ответ получен ✅)", buttons=None)

            # Send a follow-up message with the response
            await event.respond(response_text)

        print("Ожидание ответа пользователя...")
        await client.run_until_disconnected()  # Keep running to listen for button clicks

# Run the async function
# asyncio.run(main())