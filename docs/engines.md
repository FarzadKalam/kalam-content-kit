# دو موتور، یک قرارداد برند و کیفیت

HyperFrames پیش‌فرض است: HTML/CSS، GSAP و قابلیت‌های محلی سازگار، یک timeline متوقف و seek-safe، صحنه‌های ماژولار. مثال در `examples/hyperframes/` و مهارت‌های فنی در `.agents/skills/` هستند. قبل از نوشتن افکت نام‌دار، `npm run hf -- catalog --query <effect> --json` را ببین. بعد `check`، `snapshot` با `--describe false` برای اجتناب از تحلیل ابری ناخواسته، preview و render.

Remotion اختیاری است: مناسب وقتی کامپوننت React، مرجع Remotion یا ترکیب‌های داده‌محور آن مزیت واقعی دارند. همهٔ پکیج‌های Remotion باید یک نسخه داشته باشند. هر فریم با `useCurrentFrame()` و `useVideoConfig()` ساخته می‌شود؛ CSS animation، زمان دیواری و تصادف بدون seed مرجع رندر نیستند. دارایی‌ها در `public/assets`، فونت با `@font-face` محلی، ابعاد و FPS از Composition و زمان‌ها بر حسب فریم.

برای ساخت پروژهٔ Remotion، در `project.json` engine را انتخاب کن و دستورهای README همان پروژه را اجرا کن. wrapper مسیر مرورگر موجود و concurrency=1 را تنظیم می‌کند. هیچ مرورگر تازه‌ای روی C دانلود نمی‌شود؛ اگر Chrome/Edge پیدا نشد کار متوقف و مسیر خواسته می‌شود.

## مجوز استفادهٔ تیمی

طبق [صفحهٔ رسمی مجوز Remotion](https://www.remotion.dev/docs/license/pricing) در بررسی ۲۰۲۶-۱۱-۰۱، مجوز رایگان افراد و شرکت‌های حداکثر سه‌نفره را پوشش می‌دهد؛ شرکت بزرگ‌تر باید شرایط Company License را بررسی کند. این تعداد صرفاً تعداد تدوین‌گرهای این ریپو نیست. نصب کیت مجوز سازمانی نمی‌سازد؛ تا روشن‌شدن وضعیت تیم، HyperFrames مسیر پیش‌فرض بدون خرید Remotion است. هیچ خرید یا API پولی با setup انجام نمی‌شود.

منابع اصلی: [HyperFrames](https://github.com/heygen-com/hyperframes)، [مهارت رسمی Remotion](https://www.remotion.dev/docs/ai/skills)، [رندر Remotion](https://www.remotion.dev/docs/render). فایل‌های راهنمای upstream با منبع و hash در `vendor/manifest.json` بسته‌بندی شده‌اند؛ برای به‌روزرسانی، snapshot را در یک تغییر مجزا عوض و مثال‌ها را دوباره check/render کن.
