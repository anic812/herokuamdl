from pyrogram import filters
from pyrogram.types import Message

from amdlbot import bot, database
from amdlbot.helpers.filters import sudo_cmd

@bot.on_message(filters.command(["delete_user_data"]) & sudo_cmd)
async def delete_user_data_cmd(_, message: Message):
    """Delete the user data from the database."""

    if len(message.command) != 2:
        return await message.reply_text("Usage: /delete_user_data <user_id>", quote=True)

    user_id = int(message.command[1])
    await database.delete_user_data(user_id)
    return await message.reply_text(f"Deleted data for user {user_id}.", quote=True)
