from pyrogram import filters
from pyrogram.types import Message

from amdlbot import bot, database
from amdlbot.helpers.filters import sudo_cmd

@bot.on_message(filters.command("dbstats") & sudo_cmd)
async def dbstats(_, message: Message):
    """
    Returns database stats of PostgreSQL, which includes Total number
    of bot user and total number of bot chats.
    """
    cursor = database.scur(dictcur=True)
    try:
        cursor.execute("SELECT COUNT(*) FROM users")
        TotalUsers = cursor.fetchone()["count"]
        cursor.execute("SELECT COUNT(*) FROM chats")
        TotalChats = cursor.fetchone()["count"]
    finally:
        database.ccur(cursor)

    stats_string = f"**Bot Database Statics.\n\n**Total Number of users = {TotalUsers}\nTotal number of chats  = {TotalChats}"
    return await message.reply_text(stats_string)
