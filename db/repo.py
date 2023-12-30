from asyncpg import Record
from typing import List, Optional

from collections import Counter


class Repo:
    """Db abstraction layer"""

    def __init__(self, conn):
        self.conn = conn

    async def create_user(self, uid):
        await self.conn.execute(
            "INSERT INTO users(id) VALUES($1) ON CONFLICT DO NOTHING",
            uid
        )

    async def get_count_attempts(self, uid):
        row = await self.conn.fetch(
            "SELECT count(*) FROM attempts WHERE id = $1",
            uid
        )
        return row

    async def get_sending_users(self) -> List[Record]:
        row = await self.conn.fetch(
            "SELECT id FROM users"
        )
        return row

    async def get_all_count_attempts(self) -> int:
        row = await self.conn.fetch(
            "SELECT count(*) FROM attempts"
        )
        return row[0]['count']

    async def get_count_users(self) -> int:
        row = await self.conn.fetch(
            "SELECT count(*) FROM users"
        )
        return row[0]['count']

    async def get_sending_users_2(self) -> List:
        row = await self.conn.fetch(
            "SELECT id FROM users"
        )
        return row

    async def add_attempt(self, uid):
        await self.conn.execute(
            "INSERT INTO attempts(uid) VALUES($1) ON CONFLICT DO NOTHING",
            uid
        )

    async def add_utm_user(self, uid, utm):
        await self.conn.execute(
            "INSERT INTO ads_utm(uid, utm) VALUES($1, $2) ON CONFLICT DO NOTHING",
            uid, utm
        )