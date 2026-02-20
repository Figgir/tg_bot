import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from fastapi import FastAPI
import uvicorn
import aiosqlite
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# -------------------- Настройки --------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
SECRET_KEY = os.getenv("SECRET_KEY").encode()
PORT = int(os.getenv("PORT", 8000))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()
cipher = Fernet(SECRET_KEY)
DB_NAME = "bot.db"

# -------------------- База данных --------------------
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            encrypted_user_id TEXT,
            user_message_id INTEGER,
            group_message_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.commit()

def encrypt_user_id(user_id: int) -> str:
    return cipher.encrypt(str(user_id).encode()).decode()

def decrypt_user_id(token: str) -> int:
    return int(cipher.decrypt(token.encode()).decode())

async def create_ticket(user_id, user_message_id, group_message_id):
    encrypted_id = encrypt_user_id(user_id)
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO tickets (encrypted_user_id, user_message_id, group_message_id) VALUES (?, ?, ?)",
            (encrypted_id, user_message_id, group_message_id)
        )
        await db.commit()
        return cursor.lastrowid

async def get_ticket_by_group_message(group_message_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT encrypted_user_id, user_message_id FROM tickets WHERE group_message_id = ?",
            (group_message_id,)
        )
        row = await cursor.fetchone()
        return (row[0], row[1]) if row else (None, None)

# -------------------- Обработчики --------------------
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer("Напишите сообщение")

@dp.message()
async def handle_messages(message: types.Message):
    if message.chat.type == "private":
        user_id = message.from_user.id

        # -------------------- Отправка в группу --------------------
        if message.text:
            sent = await bot.send_message(
                chat_id=GROUP_ID,
                text=message.text
            )
        elif message.photo:
            sent = await bot.send_photo(
                chat_id=GROUP_ID,
                photo=message.photo[-1].file_id,
                caption=message.caption or ""
            )
        elif message.video:
            sent = await bot.send_video(
                chat_id=GROUP_ID,
                video=message.video.file_id,
                caption=message.caption or ""
            )
        elif message.document:
            sent = await bot.send_document(
                chat_id=GROUP_ID,
                document=message.document.file_id,
                caption=message.caption or ""
            )
        elif message.voice:
            sent = await bot.send_voice(
                chat_id=GROUP_ID,
                voice=message.voice.file_id,
                caption=message.caption or ""
            )
        else:
            sent = await bot.copy_message(
                chat_id=GROUP_ID,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )

        # Сохраняем тикет с user_message_id
        ticket_number = await create_ticket(user_id, message.message_id, sent.message_id)

       # Отправляем в группу номер обращения
       #await bot.send_message(
       #   text=f"🎫 Обращение #{ticket_number}"
       # )

        await message.answer(f"✅ Ваше обращение отправлено.")

    elif message.chat.type in ["group", "supergroup"]:
        # -------------------- Ответ админа --------------------
        if message.reply_to_message:
            original_group_id = message.reply_to_message.message_id
            encrypted_id, user_message_id = await get_ticket_by_group_message(original_group_id)
            if encrypted_id:
                user_id = decrypt_user_id(encrypted_id)

                # Отправляем ответ **как reply на сообщение пользователя**
                await bot.send_message(
                    chat_id=user_id,
                    text=message.text or "[Медиа/Файл]",
                    reply_to_message_id=user_message_id
                )

# -------------------- FastAPI --------------------
@app.get("/")
async def health():
    return {"status": "ok"}

# -------------------- Запуск --------------------
async def main():
    await init_db()
    polling_task = asyncio.create_task(dp.start_polling(bot))
    uvicorn_config = uvicorn.Config(app, host="0.0.0.0", port=PORT)
    server = uvicorn.Server(uvicorn_config)
    await server.serve()
    await polling_task

if __name__ == "__main__":
    asyncio.run(main())
