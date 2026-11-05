# بررسی مهارت‌های خبریاب

پژوهش مستقلِ ایجنت به درخواست مالک در ۲۰۲۶-۱۱-۰۶ انجام شد؛ هیچ بسته‌ای نصب یا اجرا نشد. مهارت‌های واقعی وجود دارند، ولی هیچ‌یک از گزینه‌های بررسی‌شده خبر فوری و کم‌اشباع از تمام سایت‌ها/تلگرام/اینستاگرام/X را بدون اتصال اضافی تضمین نمی‌کند.

| گزینه | ارزش واقعی | محدودیت برای کلام |
| --- | --- | --- |
| [last30days](https://github.com/mvanhorn/last30days-skill/blob/f01a451a5aa745cd1af4497fb7d79e171917364e/skills/last30days/SKILL.md) — MIT | discovery چندمرحله‌ای، کشف نامزد، داوری میزبان، تحقیق و زاویهٔ محتوا | جریان عمومی عمدتاً Reddit/HN/Digg؛ تلگرام فقط کانال‌های نام‌برده با کلید ScrapeCreators؛ Instagram/TikTok هم اتصال خارجی می‌خواهند |
| [fetch-news رسمی گوگل](https://github.com/google-gemini/gemini-managed-agents-templates/blob/f08a04605b1e70f9110f313b979f2012fa728622/news-curator/skills/fetch-news/scripts/fetch_news.py) — Apache-2.0 | دریافت RSS، حذف تکرار و خوراک انتخاب تحریریه | locale آمریکایی و بدون فیلتر سخت خبر فوری؛ تازه برای سابقهٔ خودش با تازه‌منتشرشده یکی نیست |
| [BlogWatcher](https://github.com/Hyaxia/blogwatcher/tree/58acfeb16258bd0e64d72f8f977ae8143cae5fa3) — MIT | RSS/Atom، feed discovery و unread در SQLite | Go/CLI جدا؛ جستجوی عمومی سوشال و داوری خبری نیست |
| [NewsHub](https://github.com/RobinZorro86/newshub-skill/blob/b2cdaed1b09256486d580942fa52629a2359b896/scripts/newshub.py) — MIT | RSS/Atom، منابع YAML/OPML، سهمیهٔ منبع و حذف مشابه | منابع اولیه چینی/انگلیسی؛ امتیاز ساده و عبور خبر بی‌تاریخ از time filter برای فوریت مناسب نیست |
| [trend-radar](https://github.com/asoiso/trend-radar/blob/18aafe5230ff6e90fcae900c8fa1bcf9acd0e739/trend-monitor/SKILL.md) — Apache-2.0 | رصد مقایسه‌ای ترند میان پلتفرم‌ها | به MCP جدا وابسته و پوشش غالب چینی است؛ دستور مهارت به‌تنهایی داده فراهم نمی‌کند |

الگوی [discovery در last30days](https://github.com/mvanhorn/last30days-skill/blob/f01a451a5aa745cd1af4497fb7d79e171917364e/skills/last30days/references/discovery.md) مفید است، اما نصب کامل آن در کیت بدون کلید توصیه نشد: سطح اتصال/نشست گسترده، خواندن اختیاری cookie و مسیرهای سرویس ثالث دارد. در مرور محدودِ کدِ fetch-news، BlogWatcher و NewsHub رفتار آشکارِ سرقت credential دیده نشد؛ این بررسی ممیزی کامل امنیتی وابستگی‌ها نیست.

تصمیم فعلی: مهارت اختصاصی `kalam-news` روی وب واقعی میزبان و ثبت/پالایش/رتبه‌بندی محلی، با قواعد و منابع جستجوگر کلام. الگوی نامزدسازی → ارزیابی → خواندن منبع → بررسی پوشش → انتخاب حفظ می‌شود، بدون ادعای دسترسی سراسری سوشال. خبر کم‌پوشش با محدودهٔ واقعی مشاهده گزارش شود؛ چند بازنشر یک منشأ، چند تأیید مستقل نیستند. نصب هر گزینهٔ بعدی باید انتقال مستقل و بازبینی‌شده باشد.
