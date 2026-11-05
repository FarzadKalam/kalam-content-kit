# مهارت‌های SVG، HTML و حرکت کلام

جست‌وجو: ۲۰۲۶-۱۱-۰۵؛ ادغام snapshotهای ثابت: ۲۰۲۶-۱۱-۰۶. این انتقال، دانش و فایل‌های مهارت را به کیت اضافه می‌کند؛ ساخت ویدیو، اجرای generator یا آزمون کیفیت خروجی تصویری در این تغییر انجام نشده است.

## دو بستهٔ نصب‌شده

| بسته | منبع و نسخهٔ ثابت | محتوای منتقل‌شده |
| --- | --- | --- |
| GSAP Skills رسمی | [GreenSock](https://github.com/greensock/gsap-skills/tree/aed9cfd3277740755f6bfc1155c7aa645403b760)، commit `aed9cfd3277740755f6bfc1155c7aa645403b760` | هشت SKILL.md اصلی در `.agents/skills/gsap-*`، متن `llms.txt` و مجوز کامل MIT؛ ۱۰ فایل و ۹۶٬۷۵۰ بایت |
| MengTo Illustration | [MengTo/Skills](https://github.com/MengTo/Skills/tree/5ea1661a0e05d82b054553daaa6baf6d0233c33c/agent-skills/illustration)، commit `5ea1661a0e05d82b054553daaa6baf6d0233c33c` | همهٔ ۱۴ سبک، ۴۲ نمونهٔ SVG، تمام drawing kitها، generatorها، craft references، style.jsonها، PROMPTها و metadata عامل، به‌علاوهٔ فهرست، تصویر مقایسهٔ سبک‌ها و مجوز MIT؛ ۱۶۱ فایل و ۵٬۵۲۵٬۳۸۶ بایت |

برای MengTo، همهٔ سبک‌ها حفظ شدند چون انتخاب سبک، قواعد craft و مرجع‌های سبک‌های همسایه به آن‌ها وابسته‌اند. `demo/index.html`های حجیم که نمونه‌های SVG را دوباره inline کرده‌اند و ۱۴ فایل `demo/preview.jpg` تکراری منتقل نشدند؛ منابع طراحی، اسکریپت، prompt و SVG حذف نشدند. هیچ مهارت vendored قبلی جایگزین نشده است.

دانلود از raw فایل‌های commit ثابت انجام شد؛ قبل از نوشتن، Git blob SHA هر فایل با tree همان commit مقایسه شد. بایت‌های اصل با UTF-8 حفظ و SHA-256 مقصد در دو ورودی `gsapSkills` و `mengtoIllustration` در `vendor/manifest.json` ثبت شدند. قالب `files: [{path, sha256}]` با validator موجود سازگار است.

## فعال‌سازی و ساختار

- `$illustration-kalam` یا `.agents/skills/illustration-kalam/SKILL.md` برای انتخاب سبک SVG، ترکیب‌بندی HTML و تطبیق با هویت کلام.
- `$gsap-kalam` یا `.agents/skills/gsap-kalam/SKILL.md` برای حرکت نرم، easing، timeline و تایپوگرافی جنبشی فارسی.
- ورودی‌های `.agents/skills/illustration-<style>/SKILL.md` برای فراخوانی سبک مشخص؛ هرکدام به بستهٔ کامل اصلی در `vendor/mengto-illustration/illustration-<style>` متصل‌اند. [فهرست سبک‌ها](../../vendor/mengto-illustration/README.md) و تصویر مقایسه در همان پوشه موجودند.

ساختار مهارت‌های محلی با discovery پوشه‌ای `SKILL.md` سازگار است. فهرست مهارت‌های یک نشست ممکن است تا نوبت بعد به‌روز نشود؛ در همین نشست می‌توان مسیر دقیق را خواند. همراه‌بردن صرف SKILL.md کافی نیست: vendor، references، kitها، نمونه‌ها، مجوز و manifest نیز باید با کیت منتقل شوند.

هشت entrypoint اصلی MengTo در این commit، `description` حاوی `: ` بدون quote دارند و YAML معتبر نیستند: `bold-pop`، `flat`، `flat-with-black`، `isometric-mono`، `outlined-cartoon`، `teal-spot`، `two-colour-brush` و `vintage-emblem`. این یک خطای واقعی upstream است، نه placeholder یا خطای تشخیص validator. اصل همهٔ ۱۴ سبک دست‌نخورده در vendor نگه داشته شد؛ ۱۴ wrapper محلی با YAML معتبر discovery را انجام می‌دهند. مسیرهای داخلی هر دستور upstream باید نسبت به پوشهٔ خودش در vendor حل شوند.

## سازگاری اجرا

مهارت‌های رسمی GSAP دستور فنی می‌دهند؛ runtime موجود پروژه `gsap: 3.15.0` است. استفاده از افزونه ابتدا به موجودبودن همان افزونه در نسخهٔ نصب‌شده وابسته است. مجوز MIT مهارت از [مجوز runtime GSAP](https://gsap.com/community/standard-license/) جداست. در این انتقال dependency یا موتور عوض نشده است.

راهنمای عمومی GSAP با قرارداد HyperFrames تطبیق داده می‌شود: timeline متوقف، ثبت پس از ساخت کامل، زمان قطعی و تکرار محدود؛ مثال‌های خودپخش، scroll، clock واقعی یا حلقهٔ مستقل وارد فیلم نمی‌شوند. روایت، SFX و زمان خواندن از سفارش می‌آیند. SplitText حرف‌به‌حرف برای فارسی پیش‌فرض نیست؛ واحد معنایی، اتصال حروف، نیم‌فاصله، RTL و policy فونت برند حفظ می‌شوند. متن تأییدشده و هویت واقعی تابع قواعد کلام باقی می‌مانند.

کیت‌های هندسی و lintهای MengTo با Node محلی کار می‌کنند؛ renderer آن‌ها Playwright/Chromium می‌خواهد که وجود Puppeteer اثبات نصبش نیست. در Windows از `CHROME_PATH` یا browser موجود استفاده شود؛ کشف خودکار مسیرها عمدتاً برای macOS/Linux نوشته شده است. wrapperهای محلی اجازهٔ نصب global یا اجرای بی‌نسخهٔ فرمان‌های نصب موجود در متن upstream نمی‌دهند. می‌توان برای مشاهده از رندر محلی موجود HyperFrames استفاده کرد. دستورهای Bash در صورت استفاده به PowerShell ترجمه شوند و generator/خروجی داخل سفارش بماند.

## حرکت نرم و kinetic و گزینه‌های بعدی

ترکیب `gsap-core`، `gsap-timeline` و `gsap-plugins` همراه راهنمای motion و registry موجود، مسیر فعلی حرکت نرم و تایپوگرافی جنبشی است: easing مناسب، فرود روشن، stagger عبارتی، overlap کنترل‌شده و مکث خواندن. نصب بستهٔ سوم برای این هدف لازم نیست.

[mblode/ui-animation](https://github.com/mblode/agent-skills/tree/main/skills/ui-animation) با مجوز MIT برای تشخیص حرکت ضعیف، اندازه‌گیری easing از ویدیوی مرجع و جزئیات SVG ارزش تکمیلی دارد؛ نصب نشده است. [Impeccable](https://github.com/pbakaus/impeccable) با مجوز Apache-2.0 برای critique، typeset و polish HTML گزینهٔ اختیاری آینده است؛ launcher و نیازهای اجرایی مستقل دارد و نصب نشده است. مهارت UI/UX موجود، logo-design و registry نیز حفظ می‌شوند؛ تصویرسازی صحنه با کیت MengTo و طراحی حرکت با GSAP به آن‌ها افزوده شده‌اند.

## مدرک بررسی

- دریافت و Git blob hash: passed؛ همهٔ ۱۷۱ فایل upstream از commit ثابت و بدون اجرای کد نصب یا اسکریپت‌های upstream دریافت شدند.
- `quick_validate.py` رسمی skill-creator: اجرای مستقیم ابتدا به علت نبود PyYAML متوقف شد. سپس PyYAML 6.0.3 از wheel با SHA-256 تأییدشده فقط در حافظه بارگذاری شد؛ نصب یا تغییر Python انجام نشد. بررسی اصل upstream، هشت خطای YAML یادشده را آشکار کرد و مبنای ساخت wrapperها شد.
- `quick_validate.py` نهایی: passed برای هر ۲۴ ورودی قابل کشف؛ شامل هشت مهارت رسمی GSAP، چهارده wrapper تصویرسازی و دو router محلی. PyYAML فقط در حافظه بود؛ هیچ نصب dependency انجام نشد.
- SHA-256: passed برای هر ۱۷۱ فایل بسته‌های جدید؛ مقایسهٔ ساختاری manifest با HEAD نیز حفظ تمام ورودی‌های قبلی را تأیید کرد.
- UTF-8 سخت‌گیرانه، مسیر لینک‌های محلی wrapperها و routerها و XML هر ۴۲ SVG نمونه: passed. این‌ها بررسی ساختار و بسته‌بندی‌اند؛ نتیجهٔ تولید/رندر/شنیدن ویدیو از آن‌ها استنباط نشود.
