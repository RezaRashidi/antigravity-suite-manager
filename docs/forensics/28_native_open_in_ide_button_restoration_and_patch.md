# Issue 26: Native "Open in IDE" Titlebar Button Discovery, Reverse Engineering & Independent Patch

## ۱. مشخصات رخداد و هدف
در برنامه دسکتاپ Google Antigravity App (هاب)، کاربران در محیط گفتگو نیاز به دکمه‌ای جهت انتقال مستقیم ورک‌اسپیس یا سشن جاری به Antigravity IDE دارند.
هدف این بررسی دو موضوع بود:
1. ریشه‌یابی و پیدا کردن **دکمه اورجینال (Original Native Button)** در معماری و کدهای منبع فرانت‌اند/الکترون برنامه.
2. بررسی نحوه اتصال دکمه‌های تزریقی (نظیر دکمه RTL در پچ `antigravity-rtl`) و ایجاد یک **پچ مستقل، ماژولار و برگشت‌پذیر (دارای Unpatch و پشتیبانی از Update)** با رعایت سقف ۱۰۰ خط برای هر فایل.

---

## ۲. مهندسی معکوس و کشف دکمه اورجینال در باندل React

با مهندسی معکوس سرور `language_server` (پورت محلی `127.0.0.1:36781`) و فایل `main.js` فرانت‌اند به حجم ۹.۷ مگابایت، کامپوننت اورجینال React و پیاده‌سازی کامل آن استخراج شد:

### الف) کامپوننت اورجینال `vXb` (OpenEditorButtonBase)
کد کامپوننت در باندل فرانت‌اند Antigravity:
```javascript
function vXb({ showOpenIde: a, onOpenInIde: b }) {
    var c = tXb(), e = uXb(), f = OD();
    if (!a || e !== "installed") return null;
    if (c.length === 0) return A.createElement(A.Fragment, null,
        A.createElement(i4, { onClick: () => { b() }, "data-testid": "open-editor-empty", "data-tooltip-id": f }, "Open IDE"),
        A.createElement(jz, { id: f, delayShow: 300, place: "bottom-end" }, "Open Antigravity IDE")
    );
    if (c.length === 1) {
        let g = c[0];
        return A.createElement(A.Fragment, null,
            A.createElement(i4, { onClick: () => { b(g) }, "data-testid": "open-editor-single", "data-tooltip-id": f }, "Open IDE"),
            A.createElement(jz, { id: f, delayShow: 300, place: "bottom-end" }, "Open in Antigravity IDE")
        );
    }
    return A.createElement(A.Fragment, null,
        A.createElement(aM, null,
            A.createElement(bM, { asChild: !0 },
                A.createElement(i4, { "data-testid": "open-editor-multi", "data-tooltip-id": f },
                    A.createElement("span", null, "Open IDE"),
                    A.createElement(X, { name: "keyboard_arrow_down", size: 14 })
                )
            ),
            A.createElement(cM, { placement: "bottom-end", className: "min-w-[180px]" },
                c.map(g => A.createElement(dM, { key: g, value: g, onSelect: () => { b(g) } }, RC(g)))
            )
        ),
        A.createElement(jz, { id: f, delayShow: 300, place: "bottom-end" }, "Open in Antigravity IDE")
    );
}
```

### ب) هندلر کلیک و پروتکل اتصال به IDE در کامپوننت `DXb`
هنگام کلیک، تابع `DXb().handleOpenInIde` اجرا می‌شود:
```javascript
handleOpenInIde: (0, A.useCallback)(c => {
    b("open_editor_from_titlebar");
    c = c || "";
    c.startsWith("file://") && (c = c.substring(7));
    var e = c ? `antigravity-ide://file${c}` : "antigravity-ide://?windowId=_blank";
    a?.openExternal ? a.openExternal(e).catch(() => { vg(window, fg(e), "_blank") }) : vg(window, fg(e), "_blank")
}, [a, b])
```
این تابع با استفاده از Deep Link اختصاصی `antigravity-ide://file<path>` یا `antigravity-ide://?windowId=_blank` مستقیماً فایل یا پروژه را در Antigravity IDE باز می‌کند.

---

## ۳. علل پنهان بودن دکمه اورجینال (دو گیت مانع)

بررسی نشان داد دکمه به دو دلیل نمایش داده نمی‌شد:

1. **گیت اول: فلگ غیرفعال `showOpenIde: false` در کانتکست `titlebarComponent`**
   - در کامپوننت تایتل‌بار (`EXb`) مقدار ویژگی به صورت زیر پاس داده می‌شود:
     `showOpenIde: k?.showOpenIde === !0`
   - در پیکربندی پیش‌فرض سازنده برنامه، `titlebarComponent.feature.showOpenIde` برابر با `false` تنظیم شده است.

2. **گیت دوم: باگ مسیر نصب IDE در لینوکس (`ide:is-installed`)**
   - هوک `uXb` شرط `e === "installed"` را چک می‌کند که متکی به IPC هندلر `electron.ipcRenderer.invoke('ide:is-installed')` است.
   - در فایل `dist/ideInstall/constants.js` مسیر لینوکس به صورت هاردکد `~/.local/share/antigravity-ide` تعریف شده است، در حالی که در توزیع‌های لینوکس مسیر اصلی نصب `/opt/antigravity-ide` است!
   - در نتیجه `fs.stat` شکست خورده و `isInstalled` مقدار `false` برمی‌گرداند؛ بنابراین دکمه کامپوننت `vXb` همواره `null` برمی‌گرداند.

---

## ۴. مقایسه با روش پچ RTL

پچ `antigravity-rtl` با قرار دادن یک المان DOM ساختگی در کلاستر دکمه‌های هدر:
```javascript
const actionsCluster = document.querySelector('[data-testid="titlebar-more-actions"]')?.parentElement
    || document.querySelector('[data-testid="install-editor"]')?.parentElement;
actionsCluster.appendChild(widgetWrapper);
```
دکمه اختصاصی خود را تزریق می‌کرد.
در مقابل، راهکار اصولی کشف‌شده در این سند، **فعال‌سازی دکمه اورجینال و بومی React** است که قابلیت‌های کامل پشتیبانی از چند ورک‌اسپیس (منوی کشویی `open-editor-multi`)، آیکون، تولتیپ بومی و اتصال به پروتکل را به صورت بی‌نقص و طبیعی فراهم می‌کند.

---

## ۵. پیاده‌سازی پچ مستقل و ماژولار

پچ مستقل شامل فایل‌های زیر به صورت کاملاً ماژولار (همه زیر ۱۰۰ خط) پیاده‌سازی شد:

1. **ماژول پچ هسته ([patch_open_ide.js](file:///home/reza/.antigravity-suite-manager/bin/lib/patch/patch_open_ide.js)):**
   - هوک هوشمند `Map.prototype.get` و `Map.prototype.set` در `preload.js` (و World 0) جهت فعال‌سازی `titlebarComponent.showOpenIde = true`.
   - اصلاح مسیر بررسی نصب در `dist/ideInstall/constants.js` جهت پشتیبانی از `/opt/antigravity-ide`.
   - فال‌بک امن `window.ide.isInstalled`.
   - قابلیت Unpatch کامل و بدون اثر باقی‌مانده.

2. **اسکریپت‌های شل ([patch_open_ide.sh](file:///home/reza/.antigravity-suite-manager/bin/lib/sh/patch_open_ide.sh) و [unpatch_open_ide.sh](file:///home/reza/.antigravity-suite-manager/bin/lib/sh/unpatch_open_ide.sh)):**
   - استخراج، اعمال پچ جاوااسکریپت، ایجاد سیم‌لینک و پکینگ مجدد `app.asar`.
   - بازگردانی کامل به حالت اولیه در زمان Unpatch.

3. **یکپارچه‌سازی با CLI، منو، کنترل سنتر و آپدیت خودکار:**
   - دستورات CLI: `patch-open-ide` و `unpatch-open-ide`.
   - گزینه‌های ۳۶ و ۳۷ در منوی کلاسیک.
   - کلید `[Y]` در Antigravity Control Center.
   - تابع `HAD_APP_OPEN_IDE` در سیستم آپدیت جهت اعمال مجدد خودکار پچ در زمان آپدیت نسخه اپلیکیشن.

4. **اعتبارسنجی:**
   - تست واحد [tests/test_open_ide_patch.py](file:///home/reza/.antigravity-suite-manager/tests/test_open_ide_patch.py) با موفقیت اجرا شد.
   - تمامی ۱۶۹ تست پروژه پاس شدند.
   - کل فایل‌های کدی مخزن زیر ۱۰۰ خط تایید شدند.
