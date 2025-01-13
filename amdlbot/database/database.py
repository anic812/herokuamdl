from typing import Union
from datetime import datetime
import json
from pyrogram.types import Message
from amdlbot.config import DATABASE_URL
from .psql import DataBaseHandle
import psycopg2
import psycopg2.extras
from amdlbot.logging import LOGGER

class UserDB(DataBaseHandle):
    def __init__(self, dburl: str = DATABASE_URL) -> None:
        super().__init__(dburl)
        cur = self.scur()
        
        # Create tables only if they don't exist
        table_users = """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY NOT NULL,
            user_id VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            username VARCHAR(255) NULL,
            date TIMESTAMP NOT NULL,
            data JSONB NULL
        );
        -- Only create index if it doesn't exist
        CREATE INDEX IF NOT EXISTS users_user_id_idx ON users(user_id);
        """
        
        table_chats = """
        CREATE TABLE IF NOT EXISTS chats (
            id SERIAL PRIMARY KEY NOT NULL,
            chat_id VARCHAR(50) UNIQUE NOT NULL,
            date TIMESTAMP NOT NULL
        );
        -- Only create index if it doesn't exist
        CREATE INDEX IF NOT EXISTS chats_chat_id_idx ON chats(chat_id);
        """
        
        try:
            cur.execute(table_users)
            cur.execute(table_chats)
            self._conn.commit()
        except psycopg2.errors.UniqueViolation:
            # Ignore if tables/indices already exist
            pass
        finally:
            self.ccur(cur)

    async def save_user(self, user: Message, data: str) -> None:
        insert_format = {
            "name": (user.first_name or " ") + (user.last_name or ""),
            "username": user.username,
            "date": datetime.now(),
            "data": json.dumps({"upload_to": data})
        }
        cur = self.scur()
        try:
            cur.execute(
                """
                INSERT INTO users (user_id, name, username, date, data)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (user_id) DO UPDATE SET
                name = EXCLUDED.name,
                username = EXCLUDED.username,
                date = EXCLUDED.date,
                data = EXCLUDED.data;
                """,
                (str(user.id), insert_format["name"], insert_format["username"], insert_format["date"], insert_format["data"])
            )
            self._conn.commit()
        finally:
            self.ccur(cur)

    async def save_chat(self, chatid: Union[int, str]) -> None:
        insert_format = {"date": datetime.now()}
        cur = self.scur()
        try:
            cur.execute(
                """
                INSERT INTO chats (chat_id, date)
                VALUES (%s, %s)
                ON CONFLICT (chat_id) DO UPDATE SET
                date = EXCLUDED.date;
                """,
                (chatid, insert_format["date"]),
            )
            self._conn.commit()
        finally:
            self.ccur(cur)

    async def get_user_data(self, user_id: int) -> dict:
        cur = self.scur(dictcur=True)
        try:
            # Convert user_id to string since the column is VARCHAR
            cur.execute("SELECT * FROM users WHERE user_id = %s", (str(user_id),))
            user = cur.fetchone()
            return user if user else {}
        finally:
            self.ccur(cur)

    async def delete_user_data(self, user_id: int) -> None:
        cur = self.scur()
        try:
            # Convert user_id to string since the column is VARCHAR
            cur.execute("DELETE FROM users WHERE user_id = %s", (str(user_id),))
            self._conn.commit()
        finally:
            self.ccur(cur)

    async def get_all_user_ids(self) -> list:
        cur = self.scur(dictcur=True)
        try:
            cur.execute("SELECT user_id FROM users")
            # Convert returned strings back to integers
            return [int(row["user_id"]) for row in cur.fetchall()]
        finally:
            self.ccur(cur)

    async def get_all_chat_ids(self) -> list:
        cur = self.scur(dictcur=True)
        try:
            cur.execute("SELECT chat_id FROM chats")
            # Convert returned strings back to integers
            return [int(row["chat_id"]) for row in cur.fetchall()]
        finally:
            self.ccur(cur)
