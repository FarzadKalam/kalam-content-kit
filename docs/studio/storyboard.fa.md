# استوری‌بورد تصویری و اجازهٔ رندر

کارگردان تدوین پیش از رندر نهایی متن مصوب، رسانه‌های تمام نماها، صوت لازم و موسیقی را کنترل می‌کند. از ترکیب واقعی snapshot یا still بگیر؛ این پیش‌نمایش فنی مجاز است ولی تصویر مولد تازه، برنامه و تأیید مستقل تصویر می‌خواهد. HyperFrames snapshot با `--describe false` و Remotion still اجرا شوند. پیش‌نمایش استوری‌بورد خروجی نهایی نیست.

فریم‌های نمایندهٔ همهٔ صحنه‌ها و حالت‌های مهم را باز کن: حروف کامل از جمله کلاه آ، جای متن در بالا/وسط/پایین امن، هویت، سایه هم‌رنگ، قاب‌های متنوع عکس، crop، SVG و میانهٔ ورود/خروج. sheet خلاصه است؛ برای حروف و mask فریم اصلی پُروضوح را هم ببین. موشن مستقل با صدای خاموش باید تمام محتوا را برساند و زیرنویس جدا لازم ندارد؛ ویدیوی دارای گفتار زیرنویس همگام و موشن می‌خواهد. این کنترل معنایی و تصویری با hash خودکار انجام نمی‌شود.

## برنامه و نسخه

عامل JSON زیر را به فایل‌های واقعی و تمام صحنه‌های سفارش تبدیل می‌کند؛ placeholder مدرک نیست:

```json
{
  "copy": {"file": "script.md", "approvalReference": "مرجع واقعی متن مصوب یا گفتار اصلی دریافت‌شده"},
  "media": [{"file": "assets/photo.png", "usage": "تصویر مستند نمای اول"}],
  "narration": {"mode": "file", "file": "assets/narration.wav"},
  "music": {"mode": "external-prompt", "promptFile": "renders/music-prompt.txt", "file": "assets/music.wav"},
  "scenes": [{"id": "scene-1", "time": {"start": 0, "end": 4.2}, "image": "renders/previews/scene-1.png", "onScreenText": "متن مصوب روی تصویر", "narrationPhrase": "عبارت دقیق همین بخش گفتار"}]
}
```

narration.mode یکی از file / existing-speech / none / silent و music.mode یکی از none / file / external-prompt است. none و silent فقط انتخاب واقعی سفارش‌اند؛ برای عبور از نبود صوت، بی‌نریشن جعل نکن. گفتار موجود نیاز به تأیید تکراری همان گفتار ندارد؛ مرجع واقعی فایل/پیام در copy ثبت شود. برای رسانهٔ تزئینی هم کاربرد روشن بنویس.

```bash
npm run content -- storyboard JOB --file .local/projects/JOB/storyboard-plan.json
```

خروجی نسخه، manifest و مسیر contact sheetها را می‌دهد. تمام صفحه‌ها و فریم‌های لازم را واقعاً در همان محیط نشان بده، سپس پاسخ روشن کاربر را بگیر. تأیید سناریوی متنی، نریشن یا برنامهٔ تصویر، تأیید این استوری‌بورد نیست. صرف لینک‌دادن بدون نمایش و فرصت دیدن، مدرک تأیید تصویری نیست.

```bash
npm run content -- approve-storyboard JOB --version N --reference USER_MESSAGE --response EXACT_APPROVAL --presented-reference IMAGE_MESSAGE
npm run content -- production-check JOB
```

reference مرجع پاسخ واقعی، response عین تأیید روشن و presented-reference مرجع پیام/ابزار نمایش تصاویر همان نسخه است. با حدس یا تصمیم عامل پر نشوند. کد اتصال مدرک را می‌سنجد؛ پاسخ انسان را احراز هویت و کیفیت طرح را تأیید نمی‌کند.

manifest به متن، تنظیمات مؤثر، منبع ترکیب، رسانه‌ها، فریم‌ها و sheetها با checksum متصل است. تغییرشان نسخه و تأیید تازه می‌خواهد؛ تغییر phase و گزارش‌های DECISIONS/REVIEW تأیید را باطل نمی‌کند. صوتی که بعداً می‌رسد ورودی جدید است؛ زمان‌بندی و استوری‌بورد با آن به‌روز و تأیید شوند. متن نریشن و پرامپت موسیقی جای فایل واقعی نیستند؛ اگر سفارش صوت می‌خواهد، production-check تا رسیدن آن آماده نمی‌شود.

wrapperهای `npm run hf -- render PATH ...` و `scripts/remotion.mjs render ...` مسیرهای `.local/projects/` را کنترل می‌کنند؛ مثال‌های `.local/examples/` سفارش مشتری نیستند. مسیر سفارش HyperFrames قبل از گزینه‌ها بیاید. preview/check/snapshot/still پیش از تأیید مجازند. اجرای مستقیم باینری موتور به‌جای wrapper کنترل را دور می‌زند و مسیر مجاز تحویل نیست. پس از تأیید هم check، رندر، ffprobe و بازبینی نهایی شاهد مستقل می‌خواهند.
