import aiosqlite
from cryptography.fernet import Fernet
import os

DB_NAME = "bot.db"
SECRET_KEY = os.getenv("SECRET_KEY").encode()
cipher = Fernet(SECRET_KEY)


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            encrypted_user_id TEXT,
            group_message_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.commit()


def encrypt_user_id(user_id: int) -> str:
    return cipher.encrypt(str(user_id).encode()).decode()


def decrypt_user_id(token: str) -> int:
    return int(cipher.decrypt(token.encode()).decode())


async def create_ticket(user_id, group_message_id):
    encrypted_id = encrypt_user_id(user_id)

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO tickets (encrypted_user_id, group_message_id) VALUES (?, ?)",
            (encrypted_id, group_message_id)
        )
        await db.commit()
        ticket_number = cursor.lastrowid

    return ticket_number


async def get_ticket_by_group_message(group_message_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT encrypted_user_id FROM tickets WHERE group_message_id = ?",
            (group_message_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None
