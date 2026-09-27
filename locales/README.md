# 🌍 Custom Locales (Optional)

Bot ke andar **13 languages** already embedded hain:

`ar`, `de`, `en`, `es`, `fr`, `hi`, `ja`, `my`, `pa`, `pt`, `ru`, `tr`, `zh`

Aapko kuch bhi copy karne ki zaroorat nahi — `/lang` command se language badal sakte hain.

## Custom translation kaise add karein?

1. Koi bhi embedded language ke keys dekhne ke liye `/lang` se language set karein,
   ya github par `main.py` me `_EMBEDDED_LOCALES` se keys nikaal lein.
2. Is folder me `<code>.json` file banayein, jaise `mr.json` (Marathi):

```json
{
  "start_pm": "👋 Namaskar {}! Main {} aahe.",
  "play_media": "🎶 <b>Vajat aahe:</b> <a href='{}'>{}</a>\n⏱️ {} | 👤 {}"
}
```

3. Jo keys aap nahi dete, unke liye automatically **English fallback** use hota hai —
   isliye aadhi-adhoori translation bhi chal jaati hai.
4. Bot restart karein — aapki file `<code>` ke roop me `/lang` menu me aa jaayegi
   (same code ka embedded locale override ho jaata hai).

> Notes: JSON me `{}` placeholders wahi rakhein jo original me hain (order important hai).
