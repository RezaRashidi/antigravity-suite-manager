# Forensic Investigation 18: IDE Chat Open Title Regression (Persian Greeting)

## ۱. مشخصات چت و خلاصه شواهد عینی
* **شناسه گفتگو:** `95ccec1a-a0ef-489f-9a34-55990309e128`
* **عنوان ثبت‌شده در اپ:** `Persian Greeting`
* **متن پرامپت اول کاربر:** `سلام`
* **رفتار:**
  - در اپلیکیشن دسکتاپ: عنوان پایدار و همیشه `Persian Greeting` است.
  - در IDE قبل از باز کردن چت: در لیست Recent، عنوان `Persian Greeting` است.
  - به محض باز کردن چت در IDE: عنوان بالای چت به `سلام` تغییر می‌کند و سپس در Recent هم `سلام` می‌شود.
  - با بستن و رفتن به اپلیکیشن: عنوان در اپلیکیشن دست‌نخورده و سالم است.

---

## ۲. ریشه‌یابی فنی دیتابیس و پروتوباف
۱. در `~/.gemini/antigravity/conversations/95ccec1a-a0ef-489f-9a34-55990309e128.db` فقط ۲ استپ وجود دارد:
   - گام ۰ (`step_type = 14` / `USER_INPUT`) شامل `Tag 19 -> Subtag 2 = "سلام"`.
   - گام ۱ (`step_type = 15` / `PLANNER_RESPONSE`) پاسخ مدل.
   - **هیچ گام ۲۳ (`CORTEX_STEP_TYPE_CHECKPOINT`) وجود ندارد.**
۲. در فرانت‌اند IDE (`jetskiAgent/main.js`):
   ```javascript
   _w = e => {
     let t = ers(e), r = M0s(e);
     return e ? t || r || "Untitled Conversation" : "";
   }
   ```
۳. به محض باز شدن چت، متد `createAgentStateProviderForConvo` استریم `streamAgentStateUpdates` را باز می‌کند.
   - پروسه `language_server` چون گام ۲۳ چک‌پوینت پیدا نمی‌کند، متن پرامپت خام گام ۰ (`"سلام"`) را در فیلد `summary` پکیج کرده و استریم می‌کند.
   - ردیوسر ریداکس IDE در `applyStreamBatch` آبجکت `summaries[cascadeId]` را با این مقدار جدید رونویسی می‌کند (`a[t] = r`).
   - در نتیجه هم هدر بالای چت (`_w`) و هم لیست Recent (`z5e`) فوراً به `"سلام"` جهش پیدا می‌کنند.

---

## ۳. بررسی گفتگوی ارجاع (`Simple Persian Greeting` با شناسه `c4ddc3ee`)
با بررسی گفتگوی جدیدی که مستقیماً در IDE با عنوان `Simple Persian Greeting` ایجاد شد (`c4ddc3ee-7c6e-44ee-9038-65e276ff4bb4`):
1. مشاهده شد که این گفتگو دارای **۵ استپ** است:
   - گام ۰ (`step_type = 14` / `USER_INPUT`: "سلام ۲")
   - گام ۱ (`step_type = 98` / `CONVERSATION_HISTORY`)
   - گام ۲ (`step_type = 99` / `KNOWLEDGE_ARTIFACTS`)
   - گام ۳ (`step_type = 15` / `PLANNER_RESPONSE`)
   - **گام ۴ (`step_type = 23` / `CHECKPOINT`):**
     دارای فیلد پروتوباف `Tag 30` شامل:
     - `Subtag 4`: رشته عنوان معتبر `Simple Persian Greeting`
     - `Subtag 9`: مقدار `1`
     - `Subtag 12`: شماره استپ `4`
     - `Subtag 19`: پرامپت کاربر `سلام ۲`
     - `Subtag 24`: مقدار `1`
     - `Subtag 25`: مقدار `0`
2. به دلیل وجود گام ۴ (`step_type = 23`)، هنگامی که چت در IDE باز می‌شود، لنگویج‌سرور عنوان تمیز را از `Tag 30 -> Subtag 4` خوانده و به عنوان `summary` می‌فرستد؛ بنابراین عنوان هرگز به متن پرامپت تغییر نمی‌کند.

---

## ۴. اصلاح موتور همگام‌ساز (Merger Engine Fix)
بدون نیاز به دستکاری کدهای IDE، موتور سینک در سورس کد مخزن به شرح زیر اصلاح شد:
1. ایجاد ماژول [checkpoint_sync.py](file:///home/reza/.antigravity-suite-manager/src/antigravity_suite/history/checkpoint_sync.py) جهت تولید پی‌لود باینری `build_step23_payload` و تزریق گام ۲۳ در دیتابیس‌های فاقد چک‌پوینت با متد `ensure_db_checkpoint_title`.
2. فراخوانی خودکار `ensure_db_checkpoint_title` در [item_persistence.py](file:///home/reza/.antigravity-suite-manager/src/antigravity_suite/history/item_persistence.py) به محض سینک گفتگو.
3. پشتیبانی از رونویسی و استخراج گام ۲۳ در [synthesizer_classify.py](file:///home/reza/.antigravity-suite-manager/src/antigravity_suite/history/synthesizer_classify.py) و [synthesizer_build.py](file:///home/reza/.antigravity-suite-manager/src/antigravity_suite/history/synthesizer_build.py).
4. پس از اجرای سینک، گام ۲۳ به دیتابیس `95ccec1a-a0ef-489f-9a34-55990309e128.db` اضافه شد و عنوان `Persian Greeting` به صورت پایدار و بدون پس‌رفت تثبیت گردید.
