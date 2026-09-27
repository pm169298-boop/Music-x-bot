#!/usr/bin/env python3
"""
================================================================================
Music-x-bot: All-in-One Single File Telegram Voice Chat Music Bot
================================================================================
Features:
- Stream high quality Audio & Video in Telegram Group Voice Chats
- YouTube search & high-speed audio extraction via py-yt-search and yt-dlp
- Hybrid Dual Database Engine:
    * Firebase Realtime Database (if FIREBASE_DATABASE_URL & credentials set)
    * Local VPS Storage (data/database.json) with Automated Backup Mode (if Firebase not set)
- Automatic Scheduled Backups + Telegram Backup Deliveries via /backup
- Queue Management, Inline Playback Controls, Video Playback (/vplay)
================================================================================
"""

import os
import re
import sys
import json
import time
import shutil
import asyncio
import logging
import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from pyrogram import Client, filters, idle
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from pyrogram.enums import ChatMemberStatus, ParseMode
from pyrogram.errors import (
    UserNotParticipant,
    ChatAdminRequired,
    UserBannedInChannel,
    ChannelPrivate,
    FloodWait,
)

# PyTgCalls
from pytgcalls import PyTgCalls, types
from pytgcalls.exceptions import (
    NoActiveGroupCall,
    NotInCallError,
)

# yt-dlp & py-yt-search
import yt_dlp
try:
    from py_yt import VideosSearch
    PY_YT_AVAILABLE = True
except ImportError:
    PY_YT_AVAILABLE = False

# psutil for system stats
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Firebase Admin SDK (Optional)
try:
    import firebase_admin
    from firebase_admin import credentials, db as fb_db
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("MusicBot")
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pytgcalls").setLevel(logging.INFO)

# Load Environment Variables
load_dotenv()

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION = os.getenv("SESSION", "")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
LOGGER_ID = int(os.getenv("LOGGER_ID", 0))

# Firebase Settings
FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL", "").strip()
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS", "").strip()

# Local VPS Storage & Backup Settings
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_INTERVAL_HOURS = int(os.getenv("BACKUP_INTERVAL_HOURS", 6))
MAX_BACKUPS_RETAINED = int(os.getenv("MAX_BACKUPS_RETAINED", 10))

# Cookies & Downloads
COOKIES_FILE = os.getenv("COOKIES_FILE", "cookies.txt")
DOWNLOADS_DIR = Path("downloads")

start_time = time.time()
bot_username = ""
assistant_username = ""


# ==============================================================================
# Database & Backup Manager (Firebase + Local VPS Fallback + Auto Backup)
# ==============================================================================
class DatabaseManager:
    """
    Hybrid Database Manager:
    - If Firebase is configured -> Uses Firebase Realtime Database
    - If Firebase is NOT set -> Saves locally on VPS (data/database.json) with Auto-Backup Mode
    """
    def __init__(self):
        self.is_firebase = False
        self.fb_ref = None
        self.local_db_file = DATA_DIR / "database.json"
        self.data: Dict[str, Any] = {
            "stats": {"songs_played": 0, "total_commands": 0, "started_at": int(time.time())},
            "sudo_users": [OWNER_ID] if OWNER_ID else [],
            "chats": {},
            "settings": {"auto_leave": True}
        }
        self.init_db()

    def init_db(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

        # 1. Attempt Firebase initialization if configured
        if FIREBASE_AVAILABLE and FIREBASE_DATABASE_URL:
            try:
                cred_obj = None
                creds_path = Path(FIREBASE_CREDENTIALS) if FIREBASE_CREDENTIALS else Path("firebase_key.json")
                if creds_path.exists():
                    cred_obj = credentials.Certificate(str(creds_path))
                elif FIREBASE_CREDENTIALS.startswith("{") and FIREBASE_CREDENTIALS.endswith("}"):
                    cred_dict = json.loads(FIREBASE_CREDENTIALS)
                    cred_obj = credentials.Certificate(cred_dict)

                if cred_obj:
                    if not firebase_admin._apps:
                        firebase_admin.initialize_app(cred_obj, {"databaseURL": FIREBASE_DATABASE_URL})
                    self.fb_ref = fb_db.reference("musicbot")
                    self.is_firebase = True
                    logger.info("🔥 [Database] Connected to Firebase Realtime Database successfully!")
                    
                    remote_data = self.fb_ref.get()
                    if remote_data and isinstance(remote_data, dict):
                        self.data.update(remote_data)
                    else:
                        self.fb_ref.set(self.data)
                    return
            except Exception as e:
                logger.warning(f"⚠️ [Database] Firebase connection failed ({e}). Falling back to Local VPS Storage Mode.")
                self.is_firebase = False

        # 2. Local VPS Storage Mode with Automated Backup Mode
        logger.info("💾 [Database] Local VPS Storage Mode is ACTIVE with Automated Backup Mode.")
        if self.local_db_file.exists():
            try:
                with open(self.local_db_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self.data.update(loaded)
                logger.info(f"Loaded existing database from {self.local_db_file}")
            except Exception as e:
                logger.error(f"Failed to read local database: {e}")
        else:
            self._save_local()

    def _save_local(self):
        """Atomic write to prevent corruption on sudden restart"""
        tmp_file = self.local_db_file.with_suffix(".tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        tmp_file.replace(self.local_db_file)

    def save(self):
        """Saves current state to either Firebase or Local VPS storage"""
        if self.is_firebase and self.fb_ref:
            try:
                self.fb_ref.set(self.data)
                return
            except Exception as e:
                logger.error(f"Firebase sync error: {e}. Saving to local VPS copy.")
        self._save_local()

    def create_backup(self) -> Path:
        """Create a timestamped backup snapshot on VPS"""
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"database_backup_{timestamp}.json"
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

        # Prune old backups
        backups = sorted(BACKUP_DIR.glob("database_backup_*.json"), key=os.path.getmtime)
        while len(backups) > MAX_BACKUPS_RETAINED:
            old = backups.pop(0)
            try:
                old.unlink()
                logger.info(f"Pruned older backup: {old.name}")
            except Exception:
                pass

        logger.info(f"Database backup created: {backup_file.name}")
        return backup_file

    def increment_stat(self, key: str, amount: int = 1):
        if "stats" not in self.data:
            self.data["stats"] = {}
        self.data["stats"][key] = self.data["stats"].get(key, 0) + amount
        self.save()

    def get_stat(self, key: str, default: Any = 0) -> Any:
        return self.data.get("stats", {}).get(key, default)

    def register_chat(self, chat_id: int, title: str):
        cid = str(chat_id)
        if cid not in self.data["chats"]:
            self.data["chats"][cid] = {"title": title, "added_at": int(time.time())}
            self.save()


db_mgr = DatabaseManager()


# ==============================================================================
# YouTube Search & Downloader (py-yt-search + yt-dlp)
# ==============================================================================
@dataclass
class Track:
    title: str
    duration: str
    duration_sec: int
    url: str
    file_path: str
    thumbnail: str
    requester: str
    is_video: bool = False


async def search_and_download(query: str, requester: str, is_video: bool = False) -> Track:
    """
    Searches YouTube and downloads audio or video using yt-dlp.
    Returns a Track dataclass object.
    """
    is_url = bool(re.match(r"^https?://", query.strip()))
    target_url = query.strip()
    title = ""
    thumbnail = ""
    duration = "0:00"
    duration_sec = 0

    if not is_url:
        found = False
        if PY_YT_AVAILABLE:
            try:
                vs = VideosSearch(query, limit=1)
                res = await vs.next()
                if res and res.get("result"):
                    r = res["result"][0]
                    target_url = r.get("link")
                    title = r.get("title", "")
                    thumbnail = r.get("thumbnails", [{}])[-1].get("url", "")
                    duration = r.get("duration", "0:00")
                    found = True
            except Exception as e:
                logger.warning(f"py_yt search error: {e}, falling back to yt-dlp search.")

        if not found:
            target_url = f"ytsearch1:{query}"

    def _download():
        DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        cookie_path = Path(COOKIES_FILE)

        ydl_opts = {
            "format": "(bestvideo[height<=?720]+bestaudio)/best" if is_video else "bestaudio/best",
            "outtmpl": str(DOWNLOADS_DIR / "%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "geo_bypass": True,
            "nocheckcertificate": True,
        }
        if cookie_path.exists():
            ydl_opts["cookiefile"] = str(cookie_path)
        if is_video:
            ydl_opts["merge_output_format"] = "mp4"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=True)
            if "entries" in info:
                info = info["entries"][0]

            track_title = info.get("title", title or "Unknown Track")
            track_thumb = info.get("thumbnail", thumbnail or "")
            dur_sec = int(info.get("duration", 0) or 0)
            dur_str = info.get("duration_string", duration or "0:00")
            dl_path = ydl.prepare_filename(info)
            if is_video and not dl_path.endswith(".mp4"):
                dl_path = os.path.splitext(dl_path)[0] + ".mp4"

            return Track(
                title=track_title[:45],
                duration=dur_str,
                duration_sec=dur_sec,
                url=info.get("webpage_url", target_url),
                file_path=dl_path,
                thumbnail=track_thumb,
                requester=requester,
                is_video=is_video,
            )

    return await asyncio.to_thread(_download)


# ==============================================================================
# Queue Manager
# ==============================================================================
class QueueManager:
    def __init__(self):
        self.queues: Dict[int, List[Track]] = {}
        self.current_tracks: Dict[int, Track] = {}
        self.playing_messages: Dict[int, int] = {}

    def get_queue(self, chat_id: int) -> List[Track]:
        return self.queues.get(chat_id, [])

    def add_to_queue(self, chat_id: int, track: Track) -> int:
        if chat_id not in self.queues:
            self.queues[chat_id] = []
        self.queues[chat_id].append(track)
        return len(self.queues[chat_id])

    def get_current(self, chat_id: int) -> Optional[Track]:
        return self.current_tracks.get(chat_id)

    def set_current(self, chat_id: int, track: Optional[Track]):
        if track:
            self.current_tracks[chat_id] = track
        else:
            self.current_tracks.pop(chat_id, None)

    def pop_next(self, chat_id: int) -> Optional[Track]:
        if chat_id in self.queues and self.queues[chat_id]:
            return self.queues[chat_id].pop(0)
        return None

    def clear(self, chat_id: int):
        self.queues.pop(chat_id, None)
        old_track = self.current_tracks.pop(chat_id, None)
        if old_track and old_track.file_path and os.path.exists(old_track.file_path):
            try:
                os.remove(old_track.file_path)
            except Exception:
                pass


queue_mgr = QueueManager()


# ==============================================================================
# Telegram Clients & PyTgCalls Setup
# ==============================================================================
bot = Client(
    name="musicbot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    parse_mode=ParseMode.HTML,
)

assistant = Client(
    name="assistant",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION,
    no_updates=True,
)

call = PyTgCalls(assistant)


# ==============================================================================
# Stream Playback & Callbacks
# ==============================================================================
async def start_stream(chat_id: int, track: Track):
    queue_mgr.set_current(chat_id, track)
    db_mgr.increment_stat("songs_played")

    stream = types.MediaStream(
        media_path=str(track.file_path),
        audio_parameters=types.AudioQuality.HIGH,
        video_parameters=types.VideoQuality.HD_720p,
        audio_flags=types.MediaStream.Flags.REQUIRED,
        video_flags=(
            types.MediaStream.Flags.AUTO_DETECT if track.is_video else types.MediaStream.Flags.IGNORE
        ),
    )

    await call.play(chat_id, stream=stream)

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸️ Pause", callback_data="cb_pause"),
            InlineKeyboardButton("▶️ Resume", callback_data="cb_resume"),
            InlineKeyboardButton("⏭️ Skip", callback_data="cb_skip"),
            InlineKeyboardButton("⏹️ Stop", callback_data="cb_stop"),
        ]
    ])

    caption = (
        f"🎶 <b>Now Playing{' (Video)' if track.is_video else ''}:</b>\n"
        f"📌 <b>Title:</b> <a href=\"{track.url}\">{track.title}</a>\n"
        f"⏱️ <b>Duration:</b> <code>{track.duration}</code>\n"
        f"👤 <b>Requested by:</b> {track.requester}"
    )

    try:
        if track.thumbnail:
            sent = await bot.send_photo(chat_id, photo=track.thumbnail, caption=caption, reply_markup=buttons)
        else:
            sent = await bot.send_message(chat_id, text=caption, reply_markup=buttons, disable_web_page_preview=True)
        queue_mgr.playing_messages[chat_id] = sent.id
    except Exception as e:
        logger.error(f"Failed to send playing card: {e}")


async def play_next_track(chat_id: int):
    old_track = queue_mgr.get_current(chat_id)
    if old_track and old_track.file_path and os.path.exists(old_track.file_path):
        try:
            os.remove(old_track.file_path)
        except Exception:
            pass

    next_track = queue_mgr.pop_next(chat_id)
    if next_track:
        try:
            await start_stream(chat_id, next_track)
        except Exception as e:
            logger.error(f"Error playing next track: {e}")
            await bot.send_message(chat_id, f"⚠️ Error playing next track: <code>{e}</code>")
            await play_next_track(chat_id)
    else:
        queue_mgr.set_current(chat_id, None)
        try:
            await call.leave_call(chat_id, close=False)
        except Exception:
            pass
        await bot.send_message(chat_id, "⏹️ <b>Queue finished. Assistant left the Voice Chat.</b>")


@call.on_update()
async def stream_update_handler(_, update: types.Update):
    if isinstance(update, types.StreamEnded):
        await play_next_track(update.chat_id)
    elif isinstance(update, types.ChatUpdate):
        if update.status in [
            types.ChatUpdate.Status.KICKED,
            types.ChatUpdate.Status.LEFT_GROUP,
            types.ChatUpdate.Status.CLOSED_VOICE_CHAT,
        ]:
            queue_mgr.clear(update.chat_id)


@bot.on_callback_query()
async def callbacks_handler(_, query: CallbackQuery):
    chat_id = query.message.chat.id
    data = query.data

    if data == "cb_pause":
        try:
            await call.pause(chat_id)
            await query.answer("⏸️ Paused!")
            await query.message.reply_text(f"⏸️ Stream paused by {query.from_user.mention}")
        except Exception as e:
            await query.answer(f"Error: {e}", show_alert=True)

    elif data == "cb_resume":
        try:
            await call.resume(chat_id)
            await query.answer("▶️ Resumed!")
            await query.message.reply_text(f"▶️ Stream resumed by {query.from_user.mention}")
        except Exception as e:
            await query.answer(f"Error: {e}", show_alert=True)

    elif data == "cb_skip":
        await query.answer("⏭️ Skipping track...")
        await query.message.reply_text(f"⏭️ Skipped by {query.from_user.mention}")
        await play_next_track(chat_id)

    elif data == "cb_stop":
        queue_mgr.clear(chat_id)
        try:
            await call.leave_call(chat_id, close=False)
        except Exception:
            pass
        await query.answer("⏹️ Stopped!")
        await query.message.reply_text(f"⏹️ Playback stopped by {query.from_user.mention}")


# ==============================================================================
# Telegram Bot Commands
# ==============================================================================
@bot.on_message(filters.command(["start", "help"]))
async def start_help_cmd(_, message: Message):
    db_mgr.register_chat(message.chat.id, getattr(message.chat, "title", "Private"))
    text = (
        "👋 <b>Welcome to Music-x-bot!</b>\n\n"
        "I am an all-in-one Telegram Voice Chat Music Bot.\n\n"
        "🎮 <b>Commands:</b>\n"
        "• <code>/play &lt;song/link&gt;</code> - Play audio in Voice Chat\n"
        "• <code>/vplay &lt;song/link&gt;</code> - Play video in Voice Chat\n"
        "• <code>/pause</code> - Pause current playback\n"
        "• <code>/resume</code> - Resume playback\n"
        "• <code>/skip</code> - Skip to next song in queue\n"
        "• <code>/stop</code> - Stop playback & leave VC\n"
        "• <code>/queue</code> - View active song queue\n"
        "• <code>/ping</code> - Check bot response latency\n"
        "• <code>/stats</code> - View system & database status\n"
        "• <code>/backup</code> - Create & download database backup (Owner only)\n\n"
        "💡 <b>Setup in Group:</b> Add me and Assistant account to your group, promote as admin, start Voice Chat and type <code>/play song name</code>!"
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Me to Your Group", url=f"https://t.me/{bot_username}?startgroup=true")]
    ])
    await message.reply_text(text, reply_markup=buttons)


@bot.on_message(filters.command(["play", "vplay"]) & filters.group)
async def play_cmd(_, message: Message):
    is_video = message.command[0].lower() == "vplay"
    if len(message.command) < 2:
        await message.reply_text(f"❗ <b>Usage:</b> <code>/{message.command[0]} &lt;song name or YouTube URL&gt;</code>")
        return

    query = message.text.split(maxsplit=1)[1]
    chat_id = message.chat.id
    db_mgr.register_chat(chat_id, message.chat.title)

    status_msg = await message.reply_text("🔍 <b>Searching and downloading track...</b>")

    # Check assistant membership
    try:
        me_as = await assistant.get_me()
        await assistant.get_chat_member(chat_id, me_as.id)
    except Exception:
        try:
            invite = await bot.export_chat_invite_link(chat_id)
            await assistant.join_chat(invite)
        except Exception:
            await status_msg.edit_text(
                f"⚠️ <b>Assistant is not in this group!</b>\n"
                f"Please add assistant account (<code>@{assistant_username}</code>) to this group and promote as admin."
            )
            return

    try:
        track = await search_and_download(query, requester=message.from_user.mention, is_video=is_video)
    except Exception as e:
        await status_msg.edit_text(f"❌ <b>Download failed:</b> <code>{e}</code>")
        return

    curr = queue_mgr.get_current(chat_id)
    if curr:
        pos = queue_mgr.add_to_queue(chat_id, track)
        await status_msg.edit_text(
            f"➕ <b>Queued at position #{pos}:</b>\n"
            f"📌 <a href=\"{track.url}\">{track.title}</a>\n"
            f"⏱️ Duration: <code>{track.duration}</code>\n"
            f"👤 Requester: {track.requester}",
            disable_web_page_preview=True
        )
    else:
        await status_msg.delete()
        try:
            await start_stream(chat_id, track)
        except (NoActiveGroupCall, NotInCallError):
            queue_mgr.clear(chat_id)
            await message.reply_text("⚠️ <b>No active Voice Chat found!</b> Please start Voice Chat in this group first.")
        except Exception as e:
            queue_mgr.clear(chat_id)
            await message.reply_text(f"❌ <b>Error starting playback:</b> <code>{e}</code>")


@bot.on_message(filters.command("pause") & filters.group)
async def pause_cmd(_, message: Message):
    chat_id = message.chat.id
    try:
        await call.pause(chat_id)
        await message.reply_text(f"⏸️ Stream paused by {message.from_user.mention}")
    except Exception as e:
        await message.reply_text(f"❌ Error: <code>{e}</code>")


@bot.on_message(filters.command("resume") & filters.group)
async def resume_cmd(_, message: Message):
    chat_id = message.chat.id
    try:
        await call.resume(chat_id)
        await message.reply_text(f"▶️ Stream resumed by {message.from_user.mention}")
    except Exception as e:
        await message.reply_text(f"❌ Error: <code>{e}</code>")


@bot.on_message(filters.command("skip") & filters.group)
async def skip_cmd(_, message: Message):
    chat_id = message.chat.id
    await message.reply_text(f"⏭️ Skipped track by {message.from_user.mention}")
    await play_next_track(chat_id)


@bot.on_message(filters.command(["stop", "end"]) & filters.group)
async def stop_cmd(_, message: Message):
    chat_id = message.chat.id
    queue_mgr.clear(chat_id)
    try:
        await call.leave_call(chat_id, close=False)
    except Exception:
        pass
    await message.reply_text(f"⏹️ Playback stopped by {message.from_user.mention}. Queue cleared.")


@bot.on_message(filters.command("queue") & filters.group)
async def queue_cmd(_, message: Message):
    chat_id = message.chat.id
    curr = queue_mgr.get_current(chat_id)
    q = queue_mgr.get_queue(chat_id)

    if not curr and not q:
        await message.reply_text("📭 The queue is currently empty.")
        return

    text = "📋 <b>Active Playback Queue:</b>\n\n"
    if curr:
        text += f"▶️ <b>Now Playing:</b> <a href=\"{curr.url}\">{curr.title}</a> (<code>{curr.duration}</code>)\n\n"

    if q:
        text += "<b>Upcoming Tracks:</b>\n"
        for i, track in enumerate(q[:10], start=1):
            text += f"<b>{i}.</b> <a href=\"{track.url}\">{track.title}</a> (<code>{track.duration}</code>) | {track.requester}\n"
        if len(q) > 10:
            text += f"\n<i>...and {len(q) - 10} more tracks in queue.</i>"

    await message.reply_text(text, disable_web_page_preview=True)


@bot.on_message(filters.command("ping"))
async def ping_cmd(_, message: Message):
    t1 = time.time()
    msg = await message.reply_text("🏓 Pong...")
    t2 = time.time()
    latency = round((t2 - t1) * 1000, 2)
    await msg.edit_text(f"🏓 <b>Pong!</b> Response Latency: <code>{latency} ms</code>")


@bot.on_message(filters.command("stats"))
async def stats_cmd(_, message: Message):
    uptime_sec = int(time.time() - start_time)
    uptime_str = str(datetime.timedelta(seconds=uptime_sec))
    db_mode = "🔥 Firebase Realtime DB" if db_mgr.is_firebase else "💾 Local VPS Storage (Auto Backup ON)"

    cpu = f"{psutil.cpu_percent()}%" if PSUTIL_AVAILABLE else "N/A"
    ram = f"{psutil.virtual_memory().percent}%" if PSUTIL_AVAILABLE else "N/A"

    text = (
        f"📊 <b>Music-x-bot System & Database Stats</b>\n\n"
        f"🗄️ <b>Storage Engine:</b> <code>{db_mode}</code>\n"
        f"🎵 <b>Total Songs Played:</b> <code>{db_mgr.get_stat('songs_played', 0)}</code>\n"
        f"💬 <b>Active Streams:</b> <code>{len(queue_mgr.current_tracks)}</code>\n"
        f"👥 <b>Saved Chats:</b> <code>{len(db_mgr.data.get('chats', {}))}</code>\n"
        f"⏱️ <b>Uptime:</b> <code>{uptime_str}</code>\n"
        f"💻 <b>CPU Usage:</b> <code>{cpu}</code>\n"
        f"🧠 <b>RAM Usage:</b> <code>{ram}</code>"
    )
    await message.reply_text(text)


@bot.on_message(filters.command("backup"))
async def backup_cmd(_, message: Message):
    # Only bot owner can create & receive backup
    if message.from_user and OWNER_ID and message.from_user.id != OWNER_ID:
        await message.reply_text("⛔ This command is restricted to the Bot Owner.")
        return

    msg = await message.reply_text("🔄 <b>Generating database backup snapshot...</b>")
    try:
        backup_file = db_mgr.create_backup()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        caption = (
            f"📦 <b>Music-x-bot Database Backup</b>\n"
            f"📅 <b>Timestamp:</b> <code>{timestamp}</code>\n"
            f"🗄️ <b>Mode:</b> <code>{'Firebase (Synced)' if db_mgr.is_firebase else 'Local VPS Storage'}</code>\n"
            f"🎵 <b>Songs Played:</b> <code>{db_mgr.get_stat('songs_played', 0)}</code>\n"
            f"👥 <b>Registered Chats:</b> <code>{len(db_mgr.data.get('chats', {}))}</code>"
        )
        await message.reply_document(document=str(backup_file), caption=caption)
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ Backup failed: <code>{e}</code>")


# ==============================================================================
# Automated Backup Background Task
# ==============================================================================
async def auto_backup_loop():
    """Runs in background and takes backup every BACKUP_INTERVAL_HOURS"""
    while True:
        await asyncio.sleep(BACKUP_INTERVAL_HOURS * 3600)
        try:
            backup_file = db_mgr.create_backup()
            logger.info(f"💾 Scheduled backup created: {backup_file.name}")
            if LOGGER_ID:
                caption = (
                    f"📦 <b>Automated Database Backup</b>\n"
                    f"🕒 <code>{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
                    f"🗄️ Storage: <code>{'Firebase (Synced)' if db_mgr.is_firebase else 'Local VPS Storage'}</code>\n"
                    f"🎵 Songs Played: <code>{db_mgr.get_stat('songs_played', 0)}</code>"
                )
                try:
                    await bot.send_document(LOGGER_ID, str(backup_file), caption=caption)
                except Exception as ex:
                    logger.warning(f"Could not send backup to LOGGER_ID: {ex}")
        except Exception as e:
            logger.error(f"Auto backup loop error: {e}")


# ==============================================================================
# Main Boot Sequence
# ==============================================================================
async def main():
    if not (API_ID and API_HASH and BOT_TOKEN and SESSION):
        logger.error("Missing mandatory environment variables! Check API_ID, API_HASH, BOT_TOKEN, SESSION.")
        sys.exit(1)

    logger.info("Starting Telegram Bot & Assistant Client...")
    await bot.start()
    await assistant.start()

    global bot_username, assistant_username
    me_bot = await bot.get_me()
    me_as = await assistant.get_me()
    bot_username = me_bot.username
    assistant_username = me_as.username
    logger.info(f"Bot started as @{bot_username}")
    logger.info(f"Assistant started as @{assistant_username}")

    logger.info("Starting PyTgCalls Client...")
    await call.start()

    # Launch automated background backup task
    asyncio.create_task(auto_backup_loop())

    if LOGGER_ID:
        try:
            db_mode_msg = "🔥 Firebase Realtime DB" if db_mgr.is_firebase else "💾 Local VPS Storage (Auto Backup ON)"
            await bot.send_message(
                LOGGER_ID,
                f"🚀 <b>Music-x-bot Started Successfully!</b>\n\n"
                f"🤖 <b>Bot:</b> @{bot_username}\n"
                f"👤 <b>Assistant:</b> @{assistant_username}\n"
                f"🗄️ <b>Database Engine:</b> <code>{db_mode_msg}</code>"
            )
        except Exception as e:
            logger.warning(f"Failed to send startup message to LOGGER_ID: {e}")

    logger.info("Bot is active and listening for commands! Press Ctrl+C to terminate.")
    await idle()

    logger.info("Shutting down bot...")
    await call.stop()
    await assistant.stop()
    await bot.stop()


if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        pass
