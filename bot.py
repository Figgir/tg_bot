import asyncio
import os
import time
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from fastapi import FastAPI
import uvicorn

from database import init_db, create_ticket, get_ticket_by_group_message, decrypt_user_id

TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()
app = FastAPI()

last_message_time = {}
SPAM_DELAY = 10


@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer("""
    🙏 Добро пожаловать в молитвенный бот! 
    Напишите ниже вашу молитвенную нужду или свидетельство.""")


@dp.message()
async def handle_messages(message: Message):

    if message.chat.type == "private":

        user_id = message.from_user.id
        now = time.time()

        if user_id in last_message_time:
            if now - last_message_time[user_id] < SPAM_DELAY:
               # await message.answer("⏳ Подождите немного перед следующим сообщением.")
                return

        last_message_time[user_id] = now

        sent = await bot.copy_message(
            chat_id=GROUP_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )

        ticket_number = await create_ticket(user_id, sent.message_id)

        try:
            await bot.edit_message_caption(
                chat_id=GROUP_ID,
                message_id=sent.message_id,
                caption=f"🎫 Обращение #{ticket_number}"
            )
        except:
            await bot.edit_message_text(
                chat_id=GROUP_ID,
                message_id=sent.message_id,
                text=f"🎫 Обращение #{ticket_number}"
            )

        await message.answer(f"✅ Ваше сообщение отправлено.")


    elif message.chat.type in ["group", "supergroup"]:

        if message.reply_to_message:

            original_id = message.reply_to_message.message_id
            encrypted_id = await get_ticket_by_group_message(original_id)

            if encrypted_id:
                user_id = decrypt_user_id(encrypted_id)

                await bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id
                )


@app.get("/")
async def health():
    return {"status": "ok"}


async def main():
    await init_db()
    asyncio.create_task(dp.start_polling(bot))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
