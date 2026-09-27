# 🎵 Music-x-bot (Telegram Voice Chat Music Bot)

Telegram Groups me high-quality music aur video stream karne ke liye ek powerful aur fast **Telegram VC Music Bot** (AnonX / LunaX architecture par based).

---

## 📖 Bot Ka Concept (Bot Kaise Kaam Karta Hai? / How It Works)

Telegram Voice Chat me music play karne ka process normal bots se thoda alag hota hai:

1. **Telegram Bot (`BOT_TOKEN`)**:
   - Ye wo bot hai jo `@BotFather` se banta hai (jaise `@your_music_bot`).
   - Ye group me users ke commands receive karta hai: `/play`, `/pause`, `/skip`, `/stop`, aur inline buttons dikhata hai.
2. **Assistant / Userbot (`SESSION` - String Session)**:
   - Telegram ke architecture me standard bots direct Voice Chat me bol ya gaana chala nahi sakte.
   - Isliye ek real Telegram account (Assistant Account) chahiye hota hai. Bot us account ke through Voice Chat me enter hota hai aur FFmpeg / Py-TgCalls ke zariye song stream karta hai.
3. **MongoDB Database (`MONGO_URL`)**:
   - Playlists, group settings, language preferences aur sudo users ka data MongoDB me save hota hai.
   - Iska free cluster `cloud.mongodb.com` par banta hai.
4. **Logger Group (`LOGGER_ID`)**:
   - Ek private Telegram group jahan Bot aur Assistant dono ko Admin banaya jata hai. Yahan bot start hone ka status, logs aur errors aate hain.

---

## 🔑 Zaroori Credentials (Prerequisites / Kya Kya Chahiye)

Bot run karne se pehle ye 7 cheezein nikaal kar rakh lein:

| Variable | Description | Kahan se milega? |
| :--- | :--- | :--- |
| **`API_ID`** | Telegram App ID (Integer) | [my.telegram.org](https://my.telegram.org) par login karke **API Development Tools** se lein. |
| **`API_HASH`** | Telegram App Hash (String) | [my.telegram.org](https://my.telegram.org) par API ID ke sath milega. |
| **`BOT_TOKEN`** | Telegram Bot Token | Telegram par [@BotFather](https://t.me/BotFather) ko `/newbot` bhej kar bot banayein aur token copy karein. |
| **`OWNER_ID`** | Aapka numeric Telegram User ID | Telegram par [@userinfobot](https://t.me/userinfobot) ko start karein, wo aapki numeric ID dega. |
| **`MONGO_URL`** | MongoDB connection string | [cloud.mongodb.com](https://cloud.mongodb.com) par free account banayein -> Free Cluster banayein -> `mongodb+srv://...` URL copy karein. |
| **`LOGGER_ID`** | Private Log Group ID | Telegram me ek private group banayein, usme Bot aur Assistant account ko add karke Admin banayein, fir group ID nikaalein (usually `-100...` se start hoti hai). |
| **`SESSION`** | Pyrogram v2 String Session | Telegram par [@StringFatherBot](https://t.me/StringFatherBot) ya Pyrogram generator se apne Assistant account ka session string banayein. |

---

## 🚀 Run Kaise Karein (Step-by-Step Deployment Guide)

### Tarika 1: VPS / Linux Server (Sabse Best & 24/7 Uptime)

Agar aapke paas Ubuntu/Debian VPS hai:

1. **Repository clone karein:**
   ```bash
   git clone https://github.com/pm169298-boop/Music-x-bot.git
   cd Music-x-bot
   ```

2. **Setup script chalayein:**
   ```bash
   bash setup
   ```
   *Ye script automatic Python, FFmpeg, Deno, uv aur sari dependencies install kar dega.*

3. **Credentials enter karein:**
   Setup ke end me aapse `API_ID`, `API_HASH`, `BOT_TOKEN`, `OWNER_ID`, `MONGO_URL`, `LOGGER_ID`, aur `SESSION` pucha jayega. Enter kar dein.

4. **Bot start karein:**
   ```bash
   bash start
   ```

5. **24/7 background me chalane ke liye (`tmux` ya `screen` use karein):**
   ```bash
   screen -S musicbot
   bash start
   # Screen detach karne ke liye: Ctrl + A fir D dabayein
   ```

---

### Tarika 2: Local PC (Windows / Linux / Mac)

1. **Prerequisites install karein:**
   - [Python 3.10+](https://www.python.org/downloads/)
   - [FFmpeg](https://ffmpeg.org/download.html) (System PATH me add hona zaroori hai)
   - Git

2. **Repo clone karein:**
   ```bash
   git clone https://github.com/pm169298-boop/Music-x-bot.git
   cd Music-x-bot
   ```

3. **Environment variables set karein:**
   - `sample.env` file ko copy karke `.env` naam dein:
     ```bash
     cp sample.env .env
     ```
   - `.env` file ko notepad/editor me open karein aur apni details fill karein:
     ```env
     API_ID=12345678
     API_HASH=abcdef1234567890abcdef1234567890
     BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
     OWNER_ID=123456789
     LOGGER_ID=-1001234567890
     MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
     SESSION=BQGabcdef...
     ```

4. **Dependencies install karein:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Ya agar `uv` use karte hain to: `uv sync`)*

5. **Bot start karein:**
   ```bash
   python3 -m anony
   ```
   *(Windows me: `python -m anony` ya `bash start`)*

---

### Tarika 3: Docker Deployment

1. `.env` file banayein aur usme apni values daalein.
2. Build aur Run karein:
   ```bash
   docker build -t musicbot .
   docker run -d --name musicbot --env-file .env musicbot
   ```

---

## 📱 Telegram Group Me Kaise Use Karein

Jab bot run ho jaye:

1. **Telegram par naya ya existing group kholein.**
2. **Voice Chat (Video Chat) start karein.**
3. **Bot ko group me invite karein aur Admin banayein** (Manage Voice Chats / Video Chats permission ON honi chahiye).
4. **Assistant account (jiska `SESSION` string banaya tha) ko group me add karein.**
5. **Group chat me command bhejein:**
   ```text
   /play Believer
   ```
   ya YouTube link:
   ```text
   /play https://www.youtube.com/watch?v=7wtfhZwyrcc
   ```
6. Bot gaana search karega, Assistant account Voice Chat me join karega, aur music stream hona shuru ho jayega! 🎶

---

## 🕹️ Useful Commands

| Command | Action |
| :--- | :--- |
| `/play <song name ya link>` | Voice chat me audio gaana play karega |
| `/vplay <song name ya link>` | Voice chat me video song play karega |
| `/pause` | Current gaana pause karega |
| `/resume` | Paused gaana resume karega |
| `/skip` | Agla gaana play karega (next in queue) |
| `/stop` | Gaana band karega aur assistant VC chhod dega |
| `/queue` | Queue me kaun-kaun se gaane hain list dikhayega |
| `/seek <seconds>` | Gaane ko aage ya peeche seek karega |
| `/ping` | Bot ka response time aur system status dikhayega |
| `/help` | Sabhi commands ki list dekhne ke liye |

---

## ⚠️ Common Problems & Fixes (Troubleshooting)

1. **`Bot has failed to access the log group` ya `Please promote the bot as an admin in logger group`:**
   - **Fix:** Aapne `LOGGER_ID` galat daala hai ya us private group me Bot ko add karke Admin nahi banaya. Make sure bot is an admin in that group.
2. **`Assistant failed to send message in log group`:**
   - **Fix:** Assistant account (jiski `SESSION` string hai) ko bhi us Logger Group me add karein.
3. **`Missing required environment variables`:**
   - **Fix:** `.env` file me 7 zaroori values me se koi chhoot gayi hai. `sample.env` check karein.
4. **Voice Chat me sound nahi aa rahi:**
   - **Fix:** Server par `ffmpeg` installed hai ya nahi check karein (`sudo apt-get install -y ffmpeg`). Group me voice chat active honi chahiye.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
