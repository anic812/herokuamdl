from amdlbot.plugins.users.am_dl import main
from amdlbot.helpers.config import Config
from pathlib import Path
from amdlbot.helpers.utils import FileUploader
from os import remove
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from amdlbot import bot, database
from amdlbot.helpers.filters import is_ratelimited
import asyncio

async def upload_file(file_path: Path, platform: str, note: str, id: str, message: Message) -> str:
    if platform == "BuzzHeavier":
        uploader = FileUploader()
        return uploader.upload_file(str(file_path), note)
    elif platform == "Telegram":
        await message.reply_document(file_path, caption=f"{id}.zip", file_name=f"{id}.zip")
        return "Uploaded to Telegram"
    else:
        raise Exception("Unsupported platform")

@bot.on_message(filters.command(["download"]) & is_ratelimited)
async def download(_, message: Message):
    url = message.text.split(maxsplit=1)[1]
    config_instance = Config()
    status_message = await message.reply_text("Starting download...")

    file_path = None
    try:
        id = await main(config_instance, url, status_message, zip_file=True)
        file_path = Path(f"downloads/{id}.zip")
        print("ok")
        user_data = await database.get_user_data(message.from_user.id)
        upload_to = user_data.get("data", {}).get("upload_to")

        await status_message.edit_text(f"Uploading to {upload_to}...")
        download_link = await upload_file(file_path, upload_to, "Uploaded from kvt BOT", id, message)
        if not download_link:
            raise Exception(f"Failed to get download link from {upload_to}!")
        
        await status_message.edit_text(f"Successfully Uploaded to {upload_to}: {download_link}")
        
    except FloodWait as e:
        await asyncio.sleep(e.x)
        await download(_, message)
    except Exception as e:
        await status_message.edit_text(f"ERROR: {e}")
    finally:
        if file_path and file_path.exists():
            remove(file_path)