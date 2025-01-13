from pyrogram import filters
from pyrogram.types import Message
from pyrogram.errors import MessageTooLong

from amdlbot import bot
from amdlbot.helpers.filters import sudo_cmd
from amdlbot.helpers.pasting_services import katbin_paste


@bot.on_message(filters.command("inspect") & sudo_cmd)
async def inspect(_, message: Message):
    """Inspects the message and give reply in json format."""

    try:
        return await message.reply_text(message, quote=True)
    except MessageTooLong:
        output = await katbin_paste(message)
        return await message.reply_text(output, quote=True)
