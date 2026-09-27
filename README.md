# 🎵 Music-x-bot — All-in-One Single File Telegram VC Music Bot

Telegram Groups ke **Voice Chat / Video Chat** me high-quality music aur video stream karne
ke liye ek **Single-File (`main.py`) bot**, jisme **Firebase Realtime Database** aur
**Local VPS Storage + Automated Backup** dono built-in hain — aur saare **23 plugins,
helpers, 13 locales aur fonts** usi ek file me embedded hain.

```
╔══════════════════════════════════════════════════════════════╗
║   🎵  Music-x-bot  v3.1.0  —  Single File Edition            ║
║   Pyrogram + PyTgCalls  |  Firebase / Local VPS + Auto Backup ║
╚══════════════════════════════════════════════════════════════╝
```

---

## ⚡ Sab Kuch Ek Hi File Me

| Cheez | Original structure | Ab is repo me |
| :--- | :--- | :--- |
| Core engine | `anony/core/*.py` (8 files) | ✅ `main.py` (inlined) |
| Plugins | `anony/plugins/*.py` (**22 plugins**) | ✅ `main.py` (inlined) + `plugins/` auto-load |
| Helpers | `anony/helpers/*.py` (8 files) | ✅ `main.py` (inlined) |
| Locales | `anony/locales/*.json` (**13 languages**) | ✅ `main.py` me embedded (lzma+base64) |
| Fonts | 2 `.ttf` files | ✅ `main.py` me embedded + runtime par extract |
| Database | MongoDB (pymongo) | ✅ **Firebase Realtime DB ⟷ Local VPS (hybrid)** |
| Backup | ❌ nahi tha | ✅ **Automated backup + Telegram delivery + restore** |

> Kuch bhi kam nahi kiya gaya — saare commands, sab features intact hain (neeche poori list).

---

## ✨ Features

### 🎧 Playback
- YouTube, YouTube Playlist, **Telegram files** (audio/video/document/voice) aur **M3U8** links support
- `/play`, `/vplay`, `/playforce`, `/vplayforce` (force = turant bajao, queue skip)
- Pause / Resume / Skip / Stop — inline buttons se bhi
- **Seek** (`/seek`, `/seekback`) — gaane me aage-peeche jaayein
- **Loop** (count based repeat `1–10`), **queue management**, now-playing timer bar
- Multi-assistant load balancing (`SESSION`, `SESSION2`, `SESSION3`, `SESSION4`)

### 🛠️ Admin
- `/auth`, `/unauth`, `/authlist` — per-chat authorized users
- `/admincache`, `/reload` — admin list refresh
- `/playmode`, `/settings` — admin-only play mode, command auto-delete, language
- `/blacklist`, `/unblacklist`, `/whitelist` — bot se group/user block (sudo)
- `/broadcast` — `-copy`, `-nochat`, `-user` flags + error report file
- `/addsudo`, `/delsudo`, `/listsudo` — sudo users (owner)
- `/eval`, `/exec` — live Python evaluation (owner)
- `/activevc`, `/stats`, `/ping`, `/alive`, `/id`, `/uptime`

### 📝 Logs
- **Rotating file logs** (`log.txt`, 10MB × 5 files) + console output
- `/logs` — log file Telegram par (sudo)
- `/logger on|off` — play/chat/user activity logging
- **Telegram error logging** — `ERROR` level logs automatic LOGGER_ID group me
- Play logs, new user/chat logs — sab LOGGER_ID me

### 🗄️ Database (Hybrid Engine)
- **Firebase mode:** `FIREBASE_DATABASE_URL` + service account set ho to data Firebase
  Realtime Database me sync hota hai (debounced background sync)
- **Local VPS mode (default):** Firebase na ho to data `data/database.json` me atomically save
- **Zero data loss:** Firebase down ho jaaye to automatic **degraded mode** → local mirror par
  likhta rahega, aur connection wapas aate hi sab cloud par sync
- `/dbstatus` (status), `/syncdb push|pull|reconnect` (manual sync)

### 📦 Automated Backup
- Har **`BACKUP_INTERVAL_HOURS`** (default 6) ghante me timestamped snapshot `data/backups/`
- **Har backup LOGGER_ID (log group) me document ban kar chala jaata hai**
- `/backup` — turant backup + Telegram par
- `/backups` — saare snapshots list + system status
- `/restore` — backup file par reply karke database restore (owner)
- Retention (`MAX_BACKUPS_RETAINED`), **gzip compression**, pre-restore safety snapshot
- Optional: `BACKUP_REMOTE_DIR` (mounted disk / rclone) par extra copy
- Optional: `FIREBASE_STORAGE_BUCKET` par cloud upload
- Startup + shutdown par bhi automatic backup

### 🌍 Baaki
- **13 languages** — ar, de, en, es, fr, hi, ja, my, pa, pt, ru, tr, zh (`/lang`)
- Custom thumbnail generation (fonts embedded)
- Inline YouTube search — kisi bhi chat me `@YourBot <query>`
- **Plugin system** — `plugins/` folder me `.py` daalo → auto-load + hot reload
- Maintenance mode (`/maintenance on|off`)

---

## 🚀 Setup & Run

### Tarika 1: Automated VPS Setup (Recommended)

```bash
git clone https://github.com/pm169298-boop/Music-x-bot.git
cd Music-x-bot
bash setup      # system deps + .env banata hai (values poochta hai)
bash start      # bot chalu
```

24/7 background:
```bash
screen -S musicbot
bash start        # detach: Ctrl+A phir D
```

### Tarika 2: Manual

```bash
pip install -r requirements.txt
cp sample.env .env      # values bharein
python3 main.py
```

### Tarika 3: Docker

```bash
docker build -t musicxbot .
docker run -d --name musicxbot -v $PWD/data:/app/data --env-file .env musicxbot
```

---

## 🔑 Environment Variables ( Zaroori )

### Telegram (Mandatory)
| Variable | Description |
| :--- | :--- |
| `API_ID` / `API_HASH` | [my.telegram.org](https://my.telegram.org) → API Development Tools |
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) se |
| `SESSION` | Assistant account ka Pyrogram v2 string session ([@StringFatherBot](https://t.me/StringFatherBot)) |
| `OWNER_ID` | Aapki numeric user id ([@userinfobot](https://t.me/userinfobot)) |
| `LOGGER_ID` | Private group id — **logs + automatic backups yahan aayenge** (bot & assistant admin) |
| `SUDO_USERS` | *(Optional)* env se extra sudo users, comma separated — ye hamesha sudo rehte hain (DB se delete bhi nahi hote) |
| `SESSION2` `SESSION3` `SESSION4` | *(Optional)* extra assistants |

### Database — Option A: Firebase (optional)
| Variable | Description |
| :--- | :--- |
| `FIREBASE_DATABASE_URL` | Firebase Realtime Database URL |
| `FIREBASE_CREDENTIALS` | Service account key file (e.g. `firebase_key.json`) |
| `FIREBASE_CREDENTIALS_JSON` | *(Alternative)* pura JSON ek string me |
| `FIREBASE_STORAGE_BUCKET` | *(Optional)* backups cloud par bhi |
| `FIREBASE_ROOT` | Realtime DB me root node (default `musicbot`) |

**Firebase kaise setup karein:**
1. [Firebase Console](https://console.firebase.google.com) → naya project → **Realtime Database** create karein
2. **Project Settings → Service accounts → Generate new private key** → `firebase_key.json` download
3. File ko project folder me rakhein (`.gitignore` me hai — safe) aur `.env` me URL + filename daalein
4. Bot start karein — local data automatic cloud par migrate ho jaayega 🔥

### Database — Option B: Local VPS + Auto Backup (default)
Kuch set karne ki zaroorat nahi. Firebase blank ho to bot automatic:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DATA_DIR` | `data` | Local storage folder |
| `BACKUP_DIR` | `data/backups` | Snapshots folder |
| `BACKUP_INTERVAL_HOURS` | `6` | Kitne ghante me auto-backup |
| `MAX_BACKUPS_RETAINED` | `10` | Kitne snapshots rakhein |
| `BACKUP_TO_LOGGER` | `True` | Backup LOGGER_ID par bhejein |
| `BACKUP_GZIP` | `True` | Compressed backups |
| `BACKUP_REMOTE_DIR` | *(khaali)* | Extra copy location (mounted disk/rclone) |

### Cookies (VPS/datacenter ke liye recommended)
| Variable | Description |
| :--- | :--- |
| `COOKIES_FILE` | `cookies.txt` (Netscape format) — **`.gitignore` me hai, GitHub par nahi jaayega** |
| `COOKIES_B64` | cookies.txt ka base64 (Heroku/Railway ke ephemeral FS ke liye) |
| `COOKIES_CONTENT` | raw netscape content |
| `COOKIES_URL` | [batbin.me](https://batbin.me) raw URL(s) |

Baaki saari options `sample.env` me comment ke saath di hui hain.

---

## 🕹️ Commands (61 total)

### 🎵 Playback
| Command | Description |
| :--- | :--- |
| `/play <naam/url>` (reply bhi) | Audio play |
| `/vplay <naam/url>` | Video play |
| `/playforce` `/vplayforce` | Queue skip karke turant play |
| `/pause` `/resume` | Pause / Resume |
| `/skip` `/next` | Next track |
| `/stop` `/end` | Stop + VC se leave |
| `/seek <sec>` `/seekback <sec>` | Aage / peeche |
| `/loop <1-10\|off>` | Repeat count |
| `/queue` `/playing` | Queue dikhayein |

### 🛡️ Admin
`/auth` `/unauth` `/authlist` `/admincache` `/reload` `/playmode` `/settings`
`/blacklist` `/unblacklist` `/whitelist` `/broadcast` `/addsudo` `/delsudo` `/listsudo` `/sudolist` `/eval` `/exec`

### 📝 Logs & Info
`/logs` `/logger on|off` `/restart` `/stats` `/ping` `/alive` `/ac` `/activevc` `/id` `/chatid` `/uptime` `/sysinfo` `/lang` `/language`

### 🗄️ Database & Backup
| Command | Access | Description |
| :--- | :--- | :--- |
| `/backup` | sudo | Turant snapshot + Telegram par |
| `/backups` | sudo | Saare backups + system status |
| `/restore` | owner | Backup file par reply → database restore |
| `/dbstatus` | sudo | Storage engine status (Firebase/local) |
| `/syncdb push\|pull\|reconnect` | owner | Manual Firebase sync |

### 🧩 Plugins & Misc
`/plugins` `/plugin list|scan|reload|enable|disable <name>` `/maintenance on|off` `/start` `/help`

---

## 🧩 Plugin System

`plugins/` folder me koi bhi `.py` file daal do — bot start hote hi **auto-load** ho jaayegi.
Koi import likhne ki zaroorat nahi (`app`, `db`, `config`, `logger`, `queue`, `yt`, `filters`,
`types` sab automatically available hote hain):

```python
# plugins/my_feature.py
@command(["hello", "hi"], description="Namaste bolta hai")
async def hello(_, message):
    await message.reply_text("Namaste! 👋")

@on_message(filters.regex("^pingme$"))
async def pingme(_, message):
    await message.reply_text("pong 🏓")
```

Runtime me manage karein:
```text
/plugins                     → saare plugins + status
/plugin scan                 → naye files dhoondo aur load karo
/plugin reload my_feature    → hot reload (bot restart ki zaroorat nahi)
/plugin disable my_feature   → band karein
```

---

## 📦 Backup Kaise Kaam Karta Hai (Step by Step)

1. **Save:** har change (lang, auth, sudo, blacklist, loop, chat) turant local mirror me
   atomically likha jaata hai + Firebase configured ho to cloud par sync hota hai.
2. **Auto snapshot:** har `BACKUP_INTERVAL_HOURS` ghante me
   `data/backups/database_backup_auto_YYYYMMDD_HHMMSS.json.gz` banta hai.
3. **Telegram delivery:** snapshot seedha aapke `LOGGER_ID` group me document ban kar bhejta hai.
4. **Retention:** sirf last `MAX_BACKUPS_RETAINED` snapshots rakhte hain (purane auto-delete).
5. **Restore:** `/restore` ke saath backup file par reply karein — pre-restore safety snapshot
   bhi automatically ban jaata hai.

---

## 🐛 Troubleshooting

| Problem | Solution |
| :--- | :--- |
| `Missing required environment variables` | `sample.env` → `.env` copy karke saari values bharein |
| Assistant VC join nahi karta | Assistant account group me add + admin banayein, VC start ho |
| `No active Voice Chat found` | Group me Voice Chat start karein, phir `/play` |
| YouTube download fail / bot check | `cookies.txt` update karein ya `COOKIES_B64` set karein |
| Firebase connect nahi ho raha | Bot Local VPS mode me chala jaayega (data safe). `/dbstatus` se error dekhein |
| Backup LOGGER_ID par nahi aa raha | Bot ko log group me **admin** banayein + `BACKUP_TO_LOGGER=True` |
| `/logs` fail | Bot ko LOGGER_ID me admin banayein, ya `LOG_FILE` path check karein |
| Commands missing | `/plugin scan` chalayein aur `/logs` dekhein |

---

## 📁 Repo Structure

```text
Music-x-bot/
├── main.py              # ⭐ sab kuch: engine + 27 plugins + helpers + locales + fonts
├── requirements.txt     # clean dependency list
├── sample.env           # saari env variables (copy → .env)
├── setup                # automated VPS setup script
├── start                # bot starter
├── Dockerfile           # docker deployment
├── Procfile             # Heroku-style worker
├── plugins/             # auto-load folder (README + example plugin)
├── locales/             # (optional) custom translations yahan rakhein
├── data/                # runtime: database.json + backups/  (gitignored)
└── cookies.txt          # (aap rakhein) — .gitignore me hai, push nahi hoga
```

---

## 🙏 Credits & License

- Single-file edition: **pm169298-boop**
- Base architecture: **AnonXMusic / LunaXMusicBot** — © 2025 [AnonymousX1025](https://github.com/AnonymousX1025) (MIT)
- License: **MIT** (dekhein [LICENSE](LICENSE))
