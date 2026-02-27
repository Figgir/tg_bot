import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv

# -------------------- Настройки --------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
PORT = int(os.getenv("PORT", 8000))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

# -------------------- Обработчики --------------------
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        "Привет 👋\n"
        "Отправьте сообщение, и оно будет переслано в чат."
    )

@dp.message()
async def handle_messages(message: types.Message):
    # Пересылаем только из личных сообщений
    if message.chat.type == "private":
        await bot.copy_message(
            chat_id=GROUP_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )

# -------------------- FastAPI --------------------
@app.get("/")
async def health():
    return {"status": "ok"}

# -------------------- Запуск --------------------
async def main():
    polling_task = asyncio.create_task(dp.start_polling(bot))
    uvicorn_config = uvicorn.Config(app, host="0.0.0.0", port=PORT)
    server = uvicorn.Server(uvicorn_config)
    await server.serve()
    await polling_task

if __name__ == "__main__":
    asyncio.run(main())
