import psycopg2
import psycopg2.extras

from amdlbot.logging import LOGGER
from amdlbot.config import DATABASE_URL as dburl


import time


class DataBaseHandle:
    _active_connections = []
    _connection_users = []

    def __init__(self, dburl: str = None) -> None:
        """Load the DB URL if available

        Args:
            dburl (str, optional): The database URI to connect to. Defaults to None.
        """

        self._dburl = dburl

        if isinstance(self._dburl, bool):
            self._block = True
        else:
            self._block = False

        if self._block:
            return

        if self._active_connections:
            self._conn = self._active_connections[0]
            self._connection_users.append(1)
        else:
            LOGGER(__name__).debug("Established Connection")
            self._conn = psycopg2.connect(self._dburl, sslmode='require')
            self._connection_users.append(1)
            self._active_connections.append(self._conn)

    def scur(self, dictcur: bool = False) -> psycopg2.extensions.cursor:
        """Starts a new cursor for the connection.

        Args:
            dictcur (bool, optional): If this is true the returned cursor
            is in dict form insted of list. Defaults to False.

        Returns:
            psycopg2.extensions.cursor: A cursor to execute sql queries.
        """

        cur = None
        for i in range(0, 5):
            try:
                if dictcur:
                    cur = self._conn.cursor(
                        cursor_factory=psycopg2.extras.DictCursor)
                else:
                    cur = self._conn.cursor()
                break

            except psycopg2.InterfaceError as e:
                LOGGER(__name__).info(f"Attempting to Re-establish the connection to server {i} times. {e}")
                self.re_establish()

        return cur

    def re_establish(self) -> None:
        """Re tries to connect to the database if in any case it disconnects.
        """

        try:
            if self._active_connections[0].closed != 0:
                LOGGER(__name__).info("Re-establish Success.")
                self._conn = psycopg2.connect(self._dburl)
                self._active_connections[0] = self._conn
            else:
                LOGGER(__name__).info("Re-establish Success Cache.")
                self._conn = self._active_connections[0]
        except:
            time.sleep(1)  # Blocking call ... this stage is panic.

    def ccur(self, cursor: psycopg2.extensions.cursor) -> None:
        """Closes the cursor that is passed to it.

        Args:
            cursor (psycopg2.extensions.cursor): The cursor that needs to be closed.
        """

        if cursor is not None:
            self._conn.commit()
            cursor.close()

    def get_all_user_ids(self) -> list:
        """Return list of all user ids in the users table."""
        cur = self.scur(dictcur=True)
        try:
            cur.execute("SELECT user_id FROM users")
            return [row["user_id"] for row in cur.fetchall()]
        finally:
            self.ccur(cur)

    def get_all_chat_ids(self) -> list:
        """Return list of all chat ids in the chats table."""
        cur = self.scur(dictcur=True)
        try:
            cur.execute("SELECT chat_id FROM chats")
            return [row["chat_id"] for row in cur.fetchall()]
        finally:
            self.ccur(cur)

    def __del__(self):
        """Close connection so that it will not overload the database server..
        """

        if self._block:
            return
        self._connection_users.pop()

        if not self._connection_users:
            self._conn.close()
