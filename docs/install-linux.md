# نصب لینوکس

هدف پشتیبانی: Linux x64 با glibc (مانند Ubuntu 22.04/24.04)، Node.js حداقل۲۲٫۱۲، Git و Chrome/Chromium موجود. نصب خود مرورگر یا کتابخانه‌های سیستم به دست مدیر همان سیستم انجام می‌شود؛ این کیت sudo یا نصب سراسری خودکار ندارد. Alpine/musl و Linux ARM در این مرحله تست‌شده نیستند.

```bash
git clone <private-repository-url> kalam-video-kit
cd kalam-video-kit
bash scripts/setup.sh
# اختیاری:
bash scripts/setup.sh --with-remotion
npm test
npm run validate
npm run doctor
```

FFmpeg و FFprobe برای سیستم جاری از dependencyهای pinشده نصب می‌شوند؛ node_modules ویندوز را به لینوکس منتقل نکن. lockfile هر دو سیستم مشترک است. اگر مرورگر در مسیر معمول نیست، `export KALAM_BROWSER_PATH=/absolute/path/to/chrome` را قبل از setup بده. Chrome به کتابخانه‌های سیستم و sandbox سالم نیاز دارد؛ خطای sandbox مجوز اجرای خودکار به‌صورت root یا غیرفعال‌کردن آن نیست.

پوشهٔ ریپو باید قابل نوشتن باشد و برای cache، dependency، مدل و رندر فضا داشته باشد. فایل‌های موقت و کش زیر `.cache`، محیط اختیاری ASR و سفارش‌ها زیر `.local` هستند. در لینوکس قاعدهٔ درایو D معنی ندارد؛ همهٔ فضای کاری در مسیر همان checkout می‌ماند. برای سیستم دوگانه، checkout/dependency جدا برای هر OS و انتقال خصوصی پوشهٔ سفارش پیشنهاد می‌شود؛ لینک node_modulesِ Remotion مربوط به OS قبلی را منتقل نکن.

ASR اختیاری، Python3.11+ با venv لازم دارد:

```bash
bash scripts/setup-asr.sh
.local/asr-venv/bin/python scripts/transcribe.py .local/projects/job/analysis/speech.wav --output .local/projects/job/analysis/transcript.json
```

نصب اولیه و دانلود مدل به اینترنت نیاز دارند؛ رندر ورودی شخصی محلی است. CI برای Windows و Ubuntu تعریف شده، اما نتیجهٔ واقعی هر اجرا باید در GitHub بررسی شود؛ تعریف job جای تست موفق لینوکس نیست. شواهد در `verification.md` ثبت می‌شوند.
