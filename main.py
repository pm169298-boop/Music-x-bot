#!/usr/bin/env python3
"""
================================================================================
    🎵 Music-x-bot — All-in-One Single File Telegram Voice Chat Music Bot
================================================================================
    Version  : 3.1.0
    Author   : pm169298-boop  (single-file edition)
    Credits  : Built on top of AnonXMusic / LunaXMusicBot architecture
               (c) 2025 AnonymousX1025 — MIT License
    Python   : 3.10+
--------------------------------------------------------------------------------
    FEATURES (sab kuch isi ek file me — kuch bhi kam nahi kiya gaya):
--------------------------------------------------------------------------------
    🎧 PLAYBACK
      • /play, /vplay, /playforce, /vplayforce (Telegram file / YouTube / M3U8)
      • /pause, /resume, /skip, /stop, /end, /replay (inline buttons se bhi)
      • /seek, /seekback (kahan se chalu karna hai)
      • /loop (count based repeat), autoplay, queue management, /queue
      • Live progress timer + control buttons ka auto-update
      • Multi-assistant support (SESSION, SESSION2, SESSION3, SESSION4)

    🎨 CUSTOM BRANDING IMAGE
      • /setimg (reply photo ya URL) -> start image, /setimg stats -> stats image
      • /setimg show | remove | status
      • Image database me save NAHI hoti — DB me sirf Telegram reference
        (chat id + message id + file id) rehta hai, image TG se load hoti hai

    📦 SOURCE EXTRACT  (admin poora code nikaal sakta hai)
      • /source -> poora project ZIP, /source main -> main.py
      • /source list -> files, /source <file> -> koi bhi file

    🛑 HOSTING STOP
      • /shutdown (confirm button ke saath) -> save + backup + graceful exit

    🎛️ ADMIN PANEL (button wala)
      • /admin, /panel, /admins -> inline-button control panel
        (stats, active VC, auth list, playmode, auto-delete, sudo list, blacklist,
         backup now, backups, restore (confirm), DB status, push/pull, plugins,
         logs tail + log file, maintenance toggle, language picker, refresh/close)
      • Role based: sudo/owner = sab, chat admin = chat toggles, baaki locked

    🛠️ ADMIN
      • /auth, /unauth, /authlist (per-chat authorized users)
      • /admincache, /reload (admin list refresh)
      • /playmode + /settings (admin-only play mode, command auto-delete, language)
      • /blacklist, /unblacklist, /whitelist (sudo only)
      • /broadcast (with -copy, -nochat, -user flags + error report)
      • /addsudo, /delsudo, /listsudo, /sudoers (owner only)
      • /eval, /exec (owner only — live python evaluation)
      • /activevc (/ac), /stats, /ping, /alive

    📝 LOGS
      • Rotating file logs (log.txt) + console
      • /logs command (log.txt Telegram par)
      • /logger on|off — play/chat/user activity logger group me
      • Telegram error-log handler (ERROR level LOGGER_ID par)
      • Auto play logs (/start, play, new chat logs)

    🗄️ DATABASE (HYBRID ENGINE)
      • Firebase Realtime Database mode (FIREBASE_DATABASE_URL + service account)
      • Local VPS mode (data/database.json) — Firebase na ho to automatic fallback
      • Firebase fail hone par degraded mode + auto-reconnect (data loss zero)
      • /dbstatus, /syncdb push|pull (manual Firebase sync)

    📦 AUTOMATED BACKUP
      • Har X ghante auto snapshot (data/backups/)
      • Backup LOGGER_ID (Telegram log group) me document ban kar bhejta hai
      • /backup (instant backup), /backups (list), /restore (reply to backup file)
      • Retention (MAX_BACKUPS_RETAINED), gzip compression, remote dir copy,
        optional Firebase Storage upload, pre-restore safety snapshot

    🌍 OTHERS
      • 13 languages (ar, de, en, es, fr, hi, ja, my, pa, pt, ru, tr, zh)
      • Custom thumbnail generation (embedded fonts — kuch install nahi karna)
      • Inline YouTube search (chat me @bot <query>)
      • Plugin system: plugins/ folder me .py daalo → auto load (hot reload bhi)
      • /maintenance on|off, /plugins, /help

--------------------------------------------------------------------------------
    LICENSE: MIT (see LICENSE file). Original AnonXMusic credits retained.
================================================================================
"""

import ast
import asyncio
import base64
import glob
import gzip
import importlib.util
import io
import json
import logging
import lzma
import os
import platform
import random
import re
import shutil
import signal
import sys
import time
import traceback
import uuid
import zipfile
from collections import defaultdict, deque
from contextlib import suppress
from dataclasses import dataclass
from functools import wraps
from html import escape
from logging.handlers import RotatingFileHandler
from pathlib import Path
from random import randint
from typing import Any, Callable, Optional, Tuple, Union

# ------------------------------------------------------------------------------
# Optional .env support
# ------------------------------------------------------------------------------
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
    load_dotenv()
except ImportError:
    pass

# ------------------------------------------------------------------------------
# Third party imports
# ------------------------------------------------------------------------------
import aiohttp
import psutil
import yt_dlp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
from py_yt import Playlist, VideosSearch
from pyrogram import Client, enums, errors, filters, types
from pyrogram import __version__ as pyrogram_version
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.errors import (
    ChatSendMediaForbidden,
    ChatSendPhotosForbidden,
    MessageIdInvalid,
)
from pyrogram.types import InputMediaPhoto, Message
from pytgcalls import PyTgCalls, exceptions
from pytgcalls import types as tgtypes

try:  # ntgcalls exceptions (multi-assistant / connection errors)
    from ntgcalls import (
        ConnectionNotFound,
        RTMPStreamingUnsupported,
        TelegramServerError,
    )
    from ntgcalls import ConnectionError as NgConnectionError
except ImportError:  # pragma: no cover
    class ConnectionNotFound(Exception):
        """ntgcalls missing — placeholder."""

    class TelegramServerError(Exception):
        """ntgcalls missing — placeholder."""

    class RTMPStreamingUnsupported(Exception):
        """ntgcalls missing — placeholder."""

    class NgConnectionError(Exception):
        """ntgcalls missing — placeholder."""

try:
    from pytgcalls.pytgcalls_session import PyTgCallsSession
except ImportError:  # pragma: no cover
    class PyTgCallsSession:
        notice_displayed = False

try:  # Firebase Realtime Database (optional)
    import firebase_admin
    from firebase_admin import credentials as fb_credentials
    from firebase_admin import db as fb_db

    FIREBASE_AVAILABLE = True
except ImportError:  # pragma: no cover
    FIREBASE_AVAILABLE = False

try:  # Optional: Firebase Storage for backups
    from firebase_admin import storage as fb_storage
except ImportError:  # pragma: no cover
    fb_storage = None

# ==============================================================================
# LOGGING SETUP  (log.txt rotating + console + optional Telegram error handler)
# ==============================================================================
logging.basicConfig(
    format="[%(asctime)s - %(levelname)s] - %(name)s: %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        RotatingFileHandler("log.txt", maxBytes=10485760, backupCount=5, encoding="utf-8"),
        logging.StreamHandler(),
    ],
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("ntgcalls").setLevel(logging.CRITICAL)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("pytgcalls").setLevel(logging.ERROR)
logging.getLogger("yt_dlp").setLevel(logging.WARNING)
logging.getLogger("py_yt").setLevel(logging.WARNING)
logging.getLogger("firebase_admin").setLevel(logging.WARNING)
logging.getLogger("google").setLevel(logging.WARNING)
logger = logging.getLogger("MusicBot")


class TelegramLogHandler(logging.Handler):
    """ERROR+ level logs ko Telegram log group me bhejta hai (rate-limited)."""

    def __init__(self, level: int = logging.ERROR, max_buffer: int = 50) -> None:
        super().__init__(level=level)
        self.buffer: deque = deque(maxlen=max_buffer)
        self.client = None
        self.chat_id: Optional[int] = None
        self._task: Optional[asyncio.Task] = None

    def attach(self, client, chat_id: int) -> None:
        if not chat_id:
            return
        self.client = client
        self.chat_id = chat_id
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        if self._task is None or self._task.done():
            self._task = loop.create_task(self._worker())

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D102
        try:
            text = f"<b>⚠️ {record.levelname}</b>\n<code>{self.format(record)}</code>"
            self.buffer.append(text[:3500])
        except Exception:  # noqa: BLE001 - logging never raises
            pass

    async def _worker(self) -> None:
        while True:
            try:
                await asyncio.sleep(15)
                if not self.buffer or self.client is None or not self.chat_id:
                    continue
                batch = []
                while self.buffer and len(batch) < 5:
                    batch.append(self.buffer.popleft())
                if batch:
                    try:
                        await self.client.send_message(
                            self.chat_id,
                            "<b>🐞 Music-x-bot Error Logs</b>\n\n" + "\n\n".join(batch),
                        )
                    except Exception:  # noqa: BLE001
                        for item in reversed(batch):
                            self.buffer.appendleft(item)
            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception:  # noqa: BLE001
                continue


telegram_log_handler = TelegramLogHandler(level=logging.ERROR)
telegram_log_handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
logging.getLogger().addHandler(telegram_log_handler)

# ------------------------------------------------------------------------------
# Global runtime state
# ------------------------------------------------------------------------------
__version__ = "3.1.0"
BOT_DISPLAY_NAME = "Music-x-bot"
tasks: list[asyncio.Task] = []
boot = time.time()
START_TIME = boot

MAINTENANCE_ALLOWED_COMMANDS = {"start", "help", "ping", "alive", "backup", "maintenance"}


# ==============================================================================
# SECTION: CONFIGURATION
# ==============================================================================
# ==============================================================================
# CONFIGURATION  (Telegram + Firebase + Local VPS + Backup + Logs)
# ==============================================================================
class _ConfigMeta(type):
    """Config attribute ko dict ki tarah bhi access karne deta hai."""


class Config:
    """
    Saari settings ek jagah.

    Sources (priority): real environment variables -> .env file -> defaults.
    """

    # ---- helpers -------------------------------------------------------------
    @staticmethod
    def _env(key: str, default: str = "") -> str:
        value = os.getenv(key)
        if value is None or not str(value).strip():
            return default
        return str(value).strip()

    @staticmethod
    def _int(key: str, default: int = 0) -> int:
        try:
            return int(float(Config._env(key, str(default))))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _float(key: str, default: float = 0.0) -> float:
        try:
            return float(Config._env(key, str(default)))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _bool(key: str, default: bool = False) -> bool:
        return Config._env(key, str(default)).lower() in {"1", "true", "yes", "on", "y", "enable", "enabled"}

    @staticmethod
    def _list(key: str, default: str = "") -> list[str]:
        raw = Config._env(key, default).replace(" ", "")
        return [item for item in raw.split(",") if item]

    @staticmethod
    def _path(key: str, default: str) -> str:
        raw = Config._env(key, default) or default
        path = Path(os.path.expandvars(os.path.expanduser(raw)))
        if not path.is_absolute():
            path = Path(__file__).resolve().parent / path
        return str(path)

    # ---- telegram ------------------------------------------------------------
    def __init__(self) -> None:
        self.API_ID: int = self._int("API_ID", 0)
        self.API_HASH: str = self._env("API_HASH")
        self.BOT_TOKEN: str = self._env("BOT_TOKEN")

        self.LOGGER_ID: int = self._int("LOGGER_ID", 0)
        self.OWNER_ID: int = self._int("OWNER_ID", 0)
        self.STRICT_LOGGER: bool = self._bool("STRICT_LOGGER", False)
        # Env se extra sudo users (comma separated) — DB ke sudoers ke upar always add hote hain
        self.SUDO_USERS: list[str] = self._list("SUDO_USERS")

        # Assistants (multi-client support)
        self.SESSION1: Optional[str] = self._env("SESSION") or None
        # True = assistant sessions available (voice chat playback possible)
        self.ASSISTANT_MODE: bool = bool(self.SESSION1)
        self.SESSION2: Optional[str] = self._env("SESSION2") or None
        self.SESSION3: Optional[str] = self._env("SESSION3") or None
        self.SESSION4: Optional[str] = self._env("SESSION4") or None

        # ---- limits / behaviour --------------------------------------------
        self.DURATION_LIMIT: int = self._int("DURATION_LIMIT", 60) * 60      # minutes -> seconds
        self.QUEUE_LIMIT: int = self._int("QUEUE_LIMIT", 20)
        self.PLAYLIST_LIMIT: int = self._int("PLAYLIST_LIMIT", 20)
        self.SEARCH_RESULTS: int = self._int("SEARCH_RESULTS", 15)

        self.AUTO_LEAVE: bool = self._bool("AUTO_LEAVE", False)
        self.AUTO_END: bool = self._bool("AUTO_END", False)
        self.THUMB_GEN: bool = self._bool("THUMB_GEN", True)
        self.VIDEO_PLAY: bool = self._bool("VIDEO_PLAY", True)
        self.LANG_CODE: str = self._env("LANG_CODE", "en")
        self.TIMER_UPDATE: int = self._int("TIMER_UPDATE", 12)
        self.VC_WATCHER: int = self._bool("VC_WATCHER", True)
        self.NOWPLAYING_TIMER_BAR: bool = self._bool("NOWPLAYING_TIMER_BAR", True)

        self.SUPPORT_CHANNEL: str = self._env("SUPPORT_CHANNEL", "https://t.me/fallenx")
        self.SUPPORT_CHAT: str = self._env("SUPPORT_CHAT", "https://t.me/DevilsHeavenMF")
        self.UPDATE_REPO: str = self._env("UPDATE_REPO", "https://github.com/pm169298-boop/Music-x-bot")

        self.DEFAULT_THUMB: str = self._env(
            "DEFAULT_THUMB", "https://te.legra.ph/file/3e40a408286d4eda24191.jpg"
        )
        self.PING_IMG: str = self._env("PING_IMG", "https://files.catbox.moe/haagg2.png")
        self.START_IMG: str = self._env("START_IMG", "https://files.catbox.moe/zvziwk.jpg")

        # ---- cookies ---------------------------------------------------------
        self.COOKIES_DIR: str = self._path("COOKIES_DIR", "cookies")
        self.COOKIES_FILE: str = self._path("COOKIES_FILE", "cookies.txt")
        self.COOKIES_URL: list[str] = [
            url for url in self._env("COOKIES_URL", "").split(" ") if url and "batbin.me" in url
        ]
        self.COOKIES_CONTENT: str = self._env("COOKIES_CONTENT")
        self.COOKIES_B64: str = self._env("COOKIES_B64")
        self.COOKIE_ENABLED: bool = self._bool("COOKIE_ENABLED", True)
        self.YTDLP_PLAYER_CLIENT: str = self._env("YTDLP_PLAYER_CLIENT")

        # ---- directories -----------------------------------------------------
        self.DATA_DIR: str = self._path("DATA_DIR", "data")
        self.DB_FILE: str = self._path("DB_FILE", "data/database.json")
        self.BACKUP_DIR: str = self._path("BACKUP_DIR", "data/backups")
        self.LOCALES_DIR: str = self._path("LOCALES_DIR", "locales")
        self.PLUGINS_DIR: str = self._path("PLUGINS_DIR", "plugins")
        self.FONTS_DIR: str = self._path("FONTS_DIR", "cache/fonts")
        self.DOWNLOADS_DIR: str = self._path("DOWNLOADS_DIR", "downloads")
        self.CACHE_DIR: str = self._path("CACHE_DIR", "cache")
        self.LOG_FILE: str = self._path("LOG_FILE", "log.txt")

        # ---- database: firebase ---------------------------------------------
        self.FIREBASE_DATABASE_URL: str = self._env("FIREBASE_DATABASE_URL")
        self.FIREBASE_CREDENTIALS: str = self._env("FIREBASE_CREDENTIALS", "firebase_key.json")
        self.FIREBASE_CREDENTIALS_JSON: str = self._env("FIREBASE_CREDENTIALS_JSON")
        self.FIREBASE_STORAGE_BUCKET: str = self._env("FIREBASE_STORAGE_BUCKET")
        self.FIREBASE_ROOT: str = self._env("FIREBASE_ROOT", "musicbot")
        self.FIREBASE_SYNC_INTERVAL: int = max(10, self._int("FIREBASE_SYNC_INTERVAL", 60))
        self.DB_LOCAL_FLUSH_INTERVAL: int = max(5, self._int("DB_LOCAL_FLUSH_INTERVAL", 15))

        # ---- automated backup ------------------------------------------------
        self.BACKUP_INTERVAL_HOURS: float = self._float("BACKUP_INTERVAL_HOURS", 6.0)
        self.MAX_BACKUPS_RETAINED: int = max(1, self._int("MAX_BACKUPS_RETAINED", 10))
        self.BACKUP_ON_START: bool = self._bool("BACKUP_ON_START", True)
        self.BACKUP_ON_SHUTDOWN: bool = self._bool("BACKUP_ON_SHUTDOWN", True)
        self.BACKUP_TO_LOGGER: bool = self._bool("BACKUP_TO_LOGGER", True)
        self.BACKUP_GZIP: bool = self._bool("BACKUP_GZIP", True)
        self.BACKUP_REMOTE_DIR: str = self._env("BACKUP_REMOTE_DIR")
        self.BACKUP_VERIFY: bool = self._bool("BACKUP_VERIFY", True)

        # ---- logs ------------------------------------------------------------
        self.LOG_TO_TELEGRAM: bool = self._bool("LOG_TO_TELEGRAM", True)
        self.LOG_LEVEL: str = self._env("LOG_LEVEL", "INFO").upper()
        self.PLAY_LOG: bool = self._bool("PLAY_LOG", True)
        self.CLEANUP_HOURS: float = self._float("CLEANUP_HOURS", 24.0)
        self.MAINTENANCE: bool = self._bool("MAINTENANCE", False)
        self.MANAGEMENT_MODE: bool = self._bool("MANAGEMENT_MODE", False)

    # ---- validation ----------------------------------------------------------
    def check(self) -> None:
        """
        Zaroori env vars check. Sirf 3 cheezein mandatory hain: API_ID, API_HASH, BOT_TOKEN.
        LOGGER_ID missing ho to OWNER_ID par fallback ho jaata hai, aur SESSION missing ho to
        bot "bot-only mode" me chalta hai (commands, admin panel, logs, backups sab kaam karte
        hain — sirf voice chat playback off rehta hai jab tak assistant session na daalein).
        """
        missing = [var for var in ["API_ID", "API_HASH", "BOT_TOKEN"] if not getattr(self, var)]
        if missing:
            raise SystemExit(
                "❌ Missing required environment variables: "
                + ", ".join(missing)
                + "\n   sample.env ko .env me copy karke values bharein (ya env vars set karein)."
            )

        if not self.OWNER_ID:
            logger.warning("⚠️ OWNER_ID set nahi hai — owner-only commands kisi ke liye kaam nahi karenge.")

        if not self.LOGGER_ID:
            self.LOGGER_ID = self.OWNER_ID or 0
            logger.warning(
                "⚠️ LOGGER_ID set nahi hai — logs/backups owner (%s) ke DM me jaayenge "
                "(group id daalna better hai).",
                self.LOGGER_ID or "?",
            )

        if not self.SESSION1:
            logger.warning(
                "⚠️ SESSION (assistant) set nahi hai — bot BOT-ONLY MODE me chalega. "
                "Commands, admin panel, logs, database aur backups sab kaam karenge, "
                "lekin /play (voice chat) ke liye assistant string session zaroori hai."
            )

    def ensure_dirs(self) -> None:
        for directory in (
            self.DATA_DIR,
            self.BACKUP_DIR,
            self.DOWNLOADS_DIR,
            self.CACHE_DIR,
            self.FONTS_DIR,
            self.COOKIES_DIR,
            self.PLUGINS_DIR,
            str(Path(self.LOG_FILE).parent),
        ):
            try:
                Path(directory).mkdir(parents=True, exist_ok=True)
            except OSError:
                continue

    @property
    def firebase_enabled(self) -> bool:
        return bool(self.FIREBASE_DATABASE_URL and (self.FIREBASE_CREDENTIALS_JSON or self.FIREBASE_CREDENTIALS))

    @property
    def storage_backend(self) -> str:
        return "🔥 Firebase Realtime DB + VPS mirror" if self.firebase_enabled else "💾 Local VPS Storage"


config = Config()
config.ensure_dirs()


# ==============================================================================
# EMBEDDED ASSETS  (13 locales + 2 fonts — lzma + base64)
# ==============================================================================
# Sab kuch isi single file me hai, isliye koi bhi locale/font file copy karne ki
# zaroorat nahi. Chahein to `locales/<code>.json` ya `cache/fonts/*.ttf` rakh kar
# inhe override bhi kar sakte hain.
_EMBEDDED_LOCALES: dict[str, str] = {
    "ar": (
        "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"
        "6JvLHEZ/sCAAAAAARZWg=="
    ),
    "de": (
        "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"
        "AgAAAAAEWVo="
    ),
    "en": (
        "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"
    ),
    "es": (
        "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"
    ),
    "fr": (
        "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"
    ),
    "hi": (
        "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"
    ),
    "ja": (
        "/Td6WFoAAATm1rRGAgAhARwAAAAQz1jM4ESqEdVdAD2CgBkbmoDgvhEE0bGmCXLKK0vKYl9j1e6wM3cmNGIGjElsUy15hDU+ZvwVGCCxCMaBAj"
        "1taTE4hgwptbFkHO1xfszzMr3Xqi0MU4Q6/zY5tA+AqKcQ3/VtcYvO6U9u6UflSdeWYqSxYuuj++F+1bz2K3fQvGAhEcEkguLMznIWJHI5wvpb"
        "kKy2IaS8jROwR6WwkVnYW8DcNJ5MywGR1kQzgQ4TaSjIfmMcZXPEJISA5zo46W7Fo6qjENKydkfXVFjot6d5goUyNWXJ5wgvq6yK9Fx89b21KS"
        "VR6riZoib9vrZb/0b4n6VjAzXJ7TRFhrJ8dGw830YCgqP7NZ4YYBpS87lAFctZj3AwbJLMOTKx7Hl5+I/PcvUE1+6EDU+3EqcWn8M61JvHtMsZ"
        "TJtrlob4uR9wqVQ5OpWuxTMXAfa15prwtA8i6dtRetcWc2vvYzAcXFmqKKKANoLvqsggr6RStGzbuPhoA67bUstImvkxE/iNofeul9YFC78x/+"
        "GkThp3pN3infudSMDKAgByzDKtXIUf6mQhCO3BjVNGnnCSS2yQoJfUtofYlYbvV0xzmAKAa9BzqNRi0ka/LMpyncqBUPSFOkqCtLE9Tc3AI6Uj"
        "DRYLJx65c9LvxZh8WkAY9xddooLrd6oqOjkF3w3LMBICuRR851ipqau2S6auHl+oub/QIAGywAWJBBMB7L4In7MkgjxHZakjH5eksmqSmU4Adq"
        "u0/qjVnLBCK0uTJAIiEEcefis/7Ox02b0bhD3mzML0mceHVx9VTUz6PK4edHeabKqJHpyakVvWhKSvBG1FFqzqZzS3gxZAy1bLm2UK7BWzcDO0"
        "E6xZrZmZQ4gw6jHzhsYjjOCIdN6de5RrOhfuNbmASiIBUJ4O7rFn23zhLt1Rf9TcTs0tjPMHMroDwx6u94JLqikvtbJznllHeUurMVPH+YnjZ3"
        "qWRonxdTFH5R6LfeZ4Ig2fxqOlJ8W9K2RV8J1i1RrvzYPadAq1ixJqIs5lVO0DZtmBwhW2dgYtfqf0sn86U12hjfUPwrQlVp64o0r+AhiJyRj4"
        "Zn/T6I/UiMGrA++o/kpjOXI2hKyBFKbQw1B3Gsg1/09u8E3gULD7zzR2/G2uhPM89+x0X7FATpZvPs3UNMxMC8yolzUJqp1Tm6LAC1Aje5MrgE"
        "P1UfkXEt+W9dGEIqm8lP5jtLarEJSp4EShUowGrNb9mGpyDJizDqm4qggD0LDf4H6XpfrHD+Q3TRHHKF5f/i6e0jL1jyft6WTYUxExKL1UMKeW"
        "wl2mO7ej4rBJjKTflNymKpbSwW/+gMijPWo3pOhpkvTwGW17+kdKiBzEI0uTotSgYSEO1fJtl3oaoSSmrU/gVBiro5fUvrxyLMP/GSsipf/DLk"
        "F/FTUUFG/qnxaqbS+L7sOa8etEH8Zxq2P7n79LFvU1u+QFlBt1TQgVmXJH0xtCPDU8++sRZaiwsHYzZIkSe96I3YoOY7Dmbmz+hmbOGus48Rzu"
        "M6RfglunnluX9AmHnAHBJR7YblROoKDsTqd75+vjpvq5SApdiobNk7ZUO5RBjSAtqbs3Tl72MhI2AAKscHVpuAASo9g4+ZnS4H9S70GC2iDINU"
        "IL7qZanYa8++8kU9c2juyM31MGpqq36hQuI46vZM0Y0Vj5+i5bVL0s0FBMvwwXmiDc4wiZKoHDDs5rCxw+IJ6OH8MsJYbZq/2zH0M4wYvjulX4"
        "Yy/YqR/kkyGZPiBYowzLy6vaQi/lG73XWJkvupbgYodWmkRnmKuuo+2IRDX6hGqCxfJ7TPD9mI1g7WX3nD9q163z3Lr02gHpy0lelx3QajxfS5"
        "EtTaAFeqTsNdfymrMv6ry8SWKry5sBYBrckDY1Aw23L38gQy0mereNRFmGP91+S8s0rrS28UXqbyKlx206HsNkzvE8sJdzqz/s78/4eg4+l3j0"
        "/x+eru6VAnEUEUM1f44JxLudUiVR3mLofpaOSlIC3WBG8hF9dQjaKEHrIDrGFOHymJ6bqjSu9HMbyeKYCmn1cjxCXuKgNQPfLB9mRIe0fPb00R"
        "ryQcZDBRfSRAMOcWXoyDfr1DT3cvd/zw7o+EN+Z42fr8BtpIo7mPF7RQ/arWhzAk+Xg9DBpSfF8oP9Zhc15x41KBLYAmiyDdNijTQb7TeaH8pg"
        "bdvXsxQgCMugo9ccfsoCXV4zwifhBVR2oqQg2NH8CMBJhR2MoSqVOYX2WfzbY+eijkLIma4yNbDFQIh+0PtkgyPXzmHtoiZccmV01MRv8SlXHH"
        "9ELkG67N8w+w4XKo+odPxd0TEbZUnP5sVL6GdS2xNRtlj/WPQ/fR/ODGuQSoThCLfEzZFGFnkKCBlH9TVNDalyw3xTIk5fBamXAck/KvVDg8Zm"
        "n3YPQuEizAHK1mLzFL3ByerO1+SyfkkIaMMKyl0ZQarO2ymxIsnsFU6CCvoKKX4nEbHBjD+OUzvoEVcB6Amob0xcItEfVx+Evi5nxVns9aQJeo"
        "Mqmc/v32po7f2AUik+rWxcZzLqJi0iKlaobzqM0KuEmK5XISid8CGpBSa5Nz9LGPAn4wqmIjIYMEE0Lh3YCtaJ2W/f9P7RYzcZd1kR1vvR8yJ1"
        "0i+SDhCGAjEE0yWDBgxu6oWgwOVYivRyXjTrMboveeMi3Mxsc8Sor61Ou/FR3lrzZmpisdYguX7/C0ICcYoAYXGePPvuizZoxD4a8vUWk3cx2n"
        "6QHmvYFw8kj6IjtFpXD3YJwt7vq6cENgMJvtY1LhlHrxO3773q8KybEivP3YRNLqXVcYOWDEpdE5Sdxhunle+70/Mgv1qWGeCY5BEdUa+piexB"
        "2ozQdtjFOxU+mceo9e8J+NSEG9rqsjkmhmNr+wyQdeMDKAdzKUQWC3IQFNAPUG80FOhj4sj/mj2xExIVOTkobT5wOMT5aRbRJsO/DGH4m8S4Sj"
        "bTP8JiM44ltjbTDRHHvSqH0he54FYarTl11S1YS/JP6umUZ0EIHszN5+wnBxzgQn1qAbQ/2cr3dps9IscDtiRkJ4CmwUf9NhFs+vGa0O1zyy/Z"
        "Mm3cK0lqeeSJcQXny1T737K4szGjfPdTpc78iOD87rnaBq5NQ86vMT2b2IEcFNhc4lpPXumpbOXWzmgwP86mGMbANytvwQZ9ajgrqM9VoBVNa7"
        "2xlcw0y2sNK0555H82ju5VUwWTBnQFpFvjIbUr6NGGDAHpkOMONFwlaK8wPLUFhAr82uGryj5QjEzJvlLwGAAUs5DzVet+VY0kcgpiVLfA5mWI"
        "KkSxsgBcvou183k/gbw81A9E3sNbCSOXtDVvfQcjlf1kPR4AEzMvkgy8AiUiMJd+N76JoSI4V4tiivTaP5dTOlMRFQBxi3fa91sI7ZkU0zEWJ6"
        "FPe1eI3USekAc6bU04QlFN8h0VNiFdTTmy7zfwe51/Mkzj3Zy125PS3Qt4E5SD9SCnEpingpDT3QCC5PZzHBpJftRx6IDGcLqLvI5Ai+wWYa1k"
        "Q7gA0iXCJH+fsyefUuS02GUF7qXVM7eN6pKWSxS1mt8sF3eSQi/PYQAWYwhd+ZmG7urGERGYW9Kd0wNizDoo/VHtCMyq24rcO4Oh/u0N6MOY4f"
        "YY/qleMrzhibsyf2oGsVAUSa+z0yRt7kOsBhqpipOMvWKI0b9OpshXmYZSYo+Dtcyr0HFTUyK0XrxHa4jCbynDEC+o6XWF2aUUvETooGnpaarw"
        "V1iFRJgb4vzO92kDfCHiOimO0cPPOXFUowojQ8ZCp9CeRxkEb6fV7bkCSvoBGEsi3qtUoA3EQDitzD5cVGDXctIoZoZZhTDX0d2VMCelXIOgHP"
        "lpdxQA4OQ++RqVjtEjXABiUcTHYlG4jGkAcSdlqM/JQMfP9abJ0t/Uz4ZXha+43Wt03k44EfDNTIz0dIHHiv01YGMcyVjLZbJ9AFwbuabU5fFe"
        "I4nZJ/hC9QPY0Qli9s0AtDhniaFj2K3Ef9Pa+ZzTGAZtICw3pam9mxHjQZLqh9VLib8T/r0O6tWu0V0Lzhj5g+/z9XFiW26vC2dhmd4EhRufGv"
        "kftUUSYDHqNeCdTfbctiC7pbx1osRpxw75FieAb33tAfpf7LWYA/qP08+SxjGMEr9jDWWWI4WMjBGE8seyF/lohEyZJuOpryVVzvwU7SXMY4Vg"
        "T54NVu6XMQD8s1YSxs/nWZn9l0XHCdAFSmpqZiqyaQjkJ+eOrBhZ36F1iKy4JgIMnTAvXEPEZkQ8633QxyYBSFuszMY8Ygt57rV66zxmd5WYXa"
        "MRfOWHvC0LiLyyxA+HUaTQ4iDN8bI6qqmuXW+9JKeGB+Ois6LUXmY7OdFPPQRUrGVGIfXlvj4IB5ZFYbHE5pbQf8rzlooIDg9AmOms3G6z82xt"
        "BluNOWS1c2EMBUxBebQ7e9EdKw5BGbrfN4ydFwNfjR6rh+TrFsmFHAsZtgJrXwrId8up7RxbM7sMILPxmgMjjaLtZd276ZnOVl/Uvfx29aOfxQ"
        "RgxOngUPTOCAv8lEWIZ66jB5cTgs2mUMNXXlSpOY64AhXiaWLQJ/qIc1dk6WM8WHG7LKhnR4zLr1e387ENvua+jll4QG0b0tO624yjVlq9Okhy"
        "E8jHMPzd3g3wHlA2ZOEO+vAjA8p3JImn73PmLGBI2f04HzGo8qkRQw6Cz94PXfZnFsat3q7b3c0WxHKwPIO9b+Hh4uePUArm2HWqZ/fVa5kJlM"
        "6/V7u5LSrT4PR1MGos5+6Jvi3BCXR8XAPN42oo/1Uk+GPl5s9n0qbLcx9YWtqTrs9Y880mgcPphzWyaHuWu7TFEQ5dE+vg55dedVD6zSvdNY06"
        "Ts996iyRXJDFLHY5zEwSOmWmAg1M3pSxGt+KLdVdOh+ujbczd0GVT6CLHk3PCKBUj5Bl4Nt6InAI7Gvg4TJ9yGgNoa2ktPKxpMVZRelarViEkr"
        "s8RtoWwGEA6YRFobC8JpwAiibHsMWC2UEDOsU0ae5i8n0BQKsKVdOEeo8VdVZ5/ymnRHGd7Z9g5Uio11wbDvJX8dcaP+B3rUF3bSn6Qa5xWU+S"
        "UBa3az2gGb4hK3KKW2TwgLsX5O/wycjBghTYWg8QZRSV8q4KeNZxPrz3XJem3Q32OEX0wJyAX3hoXFTz0QHG9DFmm1DBe9WKywAnsbca2Mdqj6"
        "snAcxpf5TP1TnYSGthxMwB2P5n+S4g0sFdkH0yndiCteHDfIcKhpitmxvus5fwMM5IqZIMsd+eP7t6Q9wH99jJeDWrNqpDi5MKl6Ry516Mhwqi"
        "Z9QXwnu7yAF6ZrbSDaEd/r3NTmksuYrC7WNJ60qL8D/ekcZX197BthMHkNPSjnOt/NHzq6gUBSpG70TNvdf/9vCf5ptdGKTaV+86Ps7bnkYCHV"
        "IuA13npfA+ZWI++2I8p59ELhJPz6zWF3cjV4qi9xEVXKG4OgWtHOtExVYWZnVkk0KIpvz4cJYq8QfeniiED/z8aB8Rmy3TC4PFE5lHpkQe6Vb5"
        "+0i2DAC/FBJJB4IytNdNkfy5jghMRYIJIuZX0UQp+yEQHE/pszd/IQDM6ND7mY1ahE1lz8Uzhs+8amdXL8VoHlXnqCnvppjPPOM/inwOlk65pH"
        "60j2NZ9NMrZOuqHk3qMemjVrXMcI7Xbc6gfo01aQuQEjXHNJRGJ7gjPJXYphxF+CIHKRaB6F5cIjZpdHuQKcZdG+RQh0TC2UpNfKeMhhN9o8ZU"
        "78J3iemWruD74LcXcFASvcJ22UZrWhhVciNhkeVEZE/U3iCVk3yNy/hq0zBqFCapLoq7lZcPKLbE7x5HnhCiMc9gDM3Kl30Ph4hbnOt9MFpq1J"
        "A0ESrWTJ0wBZbeVUswZxtyXZL7363vyBRgD1AXK5zV1a4Fh2AjMhsKecfZuYRfzXAQBaFsd9N2va6Ls4Kk4lVMH7fJg6MdX/VCdhjZi7w1CYRJ"
        "q6PEi/FnqNAL2h+lPP8yNijXj1PboeYzF7DSnL9l6I9U0UkkMsZbUGtKPiUvYgKum+qhHIOGdrJ3qd4UQrvmKk6zViHDqOFpl0RmQQRAgrhZWM"
        "rioLz2NOI7paBMxxEesHMyOmIzw+rd62SYIVK1jUfAg1ZMSrqSBzWOGdJH3mm9aomINEmR0UQHxRjAAAAAAE499pMx4heTAAHxI6uJAQD/xG/2"
        "scRn+wIAAAAABFla"
    ),
    "my": (
        "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"
        "Z/sCAAAAAARZWg=="
    ),
    "pa": (
        "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"
    ),
    "pt": (
        "/Td6WFoAAATm1rRGAgAhARwAAAAQz1jM4DbgEQxdAD2CgBkbmoDgvhEE0bGmCW+i75OOaRZin/6bcWlbvysqL8skeSA7wGs+Bgn8QLbQz+fkn2"
        "9yfXaErJsW8kPSRRaKwxQsyqEJPtrVH7ZLie8bwciw3XGBgrChh1nIYlqb6mAJlq8i8TkYfHLQ/OJy54fE2vfo5pqS+qt5X6lbaukgVYN9gxcq"
        "9DRzDHcKVDtD+nxeWVzbWfA70Z3eEbcJQonOPlb5ezWJkJaMugoEvTxX9gnJ5FImudGMtreKrgT763WyVWNX4AODdKKZRB0Tu3AAd2f14qyzU0"
        "6Bdm8WTHMs7qjzTSbnu4Rqx8msfs4hV7l7oLjtdGIKn5WO80oj5TylH7oQYL/udtmiYNIDYVUYIv1mj1W2KiT9x+zD6BqPNutvqwLMHzM6BmIH"
        "YlV9mGiiqgopfaDpXswX1SaN/n5ElYaPn+EtpKKt6iT827bpSrCeawws3wFQK4FYh7wwguXeB10i1xcbFinfCpIGPPd7gVKgARprlqcrnIzv+4"
        "18dBTqt2zJ1Ot1mpB6K5bJQA9v5yBmqkMZhmh6g68KMT4Y4XBsvvx+3qAIPJX0DMLmTZVs19nY8AYvQFf3XCGBvXI+1mfU0XzFU8IhpZniJdFp"
        "ah+pxOem1IThQWlgJ/u/9EOSYY0kKxRpnfJtaM1PkCrPyzehEieijezHbuyXUnpH+jFLFQKjoLK5vsp65L8mm45lOLNhUkkgGfuyO+Q6COHw2n"
        "69qIoFKAJPrxuVgDzshEYZDEAPpRnI+0dwE3q4DKCBKiaX6ukS/va2N4QWUFVLcttXDQ3g9mVydfMupkKXqU6Wiu9gq/QjHo3pLy7kPBdX2ZtM"
        "9AJ4lFn80IX2E3mJdn2F0oD0qgiU2zLBpwjI9EAxQeJr8ll49uLTmIPTfPjJVT9J6+FSS0OIBjO7VO6E9GsxCgR3fVTk8g2eaM+oYp6cNI/PbD"
        "sauIlnpytbC7vdx6RjLDG/N9ehVxhu2gBQQHEe/Skce0FmU6iGofGONMgb5un3lQrYOdaWjTggiW9xGmc6fBRedMLTQM5s4qHAO/B05npPOCgB"
        "Rw51Y3iEITgYTLVuWcU9lfJ9wxcgnE+5tvILqKE6BLKnCAD/ZWaG0OY15Ivpf2t54xEY2i84JDZXSBuFeVnIyPmHEaI+alF21UUMT9ax5zlWis"
        "qyHKankVx2vpkgPddP3LfKYxuaKH5DoV2M/eOngcEyCz4oqnDULaAemaPChJ3cNBQ0jiyHtq7g0kgjlcefmcGtPdbLazKDceaNsoqB80CxEWjc"
        "B/xSUt5mEP/gInem7s/cjGogB4V+XCZGvFCPlWvYVD9UMPwNpoS7/NWCcGeBtO1r+cne3BBsLwR6YvqXjZOouRNJzJodeWkqg6BAyGj1xDeRQD"
        "QHps+sSnBAk/n0/RZGJalOz29U6Az7Rx9z/PfU25f6Iun7zZLBl+GO5UzwDcmlwqUfWYrJ9F3l+zo6oCPX/eoWMQ3RaG+WNx0CHg4AxhG+ee7t"
        "VDrVmDWaiGi7riqmlKeUQUOdYYeW+gnxO8fDDKgQJDFtrvMR5s8ZxtpYyw7u21G5Q6/KQXcXF159EQeqNtgkpbLwWZwjEaKwPrkczAw9MQQhDE"
        "j86rnCHabWAudOJPyAnVoWCFMTWq3k/LRl9pMumU8MbE2YCeu9u0NFnyVkZeAtWNcVXciOFlNu+ASGdB+FhO+FBI6KgVtwD3N2wD4tqZEwxLdi"
        "bP0Ia7BVQmjr5F6ySiMN1zmzNFtET1U3EUcANCfd3KeF6cLqkRLV0dPzVqdSTgAq/e6m0bGieij0gshxJ/u1Li5r/gGdp0xbcDiaQsUM8c2LH2"
        "xNG/2xFao+00Qs3Iq5/jK9N/foxGfrCvfwOv5X9TI9LravcmXbgePOfmYjOaRVsUjgGKLeLKKw/eNcbuLOvcG9WVSiI2cZTJqrNCxPu3WRS7OO"
        "kXla4/kpzwmd1NBGnk/9mqrwxBz+vOhc0ReoXKVi258KZWgWZTR3AyN+sSxlfUlTQymxnOH8VUk8hTkjNgtx8I9Do4qU92V54f9X10MOIrzrjA"
        "J6vDNNRQyJDLhVDEfWF9akzZzt4AEKBVGmkEqFDNCMitJVSZGra+wP2RagpQEmpw0oEjEA2H/xow31RBWmKD9iODDYhaOJ+j5PN0dONtXd994R"
        "5G+IC3khwBCneMGNJIpTgWZ0GXsdzuUMdFfP4tJCQ5qtwdizdoFfs9MERc2g/FHA/jFX0KiR2KR5k9dx3uXaPglYlm/Bwiv0iOcs51RKeRkB3B"
        "GaAYk8x7EgI81yyMjYH0FMwLR+tYhiCQ6OtTkaAxM6DIh5GncFoKnCDdaWxbf5+AmMchKOG0ICaqdRg1iExrQ2mSOUrwBmqFgrPcBWSHszf/i6"
        "iHDSAtb/NCJz3TYtlXeyh3JknQOa3Z+yWfWNfLXiNVBzSBi16sV7a9Pe4EFiTk2paHwbjLWAsc+jvhCS82ddb42BIF9WWWbFUUps52eRdo0azj"
        "Jq/9EJoIipB8cRPazlyN2ym2IfdcA6rk5B4qMjCUMrJ5YbY0rogvtR/+DOemKJcbvj1Kclk7RpROBDnY121suf4QGBhKYGWq5zuPVg0cIW6t1l"
        "ui9zSNy5rXO5shGzGr1bjLKJ2PLaiO+TShwxZShrjU9MKX7fUsy07FZGGBKdLJzEcrwgbn8PyNr4Wv8AIBMW8HN9jEtEitdgi1LBgzOGkWLT8w"
        "OMZxsMM8zT+bJNTAEpysoiyLceHXdoslDV0nTpZV+0p6il0m6a2+zxzszTqr0UuWpSi/SQs+AISNNjwx6FFSwUF9vpzXrWQOdZxjbe24BvUbSJ"
        "n93vTp70m4Tsc/EZA3Iw8vaCfrgC5pN+DsuFVfnZ0guibHNblV0q6kvqEErXGdI5+8D61Q/FIfezYyXAAINXng3VShP9ZF0sfCly5itRAu31W/"
        "8mweFWjAf5rUKZvaRO7TwYnQNjfT49EhWpaOTxDOx4pQcOj0fJL7cdcFIZVHqRK29LEAx7D1q+3zfJ0q3NjC5hSWHIUKWASYyfcgsRqYfIJNBJ"
        "YezTujL3VmFTPXRatxeEapGpXSX6P6IwU3cmfIcGUEY9Cu6246ZhoB7Cgt7E+82VWwykZp2JsovX47aW0um0tzvhl4+b0WCS4a6KFr5kg+sHeZ"
        "ob3R6dn2+AFrQ8uINXpa0UBaj/MFGADX5NOYpGE5Rr9gJN7ncchqkpOwGuD9fV+q0Ny/nzgl2AtLvZ3dNH3JmV6wKI1LzyJlUj77OgXjrYmYpm"
        "88gACUZskEJsxWpiC5mjM+r0eF5ch9FpJSxhBtls3xBLD62/NbGk9XNEZAbNo+phfuKj9TBtOi5PwAhZYQFlTRSa9jMtfysmvcS4Xy0dMpFsx+"
        "xKgswUZ0WcWo87EXUjt8VZW3m26TCyJzMhsN6IhTDPCkVceqw9x98fz1dT1kRsGnjlrIozxMI5VRQdyklUzYHQKeHyZ75jUKzv96ZAMBkthec7"
        "4iGY5rL4lcHC0sBM65iE/wgpXBCH07MPtHUXXcUCEkveLRaRFwiFsaJUGucL+J66iTHIiDJYK+mLqQx6RMY3HcKwH91944H60mvobD0WLGPvWr"
        "LfPMLXiN/49/n0WQXsBGqq3hGUdES8fCEJ6AGbbnShP3g8FMKv+TDcsv8FD2v7mh7cUiJwhxs0SrQbkXQxRnZL6Ow/1nloWoqry/t5ZAl60SC7"
        "4/HD/kJr9uAEee+ftoSKkbmRL7ePqFX4ZH9/dQPWBQ/D6PfoQktjKT1nJLzNpYZMCoNeEhWzL+YpjEE9mfCKSqK/8iLrj1etKElw2M6k423Lf8"
        "JjS5Ch/ENaUHhFqu3EiGKEEvLIM5ySVqCmHS6BBWOlmag6iwtXfm3z8FhvDOoR3iEaNmWxj+34Od49HpouEbp9aFdvFJ+KYTBMqpgCcqK3KSLV"
        "C3I6NOnC7VEBp9e1jCrVGVerkVzpte29ZqvHtRq//r3gjemBOB7B/Bus6gq03OZyfW9HJM1urzjGmDf+W2CjhzZHdDwe/PEO+7UC61NTZZkLSB"
        "g1NEgOQUjfRF2t5fZlk9ycr2+bpg0qjGmnd/D1EzLFfCbPeONG/aMjbadzSSONKI2NoeHsvOxbmcqpzGz0D3RzVy1yR/x/5+ziMaJwHmWjsHRR"
        "htAunudfq8QCShsPPG9usbeQyCj6d6tOPcvB3521cJLf/jqiAW2yEKDZ5sCuYzjb/F5wzEQXdjaJOwxLFKjyuLv3uWwgSqJV+XcA2ItGBGAHrr"
        "92mMtAiq8lFjW8+aOFIF8bAlTyvB23bcNaUE1QuwryCust7ogkGx6aa0tgU71kzOfHlGwlWx8OMVBi+qc9nNg+YLXyHZ3C6YWrh/rPxuiqv1Mz"
        "Phrd6jfdHLJTOt4HL4+Y+h/oVAWkGCvEh96GKanTj5gLi5Pkr6IUHoCfQlKKfEydJnLwkVJwm+xsMCyQ8y+fHJtLK4iM5dXMzZ1S9/RMVK56Ql"
        "oAQ2gJNX50Har1gOBcYnOLz5P0zJQbm4s3S/JuGi/xJuHrR6MMlblLOiZ63iIpXAPnw9n1jqsrARyTlkXkvDDuSqQ874AuXtl+CL2HGBy/fHX2"
        "J9v3C+gJq1XnHHE2TAIdVEf74f0igp7DpGjZg83Zcb2S+JJOc9UMVl2jvMW7cvAObRawT23p77cw/GwKWBtZlO2sztxHAQ8nue2aqNxAfp7wnr"
        "g3DTHiFbV+vvRRboQ9TkdSPwyw/BVXRGC3n300RW/IFJ/lwRKd4z7ceATHapjU9DXF1yQNBa+Y1malIeXFo3AKFRJRjEdLipcyrB7Sjtm6XKL/"
        "P406f9xslVS9B5Ahu69lb0oD0qCyyjzCI5/4liYRWcGP0YxyRFc4GL7DAGZb4IdW4B9Riv1P3IHKwbAYQhFp5dwZAbR8+KW1toUFM/W5YBu0HX"
        "8X6RQ+ZSqD2wnMdo83c2kdD+/Z3xQrhrwPn9siP+OYIOKghE5ZmWOGzClr6IZwSfUIuH4a0TIYACxezHC+4rvZxMIOQyCo0tDO6mi4+W2ipV6q"
        "zuU7xyfle0EVnvc+FjnwN5SUGcTxnM542WN+ZYPxBInYKcuU5aOafZ5i4xlzI228F3RxNM1QCN9qwRzU9RCuFbLl4SYAhJpmjMm/+LJ5Qn4ggv"
        "HhJQQDUq298q187/0zc1JPBRXwBvbeyCsbPSC1vejdjaTmF6vbwBGWeXh3S8DCgGOUJdOy7EGbnqNHit1p+OxQpNJ6QaUNoSy2HL97Pe2GkpT7"
        "J2TsNF3N4FQ18ky2R7K+tMvrGL4gnpPyggyKzbN6DYqzrtyFD7regDzxiVYWamTYTpieuCvz5VklCV+dsB9tVdglMocV3KrzlxotGT5IiknD2M"
        "s+X1W2VH40DXfUBflDvKq29Nzivd2YnuAHGRwSl66HeS2PW4cXOMTx73IshugP3sFYtvXm2AThvsYdMNq8I49p7jS94177lCJdMbW4X3IRo0cv"
        "SvmnVclLj2fe9D2vA6OyFIbtwEXBsmVgYc9Lj+Lz5Q/I+vL4ZxNA/R/DtGXD1XAZACjkTGavEynnmjpDy6VdyOw8oJk78XLNOaqhxrmy33UBTY"
        "U9004qS2UJPh8wv7gQW7xnirvyQ8JUgIx0M86/t7C3MuSsRz6DWaTWOYjNEV+XHQhlh3OyQCWfpenBPOjGgEsvNfSwMXBZ4AlkRSLywI7qUCgm"
        "PIwrLZWWPTciEJTebiW3yBPwdWEHEa1jjqpw65lDK+JiAAz2iW2DBhYoOYNId/E9uMHuTUKYLSul5qk34WIfz27qW1ubcre4L2st3OaFVIZTcw"
        "WBRGhhhnC5ojjrlohb9LW3ramw6JiAAK2gJ/lJawmHAAGoIuFtAAAURdejscRn+wIAAAAABFla"
    ),
    "ru": (
        "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"
    ),
    "tr": (
        "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"
    ),
    "zh": (
        "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"
    ),
}

_EMBEDDED_FONTS: dict[str, str] = {
    "Raleway-Bold.ttf": (
        "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"
    ),
    "Inter-Light.ttf": (
        "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"
        "nZ8JrJkZnBN5WLHEZ/sCAAAAAARZWg=="
    ),
}

logger.info("Embedded assets ready: 13 locales, 2 fonts.")


# ==============================================================================
# SECTION: LANGUAGE SYSTEM
# ==============================================================================
# ==============================================================================
# LANGUAGE SYSTEM  (13 locales embedded — kuch bhi install/copy nahi karna)
# ==============================================================================
lang_codes = {
    "en": "English",
    "hi": "हिन्दी",
    "ar": "العربية",
    "de": "Deutsch",
    "es": "Español",
    "fr": "Français",
    "ja": "日本語",
    "my": "မြန်မာဘာသာ",
    "pa": "ਪੰਜਾਬੀ",
    "pt": "Português",
    "ru": "Русский",
    "tr": "Türkçe",
    "zh": "中文",
}

# Extra strings jo naye features (Firebase/backup/logs) ke liye chahiye
EXTRA_LANG_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "backup_creating": "📦 <b>Backup snapshot bana rahe hain...</b>",
        "backup_created": "✅ <b>Backup ban gaya!</b>\n📁 <code>{}</code>\n📊 Size: <code>{}</code>",
        "backup_failed": "❌ Backup fail: <code>{}</code>",
        "backup_list": "📦 <b>Available Backups</b> ({})",
        "backup_none": "📭 Abhi tak koi backup nahi bana. /backup se turant banayein.",
        "restore_usage": "↩️ Kisi backup <code>.json</code>/<code>.json.gz</code> file par reply karke <code>/restore</code> bhejein.",
        "restore_ok": "✅ <b>Database restore ho gaya!</b>\n{}",
        "restore_fail": "❌ Restore fail: <code>{}</code>",
        "db_status": "🗄️ <b>Database Status</b>",
        "maintenance_on": "🛠️ <b>Maintenance mode ON</b> — sirf sudo commands chalenge.",
        "maintenance_off": "✅ <b>Maintenance mode OFF</b> — bot ab normal hai.",
        "sudo_only": "⛔ Ye command sirf sudo users ke liye hai.",
        "owner_only": "⛔ Ye command sirf bot owner ke liye hai.",
    },
    "hi": {
        "backup_creating": "📦 <b>बैकअप बना रहे हैं...</b>",
        "backup_created": "✅ <b>बैकअप तैयार!</b>\n📁 <code>{}</code>\n📊 आकार: <code>{}</code>",
        "backup_failed": "❌ बैकअप फेल: <code>{}</code>",
        "backup_list": "📦 <b>उपलब्ध बैकअप</b> ({})",
        "backup_none": "📭 अभी कोई बैकअप नहीं बना। /backup भेजें।",
        "restore_usage": "↩️ बैकअप फ़ाइल पर reply करके <code>/restore</code> भेजें।",
        "restore_ok": "✅ <b>डेटाबेस रिस्टोर हो गया!</b>\n{}",
        "restore_fail": "❌ रिस्टोर फेल: <code>{}</code>",
        "db_status": "🗄️ <b>डेटाबेस स्टेटस</b>",
        "maintenance_on": "🛠️ <b>मेंटेनेंस मोड चालू</b>",
        "maintenance_off": "✅ <b>मेंटेनेंस मोड बंद</b>",
        "sudo_only": "⛔ यह कमांड केवल sudo यूज़र्स के लिए है।",
        "owner_only": "⛔ यह कमांड केवल बॉट ओनर के लिए है।",
    },
}


class Language:
    """
    Multilingual support.

    Locales embedded (lzma+base64) hain, aur agar `locales/` folder me koi
    `.json` mile to wo embedded version ko override kar deti hai (custom
    translation support).
    """

    def __init__(self) -> None:
        self.lang_codes = lang_codes
        self.lang_dir = Path(config.LOCALES_DIR)
        self.languages = self.load_files()

    # ------------------------------------------------------------------
    def load_files(self) -> dict[str, dict]:
        languages: dict[str, dict] = {}

        # 1) Embedded locales
        for code, blob in _EMBEDDED_LOCALES.items():
            try:
                raw = lzma.decompress(base64.b64decode(blob)).decode("utf-8")
                languages[code] = json.loads(raw)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Embedded locale '%s' load fail: %s", code, exc)

        # 2) Folder locales (override / add)
        if self.lang_dir.exists():
            for file in sorted(self.lang_dir.glob("*.json")):
                try:
                    with open(file, "r", encoding="utf-8") as handle:
                        languages[file.stem] = json.load(handle)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Locale file %s load fail: %s", file.name, exc)

        # 3) Extra strings (backup/db/logs ke naye messages)
        for code, strings in EXTRA_LANG_STRINGS.items():
            target = languages.setdefault(code, {})
            for key, value in strings.items():
                target.setdefault(key, value)

        if "en" not in languages:
            languages["en"] = {}

        # 4) Missing keys -> English fallback (translations adhoori ho to crash na ho)
        english = languages["en"]
        for code, mapping in languages.items():
            if code == "en":
                continue
            for key, value in english.items():
                mapping.setdefault(key, value)

        logger.info("Loaded languages: %s", ", ".join(sorted(languages.keys())))
        return languages

    # ------------------------------------------------------------------
    async def get_lang(self, chat_id: int) -> dict:
        code = await db.get_lang(chat_id)
        return self.languages.get(code) or self.languages.get(config.LANG_CODE) or self.languages["en"]

    def get_languages(self) -> dict:
        codes = set(self.languages.keys()) | {file.stem for file in self.lang_dir.glob("*.json")} if self.lang_dir.exists() else set(self.languages.keys())
        return {code: self.lang_codes.get(code, code) for code in sorted(codes)}

    async def save_lang(self, chat_id: int, code: str) -> None:
        await db.set_lang(chat_id, code)

    # ------------------------------------------------------------------
    def language(self):
        """Decorator: message/query object par `.lang` attribute set karta hai."""

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                fallen = next(
                    (arg for arg in args if hasattr(arg, "chat") or hasattr(arg, "message")),
                    None,
                )
                if fallen is None or not getattr(fallen, "from_user", None):
                    return

                if hasattr(fallen, "chat") and not hasattr(fallen, "message"):
                    chat = fallen.chat
                else:
                    message = getattr(fallen, "message", None) or fallen
                    chat = getattr(message, "chat", None)
                if not chat:
                    return

                # Blacklisted chat/user -> chup chaap ignore + leave
                if chat.id in db.blacklisted:
                    logger.info("Chat %s is blacklisted, leaving...", chat.id)
                    with suppress(Exception):
                        await app.leave_chat(chat.id)
                    return

                lang_code = await db.get_lang(chat.id)
                setattr(
                    fallen,
                    "lang",
                    self.languages.get(lang_code) or self.languages["en"],
                )
                try:
                    return await func(*args, **kwargs)
                except (errors.ChannelPrivate, errors.MessageIdInvalid, errors.MessageNotModified):
                    return
                except (
                    errors.Forbidden,
                    errors.ChatWriteForbidden,
                ):
                    return

            return wrapper

        return decorator


lang = Language()


# ==============================================================================
# SECTION: GLUE HELPERS
# ==============================================================================
# ==============================================================================
# GLUE HELPERS  (fonts extraction, text utils, backup file helpers)
# ==============================================================================
def ensure_font(filename: str) -> str:
    """
    Embedded (lzma+base64) fonts ko disk par nikaal kar path return karta hai.
    Fonts missing ho to system font fallback (thumbnail phir bhi bane).
    """
    target = Path(config.FONTS_DIR) / filename
    if target.exists() and target.stat().st_size > 0:
        return str(target)

    blob = _EMBEDDED_FONTS.get(filename)
    if blob:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(lzma.decompress(base64.b64decode(blob)))
            return str(target)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Font extract fail (%s): %s", filename, exc)

    # Fallback: system fonts
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ):
        if Path(candidate).exists():
            return candidate
    return filename


def fmt_bytes(size: float | int | None) -> str:
    size = float(size or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.2f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.2f} TB"


def fmt_seconds(seconds: int | float | None) -> str:
    seconds = int(seconds or 0)
    if seconds < 0:
        seconds = 0
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def human_delta(seconds: float | int) -> str:
    seconds = int(max(0, seconds))
    periods = (("d", 86400), ("h", 3600), ("m", 60), ("s", 1))
    parts = []
    for suffix, length in periods:
        value, seconds = divmod(seconds, length)
        if value:
            parts.append(f"{value}{suffix}")
    return " ".join(parts) or "0s"


def time_ago(timestamp: float | int | None) -> str:
    if not timestamp:
        return "never"
    return human_delta(time.time() - float(timestamp)) + " ago"


def split_text(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks, current = [], ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > limit:
            chunks.append(current)
            current = ""
        current += line
    if current:
        chunks.append(current)
    return chunks or [text[:limit]]


def tail_file(path: str | Path, lines: int = 80) -> str:
    path = Path(path)
    if not path.exists():
        return ""
    try:
        with open(path, "rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - 200_000))
            raw = handle.read().decode("utf-8", errors="ignore")
        return "\n".join(raw.splitlines()[-lines:])
    except OSError:
        return ""


def deep_merge(base: dict, override: dict) -> dict:
    """Nested dict merge (override jeetta hai)."""
    result = json.loads(json.dumps(base)) if base else {}
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def read_backup_file(path: str | Path) -> dict:
    """`.json` ya `.json.gz` backup padhta hai."""
    path = Path(path)
    if str(path).endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def read_backup_bytes(raw: bytes) -> dict:
    if raw[:2] == b"\x1f\x8b":
        return json.loads(gzip.decompress(raw).decode("utf-8"))
    return json.loads(raw.decode("utf-8"))


def parse_time_str(value: str) -> int:
    """'1:30' / '90' / '0:01:30' -> seconds (invalid -> 0)."""
    if not value:
        return 0
    value = str(value).strip()
    if value.isdigit():
        return int(value)
    try:
        parts = [int(part) for part in value.split(":")]
    except ValueError:
        return 0
    return sum(part * 60 ** index for index, part in enumerate(reversed(parts)))


def html_escape(value: Any) -> str:
    return escape(str(value), quote=False)


def mention_of(user: Any) -> str:
    if user is None:
        return "Unknown"
    user_id = getattr(user, "id", 0) or 0
    name = getattr(user, "first_name", None) or "User"
    if getattr(user, "last_name", None):
        name = f"{name} {user.last_name}"
    return f'<a href="tg://user?id={user_id}">{html_escape(name)}</a>'


# ==============================================================================
# SECTION: DATACLASSES (Media / Track)
# ==============================================================================
@dataclass
class Media:
    id: str
    duration: str = "00:00"
    duration_sec: int = 0
    file_path: str = None
    message_id: int = 0
    title: str = None
    url: str = None
    time: int = 0
    user: str = None
    video: bool = False


@dataclass
class Track:
    id: str
    channel_name: str = None
    duration: str = "00:00"
    duration_sec: int = 0
    title: str = None
    url: str = None
    file_path: str = None
    message_id: int = 0
    time: int = 0
    thumbnail: str = None
    user: str = None
    view_count: str = None
    video: bool = False


# ==============================================================================
# SECTION: QUEUE
# ==============================================================================
MediaItem = Union[Media, Track]


class Queue:
    def __init__(self):
        self.queues: dict[int, deque[MediaItem]] = defaultdict(deque)

    def add(self, chat_id: int, item: MediaItem) -> int:
        """Add an item to the queue and return its position (1-based)."""
        self.queues[chat_id].append(item)
        return len(self.queues[chat_id]) - 1

    def check_item(self, chat_id: int, item_id: str) -> tuple[int, MediaItem | None]:
        """Check if an item with the given ID exists in the queue."""
        pos, track = next(
            (
                (i, track)
                for i, track in enumerate(list(self.queues[chat_id]))
                if track.id == item_id
            ),
            (-1, None),
        )
        return pos, track

    def force_add(
        self, chat_id: int, item: MediaItem, remove: int | bool = False
    ) -> None:
        """Replace the currently playing item with a new one."""
        self.remove_current(chat_id)
        self.queues[chat_id].appendleft(item)
        if remove:
            self.queues[chat_id].rotate(-remove)
            self.queues[chat_id].popleft()
            self.queues[chat_id].rotate(remove)

    def get_current(self, chat_id: int) -> MediaItem | None:
        """Return the currently playing item (first in queue), if any."""
        return self.queues[chat_id][0] if self.queues[chat_id] else None

    def get_next(self, chat_id: int, check: bool = False) -> MediaItem | None:
        """Remove current item and return the next one, or None if empty."""
        if not self.queues[chat_id]:
            return None
        if check:
            return self.queues[chat_id][1] if len(self.queues[chat_id]) > 1 else None

        self.queues[chat_id].popleft()
        return self.queues[chat_id][0] if self.queues[chat_id] else None

    def get_queue(self, chat_id: int) -> list[MediaItem]:
        """Return the full queue including the currently playing item."""
        return list(self.queues[chat_id])

    def remove_current(self, chat_id: int) -> None:
        """Remove the currently playing item only (if exists)."""
        if self.queues[chat_id]:
            self.queues[chat_id].popleft()

    def clear(self, chat_id: int) -> None:
        """Clear the entire queue."""
        self.queues[chat_id].clear()


# ==============================================================================
# SECTION: INLINE KEYBOARDS
# ==============================================================================
def mode_label(state: bool) -> str:
    """Play-mode ka button label."""
    return "🔒 Admin only" if state else "👥 Everyone"


def toggle_label(state: bool) -> str:
    """ON/OFF toggle ka button label."""
    return "✅ ON" if state else "❌ OFF"


class Inline:
    def __init__(self):
        self.ikm = types.InlineKeyboardMarkup
        self.ikb = types.InlineKeyboardButton

    def cancel_dl(self, text) -> types.InlineKeyboardMarkup:
        return self.ikm([[self.ikb(text=text, callback_data="cancel_dl")]])

    def controls(
        self,
        chat_id: int,
        status: str = None,
        timer: str = None,
        remove: bool = False,
    ) -> types.InlineKeyboardMarkup:
        keyboard = []
        if status:
            keyboard.append(
                [self.ikb(text=status, callback_data=f"controls status {chat_id}")]
            )
        elif timer:
            keyboard.append(
                [self.ikb(text=timer, callback_data=f"controls status {chat_id}")]
            )

        if not remove:
            keyboard.append(
                [
                    self.ikb(text="▷", callback_data=f"controls resume {chat_id}"),
                    self.ikb(text="II", callback_data=f"controls pause {chat_id}"),
                    self.ikb(text="⥁", callback_data=f"controls replay {chat_id}"),
                    self.ikb(text="‣‣I", callback_data=f"controls skip {chat_id}"),
                    self.ikb(text="▢", callback_data=f"controls stop {chat_id}"),
                ]
            )
        return self.ikm(keyboard)

    def help_markup(
        self, _lang: dict, back: bool = False
    ) -> types.InlineKeyboardMarkup:
        if back:
            rows = [
                [
                    self.ikb(text=_lang["back"], callback_data="help back"),
                    self.ikb(text=_lang["close"], callback_data="help close"),
                ]
            ]
        else:
            cbs = ["admins", "auth", "blist", "lang", "ping", "play", "queue", "stats", "sudo"]
            buttons = [
                self.ikb(text=_lang[f"help_{i}"], callback_data=f"help {cb}")
                for i, cb in enumerate(cbs)
            ]
            rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]

        return self.ikm(rows)

    def lang_markup(self, _lang: str) -> types.InlineKeyboardMarkup:
        langs = lang.get_languages()

        buttons = [
            self.ikb(
                text=f"{name} ({code}) {'✔️' if code == _lang else ''}",
                callback_data=f"lang_change {code}",
            )
            for code, name in langs.items()
        ]
        rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
        return self.ikm(rows)

    def ping_markup(self, text: str) -> types.InlineKeyboardMarkup:
        return self.ikm([[self.ikb(text=text, url=config.SUPPORT_CHAT)]])

    def play_queued(
        self, chat_id: int, item_id: str, _text: str
    ) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(
                        text=_text, callback_data=f"controls force {chat_id} {item_id}"
                    )
                ]
            ]
        )

    def queue_markup(
        self, chat_id: int, _text: str, playing: bool
    ) -> types.InlineKeyboardMarkup:
        _action = "pause" if playing else "resume"
        return self.ikm(
            [[self.ikb(text=_text, callback_data=f"controls {_action} {chat_id} q")]]
        )

    def settings_markup(
        self,
        lang: dict,
        admin_only: bool,
        cmd_delete: bool,
        language: str,
        chat_id: int,
        admin_panel: bool = False,
    ) -> types.InlineKeyboardMarkup:
        rows = [
                [
                    self.ikb(
                        text=lang["play_mode"] + " ➜",
                        callback_data="settings",
                    ),
                    self.ikb(text=admin_only, callback_data="settings play"),
                ],
                [
                    self.ikb(
                        text=lang["cmd_delete"] + " ➜",
                        callback_data="settings",
                    ),
                    self.ikb(text=cmd_delete, callback_data="settings delete"),
                ],
                [
                    self.ikb(
                        text=lang["language"] + " ➜",
                        callback_data="settings",
                    ),
                    self.ikb(text=lang_codes[language], callback_data="language"),
                ],
        ]
        if admin_panel:
            # Settings se seedha button wale admin panel par jaayein (dono linked)
            rows.append(
                [self.ikb(text="🎛️ Admin Panel", callback_data="admpanel home")]
            )
        return self.ikm(rows)

    def start_key(
        self, lang: dict, private: bool = False
    ) -> types.InlineKeyboardMarkup:
        rows = [
            [
                self.ikb(
                    text=lang["add_me"],
                    url=f"https://t.me/{app.username}?startgroup=true",
                )
            ],
            [self.ikb(text=lang["help"], callback_data="help")],
            [
                self.ikb(text=lang["support"], url=config.SUPPORT_CHAT),
                self.ikb(text=lang["channel"], url=config.SUPPORT_CHANNEL),
            ],
        ]
        if private:
            rows += [
                [
                    self.ikb(
                        text=lang["source"],
                        url="https://github.com/AnonymousX1025/AnonXMusic",
                    )
                ]
            ]
        else:
            rows += [[self.ikb(text=lang["language"], callback_data="language")]]
        return self.ikm(rows)

    def yt_key(self, link: str) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(text="❐", copy_text=link),
                    self.ikb(text="Youtube", url=link),
                ],
            ]
        )


# ==============================================================================
# SECTION: THUMBNAIL GENERATOR
# ==============================================================================
class Thumbnail:
    def __init__(self):
        self.rect = (914, 514)
        self.fill = (255, 255, 255)
        self.mask = Image.new("L", self.rect, 0)
        self.font1 = ImageFont.truetype(ensure_font("Raleway-Bold.ttf"), 30)
        self.font2 = ImageFont.truetype(ensure_font("Inter-Light.ttf"), 30)
        self.session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        self.session = aiohttp.ClientSession()
    async def close(self) -> None:
        await self.session.close()

    async def save_thumb(self, output_path: str, url: str) -> str:
        async with self.session.get(url) as resp:
            with open(output_path, "wb") as f: f.write(await resp.read())
        return output_path

    async def generate(self, song: Track, size=(1280, 720)) -> str:
        try:
            temp = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}.png"
            if os.path.exists(output):
                return output

            await self.save_thumb(temp, song.thumbnail)
            thumb = Image.open(temp).convert("RGBA").resize(
                size, Image.Resampling.LANCZOS,
            )
            blur = thumb.filter(ImageFilter.GaussianBlur(25))
            image = ImageEnhance.Brightness(blur).enhance(.40)

            _rect = ImageOps.fit(
                thumb, self.rect,
                method=Image.LANCZOS, centering=(0.5, 0.5),
            )
            ImageDraw.Draw(self.mask).rounded_rectangle(
                (0, 0, self.rect[0], self.rect[1]),
                radius=15,
                fill=255,
            )
            _rect.putalpha(self.mask)
            image.paste(_rect, (183, 30), _rect)

            draw = ImageDraw.Draw(image)
            draw.text(
                xy=(50, 560),
                text=f"{song.channel_name[:25]} | {song.view_count}",
                font=self.font2, fill=self.fill,
            )
            draw.text((50, 600), song.title[:50], font=self.font1, fill=self.fill)
            draw.text((40, 650), "0:01", font=self.font1)
            draw.line([(140, 670), (1160, 670)], fill=self.fill, width=5, joint="curve")
            draw.text((1185, 650), song.duration, font=self.font1, fill=self.fill)

            image.save(output)
            try: os.remove(temp)
            except Exception: pass
            return output
        except Exception:
            return config.DEFAULT_THUMB


# ==============================================================================
# SECTION: UTILITIES
# ==============================================================================
class Utilities:
    def __init__(self):
        pass

    def format_eta(self, seconds: int) -> str:
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}:{seconds % 60:02d} min"
        else:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            s = seconds % 60
            return f"{h}:{m:02d}:{s:02d} h"

    def format_size(self, bytes: int) -> str:
        if bytes >= 1024**3:
            return f"{bytes / 1024 ** 3:.2f} GB"
        elif bytes >= 1024**2:
            return f"{bytes / 1024 ** 2:.2f} MB"
        else:
            return f"{bytes / 1024:.2f} KB"

    def to_seconds(self, time: str) -> int:
        parts = [int(p) for p in time.strip().split(":")]
        return sum(value * 60**i for i, value in enumerate(reversed(parts)))


    def get_url(self, message_1: types.Message) -> str | None:
        link = None
        messages = [message_1]

        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)

        for message in messages:
            entities = message.entities or message.caption_entities or []

            for entity in entities:
                if entity.type == enums.MessageEntityType.TEXT_LINK:
                    link = entity.url
                    break
                elif entity.type == enums.MessageEntityType.URL:
                    text = message.text or message.caption
                    if not text:
                        continue
                    link = text[entity.offset: entity.offset + entity.length]
                    break

        if link:
            return link.split("&si")[0].split("?si")[0]
        return None


    async def extract_user(self, msg: types.Message) -> types.User | None:
        if msg.reply_to_message:
            return msg.reply_to_message.from_user

        if msg.entities:
            for e in msg.entities:
                if e.type == enums.MessageEntityType.TEXT_MENTION:
                    return e.user

        if msg.text:
            try:
                if m := re.search(r"@(\w{5,32})", msg.text):
                    return await app.get_users(m.group(0))
                if m := re.search(r"\b\d{6,15}\b", msg.text):
                    return await app.get_users(int(m.group(0)))
            except Exception:
                pass

        return None


    async def play_log(
        self,
        m: types.Message,
        link: str,
        title: str,
        duration: str,
    ) -> None:
        if m.chat.id == app.logger:
            return
        _text = m.lang["play_log"].format(
            app.name,
            m.chat.id,
            m.chat.title,
            m.from_user.id,
            m.from_user.mention,
            link,
            title,
            duration,
        )
        await app.send_message(chat_id=app.logger, text=_text)

    async def send_log(self, m: types.Message, chat: bool = False) -> None:
        if chat:
            user = m.from_user
            return await app.send_message(
                chat_id=app.logger,
                text=m.lang["log_chat"].format(
                    m.chat.id,
                    m.chat.title,
                    user.id if user else 0,
                    user.mention if user else "Anonymous",
                ),
            )

        await app.send_message(
            chat_id=app.logger,
            text=m.lang["log_user"].format(
                m.from_user.id,
                f"@{m.from_user.username}",
                m.from_user.mention,
            ),
        )


# ==============================================================================
# SECTION: ADMIN / PERMISSION HELPERS
# ==============================================================================
def admin_check(func):
    @wraps(func)
    async def wrapper(_, update: types.Message | types.CallbackQuery, *args, **kwargs):
        async def reply(text):
            if isinstance(update, types.Message):
                return await update.reply_text(text)
            else:
                return await update.answer(text, show_alert=True)

        chat = (
            update.chat
            if isinstance(update, types.Message)
            else update.message.chat
        )
        if chat.type == enums.ChatType.PRIVATE:
            return await func(_, update, *args, **kwargs)

        user_id = update.from_user.id
        admins = await db.get_admins(chat.id)

        if user_id in app.sudoers:
            return await func(_, update, *args, **kwargs)

        if user_id not in admins:
            return await reply(update.lang["user_no_perms"])

        return await func(_, update, *args, **kwargs)

    return wrapper


def can_manage_vc(func):
    @wraps(func)
    async def wrapper(_, update: types.Message | types.CallbackQuery, *args, **kwargs):
        chat_id = (
            update.chat.id
            if isinstance(update, types.Message)
            else update.message.chat.id
        )
        user_id = update.from_user.id

        if user_id in app.sudoers:
            return await func(_, update, *args, **kwargs)

        if await db.is_auth(chat_id, user_id):
            return await func(_, update, *args, **kwargs)

        admins = await db.get_admins(chat_id)
        if user_id in admins:
            return await func(_, update, *args, **kwargs)

        if isinstance(update, types.Message):
            return await update.reply_text(update.lang["user_no_perms"])
        else:
            return await update.answer(update.lang["user_no_perms"], show_alert=True)

    return wrapper


async def is_admin(chat_id: int, user_id: int) -> bool:
    if user_id in await db.get_admins(chat_id):
        return True
    try:
        member = await app.get_chat_member(chat_id, user_id)
        return member.status in [
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.OWNER,
        ]
    except Exception:
        return False


async def reload_admins(chat_id: int) -> list[int]:
    try:
        admins = [
            admin
            async for admin in app.get_chat_members(
                chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS
            )
            if not admin.user.is_bot
        ]
        return [admin.user.id for admin in admins]
    except Exception:
        return []


# ==============================================================================
# SECTION: PLAY GUARD (checkUB)
# ==============================================================================
def checkUB(play):
    async def wrapper(_, m: types.Message):
        if not m.from_user:
            return await m.reply_text(m.lang["play_user_invalid"])

        # Bot-only mode (SESSION nahi diya) -> playback available nahi hai
        if not config.ASSISTANT_MODE:
            return await m.reply_text(
                m.lang.get("no_assistant")
                or (
                    "🎙️ <b>Voice chat playback off hai</b> — koi assistant session set nahi hai.\n\n"
                    "Bot-only mode active hai (commands, admin panel, logs, database aur backups "
                    "sab kaam kar rahe hain).\n"
                    "Playback enable karne ke liye <code>SESSION</code> env var me assistant ka "
                    "string session daalein (@StringFatherBot) aur bot restart karein."
                )
            )

        chat_id = m.chat.id
        if m.chat.type != enums.ChatType.SUPERGROUP:
            await m.reply_text(m.lang["play_chat_invalid"])
            return await app.leave_chat(chat_id)

        if not m.reply_to_message and (
            len(m.command) < 2 or (len(m.command) == 2 and m.command[1] == "-f")
        ):
            return await m.reply_text(m.lang["play_usage"])

        if len(queue.get_queue(chat_id)) >= config.QUEUE_LIMIT:
            return await m.reply_text(m.lang["play_queue_full"].format(config.QUEUE_LIMIT))

        force = m.command[0].endswith("force") or (
            len(m.command) > 1 and "-f" in m.command[1]
        )
        video = m.command[0][0] == "v" and config.VIDEO_PLAY
        url = utils.get_url(m)
        if url and yt.invalid(url):
            return await m.reply_text(m.lang["play_not_found"].format(config.SUPPORT_CHAT))
        m3u8 = url and not yt.valid(url)

        play_mode = await db.get_play_mode(chat_id)
        if play_mode or force:
            adminlist = await db.get_admins(chat_id)
            if (
                m.from_user.id not in adminlist
                and not await db.is_auth(chat_id, m.from_user.id)
                and not m.from_user.id in app.sudoers
            ):
                return await m.reply_text(m.lang["play_admin"])

        if chat_id not in db.active_calls:
            client = await db.get_client(chat_id)
            try:
                member = await app.get_chat_member(chat_id, client.id)
                if member.status in [
                    enums.ChatMemberStatus.BANNED,
                    enums.ChatMemberStatus.RESTRICTED,
                ]:
                    try:
                        await app.unban_chat_member(
                            chat_id=chat_id, user_id=client.id
                        )
                    except Exception:
                        return await m.reply_text(
                            m.lang["play_banned"].format(
                                app.name,
                                client.id,
                                client.mention,
                                f"@{client.username}" if client.username else None,
                            )
                        )
            except errors.ChatAdminRequired:
                return await m.reply_text(m.lang["admin_required"])
            except (errors.UserNotParticipant, errors.exceptions.bad_request_400.UserNotParticipant):
                if m.chat.username:
                    invite_link = m.chat.username
                    try:
                        await client.resolve_peer(invite_link)
                    except Exception:
                        pass
                else:
                    try:
                        invite_link = (await app.get_chat(chat_id)).invite_link
                        if not invite_link:
                            invite_link = await app.export_chat_invite_link(chat_id)
                    except errors.ChatAdminRequired:
                        return await m.reply_text(m.lang["admin_required"])
                    except Exception as ex:
                        return await m.reply_text(
                            m.lang["play_invite_error"].format(type(ex).__name__)
                        )

                umm = await m.reply_text(m.lang["play_invite"].format(app.name))
                await asyncio.sleep(2)
                try:
                    await client.join_chat(invite_link)
                except errors.UserAlreadyParticipant:
                    pass
                except errors.InviteRequestSent:
                    await asyncio.sleep(2)
                    try:
                        await app.approve_chat_join_request(chat_id, client.id)
                    except errors.HideRequesterMissing:
                        pass
                    except Exception as ex:
                        return await umm.edit_text(
                            m.lang["play_invite_error"].format(type(ex).__name__)
                        )
                except Exception as ex:
                    logger.error(f"Error joining chat - {chat_id}: {ex}")
                    return await umm.edit_text(
                        m.lang["play_invite_error"].format(type(ex).__name__)
                    )

                await umm.delete()
                await client.resolve_peer(chat_id)

        if await db.get_cmd_delete(chat_id):
            try:
                await m.delete()
            except Exception:
                pass

        return await play(_, m, force, m3u8, video, url)

    return wrapper


# ==============================================================================
# SECTION: EVAL HELPERS
# ==============================================================================
async def meval(code: str, globs: dict, **kwargs):
    """
    Asynchronously evaluate a code string in a controlled environment.
    """

    # Copy globals to avoid mutation
    globs = globs.copy()

    # Special globals (for relative imports)
    _global_arg = "_globs"
    while _global_arg in globs:
        _global_arg = "_" + _global_arg

    kwargs[_global_arg] = {k: globs[k] for k in ("__name__", "__package__") if k in globs}

    root = ast.parse(code, mode="exec")
    if not root.body:
        return None

    ret_name = "_ret"
    while any(isinstance(n, ast.Name) and n.id == ret_name for n in ast.walk(root)) or ret_name in globs:
        ret_name = "_" + ret_name

    body = []
    body.append(ast.Expr(ast.Call(
        func=ast.Attribute(
            value=ast.Call(func=ast.Name(id="globals", ctx=ast.Load()), args=[], keywords=[]),
            attr="update", ctx=ast.Load()
        ),
        args=[], keywords=[ast.keyword(arg=None, value=ast.Name(id=_global_arg, ctx=ast.Load()))]
    )))
    body.append(ast.Assign(
        targets=[ast.Name(id=ret_name, ctx=ast.Store())],
        value=ast.List(elts=[], ctx=ast.Load())
    ))

    for node in root.body:
        if isinstance(node, ast.Expr):
            new_node = ast.Expr(
                value=ast.Call(
                    func=ast.Attribute(value=ast.Name(id=ret_name, ctx=ast.Load()), attr="append", ctx=ast.Load()),
                    args=[node.value], keywords=[]
                )
            )
            ast.copy_location(new_node, node)
            body.append(new_node)
        else:
            body.append(node)
    body.append(ast.Return(value=ast.Name(id=ret_name, ctx=ast.Load())))

    func_def = ast.AsyncFunctionDef(
        name="tmp",
        args=ast.arguments(
            posonlyargs=[], args=[], vararg=None,
            kwonlyargs=[ast.arg(arg=k) for k in kwargs.keys()],
            kw_defaults=[None] * len(kwargs),
            kwarg=None, defaults=[]
        ),
        body=body, decorator_list=[]
    )
    ast.fix_missing_locations(func_def)

    # Compile & execute
    locs = {}
    exec(compile(ast.Module([func_def], type_ignores=[]), "<meval>", "exec"), {}, locs)

    result = await locs["tmp"](**kwargs)
    if not result:
        return None
    result = [await r if hasattr(r, "__await__") else r for r in result]
    result = [r for r in result if r is not None]

    return result[0] if len(result) == 1 else (result or None)


def format_exception(exc: BaseException, tb: Optional[list[traceback.FrameSummary]] = None) -> str:
    """Format exception traceback into a readable string."""
    if tb is None:
        tb = traceback.extract_tb(exc.__traceback__)

    cwd = os.getcwd()
    for frame in tb:
        if cwd in frame.filename:
            frame.filename = os.path.relpath(frame.filename)

    return (
        "Traceback (most recent call last):\n"
        f"{''.join(traceback.format_list(tb))}"
        f"{type(exc).__name__}{': ' + str(exc) if str(exc) else ''}"
    )


# ==============================================================================
# SECTION: HELPER SINGLETONS
# ==============================================================================
buttons = Inline()
utils = Utilities()
queue = Queue()
thumb = Thumbnail()


# ==============================================================================
# SECTION: HYBRID DATABASE + BACKUP MANAGER
# ==============================================================================
# ==============================================================================
# HYBRID DATABASE ENGINE  (Firebase Realtime DB  ⟷  Local VPS Storage)
# ==============================================================================
# Ye class AnonXMusic ke MongoDB class ka drop-in replacement hai (same async
# API) lekin isme:
#   1. FIREBASE MODE  — FIREBASE_DATABASE_URL + service account set ho to data
#      Firebase Realtime Database me sync hota hai (debounced, background).
#   2. LOCAL VPS MODE — Firebase na ho (ya fail ho jaye) to data VPS par
#      data/database.json me atomically save hota hai.
# Dono modes me har change local mirror par bhi likha jaata hai => zero data loss,
# aur data/backups/ me automated snapshots bante rehte hain.
# ==============================================================================
DEFAULT_DATA: dict[str, Any] = {
    "meta": {"version": __version__, "created_at": int(time.time()), "updated_at": int(time.time())},
    "sudoers": [],
    "bl_users": [],
    "bl_chats": [],
    "logger": False,
    "users": [],
    "chats": [],
    "chat_meta": {},
    "auth": {},
    "assistant": {},
    "loop": {},
    "notified": [],
    "stats": {"boots": 0, "streams": 0},
    "settings": {},
    "maintenance": False,
    "branding": {},
}


class HybridDatabase:
    """
    Firebase Realtime Database + Local VPS hybrid storage.

    Public surface MongoDB jaisa hi rakha gaya hai taaki saara plugin code
    (jo `await db.get_sudoers()` etc. call karta hai) bina change chale.
    """

    def __init__(self) -> None:
        # ---- runtime caches (original MongoDB class jaisa) ------------------
        self.admin_list: dict[int, list[int]] = {}
        self.active_calls: dict[int, int] = {}
        self.admin_play: set[int] = set()
        self.blacklisted: list[int] = []
        self.cmd_delete: set[int] = set()
        self.loop: dict[int, int] = {}
        self.notified: set[int] = set()
        self.logger = False

        self.assistant: dict[int, int] = {}
        self.auth: dict[int, set[int]] = {}
        self.chats: list[int] = []
        self.users: list[int] = []
        self.lang: dict[int, str] = {}

        # ---- storage ---------------------------------------------------------
        self.data: dict[str, Any] = deep_merge(DEFAULT_DATA, {})
        self.mode: str = "local"
        self.degraded: bool = False
        self.last_error: str = ""
        self.last_sync_at: float = 0.0
        self.last_local_save_at: float = 0.0
        self.migrated_to_cloud: bool = False

        self._fb_ref = None
        self._dirty = False
        self._stop = False
        self._lock = asyncio.Lock()
        self._worker: Optional[asyncio.Task] = None
        self._fb_failures = 0

    # ==========================================================================
    # Connection / boot
    # ==========================================================================
    async def connect(self) -> None:
        config.ensure_dirs()
        self.data = deep_merge(DEFAULT_DATA, self._read_local())

        if config.FIREBASE_DATABASE_URL and FIREBASE_AVAILABLE:
            connected = await asyncio.to_thread(self._connect_firebase)
            if connected:
                self.mode = "firebase"
            else:
                self.mode = "local"
                self.degraded = True
                logger.warning(
                    "⚠️ [Database] Firebase connect nahi hua -> LOCAL VPS MODE active "
                    "(backup 'data/backups/' me chalega, data safe rahega)."
                )
        elif config.FIREBASE_DATABASE_URL and not FIREBASE_AVAILABLE:
            self.mode = "local"
            self.last_error = "firebase-admin install nahi hai"
            logger.warning(
                "⚠️ [Database] FIREBASE_DATABASE_URL set hai par `firebase-admin` missing hai -> "
                "LOCAL VPS MODE. Fix: pip install firebase-admin"
            )
        else:
            self.mode = "local"
            logger.info(
                "💾 [Database] LOCAL VPS STORAGE MODE active — data: %s | auto-backup: %s",
                config.DB_FILE,
                config.BACKUP_DIR,
            )

        await self.load_cache()
        self.data.setdefault("stats", {})["boots"] = int(self.data.get("stats", {}).get("boots", 0)) + 1
        self.mark_dirty()
        await self.flush(force=True)

    async def close(self) -> None:
        self._stop = True
        await self.flush(force=True)
        if self._worker and not self._worker.done():
            self._worker.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await self._worker

    def _connect_firebase(self) -> bool:
        """Firebase Realtime DB se connect + data pull. Thread me chalta hai."""
        try:
            cred_obj = self._load_credentials()
            if cred_obj is None:
                self.last_error = f"Firebase credentials nahi mile ({config.FIREBASE_CREDENTIALS})"
                return False

            options = {"databaseURL": config.FIREBASE_DATABASE_URL}
            if config.FIREBASE_STORAGE_BUCKET:
                options["storageBucket"] = config.FIREBASE_STORAGE_BUCKET

            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred_obj, options)

            self._fb_ref = fb_db.reference(config.FIREBASE_ROOT)
            remote = self._fb_ref.get()

            if isinstance(remote, dict) and remote:
                self.data = deep_merge(DEFAULT_DATA, remote)
                logger.info("🔥 [Database] Firebase Realtime DB se data load (root='%s').", config.FIREBASE_ROOT)
            else:
                self.migrated_to_cloud = bool(self._read_local())
                self._fb_ref.set(self.data)
                logger.info(
                    "🔥 [Database] Firebase connected (root='%s')%s",
                    config.FIREBASE_ROOT,
                    " — local data cloud par migrate ho gaya." if self.migrated_to_cloud else " — naya database bana.",
                )

            self.last_sync_at = time.time()
            self._fb_failures = 0
            self._write_local(force=True)
            return True
        except Exception as exc:  # noqa: BLE001
            self.last_error = f"{type(exc).__name__}: {exc}"
            logger.error("❌ [Database] Firebase init error: %s", self.last_error)
            return False

    @staticmethod
    def _load_credentials():
        if not FIREBASE_AVAILABLE:
            return None
        if config.FIREBASE_CREDENTIALS_JSON:
            try:
                return fb_credentials.Certificate(json.loads(config.FIREBASE_CREDENTIALS_JSON))
            except Exception as exc:  # noqa: BLE001
                logger.error("❌ FIREBASE_CREDENTIALS_JSON parse fail: %s", exc)
                return None

        for candidate in (
            Path(config.FIREBASE_CREDENTIALS),
            Path(config.FIREBASE_CREDENTIALS),
            Path("firebase_key.json"),
            Path("firebase_credentials.json"),
            Path("serviceAccountKey.json"),
        ):
            try:
                if str(candidate) and candidate.exists():
                    return fb_credentials.Certificate(str(candidate))
            except OSError:
                continue
        return None

    # ==========================================================================
    # Persistence core
    # ==========================================================================
    def _snapshot(self) -> dict[str, Any]:
        """Runtime state se persistent document banata hai."""
        chat_meta: dict[str, dict] = {}
        for chat_id in set(list(self.data.get("chat_meta", {}).keys())):
            chat_meta[str(chat_id)] = dict(self.data["chat_meta"][str(chat_id)])

        if self.cmd_delete:
            for chat_id in self.cmd_delete:
                chat_meta.setdefault(str(chat_id), {})["cmd_delete"] = True
        if self.admin_play:
            for chat_id in self.admin_play:
                chat_meta.setdefault(str(chat_id), {})["admin_play"] = True
        for chat_id, code in self.lang.items():
            chat_meta.setdefault(str(chat_id), {})["lang"] = code

        return {
            "meta": {
                "version": __version__,
                "updated_at": int(time.time()),
                "backend": "firebase" if self.mode == "firebase" else "local",
            },
            "sudoers": sorted(set(int(user) for user in self.data.get("sudoers", [])) | ({config.OWNER_ID} if config.OWNER_ID else set())),
            "bl_users": sorted(set(int(user) for user in self.blacklisted if int(user) > 0)),
            "bl_chats": sorted(set(int(chat) for chat in self.blacklisted if int(chat) < 0)),
            "logger": bool(self.logger),
            "users": list(self.users),
            "chats": list(self.chats),
            "chat_meta": chat_meta,
            "auth": {str(chat): sorted(int(user) for user in users) for chat, users in self.auth.items() if users},
            "assistant": {str(chat): int(num) for chat, num in self.assistant.items()},
            "loop": {str(chat): int(count) for chat, count in self.loop.items() if count},
            "notified": list(self.notified),
            "stats": dict(self.data.get("stats", {})),
            # ---- settings / maintenance / branding (pehle save hi nahi hote the) ----
            "maintenance": bool(
                self.data.get("maintenance")
                or (self.data.get("settings") or {}).get("maintenance")
            ),
            "settings": {
                key: value
                for key, value in (self.data.get("settings") or {}).items()
                if isinstance(value, (bool, int, float, str, dict, list))
            },
            # Branding me sirf chhota reference rehta hai (image data kabhi DB me nahi)
            "branding": dict(self.data.get("branding", {}) or {}),
        }

    def _apply(self, document: dict) -> None:
        """Persistent document ko runtime state par apply karta hai."""
        self.data = deep_merge(DEFAULT_DATA, document or {})

        sudoers = {int(user) for user in self.data.get("sudoers", []) if str(user).lstrip("-").isdigit()}
        if config.OWNER_ID:
            sudoers.add(config.OWNER_ID)
        # SUDO_USERS env se aaye users always sudo rehte hain (env authoritative hai)
        for user_id in config.SUDO_USERS:
            with suppress(TypeError, ValueError):
                sudoers.add(int(user_id))
        self.data["sudoers"] = sorted(sudoers)

        self.blacklisted = [int(chat) for chat in self.data.get("bl_chats", [])] + [
            int(user) for user in self.data.get("bl_users", [])
        ]
        self.logger = bool(self.data.get("logger", False))
        self.users = [int(user) for user in self.data.get("users", [])]
        self.chats = [int(chat) for chat in self.data.get("chats", [])]
        self.notified = {int(user) for user in self.data.get("notified", [])}

        chat_meta = self.data.get("chat_meta", {}) or {}
        self.cmd_delete = {int(chat) for chat, meta in chat_meta.items() if (meta or {}).get("cmd_delete")}
        self.admin_play = {int(chat) for chat, meta in chat_meta.items() if (meta or {}).get("admin_play")}
        self.lang = {
            int(chat): str((meta or {}).get("lang"))
            for chat, meta in chat_meta.items()
            if (meta or {}).get("lang")
        }

        self.auth = {
            int(chat): {int(user) for user in (users or [])}
            for chat, users in (self.data.get("auth", {}) or {}).items()
        }
        self.assistant = {
            int(chat): int(num) for chat, num in (self.data.get("assistant", {}) or {}).items()
        }
        self.loop = {int(chat): int(count) for chat, count in (self.data.get("loop", {}) or {}).items()}

    def _read_local(self) -> dict:
        path = Path(config.DB_FILE)
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            return loaded if isinstance(loaded, dict) else {}
        except Exception as exc:  # noqa: BLE001
            logger.error("❌ Local database read fail (%s). Backup se restore karein.", exc)
            return {}

    def _write_local(self, force: bool = False) -> bool:
        path = Path(config.DB_FILE)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = self._snapshot()
            tmp = path.with_suffix(path.suffix + ".tmp")
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            tmp.replace(path)
            self.last_local_save_at = time.time()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("❌ Local VPS save fail: %s", exc)
            return False

    def _push_cloud(self) -> bool:
        if self._fb_ref is None:
            return False
        try:
            self._fb_ref.set(self._snapshot())
            self.last_sync_at = time.time()
            self._fb_failures = 0
            if self.degraded:
                self.degraded = False
                logger.info("✅ [Database] Firebase connection wapas aa gaya.")
            return True
        except Exception as exc:  # noqa: BLE001
            self._fb_failures += 1
            self.last_error = f"{type(exc).__name__}: {exc}"
            if self._fb_failures == 1:
                logger.warning("⚠️ [Database] Firebase push fail (%s) — local mirror me save kar rahe hain.", exc)
            if self._fb_failures >= 3 and not self.degraded:
                self.degraded = True
                logger.error(
                    "🚨 [Database] Firebase lagataar fail -> DEGRADED mode. Data VPS par safe hai, "
                    "connection aate hi auto-sync ho jaayega."
                )
            return False

    def mark_dirty(self) -> None:
        self._dirty = True

    # backward compatible alias
    def save(self) -> None:
        self.mark_dirty()

    async def flush(self, force: bool = False) -> bool:
        if not self._dirty and not force:
            return True
        async with self._lock:
            self._write_local(force=force)
            if self.mode == "firebase":
                await asyncio.to_thread(self._push_cloud)
            self._dirty = False
        return True

    async def start_autosave(self) -> None:
        if self._worker and not self._worker.done():
            return
        self._stop = False
        self._worker = asyncio.create_task(self._autosave_worker(), name="db-autosave")

    async def _autosave_worker(self) -> None:
        interval = config.FIREBASE_SYNC_INTERVAL if self.mode == "firebase" else config.DB_LOCAL_FLUSH_INTERVAL
        while not self._stop:
            try:
                await asyncio.sleep(interval)
                if self._dirty:
                    await self.flush()
                if self.mode == "local" and config.FIREBASE_DATABASE_URL and FIREBASE_AVAILABLE:
                    if await asyncio.to_thread(self._connect_firebase):
                        self.mode = "firebase"
                        self.degraded = False
                        await self.flush(force=True)
                        interval = config.FIREBASE_SYNC_INTERVAL
                        logger.info("🔁 [Database] Firebase reconnect successful — live cloud sync on.")
            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception as exc:  # noqa: BLE001
                logger.error("Autosave worker error: %s", exc)

    # ==========================================================================
    # Manual sync (owner commands)
    # ==========================================================================
    async def push_to_firebase(self) -> tuple[bool, str]:
        if self.mode != "firebase":
            if not await asyncio.to_thread(self._connect_firebase):
                return False, "Firebase configure/connect nahi hai."
            self.mode = "firebase"
        if await asyncio.to_thread(self._push_cloud):
            return True, "Local data Firebase par push ho gaya."
        return False, f"Firebase push fail: {self.last_error}"

    async def pull_from_firebase(self) -> tuple[bool, str]:
        if self.mode != "firebase":
            if not await asyncio.to_thread(self._connect_firebase):
                return False, "Firebase configure/connect nahi hai."
            self.mode = "firebase"
        try:
            remote = await asyncio.to_thread(self._fb_ref.get)
        except Exception as exc:  # noqa: BLE001
            return False, f"Firebase read fail: {exc}"
        if not isinstance(remote, dict) or not remote:
            return False, "Firebase par data nahi mila."
        self._apply(remote)
        self.mark_dirty()
        await self.flush(force=True)
        return True, "Firebase ka data local par pull ho gaya."

    # ==========================================================================
    # Backup / restore hooks
    # ==========================================================================
    def export_dict(self) -> dict:
        payload = self._snapshot()
        payload["meta"]["exported_at"] = int(time.time())
        return payload

    def export_json(self, indent: int = 2) -> str:
        return json.dumps(self.export_dict(), indent=indent, ensure_ascii=False)

    async def import_data(self, document: dict) -> None:
        """Backup file ka data load karta hai + turant save."""
        self._apply(document)
        self.mark_dirty()
        await self.flush(force=True)

    # ==========================================================================
    # CACHE / CALL METHODS  (original MongoDB API)
    # ==========================================================================
    async def get_call(self, chat_id: int) -> bool:
        return chat_id in self.active_calls

    async def add_call(self, chat_id: int) -> None:
        self.active_calls[chat_id] = 1

    async def remove_call(self, chat_id: int) -> None:
        self.active_calls.pop(chat_id, None)

    async def playing(self, chat_id: int, paused: Optional[bool] = None):
        if paused is not None:
            self.active_calls[chat_id] = int(not paused)
        return bool(self.active_calls.get(chat_id, 0))

    async def get_admins(self, chat_id: int, reload: bool = False) -> list[int]:
        if chat_id not in self.admin_list or reload:
            self.admin_list[chat_id] = await reload_admins(chat_id)
        return self.admin_list[chat_id]

    async def get_loop(self, chat_id: int) -> int:
        return int(self.loop.get(chat_id, 0))

    async def set_loop(self, chat_id: int, count: int) -> None:
        self.loop[chat_id] = int(count)
        self.mark_dirty()

    # ==========================================================================
    # AUTH METHODS
    # ==========================================================================
    async def _get_auth(self, chat_id: int) -> set[int]:
        if chat_id not in self.auth:
            self.auth[chat_id] = set(self.auth.get(chat_id, set()))
        return self.auth[chat_id]

    async def is_auth(self, chat_id: int, user_id: int) -> bool:
        if chat_id in self.auth:
            return int(user_id) in self.auth[chat_id]
        return int(user_id) in set(self.data.get("auth", {}).get(str(chat_id), []) or [])

    async def add_auth(self, chat_id: int, user_id: int) -> None:
        users = await self._get_auth(chat_id)
        if int(user_id) not in users:
            users.add(int(user_id))
            self.mark_dirty()

    async def rm_auth(self, chat_id: int, user_id: int) -> None:
        users = await self._get_auth(chat_id)
        if int(user_id) in users:
            users.discard(int(user_id))
            self.mark_dirty()

    # ==========================================================================
    # ASSISTANT METHODS
    # ==========================================================================
    async def set_assistant(self, chat_id: int) -> int:
        total = max(1, len(userbot.clients))
        num = randint(1, total)
        self.assistant[chat_id] = num
        self.mark_dirty()
        return num

    async def get_assistant(self, chat_id: int):
        if not anon.clients:  # bot-only mode (koi assistant session nahi)
            return None
        if chat_id not in self.assistant:
            num = self.assistant.get(chat_id)
            if not num or num > len(anon.clients):
                num = await self.set_assistant(chat_id)
            self.assistant[chat_id] = num
        index = self.assistant[chat_id] - 1
        if index < 0 or index >= len(anon.clients):
            await self.set_assistant(chat_id)
            index = max(0, min(self.assistant[chat_id] - 1, len(anon.clients) - 1))
        return anon.clients[index]

    async def get_client(self, chat_id: int):
        if not userbot.clients:  # bot-only mode
            return None
        if chat_id not in self.assistant:
            await self.get_assistant(chat_id)
        num = self.assistant.get(chat_id, 1)
        clients = {1: userbot.one, 2: userbot.two, 3: userbot.three, 4: userbot.four}
        if num > len(userbot.clients):
            num = await self.set_assistant(chat_id)
            self.assistant[chat_id] = num
        return clients.get(num, userbot.one)

    # ==========================================================================
    # BLACKLIST METHODS
    # ==========================================================================
    async def add_blacklist(self, chat_id: int) -> None:
        chat_id = int(chat_id)
        if chat_id not in self.blacklisted:
            self.blacklisted.append(chat_id)
        key = "bl_chats" if chat_id < 0 else "bl_users"
        bucket = set(self.data.get(key, []))
        bucket.add(chat_id)
        self.data[key] = sorted(bucket)
        self.mark_dirty()

    async def del_blacklist(self, chat_id: int) -> None:
        chat_id = int(chat_id)
        if chat_id in self.blacklisted:
            self.blacklisted.remove(chat_id)
        key = "bl_chats" if chat_id < 0 else "bl_users"
        bucket = set(self.data.get(key, []))
        bucket.discard(chat_id)
        self.data[key] = sorted(bucket)
        self.mark_dirty()

    async def get_blacklisted(self, chat: bool = False) -> list[int]:
        if chat:
            return sorted(int(item) for item in self.data.get("bl_chats", []))
        return sorted(int(item) for item in self.data.get("bl_users", []))

    # ==========================================================================
    # CHAT METHODS
    # ==========================================================================
    async def is_chat(self, chat_id: int) -> bool:
        return int(chat_id) in self.chats

    async def add_chat(self, chat_id: int) -> None:
        chat_id = int(chat_id)
        if chat_id not in self.chats:
            self.chats.append(chat_id)
            self.mark_dirty()

    async def rm_chat(self, chat_id: int) -> None:
        chat_id = int(chat_id)
        if chat_id in self.chats:
            self.chats.remove(chat_id)
            self.mark_dirty()

    async def get_chats(self) -> list[int]:
        if not self.chats:
            self.chats = [int(chat) for chat in self.data.get("chats", [])]
        return self.chats

    # ==========================================================================
    # COMMAND DELETE / PLAY MODE
    # ==========================================================================
    async def get_cmd_delete(self, chat_id: int) -> bool:
        return int(chat_id) in self.cmd_delete

    async def set_cmd_delete(self, chat_id: int, delete: bool = False) -> None:
        chat_id = int(chat_id)
        if delete:
            self.cmd_delete.add(chat_id)
        else:
            self.cmd_delete.discard(chat_id)
        meta = self.data.setdefault("chat_meta", {}).setdefault(str(chat_id), {})
        meta["cmd_delete"] = bool(delete)
        self.mark_dirty()

    async def get_play_mode(self, chat_id: int) -> bool:
        return int(chat_id) in self.admin_play

    async def set_play_mode(self, chat_id: int, remove: bool = False) -> None:
        chat_id = int(chat_id)
        if remove:
            self.admin_play.discard(chat_id)
        else:
            self.admin_play.add(chat_id)
        meta = self.data.setdefault("chat_meta", {}).setdefault(str(chat_id), {})
        meta["admin_play"] = not remove
        self.mark_dirty()

    # ==========================================================================
    # LANGUAGE METHODS
    # ==========================================================================
    async def set_lang(self, chat_id: int, lang_code: str) -> None:
        chat_id = int(chat_id)
        self.lang[chat_id] = lang_code
        self.data.setdefault("chat_meta", {}).setdefault(str(chat_id), {})["lang"] = lang_code
        self.mark_dirty()

    async def get_lang(self, chat_id: int) -> str:
        chat_id = int(chat_id)
        if chat_id not in self.lang:
            meta = self.data.get("chat_meta", {}).get(str(chat_id), {}) or {}
            self.lang[chat_id] = meta.get("lang") or config.LANG_CODE
        return self.lang[chat_id]

    # ==========================================================================
    # LOGGER METHODS
    # ==========================================================================
    async def is_logger(self) -> bool:
        return bool(self.logger)

    async def get_logger(self) -> bool:
        self.logger = bool(self.data.get("logger", False))
        return self.logger

    async def set_logger(self, status: bool) -> None:
        self.logger = bool(status)
        self.data["logger"] = bool(status)
        self.mark_dirty()

    # ==========================================================================
    # SUDO METHODS
    # ==========================================================================
    async def add_sudo(self, user_id: int) -> None:
        bucket = set(int(user) for user in self.data.get("sudoers", []))
        bucket.add(int(user_id))
        self.data["sudoers"] = sorted(bucket)
        self.mark_dirty()

    async def del_sudo(self, user_id: int) -> None:
        bucket = set(int(user) for user in self.data.get("sudoers", []))
        bucket.discard(int(user_id))
        self.data["sudoers"] = sorted(bucket)
        self.mark_dirty()

    async def get_sudoers(self) -> list[int]:
        bucket = {int(user) for user in self.data.get("sudoers", [])}
        if config.OWNER_ID:
            bucket.add(config.OWNER_ID)
        return sorted(bucket)

    # ==========================================================================
    # USER METHODS
    # ==========================================================================
    async def is_user(self, user_id: int) -> bool:
        return int(user_id) in self.users

    async def add_user(self, user_id: int) -> None:
        user_id = int(user_id)
        if user_id not in self.users:
            self.users.append(user_id)
            self.mark_dirty()

    async def rm_user(self, user_id: int) -> None:
        user_id = int(user_id)
        if user_id in self.users:
            self.users.remove(user_id)
            self.mark_dirty()

    async def get_users(self) -> list[int]:
        if not self.users:
            self.users = [int(user) for user in self.data.get("users", [])]
        return self.users

    # ==========================================================================
    # STATUS
    # ==========================================================================
    @property
    def mode_label(self) -> str:
        if self.mode == "firebase":
            return "🔥 Firebase Realtime DB" + (" (DEGRADED — local mirror active)" if self.degraded else " + VPS mirror")
        return "💾 Local VPS Storage (Auto Backup ON)"

    async def stats_summary(self) -> str:
        db_file = Path(config.DB_FILE)
        size = db_file.stat().st_size if db_file.exists() else 0
        pending = "yes" if self._dirty else "no"
        lines = [
            f"• <b>Storage engine:</b> <code>{self.mode_label}</code>",
            f"• <b>Firebase URL:</b> <code>{config.FIREBASE_DATABASE_URL or 'not configured'}</code>",
            f"• <b>Firebase root:</b> <code>{config.FIREBASE_ROOT}</code>",
            f"• <b>Local file:</b> <code>{config.DB_FILE}</code> ({fmt_bytes(size)})",
            f"• <b>Pending writes:</b> <code>{pending}</code>",
            f"• <b>Last cloud sync:</b> <code>{time_ago(self.last_sync_at) if self.last_sync_at else 'never'}</code>",
            f"• <b>Last VPS write:</b> <code>{time_ago(self.last_local_save_at) if self.last_local_save_at else 'never'}</code>",
            f"• <b>Chats:</b> <code>{len(self.chats)}</code> | <b>Users:</b> <code>{len(self.users)}</code>",
            f"• <b>Sudoers:</b> <code>{len(await self.get_sudoers())}</code> | <b>Blacklisted:</b> <code>{len(self.blacklisted)}</code>",
        ]
        if self.last_error:
            lines.append(f"• <b>Last error:</b> <code>{html_escape(self.last_error[:180])}</code>")
        return "\n".join(lines)

    # MongoDB compatibility no-op
    async def migrate_coll(self) -> None:
        return None

    async def load_cache(self) -> None:
        """Runtime caches load karta hai (original MongoDB.load_cache jaisa)."""
        self._apply(self.data)
        await self.get_chats()
        await self.get_users()
        await self.get_blacklisted(True)
        await self.get_logger()
        logger.info(
            "Database cache loaded (%d chats, %d users, %d sudoers, mode=%s).",
            len(self.chats),
            len(self.users),
            len(await self.get_sudoers()),
            self.mode,
        )


db = HybridDatabase()


# ==============================================================================
# AUTOMATED BACKUP MANAGER
# ==============================================================================
class BackupManager:
    """
    Database backups ka pura lifecycle:

      * Snapshot   -> data/backups/database_backup_<kind>_<timestamp>.json[.gz]
      * Retention  -> MAX_BACKUPS_RETAINED se purane snapshots delete
      * Telegram   -> har backup LOGGER_ID (log group) me document ban kar
      * Remote dir -> BACKUP_REMOTE_DIR par copy (mounted disk / rclone)
      * Firebase   -> FIREBASE_STORAGE_BUCKET set ho to cloud upload
      * Restore    -> /restore (Telegram document) ya VPS file se
      * Scheduler  -> BACKUP_INTERVAL_HOURS ke hisaab se auto loop
    """

    PATTERNS = (
        "database_backup_*.json",
        "database_backup_*.json.gz",
        "db_backup_*.json",
        "db_backup_*.json.gz",
    )

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._stop = False
        self.last_path: Optional[str] = None
        self.last_at: float = 0.0
        self.last_error: str = ""
        self.count: int = 0

    # ---- snapshot ---------------------------------------------------------
    def create(self, kind: str = "auto") -> Optional[Path]:
        try:
            backup_dir = Path(config.BACKUP_DIR)
            backup_dir.mkdir(parents=True, exist_ok=True)
            # millisecond suffix -> same second me bhi har snapshot unique rahe
            stamp = time.strftime("%Y%m%d_%H%M%S") + f"{int(time.time() * 1000) % 1000:03d}"
            suffix = ".json.gz" if config.BACKUP_GZIP else ".json"
            path = backup_dir / f"database_backup_{kind}_{stamp}{suffix}"
            # Race-safe: same millisecond me bhi do snapshots overwrite na karein
            counter = 1
            while path.exists():
                path = backup_dir / f"database_backup_{kind}_{stamp}_{counter}{suffix}"
                counter += 1

            payload = db.export_dict()
            payload.setdefault("meta", {})["backup_kind"] = kind

            tmp = path.with_name(path.name + ".tmp")
            raw_json = json.dumps(payload, indent=2, ensure_ascii=False)
            if config.BACKUP_GZIP:
                # mtime=0 -> deterministic gzip header (diff-friendly backups)
                buffer = io.BytesIO()
                with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as gz:
                    gz.write(raw_json.encode("utf-8"))
                tmp.write_bytes(buffer.getvalue())
            else:
                tmp.write_text(raw_json, encoding="utf-8")
            tmp.replace(path)

            self.last_path = str(path)
            self.last_at = time.time()
            self.count += 1

            pruned = self.prune()
            self.copy_to_remote(path)
            self.upload_to_storage_async(path)

            logger.info(
                "📦 [Backup] '%s' snapshot: %s (%s)%s",
                kind,
                path.name,
                fmt_bytes(path.stat().st_size),
                f" | {pruned} purane prune kiye" if pruned else "",
            )
            return path
        except Exception as exc:  # noqa: BLE001
            self.last_error = f"{type(exc).__name__}: {exc}"
            logger.error("❌ [Backup] Snapshot fail: %s", self.last_error)
            return None

    # ---- retention / external copies --------------------------------------
    def list_backups(self) -> list[Path]:
        backup_dir = Path(config.BACKUP_DIR)
        if not backup_dir.exists():
            return []
        files: list[Path] = []
        for pattern in self.PATTERNS:
            files.extend(backup_dir.glob(pattern))
        try:
            return sorted(set(files), key=lambda item: item.stat().st_mtime)
        except OSError:
            return sorted(set(files))

    def prune(self) -> int:
        removed = 0
        backups = self.list_backups()
        while len(backups) > config.MAX_BACKUPS_RETAINED:
            old = backups.pop(0)
            try:
                old.unlink()
                removed += 1
            except OSError:
                break
        return removed

    def copy_to_remote(self, path: Path) -> bool:
        if not config.BACKUP_REMOTE_DIR:
            return False
        try:
            remote_dir = Path(config.BACKUP_REMOTE_DIR).expanduser()
            remote_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, remote_dir / path.name)
            logger.info("📁 [Backup] Remote copy: %s", remote_dir / path.name)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("⚠️ [Backup] Remote copy fail (%s): %s", config.BACKUP_REMOTE_DIR, exc)
            return False

    def upload_to_storage_async(self, path: Path) -> None:
        if not config.FIREBASE_STORAGE_BUCKET:
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(asyncio.to_thread(self.upload_to_storage, path))
        except RuntimeError:
            self.upload_to_storage(path)

    def upload_to_storage(self, path: Path) -> bool:
        if not config.FIREBASE_STORAGE_BUCKET or fb_storage is None:
            return False
        try:
            bucket = fb_storage.bucket(config.FIREBASE_STORAGE_BUCKET)
            blob = bucket.blob(f"music-x-bot-backups/{path.name}")
            blob.upload_from_filename(str(path))
            logger.info("☁️ [Backup] Firebase Storage upload: %s", path.name)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("⚠️ [Backup] Firebase Storage upload fail: %s", exc)
            return False

    # ---- verification / restore -------------------------------------------
    def verify(self, path: Path) -> tuple[bool, str]:
        try:
            data = read_backup_file(path)
            if not isinstance(data, dict) or not ({"chats", "users", "sudoers"} & set(data.keys())):
                return False, "Ye valid Music-x-bot database backup nahi hai."
            return True, (
                f"✅ Verified — chats: <code>{len(data.get('chats', []))}</code>, "
                f"users: <code>{len(data.get('users', []))}</code>, "
                f"sudoers: <code>{len(data.get('sudoers', []))}</code>"
            )
        except Exception as exc:  # noqa: BLE001
            return False, f"Corrupt backup: {exc}"

    async def restore_from_path(self, path: Path) -> tuple[bool, str]:
        path = Path(path)
        if not path.exists():
            return False, f"File nahi mili: {path}"
        ok, message = self.verify(path)
        if not ok:
            return False, message
        self.create("pre-restore")
        try:
            payload = await asyncio.to_thread(read_backup_file, path)
        except Exception as exc:  # noqa: BLE001
            return False, f"Backup padha nahi ja saka: {exc}"
        await db.import_data(payload)
        logger.info("♻️ [Backup] Restore complete: %s", path.name)
        return True, message

    async def restore_from_bytes(self, raw: bytes) -> tuple[bool, str]:
        try:
            payload = read_backup_bytes(raw)
        except Exception as exc:  # noqa: BLE001
            return False, f"Document parse fail: {exc}"
        if not isinstance(payload, dict):
            return False, "Backup format invalid."
        self.create("pre-restore")
        await db.import_data(payload)
        logger.info("♻️ [Backup] Telegram document se restore complete.")
        return True, (
            f"chats: <code>{len(payload.get('chats', []))}</code>, "
            f"users: <code>{len(payload.get('users', []))}</code>"
        )

    # ---- Telegram delivery -------------------------------------------------
    async def send_backup(self, client, chat_id: int, path: Optional[Path] = None, caption: str = "") -> bool:
        path = Path(path) if path else self.latest()
        if not path or not path.exists() or not chat_id:
            return False
        try:
            default_caption = (
                f"📦 <b>{BOT_DISPLAY_NAME} Database Backup</b>\n"
                f"🕒 <b>Time:</b> <code>{time.strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
                f"🗄️ <b>Engine:</b> {db.mode_label}\n"
                f"📊 <b>Size:</b> <code>{fmt_bytes(path.stat().st_size)}</code>\n"
                f"👥 <b>Chats:</b> <code>{len(db.chats)}</code> | <b>Users:</b> <code>{len(db.users)}</code>"
            )
            await client.send_document(chat_id=chat_id, document=str(path), caption=(caption or default_caption)[:1024])
            return True
        except Exception as exc:  # noqa: BLE001
            self.last_error = str(exc)
            logger.warning("⚠️ [Backup] Telegram delivery fail (%s): %s", chat_id, exc)
            return False

    def latest(self) -> Optional[Path]:
        backups = self.list_backups()
        return backups[-1] if backups else None

    # ---- lifecycle ---------------------------------------------------------
    async def on_startup(self, client=None) -> None:
        if not config.BACKUP_ON_START:
            return
        path = await asyncio.to_thread(self.create, "startup")
        if path and client and config.LOGGER_ID and config.BACKUP_TO_LOGGER:
            await self.send_backup(
                client,
                config.LOGGER_ID,
                path,
                caption=(
                    f"🚀 <b>{BOT_DISPLAY_NAME} v{__version__} started</b>\n"
                    f"📦 Startup backup attached.\n🗄️ Engine: {db.mode_label}"
                ),
            )

    async def on_shutdown(self) -> None:
        if config.BACKUP_ON_SHUTDOWN:
            path = await asyncio.to_thread(self.create, "shutdown")
            if path:
                logger.info("📦 [Backup] Shutdown snapshot saved: %s", path.name)

    async def start_scheduler(self, client) -> None:
        if self._task and not self._task.done():
            return
        self._stop = False
        self._task = asyncio.create_task(self._loop(client), name="auto-backup")

    async def stop_scheduler(self) -> None:
        self._stop = True
        if self._task and not self._task.done():
            self._task.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await self._task

    async def _loop(self, client) -> None:
        interval = max(60.0, config.BACKUP_INTERVAL_HOURS * 3600)
        logger.info(
            "⏰ [Backup] Auto-backup scheduler ON — har %.2f ghante | retention %d | delivery %s",
            config.BACKUP_INTERVAL_HOURS,
            config.MAX_BACKUPS_RETAINED,
            f"LOGGER_ID {config.LOGGER_ID}" if (config.LOGGER_ID and config.BACKUP_TO_LOGGER) else "sirf VPS disk",
        )
        while not self._stop:
            try:
                await asyncio.sleep(interval)
                path = await asyncio.to_thread(self.create, "auto")
                if path and config.LOGGER_ID and config.BACKUP_TO_LOGGER:
                    await self.send_backup(client, config.LOGGER_ID, path)
            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception as exc:  # noqa: BLE001
                logger.error("Auto backup loop error: %s", exc)

    # ---- reporting ---------------------------------------------------------
    def status_text(self, limit: int = 8) -> str:
        backups = self.list_backups()
        total = sum(item.stat().st_size for item in backups if item.exists())
        lines = [
            "📦 <b>Automated Backup System</b>",
            "",
            f"• <b>Interval:</b> <code>har {config.BACKUP_INTERVAL_HOURS} ghante</code>",
            f"• <b>Retention:</b> <code>last {config.MAX_BACKUPS_RETAINED} snapshots</code>",
            f"• <b>Folder:</b> <code>{config.BACKUP_DIR}</code>",
            f"• <b>Snapshots:</b> <code>{len(backups)}</code> ({fmt_bytes(total)})",
            f"• <b>Compression:</b> <code>{'gzip' if config.BACKUP_GZIP else 'plain json'}</code>",
            f"• <b>Telegram delivery:</b> <code>{'ON -> ' + str(config.LOGGER_ID) if (config.LOGGER_ID and config.BACKUP_TO_LOGGER) else 'OFF'}</code>",
            f"• <b>Remote dir copy:</b> <code>{config.BACKUP_REMOTE_DIR or 'disabled'}</code>",
            f"• <b>Firebase Storage:</b> <code>{config.FIREBASE_STORAGE_BUCKET or 'disabled'}</code>",
            f"• <b>Startup/Shutdown backup:</b> <code>{config.BACKUP_ON_START}</code> / <code>{config.BACKUP_ON_SHUTDOWN}</code>",
            f"• <b>Last backup:</b> <code>{time_ago(self.last_at) if self.last_at else 'never'}</code>",
        ]
        if backups:
            lines.append("")
            lines.append("<b>Recent snapshots:</b>")
            for path in reversed(backups[-limit:]):
                stamp = time.strftime("%d %b %H:%M", time.localtime(path.stat().st_mtime))
                lines.append(f"• <code>{path.name}</code> — {fmt_bytes(path.stat().st_size)} — {stamp}")
        else:
            lines.append("")
            lines.append("<i>Koi snapshot nahi mila. /backup se turant banayein.</i>")
        if self.last_error:
            lines.append("")
            lines.append(f"⚠️ <b>Last error:</b> <code>{html_escape(self.last_error[:180])}</code>")
        return "\n".join(lines)


backup_manager = BackupManager()

# Backward-compatible short alias (naye commands ise use karte hain)
backup = backup_manager


# ==============================================================================
# SECTION: YOUTUBE + TELEGRAM ENGINES
# ==============================================================================
# ==============================================================================
# YOUTUBE ENGINE  (search + playlist + yt-dlp download + cookies)
# ==============================================================================
def run_ytdlp_download(opts: dict, url: str, video: bool = False) -> Optional[str]:
    """
    Blocking yt-dlp download (asyncio.to_thread ke andar chalta hai).
    Downloaded file ka actual path return karta hai, warna None.
    """
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
            except yt_dlp.utils.DownloadError as exc:
                logger.warning("Download failed (%s): %s", url, exc)
                return None
            except Exception as exc:  # noqa: BLE001
                logger.warning("Download unexpected error (%s): %s", url, exc)
                return None

            if not info:
                return None
            if info.get("entries"):  # playlist entry (noplaylist hone par bhi safe)
                info = info["entries"][0]

            resolved = None
            with suppress(Exception):
                resolved = ydl.prepare_filename(info)

        candidates: list[str] = []
        if video and resolved:
            candidates.append(os.path.splitext(resolved)[0] + ".mp4")
        if resolved:
            candidates.append(resolved)

        video_id = info.get("id", "")
        if video_id:
            for ext in ("mp4", "webm", "m4a", "mkv", "opus"):
                candidates.append(str(Path(config.DOWNLOADS_DIR) / f"{video_id}.{ext}"))

        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate

        if video_id:
            matches = [
                path
                for path in glob.glob(str(Path(config.DOWNLOADS_DIR) / f"{video_id}.*"))
                if not path.endswith((".part", ".ytdl", ".temp"))
            ]
            if matches:
                return matches[0]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Download error: %s", exc)
    return None


class YouTube:
    """
    YouTube search / playlist / download engine.

    Cookies sources (priority):
      1. config.COOKIES_DIR ke andar saari *.txt files
      2. config.COOKIES_FILE (cookies.txt)
      3. COOKIES_CONTENT / COOKIES_B64 env vars (runtime par file bana deta hai)
      4. COOKIES_URL (batbin.me) se startup par download
    """

    def __init__(self) -> None:
        self.base = "https://www.youtube.com/watch?v="
        self.cookies: list[str] = []
        self.checked = False
        self.warned = False
        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )
        self.iregex = re.compile(
            r"https?://(?:www\.|m\.|music\.)?(?:youtube\.com|youtu\.be)"
            r"(?!/(watch\?v=[A-Za-z0-9_-]{11}|shorts/[A-Za-z0-9_-]{11}"
            r"|playlist\?list=PL[A-Za-z0-9_-]+|[A-Za-z0-9_-]{11}))\S*"
        )

    # ---- cookies -----------------------------------------------------------
    def _materialize_env_cookies(self) -> None:
        """COOKIES_CONTENT / COOKIES_B64 ko cookies file me likh deta hai."""
        if not config.COOKIE_ENABLED:
            return
        target = Path(config.COOKIES_FILE)
        if target.exists() and target.stat().st_size > 0:
            return

        content = ""
        if config.COOKIES_B64:
            with suppress(Exception):
                content = base64.b64decode(config.COOKIES_B64).decode("utf-8", errors="ignore")
        elif config.COOKIES_CONTENT:
            raw = config.COOKIES_CONTENT
            if "# Netscape" in raw:
                content = raw
            else:
                with suppress(Exception):
                    decoded = base64.b64decode(raw).decode("utf-8", errors="ignore")
                    if "# Netscape" in decoded or "youtube.com" in decoded:
                        content = decoded
                if not content:
                    content = raw

        if content.strip():
            with suppress(OSError):
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                logger.info("🍪 Cookies env se %s par save ki gayi.", target)

    def get_cookies(self) -> Optional[str]:
        """Available cookies me se ek random file return karta hai."""
        if not config.COOKIE_ENABLED:
            return None

        if not self.checked:
            self._materialize_env_cookies()
            cookie_dir = Path(config.COOKIES_DIR)
            if cookie_dir.exists():
                for file in sorted(cookie_dir.glob("*.txt")):
                    if file.stat().st_size > 0:
                        self.cookies.append(str(file))
            single = Path(config.COOKIES_FILE)
            if single.exists() and single.stat().st_size > 0 and str(single) not in self.cookies:
                self.cookies.append(str(single))
            self.checked = True

        if not self.cookies:
            if not self.warned:
                self.warned = True
                logger.warning(
                    "🍪 Cookies missing — YouTube downloads fail ho sakti hain "
                    "(datacenter IP par bot-check aata hai). cookies.txt ya COOKIES_B64 set karein."
                )
            return None
        return random.choice(self.cookies)

    async def save_cookies(self, urls: list[str]) -> None:
        """batbin.me URLs se cookies download karta hai (COOKIES_URL env)."""
        if not urls:
            return
        logger.info("Saving cookies from urls...")
        cookie_dir = Path(config.COOKIES_DIR)
        cookie_dir.mkdir(parents=True, exist_ok=True)
        async with aiohttp.ClientSession() as session:
            for url in urls:
                name = url.split("/")[-1]
                link = "https://batbin.me/raw/" + name
                try:
                    async with session.get(link) as resp:
                        resp.raise_for_status()
                        (cookie_dir / f"{name}.txt").write_bytes(await resp.read())
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Cookie download fail (%s): %s", link, exc)
        self.checked = False
        self.cookies.clear()
        logger.info("Cookies saved in %s.", cookie_dir)

    # ---- validation --------------------------------------------------------
    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url or ""))

    def invalid(self, url: str) -> bool:
        return bool(re.match(self.iregex, url or ""))

    def path_for(self, video_id: str, video: bool = False) -> str:
        ext = "mp4" if video else "webm"
        return str(Path(config.DOWNLOADS_DIR) / f"{video_id}.{ext}")

    # ---- search ------------------------------------------------------------
    @staticmethod
    def _to_seconds(duration: str | int | None) -> int:
        if isinstance(duration, (int, float)):
            return int(duration)
        return parse_time_str(duration or "0:00")

    async def search(self, query: str, m_id: int, video: bool = False) -> Optional[Track]:
        """Query se pehla YouTube result return karta hai (ya None)."""
        try:
            _search = VideosSearch(query, limit=1, with_live=False)
            results = await _search.next()
        except Exception as exc:  # noqa: BLE001
            logger.warning("YouTube search fail: %s", exc)
            return None

        if not (results and results.get("result")):
            # yt-dlp fallback (py-yt-search block ho jaye to)
            return await self._search_with_ytdlp(query, m_id, video)

        data = results["result"][0]
        thumbnails = data.get("thumbnails") or [{}]
        return Track(
            id=data.get("id"),
            channel_name=(data.get("channel") or {}).get("name", ""),
            duration=data.get("duration") or "00:00",
            duration_sec=self._to_seconds(data.get("duration")),
            message_id=m_id,
            title=(data.get("title") or "Unknown")[:45],
            thumbnail=(thumbnails[-1].get("url") or "").split("?")[0],
            url=data.get("link") or f"{self.base}{data.get('id')}",
            view_count=(data.get("viewCount") or {}).get("short", ""),
            video=video,
        )

    async def _search_with_ytdlp(self, query: str, m_id: int, video: bool) -> Optional[Track]:
        def _run():
            opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "extract_flat": True,
                "noplaylist": True,
                "nocheckcertificate": True,
                "geo_bypass": True,
            }
            cookie = self.get_cookies()
            if cookie:
                opts["cookiefile"] = cookie
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            entries = (info or {}).get("entries") or []
            return entries[0] if entries else None

        try:
            entry = await asyncio.to_thread(_run)
        except Exception as exc:  # noqa: BLE001
            logger.warning("yt-dlp search fallback fail: %s", exc)
            return None
        if not entry:
            return None

        video_id = entry.get("id") or ""
        return Track(
            id=video_id,
            channel_name=entry.get("uploader") or entry.get("channel") or "",
            duration=entry.get("duration_string") or fmt_seconds(entry.get("duration") or 0),
            duration_sec=int(entry.get("duration") or 0),
            message_id=m_id,
            title=(entry.get("title") or "Unknown")[:45],
            thumbnail=entry.get("thumbnail") or (f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else ""),
            url=entry.get("webpage_url") or f"{self.base}{video_id}",
            view_count="",
            video=video,
        )

    # ---- playlist ----------------------------------------------------------
    async def playlist(self, limit: int, user: str, url: str, video: bool) -> list[Track]:
        """Playlist URL se tracks (py_yt -> yt-dlp fallback)."""
        tracks: list[Track] = []
        try:
            plist = await Playlist.get(url)
            for data in (plist or {}).get("videos", [])[:limit]:
                thumbnails = data.get("thumbnails") or [{}]
                tracks.append(
                    Track(
                        id=data.get("id"),
                        channel_name=(data.get("channel") or {}).get("name", ""),
                        duration=data.get("duration") or "00:00",
                        duration_sec=self._to_seconds(data.get("duration")),
                        title=(data.get("title") or "Unknown")[:45],
                        thumbnail=(thumbnails[-1].get("url") or "").split("?")[0],
                        url=(data.get("link") or "").split("&list=")[0],
                        user=user,
                        view_count="",
                        video=video,
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("py-yt playlist fail (%s) -> yt-dlp fallback.", exc)

        if not tracks:
            tracks = await self._playlist_with_ytdlp(limit, user, url, video)
        return tracks

    async def _playlist_with_ytdlp(self, limit: int, user: str, url: str, video: bool) -> list[Track]:
        def _run():
            opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "extract_flat": "in_playlist",
                "noplaylist": False,
                "nocheckcertificate": True,
                "geo_bypass": True,
            }
            cookie = self.get_cookies()
            if cookie:
                opts["cookiefile"] = cookie
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            return (info or {}).get("entries") or []

        try:
            entries = await asyncio.to_thread(_run)
        except Exception as exc:  # noqa: BLE001
            logger.warning("yt-dlp playlist fail: %s", exc)
            return []

        tracks: list[Track] = []
        for entry in entries[:limit]:
            if not entry:
                continue
            video_id = entry.get("id") or ""
            tracks.append(
                Track(
                    id=video_id,
                    channel_name=entry.get("uploader") or "",
                    duration=entry.get("duration_string") or fmt_seconds(entry.get("duration") or 0),
                    duration_sec=int(entry.get("duration") or 0),
                    title=(entry.get("title") or "Unknown")[:45],
                    thumbnail=entry.get("thumbnail") or (f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else ""),
                    url=entry.get("url") or f"{self.base}{video_id}",
                    user=user,
                    view_count="",
                    video=video,
                )
            )
        return tracks

    # ---- download ----------------------------------------------------------
    async def download(self, video_id: str, video: bool = False) -> Optional[str]:
        """Audio (webm/opus) ya video (mp4) download karke local path return karta hai."""
        url = video_id if str(video_id).startswith("http") else self.base + str(video_id)
        guess = self.path_for(str(video_id), video)
        if Path(guess).exists() and Path(guess).stat().st_size > 0:
            return guess

        cookie = self.get_cookies()
        opts: dict[str, Any] = {
            "outtmpl": str(Path(config.DOWNLOADS_DIR) / "%(id)s.%(ext)s"),
            "quiet": True,
            "noplaylist": True,
            "geo_bypass": True,
            "no_warnings": True,
            "overwrites": False,
            "nocheckcertificate": True,
            "noprogress": True,
            "retries": 5,
            "fragment_retries": 5,
            "socket_timeout": 30,
            "concurrent_fragment_downloads": 3,
        }
        if cookie:
            opts["cookiefile"] = cookie
        if config.YTDLP_PLAYER_CLIENT:
            opts["extractor_args"] = {"youtube": {"player_client": config.YTDLP_PLAYER_CLIENT.split(",")}}

        if video:
            opts.update(
                {
                    "format": (
                        "bestvideo[height<=?720][ext=mp4]+bestaudio[ext=m4a]/"
                        "bestvideo[height<=?720]+bestaudio/best[height<=?720]/best"
                    ),
                    "merge_output_format": "mp4",
                }
            )
        else:
            opts["format"] = "bestaudio[ext=webm][acodec=opus]/bestaudio[ext=m4a]/bestaudio/best"

        return await asyncio.to_thread(run_ytdlp_download, opts, url, video)


yt = YouTube()


# ==============================================================================
# TELEGRAM MEDIA DOWNLOADER
# ==============================================================================
class Telegram:
    """Telegram video/audio/document/voice download + m3u8 handling."""

    def __init__(self) -> None:
        self.active: list[str] = []
        self.events: dict[int, asyncio.Event] = {}
        self.last_edit: dict[int, float] = {}
        self.active_tasks: dict[int, asyncio.Task] = {}
        self.sleep = 5

    def get_media(self, msg: types.Message) -> bool:
        if msg is None:
            return False
        return any([msg.video, msg.audio, msg.document, msg.voice])

    async def cancel(self, query: types.CallbackQuery):
        event = self.events.get(query.message.id)
        task = self.active_tasks.pop(query.message.id, None)
        if event:
            event.set()
        if task and not task.done():
            task.cancel()
        if event or task:
            await query.edit_message_text(query.lang["dl_cancel"].format(query.from_user.mention))
        else:
            await query.answer(query.lang["dl_not_found"], show_alert=True)

    async def download(self, msg: types.Message, sent: types.Message):
        msg_id = sent.id
        event = asyncio.Event()
        self.events[msg_id] = event
        self.last_edit[msg_id] = 0
        start_time = time.time()

        media = msg.audio or msg.voice or msg.video or msg.document
        if media is None:
            return None
        file_id = getattr(media, "file_unique_id", None) or str(msg.id)
        file_ext = (getattr(media, "file_name", "") or f"media.{'mp4' if msg.video else 'mp3'}").split(".")[-1]
        file_size = getattr(media, "file_size", 0) or 0
        file_title = getattr(media, "title", None) or getattr(media, "file_name", None) or "Telegram File"
        duration = getattr(media, "duration", 0) or 0
        video = bool(getattr(media, "mime_type", "") or "").startswith("video/") or bool(msg.video)

        if config.DURATION_LIMIT and duration > config.DURATION_LIMIT:
            await sent.edit_text(sent.lang["play_duration_limit"].format(config.DURATION_LIMIT // 60))
            return await sent.stop_propagation()

        if file_size > 200 * 1024 * 1024:
            await sent.edit_text(sent.lang["dl_limit"])
            return await sent.stop_propagation()

        async def progress(current, total):
            if event.is_set():
                return
            now = time.time()
            if now - self.last_edit.get(msg_id, 0) < self.sleep:
                return
            self.last_edit[msg_id] = now
            percent = current * 100 / total if total else 0
            speed = current / (now - start_time or 1e-6)
            eta = fmt_seconds(int((total - current) / speed) if speed else 0)
            text = sent.lang["dl_progress"].format(
                utils.format_size(current),
                utils.format_size(total),
                percent,
                utils.format_size(speed),
                eta,
            )
            with suppress(Exception):
                await sent.edit_text(text, reply_markup=buttons.cancel_dl(sent.lang["cancel"]))

        try:
            file_path = str(Path(config.DOWNLOADS_DIR) / f"{file_id}.{file_ext}")
            if not os.path.exists(file_path):
                if file_id in self.active:
                    await sent.edit_text(sent.lang["dl_active"])
                    return await sent.stop_propagation()

                self.active.append(file_id)
                try:
                    task = asyncio.create_task(msg.download(file_name=file_path, progress=progress))
                    self.active_tasks[msg_id] = task
                    await task
                except asyncio.CancelledError:
                    return await sent.stop_propagation()
                finally:
                    if file_id in self.active:
                        self.active.remove(file_id)
                    self.active_tasks.pop(msg_id, None)
                await sent.edit_text(sent.lang["dl_complete"].format(round(time.time() - start_time, 2)))

            return Media(
                id=file_id,
                duration=time.strftime("%M:%S", time.gmtime(duration)),
                duration_sec=duration,
                file_path=file_path,
                message_id=sent.id,
                url=msg.link,
                title=file_title[:25],
                user=None,
                video=video,
            )
        except asyncio.CancelledError:
            return await sent.stop_propagation()
        finally:
            self.events.pop(msg_id, None)
            self.last_edit.pop(msg_id, None)

    async def process_m3u8(self, url: str, msg_id: int, video: bool) -> Media:
        return Media(
            id=str(msg_id),
            file_path=url,
            message_id=msg_id,
            url=url,
            title="M3U8 Stream",
            video=video,
        )


tg = Telegram()


# ==============================================================================
# SECTION: TELEGRAM CLIENTS
# ==============================================================================
# ==============================================================================
# TELEGRAM CLIENTS  (assistants + bot)
# ==============================================================================
class Userbot(Client):
    """
    Assistant account(s). Multi-assistant support:

        SESSION   -> assistant 1 (mandatory)
        SESSION2  -> assistant 2 (optional)
        SESSION3  -> assistant 3 (optional)
        SESSION4  -> assistant 4 (optional)
    """

    SESSION_KEYS = {
        "one": "SESSION1",
        "two": "SESSION2",
        "three": "SESSION3",
        "four": "SESSION4",
    }

    def __init__(self) -> None:
        self.clients: list[Client] = []
        for key, string_key in self.SESSION_KEYS.items():
            session = getattr(config, string_key, None)
            client = None
            if session:
                client = Client(
                    name=f"MusicXUB{key[-1]}",
                    api_id=config.API_ID,
                    api_hash=config.API_HASH,
                    session_string=session,
                    no_updates=True,
                )
            setattr(self, key, client)

    def client_for(self, num: int) -> Optional[Client]:
        return {1: self.one, 2: self.two, 3: self.three, 4: self.four}.get(num)

    async def boot_client(self, num: int, ub: Client) -> None:
        client = self.client_for(num)
        if client is None:
            return
        await client.start()
        try:
            await client.send_message(config.LOGGER_ID, f"Assistant {num} Started")
        except Exception as exc:  # noqa: BLE001
            message = f"Assistant {num} LOGGER_ID me message nahi bhej paya: {exc}"
            if config.STRICT_LOGGER:
                raise SystemExit(message) from exc
            logger.warning(message)

        client.id = ub.me.id
        client.name = ub.me.first_name
        client.username = ub.me.username
        client.mention = ub.me.mention
        self.clients.append(client)

        for chat in ("fallenx",):
            with suppress(Exception):
                await ub.join_chat(chat)
        logger.info("Assistant %s started as @%s", num, client.username)

    async def boot(self) -> None:
        for num, key in enumerate(self.SESSION_KEYS.values(), start=1):
            session = getattr(config, key, None)
            if not session:
                continue
            client = self.client_for(num)
            if client is None:
                continue
            try:
                await self.boot_client(num, client)
            except SystemExit:
                raise
            except Exception as exc:  # noqa: BLE001
                raise SystemExit(f"Assistant {num} start nahi ho paya: {exc}") from exc

        if not self.clients:
            logger.warning(
                "⚠️ Koi assistant session start nahi hua — BOT-ONLY MODE active. "
                "Voice chat (/play) ke liye SESSION env var me assistant string session daalein."
            )

    async def exit(self) -> None:
        for client in self.clients:
            with suppress(Exception):
                await client.stop()
        logger.info("Assistants stopped.")


userbot = Userbot()


class Bot(Client):
    """Main bot client (commands, logs, backups)."""

    def __init__(self) -> None:
        super().__init__(
            name="MusicXBot",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
            parse_mode=enums.ParseMode.HTML,
            max_concurrent_transmissions=7,
        )
        self.owner = config.OWNER_ID
        self.logger = config.LOGGER_ID
        self.bl_users = filters.user()
        self.sudoers = filters.user(self.owner)
        self.management_mode = config.MANAGEMENT_MODE

    # ------------------------------------------------------------------
    async def boot(self) -> None:
        await super().start()
        self.id = self.me.id
        self.name = self.me.first_name
        self.username = self.me.username
        self.mention = self.me.mention

        if self.logger:
            try:
                await self.send_message(self.logger, "Bot Started 🤖")
                member = await self.get_chat_member(self.logger, self.id)
                if member.status != enums.ChatMemberStatus.ADMINISTRATOR:
                    warning = (
                        "⚠️ Bot ko LOGGER_ID group me ADMIN promote karein "
                        "(warna /logs aur backup delivery fail hongi)."
                    )
                    if config.STRICT_LOGGER:
                        raise SystemExit(warning)
                    logger.warning(warning)
            except SystemExit:
                raise
            except Exception as exc:  # noqa: BLE001
                message = f"Bot LOGGER_ID ({self.logger}) access nahi kar paya: {exc}"
                if config.STRICT_LOGGER:
                    raise SystemExit(message) from exc
                logger.warning(message)

        logger.info("Bot started as @%s", self.username)

    async def register_commands(self) -> None:
        """Slash commands ko Telegram menu me set karta hai."""
        commands = [
            types.BotCommand("start", "Start the bot / help menu"),
            types.BotCommand("help", "Commands ki list"),
            types.BotCommand("play", "Gaana / audio play karein"),
            types.BotCommand("vplay", "Video play karein"),
            types.BotCommand("pause", "Pause"),
            types.BotCommand("resume", "Resume"),
            types.BotCommand("skip", "Next track"),
            types.BotCommand("stop", "Stop + VC se leave"),
            types.BotCommand("seek", "Aage seek karein"),
            types.BotCommand("loop", "Repeat count set karein"),
            types.BotCommand("queue", "Queue dikhayein"),
            types.BotCommand("ping", "Latency check"),
            types.BotCommand("stats", "Bot statistics"),
            types.BotCommand("lang", "Language badlein"),
            types.BotCommand("backup", "Instant database backup (owner)"),
            types.BotCommand("backups", "Backup list + status"),
            types.BotCommand("restore", "Backup se restore (owner)"),
            types.BotCommand("dbstatus", "Database engine status"),
            types.BotCommand("logs", "Log file (sudo)"),
            types.BotCommand("plugins", "Plugin manager (sudo)"),
        ]
        with suppress(Exception):
            await self.set_bot_commands(commands)

    async def exit(self) -> None:
        with suppress(Exception):
            await super().stop()
        logger.info("Bot stopped.")


app = Bot()

# ------------------------------------------------------------------------------
# Handler registration safety net
# ------------------------------------------------------------------------------
# Kurigram me `Dispatcher.add_handler()` ek async task banata hai. Ye tasks usi
# event loop par chalte hain jo import ke waqt current tha, isliye hum har handler
# ko record bhi kar lete hain. Agar loop mismatch ho jaaye (e.g. koi external
# runner `asyncio.run()` use kare) to `ensure_handlers_registered()` inhe
# synchronously dispatcher me daal deta hai — commands kabhi miss nahi hoti.
RECORDED_HANDLERS: list[tuple[Any, int]] = []
_original_add_handler = app.add_handler


def _recording_add_handler(handler, group: int = 0):
    if not any(entry is handler for entry, _ in RECORDED_HANDLERS):
        RECORDED_HANDLERS.append((handler, group))
    return _original_add_handler(handler, group)


app.add_handler = _recording_add_handler  # type: ignore[assignment]


def handler_count(client: Client = None) -> int:
    client = client or app
    return sum(len(group) for group in client.dispatcher.groups.values())


def ensure_handlers_registered(client: Client = None) -> int:
    """Handlers guarantee ke saath register karo (async task race ka safety net)."""
    client = client or app
    registered = handler_count(client)
    if registered >= len(RECORDED_HANDLERS):
        return registered

    logger.warning(
        "Handler registration race detected (registered=%d / expected=%d) — direct registration.",
        registered,
        len(RECORDED_HANDLERS),
    )
    for handler, group in RECORDED_HANDLERS:
        bucket = client.dispatcher.groups.setdefault(group, [])
        # Handler object ek hi ho to duplicate na ho
        if any(existing is handler for existing in bucket):
            continue
        bucket.append(handler)
        client.dispatcher.groups = type(client.dispatcher.groups)(
            sorted(client.dispatcher.groups.items())
        )
    return handler_count(client)


# ==============================================================================
# SECTION: VOICE CHAT ENGINE
# ==============================================================================
# ==============================================================================
# VOICE CHAT ENGINE  (PyTgCalls wrapper — multi assistant)
# ==============================================================================
class TgCall:
    """
    Har assistant client ka apna PyTgCalls instance hota hai; `db.get_assistant()`
    chat ke hisaab se sahi client deta hai. Isse multi-assistant load balancing
    hota hai (AnonXMusic architecture jaisa).
    """

    def __init__(self) -> None:
        self.clients: list[PyTgCalls] = []
        self._locks: dict[int, asyncio.Lock] = {}
        self._last_advance: dict[int, float] = {}

    # ------------------------------------------------------------------
    def _lock(self, chat_id: int) -> asyncio.Lock:
        if chat_id not in self._locks:
            self._locks[chat_id] = asyncio.Lock()
        return self._locks[chat_id]

    async def pause(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        await db.playing(chat_id, paused=True)
        return await client.pause(chat_id)

    async def resume(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        await db.playing(chat_id, paused=False)
        return await client.resume(chat_id)

    async def stop(self, chat_id: int) -> None:
        client = await db.get_assistant(chat_id)
        media = queue.get_current(chat_id)
        queue.clear(chat_id)
        await db.remove_call(chat_id)
        await db.set_loop(chat_id, 0)

        if media and media.message_id:
            with suppress(Exception):
                await app.delete_messages(chat_id=chat_id, message_ids=media.message_id, revoke=True)
                media.message_id = 0

        with suppress(Exception):
            await client.leave_call(chat_id, close=False)

    async def play_media(
        self,
        chat_id: int,
        message: Message,
        media: Union["Media", "Track"],
        seek_time: int = 0,
    ) -> None:
        client = await db.get_assistant(chat_id)
        _lang = await lang.get_lang(chat_id)
        _thumb = (
            await thumb.generate(media) if isinstance(media, Track) else config.DEFAULT_THUMB
        ) if config.THUMB_GEN else None

        if not media.file_path:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            return await self.play_next(chat_id)

        video_flags = (
            tgtypes.MediaStream.Flags.AUTO_DETECT if media.video else tgtypes.MediaStream.Flags.IGNORE
        )
        stream = tgtypes.MediaStream(
            media_path=media.file_path,
            audio_parameters=tgtypes.AudioQuality.HIGH,
            video_parameters=tgtypes.VideoQuality.HD_720p,
            audio_flags=tgtypes.MediaStream.Flags.REQUIRED,
            video_flags=video_flags,
            ffmpeg_parameters=f"-ss {seek_time}" if seek_time > 1 else None,
        )

        try:
            await client.play(
                chat_id=chat_id,
                stream=stream,
                config=tgtypes.GroupCallConfig(auto_start=False),
            )

            if not seek_time:
                media.time = 1
                await db.add_call(chat_id)
                text = _lang["play_media"].format(media.url, media.title, media.duration, media.user)
                keyboard = buttons.controls(chat_id)
                try:
                    if _thumb:
                        await message.edit_media(
                            media=InputMediaPhoto(media=_thumb, caption=text),
                            reply_markup=keyboard,
                        )
                    else:
                        await message.edit_text(text, reply_markup=keyboard)
                except (ChatSendMediaForbidden, ChatSendPhotosForbidden, MessageIdInvalid):
                    if _thumb:
                        sent = await app.send_photo(
                            chat_id=chat_id, photo=_thumb, caption=text, reply_markup=keyboard
                        )
                    else:
                        sent = await app.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
                    media.message_id = sent.id
        except FileNotFoundError:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            await self.play_next(chat_id)
        except exceptions.NoActiveGroupCall:
            await self.stop(chat_id)
            await message.edit_text(_lang["error_no_call"])
        except exceptions.NoAudioSourceFound:
            await message.edit_text(_lang["error_no_audio"])
            await self.play_next(chat_id)
        except (NgConnectionError, ConnectionNotFound, TelegramServerError):
            await self.stop(chat_id)
            await message.edit_text(_lang["error_tg_server"])
        except RTMPStreamingUnsupported:
            await self.stop(chat_id)
            await message.edit_text(_lang["error_rtmp"])
        except Exception as exc:  # noqa: BLE001
            logger.error("play_media error (%s): %s", chat_id, exc)
            await self.stop(chat_id)
            with suppress(Exception):
                await message.edit_text(f"❌ Playback error: <code>{str(exc)[:200]}</code>")

    async def replay(self, chat_id: int) -> None:
        if not await db.get_call(chat_id):
            return
        media = queue.get_current(chat_id)
        if media is None:
            return
        _lang = await lang.get_lang(chat_id)
        msg = await app.send_message(chat_id=chat_id, text=_lang["play_again"])
        media.message_id = msg.id
        await self.play_media(chat_id, msg, media)

    async def play_next(self, chat_id: int) -> None:
        async with self._lock(chat_id):
            now = time.monotonic()
            if now - self._last_advance.get(chat_id, 0) < 3:
                logger.debug("Duplicate play_next event ignore (chat %s)", chat_id)
                return
            self._last_advance[chat_id] = now

            # loop count (original AnonXMusic behaviour: N baar repeat)
            if loop := await db.get_loop(chat_id):
                await db.set_loop(chat_id, loop - 1)
                return await self.replay(chat_id)

            media = queue.get_next(chat_id)
            with suppress(Exception):
                if media and media.message_id:
                    await app.delete_messages(chat_id=chat_id, message_ids=media.message_id, revoke=True)
                    media.message_id = 0

            if not media:
                return await self.stop(chat_id)

            _lang = await lang.get_lang(chat_id)
            msg = await app.send_message(chat_id=chat_id, text=_lang["play_next"])
            if not media.file_path:
                media.file_path = await yt.download(media.id, video=media.video)
                if not media.file_path:
                    await msg.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
                    return await self.play_next(chat_id)

            media.message_id = msg.id
            await self.play_media(chat_id, msg, media)

    # ------------------------------------------------------------------
    async def ping(self) -> float:
        pings = [client.ping for client in self.clients if getattr(client, "ping", None)]
        if not pings:
            return 0.0
        return round(sum(pings) / len(pings), 2)

    def clear_chat(self, chat_id: int) -> None:
        queue.clear(chat_id)
        self._last_advance.pop(chat_id, None)

    async def active_count(self) -> int:
        return len(db.active_calls)

    async def seek(self, chat_id: int, seconds: int) -> bool:
        client = await db.get_assistant(chat_id)
        stream = None
        with suppress(Exception):
            media = queue.get_current(chat_id)
            if media and media.file_path:
                stream = tgtypes.MediaStream(
                    media_path=media.file_path,
                    audio_parameters=tgtypes.AudioQuality.HIGH,
                    video_parameters=tgtypes.VideoQuality.HD_720p,
                    audio_flags=tgtypes.MediaStream.Flags.REQUIRED,
                    video_flags=(
                        tgtypes.MediaStream.Flags.AUTO_DETECT
                        if media.video
                        else tgtypes.MediaStream.Flags.IGNORE
                    ),
                    ffmpeg_parameters=f"-ss {max(0, int(seconds))}",
                )
        if stream is None:
            return False
        await client.play(
            chat_id=chat_id, stream=stream, config=tgtypes.GroupCallConfig(auto_start=False)
        )
        return True

    # ------------------------------------------------------------------
    def decorators(self, client: PyTgCalls) -> None:
        @client.on_update()
        async def update_handler(_, update: tgtypes.Update) -> None:
            try:
                if isinstance(update, tgtypes.StreamEnded):
                    if update.stream_type == tgtypes.StreamEnded.Type.AUDIO:
                        await self.play_next(update.chat_id)
                elif isinstance(update, tgtypes.ChatUpdate):
                    if update.status in [
                        tgtypes.ChatUpdate.Status.KICKED,
                        tgtypes.ChatUpdate.Status.LEFT_GROUP,
                        tgtypes.ChatUpdate.Status.CLOSED_VOICE_CHAT,
                    ]:
                        await self.stop(update.chat_id)
            except Exception as exc:  # noqa: BLE001
                logger.error("VC update handler error: %s", exc)

    async def boot(self) -> None:
        PyTgCallsSession.notice_displayed = True
        for ub in userbot.clients:
            client = PyTgCalls(ub, cache_duration=100)
            await client.start()
            self.clients.append(client)
            self.decorators(client)
        logger.info("PyTgCalls client(s) started: %d", len(self.clients))

    async def exit(self) -> None:
        for client in self.clients:
            with suppress(Exception):
                await client.stop()


anon = TgCall()


# ==============================================================================
# SECTION: PLUGIN SYSTEM (loader + decorators)
# ==============================================================================
# ==============================================================================
# PLUGIN SYSTEM  (built-in features + external plugins/ folder auto-load)
# ==============================================================================
# Is file ke neeche saare built-in plugins (play, admin, logs, backup...) maujood
# hain. Iske alawa `plugins/` folder me koi bhi `.py` daal do — bot start hote hi
# automatic load ho jaayega (aur /plugin reload se hot reload bhi).
#
# External plugin likhne ka tarika (koi import zaroori nahi):
#
#     @command(["hello"], description="Namaste bolta hai")
#     async def hello(_, message):
#         await message.reply_text("Namaste! 👋")
# ==============================================================================

# ---- built-in plugin modules ki list (stats/help ke liye) --------------------
BUILTIN_PLUGINS: tuple[str, ...] = (
    "active",
    "auth",
    "backup",
    "blacklist",
    "broadcast",
    "callbacks",
    "database",
    "eval",
    "iquery",
    "language",
    "logs",
    "loop",
    "maintenance",
    "misc",
    "pause",
    "ping",
    "play",
    "plugins",
    "queue",
    "restart",
    "resume",
    "seek",
    "skip",
    "start",
    "stats",
    "stop",
    "sudoers",
)
ALL_MODULES: frozenset[str] = frozenset(BUILTIN_PLUGINS)

# ---- decorator registry ------------------------------------------------------
PENDING_HANDLERS: list[tuple[Any, int]] = []
COMMAND_REGISTRY: list[dict[str, Any]] = []
CURRENT_PLUGIN: Optional[str] = None

MAINTENANCE_ALLOWED = {"start", "help", "ping", "alive", "backup", "restore", "dbstatus", "maintenance", "logs"}


def _is_maintenance() -> bool:
    return bool(config.MAINTENANCE or db.data.get("maintenance") or db.data.get("settings", {}).get("maintenance"))


def drain_pending() -> list[tuple[Any, int]]:
    drained = list(PENDING_HANDLERS)
    PENDING_HANDLERS.clear()
    return drained


def drop_commands_of(plugin: str) -> None:
    COMMAND_REGISTRY[:] = [entry for entry in COMMAND_REGISTRY if entry.get("plugin") != plugin]


async def _deny(client, message, text: str) -> None:
    with suppress(Exception):
        await message.reply_text(text)
        return
    with suppress(Exception):
        await client.send_message(message.chat.id, text)


async def _permission_ok(client, message, *, owner: bool, sudo: bool, admin: bool) -> tuple[bool, str]:
    user_id = getattr(getattr(message, "from_user", None), "id", 0) or 0
    chat = getattr(message, "chat", None)
    chat_id = getattr(chat, "id", 0)

    if _is_maintenance() and not sudo_check(user_id):
        return False, "🛠️ <b>Bot maintenance mode me hai.</b> Thodi der baad try karein."

    if owner:
        if user_id == config.OWNER_ID:
            return True, ""
        return False, "⛔ Ye command sirf <b>bot owner</b> ke liye hai."

    if sudo:
        if sudo_check(user_id):
            return True, ""
        return False, "⛔ Ye command sirf <b>sudo users</b> ke liye hai."

    if admin:
        if await is_admin(chat_id, user_id):
            return True, ""
        return False, "⛔ Ye command group admins ke liye hai."

    return True, ""


def sudo_check(user_id: int) -> bool:
    return bool(user_id) and user_id in app.sudoers


def _wrap_filter(extra_filter, group_only: bool, private_only: bool):
    filters_list = [extra_filter] if extra_filter is not None else []
    if group_only:
        filters_list.append(filters.group)
    if private_only:
        filters_list.append(filters.private)
    if not filters_list:
        return None
    combined = filters_list[0]
    for item in filters_list[1:]:
        combined = combined & item
    return combined


def command(
    names: Union[str, list[str]],
    *,
    owner: bool = False,
    sudo: bool = False,
    admin: bool = False,
    group_only: bool = False,
    private_only: bool = False,
    group: int = 0,
    description: str = "",
    usage: str = "",
    category: Optional[str] = None,
):
    """External/built-in plugins ke liye command decorator (permission aware)."""
    command_names = [names] if isinstance(names, str) else list(names)
    primary = command_names[0]

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(client, message):
            allowed, denial = await _permission_ok(client, message, owner=owner, sudo=sudo, admin=admin)
            if not allowed:
                if denial:
                    await _deny(client, message, denial)
                return None
            try:
                return await func(client, message)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Command /%s error: %s", primary, exc)
                await _deny(client, message, f"❌ <b>Error:</b> <code>{escape(str(exc))[:300]}</code>")
                return None

        handler = MessageHandler(wrapper, _wrap_filter(filters.command(command_names), group_only, private_only))
        PENDING_HANDLERS.append((handler, group))

        COMMAND_REGISTRY.append(
            {
                "names": command_names,
                "primary": primary,
                "description": description or (func.__doc__ or "").strip().split("\n")[0],
                "usage": usage or f"/{primary}",
                "category": category or (CURRENT_PLUGIN or "misc").replace("_", " ").title(),
                "plugin": CURRENT_PLUGIN,
                "level": "owner" if owner else ("sudo" if sudo else ("admin" if admin else "user")),
            }
        )
        return wrapper

    return decorator


def on_message(extra_filter=None, *, group: int = 0, group_only: bool = False, private_only: bool = False):
    """Generic message handler decorator (additional filters ke saath)."""

    def decorator(func: Callable) -> Callable:
        handler = MessageHandler(func, _wrap_filter(extra_filter, group_only, private_only))
        PENDING_HANDLERS.append((handler, group))
        return func

    return decorator


def callback(pattern: str, *, group: int = 0):
    """Callback query handler decorator (regex pattern)."""

    def decorator(func: Callable) -> Callable:
        handler = CallbackQueryHandler(func, filters.regex(pattern))
        PENDING_HANDLERS.append((handler, group))
        return func

    return decorator


class PluginManager:
    """`plugins/` folder ke external plugins ko manage karta hai."""

    API: dict[str, Any] = {}

    def __init__(self, client: Client) -> None:
        self.client = client
        self.plugins_dir = Path(config.PLUGINS_DIR)
        self.handlers: dict[str, list[tuple[Any, int]]] = {}
        self.modules: dict[str, Any] = {}
        self.errors: dict[str, str] = {}
        self.disabled: set[str] = set()
        self.ApiNamespace = {
            "app": app,
            "client": app,
            "bot": app,
            "db": db,
            "config": config,
            "logger": logger,
            "lang": lang,
            "queue": queue,
            "yt": yt,
            "tg": tg,
            "anon": anon,
            "thumb": thumb,
            "userbot": userbot,
            "buttons": buttons,
            "utils": utils,
            "backup": backup_manager,
            "filters": filters,
            "types": types,
            "enums": enums,
            "errors": errors,
            "command": command,
            "on_message": on_message,
            "callback": callback,
            "__version__": __version__,
        }

    # ------------------------------------------------------------------
    def discover(self) -> list[Path]:
        if not self.plugins_dir.exists():
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
        return [
            path
            for path in sorted(self.plugins_dir.glob("*.py"))
            if not path.name.startswith(("_", "."))
        ]

    def load_all(self) -> dict[str, int]:
        loaded: dict[str, int] = {}
        for path in self.discover():
            name = path.stem
            if name in self.disabled:
                continue
            count = self.load_plugin(name, path)
            if count is not None:
                loaded[name] = count
        logger.info("🧩 External plugins: %d loaded%s", len(loaded), f", {len(self.errors)} failed" if self.errors else "")
        return loaded

    def load_plugin(self, name: str, path: Optional[Path] = None) -> Optional[int]:
        global CURRENT_PLUGIN
        path = path or (self.plugins_dir / f"{name}.py")
        if not path.exists():
            self.errors[name] = f"file nahi mili ({path})"
            return None

        module_name = f"musicxbot_plugin_{name}"
        CURRENT_PLUGIN = name
        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                raise ImportError(f"module spec ban nahi paya ({path})")
            module = importlib.util.module_from_spec(spec)
            module.__dict__.update({key: value for key, value in self.ApiNamespace.items() if not key.startswith("__")})
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        except Exception as exc:  # noqa: BLE001
            CURRENT_PLUGIN = None
            PENDING_HANDLERS.clear()
            self.errors[name] = f"{type(exc).__name__}: {exc}"
            logger.error("❌ Plugin '%s' import fail:\n%s", name, traceback.format_exc())
            return None
        finally:
            CURRENT_PLUGIN = None

        registered: list[tuple[Any, int]] = []
        for handler, group in drain_pending():
            with suppress(Exception):
                registered.append(self.client.add_handler(handler, group))

        self.handlers[name] = registered
        self.modules[name] = module
        self.errors.pop(name, None)

        setup = getattr(module, "setup", None)
        if callable(setup):
            try:
                result = setup(self.client)
                if hasattr(result, "__await__"):
                    with suppress(RuntimeError):
                        asyncio.get_running_loop().create_task(result)
            except Exception as exc:  # noqa: BLE001
                logger.error("Plugin '%s' setup() fail: %s", name, exc)

        logger.info("✅ External plugin '%s' loaded (%d handlers)", name, len(registered))
        return len(registered)

    def unload_plugin(self, name: str) -> bool:
        handlers = self.handlers.pop(name, [])
        for handler, group in handlers:
            with suppress(Exception):
                self.client.remove_handler(handler, group)
        drop_commands_of(name)
        self.modules.pop(name, None)
        sys.modules.pop(f"musicxbot_plugin_{name}", None)
        return bool(handlers)

    def reload_plugin(self, name: str) -> tuple[bool, str]:
        if not (self.plugins_dir / f"{name}.py").exists():
            return False, f"Plugin <code>{name}</code> ka file nahi mila."
        self.unload_plugin(name)
        self.disabled.discard(name)
        count = self.load_plugin(name)
        if count is None:
            return False, f"Reload fail: <code>{html_escape(self.errors.get(name, 'unknown'))}</code>"
        return True, f"♻️ Plugin <code>{name}</code> reload ho gaya ({count} handlers)."

    def disable_plugin(self, name: str) -> tuple[bool, str]:
        self.disabled.add(name)
        removed = self.unload_plugin(name)
        if name not in self.disabled:
            return False, f"Plugin <code>{name}</code> mila nahi."
        return True, f"⏸️ Plugin <code>{name}</code> disable kar diya." + ("" if removed else " (active nahi tha)")

    def enable_plugin(self, name: str) -> tuple[bool, str]:
        self.disabled.discard(name)
        if name in self.handlers:
            return True, f"Plugin <code>{name}</code> pehle se active hai."
        count = self.load_plugin(name)
        if count is None:
            return False, f"Enable fail: <code>{html_escape(self.errors.get(name, 'unknown'))}</code>"
        return True, f"▶️ Plugin <code>{name}</code> enable ho gaya ({count} handlers)."

    # ------------------------------------------------------------------
    def list_plugins(self) -> list[dict]:
        items: list[dict] = []
        for path in self.discover():
            name = path.stem
            if name in self.disabled:
                status = "disabled"
            elif name in self.errors:
                status = "error"
            elif name in self.handlers:
                status = "active"
            else:
                status = "not loaded"
            items.append(
                {
                    "name": name,
                    "status": status,
                    "handlers": len(self.handlers.get(name, [])),
                    "error": self.errors.get(name, ""),
                    "size": path.stat().st_size if path.exists() else 0,
                }
            )
        return items

    def status_text(self) -> str:
        items = self.list_plugins()
        active = sum(1 for item in items if item["status"] == "active")
        lines = [
            "🧩 <b>Plugin Manager</b>",
            "",
            f"• <b>Built-in plugins:</b> <code>{len(BUILTIN_PLUGINS)}</code>",
            f"• <b>External folder:</b> <code>{self.plugins_dir}</code>",
            f"• <b>External files:</b> <code>{len(items)}</code> | <code>active: {active}</code>",
            "",
        ]
        if items:
            lines.append("<b>External plugins:</b>")
            for item in items:
                icon = {"active": "✅", "disabled": "⏸️", "error": "❌", "not loaded": "⚠️"}.get(item["status"], "•")
                lines.append(f"{icon} <code>{item['name']}</code> — {item['handlers']} handler(s)")
                if item["error"]:
                    lines.append(f"     └ <i>{html_escape(item['error'][:120])}</i>")
        else:
            lines.append("<i>Folder khaali hai — koi bhi .py daalein aur /plugin reload karein.</i>")
        lines.append("")
        lines.append("<b>Built-in:</b> " + ", ".join(f"<code>{name}</code>" for name in BUILTIN_PLUGINS))
        return "\n".join(lines)


plugin_manager = PluginManager(app)


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: start
# ==============================================================================
@app.on_message(filters.command(["help"]) & filters.private & ~app.bl_users)
@lang.language()
async def _help(_, m: types.Message):
    await m.reply_text(
        text=m.lang["help_menu"],
        reply_markup=buttons.help_markup(m.lang),
    )


@app.on_message(filters.command(["start"]))
@lang.language()
async def start(_, message: types.Message):
    if message.from_user.id in app.bl_users and message.from_user.id not in db.notified:
        return await message.reply_text(message.lang["bl_user_notify"])

    if len(message.command) > 1 and message.command[1] == "help":
        return await _help(_, message)

    private = message.chat.type == enums.ChatType.PRIVATE
    _text = (
        message.lang["start_pm"].format(message.from_user.first_name, app.name)
        if private
        else message.lang["start_gp"].format(app.name)
    )

    key = buttons.start_key(message.lang, private)
    await message.reply_photo(
        photo=branding_image("start"),
        caption=_text,
        reply_markup=key,
    )

    if private:
        if await db.is_user(message.from_user.id):
            return
        await utils.send_log(message)
        await db.add_user(message.from_user.id)
    else:
        if await db.is_chat(message.chat.id):
            return
        await utils.send_log(message, True)
        await db.add_chat(message.chat.id)


@app.on_message(filters.command(["playmode", "settings"]) & filters.group & ~app.bl_users)
@lang.language()
async def settings(_, message: types.Message):
    admin_only = await db.get_play_mode(message.chat.id)
    cmd_delete = await db.get_cmd_delete(message.chat.id)
    _language = await db.get_lang(message.chat.id)
    # Button par True/False ki jagah readable label + admin panel ka link
    is_admin = message.from_user.id in app.sudoers or message.from_user.id in await db.get_admins(
        message.chat.id
    )
    await message.reply_text(
        text=message.lang["start_settings"].format(message.chat.title),
        reply_markup=buttons.settings_markup(
            message.lang,
            mode_label(admin_only),
            toggle_label(cmd_delete),
            _language,
            message.chat.id,
            admin_panel=is_admin,
        ),
    )


@app.on_message(filters.new_chat_members, group=7)
@lang.language()
async def _new_member(_, message: types.Message):
    if message.chat.type != enums.ChatType.SUPERGROUP:
        return await message.chat.leave()

    await asyncio.sleep(3)
    for member in message.new_chat_members:
        if member.id == app.id:
            if await db.is_chat(message.chat.id):
                return
            await utils.send_log(message, True)
            await db.add_chat(message.chat.id)


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: play
# ==============================================================================
from pathlib import Path


def playlist_to_queue(chat_id: int, tracks: list) -> str:
    text = "<blockquote expandable>"
    for track in tracks:
        pos = queue.add(chat_id, track)
        text += f"<b>{pos}.</b> {track.title}\n"
    text = text[:1948] + "</blockquote>"
    return text

@app.on_message(
    filters.command(["play", "playforce", "vplay", "vplayforce"])
    & filters.group
    & ~app.bl_users
)
@lang.language()
@checkUB
async def play_hndlr(
    _,
    m: types.Message,
    force: bool = False,
    m3u8: bool = False,
    video: bool = False,
    url: str = None,
) -> None:
    sent = await m.reply_text(m.lang["play_searching"])
    file = None
    mention = m.from_user.mention
    media = tg.get_media(m.reply_to_message) if m.reply_to_message else None
    tracks = []

    if media:
        setattr(sent, "lang", m.lang)
        file = await tg.download(m.reply_to_message, sent)

    elif m3u8:
        file = await tg.process_m3u8(url, sent.id, video)

    elif url:
        if "playlist" in url:
            await sent.edit_text(m.lang["playlist_fetch"])
            tracks = await yt.playlist(
                config.PLAYLIST_LIMIT, mention, url, video
            )

            if not tracks:
                return await sent.edit_text(m.lang["playlist_error"])

            file = tracks[0]
            tracks.remove(file)
            file.message_id = sent.id
        else:
            file = await yt.search(url, sent.id, video=video)

        if not file:
            return await sent.edit_text(
                m.lang["play_not_found"].format(config.SUPPORT_CHAT)
            )

    elif len(m.command) >= 2:
        query = " ".join(m.command[1:])
        file = await yt.search(query, sent.id, video=video)
        if not file:
            return await sent.edit_text(
                m.lang["play_not_found"].format(config.SUPPORT_CHAT)
            )

    if not file:
        return await sent.edit_text(m.lang["play_usage"])

    if file.duration_sec > config.DURATION_LIMIT:
        return await sent.edit_text(
            m.lang["play_duration_limit"].format(config.DURATION_LIMIT // 60)
        )

    if await db.is_logger():
        await utils.play_log(m, sent.link, file.title, file.duration)

    file.user = mention
    if force:
        queue.force_add(m.chat.id, file)
    else:
        position = queue.add(m.chat.id, file)

        if position != 0 or await db.get_call(m.chat.id):
            await sent.edit_text(
                m.lang["play_queued"].format(
                    position,
                    file.url,
                    file.title,
                    file.duration,
                    m.from_user.mention,
                ),
                reply_markup=buttons.play_queued(
                    m.chat.id, file.id, m.lang["play_now"]
                ),
            )
            if tracks:
                added = playlist_to_queue(m.chat.id, tracks)
                await app.send_message(
                    chat_id=m.chat.id,
                    text=m.lang["playlist_queued"].format(len(tracks)) + added,
                )
            return

    if not file.file_path:
        fname = f"{config.DOWNLOADS_DIR}/{file.id}.{'mp4' if video else 'webm'}"
        if Path(fname).exists():
            file.file_path = fname
        else:
            await sent.edit_text(m.lang["play_downloading"])
            file.file_path = await yt.download(file.id, video=video)

    await anon.play_media(chat_id=m.chat.id, message=sent, media=file)
    if not tracks:
        return
    added = playlist_to_queue(m.chat.id, tracks)
    await app.send_message(
        chat_id=m.chat.id,
        text=m.lang["playlist_queued"].format(len(tracks)) + added,
    )


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: queue
# ==============================================================================
@app.on_message(filters.command(["queue", "playing"]) & filters.group & ~app.bl_users)
@lang.language()
async def _queue_func(_, m: types.Message):
    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    _reply = await m.reply_text(m.lang["queue_fetching"])
    _queue = queue.get_queue(m.chat.id)
    _media = _queue[0]
    _thumb = (
        await thumb.generate(_media)
        if isinstance(_media, Track)
        else config.DEFAULT_THUMB
    ) if config.THUMB_GEN else None
    _text = m.lang["queue_curr"].format(
        _media.url,
        _media.title[:50],
        _media.duration,
        _media.user,
    )
    _queue.pop(0)

    if _queue:
        _text += "<blockquote expandable>"
        for i, media in enumerate(_queue, start=1):
            if i == 15:
                break
            _text += m.lang["queue_item"].format(
                i + 1, media.title, media.duration
            )
        _text += "</blockquote>"

    _playing = await db.playing(m.chat.id)
    _buttons = buttons.queue_markup(
            m.chat.id,
            m.lang["playing"] if _playing else m.lang["paused"],
            _playing,
        )
    if thumb:
        await _reply.edit_media(
            media=types.InputMediaPhoto(
                media=_thumb,
                caption=_text,
            ),
            reply_markup=_buttons,
        )
    else:
        await _reply.edit_text(
            text=_text,
            reply_markup=_buttons,
        )


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: pause
# ==============================================================================
@app.on_message(filters.command(["pause"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _pause(_, m: types.Message):
    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    if not await db.playing(m.chat.id):
        return await m.reply_text(m.lang["play_already_paused"])

    await anon.pause(m.chat.id)
    await m.reply_text(
        text=m.lang["play_paused"].format(m.from_user.mention),
        reply_markup=buttons.controls(m.chat.id),
    )


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: resume
# ==============================================================================
@app.on_message(filters.command(["resume"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _resume(_, m: types.Message):
    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    if await db.playing(m.chat.id):
        return await m.reply_text(m.lang["play_not_paused"])

    await anon.resume(m.chat.id)
    await m.reply_text(
        text=m.lang["play_resumed"].format(m.from_user.mention),
        reply_markup=buttons.controls(m.chat.id),
    )


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: skip
# ==============================================================================
@app.on_message(filters.command(["skip", "next"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _skip(_, m: types.Message):
    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    await anon.play_next(m.chat.id)
    await m.reply_text(m.lang["play_skipped"].format(m.from_user.mention))


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: stop
# ==============================================================================
@app.on_message(filters.command(["end", "stop"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _stop(_, m: types.Message):
    if len(m.command) > 1:
        return

    call = await db.get_call(m.chat.id)
    await anon.stop(m.chat.id)
    if not call:
        return await m.reply_text(m.lang["not_playing"])

    await m.reply_text(m.lang["play_stopped"].format(m.from_user.mention))


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: loop
# ==============================================================================
@app.on_message(filters.command(["loop"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _loop(_, m: types.Message):
    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    chat_id = m.chat.id
    if len(m.command) < 2:
        if count := await db.get_loop(chat_id):
            return await m.reply_text(m.lang["loop_count"].format(count))
        else:
            return await m.reply_text(m.lang["loop_usage"])

    disable = m.command[1].lower() in ["off", "disable"]
    if not m.command[1].isdigit() and not disable:
        return await m.reply_text(m.lang["loop_usage"])

    loop = int(m.command[1]) if not disable else 0
    if loop < 1: loop = 0
    elif loop > 10: loop = 10

    await db.set_loop(m.chat.id, loop)
    if loop == 0:
        return await m.reply_text(m.lang["loop_off"])
    await m.reply_text(m.lang["loop_set"].format(loop))


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: seek
# ==============================================================================
@app.on_message(filters.command(["seek", "seekback"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _seek(_, m: types.Message):
    if len(m.command) < 2:
        return await m.reply_text(m.lang["play_seek_usage"].format(m.command[0]))

    try:
        to_seek = int(m.command[1])
    except ValueError:
        return await m.reply_text(m.lang["play_seek_usage"].format(m.command[0]))
    if to_seek < 10:
        return await m.reply_text(m.lang["play_seek_min"])

    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    if not await db.playing(m.chat.id):
        return await m.reply_text(m.lang["play_already_paused"])

    media = queue.get_current(m.chat.id)
    if not media.duration_sec:
        return await m.reply_text(m.lang["play_seek_no_dur"])

    sent = await m.reply_text(m.lang["play_seeking"])
    if m.command[0] == "seekback":
        stype = m.lang["backward"]
        start_from = media.time - to_seek
        if start_from < 1:
            start_from = 1
    else:
        stype = m.lang["forward"]
        start_from = media.time + to_seek
        if start_from + 10 > media.duration_sec:
            start_from = media.duration_sec - 5

    await anon.play_media(m.chat.id, sent, media, start_from)
    media.time = start_from
    await sent.edit_text(
        m.lang["play_seeked"].format(stype, start_from, m.from_user.mention)
    )


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: active
# ==============================================================================
@app.on_message(filters.command(["ac", "activevc"]) & app.sudoers)
@lang.language()
async def _activevc(_, m: types.Message):
    if not db.active_calls:
        return await m.reply_text(m.lang["vc_empty"])

    if m.command[0] == "ac":
        return await m.reply_text(m.lang["vc_count"].format(len(db.active_calls)))

    sent = await m.reply_text(m.lang["vc_fetching"])
    text = ""

    for i, chat in enumerate(db.active_calls):
        playing = queue.get_current(chat)
        text += f"\n{i+1}. <code>{chat}</code>\n    ➜ {playing.title[:25]}"

    if len(text) < 4000:
        return await sent.edit_text(m.lang["vc_list"] + text)

    with open("activevc.txt", "w") as f:
        f.write(text)
    f.close()
    await sent.edit_media(
        media=types.InputMediaDocument(
            media="activevc.txt",
            caption=m.lang["vc_list"],
        )
    )
    os.remove("activevc.txt")


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: auth
# ==============================================================================
@app.on_message(filters.command(["auth", "unauth"]) & filters.group & ~app.bl_users)
@lang.language()
@admin_check
async def _auth(_, m: types.Message):
    user = await utils.extract_user(m)
    if not user:
        return await m.reply_text(m.lang["user_not_found"])

    if m.command[0] == "auth":
        if await is_admin(m.chat.id, user.id):
            return await m.reply_text(m.lang["auth_is_admin"])

        await db.add_auth(m.chat.id, user.id)
        await m.reply_text(m.lang["auth_added"].format(user.mention))
    else:
        await db.rm_auth(m.chat.id, user.id)
        await m.reply_text(m.lang["auth_removed"].format(user.mention))


@app.on_message(filters.command(["authlist"]) & filters.group & ~app.bl_users)
@lang.language()
@admin_check
async def _authlist(_, m: types.Message):
    auth = await db._get_auth(m.chat.id)
    if not auth:
        return await m.reply_text(m.lang["auth_empty"])

    auth_txt = m.lang["auth_list"].format(m.chat.title)
    for i, user in enumerate(auth, start=1):
        auth_txt += f"\n{i}. <a href=tg://user?id={user}>{user}</a>"
    await m.reply_text(auth_txt)


rel_hist = {}

@app.on_message(filters.command(["admincache", "reload"]) & filters.group & ~app.bl_users)
@lang.language()
async def _admincache(_, m: types.Message):
    if m.from_user.id in rel_hist:
        if time.time() < rel_hist[m.from_user.id]:
            return await m.reply_text(m.lang["admin_cache_wait"])

    rel_hist[m.from_user.id] = time.time() + 600
    sent = await m.reply_text(m.lang["admin_cache_reloading"])
    await db.get_admins(m.chat.id, reload=True)
    await sent.edit_text(m.lang["admin_cache_reloaded"])


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: blacklist
# ==============================================================================
@app.on_message(filters.command(["blacklist", "unblacklist", "whitelist"]) & app.sudoers)
@lang.language()
async def _blacklist(_, m: types.Message):
    if len(m.command) < 2:
        return await m.reply_text(m.lang["bl_usage"].format(m.command[0]))

    try:
        chat_id = m.command[1]
        if not str(chat_id).startswith("@"):
            chat_id = int(chat_id)
        else:
            chat_id = (await app.get_chat(chat_id)).id
    except Exception:
        return await m.reply_text(m.lang["bl_invalid"])

    if m.command[0] == "blacklist":
        if chat_id in db.blacklisted or chat_id in app.bl_users:
            return await m.reply_text(m.lang["bl_already"])
        if not str(chat_id).startswith("-100"):
            app.bl_users.add(chat_id)
        await db.add_blacklist(chat_id)
        await m.reply_text(m.lang["bl_added"])
    else:
        if chat_id not in db.blacklisted and chat_id not in app.bl_users:
            return await m.reply_text(m.lang["bl_not"])
        if not str(chat_id).startswith("-100"):
            app.bl_users.discard(chat_id)
        await db.del_blacklist(chat_id)
        await m.reply_text(m.lang["bl_removed"])


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: broadcast
# ==============================================================================
broadcasting = asyncio.Lock()

@app.on_message(filters.command(["broadcast"]) & app.sudoers)
@lang.language()
async def _broadcast(_, message: types.Message):
    if not message.reply_to_message:
        return await message.reply_text(message.lang["gcast_usage"])

    if broadcasting.locked():
        return await message.reply_text(message.lang["gcast_active"])

    msg = message.reply_to_message
    copy = "-copy" in message.command
    count, ucount = 0, 0
    groups, users = set(), set()
    sent = await message.reply_text(message.lang["gcast_start"])

    if "-nochat" not in message.command:
        groups = set(await db.get_chats())
    if "-user" in message.command:
        users = set(await db.get_users())

    chats = list(groups | users)
    failed = None

    async with broadcasting:
        for chat in chats:
            try:
                (
                    await msg.copy(chat, reply_markup=msg.reply_markup)
                    if copy
                    else await msg.forward(chat)
                )
                if chat in groups:
                    count += 1
                else:
                    ucount += 1
                await asyncio.sleep(0.2)
            except errors.FloodWait as fw:
                await asyncio.sleep(fw.value + 10)
            except Exception as ex:
                if not failed:
                    failed = open("errors.txt", "w")
                failed.write(f"{chat} - {ex}\n")
                continue

    text = message.lang["gcast_end"].format(count, ucount)
    if failed:
        failed.close()
        await message.reply_document(
            document="errors.txt",
            caption=text,
        )
        try: os.remove("errors.txt")
        except Exception: pass

    await sent.edit_text(text)


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: callbacks
# ==============================================================================
@app.on_callback_query(filters.regex("cancel_dl") & ~app.bl_users)
@lang.language()
async def cancel_dl(_, query: types.CallbackQuery):
    await query.answer()
    await tg.cancel(query)


@app.on_callback_query(filters.regex("controls") & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _controls(_, query: types.CallbackQuery):
    args = query.data.split()
    action, chat_id = args[1], int(args[2])
    qaction = len(args) == 4
    user = query.from_user.mention

    if not await db.get_call(chat_id):
        try:
            return await query.answer(query.lang["not_playing"], show_alert=True)
        except errors.QueryIdInvalid:
            try:
                await query.message.delete()
            except Exception:
                pass
            return

    if action == "status":
        return await query.answer()
    await query.answer(query.lang["processing"], show_alert=True)

    if action == "pause":
        if not await db.playing(chat_id):
            return await query.answer(
                query.lang["play_already_paused"], show_alert=True
            )
        await anon.pause(chat_id)
        if qaction:
            return await query.edit_message_reply_markup(
                reply_markup=buttons.queue_markup(chat_id, query.lang["paused"], False)
            )
        status = query.lang["paused"]
        reply = query.lang["play_paused"].format(user)

    elif action == "resume":
        if await db.playing(chat_id):
            return await query.answer(query.lang["play_not_paused"], show_alert=True)
        await anon.resume(chat_id)
        if qaction:
            return await query.edit_message_reply_markup(
                reply_markup=buttons.queue_markup(chat_id, query.lang["playing"], True)
            )
        reply = query.lang["play_resumed"].format(user)

    elif action == "skip":
        await anon.play_next(chat_id)
        status = query.lang["skipped"]
        reply = query.lang["play_skipped"].format(user)

    elif action == "force":
        pos, media = queue.check_item(chat_id, args[3])
        if not media or pos == -1:
            return await query.edit_message_text(query.lang["play_expired"])

        m_id = queue.get_current(chat_id).message_id
        queue.force_add(chat_id, media, remove=pos)
        try:
            await app.delete_messages(
                chat_id=chat_id, message_ids=[m_id, media.message_id], revoke=True
            )
            media.message_id = None
        except Exception:
            pass

        msg = await app.send_message(chat_id=chat_id, text=query.lang["play_next"])
        if not media.file_path:
            media.file_path = await yt.download(media.id, video=media.video)
        media.message_id = msg.id
        return await anon.play_media(chat_id, msg, media)

    elif action == "replay":
        media = queue.get_current(chat_id)
        media.user = user
        await anon.replay(chat_id)
        status = query.lang["replayed"]
        reply = query.lang["play_replayed"].format(user)

    elif action == "stop":
        await anon.stop(chat_id)
        status = query.lang["stopped"]
        reply = query.lang["play_stopped"].format(user)

    try:
        if action in ["skip", "replay", "stop"]:
            await query.message.reply_text(reply, )
            await query.message.delete()
        else:
            mtext = re.sub(
                r"\n\n<blockquote>.*?</blockquote>",
                "",
                query.message.caption.html or query.message.text.html,
                flags=re.DOTALL,
            )
            keyboard = buttons.controls(
                chat_id, status=status if action != "resume" else None
            )
        await query.edit_message_text(
            f"{mtext}\n\n<blockquote>{reply}</blockquote>", reply_markup=keyboard
        )
    except Exception:
        pass


@app.on_callback_query(filters.regex("help") & ~app.bl_users)
@lang.language()
async def _help_query(_, query: types.CallbackQuery):
    data = query.data.split()
    if len(data) == 1:
        return await query.answer(url=f"https://t.me/{app.username}?start=help")

    if data[1] == "back":
        return await query.edit_message_text(
            text=query.lang["help_menu"], reply_markup=buttons.help_markup(query.lang)
        )
    elif data[1] == "close":
        try:
            await query.message.delete()
            return await query.message.reply_to_message.delete()
        except Exception:
            return

    await query.edit_message_text(
        text=query.lang[f"help_{data[1]}"],
        reply_markup=buttons.help_markup(query.lang, True),
    )


@app.on_callback_query(filters.regex("settings") & ~app.bl_users)
@lang.language()
@admin_check
async def _settings_cb(_, query: types.CallbackQuery):
    cmd = query.data.split()
    if len(cmd) == 1:
        return await query.answer()
    await query.answer(query.lang["processing"], show_alert=True)

    chat_id = query.message.chat.id
    _admin = await db.get_play_mode(chat_id)
    _delete = await db.get_cmd_delete(chat_id)
    _language = await db.get_lang(chat_id)

    if cmd[1] == "delete":
        _delete = not _delete
        await db.set_cmd_delete(chat_id, _delete)
    elif cmd[1] == "play":
        await db.set_play_mode(chat_id, _admin)
        _admin = not _admin
    # Har toggle turant save (force flush) — data loss zero
    with suppress(Exception):
        await db.flush(force=True)
    await query.edit_message_reply_markup(
        reply_markup=buttons.settings_markup(
            query.lang,
            mode_label(_admin),
            toggle_label(_delete),
            _language,
            chat_id,
            admin_panel=True,  # yahan sirf admins/sudo pahunchte hain (admin_check)
        )
    )


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: eval
# ==============================================================================
@app.on_message(filters.command(["eval", "exec"]) & filters.user(app.owner))
@app.on_edited_message(filters.command(["eval", "exec"]) & filters.user(app.owner))
@lang.language()
async def eval_handler(_, message: types.Message):
    if len(message.command) < 2:
        return await message.reply_text(message.lang["eval_inp"])

    code = message.text.split(None, 1)[1]
    out_buf = io.StringIO()

    async def _eval_code() -> Tuple[str, Optional[str]]:
        async def send(*args: Any, **kwargs: Any) -> types.Message:
            return await message.reply_text(*args, **kwargs)

        def _print(*args: Any, **kwargs: Any) -> None:
            kwargs.setdefault("file", out_buf)
            print(*args, **kwargs)

        eval_vars = {
            "m": message,
            "r": message.reply_to_message,
            "chat": message.chat,
            "user": message.from_user,
            "app": app,
            "anon": anon,
            "db": db,
            "client": app,
            "ub": userbot,
            "ikb": types.InlineKeyboardButton,
            "ikm": types.InlineKeyboardMarkup,
            "send": send,
            "config": config,
            "print": _print,
            "os": os,
            "re": re,
            "sys": sys,
            "tb": traceback,
        }

        try:
            result = await meval(code, globals(), **eval_vars)
            return "", result
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            snippet_tb = next(
                (i for i, f in enumerate(tb) if f.filename == "<string>"), -1
            )
            formatted_tb = format_exception(
                e, tb[snippet_tb:] if snippet_tb != -1 else tb
            )
            return message.lang["eval_error"], formatted_tb

    _, result = await _eval_code()

    if result is not None or not out_buf.getvalue():
        print(result, file=out_buf)

    output = out_buf.getvalue().strip()
    response = message.lang["eval_out"].format(escape(output))

    if len(response) > 4096:
        with io.BytesIO(output.encode()) as out_file:
            out_file.name = f"{uuid.uuid4().hex[:8].lower()}.txt"
            return await message.reply_document(
                document=out_file, disable_notification=True
            )

    await message.reply_text(response)


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: iquery
# ==============================================================================
@app.on_inline_query(~app.bl_users)
async def inline_query_handler(_, query: types.InlineQuery):
    text = query.query.strip().lower()
    if not text:
        return

    try:
        search = VideosSearch(text, limit=15)
        results = (await search.next()).get("result", [])

        answers = []
        for video in results:
            title = video.get("title", "Unknown Title").title()
            duration = video.get("duration", "N/A")
            views = video.get("viewCount", {}).get("short", "N/A")
            thumbnail = video.get("thumbnails", [{}])[0].get("url", "").split("?")[0]
            channel = video.get("channel", {}).get("name", "Unknown Channel")
            channellink = video.get("channel", {}).get("link", "https://youtube.com")
            link = video.get("link", "https://youtube.com")
            published = video.get("publishedTime", "N/A")

            description = f"{views} | {duration} | {channel} | {published}"
            caption = (
                f"<b>Title:</b> <a href='{link}'>{title[:250]}</a>\n\n"
                f"<b>Duration:</b> {duration}\n"
                f"<b>Views:</b> <code>{views}</code>\n"
                f"<b>Channel:</b> <a href='{channellink}'>{channel}</a>\n"
                f"<b>Published:</b> {published}\n\n"
                f"<u><i>Fetched by {app.name}</i></u>"
            )

            answers.append(
                types.InlineQueryResultPhoto(
                    photo_url=thumbnail,
                    title=title,
                    description=description,
                    caption=caption,
                    reply_markup=buttons.yt_key(link),
                )
            )

        if answers:
            await app.answer_inline_query(query.id, results=answers, cache_time=5)
    except Exception:
        pass


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: language
# ==============================================================================
@app.on_message(filters.command(["lang", "language"]) & ~app.bl_users)
@lang.language()
async def _lang(_, m: types.Message):
    current = await db.get_lang(m.chat.id)
    keyboard = buttons.lang_markup(current)
    await m.reply_text(m.lang["lang_choose"], reply_markup=keyboard)


@app.on_callback_query(filters.regex(r"^lang(?:_change|uage)") & ~app.bl_users)
@lang.language()
@admin_check
async def _lang_cb(_, query: types.CallbackQuery):
    data = query.data.split()
    if data[0] == "language":
        current = await db.get_lang(query.message.chat.id)
        keyboard = buttons.lang_markup(current)
        return await query.edit_message_text(
            query.lang["lang_choose"], reply_markup=keyboard
        )

    _lang = data[1]
    current = await db.get_lang(query.message.chat.id)
    if current == _lang:
        return await query.answer(
            query.lang["lang_same"].format(current), show_alert=True
        )

    await query.answer(query.lang["lang_change"].format(_lang), show_alert=True)
    await db.set_lang(query.message.chat.id, _lang)
    await query.edit_message_text(query.lang["lang_changed"].format(_lang))


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: ping
# ==============================================================================
@app.on_message(filters.command(["alive", "ping"]) & ~app.bl_users)
@lang.language()
async def _ping(_, m: types.Message):
    start = time.time()
    sent = await m.reply_text(m.lang["pinging"])
    get_time = lambda s: (lambda r: (f"{r[-1]}, " if r[-1][:-4] != "0" else "") + ":".join(reversed(r[:-1])))([f"{v}{u}" for v, u in zip([s%60, (s//60)%60, (s//3600)%24, s//86400], ["s", "m", "h", "days"])])
    uptime = get_time(int(time.time() - boot))
    latency = round((time.time() - start) * 1000, 2)
    await sent.edit_media(
        media=types.InputMediaPhoto(
            media=config.PING_IMG,
            caption=m.lang["ping_pong"].format(
                latency,
                uptime,
                psutil.cpu_percent(interval=0),
                psutil.virtual_memory().percent,
                psutil.disk_usage("/").percent,
                await anon.ping(),
            )
        ),
        reply_markup=buttons.ping_markup(m.lang["support"]),
    )


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: restart
# ==============================================================================
@app.on_message(filters.command(["logs"]) & app.sudoers)
@lang.language()
async def _logs(_, m: types.Message):
    sent = await m.reply_text(m.lang["log_fetch"])
    if not os.path.exists(config.LOG_FILE):
        return await sent.edit_text(m.lang["log_not_found"])
    await sent.edit_media(
        media=types.InputMediaDocument(
            media=config.LOG_FILE,
            caption=m.lang["log_sent"].format(app.name),
        )
    )


@app.on_message(filters.command(["logger"]) & app.sudoers)
@lang.language()
async def _logger(_, m: types.Message):
    if len(m.command) < 2:
        return await m.reply_text(m.lang["logger_usage"].format(m.command[0]))
    if m.command[1] not in ("on", "off"):
        return await m.reply_text(m.lang["logger_usage"].format(m.command[0]))

    if m.command[1] == "on":
        await db.set_logger(True)
        await m.reply_text(m.lang["logger_on"])
    else:
        await db.set_logger(False)
        await m.reply_text(m.lang["logger_off"])


@app.on_message(filters.command(["restart"]) & app.sudoers)
@lang.language()
async def _restart(_, m: types.Message):
    sent = await m.reply_text(m.lang["restarting"])

    for directory in ["cache", "downloads"]:
        shutil.rmtree(directory, ignore_errors=True)

    await sent.edit_text(m.lang["restarted"])
    task = asyncio.create_task(stop())
    await task

    try: os.remove(config.LOG_FILE)
    except Exception: pass

    os.execl(sys.executable, sys.executable, os.path.abspath(__file__))


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: stats
# ==============================================================================
from pytgcalls import __version__ as pytgver


@app.on_message(filters.command(["stats"]) & filters.group & ~app.bl_users)
@lang.language()
async def _stats(_, m: types.Message):
    sent = await m.reply_photo(
        photo=branding_image("stats"),
        caption=m.lang["stats_fetching"],
    )

    pid = os.getpid()
    _utext = m.lang["stats_user"].format(
        app.name,
        len(userbot.clients),
        config.AUTO_LEAVE,
        len(db.blacklisted),
        len(app.bl_users),
        len(app.sudoers),
        len(await db.get_chats()),
        len(await db.get_users()),
    )
    if m.from_user.id in app.sudoers:
        process = psutil.Process(pid)
        storage = psutil.disk_usage("/")
        _utext += m.lang["stats_sudo"].format(
            len(ALL_MODULES),
            platform.system(),
            f"{process.memory_info().rss / 1024**2:.2f}",
            round(psutil.virtual_memory().total / (1024.0**3)),
            process.cpu_percent(interval=1.0),
            psutil.cpu_count(),
            f"{storage.used / (1024.0**3):.2f}",
            f"{storage.total / (1024.0**3):.2f}",
            sys.version.split()[0],
            pyrogram_version,
            pytgver,
        )
    await sent.edit_caption(_utext)


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: sudoers
# ==============================================================================
@app.on_message(filters.command(["addsudo", "delsudo", "rmsudo"]) & filters.user(app.owner))
@lang.language()
async def _sudo(_, m: types.Message):
    user = await utils.extract_user(m)
    if not user:
        return await m.reply_text(m.lang["user_not_found"])

    if m.command[0] == "addsudo":
        if user.id in app.sudoers:
            return await m.reply_text(m.lang["sudo_already"].format(user.mention))

        app.sudoers.add(user.id)
        await db.add_sudo(user.id)
        await m.reply_text(m.lang["sudo_added"].format(user.mention))
    else:
        if user.id not in app.sudoers:
            return await m.reply_text(m.lang["sudo_not"].format(user.mention))

        app.sudoers.discard(user.id)
        await db.del_sudo(user.id)
        await m.reply_text(m.lang["sudo_removed"].format(user.mention))


o_mention = None

@app.on_message(filters.command(["listsudo", "sudolist"]))
@lang.language()
async def _listsudo(_, m: types.Message):
    global o_mention
    sent = await m.reply_text(m.lang["sudo_fetching"])

    if not o_mention:
        o_mention = (await app.get_users(app.owner)).mention
    txt = m.lang["sudo_owner"].format(o_mention)
    sudoers = await db.get_sudoers()
    if sudoers:
        txt += m.lang["sudo_users"]

    for user_id in sudoers:
        try:
            user = (await app.get_users(user_id)).mention
            txt += f"\n- {user}"
        except Exception:
            continue

    await sent.edit_text(txt)


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: misc
# ==============================================================================
@app.on_message(filters.video_chat_started, group=19)
@app.on_message(filters.video_chat_ended, group=20)
async def _watcher_vc(_, m: types.Message):
    await anon.stop(m.chat.id)


async def auto_leave():
    while True:
        await asyncio.sleep(3600)
        for ub in userbot.clients:
            try:
                chats = [dialog.chat.id async for dialog in ub.get_dialogs()
                            if dialog.chat.type in [
                                enums.ChatType.GROUP, enums.ChatType.SUPERGROUP,
                            ]][-20:]
                for chat in chats:
                    if chat in [app.logger, -1001686672798, -1001549206010]:
                        continue
                    if chat in db.active_calls:
                        continue
                    await ub.leave_chat(chat)
                    await asyncio.sleep(12)
            except asyncio.CancelledError:
                raise
            except Exception:
                continue


async def track_time():
    while True:
        await asyncio.sleep(1)
        for chat_id in list(db.active_calls):
            if not await db.playing(chat_id):
                continue
            media = queue.get_current(chat_id)
            if not media:
                continue
            media.time += 1


async def update_timer(length=10, sleep=12):
    while True:
        await asyncio.sleep(sleep)
        for chat_id in list(db.active_calls):
            if not await db.playing(chat_id):
                continue
            try:
                media = queue.get_current(chat_id)
                if not media:
                    continue
                duration, message_id = media.duration_sec, media.message_id
                if not duration or not message_id or not media.time:
                    continue
                played = media.time
                remaining = max(duration - played, 0)
                pos = min(int((played / duration) * length), length - 1)
                timer = "—" * pos + "◉" + "—" * (length - pos - 1)

                if remaining <= 30:
                    next = queue.get_next(chat_id, check=True)
                    if next and not next.file_path:
                        next.file_path = await yt.download(next.id, video=next.video)

                if remaining < 10:
                    remove = True
                else:
                    if config.THUMB_GEN:
                        timer = f"{time.strftime('%M:%S', time.gmtime(played))} | {timer} | -{time.strftime('%M:%S', time.gmtime(remaining))}"
                    else:
                        timer = None
                    remove = False

                if not timer and not remove:
                    continue

                await app.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=buttons.controls(
                        chat_id=chat_id, timer=timer, remove=remove
                    ),
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                pass


async def vc_watcher(sleep=15):
    while True:
        await asyncio.sleep(sleep)
        for chat_id in list(db.active_calls):
            client = await db.get_assistant(chat_id)
            media = queue.get_current(chat_id)
            if not media:
                continue
            participants = await client.get_participants(chat_id)
            if len(participants) < 2 and media.time > 30:
                _lang = await lang.get_lang(chat_id)
                try:
                    sent = await app.edit_message_reply_markup(
                        chat_id=chat_id,
                        message_id=media.message_id,
                        reply_markup=buttons.controls(
                            chat_id=chat_id, status=_lang["stopped"], remove=True
                        ),
                    )
                    await anon.stop(chat_id)
                    await sent.reply_text(_lang["auto_left"])
                except errors.MessageIdInvalid:
                    pass


# Background tasks (auto_leave / vc_watcher / track_time / update_timer) ko main()
# me `start_misc_tasks()` se start kiya jaata hai.


# ==============================================================================
# SECTION: BUILT-IN PLUGINS: backup / database / plugins / maintenance
# ==============================================================================
# ==============================================================================
# BUILT-IN PLUGIN: BACKUP  (/backup, /backups, /restore)
# ==============================================================================
@app.on_message(filters.command(["backup"]) & app.sudoers)
@lang.language()
async def _backup_cmd(_, m: types.Message):
    sent = await m.reply_text(m.lang["backup_creating"])
    path = await asyncio.to_thread(backup_manager.create, "manual")
    if path is None:
        return await sent.edit_text(m.lang["backup_failed"].format(backup_manager.last_error or "unknown"))

    caption = m.lang["backup_created"].format(path.name, fmt_bytes(path.stat().st_size))
    caption += f"\n🗄️ <b>Engine:</b> {db.mode_label}"
    caption += f"\n🎵 <b>Chats:</b> {len(db.chats)} | <b>Users:</b> {len(db.users)}"
    await sent.delete()
    await m.reply_document(document=str(path), caption=caption)

    # Log group me bhi bhej do (agar current chat logger nahi hai)
    if config.LOGGER_ID and config.BACKUP_TO_LOGGER and m.chat.id != config.LOGGER_ID:
        await backup_manager.send_backup(app, config.LOGGER_ID, path)


@app.on_message(filters.command(["backups", "backuplist"]) & app.sudoers)
@lang.language()
async def _backups_cmd(_, m: types.Message):
    text = m.lang["backup_list"].format(len(backup_manager.list_backups()))
    text += "\n\n" + backup_manager.status_text()
    text += "\n\n" + m.lang["db_status"] + "\n" + await db.stats_summary()
    for chunk in split_text(text):
        await m.reply_text(chunk)


@app.on_message(filters.command(["restore"]) & filters.user(app.owner))
@lang.language()
async def _restore_cmd(_, m: types.Message):
    if not m.reply_to_message or not (
        m.reply_to_message.document or m.reply_to_message.audio or m.reply_to_message.video
    ):
        return await m.reply_text(m.lang["restore_usage"])

    sent = await m.reply_text("⏳ <b>Backup verify + restore kar rahe hain...</b>")
    file_name = getattr(m.reply_to_message.document, "file_name", "") or ""
    with suppress(Exception):
        file_name = file_name or getattr(m.reply_to_message.audio, "file_name", "") or ""

    try:
        if file_name.lower().endswith((".json", ".gz")):
            raw = await m.reply_to_message.download(in_memory=True)
            raw = raw.getvalue() if hasattr(raw, "getvalue") else bytes(raw)
            ok, message = await backup_manager.restore_from_bytes(raw)
        else:
            # VPS par pada backup file ka naam le kar restore karo
            candidate = Path(config.BACKUP_DIR) / file_name if file_name else None
            if not candidate or not candidate.exists():
                return await sent.edit_text(
                    "❌ File name se VPS backup nahi mila. Backup document par reply karein "
                    "ya <code>/restore &lt;backup-file-name&gt;</code> use karein."
                )
            ok, message = await backup_manager.restore_from_path(candidate)
    except Exception as exc:  # noqa: BLE001
        return await sent.edit_text(m.lang["restore_fail"].format(escape(str(exc))))

    if not ok:
        return await sent.edit_text(m.lang["restore_fail"].format(message))
    await sent.edit_text(m.lang["restore_ok"].format(message))
    if config.LOGGER_ID:
        with suppress(Exception):
            await app.send_message(
                config.LOGGER_ID,
                f"♻️ <b>Database restored</b> by {m.from_user.mention}\n{message}",
            )


# ==============================================================================
# BUILT-IN PLUGIN: DATABASE STATUS  (/dbstatus, /syncdb)
# ==============================================================================
@app.on_message(filters.command(["dbstatus", "database"]) & app.sudoers)
@lang.language()
async def _dbstatus_cmd(_, m: types.Message):
    text = m.lang["db_status"] + "\n\n" + await db.stats_summary()
    text += "\n\n" + backup_manager.status_text(limit=5)
    for chunk in split_text(text):
        await m.reply_text(chunk)


@app.on_message(filters.command(["syncdb", "dbsync"]) & filters.user(app.owner))
@lang.language()
async def _syncdb_cmd(_, m: types.Message):
    if len(m.command) < 2 or m.command[1].lower() not in {"push", "pull", "reconnect"}:
        return await m.reply_text(
            "ℹ️ <b>Usage:</b> <code>/syncdb push</code> (local -> Firebase) | "
            "<code>/syncdb pull</code> (Firebase -> local) | <code>/syncdb reconnect</code>\n\n"
            f"🗄️ Current engine: {db.mode_label}"
        )

    action = m.command[1].lower()
    sent = await m.reply_text("🔄 <b>Sync chal raha hai...</b>")
    if action == "push":
        ok, message = await db.push_to_firebase()
    elif action == "pull":
        ok, message = await db.pull_from_firebase()
    else:
        ok = await asyncio.to_thread(db._connect_firebase)  # noqa: SLF001
        if ok:
            db.mode = "firebase"
            db.degraded = False
            await db.flush(force=True)
        message = "Firebase reconnect ho gaya." if ok else f"Reconnect fail: {db.last_error}"

    icon = "✅" if ok else "❌"
    await sent.edit_text(f"{icon} <code>{escape(str(message))}</code>\n\n🗄️ {db.mode_label}")


# ==============================================================================
# BUILT-IN PLUGIN: MAINTENANCE MODE  (/maintenance)
# ==============================================================================
@app.on_message(filters.command(["maintenance"]) & filters.user(app.owner))
@lang.language()
async def _maintenance_cmd(_, m: types.Message):
    if len(m.command) < 2 or m.command[1].lower() not in {"on", "off", "yes", "no", "true", "false"}:
        state = "ON" if _is_maintenance() else "OFF"
        return await m.reply_text(
            f"🛠️ <b>Maintenance mode:</b> <code>{state}</code>\n\n"
            "Usage: <code>/maintenance on</code> — sirf sudo commands chalenge\n"
            "           <code>/maintenance off</code> — bot normal"
        )

    enable = m.command[1].lower() in {"on", "yes", "true"}
    db.data["maintenance"] = enable
    db.data.setdefault("settings", {})["maintenance"] = enable
    db.mark_dirty()
    await db.flush(force=True)
    await m.reply_text(m.lang["maintenance_on"] if enable else m.lang["maintenance_off"])


# ==============================================================================
# BUILT-IN PLUGIN: PLUGIN MANAGER  (/plugins, /plugin)
# ==============================================================================
@app.on_message(filters.command(["plugins", "plug"]) & app.sudoers)
@lang.language()
async def _plugins_cmd(_, m: types.Message):
    for chunk in split_text(plugin_manager.status_text()):
        await m.reply_text(chunk)


@app.on_message(filters.command(["plugin"]) & app.sudoers)
@lang.language()
async def _plugin_cmd(_, m: types.Message):
    args = m.command[1:]
    if not args or args[0].lower() not in {"reload", "enable", "disable", "load", "unload", "list", "scan"}:
        return await m.reply_text(
            "🧩 <b>Plugin Manager</b>\n\n"
            "<code>/plugin list</code> — plugins ki list\n"
            "<code>/plugin scan</code> — naye .py files dhoondo aur load karo\n"
            "<code>/plugin reload &lt;name&gt;</code> — hot reload\n"
            "<code>/plugin enable &lt;name&gt;</code> / <code>disable &lt;name&gt;</code>\n\n"
            f"📂 Folder: <code>{config.PLUGINS_DIR}</code>"
        )

    action = args[0].lower()
    if action in {"list", "scan"}:
        if action == "scan":
            loaded = plugin_manager.load_all()
            await m.reply_text(
                f"🔍 Scan complete — <code>{len(loaded)}</code> plugin(s) load hue."
            )
        for chunk in split_text(plugin_manager.status_text()):
            await m.reply_text(chunk)
        return

    if len(args) < 2:
        return await m.reply_text(f"⚠️ Plugin name bhi dein: <code>/plugin {action} &lt;name&gt;</code>")

    name = args[1].replace(".py", "")
    if action == "reload":
        ok, message = await asyncio.to_thread(plugin_manager.reload_plugin, name)
    elif action == "enable":
        ok, message = await asyncio.to_thread(plugin_manager.enable_plugin, name)
    elif action == "disable":
        ok, message = await asyncio.to_thread(plugin_manager.disable_plugin, name)
    elif action == "load":
        count = await asyncio.to_thread(plugin_manager.load_plugin, name)
        ok = count is not None
        message = f"Plugin <code>{name}</code> load ho gaya ({count} handlers)." if ok else f"Load fail: {plugin_manager.errors.get(name, 'unknown')}"
    else:  # unload
        ok = await asyncio.to_thread(plugin_manager.unload_plugin, name)
        message = f"Plugin <code>{name}</code> unload ho gaya." if ok else f"Plugin <code>{name}</code> active nahi tha."

    await m.reply_text(("✅ " if ok else "❌ ") + message)


# ==============================================================================
# BUILT-IN PLUGIN: EXTRA UTILITIES  (/id, /speedtest-lite, /uptime)
# ==============================================================================
@app.on_message(filters.command(["id", "chatid"]) & ~app.bl_users)
@lang.language()
async def _id_cmd(_, m: types.Message):
    text = f"🆔 <b>Chat ID:</b> <code>{m.chat.id}</code>\n"
    text += f"👤 <b>Your ID:</b> <code>{m.from_user.id}</code>"
    if m.reply_to_message and m.reply_to_message.from_user:
        text += f"\n↩️ <b>Replied user ID:</b> <code>{m.reply_to_message.from_user.id}</code>"
    await m.reply_text(text)


@app.on_message(filters.command(["uptime", "sysinfo"]) & app.sudoers)
@lang.language()
async def _uptime_cmd(_, m: types.Message):
    process = psutil.Process(os.getpid())
    storage = psutil.disk_usage("/")
    text = (
        f"⏱️ <b>Uptime:</b> <code>{human_delta(time.time() - boot)}</code>\n"
        f"🧠 <b>RAM:</b> <code>{process.memory_info().rss / 1024 ** 2:.2f} MB</code> / "
        f"<code>{psutil.virtual_memory().total / 1024 ** 3:.1f} GB</code>\n"
        f"💻 <b>CPU:</b> <code>{process.cpu_percent(interval=0.5)}%</code> "
        f"(<code>{psutil.cpu_count()}</code> cores)\n"
        f"💾 <b>Disk:</b> <code>{storage.used / 1024 ** 3:.1f} / {storage.total / 1024 ** 3:.1f} GB</code>\n"
        f"🎧 <b>Active VCs:</b> <code>{len(db.active_calls)}</code>\n"
        f"🗄️ <b>Engine:</b> {db.mode_label}"
    )
    await m.reply_text(text)


# ==============================================================================
# SECTION: BUILT-IN PLUGIN: ADMIN PANEL (button wala panel)
# ==============================================================================
# ==============================================================================
# BUILT-IN PLUGIN: ADMIN PANEL  (button wala admin control panel — /admin)
# ==============================================================================
# Poore admin actions ek inline keyboard panel me:
#   commands bhi kaam karte hain, aur ye panel buttons se bhi wahi kaam karata hai.
#
# Permission model:
#   * Sudo/owner  -> sab kuch (stats, sudo list, blacklist, backup, restore, db, sync, maintenance)
#   * Chat admin  -> chat-level toggles (auth list, playmode, auto-delete, language)
#   * Baaki log   -> kuch nahi (locked buttons par alert aata hai)
# ==============================================================================

# Ye sections sirf sudo/owner ke liye hain
ADMIN_PANEL_SUDO_ONLY: frozenset[str] = frozenset(
    {
        "stats",
        "vc",
        "sudo",
        "bl",
        "plugins",
        "pluginreload",
        "backup",
        "backups",
        "restore",
        "restore_yes",
        "db",
        "push",
        "pull",
        "reconnect",
        "maint",
        "logs",
        "logfile",
    }
)

# Chat admin (ya sudo) ke liye
ADMIN_PANEL_CHAT_LEVEL: frozenset[str] = frozenset(
    {"auth", "settings", "play", "delete", "lang"}
)


def admin_panel_markup(
    is_sudo: bool, in_group: bool, maint: bool = False
) -> types.InlineKeyboardMarkup:
    """Admin panel ka main keyboard (role ke hisaab se buttons)."""
    ikb, ikm = buttons.ikb, buttons.ikm
    rows: list[list] = []

    top = [ikb(text="📊 Stats", callback_data="admpanel stats")]
    if is_sudo:
        top.append(ikb(text="🎧 Active VC", callback_data="admpanel vc"))
    rows.append(top)

    if in_group:
        rows.append(
            [
                ikb(text="✅ Auth list", callback_data="admpanel auth"),
                ikb(text="⚙️ Chat Settings", callback_data="admpanel settings"),
            ]
        )

    if is_sudo:
        rows.append(
            [
                ikb(text="👑 Sudo list", callback_data="admpanel sudo"),
                ikb(text="📛 Blacklist", callback_data="admpanel bl"),
            ]
        )
        rows.append(
            [
                ikb(text="📦 Backup now", callback_data="admpanel backup"),
                ikb(text="🗂 Backups", callback_data="admpanel backups"),
                ikb(text="♻️ Restore", callback_data="admpanel restore"),
            ]
        )
        rows.append(
            [
                ikb(text="🗄 DB status", callback_data="admpanel db"),
                ikb(text="⬆️ Push", callback_data="admpanel push"),
                ikb(text="⬇️ Pull", callback_data="admpanel pull"),
            ]
        )
        rows.append(
            [
                ikb(text="🔌 Plugins", callback_data="admpanel plugins"),
                ikb(text="🧾 Logs", callback_data="admpanel logs"),
                ikb(
                    text=("🛠 Maint: ON" if maint else "🛠 Maint: OFF"),
                    callback_data="admpanel maint",
                ),
            ]
        )

    rows.append(
        [
            ikb(text="🌐 Language", callback_data="admpanel lang"),
            ikb(text="🔄 Refresh", callback_data="admpanel home"),
            ikb(text="❌ Close", callback_data="admpanel close"),
        ]
    )
    return ikm(rows)


def admin_panel_home_text(is_sudo: bool, in_group: bool, chat_id: int) -> str:
    """Panel ka default (home) text."""
    engine = db.mode_label
    health = "🟢 OK" if not db.degraded else "🟠 DEGRADED (local fallback)"
    text = (
        f"🎛️ <b>{escape(BOT_DISPLAY_NAME)} — Admin Control Panel</b>\n"
        f"<blockquote>Neeche buttons se poora control — commands ki zaroorat nahi.</blockquote>\n\n"
        f"🗄️ <b>Engine:</b> {engine}\n"
        f"🩺 <b>Status:</b> {health}\n"
        f"⏱️ <b>Uptime:</b> {human_delta(time.time() - boot)}\n"
        f"💬 <b>Chats:</b> <code>{len(db.chats)}</code> | 👤 <b>Users:</b> <code>{len(db.users)}</code>\n"
        f"👑 <b>Sudo:</b> <code>{len(app.sudoers)}</code> | 🚫 <b>Blacklist:</b> <code>{len(app.bl_users)}</code>\n"
        f"🎧 <b>Active VC:</b> <code>{len(db.active_calls)}</code> | 🧩 <b>Plugins:</b> <code>{len(plugin_manager.handlers)}</code>\n"
        f"🛠️ <b>Maintenance:</b> <code>{'ON' if _is_maintenance() else 'OFF'}</code>\n"
    )
    if in_group:
        text += f"\n🆔 <b>Chat:</b> <code>{chat_id}</code>"
    if not is_sudo:
        text += "\n\n🔒 <i>Kuch buttons sirf sudo/owner ke liye hain.</i>"
    return text


async def admin_panel_settings_view(
    chat_id: int, note: str = ""
) -> tuple[str, types.InlineKeyboardMarkup]:
    """
    Chat settings + saare toggles ek hi panel me.
    (`/settings` ka panel bhi isi jagah link hota hai — dono ek doosre se connected.)
    """
    play_mode = await db.get_play_mode(chat_id)
    cmd_delete = await db.get_cmd_delete(chat_id)
    language = await db.get_lang(chat_id)
    text = (
        "⚙️ <b>Chat Settings</b>\n\n"
        f"🎚️ <b>Playmode:</b> <code>{'Admin only' if play_mode else 'Everyone'}</code>\n"
        f"🗑 <b>Auto-delete:</b> <code>{'ON' if cmd_delete else 'OFF'}</code>\n"
        f"🌐 <b>Language:</b> <code>{language}</code>\n"
        "<blockquote>Tap karke turant badlein — saari chat settings ek hi jagah.</blockquote>"
    )
    if note:
        text += f"\n{note}"
    rows = [
        [
            buttons.ikb(
                text=f"🎚 Playmode: {mode_label(play_mode)}",
                callback_data="admpanel play",
            )
        ],
        [
            buttons.ikb(
                text=f"🗑 Auto-delete: {toggle_label(cmd_delete)}",
                callback_data="admpanel delete",
            )
        ],
        [buttons.ikb(text="🌐 Language badlein", callback_data="admpanel lang")],
        [buttons.ikb(text="🔙 Admin Panel", callback_data="admpanel home")],
    ]
    return text, buttons.ikm(rows)


async def admin_panel_section(
    section: str,
    chat_id: int,
    is_sudo: bool,
    in_group: bool,
    lang_obj: dict | None = None,
) -> tuple[str, types.InlineKeyboardMarkup]:
    """
    Panel ka har section — (text, keyboard) return karta hai.
    Toggle wale sections (playmode / auto-delete / maintenance) yahi side-effect karte hain.
    """
    lang_obj = lang_obj or {}
    back = [[buttons.ikb(text="🔙 Back", callback_data="admpanel home")]]
    markup = lambda: buttons.ikm(back)  # noqa: E731

    if section == "stats":
        process = psutil.Process(os.getpid())
        disk = psutil.disk_usage("/")
        userbot_count = len(getattr(userbot, "clients", []) or [])
        text = (
            "📊 <b>Bot Statistics</b>\n\n"
            f"🤖 <b>Bot:</b> {escape(getattr(app, 'name', BOT_DISPLAY_NAME))} v{__version__}\n"
            f"🆔 <b>ID:</b> <code>{getattr(app, 'id', '—')}</code>\n"
            f"👥 <b>Users:</b> <code>{len(await db.get_users())}</code>\n"
            f"💬 <b>Chats:</b> <code>{len(await db.get_chats())}</code>\n"
            f"🎧 <b>Active VC:</b> <code>{len(db.active_calls)}</code>\n"
            f"🎵 <b>Assistants:</b> <code>{userbot_count}</code>\n"
            f"👑 <b>Sudo:</b> <code>{len(app.sudoers)}</code>\n"
            f"🚫 <b>Blacklist:</b> <code>{len(app.bl_users)}</code> (+{len(db.blacklisted)} chats)\n"
            f"🧩 <b>Plugins:</b> <code>{len(plugin_manager.handlers)}</code> "
            f"(built-in modules: <code>{len(ALL_MODULES)}</code>)\n\n"
            f"🧠 <b>RAM:</b> {process.memory_info().rss / 1024 ** 2:.2f} MB | "
            f"💻 <b>CPU:</b> {psutil.cpu_percent()}% / {psutil.cpu_count()} cores\n"
            f"💾 <b>Disk:</b> {disk.used / 1024 ** 3:.2f} / {disk.total / 1024 ** 3:.2f} GB\n"
            f"🐍 <b>Python:</b> {sys.version.split()[0]} | <b>OS:</b> {platform.system()}\n"
            f"📦 <b>Pyrogram:</b> {pyrogram_version} | <b>PyTgCalls:</b> {pytgver}\n"
            f"⏱️ <b>Uptime:</b> {human_delta(time.time() - boot)}"
        )
        return text, markup()

    if section == "vc":
        if not db.active_calls:
            return "🎧 <b>Active Voice Chats:</b> koi nahi.", markup()
        text = f"🎧 <b>Active Voice Chats ({len(db.active_calls)})</b>\n"
        for i, cid in enumerate(db.active_calls, start=1):
            playing = queue.get_current(cid)
            title = (playing.title[:30] if playing else "—")
            text += f"\n{i}. <code>{cid}</code>\n    ➜ {escape(title)}"
        return text, markup()

    if section == "sudo":
        sudoers = sorted(await db.get_sudoers())
        text = f"👑 <b>Sudo users ({len(sudoers)})</b>\n\n"
        text += f"• <a href=\"tg://user?id={app.owner}\">{app.owner}</a> <i>(owner)</i>\n"
        for uid in sudoers:
            if int(uid) == app.owner:
                continue
            text += f"• <a href=\"tg://user?id={uid}\">{uid}</a>\n"
        text += "\n<i>Add/remove: /addsudo, /delsudo</i>"
        return text, markup()

    if section == "bl":
        bl_users = sorted(app.bl_users)
        bl_chats = sorted(db.blacklisted)
        text = f"📛 <b>Blacklist</b>\n\n👤 <b>Users ({len(bl_users)}):</b>\n"
        text += "".join(f"• <a href=\"tg://user?id={uid}\">{uid}</a>\n" for uid in bl_users[:40]) or "—\n"
        text += f"\n💬 <b>Chats ({len(bl_chats)}):</b>\n"
        text += "".join(f"• <code>{cid}</code>\n" for cid in bl_chats[:40]) or "—\n"
        text += "\n<i>Add/remove: /blacklist, /unblacklist, /whitelist</i>"
        return text, markup()

    if section == "auth":
        auth = sorted(await db._get_auth(chat_id))  # noqa: SLF001
        text = f"✅ <b>Authorised users ({len(auth)})</b>\n\n"
        text += "".join(
            f"{i}. <a href=\"tg://user?id={uid}\">{uid}</a>\n" for i, uid in enumerate(auth, start=1)
        ) or "<i>Koi authorised user nahi.</i>\n"
        text += "\n<i>Add/remove: /auth (reply), /unauth (reply)</i>"
        return text, markup()

    if section in {"settings", "play", "delete"}:
        note = ""
        if section == "play":
            current = await db.get_play_mode(chat_id)
            await db.set_play_mode(chat_id, current)
            note = (
                "🔒 Ab sirf <b>chat admins / authorised users</b> gaana play kar sakte hain."
                if not current
                else "👥 Ab <b>sabhi members</b> gaana play kar sakte hain."
            )
        elif section == "delete":
            current = await db.get_cmd_delete(chat_id)
            await db.set_cmd_delete(chat_id, not current)
            note = (
                "🗑 Ab bot ke command messages automatically delete honge."
                if not current
                else "⌨️ Ab command messages delete nahi honge."
            )
        return await admin_panel_settings_view(chat_id, note)

    if section == "lang":
        current = await db.get_lang(chat_id)
        text = (
            "🌐 <b>Language / भाषा</b>\n\n"
            f"Current: <code>{current}</code>\nNeeche se koi bhi language chunein:"
        )
        rows = buttons.lang_markup(current)
        rows.inline_keyboard.append(
            [buttons.ikb(text="🔙 Back", callback_data="admpanel home")]
        )
        return text, rows

    if section == "plugins":
        text = "🔌 <b>Plugins</b>\n\n" + plugin_manager.status_text()
        text += "\n\n<i>/plugin reload &lt;name&gt; — hot reload | /plugin scan — naye files load</i>"
        return text, markup()

    if section == "backup":
        path = await asyncio.to_thread(backup_manager.create, "manual")
        if path is None:
            return (
                f"❌ <b>Backup fail:</b> <code>{escape(str(backup_manager.last_error or 'unknown'))}</code>",
                markup(),
            )
        size = fmt_bytes(path.stat().st_size)
        text = (
            "📦 <b>Backup ban gaya</b>\n\n"
            f"📄 <code>{escape(path.name)}</code>\n"
            f"💾 Size: <code>{size}</code>\n"
            f"🗄️ Engine: {db.mode_label}\n"
            f"💬 Chats: <code>{len(db.chats)}</code> | 👤 Users: <code>{len(db.users)}</code>\n"
        )
        if config.LOGGER_ID and config.BACKUP_TO_LOGGER:
            sent = await backup_manager.send_backup(app, config.LOGGER_ID, path)
            text += "\n📤 Log group me bhi bhej diya." if sent else "\n⚠️ Log group delivery skip hui."
        return text, markup()

    if section == "backups":
        listing = backup_manager.list_backups()
        text = f"🗂 <b>Backups ({len(listing)})</b>\n\n" + backup_manager.status_text(limit=10)
        return text, markup()

    if section == "restore":
        listing = backup_manager.list_backups()
        if not listing:
            return "♻️ <b>Restore:</b> koi backup file nahi mili.", markup()
        latest = listing[-1]
        size = fmt_bytes(latest.stat().st_size)
        text = (
            "♻️ <b>Restore confirmation</b>\n\n"
            f"Latest backup: <code>{escape(latest.name)}</code>\n"
            f"💾 Size: <code>{size}</code>\n"
            f"🗄️ Engine: {db.mode_label}\n\n"
            "⚠️ Ye current database ko backup se replace kar dega "
            "(restore se pehle ek safety backup bhi banta hai)."
        )
        rows = [
            [
                buttons.ikb(text="✅ Haan, restore karo", callback_data="admpanel restore_yes"),
                buttons.ikb(text="❌ Cancel", callback_data="admpanel home"),
            ]
        ]
        return text, buttons.ikm(rows)

    if section == "restore_yes":
        listing = backup_manager.list_backups()
        if not listing:
            return "❌ Restore fail: backup file nahi mili.", markup()
        ok, message = await backup_manager.restore_from_path(listing[-1])
        icon = "✅" if ok else "❌"
        text = (
            f"{icon} <b>Restore {'complete' if ok else 'fail'}</b>\n\n"
            f"<code>{escape(str(message))}</code>\n\n"
            f"🚫 Blacklist: <code>{len(db.blacklisted)}</code> | 👑 Sudo: <code>{len(app.sudoers)}</code>"
        )
        if ok and config.LOGGER_ID:
            with suppress(Exception):
                await app.send_message(
                    config.LOGGER_ID, f"♻️ Restore admin panel se hua.\n{escape(str(message))}"
                )
        return text, markup()

    if section in {"db", "push", "pull", "reconnect"}:
        extra = ""
        if section == "push":
            ok, message = await db.push_to_firebase()
            extra = f"\n\n⬆️ <b>Push:</b> {'✅' if ok else '❌'} <code>{escape(str(message))}</code>"
        elif section == "pull":
            ok, message = await db.pull_from_firebase()
            extra = f"\n\n⬇️ <b>Pull:</b> {'✅' if ok else '❌'} <code>{escape(str(message))}</code>"
        elif section == "reconnect":
            ok = await asyncio.to_thread(db._connect_firebase)  # noqa: SLF001
            if ok:
                db.mode = "firebase"
                db.degraded = False
                await db.flush(force=True)
            extra = (
                f"\n\n🔄 <b>Reconnect:</b> {'✅ ho gaya' if ok else '❌ fail'} "
                f"(mode: <code>{db.mode}</code>)"
            )
        text = "🗄️ <b>Database</b>\n\n" + await db.stats_summary() + extra
        text += "\n\n" + backup_manager.status_text(limit=5)
        return text, markup()

    if section == "maint":
        enable = not _is_maintenance()
        db.data["maintenance"] = enable
        db.data.setdefault("settings", {})["maintenance"] = enable
        db.mark_dirty()
        await db.flush(force=True)
        return (
            f"🛠️ <b>Maintenance mode:</b> <code>{'ON' if enable else 'OFF'}</code>\n\n"
            + (
                "Ab sirf sudo/owner wale commands respond karenge."
                if enable
                else "Bot normal mode me wapas aa gaya."
            ),
            markup(),
        )

    if section == "logs":
        if not os.path.exists(config.LOG_FILE):
            return "🧾 <b>Logs:</b> log file abhi nahi bani.", markup()
        with open(config.LOG_FILE, "r", encoding="utf-8", errors="replace") as handle:
            tail = handle.readlines()[-25:]
        body = "".join(tail).strip() or "(log khaali hai)"
        text = f"🧾 <b>Last 25 log lines</b> <i>({escape(config.LOG_FILE)})</i>\n\n<pre>{escape(body[-3500:])}</pre>"
        rows = [
            [
                buttons.ikb(text="📤 Poora log file", callback_data="admpanel logfile"),
                buttons.ikb(text="🔙 Back", callback_data="admpanel home"),
            ]
        ]
        return text, buttons.ikm(rows)

    # default -> home
    return (
        admin_panel_home_text(is_sudo, in_group, chat_id),
        admin_panel_markup(is_sudo, in_group, _is_maintenance()),
    )


@app.on_message(filters.command(["admin", "panel", "admins"]) & ~app.bl_users)
@lang.language()
@admin_check
async def _admin_panel(_, m: types.Message):
    is_sudo = m.from_user.id in app.sudoers
    in_group = m.chat.type != enums.ChatType.PRIVATE
    text = admin_panel_home_text(is_sudo, in_group, m.chat.id)
    markup = admin_panel_markup(is_sudo, in_group, _is_maintenance())
    await m.reply_text(
        text,
        reply_markup=markup,
        link_preview_options=types.LinkPreviewOptions(is_disabled=True),
    )


@app.on_callback_query(filters.regex("admpanel") & ~app.bl_users)
@lang.language()
async def _admin_panel_cb(_, query: types.CallbackQuery):
    args = query.data.split()
    section = args[1].lower() if len(args) > 1 else "home"

    chat = query.message.chat
    chat_id = chat.id
    in_group = chat.type != enums.ChatType.PRIVATE
    user_id = query.from_user.id
    is_sudo = user_id in app.sudoers

    if section == "close":
        with suppress(Exception):
            await query.answer()
        with suppress(Exception):
            await query.message.delete()
        return

    # permission gates
    if section in ADMIN_PANEL_SUDO_ONLY and not is_sudo:
        return await query.answer("🔒 Ye action sirf sudo/owner ke liye hai.", show_alert=True)

    if (
        section in ADMIN_PANEL_CHAT_LEVEL
        and in_group
        and not is_sudo
        and user_id not in await db.get_admins(chat_id)
    ):
        return await query.answer("🔒 Sirf chat admins ya sudo users.", show_alert=True)

    try:
        await query.answer("⏳")
    except Exception:
        pass

    if section == "logfile":
        if not os.path.exists(config.LOG_FILE):
            return await query.answer("❌ Log file nahi mili.", show_alert=True)
        with suppress(Exception):
            await query.message.reply_document(
                document=config.LOG_FILE,
                caption=f"🧾 <b>{escape(getattr(app, 'name', BOT_DISPLAY_NAME))}</b> log file",
            )
        return

    if section == "refreshvc":
        section = "vc"

    text, markup = await admin_panel_section(section, chat_id, is_sudo, in_group, query.lang)
    try:
        await query.edit_message_text(text, reply_markup=markup)
    except errors.MessageNotModified:
        pass
    except Exception:
        with suppress(Exception):
            await query.message.reply_text(
                text,
                reply_markup=markup,
                link_preview_options=types.LinkPreviewOptions(is_disabled=True),
            )


# ==============================================================================
# SECTION: BRANDING / SOURCE EXTRACT / HOSTING STOP
# ==============================================================================
# ==============================================================================
# SECTION: CUSTOM BRANDING IMAGE  (start / stats pic — TG reference se load)
# ==============================================================================
# Admin kisi bhi photo ko reply karke (ya URL de kar) bot ki image set kar sakta hai.
#
# IMPORTANT: image ka DATA database me NAHI jaata — DB me sirf chhota reference
#             rehta hai: {type, value, chat_id, message_id, set_by, set_at}.
#             Bot image ko Telegram se hi load karta hai:
#               • file_id  -> app.download_media(file_id)      (Telegram se)
#               • url      -> aiohttp se download
#             aur cache/branding_<slot>.jpg me rakhta hai (local cache, DB me nahi).
#
# Commands (sudo/owner only):
#   /setimg                     -> reply ki gayi photo ko start image banao
#   /setimg <url>               -> URL se start image set karo
#   /setimg stats               -> (reply/url) stats image ke liye
#   /setimg start|stats remove  -> default par wapas
#   /setimg show                -> current image dikhao
# ==============================================================================

BRANDING_SLOTS = ("start", "stats")
BRANDING_FILES = {
    "start": "branding_start.jpg",
    "stats": "branding_stats.jpg",
}


def branding_data() -> dict:
    """DB me branding references (chhota dict — image bytes DB me nahi)."""
    data = db.data
    store = data.get("branding")
    if not isinstance(store, dict):
        store = {}
        data["branding"] = store
    settings = data.setdefault("settings", {})
    settings["branding"] = store
    return store


def branding_ref(slot: str = "start") -> Optional[dict]:
    ref = branding_data().get(slot)
    return ref if isinstance(ref, dict) and ref.get("value") else None


def branding_cache_path(slot: str) -> Path:
    return Path(config.CACHE_DIR) / BRANDING_FILES.get(slot, "branding.jpg")


async def branding_load(slot: str = "start", force: bool = False) -> Optional[str]:
    """
    Image ko Telegram/URL se laa kar cache me rakhta hai aur path return karta hai.
    Pehle local cache check hota hai (fast), phir referer se download.
    """
    ref = branding_ref(slot)
    if not ref:
        return None

    path = branding_cache_path(slot)
    if path.exists() and not force and path.stat().st_size > 0:
        return str(path)

    kind, value = ref.get("type"), str(ref.get("value", ""))
    try:
        if kind == "file_id":
            with suppress(FileNotFoundError):
                path.unlink()
            result = await app.download_media(value, file_name=str(path))
            if result and Path(result).exists():
                ref["loaded_at"] = int(time.time())
                db.mark_dirty()
                return str(result)
            logger.warning("Branding (%s): file_id se image nahi mili, URL fallback try.", slot)

        if value.startswith(("http://", "https://")) or kind == "url":
            async with aiohttp.ClientSession() as session:
                async with session.get(value, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        path.write_bytes(await resp.read())
                        return str(path)
                    logger.warning("Branding (%s): URL %s -> HTTP %s", slot, value, resp.status)

        # Last option: TG message se dobara download (message_id + chat_id)
        chat_id, message_id = ref.get("chat_id"), ref.get("message_id")
        if chat_id and message_id:
            msg = await app.get_messages(int(chat_id), int(message_id))
            if msg and (msg.photo or msg.document):
                result = await msg.download(file_name=str(path))
                if result and Path(result).exists():
                    return str(result)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Branding image load fail (%s): %s", slot, exc)
    return None


def branding_sync_value(slot: str = "start") -> str:
    """Boot ke baad config.START_IMG / PING_IMG ke liye value (cache path ya default)."""
    path = branding_cache_path(slot)
    if path.exists() and path.stat().st_size > 0:
        return str(path)
    return ""


async def branding_apply() -> None:
    """Boot par: DB reference se image load karke config ko override karo."""
    for slot in BRANDING_SLOTS:
        if not branding_ref(slot):
            continue
        got = await branding_load(slot)
        if not got:
            continue
        if slot == "start":
            config.START_IMG = got
        else:
            config.PING_IMG = got
        logger.info("🎨 Custom %s image active: %s", slot, got)


def branding_status_text() -> str:
    lines = ["🎨 <b>Branding images</b>\n"]
    for slot in BRANDING_SLOTS:
        ref = branding_ref(slot)
        default = config.START_IMG if slot == "start" else config.PING_IMG
        if ref:
            kind = "Telegram file" if ref.get("type") == "file_id" else "URL"
            value = str(ref.get("value", ""))[:48]
            cached = branding_cache_path(slot).exists()
            lines.append(
                f"• <b>{slot}</b>: {kind} — <code>{escape(value)}</code>"
                f" {'✅ cached' if cached else '⚠️ cache nahi'}"
                f"\n  <i>chat:</i> <code>{ref.get('chat_id', '—')}</code>"
                f" <i>msg:</i> <code>{ref.get('message_id', '—')}</code>"
            )
        else:
            lines.append(f"• <b>{slot}</b>: default (<code>{escape(str(default))[:40]}</code>)")
    lines.append(
        "\n<b>Set kaise karein:</b>\n"
        "• Kisi photo par reply karke <code>/setimg</code>\n"
        "• Ya <code>/setimg https://.../pic.jpg</code>\n"
        "• Stats image: <code>/setimg stats</code> (reply/url)\n"
        "• Hatane ke liye: <code>/setimg remove</code>\n\n"
        "<i>Note: image database me save nahi hoti — DB me sirf Telegram reference "
        "(chat id + message id + file id) rehta hai, photo Telegram se load hoti hai.</i>"
    )
    return "\n".join(lines)


@app.on_message(
    filters.command(["setimg", "setimage", "setpic", "setthumb", "branding"]) & app.sudoers
)
@lang.language()
async def _setimg_cmd(_, m: types.Message):
    args = [a for a in m.command[1:]]
    slot = "start"
    if args and args[0].lower() in BRANDING_SLOTS:
        slot = args[0].lower()
        args = args[1:]

    action = (args[0].lower() if args else "").strip()

    if action in {"show", "status"} or not args and not m.reply_to_message:
        # current image bhej do (agar hai)
        ref = branding_ref(slot)
        if not ref:
            return await m.reply_text(branding_status_text())
        got = await branding_load(slot) or str(branding_ref_any_default(slot))
        with suppress(Exception):
            return await m.reply_photo(photo=got, caption=branding_status_text())
        return await m.reply_text(branding_status_text())

    if action in {"remove", "reset", "delete", "clear", "del", "off"}:
        store = branding_data()
        store.pop(slot, None)
        with suppress(OSError):
            branding_cache_path(slot).unlink()
        db.mark_dirty()
        await db.flush(force=True)
        return await m.reply_text(
            f"🧹 <b>{slot}</b> image hata di — ab default image use hogi.\n\n"
            + branding_status_text()
        )

    # source image: reply ki photo/document ya URL
    url = args[0] if args else None
    if not url and m.reply_to_message and (m.reply_to_message.photo or m.reply_to_message.document):
        url = None  # reply se lete hain
    elif url and not url.startswith(("http://", "https://")):
        return await m.reply_text(
            "⚠️ URL <code>http(s)://</code> se shuru hona chahiye, ya kisi photo par "
            "reply karke <code>/setimg</code> bhejein."
        )

    sent = await m.reply_text("🎨 <b>Image save kar rahe hain...</b>")
    ref: dict
    if url:
        ref = {
            "type": "url",
            "value": url,
            "chat_id": m.chat.id,
            "message_id": m.id,
            "set_by": m.from_user.id,
            "set_at": int(time.time()),
        }
    else:
        media_msg = m.reply_to_message
        file_id = None
        with suppress(Exception):
            file_id = media_msg.photo.file_id if media_msg.photo else media_msg.document.file_id
        if not file_id:
            return await sent.edit_text("❌ Photo/document ka file id nahi mila, dobara try karein.")
        ref = {
            "type": "file_id",
            "value": file_id,              # chhota reference — image DB me nahi
            "chat_id": media_msg.chat.id,  # TG chat id (jahan se load hoga)
            "message_id": media_msg.id,    # TG message id (backup reference)
            "set_by": m.from_user.id,
            "set_at": int(time.time()),
        }

    branding_data()[slot] = ref
    db.mark_dirty()
    got = await branding_load(slot, force=True)
    if not got:
        return await sent.edit_text(
            "⚠️ Reference save ho gaya, lekin image load nahi ho payi (bot ko media access "
            "nahi mila?).<br>\n" + branding_status_text()
        )

    if slot == "start":
        config.START_IMG = got
    else:
        config.PING_IMG = got
    await db.flush(force=True)
    with suppress(Exception):
        return await sent.edit_media(
            media=types.InputMediaPhoto(media=got, caption="✅ " + branding_status_text())
        )
    await sent.edit_text("✅ " + branding_status_text())


def branding_ref_any_default(slot: str) -> str:
    return config.START_IMG if slot == "start" else config.PING_IMG


def branding_image(slot: str = "start") -> str:
    """Start/stats handlers ke liye image (custom ho to cache path, warna config default)."""
    path = branding_cache_path(slot)
    if branding_ref(slot) and path.exists() and path.stat().st_size > 0:
        return str(path)
    return config.START_IMG if slot == "start" else config.PING_IMG


# ==============================================================================
# SECTION: SOURCE EXTRACT  (/source — admin poora code nikaal sakta hai)
# ==============================================================================
SOURCE_EXCLUDE_DIRS = {"data", "cache", "downloads", ".git", "__pycache__", ".venv", "venv"}
SOURCE_EXTRA_HINT = (
    "💡 <b>Options:</b>\n"
    "<code>/source</code> — poora project ZIP\n"
    "<code>/source main</code> — sirf main.py\n"
    "<code>/source list</code> — files ki list\n"
    "<code>/source &lt;filename&gt;</code> — koi bhi file (e.g. <code>/source requirements.txt</code>)"
)


def source_root() -> Path:
    return Path(__file__).resolve().parent


def source_files() -> list[Path]:
    root = source_root()
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in SOURCE_EXCLUDE_DIRS for part in rel.parts):
            continue
        if rel.suffix in {".pyc", ".session", ".log"} or rel.name in {"log.txt", ".env"}:
            continue
        files.append(path)
    return files


def source_zip(dest: Optional[Path] = None) -> Optional[Path]:
    """Poora source ek zip me — cache/ me banta hai (repo me kuch nahi likha jaata)."""
    files = source_files()
    if not files:
        return None
    dest = dest or (Path(config.CACHE_DIR) / f"{BOT_DISPLAY_NAME}-source.zip")
    dest.parent.mkdir(parents=True, exist_ok=True)
    root = source_root()
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            with suppress(Exception):
                zf.write(path, arcname=str(Path(BOT_DISPLAY_NAME) / path.relative_to(root)))
    return dest


@app.on_message(filters.command(["source", "extract", "codes", "getcode"]) & app.sudoers)
@lang.language()
async def _source_cmd(_, m: types.Message):
    args = [a for a in m.command[1:]]
    root = source_root()
    sent = await m.reply_text("📦 <b>Source nikaal rahe hain...</b>")

    if not args:
        path = await asyncio.to_thread(source_zip)
        if not path:
            return await sent.edit_text("❌ Source files nahi mili.")
        size = fmt_bytes(path.stat().st_size)
        await sent.delete()
        await m.reply_document(
            document=str(path),
            caption=(
                f"📦 <b>{escape(BOT_DISPLAY_NAME)} — poora source code</b>\n"
                f"🧾 <b>Files:</b> <code>{len(source_files())}</code> | 💾 <code>{size}</code>\n"
                f"⚙️ <b>Version:</b> <code>v{__version__}</code>\n\n"
                + SOURCE_EXTRA_HINT
            ),
        )
        return

    target = args[0].lower()
    if target in {"list", "ls", "files"}:
        files = source_files()
        lines = [f"📂 <b>Source files ({len(files)})</b>\n"]
        for path in files[:120]:
            lines.append(f"• <code>{escape(str(path.relative_to(root)))}</code>")
        if len(files) > 120:
            lines.append(f"… +{len(files) - 120} more")
        for chunk in split_text("\n".join(lines)):
            await m.reply_text(chunk)
        return await sent.delete()

    if target in {"main", "main.py"}:
        main_file = root / "main.py"
        await sent.delete()
        await m.reply_document(
            document=str(main_file),
            caption=(
                f"📄 <b>main.py</b> — <code>v{__version__}</code> "
                f"({fmt_bytes(main_file.stat().st_size)}, {len(open(main_file, encoding='utf-8').readlines())} lines)\n\n"
                + SOURCE_EXTRA_HINT
            ),
        )
        return

    for name in args:
        candidate = (root / name).resolve()
        if root not in candidate.parents and candidate != root:
            return await sent.edit_text("🚫 Sirf project folder ki files mil sakti hain.")
        if candidate.is_file():
            await sent.delete()
            await m.reply_document(document=str(candidate), caption=f"📄 <code>{escape(str(name))}</code>")
            return

    await sent.edit_text("❌ File nahi mili.\n\n" + SOURCE_EXTRA_HINT)


# ==============================================================================
# SECTION: HOSTING STOP  (/shutdown — confirm button ke saath)
# ==============================================================================
SHUTDOWN_MARKUP_KEY = "shutdown_confirm"


def shutdown_markup() -> types.InlineKeyboardMarkup:
    return buttons.ikm(
        [
            [
                buttons.ikb(text="🛑 Haan, bot band karo", callback_data="hostshutdown yes"),
                buttons.ikb(text="❌ Cancel", callback_data="hostshutdown no"),
            ]
        ]
    )


async def perform_shutdown(reason: str = "manual") -> None:
    """
    Hosting graceful band: pending DB flush + shutdown backup + logs, phir process exit.
    (Hosting panel/GitHub runner apne aap process ko dead mark kar dega.)
    """
    logger.warning("🛑 SHUTDOWN requested (%s) — save + backup kar rahe hain...", reason)
    with suppress(Exception):
        await db.flush(force=True)
    with suppress(Exception):
        path = await asyncio.to_thread(backup_manager.create, "shutdown")
        if path and config.LOGGER_ID and config.BACKUP_TO_LOGGER:
            await backup_manager.send_backup(app, config.LOGGER_ID, path, "🛑 Shutdown backup")
    with suppress(Exception):
        await app.send_message(
            config.LOGGER_ID,
            f"🛑 <b>Bot band kiya gaya</b> ({escape(reason)})\n"
            f"🗄️ DB: {db.mode_label} | 💬 Chats: <code>{len(db.chats)}</code> | "
            f"👤 Users: <code>{len(db.users)}</code>",
        )
    logger.warning("🛑 Shutdown complete — process exit ho raha hai.")
    await asyncio.sleep(1)  # messages jaane ka mauka
    os.kill(os.getpid(), signal.SIGTERM)


@app.on_message(filters.command(["shutdown", "stopbot", "hoststop", "killbot"]) & app.sudoers)
@lang.language()
async def _shutdown_cmd(_, m: types.Message):
    await m.reply_text(
        "🛑 <b>Bot hosting band kar dein?</b>\n\n"
        "• Pending data save + shutdown backup banega\n"
        "• Log group me notification jayega\n"
        "• Phir process band ho jayega (hosting panel me 'down' dikhega)\n\n"
        "<i>Chalane ke liye dobara start karna hoga.</i>",
        reply_markup=shutdown_markup(),
        link_preview_options=types.LinkPreviewOptions(is_disabled=True),
    )


@app.on_callback_query(filters.regex("hostshutdown") & app.sudoers)
@lang.language()
async def _shutdown_cb(_, query: types.CallbackQuery):
    args = query.data.split()
    if len(args) < 2 or args[1].lower() != "yes":
        with suppress(Exception):
            await query.answer("✅ Cancel kar diya.")
        return await query.edit_message_text("✅ Shutdown cancel kar diya — bot chalta rahega.")

    await query.answer("🛑 Band kar rahe hain...", show_alert=True)
    with suppress(Exception):
        await query.edit_message_text("🛑 <b>Bot band ho raha hai</b> — save + backup ke baad process exit.")
    asyncio.create_task(perform_shutdown(f"manual by {query.from_user.id}"))


# ==============================================================================
# SECTION: BOOT SEQUENCE
# ==============================================================================
# ==============================================================================
# BOOT SEQUENCE  (main entrypoint)
# ==============================================================================
async def idle() -> None:
    """Signals ka wait karta hai (Ctrl+C / SIGTERM par gracefully exit)."""
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGABRT):
        with suppress(NotImplementedError, ValueError, RuntimeError):
            loop.add_signal_handler(sig, stop_event.set)
    await stop_event.wait()


async def stop() -> None:
    """Sab kuch band karo — lekin pehle database + backup safe karo."""
    logger.info("Stopping...")

    # 1. PyTgCalls streams band karo
    with suppress(Exception):
        await anon.exit()

    # 2. Background tasks cancel
    for task in tasks:
        task.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await task

    await backup_manager.stop_scheduler()

    # 3. Shutdown backup + database flush
    with suppress(Exception):
        await backup_manager.on_shutdown()
    with suppress(Exception):
        await db.close()

    # 4. Clients band karo
    with suppress(Exception):
        await app.exit()
    with suppress(Exception):
        await userbot.exit()
    with suppress(Exception):
        await thumb.close()

    logger.info("Stopped.\n")


def start_misc_tasks() -> None:
    """misc plugin ke background tasks (auto-leave, VC watcher, timer) start karo."""
    if config.AUTO_END and config.VC_WATCHER:
        tasks.append(asyncio.create_task(vc_watcher()))
    if config.AUTO_LEAVE:
        tasks.append(asyncio.create_task(auto_leave()))
    tasks.append(asyncio.create_task(track_time()))
    tasks.append(asyncio.create_task(update_timer()))
    tasks.append(asyncio.create_task(cleanup_loop()))


async def cleanup_loop() -> None:
    """Purani downloaded files ko periodic cleanup (disk full hone se bachao)."""
    while True:
        try:
            await asyncio.sleep(3600 * 6)
            active: set[str] = set()
            for chat_id in list(db.active_calls):
                media = queue.get_current(chat_id)
                if media and media.file_path:
                    active.add(str(media.file_path))
            removed = 0
            now = time.time()
            for path in Path(config.DOWNLOADS_DIR).glob("*"):
                try:
                    if not path.is_file() or str(path) in active:
                        continue
                    if now - path.stat().st_mtime < config.CLEANUP_HOURS * 3600:
                        continue
                    path.unlink()
                    removed += 1
                except OSError:
                    continue
            if removed:
                logger.info("🧹 Cleanup: %d purani file(s) delete ki gayi.", removed)
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("Cleanup loop error: %s", exc)


async def main() -> None:
    print(
        f"""
╔══════════════════════════════════════════════════════════════╗
║   🎵  {BOT_DISPLAY_NAME}  v{__version__}  —  Single File Edition
║   Pyrogram + PyTgCalls  |  Firebase / Local VPS + Auto Backup
╚══════════════════════════════════════════════════════════════╝
"""
    )
    config.check()  # mandatory env vars

    # 1. Database (Firebase ya Local VPS) + autosave worker
    await db.connect()
    await db.start_autosave()

    # 2. Telegram clients
    await app.boot()
    await userbot.boot()

    # 3. Voice chat engine
    await anon.boot()

    # 3b. Custom branding images (DB reference -> Telegram/URL se load)
    with suppress(Exception):
        await branding_apply()

    # 4. Thumbnail generator (aiohttp session)
    with suppress(Exception):
        await thumb.start()

    # 5. External plugins (plugins/ folder)
    plugin_manager.load_all()

    # 6. Cookies from COOKIES_URL (batbin.me) agar set hai
    if config.COOKIES_URL:
        with suppress(Exception):
            await yt.save_cookies(config.COOKIES_URL)

    # 7. Sudoers / blacklist cache
    # NOTE: `app.sudoers` / `app.bl_users` ko REPLACE nahi karte — saare plugins ne
    # import time par inhi filter objects ka reference le rakha hai, isliye in-place
    # mutate karna zaroori hai (warna DB se aaye sudoers kaam nahi karenge).
    for user_id in await db.get_sudoers():
        app.sudoers.add(int(user_id))
    for user_id in await db.get_blacklisted():
        if not str(user_id).startswith("-"):
            app.bl_users.add(int(user_id))
    logger.info("Loaded %d sudo users and %d blacklisted users.", len(app.sudoers), len(app.bl_users))

    # 8. Telegram error-log handler + slash command menu
    telegram_log_handler.attach(app, config.LOGGER_ID)
    with suppress(Exception):
        await app.register_commands()

    # 9. Background tasks + automated backup + startup backup
    await asyncio.sleep(0)
    start_misc_tasks()
    await backup_manager.start_scheduler(app)
    await backup_manager.on_startup(app)

    # 10. Handler registration safety net (loop mismatch / async race)
    total_handlers = ensure_handlers_registered(app)
    logger.info("Registered %d command handlers.", total_handlers)

    print(f"✅ {BOT_DISPLAY_NAME} is live!  (Ctrl+C to stop)\n")
    logger.info("Bot is live — database=%s, backups=%s", db.mode_label, config.BACKUP_DIR)

    await idle()
    asyncio.create_task(stop())
    await asyncio.sleep(3)


if __name__ == "__main__":
    # Client ne jis loop par handlers schedule kiye wahi loop use karo
    loop = getattr(app, "loop", None)
    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
    with suppress(RuntimeError):
        asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n👋 Bye!")
    finally:
        with suppress(Exception):
            loop.close()
