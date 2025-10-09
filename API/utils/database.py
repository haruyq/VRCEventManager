import aiosqlite
import os
import json

from utils.logger import Logger
from connector.sender import Sender

Log = Logger(__name__)
USERS_DB_PATH = "/Database/users.db"

class UsersDB:
    @staticmethod
    async def init_db():
        async with aiosqlite.connect(USERS_DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS allowed_users (
                    user_id INTEGER NOT NULL,
                    email TEXT,
                    PRIMARY KEY (user_id)
                );
            """)
            await db.commit()
    
    @staticmethod
    async def get_allowed_users() -> dict:
        async with aiosqlite.connect(USERS_DB_PATH) as db:
            cursor = await db.execute("SELECT user_id FROM allowed_users")
            rows = await cursor.fetchall()
            await cursor.close()
            return [{"user_id": row[0]} for row in rows]

    @staticmethod
    async def add_allowed_user(user_id: int, email: str):
        async with aiosqlite.connect(USERS_DB_PATH) as db:
            await db.execute("INSERT INTO allowed_users (user_id, email) VALUES (?, ?)", (user_id, email))
            await db.commit()
    
    @staticmethod
    async def remove_allowed_user(user_id: int, guild_id: int):
        async with aiosqlite.connect(USERS_DB_PATH) as db:
            await db.execute("DELETE FROM allowed_users WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
            await db.commit()
    
    @staticmethod
    async def is_user_allowed(user_id: int, sender: Sender) -> bool:
        try:
            guild_id = int(os.environ.get("GUILD_ID", 0)) # GuildIDはいつか可変にするかも
            result: dict = await sender.send_async(
                json.dumps({
                    "action": "check_admin",
                    "user_id": user_id,
                    "guild_id": guild_id
                })
            )
        except Exception as e:
            Log.error(f"Error checking admin status: {e}", exc_info=True)
            return False

        message = result.get("message")
        is_admin = False
        if message and isinstance(message, dict):
            is_admin = message.get("is_admin", False)
            
        if is_admin:
            async with aiosqlite.connect(USERS_DB_PATH) as db:
                cursor = await db.execute(
                    "SELECT 1 FROM allowed_users WHERE user_id = ?",
                    (user_id,)
                )
                row = await cursor.fetchone()
                await cursor.close()
                return row is not None
            
        return False