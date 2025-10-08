import aiosqlite

USERS_DB_PATH = "/Database/users.db"

class UsersDB:
    @staticmethod
    async def init_db():
        async with aiosqlite.connect(USERS_DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS allowed_users (
                    user_id INTEGER PRIMARY KEY
                )
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
    async def add_allowed_user(user_id: int):
        async with aiosqlite.connect(USERS_DB_PATH) as db:
            await db.execute("INSERT INTO allowed_users (user_id) VALUES (?)", (user_id,))
            await db.commit()
        
    @staticmethod
    async def is_user_allowed(user_id: int) -> bool:
        async with aiosqlite.connect(USERS_DB_PATH) as db:    
            cursor = await db.execute("SELECT 1 FROM allowed_users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            await cursor.close()
            return row is not None