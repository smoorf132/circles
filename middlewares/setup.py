from aiogram import Dispatcher

from middlewares.album_middleware import AlbumMiddleware
from middlewares.repo import RepoMiddleware


def setup_main_middlewares(dp: Dispatcher, pool):
    dp.update.middleware.register(RepoMiddleware(pool))
    dp.message.middleware.register((AlbumMiddleware()))
