# 🎵 Music-x-bot (All-in-One Single File Telegram VC Music Bot)

Telegram Groups ke Voice Chat / Video Chat me high-quality music aur video stream karne ke liye ek **Single-File (`main.py`) Telegram Music Bot**, jisme **Firebase Realtime Database** aur **Local VPS Storage + Automated Backup Mode** dono inbuilt hain!

---

## ✨ Features (Khaas Baatein)

- ⚡ **Single-File Code (`main.py`):** 80+ files ki jhanjhat khatam! Pura bot ek single, clean aur fully documented `main.py` file me chalte hai.
- 🗄️ **Hybrid Database System (Firebase + Local VPS):**
  - **Firebase Mode:** Agar aap `FIREBASE_DATABASE_URL` aur credentials dete hain, to data Firebase Realtime Database me cloud par save hota hai.
  - **Local VPS Backup Mode (Default):** Agar Firebase set nahi hai, to data automatically VPS par `data/database.json` me save hota hai.
- 📦 **Automated Backup System:**
  - VPS par har 6 ghante me auto-snapshot banta hai (`data/backups/`).
  - Auto-backup seedha aapke Telegram Log Group (`LOGGER_ID`) me send ho jata hai.
  - `/backup` command se Bot Owner kabhi bhi Telegram me latest database backup document mangwa sakta hai.
- 🎧 **Audio & Video Streaming:** YouTube se audio (`/play`) aur 720p HD video (`/vplay`) dono stream karta hai.
- 🎛️ **Inline Interactive Buttons:** Pause, Resume, Skip, Stop ke buttons gaana play hote waqt direct chat me aate hain.
- 🍪 **YouTube Cookies Support:** Datacenter IP blocking se bachne ke liye `cookies.txt` support.

---

## 🔑 Zaroori Credentials (Prerequisites / Kya Kya Chahiye)

### 1. Telegram Credentials (Mandatory)
| Variable | Description | Kahan se milega? |
| :--- | :--- | :--- |
| **`API_ID`** | Telegram App ID (Integer) | [my.telegram.org](https://my.telegram.org) par login karke **API Development Tools** se lein. |
| **`API_HASH`** | Telegram App Hash (String) | [my.telegram.org](https://my.telegram.org) par API ID ke sath milega. |
| **`BOT_TOKEN`** | Telegram Bot Token | Telegram par [@BotFather](https://t.me/BotFather) se `/newbot` bhej kar banayein. |
| **`SESSION`** | Pyrogram v2 String Session | Telegram par [@StringFatherBot](https://t.me/StringFatherBot) par apne Assistant account ka session generate karein. |
| **`OWNER_ID`** | Aapka Telegram numeric User ID | Telegram par [@userinfobot](https://t.me/userinfobot) ko `/start` karein. |
| **`LOGGER_ID`** | Private Log Group ID | Ek private Telegram group banayein, Bot aur Assistant dono ko Admin banayein, fir group ID lein (e.g. `-100...`). Yahan auto-backups aayenge! |

### 2. Database Options (Firebase ya Local VPS)
- **Option 1 (Firebase):** Agar cloud database chahiye to Firebase Console me Realtime Database banayein aur `.env` me `FIREBASE_DATABASE_URL` aur Service Account key (`firebase_key.json` ya raw JSON string) set karein.
- **Option 2 (Local VPS with Auto-Backup):** Kuchh set karne ki zaroorat nahi! Agar Firebase variables blank hain, to bot automatically VPS pe local storage mode me chalega aur backups banata rahega.

---

## 🚀 Setup & Run Kaise Karein

### Tarika 1: Automated VPS Setup (Recommended)

Agar aapke paas Ubuntu/Debian VPS hai:

1. **Repo clone karein:**
   ```bash
   git clone https://github.com/pm169298-boop/Music-x-bot.git
   cd Music-x-bot
   ```

2. **Setup script chalayein:**
   ```bash
   bash setup
   ```
   *Ye script Python3, FFmpeg, pip packages install karega aur aapse values puch kar `.env` file automatic bana dega.*

3. **Bot start karein:**
   ```bash
   bash start
   ```
   ya direct:
   ```bash
   python3 main.py
   ```

4. **24/7 background me chalane ke liye:**
   ```bash
   screen -S musicbot
   python3 main.py
   ```
   *(Screen detach karne ke liye keyboard par `Ctrl + A` fir `D` dabayein).*

---

### Tarika 2: Manual PC / Server Setup

1. **Prerequisites:** Python 3.10+ aur FFmpeg install karein.
2. **Dependencies install karein:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configuration file (.env) banayein:**
   `sample.env` ko copy karke `.env` banayein:
   ```bash
   cp sample.env .env
   ```
   Aur apni details daalein:
   ```env
   API_ID=12345678
   API_HASH=abcdef1234567890abcdef1234567890
   BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
   SESSION=BQGabcdef...
   OWNER_ID=123456789
   LOGGER_ID=-1001234567890

   # Firebase (Optional - Chhod sakte hain agar local VPS save chahiye)
   FIREBASE_DATABASE_URL=
   FIREBASE_CREDENTIALS=firebase_key.json
   ```
4. **Run karein:**
   ```bash
   python3 main.py
   ```

---

### Tarika 3: Docker Deployment

```bash
docker build -t musicbot .
docker run -d --name musicbot --env-file .env musicbot
```

---

## 🎮 Telegram Group Me Kaise Use Karein

1. Group me **Voice Chat (Video Chat)** start karein.
2. Apne **Bot** aur **Assistant Account** dono ko group me add karein aur Bot ko **Admin** banayein.
3. Group me command bhejein:
   ```text
   /play Kesariya
   ```
   ya video ke liye:
   ```text
   /vplay https://www.youtube.com/watch?v=BddP6PYo2gs
   ```
4. Assistant account Voice Chat join karega aur gaana bajne lagega!

---

## 🕹️ Commands List

| Command | Action |
| :--- | :--- |
| `/play <song/link>` | Voice chat me audio play karega |
| `/vplay <song/link>` | Voice chat me video play karega |
| `/pause` | Current gaana pause karega |
| `/resume` | Paused gaana resume karega |
| `/skip` | Agla gaana play karega |
| `/stop` ya `/end` | Gaana band karke Assistant ko VC se bahar nikal dega |
| `/queue` | Upcoming gaano ki list dikhayega |
| `/ping` | Bot ka latency aur response time check karega |
| `/stats` | System CPU, RAM, Total songs played aur active database mode dikhayega |
| `/backup` | **(Owner only)** Latest database backup file Telegram chat me bhej dega |

---

## 📦 Backup Mode Kaise Kaam Karta Hai?

1. **Auto-Save:** Har command, naya chat aur song count local file `data/database.json` me turant atomically save hota hai taaki crash hone par bhi file corrupt na ho.
2. **Scheduled Backups:** Har 6 ghante me ek naya timestamped snapshot `data/backups/database_backup_YYYYMMDD_HHMMSS.json` ban jata hai aur agar `LOGGER_ID` set hai, to seedha Telegram logger group me document ban kar send ho jata hai.
3. **Manual Backup (`/backup`):** Bot owner kisi bhi waqt bot ko `/backup` bhej kar instant backup file mangwa sakta hai.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
