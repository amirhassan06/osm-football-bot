# ⚽ OSM Football Bot — Telegram

بات مدیریت فوتبال مثل OSM روی Cloudflare Workers + D1

---

## 📁 ساختار فایل‌ها

```
osm_bot/
├── wrangler.toml              ← تنظیمات Cloudflare
├── migrations/
│   ├── 0001_init.sql          ← ساخت جداول
│   └── 0002_seed.sql          ← داده اولیه (auto-generated)
├── data/
│   └── players_template.csv  ← template داده بازیکنان
├── scripts/
│   └── csv_to_sql.py         ← تبدیل CSV به SQL seed
└── src/
    ├── index.py               ← entry point (webhook handler)
    ├── db.py                  ← توابع دیتابیس D1
    ├── simulator.py           ← موتور شبیه‌ساز بازی (Poisson)
    ├── keyboards.py           ← Inline keyboards تلگرام
    └── messages.py            ← پیام‌های متنی
```

---

## 🚀 مراحل Deploy

### ۱. پیش‌نیازها

```bash
npm install -g wrangler
wrangler login
```

### ۲. ساخت D1 database

```bash
wrangler d1 create osm_football
```

خروجی یه `database_id` میده — اون رو توی `wrangler.toml` بذار:
```toml
[[d1_databases]]
database_id = "xxxx-xxxx-xxxx"
```

### ۳. اجرای migration (ساخت جداول)

```bash
wrangler d1 execute osm_football --file=migrations/0001_init.sql
```

### ۴. آماده‌سازی داده بازیکنان

فایل `data/players_template.csv` رو ویرایش کن یا با داده‌های خودت جایگزین کن.

ستون‌های مورد نیاز:
```
name, position, rating, age, club_name, league_name, league_country
```

**position** باید یکی از این باشه: `GK`, `DEF`, `MID`, `ATT`

### ۵. تبدیل CSV به SQL و اجرا

```bash
python3 scripts/csv_to_sql.py data/players_template.csv > migrations/0002_seed.sql
wrangler d1 execute osm_football --file=migrations/0002_seed.sql
```

### ۶. تنظیم متغیرهای محیطی

توی داشبورد Cloudflare (Settings → Variables) یا:

```bash
wrangler secret put BOT_TOKEN
# وارد کن: توکن بات تلگرامت

wrangler secret put WEBHOOK_SECRET
# وارد کن: یه رشته رندوم مثل: myS3cr3tKey2025
```

### ۷. Deploy

```bash
wrangler deploy
```

آدرس Worker چیزی شبیه اینه:
```
https://osm-football-bot.<your-subdomain>.workers.dev
```

### ۸. ثبت Webhook تلگرام

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook\
?url=https://osm-football-bot.<subdomain>.workers.dev/webhook\
&secret_token=<YOUR_WEBHOOK_SECRET>"
```

---

## 🎮 ویژگی‌های MVP

| ویژگی | وضعیت |
|-------|--------|
| ثبت‌نام و انتخاب تیم | ✅ |
| نمایش ترکیب (Squad) | ✅ |
| تنظیم تاکتیک و فرمیشن | ✅ |
| شبیه‌سازی بازی (Poisson) | ✅ |
| جدول لیگ (Standings) | ✅ |
| برنامه بازی‌ها | ✅ |
| سیستم Training | ✅ |
| مارکت ترانسفر | ✅ |
| Manager Points | ✅ |
| Stamina بازیکنان | ✅ |

---

## ⚙️ الگوریتم شبیه‌ساز

```
xG هر تیم = (قدرت حمله / دفاع حریف) × ضریب تاکتیک × مزیت خانگی

تاکتیک‌ها:
  attacking  → حمله ×1.25 | دفاع ×0.85
  balanced   → حمله ×1.00 | دفاع ×1.00
  defensive  → حمله ×0.80 | دفاع ×1.20
  counter    → حمله ×0.95 | دفاع ×1.05
  possession → حمله ×1.10 | دفاع ×1.05

گل‌ها از توزیع Poisson سمپل می‌شوند
Stamina < 30% → عملکرد بازیکن کاهش پیدا می‌کنه
```

---

## 📊 ارزش‌گذاری بازیکنان

```python
value = rating² × age_factor × 1500
age_factor = 1 - |age - 27| × 0.035
```

بازیکن ۲۴ ساله با rating 85 ≈ €9.5M

---

## 🔧 افزودن لیگ/بازیکن جدید

CSV جدید آماده کن و مجدد اجرا کن:
```bash
python3 scripts/csv_to_sql.py data/new_players.csv >> migrations/0002_seed.sql
wrangler d1 execute osm_football --file=migrations/0002_seed.sql
```

---

## 🛣 نقشه راه V2

- [ ] سیستم Scout (جستجوی بازیکن با فیلتر)
- [ ] AI Transfer بین تیم‌های کامپیوتری
- [ ] جام حذفی (Cup)
- [ ] Achievements و badges
- [ ] آمار تاریخچه سیزن‌ها
