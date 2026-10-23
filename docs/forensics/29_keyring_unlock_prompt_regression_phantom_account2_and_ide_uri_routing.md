# Issue 27: GNOME Keyring Unlock Prompt Regression, Phantom Account 2 Isolation & IDE URI Routing

## ۱. مشخصات رخداد و نشانه‌ها
پس از پیاده‌سازی و استقرار پچ‌های سوئیت منیجر، سه رفتار غیرمنتظره توسط کاربر گزارش شد:
1. **درخواست رمز عبور گنوم پس از ریستارت (Keyring Unlock Prompt):**
   با اینکه کاربر وضعیت کی‌رینگ را روی حالت «Normal File Storage» (بدون استفاده از GNOME Keyring) تنظیم کرده بود، پس از ریستارت سیستم با باز کردن اپلیکیشن دسکتاپ پنجره مشهور گنوم ظاهر شده و تقاضای پسورد دسته‌کلید ورودی (`Enter password to unlock your login keyring`) می‌کرد.
2. **باز شدن پوشه به عنوان فایل تکی در دکمه Open in IDE:**
   هنگام فشردن دکمه «Open IDE» در برنامه اصلی، به جای آنکه Antigravity IDE پوشه پروژه را به عنوان یک Workspace باز کند، آن را به عنوان یک فایل متنی تکی باز می‌کرد و تبی با نام پوشه ایجاد می‌نمود.
3. **نمایش فانتوم اکانت ۲ (Phantom Account 2):**
   در جدول کنترل‌سنتر (`manage-antigravity.sh`) و منوی کی‌رینگ، نمونه `[3] Antigravity (Account 2)` نمایش داده می‌شد در حالی که کاربر هرگز اکانت دومی نصب نکرده بود و هیچ لانچر یا فایل دسکتاپی برای آن وجود نداشت.

---

## ۲. ریشه‌یابی فنی (Root Cause Analysis)

### الف) ریشه‌یابی پرامپت پسورد کی‌رینگ پس از ریستارت
مهندسی معکوس باینری هسته گوگل (`/opt/Antigravity-x64/resources/bin/language_server`) و ماژول فرانت‌اند نشان داد:
1. **باینری زبان گوگل (`language_server` کامپایل شده با Go):**
   این باینری برای مدیریت احراز هویت از پکیج `github.com/zalando/go-keyring` استفاده می‌کند. باینری یک گیت کنترلی داخلی دارد:
   مسیر کش (`~/.gemini/cache/`) را بررسی می‌کند؛ اگر فایلی به نام `antigravity-keyring-unavailable` در آن وجود نداشته باشد، باینری به صورت پیش‌فرض فرض می‌کند که دسته‌کلید سیستمی در دسترس است و مستقیماً از طریق D-Bus متد `secret_service.GetLoginCollection` و `Unlock` را صدا می‌زند.
2. **قفل بودن کی‌رینگ در استارت‌آپ دسکتاپ:**
   در لینوکس پس از ریستارت، تا قبل از اولین لاگین معتبر با PAM، کی‌رینگ گنوم قفل است. بنابراین درخواست D-Bus باینری گوگل بلافاصله دیالوگ گرافیکی Unlock Prompt را روی صفحه پرتاب می‌کرد.
3. **ناپایداری فایل نشانگر کش:**
   اسکریپت‌های راه‌اندازی اولیه اپلیکیشن (`instance_app.sh`) و دستورات پاک‌سازی کش، فایل `~/.gemini/cache/antigravity-keyring-unavailable` را ایجاد نمی‌کردند یا در زمان پاک‌سازی کش آن را حذف می‌کردند. در غیاب این فایل، باینری گوگل فوراً به سراغ گنوم کی‌رینگ می‌رفت.
4. **فال‌بک در ماژول چند اکانته (`router/accounts.js`):**
   تابع `readTokenFromKeyring()` در صورت عدم وجود مستقیم توکن، به عنوان فال‌بک متد پایتونی `keyring_dbus.py` را فراخوانی می‌کرد که متد `Secret.Prompt` را برای باز کردن قفل ارسال می‌نمود.

### ب) ریشه‌یابی باگ دکمه Open IDE
کد بومی دکمه در برنامه گوگل به این صورت است:
```javascript
var e = c ? `antigravity-ide://file${c}` : "antigravity-ide://?windowId=_blank";
```
1. وقتی این پروتکل به لینوکس فرستاده می‌شد، لینوکس آن را به فایل دسکتاپ `antigravity-ide.desktop` و نهایتاً به لانچر `~/.local/bin/antigravity-ide %U` تحویل می‌داد.
2. لانچر نیز کل این رشته پروتکل (`antigravity-ide://file/path/to/folder`) را مستقیماً به باینری هسته IDE (بر پایه VS Code) تحویل می‌داد.
3. پروتکل هندلر درونی VS Code یعنی `vscode://file/...` منحصراً برای «باز کردن یک فایل متنی» در ادیتور برنامه‌نویسی شده است؛ بنابراین وقتی مسیر یک دایرکتوری به آن داده می‌شد، آن را به عنوان یک فایل در تب ویرایشگر باز می‌کرد، در حالی که اگر مسیر یک پوشه بدون پیشوند URL به باینری تحویل داده شود، VS Code آن را به عنوان یک Project Workspace باز می‌کند.

### ج) ریشه‌یابی تشخیص فانتوم اکانت ۲
1. در تاریخ ۲۲ اکتبر، اجرای دستور `antigravity-keyring.py set all normal` باعث فراخوانی تابع `apply_mode_for_app2` در `keyring_apply.py` شده بود.
2. این تابع بدون اینکه بررسی کند آیا اکانت ۲ واقعاً نصب شده یا خیر، پوشه `~/.antigravity-profile2/.gemini/cache` را با `os.makedirs` ایجاد کرده بود.
3. سپس اسکنر کنترل‌سنتر (`clones_scan_app.py`)، منوی کی‌رینگ (`keyring.sh`) و جدول وضعیت کی‌رینگ (`keyring_status.py`) شرط شناسایی را صرفاً به صورت `if os.path.isdir(acc2_profile)` قرار داده بودند و هیچ تاییدیه‌ای برای وجود فایل لانچر `antigravity-acc2` یا فایل دسکتاپ آن نمی‌گرفتند.

---

## ۳. اقدامات اصلاحی و پیاده‌سازی (Engineering Solutions)

### ۱. اصلاح قطعی مشکل کی‌رینگ در لایه لانچرها
- در قالب لانچر اپلیکیشن ([`app_launcher.sh`](file:///home/reza/.antigravity-suite-manager/bin/lib/sh/app_launcher.sh)) و IDE ([`ide_launcher.sh`](file:///home/reza/.antigravity-suite-manager/bin/lib/sh/ide_launcher.sh)) و لانچرهای فعال سیستم، تضمین شد که در صورت فعال بودن حالت Normal، قبل از اجرای باینری برنامه، فایل مارکر `antigravity-keyring-unavailable` در مسیرهای کش بررسی و ساخته شود. بنابراین `language_server` در بدو شروع متوجه غیرفعال بودن کی‌رینگ شده و هرگز درخواستی به D-Bus ارسال نمی‌کند.
- در ماژول [`keyring_dbus.py`](file:///home/reza/.antigravity-suite-manager/src/antigravity_suite/auth/keyring_dbus.py) فراخوانی اینتراکتیو دیالوگ قفل با آرگومان پیش‌فرض `interactive: bool = False` مسدود شد.
- در ماژول [`router/accounts.js`](file:///home/reza/.antigravity-suite-manager/bin/lib/patch/router/accounts.js) بررسی گارد مارکر قرار گرفت تا از فراخوانی بیهوده کی‌رینگ جلوگیری شود.

### ۲. تصحیح هندلر ورودی دکمه Open IDE
- در لانچر [`antigravity-ide`](file:///home/reza/.local/bin/antigravity-ide) و ژنراتور آن [`ide_launcher.sh`](file:///home/reza/.antigravity-suite-manager/bin/lib/sh/ide_launcher.sh)، منطق استخراج و دیکود مسیر قرار گرفت:
```bash
IDE_ARGS=()
for arg in "$@"; do
    if [[ "$arg" == antigravity-ide://file/* ]]; then
        tgt="${arg#antigravity-ide://file}"
        IDE_ARGS+=("$(printf '%b' "${tgt//%/\\x}")")
    elif [[ "$arg" == "antigravity-ide://?windowId=_blank" ]]; then
        IDE_ARGS+=("--new-window")
    else
        IDE_ARGS+=("$arg")
    fi
done
```
با این تغییر، مسیر دایرکتوری به طور تمیز و استاندارد به باینری تحویل داده شده و IDE آن را به عنوان ورک‌اسپیس کامل پروژه باز می‌کند.

### ۳. حذف کامل اکانت ۲ فانتوم و سخت‌گیرانه کردن شروط شناسایی
- در [`clones_scan_app.py`](file:///home/reza/.antigravity-suite-manager/src/antigravity_suite/detect/clones_scan_app.py)، [`instance_list.py`](file:///home/reza/.antigravity-suite-manager/bin/lib/sh/instance_list.py)، [`status_env_inspect.py`](file:///home/reza/.antigravity-suite-manager/bin/lib/sh/status_env_inspect.py) و [`keyring_status.py`](file:///home/reza/.antigravity-suite-manager/src/antigravity_suite/auth/keyring_status.py) شرط احراز هویت اکانت ۲ به صورت زیر اصلاح شد:
```python
acc2_exists = (os.path.isfile(acc2_lnch) or os.path.isfile(acc2_dt) or acc2_run) and os.path.isdir(acc2_profile)
```
- در اسکریپت اینتراکتیو [`keyring.sh`](file:///home/reza/.antigravity-suite-manager/bin/lib/sh/keyring.sh)، تا زمانی که اکانت ۲ واقعاً نصب نشده باشد، گزینه‌های مربوط به آن مخفی شده و منو تنها برای App اصلی و IDE نمایش داده می‌شود.
- پوشه باقیمانده و بی‌استفاده `~/.antigravity-profile2` از دیسک پاک‌سازی شد.

---

## ۴. اعتبارسنجی و تست‌ها
- ایجاد تست‌های واحد جامع در [`tests/test_keyring_and_clone_detection.py`](file:///home/reza/.antigravity-suite-manager/tests/test_keyring_and_clone_detection.py).
- اجرای موفقیت‌آمیز تمامی ۱۷۲ تست سوئیت (`172 passed in 10.09s`).
- بررسی و تایید قانون حداکثر ۱۰۰ خط کد برای تمامی فایل‌های پایتون و شل پروژه (`0 files > 100 lines`).
