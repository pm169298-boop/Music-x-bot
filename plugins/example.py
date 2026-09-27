#!/usr/bin/env python3
"""
================================================================================
Example Plugin — Music-x-bot
================================================================================
Is file me koi import nahi likhna padta: `app`, `db`, `config`, `logger`, `filters`,
`types` aur decorators (`command`, `on_message`, `callback`) automatically
available hote hain.

Test karne ke liye:
    /example          -> simple reply
    /example 5        -> repeat count
    /whereami         -> chat + database info (sudo only)
    button dabao      -> callback query example
================================================================================
"""


@command(["example"], description="Example plugin ka demo command", usage="/example [count]")
async def example_cmd(_, message):
    """Example plugin chalu hai — ye /example command ka jawab hai."""
    count = 3
    if len(message.command) > 1 and message.command[1].isdigit():
        count = max(1, min(int(message.command[1]), 10))

    text = f"🎉 <b>Example plugin active hai!</b>\n\nYe message {count} baar likha gaya:\n\n"
    text += "\n".join(f"• Example <b>#{index}</b>" for index in range(1, count + 1))

    await message.reply_text(
        text,
        reply_markup=types.InlineKeyboardMarkup(
            [[types.InlineKeyboardButton("🗑️ Delete", callback_data="example delete")]]
        ),
    )


@callback(r"^example delete$")
async def example_delete(_, query):
    await query.answer("Delete kar diya!")
    try:
        await query.message.delete()
    except Exception:
        pass


@command(["whereami"], sudo=True, description="Chat + database info dikhata hai")
async def whereami(_, message):
    chat = message.chat
    lang_code = await db.get_lang(chat.id)
    play_mode = await db.get_play_mode(chat.id)
    active = chat.id in db.active_calls

    await message.reply_text(
        f"📍 <b>Chat:</b> <code>{chat.id}</code> ({chat.title or chat.first_name or 'Private'})\n"
        f"🗄️ <b>Storage engine:</b> {db.mode_label}\n"
        f"🌍 <b>Language:</b> <code>{lang_code}</code>\n"
        f"🔐 <b>Admin-only play mode:</b> <code>{play_mode}</code>\n"
        f"🎧 <b>VC active:</b> <code>{active}</code>\n"
        f"🧩 <b>Loaded by:</b> plugin loader (plugins/example.py)"
    )
