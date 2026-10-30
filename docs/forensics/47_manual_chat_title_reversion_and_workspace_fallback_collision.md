# Case 47: Manual Chat Title Reversion & Workspace Fallback Collision

## ۱. مشخصات رخداد و خلاصه شواهد عینی
کاربر گزارش داد که با ویرایش دستی عنوان چت‌ها در محیط Antigravity، پس از چند ثانیه سیستم مرجر عنوان را به حالت قبلی بازمی‌گرداند.
نمونه مورد بررسی:
- **شناسه گفتگو:** `1a1eb662-3ec5-408a-a7a3-a8260911711e`
- **ورک‌اسپیس:** `file:///home/reza/PhpstormProjects/Odirect`
- **عنوان تنظیم‌شده توسط کاربر:** `odirect`
- **عنوان بازگردانده‌شده توسط مرجر:** `Project Refactoring And Feature Organization`

---

## ۲. شواهد فورنزیک در لاگ‌های مرجر

بررسی فایل `history_merger_audit.log` در سطر ۵۳۱۳ رخداد زیر را به طور دقیق ثبت کرده بود:
```json
{
  "timestamp": "2026-10-30T09:48:47.382244+00:00",
  "run_id": "20261030_094847_319041",
  "type": "TITLE_CHANGED",
  "conv_id": "1a1eb662-3ec5-408a-a7a3-a8260911711e",
  "old_title": "Odirect",
  "new_title": "Project Refactoring And Feature Organization",
  "reason": "sync_sanitization",
  "is_suspicious": false,
  "anomalies": []
}
```

و در `history_sync_journal.log`:
```text
[2026-10-30 09:48:47] [1a1eb662] TITLE_UPDATED | Title: 'Odirect' -> 'Project Refactoring And Feature Organization' (via brain_artifact) | Partition: antigravity (unified_history) | Steps: 3033 | Stores: [sqlite,proto,vscdb,anno]
```

شواهد نشان داد که مرجر عنوان تنظیم‌شده کاربر (`Odirect`) را خوانده اما آن را به عنوان یک عنوان نامعتبر رد صلاحیت کرده و به `brain_artifact` (سرفصل استخراج‌شده از گام‌های چک‌پوینت) بازگردانده است.

---

## ۳. ریشه‌یابی فنی باگ‌ها (Technical Root Causes)

تحلیل عمیق سورس کد نشان داد ۳ باگ همزمان باعث این رفتار می‌شدند:

### باگ اول: اضافه شدن نام خام دایرکتوری پروژه به عناوین فال‌بک در `title_fallback.py`
در تابع `get_constructible_fallback_titles`:
```python
for ws in ws_list:
    raw_name = Path(ws).name.strip()
    clean_name = raw_name.replace("-", " ").replace("_", " ").strip().title()
    for variant in [raw_name, clean_name]:
        if variant:
            fallbacks.add(f"{variant.lower()} chat")
            fallbacks.add(variant.lower())  # <-- باگ اساسی
```
- خط `fallbacks.add(variant.lower())` نام خام پوشه ورک‌اسپیس (`odirect`) را وارد لیست سیاه عناوین خودکار (Fallback) می‌کرد!
- هنگامی که کاربر عنوان چت را به `odirect` تغییر داد، تابع `is_workspace_fallback_title("odirect", ws)` مقدار `True` برگرداند.
- مرجر فرض کرد که این عنوان صرفاً یک عنوان موقت سیستم است؛ بنابراین آن را دور انداخت و به سراغ آرتیفکت‌های قبلی در `brain/` رفت و عنوان طولانی چک‌پوینت را بازنویسی کرد.
- در واقع سیستم فقط باید عناوینی با الگوی `<Project> Chat` را به عنوان فال‌بک بشناسد، نه نام مستقیم پروژه را.

### باگ دوم: اولویت اشتباه کاندیداها در `resolver.py`
در تابع `resolve_conversation_item`:
```python
existing_candidates = [curr_title, meta["anno_title"], parsed_raw.get("title", "")]
```
- `curr_title` مقدار ذخیره‌شده در جدول دیتابیس SQLite از دوره‌های قبلی سینک بود.
- `meta["anno_title"]` مقدار فایل زنده روی دیسک در دایرکتوری `annotations/<conv_id>.pbtxt` بود (جایی که نرم‌افزار تغییرات دستی کاربر را ذخیره می‌کند).
- قرار گرفتن `curr_title` قبل از `meta["anno_title"]` باعث می‌شد حتی اگر کاربر عنوان را به عبارتی دیگر (مثلاً "توسعه درگاه") تغییر دهد، تابع `pick_first_valid_title` ابتدا مقدار قدیمی دیتابیس را برگزیند و عنوان جدید کاربر را در فایل annotation با مقدار قدیمی بازنویسی کند!

### باگ سوم: عدم پایش فایل‌های `annotations/*.pbtxt` در واچر و `is_item_clean`
- تابع `get_mtime_snapshot` در `watcher_targets.py` فایل‌های دایرکتوری `annotations` را پایش نمی‌کرد.
- تابع `is_item_clean` در `resolver_clean.py` نیز تغییرات عنوان فایل annotation نسبت به عنوان دیتابیس را بررسی نمی‌کرد؛ در نتیجه تغییرات کاربر به عنوان چت بلافاصله به عنوان رویداد کثیف (dirty) شناخته نمی‌شد تا در دیتابیس ثبت شود.

---

## ۴. معماری اصلاحات انجام‌شده

1. **حذف نام خام پروژه از فال‌بک‌ها در [title_fallback.py](file:///home/reza/.antigravity-suite-manager/src/antigravity_suite/history/title_fallback.py):**
   خط `fallbacks.add(variant.lower())` حذف شد تا فقط عناوینی که پسوند ` Chat` دارند و الگوهای جنریک موقت (مانند `Conversation` یا `Untitled Conversation`) به عنوان فال‌بک تلقی شوند.
2. **اصلاح اولویت کاندیداها در [resolver.py](file:///home/reza/.antigravity-suite-manager/src/antigravity_suite/history/resolver.py):**
   ترتیب کاندیداها به `[meta["anno_title"], curr_title, parsed_raw.get("title", "")]` تغییر یافت تا عنوان دستی کاربر در `annotations` همیشه بر کش قدیمی SQLite اولویت داشته باشد.
3. **تشخیص بلادرنگ ویرایش عنوان در [resolver_clean.py](file:///home/reza/.antigravity-suite-manager/src/antigravity_suite/history/resolver_clean.py):**
   بررسی شد که اگر عنوان موجود در فایل annotation با عنوان ثبت‌شده دیتابیس مغایرت داشته باشد (`clean_anno != title`)، بلافاصله گفتگو به عنوان dirty شناخته شده و رزولوشن اعمال شود.
4. **پایش `annotations/*.pbtxt` در [watcher_targets.py](file:///home/reza/.antigravity-suite-manager/src/antigravity_suite/history/watcher_targets.py):**
   فایل‌های annotation به اسنپ‌شات مانیتورینگ mtime دیمن واچر افزوده شدند.
5. **همگام‌سازی دوطرفه ویرایش در IDE در [vscdb_ingest.py](file:///home/reza/.antigravity-suite-manager/src/antigravity_suite/history/vscdb_ingest.py) و [vscdb_ingest_update.py](file:///home/reza/.antigravity-suite-manager/src/antigravity_suite/history/vscdb_ingest_update.py):**
   اگر عنوان در `state.vscdb` محیط IDE ویرایش شده باشد، با شرایط معتبر به عنوان تغییر جدید پذیرفته می‌شود.

---

## ۵. تست و اعتبارسنجی عملیاتی

1. **تست روی گفتگوی کاربر (`1a1eb662`):**
   عنوان به صورت دستی به `odirect` تغییر داده شد و عملیات سینک کامل انجام گرفت:
   ```text
   [2026-10-30 10:39:41] [1a1eb662] TITLE_UPDATED | Title: 'Project Refactoring And Feature Organization' -> 'odirect' (via existing_clean)
   [2026-10-30 10:39:53] [1a1eb662] SYNCHRONIZED  | Title: 'odirect' (via existing_clean)
   ```
   عنوان `odirect` در تمام استورها (`annotations`، `SQLite` و `state.vscdb`) تثبیت شد و در چرخه‌های متوالی واچر دست‌نخورده باقی ماند.
2. **اجرای تست‌های یونیت:**
   تست‌های اختصاصی `tests/test_title_fallback_constructible.py` اضافه شدند و تمامی ۲۳۱ تست با موفقیت پاس شدند.
3. **محدودیت خطوط:**
   تمام فایل‌های اصلاح‌شده به طور کامل زیر ۱۰۰ خط حفظ شدند.
