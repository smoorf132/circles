import datetime
from typing import Callable, Dict, Any, Awaitable, Union

from aiogram import BaseMiddleware
from aiogram.types import Update, ChatJoinRequest
from asyncpg import create_pool
import aiogram
from aiogram import Bot
import random
from db.repo import Repo
import asyncio


class RepoMiddleware(BaseMiddleware):
    def __init__(self, pool) -> None:
        self.pool = pool

    async def __call__(
            self,
            handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: Dict[str, Any],
    ) -> Any:
        async with self.pool.acquire() as session:
            data["repo"] = Repo(session)
            return await handler(event, data)
