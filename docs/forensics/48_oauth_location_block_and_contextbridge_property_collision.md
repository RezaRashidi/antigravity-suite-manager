# Case 48: OAuth Location Block & ContextBridge Property Collision

## ۱. مشخصات رخداد و خلاصه شواهد عینی
کاربر پس از آخرین ری‌استارت نرم‌افزار Antigravity با دو رخداد بحرانی مواجه شد:
۱. **درخواست لاگین مداوم (Login Loop):** برنامه پس از باز شدن مرتباً نشست کاربر را نامعتبر دانسته و پنجره ورود را مجدداً باز می‌کرد.
۲. **خطای مسدودیت مکانی روی تمام اکانت‌ها (Unsupported Location):** با ورود با هر اکانت مجاز دیگری (از جمله `reza202501`، `ali.morgan1243` و `shakhinsta97`)، با خطای زیر متوقف می‌شد:
> `Sorry, this account is ineligible to use Antigravity. Your current account is not eligible for Antigravity, because it is not currently available in your location. Learn more by visiting our FAQ.`

با وجود اینکه ریجن و مشخصات سایر اکانت‌ها معتبر و مجاز بود، ارور لوکیشن بر روی همه آن‌ها بازتولید می‌شد.

---

## ۲. ریشه‌یابی دقیق فنی و شواهد در کدهای سیستم

### الف) تله جایگزینی توکن در `server.js` و قفل شدن روی اکانت نامعتبر (علت خطای Location)
در کامیت `ba6aa64d`، لیست متدهای تحت پوشش `isAccountRpc` در `bin/lib/patch/router/server.js` توسعه یافته بود:
```javascript
const isAccountRpc = req.url && (
    isGen ||
    req.url.includes('retrieveUserQuota') ||
    req.url.includes('fetchAvailableModels') ||
    req.url.includes('loadCodeAssist') ||     // <-- ریشه باگ
    req.url.includes('fetchUserInfo') ||      // <-- ریشه باگ
    req.url.includes('listModelConfigs')
);
```

#### نحوه عملکرد باگ:
1. متد `loadCodeAssist` یک درخواست احراز هویت اولیه در سطح سیستم (Bootstrap/Handshake) است که Language Server بلافاصله پس از لاگین کاربر یا بالا آمدن نرم‌افزار به سمت سرور گوگل ارسال می‌کند تا مجاز بودن نشست فعلی و Tier کاربر را بررسی کند.
2. چون درخواست `loadCodeAssist` مربوط به هیچ چت یا Cascade خاصی نیست (`cascadeId == null`)، روتر به تابع `getActiveAccountEmail()` رجوع می‌کرد.
3. در فایل `bindings.json`، اکانت فعال سیستم روی `aiyearreza@gmail.com` قرار داشت. این اکانت از سمت سرورهای گوگل دارای فلگ `UNSUPPORTED_LOCATION` در آرایه `ineligibleTiers` بود.
4. هر زمان کاربر در مرورگر با اکانت جدید و معتبری لاگین می‌کرد، Language Server توکن تازه آن اکانت را برای `loadCodeAssist` ارسال می‌کرد.
5. روتر لوپ‌بک (`server.js`) توکن جدید را دور می‌انداخت و هدر `Authorization` را با توکن اکانت معیوب (`aiyearreza`) بازنویسی می‌کرد!
6. در نتیجه گوگل خطای عدم پشتیبانی مکانی اکانت را بازمی‌گرداند، انتی‌گرویتی نشست کاربر را ابطال می‌کرد و کاربر را دوباره به صفحه لاگین بازمی‌گرداند. بدین ترتیب **هیچ اکانت دیگری هم امکان ورود پیدا نمی‌کرد**.

#### راه‌حل اعمال‌شده:
حذف اندپوینت‌های زیرساختی `loadCodeAssist` و `fetchUserInfo` از لیست `isAccountRpc`. این درخواست‌ها اکنون مستقیماً با همان توکن بومی نشست لنگویج‌سرور (`Native LS Session`) به گوگل ارسال می‌شوند.

---

### ب) کرش زنجیره‌ای در Preload الکترون (علت درخواست لاگین مداوم)
در پچ `patch_open_ide.js` و فایل `preload.js`، کدی برای بازنویسی ویژگی `window.ide` در Isolated World 0 تزریق شده بود:
```javascript
if (typeof window !== 'undefined') {
    let _i = window.ide;
    Object.defineProperty(window, 'ide', {
        configurable: true, enumerable: true,
        get() { return _i || { isInstalled: async () => true }; },
        set(val) { ... }
    });
}
```

#### نحوه عملکرد باگ:
1. در الکترون، متد بومی `contextBridge.exposeInMainWorld(key, api)` وظیفه ارتباط امن بین فرایند رندر و هسته الکترون را بر عهده دارد.
2. چنانچه کلید مدنظر (در اینجا `'ide'`) قبلاً توسط اسکریپت رندر روی شیء `window` تعریف شده باشد، موتور الکترون با پرتاب استثنای غیرقابل بازگشت زیر متوقف می‌شود:
   `Error: Cannot bind an API on top of an existing property 'ide'`
3. این ارور در خط ۱۶۱ فایل `preload.js` رخ می‌داد و باعث می‌شد اجرای ادامه اسکریپت لغو شود.
4. در نتیجه خطوط بعدی، به ویژه تعریف واسط `antigravityMultiAccount` (در خط ۲۱۱۴) هرگز اجرا نمی‌شد و UI چت امکان برقراری ارتباط با سیستم چنداکانته و اعتبارسنجی ورود را از دست می‌داد.

#### راه‌حل اعمال‌شده:
حذف کامل تعریف پیش‌رس `Object.defineProperty(window, 'ide')`. قابلیت دکمه Open IDE کماکان بدون تداخل از طریق قلاب `Map.prototype.get/set` روی `titlebarComponent` فعال باقی ماند.

---

### ج) شناسایی نشدن توکن اصلی سیستم در `accounts.js` و `vault.py`
فایل توکن اختصاصی انتی‌گرویتی در نسخه ۲.۲۴ در مسیر `~/.gemini/jetski-standalone-oauth-token` فیلد ایمیل را با کلید `id_token_email` ذخیره می‌کند و فاقد کلید `email` یا JWT خام `id_token` است.

1. کدهای قبلی فقط `d.email` را جستجو می‌کردند؛ بنابراین اکانت اصلی سیستم (`reza202501@gmail.com`) در لیست اکانت‌ها نادیده گرفته می‌شد و صفت `is_primary: true` دریافت نمی‌کرد.
2. با اضافه شدن پشتیبانی از `d.id_token_email` در `accounts.js` و `vault.py`، و اصلاح تابع `getActiveAccountEmail` در `bindings.js` برای ترجیح دادن اکانت `is_primary`، اکانت پیش‌فرض سیستم پایدار و معتبر شد.

---

## ۳. نتایج اعتبارسنجی و وضعیت فعلی

1. **تست‌های پایتون:** تمام ۲۳۲ تست موجود در سوئیت (`pytest`) با موفقیت پاس شدند.
2. **تست‌های نود (Node):** فایل `tests/test_router_quota_routing.js` ایزوله شده و با خروج پاکیزه کد ۰ پاس شد.
3. **وضعیت کدهای برنامه اصلی:** فایل `/opt/Antigravity-x64/resources/app.asar` با نسخه‌های اصلاح‌شده `dist/preload.js` و `dist/router/server.js` به‌روزرسانی شد.
4. **بررسی ترافیک زنده (`traffic.log`):**
   - فراخوانی `loadCodeAssist` با موفقیت از مسیر `ControlPlane -> Native LS Session` به جای توکن‌های اشتباهی عبور می‌کند.
   - نشست‌های چت و تولید محتوا (`ChatGen`) با کد HTTP 200 بدون قطعی در جریان هستند.
   - وضعیت سهمیه‌ها (`QUOTA`) برای هر ۴ اکانت فعال به‌صورت نرمال گزارش می‌شود.
5. **محدودیت خطوط فایل‌ها:** تمامی فایل‌های `.py` و `.sh` در محدوده استاندارد (زیر ۱۰۰ سطر) تأیید شدند.
