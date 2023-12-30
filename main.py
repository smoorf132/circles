import asyncio
import logging
import os
from typing import List

import aiofiles
import aiogram.filters
import asyncpg
import ujson
from aiogram import Bot, Dispatcher, types
from aiogram import F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, InlineKeyboardButton, KeyboardButton, CallbackQuery
from aiogram.types import Message
from aiogram.utils.keyboard import KeyboardBuilder
from aiogram.utils.media_group import MediaGroupBuilder

from db.repo import Repo
from middlewares.setup import setup_main_middlewares
from sending_module import TestSending

TOKEN = "6179056274:AAF86swPHkVF3MNoJp9HhImZQw7qeBfSNtw"
dp = Dispatcher()
logger = logging.getLogger(__name__)

session = AiohttpSession()
bot = Bot(TOKEN, parse_mode="html")

CIDS = [[-1001345824533, 'https://t.me/+TdB59i41avA4M2Ji'],
        [-1001508161723, 'https://t.me/+cNPd-HPsqEY1YmIy']]  # крупный


class Mailing(StatesGroup):
    waiting_for_message = State()
    album_state = State()


async def create_pool(user, password, database, host):
    pool = await asyncpg.create_pool(database=database,
                                     user=user,
                                     password=password,
                                     host=host,
                                     max_inactive_connection_lifetime=1,
                                     max_size=100
                                     )
    return pool


def conv_kb():
    channels_two = KeyboardBuilder(button_type=KeyboardButton)
    channel_key = KeyboardButton(text='📥 Конвертировать')
    channels_two.add(channel_key)
    return channels_two.as_markup(resize_keyboard=True)


async def subscription_check(user_id):
    channels_two = KeyboardBuilder(button_type=InlineKeyboardButton)
    for CID in CIDS:
        if (await bot.get_chat_member(CID[0], user_id)).status == 'left':
            channel_key = InlineKeyboardButton(text='🎯 Подписаться', url=CID[1])
            channels_two.row(channel_key, width=1)
        else:
            pass
    menu = InlineKeyboardButton(text='Проверить подписку 🔄', callback_data="CheckSub")
    channels_two.row(menu, width=1)
    return channels_two.as_markup()


async def checker(uid):
    for CID in CIDS:
        if (await bot.get_chat_member(CID[0], uid)).status == 'left':
            return 'bad'
    return 'good'


async def o_p(message: Message):
    await message.answer('Для использования бота нужно быть подписанным на наши каналы!\n\n'
                         'Подпишись и нажми кнопку «Проверить подписку»',
                         reply_markup=await subscription_check(message.from_user.id))


@dp.message(Command(commands=["admin_mailing"]))
async def command_mailing_handler(message: Message, state: FSMContext) -> None:
    await message.answer(f"Отправьте сообщение для рассылки")
    await state.set_state(Mailing.waiting_for_message)


def approve_mailing_kb():
    channels_two = KeyboardBuilder(button_type=InlineKeyboardButton)
    menu = InlineKeyboardButton(text='🔥Уверен', callback_data="mailing_approve")
    channels_two.row(menu, width=1)
    return channels_two.as_markup()


@dp.message(Command(commands=["start"]))
async def command_start_handler(message: Message, state: FSMContext) -> None:
    """
    await repo.create_user(message.from_user.id)
    if await checker(message.from_user.id) == 'bad':
        await o_p(message)
        return"""
    await message.answer(f"""Привет, <b>{message.from_user.full_name}!</b>

С моей помощью ты можешь превратить любое свое обычное видео в видеосообщение!

Нажми на кнопку ниже, чтобы продолжить 👇""", reply_markup=conv_kb())
    await state.clear()


@dp.message(Mailing.waiting_for_message, F.media_group_id)
async def mailing_media_group(
        message: Message,
        state: FSMContext,
        album: List[Message]
):
    await state.set_state(Mailing.album_state)
    builder = MediaGroupBuilder()
    for element in album:
        caption_kwargs = {"caption": element.html_text, "caption_entities": element.caption_entities,
                          "parse_mode": "html"}
        if element.photo:
            builder.add_photo(media=element.photo[-1].file_id, **caption_kwargs)
        elif element.video:
            builder.add_video(media=element.video.file_id, **caption_kwargs)
        elif element.document:
            builder.add_document(media=element.document.file_id, **caption_kwargs)
        elif element.audio:
            builder.add_audio(media=element.audio.file_id, **caption_kwargs)
        else:
            return message.answer("This media type isn't supported!")

    album_list_pack = [model.model_dump() for model in builder.build()]
    album_pack = ujson.dumps(album_list_pack)
    print(album_pack)
    await state.update_data(album_pack=album_pack)
    await message.answer('Вы уверены, что хотите запустить рассылку?\n\n'
                         'Остановить её можно будет только написав разработчику.',
                         reply_markup=approve_mailing_kb())


@dp.message(Mailing.waiting_for_message)
async def mailing_message(
        message: Message,
        state: FSMContext,
):
    await message.answer('Вы уверены, что хотите запустить рассылку?\n\n'
                         'Остановить её можно будет только написав разработчику.',
                         reply_markup=approve_mailing_kb())
    await state.update_data(mailing_message=message.model_dump_json())


@dp.callback_query(Mailing.album_state, F.data == 'mailing_approve')
async def mailing_group_approver(call: CallbackQuery,
                                 state: FSMContext, repo: Repo):
    await call.message.edit_text('Рассылка запускается')
    user_data = await state.get_data()
    to_mailing_message = user_data.get('album_pack')
    users = await repo.get_sending_users()
    task = TestSending(to_mailing_message, users)
    asyncio.create_task(task.group_worker(call.from_user.id))


@dp.callback_query(F.data == 'mailing_approve')
async def mailing_approver(call: CallbackQuery,
                           state: FSMContext, repo: Repo):
    await call.message.edit_text('Рассылка запускается')
    user_data = await state.get_data()
    to_mailing_message = Message.model_validate_json(user_data.get('mailing_message'))
    users = await repo.get_sending_users()
    task = TestSending(to_mailing_message, users)
    asyncio.create_task(task.worker())


@dp.message(Command(commands=["admin_users"]))
async def command_answer_handler(message: Message, state: FSMContext, repo: Repo) -> None:
    attempts_all = await repo.get_all_count_attempts()
    users = await repo.get_count_users()
    await message.answer(f"Юзеров в боте: {users}\n"
                         f"Попыток всего: {attempts_all}\n")
    await state.clear()


@dp.message(Command(commands=["help"]))
async def command_help_handler(message: Message) -> None:
    await message.answer(f"""
    Инструкция: <a href="https://telegra.ph/FAQ-Kruzhki-dlya-dialogov-01-27-2">Как сделать кружочек?</a>

Если возникли другие вопросы - @lazarenko_tg""")


@dp.callback_query(F.data == 'CheckSub')
async def call_checker(call: aiogram.types.CallbackQuery):
    if await checker(call.from_user.id) == 'bad':
        await call.answer('Вы не выполнили все условия', show_alert=True)
        return
    else:
        await call.answer('Отлично, теперь вы можете пользоваться ботом', )
        await call.message.delete()
        await call.message.answer("""<b>Отправьте мне любое видео, которое хотите загрузить в формате кружочка.</b>

❗️ <b>Обратите внимание:</b> <i>чтобы получился кругляшок – видео при загрузке должно быть обязательно квадратным.

Для этого обрежьте видео при загрузке.

⏳ Длительность видео - до 60 сек.</i>

<b>Если у вас возникли затруднения - воспользуйтесь командой /help</b>""",
                                  reply_markup=conv_kb())


@dp.message(F.video)
async def echo_handler(message: types.Message) -> None:
    if await checker(message.from_user.id) == 'bad':
        await o_p(message)
        return
    try:
        height = message.video.height
        width = message.video.width
        if height != width:
            await message.answer('🔗Видео принимаются только в формате 1:1\n\n'
                                 '<b>Смотри <a href="https://telegra.ph/FAQ-Kruzhki-dlya-dialogov-01-27-2">'
                                 'инструкцию!</a></b>')
            return
        elif height > 640 or width > 640:
            await message.answer('❌ Ширина или высота видео больше чем 640.\n'
                                 'Размеры вашего видео {}x{} (ШxВ), а должны быть меньше 640'.format(width, height))
        else:
            m = await message.answer('🔄Конвертирую видео\n'
                                     '<i>Обычно это занимает от 10 до 20 секунд</i>')
            file_info = await bot.get_file(message.video.file_id)
            print(file_info.file_path)
            downloaded_file = await bot.download_file(file_info.file_path)
            filename = f'{file_info.file_id}.{"mp4"}'
            src = file_info.file_id + filename
            async with aiofiles.open(src, 'wb') as new_file:
                await new_file.write(downloaded_file.read())
            vd = FSInputFile(path=src)
            await m.delete()
            await message.answer_video_note(video_note=vd)
            os.remove(src)
            await message.answer('Видео успешно конвертировано! 👆')
    except TypeError:
        await message.answer("Nice try!")


@dp.message(F.text)
async def echo(message: types.Message) -> None:
    await message.answer("""<b>Отправьте мне любое видео, которое хотите загрузить в формате кружочка.</b>

❗️ <b>Обратите внимание:</b> <i>чтобы получился кругляшок – видео при загрузке должно быть обязательно квадратным.

Для этого обрежьте видео при загрузке.

⏳ Длительность видео - до 60 сек.</i>

<b>Если у вас возникли затруднения - воспользуйтесь командой /help</b>""")


async def on_startup(dispatcher: Dispatcher):
    pool = await create_pool(
        user='circle_user',
        password='Haxonebot123',
        database='tg_circles',
        host='185.174.136.21'
    )
    setup_main_middlewares(dispatcher, pool)


def main() -> None:
    # And the run events dispatching
    dp.startup.register(on_startup)
    dp.run_polling(bot)


if __name__ == "__main__":
    main()
