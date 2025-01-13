from pyrogram import filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from pyrogram.errors import UserNotParticipant, ChatAdminRequired

from amdlbot import bot, database
from amdlbot.helpers.filters import is_ratelimited
from amdlbot.config import OWNER_USERID, SUDO_USERID
from amdlbot.helpers.start_constants import (
    START_CAPTION,
    USER_TEXT,
    COMMAND_CAPTION,
    ABOUT_CAPTION,
    DEV_TEXT,
    SUDO_TEXT,
)


START_BUTTON = [
    [
        InlineKeyboardButton("📖 Commands", callback_data="COMMAND_BUTTON"),
        InlineKeyboardButton("👨‍💻 About me", callback_data="ABOUT_BUTTON"),
    ],
    # [
    #     InlineKeyboardButton(
    #         "🔭 Original Repo",
    #         url="https://github.com/sanjit-sinha/amdlbot-Boilerplate",
    #     )
    # ],
]


COMMAND_BUTTON = [
    [
        InlineKeyboardButton("Users", callback_data="USER_BUTTON"),
        InlineKeyboardButton("Admin", callback_data="SUDO_BUTTON"),
    ],
    #[InlineKeyboardButton("Devs", callback_data="DEV_BUTTON")],
    [InlineKeyboardButton("Settings", callback_data="SETTINGS_BUTTON")],
    [InlineKeyboardButton("🔙 Go Back", callback_data="START_BUTTON")],
]


GOBACK_1_BUTTON = [[InlineKeyboardButton("🔙 Go Back", callback_data="START_BUTTON")]]
GOBACK_2_BUTTON = [[InlineKeyboardButton("🔙 Go Back", callback_data="COMMAND_BUTTON")]]


CHANNEL_USERNAME = "gomikoneko"

async def check_subscription(user_id: int) -> bool:
    try:
        user = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if user.status == "left":
            raise UserNotParticipant
        return True
    except UserNotParticipant:
        return False
    except ChatAdminRequired:
        return None


@bot.on_message(filters.command(["start", "help"]) & is_ratelimited)
async def start(_, message: Message):
    is_subscribed = await check_subscription(message.from_user.id)
    if is_subscribed is False:
        return await message.reply_text(
            "You must join our channel to use this bot.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME}")]]
            ),
            quote=True,
        )
    elif is_subscribed is None:
        return await message.reply_text(
            "Bot needs to be an admin in the channel to check membership status.",
            quote=True,
        )
    await database.save_user(message.from_user, "Telegram")  # Default data
    return await message.reply_text(
        START_CAPTION, reply_markup=InlineKeyboardMarkup(START_BUTTON), quote=True
    )


def get_settings_buttons(current_platform: str) -> list:
    telegram_emoji = "🏸" if current_platform == "Telegram" else ""
    buzzheavier_emoji = "🏸" if current_platform == "BuzzHeavier" else ""

    return [
        [
            InlineKeyboardButton(f"{telegram_emoji} Telegram {telegram_emoji}", callback_data="SETTINGS_TELEGRAM"),
            InlineKeyboardButton(f"{buzzheavier_emoji} BuzzHeavier {buzzheavier_emoji}", callback_data="SETTINGS_BUZZHEAVIER"),
        ],
        [InlineKeyboardButton("🔙 Go Back", callback_data="COMMAND_BUTTON")],
    ]


@bot.on_message(filters.command(["settings"]) & is_ratelimited)
async def settings(_, message: Message):
    is_subscribed = await check_subscription(message.from_user.id)
    if is_subscribed is False:
        return await message.reply_text(
            "You must join our channel to use this bot.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME}")]]
            ),
            quote=True,
        )
    elif is_subscribed is None:
        return await message.reply_text(
            "Bot needs to be an admin in the channel to check membership status.",
            quote=True,
        )

    user_data = await database.get_user_data(message.from_user.id)
    current_platform = user_data.get("data", {}).get("upload_to")

    await message.reply_text(
        f"Choose your preferred Uploading (current: {current_platform}):",
        reply_markup=InlineKeyboardMarkup(get_settings_buttons(current_platform)),
        quote=True,
    )


@bot.on_callback_query(filters.regex("SETTINGS_"))
async def settings_callback(_, CallbackQuery: CallbackQuery):
    platform = "Telegram" if CallbackQuery.data == "SETTINGS_TELEGRAM" else "BuzzHeavier"
    await database.save_user(CallbackQuery.from_user, platform)
    await CallbackQuery.answer(f"OK!! will upload to {platform}.", show_alert=True)

    await CallbackQuery.edit_message_text(
        f"Your Uploading set to {platform}.",
        reply_markup=InlineKeyboardMarkup(get_settings_buttons(platform)),
    )


@bot.on_callback_query(filters.regex("_BUTTON"))
async def botCallbacks(_, CallbackQuery: CallbackQuery):

    is_subscribed = await check_subscription(CallbackQuery.from_user.id)
    if is_subscribed is False:
        return await CallbackQuery.answer(
            "You must join our channel to use this bot.",
            show_alert=True,
        )
    elif is_subscribed is None:
        return await CallbackQuery.answer(
            "Bot needs to be an admin in the channel to check membership status.",
            show_alert=True,
        )

    clicker_user_id = CallbackQuery.from_user.id
    user_id = CallbackQuery.message.reply_to_message.from_user.id

    if clicker_user_id != user_id:
        return await CallbackQuery.answer(
            "This command is not initiated by you.", show_alert=True
        )

    if CallbackQuery.data == "SUDO_BUTTON":
        if clicker_user_id not in SUDO_USERID:
            return await CallbackQuery.answer(
                "You are not in the sudo user list.", show_alert=True
            )
        await CallbackQuery.edit_message_text(
            SUDO_TEXT, reply_markup=InlineKeyboardMarkup(GOBACK_2_BUTTON)
        )

    elif CallbackQuery.data == "DEV_BUTTON":
        if clicker_user_id not in OWNER_USERID:
            return await CallbackQuery.answer(
                "This is developer restricted command.", show_alert=True
            )
        await CallbackQuery.edit_message_text(
            DEV_TEXT, reply_markup=InlineKeyboardMarkup(GOBACK_2_BUTTON)
        )

    if CallbackQuery.data == "ABOUT_BUTTON":
        await CallbackQuery.edit_message_text(
            ABOUT_CAPTION, reply_markup=InlineKeyboardMarkup(GOBACK_1_BUTTON)
        )

    elif CallbackQuery.data == "START_BUTTON":
        await CallbackQuery.edit_message_text(
            START_CAPTION, reply_markup=InlineKeyboardMarkup(START_BUTTON)
        )

    elif CallbackQuery.data == "COMMAND_BUTTON":
        await CallbackQuery.edit_message_text(
            COMMAND_CAPTION, reply_markup=InlineKeyboardMarkup(COMMAND_BUTTON)
        )

    elif CallbackQuery.data == "USER_BUTTON":
        await CallbackQuery.edit_message_text(
            USER_TEXT, reply_markup=InlineKeyboardMarkup(GOBACK_2_BUTTON)
        )

    elif CallbackQuery.data.startswith("SETTINGS_"):
        platform = "Telegram" if CallbackQuery.data == "SETTINGS_TELEGRAM" else "BuzzHeavier"
        await database.save_user(CallbackQuery.from_user, platform)
        await CallbackQuery.answer(f"Platform set to {platform}.", show_alert=True)

        await CallbackQuery.edit_message_text(
            f"Your preferred platform is now {platform}.",
            reply_markup=InlineKeyboardMarkup(get_settings_buttons(platform)),
        )

    await CallbackQuery.answer()


@bot.on_message(filters.new_chat_members, group=1)
async def new_chat(_, message: Message):
    """
    Get notified when someone add bot in the group,
    then it saves that group chat_id in the database.
    """

    chatid = message.chat.id
    for new_user in message.new_chat_members:
        if new_user.id == bot.me.id:
            await database.save_chat(chatid)
