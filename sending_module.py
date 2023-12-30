import asyncio
import datetime
import random
import time
from typing import Union, List

import ujson
from aiogram import types
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import ContentType, Message
from pydantic import parse_obj_as

from config import bot

InputMedia = Union[
    types.InputMediaPhoto, types.InputMediaVideo,
    types.InputMediaAudio, types.InputMediaDocument
]

SEND_METHODS = {
    ContentType.ANIMATION: "send_animation",
    ContentType.AUDIO: "send_audio",
    ContentType.DOCUMENT: "send_document",
    ContentType.PHOTO: "send_photo",
    ContentType.VIDEO: "send_video",
    ContentType.VIDEO_NOTE: "send_video_note",
    ContentType.STICKER: "send_sticker",
    ContentType.VOICE: "send_voice",
    'text': "send_message"}


def get_file_id(message: Message):
    if not message.text:
        if message.document:
            return message.document.file_id
        elif message.photo:
            return message.photo[-1].file_id
        elif message.video:
            return message.video.file_id
        elif message.voice:
            return message.voice.file_id
        elif message.audio:
            return message.audio.file_id
        elif message.video_note:
            return message.video_note.file_id
        else:
            return message.animation.file_id
    else:
        return None


async def send_any_msg(msg, chat_id, markup=None):
    if msg.sticker:
        file_id = msg.sticker.file_id
        return await bot.send_sticker(chat_id=chat_id, sticker=file_id,
                                      reply_markup=markup if markup else None)
    text = msg.html_text
    if msg.video or msg.animation or msg.photo or msg.video_note or msg.voice or msg.audio or msg.poll:
        media = get_file_id(msg)
        method = getattr(bot, SEND_METHODS[msg.content_type], None)
        print(media)
        if msg.video_note or msg.voice:
            return await method(
                chat_id,
                media,
                reply_markup=markup if markup else None,
            )
        else:
            return await method(
                chat_id,
                media,
                caption=text,
                reply_markup=markup,
                has_spoiler=False
            )
    if msg.dice:
        return await bot.send_dice(chat_id=chat_id)
    if msg.text:
        return await bot.send_message(chat_id=chat_id, text=text,
                                      reply_markup=markup if markup else None,
                                      disable_web_page_preview=True)
    else:
        raise ValueError('Неподдерживаемый тип поста')


class TestSending:
    def __init__(self, message, users):
        self.cid = 12313
        self.users = users
        self.all_count = 0
        self.ban_count = 0
        self.last_second_count = 0
        self.message = message
        self.current_second = datetime.datetime.second
        self.lock = asyncio.Lock()
        self.limit_per_sec = 24
        self.file = None

    async def init_sessions(self):
        self.sessions = None

    async def send(self, num):
        try:
            await send_any_msg(self.message, num['user_id'], markup=self.message.reply_markup)
            self.all_count += 1
        except Exception as e:
            self.all_count += 1
            self.ban_count += 1
            print(e)

    async def send_group(self, num, media_group):
        try:
            await bot.send_media_group(num['user_id'], media=media_group)
            self.all_count += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except Exception as e:
            self.all_count += 1
            self.ban_count += 1
            print(e)

    async def worker(self):
        await self.init_sessions()
        time1 = time.time()
        progress_text = "Получили рассылку: {}\n" \
                        "Заблокировали бота: {}"
        await bot.send_message(chat_id=self.message.from_user.id,
                               text='Рассылка запущена')
        progress_msg = await bot.send_message(chat_id=self.message.from_user.id,
                                              text=progress_text.format(self.all_count - self.ban_count,
                                                                        self.ban_count))
        for i in self.users:
            async with self.lock:
                if self.last_second_count >= self.limit_per_sec and datetime.datetime.second == self.current_second:
                    await asyncio.sleep(1)
                    self.last_second_count = 0
                    self.current_second = datetime.datetime.second
                    if random.randint(1, 10) == 3:
                        try:
                            await bot.edit_message_text(
                                text=progress_text.format(self.all_count - self.ban_count, self.ban_count),
                                chat_id=progress_msg.chat.id, message_id=progress_msg.message_id)
                        except:
                            pass
                else:
                    asyncio.create_task(self.send(i))
                    print(i)
                    self.last_second_count += 1
        try:
            await bot.edit_message_text(text=progress_text.format(self.all_count - self.ban_count, self.ban_count),
                                        chat_id=progress_msg.chat.id, message_id=progress_msg.message_id)
        except:
            pass
        await bot.send_message(chat_id=self.message.from_user.id,
                               text='Рассылка была успешно завершена')
        print('=============== success ============')
        print(self.all_count)
        print(time.time() - time1, self.all_count)

    async def group_worker(self, user_id: int):
        await self.init_sessions()
        time1 = time.time()
        progress_text = "Получили рассылку: {}\n" \
                        "Заблокировали бота: {}"
        await bot.send_message(chat_id=user_id,
                               text='Рассылка запущена')
        progress_msg = await bot.send_message(chat_id=user_id,
                                              text=progress_text.format(self.all_count - self.ban_count,
                                                                        self.ban_count))
        media_group_unpack = ujson.loads(self.message)
        media_group = parse_obj_as(List[InputMedia], media_group_unpack)
        print(media_group)

        for i in self.users:
            async with self.lock:
                if self.last_second_count >= self.limit_per_sec and datetime.datetime.second == self.current_second:
                    await asyncio.sleep(1)
                    self.last_second_count = 0
                    self.current_second = datetime.datetime.second
                    if random.randint(1, 10) == 3:
                        try:
                            await bot.edit_message_text(
                                text=progress_text.format(self.all_count - self.ban_count, self.ban_count),
                                chat_id=progress_msg.chat.id, message_id=progress_msg.message_id)
                        except:
                            pass
                else:
                    asyncio.create_task(self.send_group(i, media_group))
                    print(i)
                    self.last_second_count += 1
        try:
            await bot.edit_message_text(text=progress_text.format(self.all_count - self.ban_count, self.ban_count),
                                        chat_id=progress_msg.chat.id, message_id=progress_msg.message_id)
        except:
            pass
        await bot.send_message(chat_id=user_id,
                               text='Рассылка была успешно завершена')
        print('=============== success ============')
        print(self.all_count)
        print(time.time() - time1, self.all_count)
