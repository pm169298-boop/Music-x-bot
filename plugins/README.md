# 🧩 Plugins Folder

Is folder me koi bhi `.py` file daalein — bot start hone par **automatic load** ho jaayegi.
Bot restart kiye bina bhi load kar sakte hain:

```text
/plugin scan              → naye plugins dhoondo aur load karo
/plugin reload <name>     → hot reload
/plugin disable <name>    → band karein
/plugins                  → saare plugins + status
```

## Koi import likhne ki zaroorat nahi

Plugin file me ye sab **pehle se available** hote hain:

`app` (bot client), `db` (hybrid database), `config`, `logger`, `lang`, `queue`, `yt`,
`tg`, `anon` (PyTgCalls), `thumb`, `userbot`, `buttons`, `utils`, `backup`,
`filters`, `types`, `enums`, `errors`, aur decorators: `command`, `on_message`, `callback`

## Example

`example.py` file dekhein:

```python
@command(["mycmd"], description="Mera custom command")
async def mycmd(_, message):
    await message.reply_text("Hello from plugin! 🎉")
```

### Permission levels

```python
@command(["owneronly"], owner=True)     # sirf bot owner
@command(["sudoonly"], sudo=True)       # owner + sudo users
@command(["adminonly"], admin=True)     # group admins
@command(["everyone"])                  # sab log
```

### Notes
- `_` se shuru hone wali files (`_helper.py`) load **nahi** hoti — unhe aap apne
  plugin ke sath import kar sakte hain.
- Ek plugin error de to bot nahi rukta: `/plugins` me ❌ ke saath error dikh jaayega.
