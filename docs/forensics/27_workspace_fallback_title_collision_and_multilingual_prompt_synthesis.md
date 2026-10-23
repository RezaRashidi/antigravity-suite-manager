# Issue 25: Workspace Fallback Title Collision & Investigation of Direct Q&A Conversations

## ۱. مشخصات رخداد و خلاصه شواهد عینی
در سیستم همگام‌ساز تاریخچه چت‌ها (`history merger`)، دو گفتگوی زیر مورد بررسی و رفع اشکال قرار گرفتند:

### چت اول: `e069face-57b3-48ee-9745-449f02f17aab`
* **عنوان اصیل (تولید شده توسط مدل / کاربر):** `"How To Fork A Chat"`
* **ورک‌اسپیس:** `Odirect`
* **عنوان تحریف‌شده در سایدبار و دیتابیس‌ها:** `"Odirect Chat"`
* **رفتار:** با وجود آنکه عنوان معتبر `"How To Fork A Chat"` برای این چت وجود داشت، موتور مرجر در هر دوره سینک آن را نادیده گرفته و به نام پوشه ورک‌اسپیس جاری (`"Odirect Chat"`) تبدیل می‌کرد.

### چت دوم: `421402e0-384e-4cd0-a196-0bec02aa6bdc`
* **پرامپت کاربر:** `"من می خوام چند مودم را با کابل به سیستم وصل کنم چطوری می تونم با سوییچ میشه"`
* **عنوان ثبت‌شده در مرجر:** `".Antigravity Suite Manager Chat"`
* **رفتار:** این گفتگو فاقد فایل آرتیفکت مارک‌داون در دایرکتوری `brain` و فاقد گام ۲۳ چک‌پوینت بود و عنوان آن به نام ورک‌اسپیس پروژه تبدیل شده بود.

---

## ۲. ریشه‌یابی فنی و سناریوی باگ‌ها

### الف) ریشه‌یابی باگ عنوان در چت `e069face` (باگ `endswith(" Chat")`)
در پیاده‌سازی قبلی، فیلتر تشخیص عنوان موقت ورک‌اسپیس به صورت زیر نوشته شده بود:
```python
is_fb = s.endswith(" Chat")
```
و در ماژول‌های `checkpoint_sync.py`، `extractor_text.py` و `item_persistence.py`:
```python
if cand.endswith(" Chat"):
    cand = ""
```
**سناریوی شکست:**
1. عنوان معتبر این چت `"How To Fork A Chat"` بود که کلمه آخر آن `"Chat"` است.
2. شرط `s.endswith(" Chat")` مقدار `True` برگرداند.
3. در نتیجه، مرجر این عنوان معتبر را به عنوان یک عنوان پیش‌فرض نامعتبر تلقی کرد و آن را رد صلاحیت نمود (`cand = ""`).
4. مرجر به اولویت fallback سقوط کرد و نام پوشه ورک‌اسپیس (`Odirect`) را برداشته و عنوان `"Odirect Chat"` را تولید و در دیتابیس‌ها ثبت کرد.

### ب) بررسی علت عدم ایجاد مارک‌داون در چت `421402e0`
بررسی دقیق فایل‌های لاگ `transcript_full.jsonl` و ساختار ذخیره‌سازی Antigravity نشان داد:
1. **طبیعت آرتیفکت‌های مارک‌داون در معماری Antigravity:**
   - فایل‌های مارک‌داون در مسیر `~/.gemini/antigravity/brain/<uuid>/` (مانند `task.md`، `implementation_plan.md`، `architecture.md`) صرفاً زمانی ایجاد می‌شوند که ایجنت در جریان کدنویسی یا برنامه‌ریزی از ابزار `write_file` برای ذخیره آرتیفکت استفاده کند.
   - پرامپت کاربر در چت `421402e0` یک سوال فنی و مکالمه‌ای کوتاه در مورد شبکه در لینوکس (اتصال چند مودم با سوییچ) بوده است.
   - بر اساس پرامپت سیستمی مدل:
     > *"Don't use artifacts for: Simple one-off answers or very short paragraph content - just respond directly"*
   - بنابراین، در مکالمات مستقیم و پرسش‌وپاسخ‌های فنی بدون تولید کد یا سند، عدم وجود فایل مارک‌داون در پوشه `brain` رفتاری **کاملاً طبیعی و مطابق طراحی استاندارد** سیستم است (مشابه مستند فورنزیک شماره ۱۲: `12_ide_vs_app_title_discrepancy_language_server.md`).

### ج) علت عدم تولید گام ۲۳ چک‌پوینت توسط Language Server برای چت `421402e0`
1. در حالت عادی، پس از ارسال اولین پیام کاربر، سرویس Language Server در بک‌گراند فرآیند تولید عنوان با هوش مصنوعی را اجرا کرده و نتیجه را در `annotations/<uuid>.pbtxt` و `state.vscdb` ثبت می‌کند.
2. با بررسی لاگ زمانی در تاریخ `2026-10-22 22:21:43`، مشخص شد که در همان گام اول (`Steps: 1`) و قبل از پاسخ کامل مدل و Language Server، دیمن همگام‌ساز پس‌زمینه (`antigravity-sync.service`) یک دور اجرا شده است.
3. مرجر چت جدید را بدون عنوان دیده و بلافاصله عنوان موقت ورک‌اسپیس (`".Antigravity Suite Manager Chat"`) را در فایل `annotations/421402e0.pbtxt` نوشت.
4. هنگامی که Language Server برای تعیین عنوان به فایل annotation مراجعه کرد، دید که فیلد `title` قبلاً پر شده است؛ در نتیجه فرض کرد که کاربر شخصاً عنوان را تنظیم کرده و فرآیند تولید عنوان LLM (گام ۲۳) را لغو کرد!

### د) چرایی غلط بودن روش `synthesize_topic_from_prompt`
- تلاش قبلی برای برش دادن و سنتز پرامپت فارسی/انگلیسی با عبارات منظم (`synthesize_topic_from_prompt`):
  1. باعث نشت تکه‌هایی از پرامپت خام کاربر به عنوان می‌شد.
  2. روی جملات مختلف شکننده بود و با رفتار سیستم همخوانی نداشت.
  3. بنا به دستور صریح کاربر، این روش به طور کامل حذف شد.

---

## ۳. معماری راه‌حل قطعی (Deterministic Constructible Fallback)

به جای استفاده از روش‌های حدسی NLP یا استاپ‌وردهای زبانی، منطق سیستم بر اساس **شناخت دقیق عناوینی که کد می‌تواند برای این چت بسازد** پیاده‌سازی شد:

### ۱. محاسبه عناوین قابل ساخت برای هر ورک‌اسپیس ([title_fallback.py](file:///home/reza/.antigravity-suite-manager/src/antigravity_suite/history/title_fallback.py))
تابع `get_constructible_fallback_titles(workspace)` دقیقاً عناوینی را که خود مرجر ممکن است بر اساس نام ورک‌اسپیس چت بسازد محاسبه می‌کند:
- برای چت `e069face` با ورک‌اسپیس `Odirect`، مجموعه عناوین قابل ساخت شامل موارد زیر است:
  `{"odirect chat", "odirect", "conversation", "untitled conversation", "new chat", "chat"}`
- تابع `is_workspace_fallback_title(title, fallback_workspace)` بررسی می‌کند که آیا عنوان کاندید جزو این مجموعه قابل ساخت است یا خیر:
  - عنوان `"Odirect Chat"` در این مجموعه است $\rightarrow$ رد می‌شود (عنوان بازگشتی است).
  - عنوان `"How To Fork A Chat"` در این مجموعه **نیست** $\rightarrow$ به عنوان عنوان اصیل پذیرفته می‌شود!

### ۲. حذف کامل ماژول ساختگی `title_topic.py`
- فایل `src/antigravity_suite/history/title_topic.py` به طور کامل حذف گردید.
- کلیه وابستگی‌های آن در [title_sanitizer.py](file:///home/reza/.antigravity-suite-manager/src/antigravity_suite/history/title_sanitizer.py) و [title_resolver.py](file:///home/reza/.antigravity-suite-manager/src/antigravity_suite/history/title_resolver.py) پاکسازی شد.

### ۳. رعایت سقف سخت‌گیرانه خطوط کد (حداکثر ۱۰۰ خط)
- تمام فایل‌های کدی ایجاد یا اصلاح‌شده در کل مخزن (`src/`، `bin/`، `scripts/`) زیر ۱۰۰ خط هستند.

---

## ۴. نتایج اعتبارسنجی و تست‌ها

۱. **تست‌های واحد رگرسیون:**
   - فایل تستی [tests/test_title_fallback_constructible.py](file:///home/reza/.antigravity-suite-manager/tests/test_title_fallback_constructible.py) اجرا شد و صحت تفکیک عناوین اصیل خاتمه‌یافته با کلمه `Chat` تایید شد.
   - اجرای ۱۶۸ تست کل پروژه (`pytest tests/`) با موفقیت ۱۰۰٪ پاس شد.

۲. **بررسی عدم وجود فایل کدی بالای ۱۰۰ خط:**
   - دستور `find src bin scripts -type f \( -name "*.py" -o -name "*.sh" \) -exec wc -l {} + | awk '$1 > 100 && $2 != "total"'` هیچ خروجی نداد (۰ فایل).
