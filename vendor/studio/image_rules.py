"""Generated offline Studio rules. See sources.json. No service imports."""
from __future__ import annotations
import re, json, hashlib, copy
from http import HTTPStatus
from pathlib import Path

AVALAI_IMAGE_FULL_MODEL = "gpt-image-2.5-flare"

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

def fa_number(value: int | str) -> str:
    return str(value).translate(FA_DIGITS)

def uses_editorial_header(record: dict) -> bool:
    """Studio scenes carry identity inside the set, never as a social masthead."""
    request = record.get("request", {})
    format_ = request.get("format", {})
    return resolved_logo_behavior(record) == "system_header"

def resolved_logo_behavior(record: dict) -> str:
    format_ = record.get("request", {}).get("format", {})
    value = str(format_.get("logoBehavior", "")).strip()
    if value in {"system_header", "floating_profile", "none"}:
        return value
    # Preserve old projects: the historical Studio switch controlled only
    # the system masthead, while ordinary designs always had it.
    if format_.get("family") == "studio" or record.get("request", {}).get("image", {}).get("mode") == "studio":
        studio = format_.get("studio") if isinstance(format_.get("studio"), dict) else {}
        return "system_header" if bool(studio.get("headerEnabled", False)) else "floating_profile"
    return "system_header" if format_.get("template") != "sticker" else "none"

def editorial_header_copy(record: dict) -> tuple[str, str]:
    """Return the two approved, deterministic masthead strings."""
    request = record.get("request", {})
    content = request.get("content", {})
    format_ = request.get("format", {})
    template = format_.get("template", "news_story")
    header_label = {
        "news_story": "خبر", "news_post": "خبر", "photo_report": "گزارش تصویری", "video_placeholder": "ویدیو",
        "citizen_message": "کلام مردم", "infographic": "اینفوگرافی", "poster": "پوستر", "classifieds": "نیازمندی‌ها", "morning_local": "صبح بخیر",
        "morning_kalam": "صبح بخیر", "market": "نبض بازار", "editorial_note": "یادداشت", "night": "شبانه", "home_tip": "خانه‌داری",
        "visual_riddle": "معما", "nature": "طبیعت‌گردی", "poll_story": "نظرسنجی", "poll_post": "نظرسنجی", "sport": "ورزش",
        "occasion_greeting": "مناسبت",
    }.get(template, "کلام تازه")
    if template == "occasion_greeting":
        header_label = "تبریک" if str(content.get("occasionTone", "")).strip() == "congratulation" else "تسلیت"
    if template in {"morning_local", "morning_kalam"}:
        greeting_emojis = ("☀️", "🌤️", "🌱", "✨", "🌅", "☕")
        request_seed = sum(str(record.get("requestId", "")).encode("utf-8"))
        header_label = f"صبح تازه‌تون بخیر {greeting_emojis[request_seed % len(greeting_emojis)]}"
    brand_title = {
        "kalametaze": "پایگاه خبری کلام تازه",
        "golbahar": "پایگاه خبری کلام تازه گلبهار",
        "chenaran": "پایگاه خبری کلام تازه چناران",
    }.get(request.get("brand", "kalametaze"), "پایگاه خبری کلام تازه")
    return header_label, brand_title

def floating_profile_prompt() -> str:
    """One art-direction module, shared by single images and carousel slides."""
    return """پروتکل طراحی نشان پروفایل شناور:
تصویر پیوست با برچسب BRAND PROFILE دارایی رسمی و قفل‌شدهٔ رسانه است؛ تصویر سوژه یا محتوای مانیتور نیست. فقط یک نشان دایره‌ای کامل از همین دارایی در خودِ طراحی بساز. همهٔ نوشته‌ها، رنگ‌ها، نسبت‌ها و کیفیت داخل نشان را عیناً حفظ کن؛ بازنویسی، تغییر لوگو، برش حروف و حذف بخشی از دایره ممنوع است.
نشان را از ابتدا جزئی از آرت‌دایرکشن و گرید همان تصویر طراحی کن، نه آواتار چسبانده‌شده در گوشه. یکی از این راهکارها را متناسب با طرح انتخاب کن: مدالیون ظریف هم‌سطح با کارت خبری، نشانی با عمق شیشه‌ای کنترل‌شده در اتصال دو سطح، یا نشان دایره‌ای در فضای منفی مرتبط با مسیر بصری تیتر. دور نشان فضای تنفس، لبهٔ بسیار تمیز، نور هم‌جهت صحنه و سایهٔ اتصال ظریف داشته باشد. از قاب سفید ضخیم، هالهٔ اغراق‌آمیز، افکت استیکری، دایرهٔ ناقص، اعوجاج و بزرگی مزاحم پرهیز کن.
چهره، تیتر، نقشه و اطلاعات مانیتور را نپوشان. نشان در اندازهٔ موبایل خوانا باشد ولی بر تیتر غالب نشود. در سری، زبان طراحی نشان هماهنگ بماند، اما محل آن متناسب با ترکیب‌بندی هر اسلاید انتخاب شود. یک پروفایل کافی است؛ هیچ پروفایل دوم یا سربرگ سیستمی نساز. رنگ تیتر را از عکس، موضوع و کنتراست صحنه انتخاب کن؛ رنگ پروفایل پالت اجباریِ طرح نیست. نقش‌ها و فرم‌های داخل پروفایل فقط داخل همان نشان بمانند و به پس‌زمینه یا حاشیه‌ها تکثیر نشوند. هیچ نشان دستی بعد از تولید اضافه نمی‌شود؛ همین خروجی باید نشان را کامل و زیبا داشته باشد."""

def news_art_direction() -> str:
    """Shared render direction, not an editorial text-generation prompt."""
    return """جهت هنری رندر خبری — جلد مجلهٔ ممتاز:
مثل یک آرت‌دایرکتور و طراح واقعی، ابتدا ایدهٔ بصری مخصوص همین خبر، گرید، فضای تنفس، نقطهٔ کانونی و مسیر نگاه از عکس به تیتر و اطلاعات مکمل را طراحی کن؛ سپس جزئیات را اجرا کن. خروجی نباید فقط عکس با نوشتهٔ چسبانده‌شده، اسلاید پاورپوینت یا قالب تکراری خبر فوری باشد.
تیتر قهرمان تایپوگرافی است: وزن حرفه‌ای، شکست سطر آگاهانه و تضاد روشن؛ حداکثر یک رنگ پایه و در صورت نیاز یک رنگ تأکیدی متناسب با عکس و موضوع. پالت از محتوای همین خبر و نور عکس بیاید، نه از رنگ لوگو؛ استفاده از رنگ رسانه کاملاً اختیاری است. زرد، مشکی/زرد، نوار قرمز و محل ثابت تیتر پیش‌فرض نیستند.
کارت‌های شیشه‌ای ممتاز بخشی از زبان طراحی‌اند: برای کپشن، زیرتیتر، منبع یا تعاملِ واقعاً فعال، سطح نیمه‌شفاف با تضاد خوانا، محوشدگی ظریفِ پشت سطح، لبهٔ نازک روشن، عمق و سایهٔ اتصال کنترل‌شده بساز. کارت با عکس، گرید و نور درهم‌تنیده باشد، نه مستطیل آماده یا حباب جدا. برای تیتر نیز سطح شیشه‌ایِ اختصاصی و یکپارچه مجاز است؛ ممنوعیت باکس کلیشه‌ای به معنی ممنوعیت کارت شیشه‌ایِ هنرمندانه نیست. بدون داده هیچ کارت یا متن تازه‌ای نساز.
هر خبر تصمیم طراحی تازه می‌خواهد؛ چیدمان ثابت را تکرار نکن. در کاروسل، خانوادهٔ رنگ، جنس شیشه، تایپوگرافی و نشانگرها هماهنگ بمانند ولی متن، سوژه و ایدهٔ هر اسلاید فقط از داده‌های همان اسلاید بیاید. عکس مرجع، چهره و محتوای مانیتور را برای زیباسازی تغییر نده؛ در حالت حفظ عکس، افکت‌ها فقط در گرافیک بیرون از محتوای قفل‌شده مجازند.
فضای ویدیو خالی بماند، فقط‌تیتر عکس نگیرد و پنل خالی با نوشتهٔ حدسی پُر نشود. حرفه‌ای‌بودن یعنی انتخاب هدفمند و خوانایی، نه افکت بیشتر یا تزئین تصادفی."""

def persian_glyph_contract() -> str:
    return """کنترل رندر حروف فارسی:
متن تأییدشده مرجع املایی قطعی است؛ آن را ویرایش یا تصحیح حدسی نکن. در خودِ رندر، اسکلت حرف، اتصال صحیح، تعداد و جای دقیق نقطه‌های بالا/پایین، دندانه‌ها، سرکش، نیم‌فاصله و علائم را حفظ کن؛ ب/پ/ت/ث، ج/چ/ح/خ، د/ذ، ر/ز/ژ، س/ش و ف/ق نباید به هم تبدیل شوند.
از فونت فارسی چاپیِ واضح، اندازهٔ کافی، فاصلهٔ سطر مناسب و لبهٔ شارپ استفاده کن. نقطه‌ها را با بافت، ذرات، درخشش، سایه یا نقش شیشه اشتباه نگیر؛ تزئین را روی حروف یا نقطه‌هایشان قرار نده. برای جا دادن متن، حروف را له، ناقص، کشیدهٔ افراطی یا ادغام نکن؛ فضای متن و شکست سطر را اصلاح کن.
پیش از تحویل، هر واژهٔ رندرشده را با رشتهٔ تأییدشده مقابله کن، به‌ویژه نام‌ها و تیتر: هیچ نقطه، حرف، عدد یا نشانه‌ای کم، زیاد یا جابه‌جا نباشد. این کنترل باید در تصویر نهایی اجرا شود؛ فهرست کنترل و نام حروف را روی تصویر ننویس."""

def news_palette_contract() -> str:
    """Keep media identity separate from the scene's art direction."""
    return """استقلال پالت و ترکیب‌بندی از نشان رسانه:
این قاعده بر توصیهٔ عمومیِ رنگ برند در سبک یا مرجع هویت اولویت دارد: رنگ رسانه الزام طراحی نیست. پالت را از موضوع خبر، عکس و نور واقعی انتخاب کن؛ استفاده‌نکردن از رنگ لوگو کاملاً مجاز است. هویت رسانه با پروفایل/سربرگِ انتخاب‌شده و واترمارک‌ها حفظ می‌شود، نه با رنگ‌کردن صحنه.
از رنگ یا شکل لوگو، موج سینوسیِ تزئینی، روبان منحنی، خطوط سیال تکراری، نوار رنگیِ بالا و پایین یا قاب سازمانیِ آماده استخراج نکن. اگر این شکل‌ها بخشی از عکس واقعی یا درخواست صریح کاربرند، حفظ شوند؛ خودکار به‌عنوان تزئین برند اضافه نشوند. شیشه‌ها سطح خواناییِ یکپارچه با عکس و گرید باشند، نه بهانه‌ای برای افزودن موج و حاشیهٔ رنگی.
در کاروسل پالتِ انتخاب‌شدهٔ همان پروژه را هماهنگ نگه دار؛ بین خبرهای مستقل پالت ثابت تحمیل نکن. در ویرایش تصویر، رنگ‌ها و ترکیب موجود را حفظ کن مگر تغییرشان صریحاً خواسته شده باشد."""

def news_watermark_contract(brand_watermark: str, photo: bool) -> str:
    placement = "در محدودهٔ خودِ عکس خبری، حتی وقتی عکس قاب مستقل دارد" if photo else "روی بافت گرافیکیِ بدنه، بیرون فضای خالیِ ویدیو و پنل نوشتن"
    return f"""واترمارک پراکندهٔ رسانه، مستقل از حالت لوگو و سربرگ:
دقیقاً سه واترمارک با متن لاتینِ قفل‌شدهٔ «{brand_watermark}» {placement} طراحی کن. آن‌ها را در سه ناحیهٔ جدا و نامتقارن، ظریف و کم‌کنتراست اما قابل تشخیص در اندازهٔ کامل قرار بده؛ نه یک امضای درشت گوشه‌ای و نه کاشی‌کاری سراسری. فاصلهٔ کافی از تیتر، نقطه‌های حروف، چهره، نقشه، منبع و نشانگر صفحه حفظ شود. متن لاتین را ترجمه، فارسی یا بازنویسی نکن. واترمارک چهارم، آیدی دیگر یا پروفایل دوم نساز. «بدون پروفایل» فقط نشان دایره‌ای و سربرگ را حذف می‌کند، نه این سه واترمارک خبری."""

def render_prompt(record: dict) -> str:
    """Build one finished, AI-authored design — no post-generation renderer.

    Templates intentionally read like a creative director's production brief:
    stable identity and hierarchy first, then only the fields the editor filled.
    This keeps a series cohesive while allowing the image model to make the
    final visual decisions.
    """
    request = record["request"]
    content = request.get("content", {})
    additional_instructions = str(content.get("additionalInstructions", "")).strip()
    image_contract = request.get("image", {}) if isinstance(request.get("image"), dict) else {}
    image_mode_contract = str(image_contract.get("mode", "generate"))
    image_prompt = str(image_contract.get("prompt", "")).strip()
    image_reference_instructions = str(image_contract.get("referenceInstructions", "")).strip()
    design_presenter_ids = [str(item) for item in image_contract.get("presenterIds", []) if str(item)]
    format_ = request.get("format", {})
    brand = request.get("brand", "kalametaze")
    is_news = format_.get("family") == "news" or format_.get("baseFamily") == "news"
    is_studio_image = format_.get("family") == "studio" or image_mode_contract == "studio"
    is_post_canvas = format_.get("canvas") == "post_1080x1350"
    # The approved masthead itself stays at its current position. The model
    # needs coordinates in its own raster: Gemini uses its 1K raster while
    # Flare receives exact 1280×1600 / 1152×2048 canvases. Mixing legacy sizes
    # can put Persian headlines under the deterministic masthead.
    # The masthead itself reaches roughly y=310 after its final transparent
    # asset is composited.  Leave a real buffer rather than merely clearing
    # the model's old 280px estimate, which let tall Persian glyphs land under
    # the official header on posts and, occasionally, stories.
    safe_top_pixels = 340
    safe_canvas_label = "۱۰۸۰×۱۳۵۰" if is_post_canvas else "۱۰۸۰×۱۹۲۰"
    is_gemini_image = selected_image_model(record).startswith("gemini-")
    if is_gemini_image:
        safe_top_provider_pixels = 292 if is_post_canvas else 244
        safe_provider_label = "۹۲۸×۱۱۵۲" if is_post_canvas else "۷۶۸×۱۳۷۶"
    else:
        safe_top_provider_pixels = 403 if is_post_canvas else 363
        safe_provider_label = "۱۲۸۰×۱۶۰۰" if is_post_canvas else "۱۱۵۲×۲۰۴۸"
    safe_top_percent = "۲۵٫۱۹٪" if is_post_canvas else "۱۷٫۷۱٪"
    readable_text_geometry = (
        f"قرارداد هندسی قطعی و مخصوص همین نسبت تصویر: در خروجی نهایی {safe_canvas_label}، ردیف‌های y=0..{fa_number(safe_top_pixels - 1)} "
        f"(بالای {safe_top_percent} تصویر) منطقهٔ ممنوعهٔ متن‌اند و bounding box هر نوشته باید y_min >= {fa_number(safe_top_pixels)} باشد. "
        f"تو عملاً روی بوم {safe_provider_label} رندر می‌کنی؛ بنابراین در همان تصویر واقعیِ خودت ردیف‌های "
        f"y=0..{fa_number(safe_top_provider_pixels - 1)} را کاملاً بدون نوشته نگه دار و bounding box کامل هر نوشته را فقط از "
        f"y >= {fa_number(safe_top_provider_pixels)} آغاز کن. این عددِ دوم مختصات عملیاتی توست. روتیتر، تیتر، زیرتیتر، منبع، "
        "تعامل، کپشن، عدد، آیدی، برچسب و تمام سایه/حاشیهٔ حروف همگی مشمول همین مرزند؛ حتی یک پیکسل متن از آن عبور نکند. "
        "این اندازه‌ها فقط دستور داخلیِ صفحه‌آرایی‌اند: هرگز عدد، خط، کادر، نوار، تغییر رنگ یا نشانه‌ای برای نمایش مرزِ ناحیهٔ امن در خود تصویر نکش."
    )
    provider_text_start = (
        f"در بوم واقعی {safe_provider_label}: بالاترین پیکسلِ هر نوشته y >= {fa_number(safe_top_provider_pixels)}؛ "
        f"در بوم نهایی {safe_canvas_label}: بالاترین پیکسلِ هر نوشته y >= {fa_number(safe_top_pixels)}."
    )
    if not uses_editorial_header(record):
        readable_text_geometry = "هیچ فضای سربرگ سیستمی رزرو نکن؛ از کل بوم با حاشیهٔ امن معمول استفاده کن."
        provider_text_start = readable_text_geometry
    news = format_.get("news") or {}
    citizen = format_.get("citizen") or {}
    studio = format_.get("studio") or {}
    foundation = (
        "یک تصویر استودیوییِ کامل و واقع‌گرایانه بساز؛ کیفیت چهره، نور، لنز، عمق صحنه و وفاداری به تصاویر مرجع اولویت مطلق است."
        if is_studio_image else
        app.image_base_prompt() if is_news else app.image_non_news_prompt()
    )
    template = format_.get("template", "news_story")
    header_label, brand_title = editorial_header_copy(record)
    brand_watermark = {
        "kalametaze": "@kalametaze.ir",
        "golbahar": "@golbahar.kalametaze",
        "chenaran": "@chenaran.kalametaze",
    }.get(brand, "@kalametaze.ir")
    slide_mode = str(format_.get("slideMode", "single"))
    slide_count = max(1, min(10, int(format_.get("slideCount", 1) or 1)))
    slide_index = max(1, min(slide_count, int(format_.get("slideIndex", 1) or 1)))
    is_series_slide = slide_mode in {"multi_story", "carousel"} and slide_count > 1
    # Keep the approved body as private layout context for continuation
    # slides. It may be removed from visual-copy fields below, but the model
    # still needs its real rhythm and length to reserve the right amount of
    # empty writing space.
    series_caption_context = str(content.get("caption", "")).strip() if is_series_slide and is_news else ""
    series_blank_fields: list[tuple[str, int]] = []
    if is_series_slide:
        club_showcase = content.get("clubShowcase") if template == "club_showcase" else None
        # A serial slide is deliberately a sealed, minimal payload.  Old
        # hidden values from the general design form must never leak into it.
        allowed_by_template = {
            "citizen_message": {"citizenMessageText", "citizenHeadline", "citizenResponse", "citizenInteraction"},
            "editorial_note": {"title", "caption", "source", "editorialNoteStyle"},
        }
        allowed = allowed_by_template.get(template, {"kicker", "title", "subtitle", "caption", "interactionText", "source"})
        content = {key: value for key, value in content.items() if key in allowed and isinstance(value, str) and value.strip()}
        if isinstance(club_showcase, dict):
            content["clubShowcase"] = club_showcase
        # Image models are not dependable for long Persian paragraphs.  They
        # receive only the amount, never the words, and must reserve a blank
        # writing area. These limits are intentionally generous for mobile.
        visible_limits = {"title": 240, "subtitle": 280, "caption": 700, "interactionText": 240, "source": 180, "citizenHeadline": 240, "citizenResponse": 420, "citizenInteraction": 240, "citizenMessageText": 700}
        for key, limit in visible_limits.items():
            value = str(content.get(key, "")).strip()
            if value and len(value) > limit:
                series_blank_fields.append((key, len(value)))
                content.pop(key, None)
    else:
        # Apply the same safe visual-text contract to ordinary single designs.
        # The full text remains in the form/publication flow; it simply is not
        # entrusted to image generation once it is too long for reliable copy.
        visible_limits = {"title": 240, "subtitle": 280, "caption": 700, "interactionText": 240, "citizenMessageText": 700, "citizenHeadline": 240, "citizenResponse": 420, "citizenInteraction": 240, "occasionHeadline": 240, "occasionMessage": 700}
        for key, limit in visible_limits.items():
            value = str(content.get(key, "")).strip()
            if value and len(value) > limit:
                series_blank_fields.append((key, len(value)))
                content.pop(key, None)
    # A news-series cover is an intentionally minimal entry point.  Enforce
    # this at the worker too, so stale deck fields or an old client cannot put
    # article paragraphs, sources, or arbitrary CTAs on slide one.
    if is_series_slide and is_news:
        if slide_index == 1:
            content = {
                key: str(content.get(key, "")).strip()
                for key in ("kicker", "title", "subtitle")
                if str(content.get(key, "")).strip()
            }
            content["interactionText"] = "ورق بزنید"
        else:
            content.pop("kicker", None)
    # Admin-only helper answers are intentionally never part of the visual
    # brief. They exist only to make puzzle suggestions reviewable.
    approved_copy = {key: value for key, value in content.items() if value and key not in {"additionalInstructions", "titleOnly", "titleLayout", "morningRiddleAnswer", "morningVisualRiddleAnswer"}}
    if template == "club_showcase":
        approved_copy = {"title": str((content.get("clubShowcase") or {}).get("title", ""))}
    output_kind = news.get("outputKind", "title_photo")
    layout = news.get("layout", "top")
    photo_frame = news.get("photoFrame", "full")
    video_overlay = bool(news.get("videoOverlay"))
    video_frame = news.get("videoFrame", "landscape")
    video_background_blur = bool(news.get("videoBackgroundBlur"))
    site_link_placeholder = bool(news.get("siteLinkPlaceholder"))
    if is_news and template != "sport":
        # Keep the data payload as small as the selected form state requires;
        # stale text from an earlier selection must never contradict the brief.
        # Caption is sent only to determine the amount of *empty* caption
        # space. It is deliberately excluded from the visible-copy module.
        allowed = {"kicker", "title", "subtitle", "caption", "source", "interactionText"}
        approved_copy = {key: value for key, value in approved_copy.items() if key in allowed}
    template_briefs = {
        "morning_local": "یک استوری صبحگاهی مجله‌ای و ممتاز بساز. کارت‌های شیشه‌ای مستقل برای آب‌وهوا، اوقات شرعی و معما داشته باش. برای هر ردیف اوقات شرعی و هر دادهٔ آب‌وهوا آیکون سه‌بعدیِ ظریف و حرفه‌ای طراحی کن. معما در کارت مستقل و چشمگیر باشد.",
        "morning_kalam": "یک جلد صبحگاهی ملی با حس امید، تقویم و مناسبت‌ها بساز. مناسبت‌ها و معما دو کارت مستقل با آیکون اختصاصی داشته باشند.",
        "market": "یک داشبورد مالی لوکس، طلایی و تیره بساز؛ هر نرخ در یک ردیف/ویجت واضح، حرفه‌ای و قابل اسکن باشد. عددها و واحدها را عیناً حفظ کن.",
        "editorial_note": "یک یادداشت سردبیر/ادمینِ اینستاگرامی با هویت رنگی رسانه، حس انسانی و اقتدار تحریریه، گرید مجله‌ای خلوت و تایپوگرافی حرفه‌ای بساز.",
        "citizen_message": "یک طراحی فیروزه‌ای، انسانی و معتبر برای پیام مردمی بساز؛ متن اصلی با احترام و خوانایی بالا در کارت شیشه‌ای قرار گیرد.",
        "night": "یک طراحی شبانه با ترکیب بنفش عمیق و مشکی، حس فرهنگی و سینمایی، مناسب کتاب/شعر/موسیقی بساز.",
        "home_tip": "یک طراحی کاربردی، گرم و تمیز با حس مجلهٔ سبک زندگی بساز.",
        "visual_riddle": "یک طراحی بازی‌گونه اما حرفه‌ای برای تعامل بساز؛ معما واضح و فضای پاسخ‌گویی جذاب باشد.",
        "nature": "یک طراحی سفر و طبیعت با حس کشف، نقشه/مسیر نمادین و کادرهای اطلاعاتی لوکس بساز.",
        "poll_story": "یک استوری نظرسنجی پرانرژی با فضای مناسب تعامل و دکمه‌های ظاهریِ غیرقابل‌کلیک بساز.",
        "poll_post": "یک پست نظرسنجی چشمگیر با گرید مرتب و فضای پاسخ‌گویی بساز.",
        "sport": "یک طراحی ورزشی پویا، پرانرژی و حرفه‌ای با تایپوگرافی قوی و آیکون‌های ورزشی ظریف بساز.",
        "poster": "یک پوستر تبلیغاتی یا اطلاع‌رسانیِ حرفه‌ای، قابل‌انتشار و دارای پیام اصلیِ بسیار خوانا، گرید ممتاز و دعوت به اقدامِ واضح بساز.",
        "classifieds": "یک صفحهٔ نیازمندی روزنامه‌ایِ حرفه‌ای بساز؛ هر آگهی در کادر مستقل با آیکون کوچک مرتبط، تیتر، متن و راه تماس دقیق قرار بگیرد.",
    }
    # The editable gateway file is the source of truth.  The in-code wording
    # remains a safe fallback for an unknown/legacy template only.
    brief = app.image_template_prompt(template) if hasattr(app, "image_template_prompt") else template_briefs.get(template, "یک استوری خبری واقع‌گرایانه، مدرن و در حد جلد مجله بساز. عکس زمینه ایرانی، معتبر و مستقیماً مرتبط با موضوع باشد. تیتر در بخش طبیعی و آرام تصویر قرار گیرد، نه در یک کادر تیترِ جدا.")
    image_mode = image_mode_contract
    # A visual edit always uses the already-generated parent image as its
    # immutable reference.  In the prompt it therefore has the same visual
    # contract as preserving a real image, while avoiding a missing dictionary
    # key for the internal ``edit_existing`` transport mode.
    if image_mode == "edit_existing":
        image_mode = "preserve"
    reference_count = len([item for item in (record.get("uploadedImages") or []) if item.get("role") != "series_previous_slide"])
    uploaded_items = [item for item in (record.get("uploadedImages") or []) if isinstance(item, dict)]
    continuity_count = sum(1 for item in uploaded_items if str(item.get("role", "")) == "series_previous_slide")
    user_reference_count = sum(1 for item in uploaded_items if str(item.get("role", "")) != "series_previous_slide")
    has_user_reference = user_reference_count > 0
    reference_instruction = (
        "تصویر پیوست‌شده داراییِ قفل‌شده و خودِ عکس نهایی است، نه منبع الهام: تمام پیکسل‌های بخش اصلی، سوژه، چهره، بافت پوست، لباس، مکان، اشیا، نور و معنای آن را بدون بازسازی و تغییر نگه دار. عکس مشابه یا نسخهٔ تازه نساز. فقط اگر نسبت بوم ایجاب می‌کند، زمینه را از لبه‌های بیرونی همان عکس به‌طور طبیعی گسترش بده؛ داخل محدودهٔ اصلی عکس را دست‌کاری نکن."
        if reference_count <= 1 else
        "همهٔ تصاویر پیوست‌شده دارایی‌های قفل‌شده‌اند و باید بدون بازسازی، تغییر چهره/سوژه/لباس/مکان/اشیا، حذف یا جایگزینی استفاده شوند. هر عکس را با تمام محتوای اصلی‌اش دقیقاً حفظ کن و فقط در بیرونِ لبه‌های آن برای هماهنگی با بوم outpaint انجام بده. اگر چند تصویر باید کنار هم بیایند، کولاژ مجله‌ایِ تمیز بساز اما داخل هیچ عکس را تغییر نده و هیچ تصویر تازه‌ای به‌جای آن‌ها تولید نکن."
    )
    image_instructions = {
        "generate": "عکس خبریِ بدنه را خودت، دقیقاً متناسب با موضوع تیتر، کاملاً واقع‌گرایانه، ایرانی و با حس عکاسی خبری تولید کن. پیش از ساخت عکس، برای بخشِ آرام و خوانای تیتر برنامه‌ریزی کن.",
        "preserve": "همهٔ تصاویر پیوست‌شده، داراییِ قفل‌شده و خودِ عکس نهایی هستند: محدودهٔ اصلی هر عکس و تمام پیکسل‌ها، سوژه‌ها، چهره‌ها، بافت پوست، لباس، مکان، اشیا، نور، لحظه و معنای آن را دقیقاً نگه دار. بهبود یا بازسازی داخل عکس، تغییر رنگ و نور، روتوش، برشِ محتوای اصلی، جایگزینی یا تولید عکس مشابه ممنوع است. فقط گسترش طبیعی زمینه در بیرون لبه‌های عکس برای تکمیل نسبت بوم مجاز است.",
        "reference": reference_instruction,
        "studio": "Ù‡Ù…Ø§Ù† Ù„ÙˆÚ©ÛŒØ´Ù† Ø§Ø³ØªÙˆØ¯ÛŒÙˆÛŒÛŒ Ùˆ Ø§Ù„Ù…Ø§Ù†â€ŒÙ‡Ø§ÛŒ ØªØ£ÛŒÛŒØ¯Ø´Ø¯Ù‡ Ø±Ø§ Ø­ÙØ¸ Ú©Ù†؛ Ø§Ú¯Ø± Ø±ÙØ±Ù†Ø³ Ø§Ø±Ø§Ø¦Ù‡ Ø´Ø¯Ù‡ØŒ Ú©Ø§Ù…Ø±Ø§ØŒ Ú†ÛŒØ¯Ù…Ø§Ù†ØŒ Ù†ÙˆØ±ØŒ Ø²Ù…ÛŒÙ†Ù‡ Ùˆ Ø¬Ø§ÛŒÚ¯Ø°Ø§Ø±ÛŒ Ø±Ø§ Ø¨Ø¯ÙˆÙ† ØªØºÛŒÛŒØ± Ù†Ú¯Ù‡ Ø¯Ø§Ø±؛ Ù…ØªÙ† Ø§ÛŒÙ† Ø§Ø³Ù„Ø§ÛŒØ¯ Ø±Ø§ Ø¨Ø§ Ù‡Ù…ÛŒÙ† Ù„ÙˆÚ©ÛŒØ´Ù† Ùˆ Ù‡Ù…Ø§Ù‡Ù†Ú¯ÛŒ Ù…Ø¬Ù„Ù‡â€ŒØ§ÛŒ Ø±Ù†Ø¯Ø± Ú©Ù†.",
        "none": "هیچ عکس خبری، قاب عکس یا سوژهٔ تصویری مستقل نساز. با تایپوگرافی، رنگ، بافت و گرافیک حرفه‌ایِ کاملاً متناسب با موضوع، طرح را کامل کن.",
    }
    # The worker file historically contained a mojibake copy of the Studio
    # wording. Keep the provider-facing contract explicit and ASCII-safe:
    # attached monitor/reference pixels are evidence to preserve, not a cue to
    # redraw. This override also applies to legacy saved jobs.
    image_instructions["studio"] = (
        "Studio image contract: preserve every attached user-reference image exactly when the request says preserve/reference. "
        "For a monitor image, place the original image inside the existing monitor surface with its pixels, map geometry, labels, typography and colors unchanged; only apply the monitor's natural perspective, glare and scene lighting outside the image content. "
        "Do not redraw, translate, summarize, sharpen, recolor, crop, regenerate or replace any part of the attached image. "
        "The current-slide attachment always outranks a previous-slide continuity reference."
    )
    layout_instructions = {
        "top": f"صفحه‌بندی پیش‌فرضِ مجله‌ای: {provider_text_start} کل کادر تیتر، تمام حروف و سایهٔ آن را پایین این مرز قرار بده. جای تیتر را متناسب با عکس انتخاب کن و آن را تکراری نساز؛ راست‌چین، وسط‌چین یا چپ‌چین بودن باید آگاهانه و هماهنگ با صحنه باشد. یک یا دو تأکید خلاقانهٔ کنترل‌شده انتخاب کن: بزرگ‌کردن یک واژهٔ کلیدی، تغییر رنگ واژه‌ای مهم، خط ظریف کنار/زیر چند کلمه، یا باکس رنگی محدود زیر بخش مهم تیتر. عکس باید جای طبیعی تیتر را ایجاد کند؛ باکس تیترِ جدا و کلیشه‌ای نساز.",
        "right_column": f"یک ستون عمودیِ یکپارچه و حرفه‌ای در سمت راست بساز. {provider_text_start} خود ستون می‌تواند ادامهٔ طبیعی گرید باشد، اما تیتر و تمام نوشته‌های آن فقط پایین این مرز آغاز شوند. تیتر در بالای همین ستونِ پایین‌آمده، چندخطی و با حداکثر یک یا دو کلمه در هر خط باشد. اگر خروجی پنل کپشن دارد، نیمهٔ پایین ستون را برای همان پنل رزرو کن؛ نوع خروجی مشخص می‌کند پنل خالی باشد یا متن کپشن را بگیرد. در غیر این صورت تیتر در ارتفاع ستون متعادل و شاخص قرار گیرد.",
        "center": f"{provider_text_start} تیتر را به‌عنوان قهرمان اصلی طرح، با ترکیب‌بندی مجله‌ای شاخص در مرکزِ مجازِ پایین این مرز قرار بده. اگر قاب عکسِ غیرتمام‌صفحه انتخاب شده، تیتر باید در ناحیهٔ خلوتِ بیرون قاب باشد و با آن هم‌پوشانی نداشته باشد؛ اگر عکس تمام‌صفحه است، در خودِ عکس یک ناحیهٔ طبیعی، آرام و با تضاد کافی برای تیتر بساز، بدون باکس کلیشه‌ای. در حالت فقط تیتر نیز هیچ قاب عکس یا سوژهٔ تصویری مستقل نساز. اگر پنل کپشنِ خالی وجود دارد، تیتر وسط نباید وارد آن شود. اندازه، وزن و شکست خطوط تیتر اولویت بصری اصلی باشد.",
        "bottom": f"{provider_text_start} تیتر را به‌عنوان قهرمان اصلی طرح، با ترکیب‌بندی مجله‌ای شاخص در پایین تصویر قرار بده. اگر قاب عکسِ غیرتمام‌صفحه انتخاب شده، تیتر باید در ناحیهٔ خلوتِ بیرون قاب باشد و با آن هم‌پوشانی نداشته باشد؛ اگر عکس تمام‌صفحه است، در خودِ عکس یک ناحیهٔ طبیعی، آرام و با تضاد کافی در پایین برای تیتر بساز، بدون باکس کلیشه‌ای. در حالت فقط تیتر نیز هیچ قاب عکس یا سوژهٔ تصویری مستقل نساز. اگر پنل کپشنِ خالی وجود دارد، تیتر پایین نباید وارد آن شود. اندازه، وزن و شکست خطوط تیتر اولویت بصری اصلی باشد.",
    }
    photo_frame_instructions = {
        "full": "عکس خبر سراسر بدنه را با برش هوشمند، طبیعی و بدون حاشیهٔ بی‌دلیل پُر کند؛ ناحیهٔ امن بالا و نواحی متن بخشی از همان ترکیب‌بندی پیوسته باشند.",
        "landscape": "در بدنه یک قاب افقیِ بزرگ، مجله‌ای و یکپارچه با گرید بساز و آن را با عکس واقعی یا تولیدشده کاملاً پُر کن. بیرون قاب برای تیتر و عناصر کمکی، خلوت و حساب‌شده بماند.",
        "square": "در بدنه یک قاب مربعِ بزرگ، مجله‌ای و یکپارچه با گرید بساز و آن را با عکس واقعی یا تولیدشده کاملاً پُر کن. بیرون قاب برای تیتر و عناصر کمکی، خلوت و حساب‌شده بماند.",
        "portrait_3_4": "در بدنه یک قاب عمودیِ بزرگ با نسبت دقیق ۳:۴، مجله‌ای و یکپارچه با گرید بساز و آن را با عکس واقعی یا تولیدشده کاملاً پُر کن. بیرون قاب برای تیتر و عناصر کمکی، خلوت و حساب‌شده بماند.",
    }
    video_instruction = "" if not video_overlay else (
        f"این طرح برای قراردادن ویدیو است، نه کاور و نه قاب نمایشی. در بدنه یک فضای ویدیوییِ کاملاً خالی با نسبت دقیق { {'landscape': '۱۶:۹ افقی', 'square': '۱:۱ مربع', 'portrait': '۹:۱۶ عمودی'}[video_frame] } رزرو کن. در حالت افقی یا مربع، این فضا باید با حداکثر عرضِ ممکن و حدود ۳٫۵٪ فاصله از کناره‌ها باشد؛ در حالت عمودی، با حداکثر ارتفاعِ ممکن و در مرکز قرار بگیرد. داخل فضای رزروشده هیچ انسان، عکس، نوشته، لوگو، آیکون، دکمهٔ پخش، بافت، نور، سایه، گرادینت یا عنصر گرافیکی نساز. اگر شفافیت واقعی PNG را پشتیبانی می‌کنی، خودِ این فضا را شفاف بگذار؛ در غیر این صورت همان ناحیه را یک باکس ساده، تمیز، خالی و یکدست با مرز بسیار ظریف بساز تا محل ویدیو دقیق و قابل‌تشخیص باشد. بیرون این باکس ترکیب‌بندی و هویت بصری را با کیفیت ممتاز کامل کن. هیچ پردازش دستی یا حذف پس‌زمینه‌ای بعد از تولید انجام نمی‌شود."
    )
    def module(title: str, body: str) -> str:
        """Return a prompt section only when its controlling form state is active."""
        body = body.strip()
        return f"### {title}\n{body}" if body else ""

    def occasion_instruction(value: str, placement: str) -> str:
        """Safely typeset only short occasions; reserve room for long lists.

        Image models are unreliable with multi-line Persian copy.  The same
        rule as citizen messages therefore gives the editor a designed blank
        area and keeps the authoritative text available for manual overlay.
        """
        lines = [line.strip() for line in value.splitlines() if line.strip()]
        words = len(lines[0].split()) if len(lines) == 1 else 0
        if len(lines) == 1 and words <= 14:
            return f"{placement}، مناسبت امروز را دقیقاً و بدون تغییر در یک خط مستقل بنویس: «{lines[0]}»."
        if lines:
            return f"{placement}، برای {fa_number(len(lines))} خط مناسبتِ تأییدشده (در مجموع حدود {fa_number(sum(len(line.split()) for line in lines))} واژه) یک فضای خالیِ شیشه‌ای، جادار و خوانا رزرو کن. هیچ‌یک از متن مناسبت‌ها، متن آزمایشی، عدد، عنوان یا مناسبت حدسی را در آن ننویس؛ تحریریه متن را بعداً دستی اضافه می‌کند."
        return ""

    # These booleans are the prompt contract for the dynamic news form.  A
    # disabled form branch must never leak a stale instruction into the model.
    has_news_photo = is_news and template != "citizen_message" and output_kind != "title_only" and not video_overlay

    form_modules: list[str] = []
    advertising = request.get("advertising") if isinstance(request.get("advertising"), dict) else {}
    if advertising.get("enabled"):
        ad_mode = {"card": "کارت تبلیغات مستقل", "subtitle": "زیرنویس تبلیغاتی جذاب روی طراحی", "embedded": "طراحی تبلیغ در بطن تصویر"}.get(str(advertising.get("mode")), "کارت تبلیغات مستقل")
        ad_lines = [f"حالت تبلیغ: {ad_mode}"]
        for key, label in (("title", "عنوان"), ("subtitle", "زیرعنوان"), ("description", "توضیحات"), ("contact", "راه‌های ارتباطی")):
            value = str(advertising.get(key) or "").strip()
            if value:
                ad_lines.append(f"{label} را دقیقاً و بدون تغییر استفاده کن: «{value}».")
        ad_lines.append("فایل‌های تبلیغِ پیوست‌شده مرجع قفل‌شده‌اند؛ لوگو، محصول، بسته‌بندی، چهره و نوشته‌های داخل آن‌ها را حفظ کن و فقط مطابق حالت تبلیغ در ترکیب‌بندی اصلی ادغام کن. هیچ ادعا، قیمت، تخفیف، شماره، نشانی یا لوگوی تازه‌ای اختراع نکن.")
        form_modules.append(module("ماژول تبلیغات", "\n".join(ad_lines)))
    if template.startswith("club_"):
        form_modules.append(module("هویت محتوای باشگاه مخاطبان", app.image_template_prompt(template)))
    if template == "club_showcase":
        showcase = content.get("clubShowcase") or {}
        if isinstance(showcase, dict):
            labels = {"title": "عنوان جایزه", "store": "نام فروشگاه", "discount": "تخفیف", "gift": "هدیه", "description": "شرایط جایزه", "points": "امتیاز لازم", "expires": "مهلت استفاده", "address": "نشانی"}
            copy = "\n".join(f"{label}: {str(showcase.get(key, '')).strip()}" for key, label in labels.items() if str(showcase.get(key, '')).strip())
            form_modules.append(module("اطلاعات دقیق کارت جایزه", copy + "\nفقط مقدار فیلدهای بالا را نمایش بده؛ برچسب‌های خالی، شناسه داخلی جایزه و مقادیر حدسی را ننویس. عکس محصول و لوگوی فروشگاه مرجع واقعی هستند؛ تصویر کارت سه‌بعدی را با حفظ ظاهر و هویت آن‌ها طراحی کن."))
    if image_prompt:
        form_modules.append(module(
            "پرامپت اختصاصی لایهٔ تصویر",
            "این دستور فقط سوژه، رخداد، فضا، اشیا، سبک عکاسی و نورِ خودِ تصویر را کنترل می‌کند و حق تغییر متن‌های قفل‌شده، هدر، لوگو، گرید یا ماژول‌های فرم را ندارد. "
            f"تصویر را دقیقاً بر اساس این توضیح بساز: «{image_prompt}»",
        ))
    if image_reference_instructions and image_mode in {"preserve", "reference"}:
        form_modules.append(module(
            "توضیحات اختصاصیِ تصویر مرجع",
            "این دستور فقط بر نحوهٔ استفاده از خودِ عکس/عکس‌های مرجع اثر می‌گذارد و نباید متن طرح، هدر، تایپوگرافی یا سایر ماژول‌ها را تغییر دهد. "
            f"دستور کنترل‌شده: «{image_reference_instructions}»",
        ))
    if design_presenter_ids and not is_studio_image:
        presenter_labels = [app.VIDEO_ASSET_ENTITIES["presenter"].get(item, item) for item in design_presenter_ids]
        form_modules.append(module(
            "حضور مجری‌های مرجع در تصویر",
            "مجری‌های انتخاب‌شده را به‌صورت طبیعی و مرتبط با موضوع در ترکیب‌بندی قرار بده: " + "، ".join(presenter_labels) + ". "
            "تصاویر PRESENTER IDENTITY فقط قرارداد هویت‌اند: هندسهٔ چهره، سن ظاهری، بافت طبیعی پوست، مو و ویژگی‌های تشخیصی هر شخص را دقیق حفظ کن. "
            "ژست، نگاه، میمیک، حالت دست‌ها، زاویهٔ بدن و لباس می‌تواند متناسب با موضوع و توضیحات تکمیلی تغییر کند، اما هویت شخص هرگز نباید تغییر یا با فرد دیگری ادغام شود.",
        ))
    if template == "morning_local":
        def value(name: str) -> str:
            return str(content.get(name, "")).strip()

        morning_city = "چناران" if value("morningCity") == "chenaran" else "گلبهار"
        morning_title = f"اوقات شرعی و آب و هوای امروز شهرستان {morning_city}"
        date_lines = [item for item in (value("morningWeekday"), value("morningPersianDate"), value("morningGregorianDate"), value("morningHijriDate")) if item]
        prayer_facts = [
            ("اذان صبح", value("morningFajr")), ("طلوع آفتاب", value("morningSunrise")),
            ("اذان ظهر", value("morningNoon")), ("غروب", value("morningSunset")),
            ("اذان مغرب", value("morningMaghrib")), ("نیمه‌شب", value("morningMidnight")),
        ]
        morning_sections = [
            "این نخستین استوری صبحگاهیِ یک رسانهٔ خبری است؛ آن را در سطح یک جلد مجلهٔ ممتاز و اثر قابل‌ارسال به جشنوارهٔ طراحی بساز. بدنه باید مدرن، شاداب، مجله‌ای و دارای کارت‌های شیشه‌ایِ حرفه‌ای باشد؛ نه یک قالب خبری معمولی.",
            f"عنوان اصلی طرح را دقیقاً، بدون بازنویسی، کوتاه‌سازی یا افزودن واژه، این‌گونه بنویس: «{morning_title}». این عنوان باید یک‌بار، خوانا و با سلسله‌مراتب اصلی طرح نمایش داده شود.",
            "اگر تصویر مرجع پیوست شده، از همان تصویر در بدنه استفاده کن و بخش شاخص و زیبای آن را نگه دار. فقط ارتقای کیفیت، نور، رنگ و گسترش طبیعی کادر برای تمام‌صفحه‌شدن مجاز است. ناحیهٔ امن بالا را با رنگ، نور و امتداد طبیعی همان تصویر هماهنگ و بدون متن یا نشان نگه دار.",
        ]
        if value("morningLocation"):
            morning_sections.append(f"روی خود عکس، یک نشان کوچکِ لوکیشن با آیکون مکان و متن دقیق «{value('morningLocation')}» بگذار.")
        if value("morningPhotoCredit"):
            morning_sections.append(f"روی خود عکس، یک نشان کوچکِ دوربین با متن دقیق «{value('morningPhotoCredit')}» بگذار.")
        if date_lines:
            morning_sections.append("یک کارت تاریخِ شیشه‌ایِ خوانا بساز؛ عنوانی مانند «تاریخ» یا «کارت تاریخ» ننویس. این خطوط را با سلسله‌مراتب تایپوگرافیِ درست و دقیقاً بدون تغییر درج کن؛ روز هفته و تاریخ شمسی شاخص‌تر باشند:\n" + "\n".join(f"- {line}" for line in date_lines))
        local_occasion = value("morningLocalOccasion")
        if local_occasion:
            morning_sections.append(occasion_instruction(local_occasion, "در یک کارت مستقل، ظریف و هماهنگ با تاریخ"))
        weather_lines = []
        if value("morningWeatherCondition"):
            weather_lines.append(f"- وضعیت جوی با آیکون سه‌بعدیِ مناسب: «{value('morningWeatherCondition')}»")
        if value("morningMinTemperature"):
            weather_lines.append(f"- مقدار کمینه: «{value('morningMinTemperature')}» با فلش کوچک قرمز رو به پایین")
        if value("morningMaxTemperature"):
            weather_lines.append(f"- مقدار بیشینه: «{value('morningMaxTemperature')}» با فلش کوچک سبز رو به بالا")
        if value("morningWindSpeed"):
            weather_lines.append(f"- سرعت باد: «{value('morningWindSpeed')}» با آیکون باد")
        if value("morningHumidity"):
            weather_lines.append(f"- رطوبت: «{value('morningHumidity')}» با آیکون قطره")
        if value("morningAttire"):
            weather_lines.append(f"- پوشاک پیشنهادی: «{value('morningAttire')}» با آیکون پوشاک")
        if weather_lines:
            morning_sections.append("یک ویجت آب‌وهوای حرفه‌ای و شبیه اپلیکیشن بساز؛ عنوان «آب‌وهوا»، و کلمات «کمینه»، «بیشینه»، «باد» و «رطوبت» را روی طرح ننویس. اعداد کمینه و بیشینه باید بزرگ، شاخص و با آیکون وضعیتِ متناسب با داده‌ها باشند. فقط این داده‌های تأییدشده را استفاده کن:\n" + "\n".join(weather_lines))
        prayer_lines = [f"- {label}: {item}" for label, item in prayer_facts if item]
        if prayer_lines:
            morning_sections.append("یک کارت اوقات شرعیِ شیشه‌ای، منظم و آرام با آیکون‌های ظریف بساز و فقط این ساعت‌ها را دقیقاً بنویس:\n" + "\n".join(prayer_lines))
        riddle_question = value("morningRiddleQuestion")
        if riddle_question:
            game_name = "معمای امروز"
            riddle_hint = value("morningRiddleHint")
            riddle_lines = [f"نام کارت، دقیقاً: «{game_name}»", f"پرسش، دقیقاً: «{riddle_question}»"]
            if riddle_hint:
                riddle_lines.append(f"متن کوچک، دقیقاً: «{riddle_hint}»")
            morning_sections.append("در پایین‌ترین بخش طرح، یک کارت تعامل مستقل، جذاب و قابل‌خواندن بساز. پاسخ یا راهنمای اضافه ننویس.\n" + "\n".join(f"- {line}" for line in riddle_lines))
        local_puzzle_count = len([item for item in record.get("uploadedImages", []) if item.get("role") == "puzzle"])
        if local_puzzle_count:
            morning_sections.append(f"{fa_number(local_puzzle_count)} فایل آخرِ مرجع، ایموجی/تصاویر معمای تصویری هستند، نه عکس پس‌زمینه. زمینهٔ آن‌ها را حذف کن، خودِ اجزا را بدون تغییر معنا، رنگ یا جزئیات نگه دار و در یک کارت مستقل و هنرمندانه بچین. بالای این کارت فقط دقیقاً بنویس: «معمای تصویری». پایین آن فقط و با اندازهٔ کوچک دقیقاً بنویس: «پاسخ معمای امروز را برامون بفرستین.» هیچ کلمهٔ اضافی مانند «کارت»، «ایموجی» یا «آیکون» ننویس.")
        elif value("morningVisualRiddleIdea"):
            morning_sections.append(f"در یک کارت مستقل و هنرمندانه، این معمای تصویریِ پیشنهادی را با عناصر دیداریِ واضح و بدون پاسخ اجرا کن: «{value('morningVisualRiddleIdea')}». بالای کارت فقط دقیقاً بنویس: «معمای تصویری». پایین آن فقط و با اندازهٔ کوچک دقیقاً بنویس: «پاسخ معمای امروز را برامون بفرستین.» هیچ کلمهٔ اضافی مانند «کارت»، «ایموجی»، «آیکون» یا پاسخ معما ننویس.")
        morning_sections.append("هر سه واترمارکِ هویت رسانه باید پراکنده، ظریف و کم‌رنگ روی خودِ عکس اصلی باشند، نه روی کارت‌های اطلاعاتی یا فضای خالی.")
        form_modules.append(module("قالب اختصاصی صبح بخیر محلی", "\n\n".join(morning_sections)))
        if image_mode in {"generate", "preserve", "reference"}:
            form_modules.append(module("نحوهٔ استفاده از تصویر", image_instructions[image_mode]))
    elif template == "morning_kalam":
        def kalam_value(name: str) -> str:
            return str(content.get(name, "")).strip()

        morning_kalam = format_.get("morningKalam") or {}
        today_index = int(morning_kalam.get("todayIndex", 1) or 1)
        holiday_indexes = {int(item) for item in morning_kalam.get("holidayIndexes", []) if str(item).isdigit()}
        week_days = [kalam_value(f"morningKalamDay{index}") for index in range(1, 8)]
        calendar_weekdays = ("شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه")
        calendar_lines = []
        for index, day in enumerate(week_days, start=1):
            if not day:
                continue
            tags = []
            if index == today_index:
                tags.append("امروز؛ بزرگ‌تر و شاخص")
            if index in holiday_indexes:
                tags.append("تعطیل؛ رنگ قرمز")
            calendar_lines.append(f"- {calendar_weekdays[index - 1]}: «{day}»" + (f" ({'، '.join(tags)})" if tags else ""))
        main_photo_count = len([item for item in record.get("uploadedImages", []) if item.get("role") != "puzzle"])
        puzzle_count = len([item for item in record.get("uploadedImages", []) if item.get("role") == "puzzle"])
        kalam_sections = [
            "یک استوری اول صبحِ ملی برای کلام تازه، در سطح ارسال به جشنوارهٔ طراحی بساز: مدرن، جذاب، مجله‌ای، سرزنده و دارای کارت‌های شیشه‌ایِ حرفه‌ای. این قالب خبری عادی نیست؛ حس تقویم روزانه، امید صبح و کشفِ معمای تصویری داشته باشد.",
            "اگر تصویر اصلی مرجع پیوست شده، آن را با حفظ سوژه و محتوای اصلی، فقط با ارتقای کیفیت، نور، رنگ و گسترش طبیعی کادر استفاده کن. بخش شاخص و زیبای عکس را حفظ کن و کارت‌ها را در نواحی دیگر با گرید حرفه‌ای بچین.",
        ]
        if kalam_value("morningKalamLocation"):
            kalam_sections.append(f"روی خود عکس، یک نشان کوچکِ لوکیشن با آیکون مکان و متن دقیق «{kalam_value('morningKalamLocation')}» بگذار.")
        if kalam_value("morningKalamPhotoCredit"):
            kalam_sections.append(f"روی خود عکس، یک نشان کوچکِ دوربین با متن دقیق «{kalam_value('morningKalamPhotoCredit')}» بگذار.")
        week_label = kalam_value("morningKalamWeekLabel")
        if week_label and calendar_lines:
            kalam_sections.append("یک کارت تقویم هفتگیِ شیشه‌ای و چشمگیر بساز. عنوان ماه/سال را دقیقاً بنویس: «%s». این هفت خانه دقیقاً روزهای هفته‌اند و ترتیب‌شان قطعی است: شنبه، یکشنبه، دوشنبه، سه‌شنبه، چهارشنبه، پنج‌شنبه، جمعه. فقط یکی از این دو چیدمان را انتخاب کن: یک ردیف افقی راست‌به‌چپ که شنبه در راست‌ترین خانه و جمعه در چپ‌ترین خانه باشد؛ یا یک ستون عمودی از بالا به پایین که شنبه در بالا و جمعه در پایین باشد. نام کامل هر روز را دقیقاً همان‌گونه که زیر آمده بنویس؛ هیچ مخفف، حرف تک‌نفره، نام ساختگی، ترتیب دیگر یا روز تکراری نساز. خودِ کلمات راهنما مانند «کارت»، «تقویم»، «امروز» یا «تعطیل» را روی طرح ننویس؛ فقط نام روزها و تاریخ‌های زیر را با وضعیت بصری تعیین‌شده نمایش بده:\n%s" % (week_label, "\n".join(calendar_lines)))
        if kalam_value("morningKalamOccasion"):
            kalam_sections.append(occasion_instruction(kalam_value("morningKalamOccasion"), "در زیر تاریخ‌های هفته و در همان کارت"))
        if puzzle_count:
            kalam_sections.append(f"{fa_number(puzzle_count)} تصویر آخرِ مرجع، فایل‌های ایموجیِ معمای تصویری هستند، نه عکس پس‌زمینه. زمینهٔ آن‌ها را حذف کن، خودِ ایموجی‌ها را بدون تغییر معنا، رنگ یا جزئیات نگه دار و در یک کارت مستقل و هنرمندانه بچین. بالای این کارت فقط دقیقاً بنویس: «معمای تصویری». پایین آن فقط و با اندازهٔ کوچک دقیقاً بنویس: «پاسخ معمای امروز را برامون بفرستین.» هیچ کلمهٔ اضافی مانند «کارت»، «ایموجی» یا «آیکون» ننویس.")
        elif kalam_value("morningVisualRiddleIdea"):
            kalam_sections.append(f"در یک کارت مستقل و هنرمندانه، این معمای تصویریِ پیشنهادی را با عناصر دیداریِ واضح و بدون پاسخ اجرا کن: «{kalam_value('morningVisualRiddleIdea')}». بالای کارت فقط دقیقاً بنویس: «معمای تصویری». پایین آن فقط و با اندازهٔ کوچک دقیقاً بنویس: «پاسخ معمای امروز را برامون بفرستین.» هیچ کلمهٔ اضافی مانند «کارت»، «ایموجی»، «آیکون» یا پاسخ معما ننویس.")
        else:
            kalam_sections.append("برای معمای تصویری، یک کارت خالی و مجله‌ای با فضای کافی بساز؛ بالای آن فقط «معمای تصویری» و پایین آن فقط «پاسخ معمای امروز را برامون بفرستین.» بنویس. ایموجی یا معمای حدسی تولید نکن.")
        kalam_sections.append("سه واترمارک هویت رسانه را پراکنده، ظریف و کم‌رنگ روی خودِ عکس اصلی بگذار؛ روی کارت تقویم یا کارت معما قرار نگیرند.")
        if main_photo_count and image_mode in {"generate", "preserve", "reference"}:
            kalam_sections.append("فقط تصاویر مرجعِ اصلی را برای عکس بدنه در نظر بگیر؛ فایل‌های معمای تصویری را هرگز به‌عنوان عکس پس‌زمینه، کولاژ خبری یا سوژهٔ اصلی استفاده نکن. " + image_instructions[image_mode])
        elif not main_photo_count:
            kalam_sections.append("برای بدنهٔ عکس، تصویر یا سوژهٔ شانسی تولید نکن؛ پالت، نور و بافت را از هویت رنگی رسانه و کارت‌های صبحگاهی بساز.")
        form_modules.append(module("قالب اختصاصی صبح بخیر کلام", "\n\n".join(kalam_sections)))
    elif template == "citizen_message":
        def citizen_value(name: str) -> str:
            return str(content.get(name, "")).strip()

        message_type = citizen.get("messageType", "text")
        citizen_photo_frame = citizen.get("photoFrame", "full")
        citizen_video_frame = citizen.get("videoFrame", "landscape")
        message_text = citizen_value("citizenMessageText")
        message_length = len(message_text)
        bubble_size = "کوتاه و جمع‌وجور" if message_length <= 180 else "متوسط و جادار" if message_length <= 650 else "بزرگ و غالب، با ظرفیت چند پاراگراف"
        citizen_sections = [
            "یک استوری پیام مردمیِ مدرن، قابل‌اعتماد و در سطح یک طراحی مجله‌ای ممتاز بساز؛ نه یک قالب خبری قرمز. پالت اصلی باید فیروزه‌ای/آبی، با تضاد حرفه‌ای، شیشه‌های ظریف، نور کنترل‌شده و جزئیات گرافیکی محدود باشد.",
            f"در بدنه، یک ترکیب‌بندی الهام‌گرفته از صفحهٔ گفت‌وگو بساز؛ بدون لوگوی پیام‌رسان، نام اپ، زمانِ ساختگی، تیک پیام، متن آزمایشی یا حباب‌های تصادفی. یک حباب گفت‌وگوی اصلیِ {bubble_size} با فضای داخلی کاملاً خالی بساز. متن پیام مردمی را روی تصویر ننویس؛ فقط همین فضای خالی را متناسب با طول واقعیِ پیامِ ثبت‌شده ({fa_number(message_length)} نویسه) آماده کن تا تحریریه بعداً متن را دستی و دقیق وارد کند.",
            "در پایین طرح، دقیقاً و با فارسی صحیح این متن ثابت را کوچک، خوانا و در یک ناحیهٔ اطلاع‌رسانیِ آرام بنویس: «کلام تازه، محتوای ارسالی توسط هیچ یک از مخاطبان را تایید یا رد نمی‌کند و انتشار آن صرفاً جهت اطلاع مسئولین است.»",
        ]
        sender_context = citizen_value("senderContext")
        known_city = "گلبهار" if "گلبهار" in sender_context else "چناران" if "چناران" in sender_context else ""
        if known_city:
            citizen_sections.append(f"برای معرفی پیام، فقط در صورت نیاز به یک سطر انتساب، دقیقاً از این عبارت استفاده کن: «مخاطب کلام تازه از {known_city} برایمان نوشت:». هرگز «به گزارش کلام تازه» ننویس و شهر دیگری حدس نزن.")
        else:
            citizen_sections.append("اگر برای معرفی پیام به یک سطر انتساب نیاز بود، فقط یکی از این عبارت‌های طبیعی را به‌کار ببر: «به گفته مخاطب کلام تازه»، «طبق پیام مخاطب کلام تازه» یا «مخاطب کلام تازه در پیامی نوشت:». هرگز «به گزارش کلام تازه» ننویس؛ مکان/شهر را هم بدون تصریح کاربر حدس نزن.")
        headline = citizen_value("citizenHeadline")
        if headline:
            citizen_sections.append(f"تیتر مستقل را خارج از حباب اصلی، با تایپوگرافی شاخص اما محترمانه و دقیقاً بدون تغییر بنویس: «{headline}». خود کلمهٔ «تیتر» را ننویس.")
        response = citizen_value("citizenResponse")
        if response:
            citizen_sections.append(f"یک حباب پاسخ مستقل با سلسله‌مراتب بصری متفاوت و محترمانه بساز و دقیقاً این پاسخ کلام تازه را در آن بنویس: «{response}». هیچ پاسخ یا توضیح دیگری اضافه نکن.")
        interaction = citizen_value("citizenInteraction")
        if interaction:
            citizen_sections.append(f"یک کارت تعامل کوچک و جدا از متن ثابت در پایین طرح بساز و دقیقاً بنویس: «{interaction}».")
        if message_type == "photo":
            citizen_sections.append("این پیام شامل عکس است. " + photo_frame_instructions.get(citizen_photo_frame, photo_frame_instructions["full"]))
            if image_mode == "none":
                citizen_sections.append("عکس یا سوژهٔ شانسی تولید نکن؛ بدنه را با بافت، نور و گرافیک فیروزه‌ایِ حرفه‌ای کامل کن.")
            else:
                citizen_sections.append(image_instructions[image_mode])
        elif message_type == "video":
            ratio = {"landscape": "۱۶:۹ افقی", "square": "۱:۱ مربع", "portrait": "۹:۱۶ عمودی"}.get(citizen_video_frame, "۱۶:۹ افقی")
            citizen_sections.append(f"این پیام شامل فیلم است: یک قاب ویدیوییِ بزرگ، خالی، بدون متن، آیکون پخش یا تصویر فرضی، با نسبت {ratio} بساز. قاب باید بخش مهمی از بدنه باشد و برای جای‌گذاری فیلم در مرحلهٔ بعد فضای کافی داشته باشد.")
            if image_mode != "none":
                citizen_sections.append(f"اگر عکس مرجع پیوست شده، {image_instructions[image_mode]} این تصویر فقط پس‌زمینهٔ بیرون قاب فیلم است و نباید وارد فضای خالی فیلم شود.")
            else:
                citizen_sections.append("بدون عکس مرجع، پس‌زمینه را فقط با پالت فیروزه‌ای، بافت و نور گرافیکی بساز؛ صحنه یا سوژهٔ شانسی تولید نکن.")
        else:
            citizen_sections.append("این پیام فقط متن است؛ هیچ عکس، سوژه یا قاب رسانه‌ای فرضی تولید نکن و تمرکز را روی گفت‌وگوی خالی، تیتر احتمالی و گرافیک فیروزه‌ای نگه دار.")
        form_modules.append(module("قالب اختصاصی کلام مردم", "\n\n".join(citizen_sections)))
    elif template == "sticker":
        kind = {"news": "خبری", "promotion": "تبلیغاتی"}.get(str(content.get("stickerKind", "news")), "خبری")
        sticker_text = str(content.get("stickerText", "")).strip()
        sticker_subtext = str(content.get("stickerSubtext", "")).strip()
        sticker_sections = [
            f"یک استیکر {kind} با لبه‌های تمیز و سیلوئتِ مستقل بساز. متن اصلی را دقیقاً بنویس: «{sticker_text}».",
            "کل بوم مربع PNG باید بیرون از خودِ استیکر واقعاً شفاف باشد؛ پس‌زمینه، مستطیل سفید، رنگ تخت، شطرنجی یا صحنه نساز. سایه فقط اگر وجود دارد، نرم و محدود به اطراف خود استیکر باشد.",
        ]
        if kind == "خبری":
            sticker_sections.append("لحن بصری باید ژورنالیستی، فاخر و تحریریه‌ای باشد؛ شبیه لیبل خبر فوریِ معتبر یا نشان یک پروندهٔ خبری ممتاز، نه استیکر کودکانه، ایموجی، برچسب فروش یا دعوت تبلیغاتی. از یک شکل هندسیِ ساده اما متمایز (نشان نواریِ نامتقارن، پلاک زاویه‌دارِ متعادل یا مُهرِ مدرن) با نسبت‌های دقیق و فضای تنفس کافی استفاده کن. تایپوگرافی فارسی را با وزنِ تیترِ روزنامه‌ایِ جدی، حروف خوش‌خوان، کرنینگ دقیق، شکست خطِ سنجیده و سلسله‌مراتب روشن طراحی کن؛ از فونت فانتزی، حبابی، دست‌نویس، کشیده‌نویسی افراطی، افکت سه‌بعدی، استروک ضخیم و رنگ‌های جیغ دوری کن. نهایتاً یک نشانهٔ خبری انتزاعی و بسیار محدود مجاز است؛ هیچ آیکون کلیشه‌ای یا تزئین اضافه نیاور.")
        if sticker_subtext:
            sticker_sections.append(f"متن تکمیلی را کوچک‌تر و دقیقاً بنویس: «{sticker_subtext}».")
        form_modules.append(module("قالب اختصاصی استیکر شفاف", "\n\n".join(sticker_sections)))
    elif template == "poster":
        def poster_value(name: str) -> str:
            return str(content.get(name, "")).strip()

        purpose_labels = {
            "promotion": "تبلیغ / معرفی",
            "campaign": "کمپین و فراخوان",
            "event": "رویداد و برنامه",
            "media": "معرفی رسانه یا کانال",
            "announcement": "اطلاعیه",
        }
        style_instructions = {
            "modern": "مدرن و مجله‌ای: گرید روشن، عمق ظریف، کنتراست دقیق و تایپوگرافی معاصر.",
            "bold": "جسور و پرانرژی: یک نقطهٔ کانونی قوی، حرکت کنترل‌شده و تضاد بالا؛ اما نه شلوغ یا ارزان.",
            "luxury": "لوکس و مینیمال: فضای تنفس فراوان، متریال و نور کنترل‌شده، جزئیات کم اما دقیق.",
            "local": "گرم و محلی: حس انسانی و اصیل، بدون کلیشه یا نماد مکانِ حدسی.",
            "corporate": "رسمی و سازمانی: گرید منظم، قابل‌اعتماد، واضح و بدون تزئین اضافی.",
        }
        poster_sections = [
            "یک پوستر نهایی و آمادهٔ انتشار بساز؛ این قالب آزاد اما ساختارمند است و باید برای تبلیغ، معرفی رسانه/کانال، کمپین، برنامه یا اطلاعیه قابل استفاده باشد. اثر باید در نگاه اول پیام اصلی را منتقل کند، در اندازهٔ کوچک موبایل خوانا بماند و حس یک آرت‌دایرکشن حرفه‌ای داشته باشد؛ نه فلایر آماده، نه بنر ارزان و نه موکاپ.",
            f"کاربری پوستر: «{purpose_labels.get(poster_value('posterPurpose'), 'تبلیغ / معرفی')}». حال‌وهوای انتخاب‌شده: {style_instructions.get(poster_value('posterStyle'), style_instructions['modern'])}",
        ]
        headline = poster_value("posterHeadline")
        if headline:
            poster_sections.append(f"پیام اصلی و قهرمان پوستر را دقیقاً، بدون تغییر، خلاصه‌سازی یا افزودن واژه بنویس: «{headline}». این بزرگ‌ترین متن طرح است و باید فضای کافی، کنتراست واقعی و شکست سطر آگاهانه داشته باشد.")
        subheadline = poster_value("posterSubheadline")
        if subheadline:
            poster_sections.append(f"زیرپیام را فقط به‌عنوان متن ثانویه و دقیقاً با این رشته بنویس: «{subheadline}». آن را با تیتر اصلی قاطی نکن.")
        body = poster_value("posterBody")
        if body:
            poster_sections.append(f"جزئیات تکمیلیِ تأییدشده را دقیقاً و خوانا بنویس: «{body}». اگر چندخطی است، آن را در یک ناحیهٔ اطلاعاتیِ مستقل با سلسله‌مراتب آرام بچین؛ هیچ تاریخ، مزیت، آدرس، قیمت یا ادعای تازه‌ای نساز.")
        cta = poster_value("posterCta")
        if cta:
            poster_sections.append(f"یک دعوت به اقدامِ مشخص، کوچک‌تر از تیتر و جدا از جزئیات بساز و دقیقاً این متن را بنویس: «{cta}». دکمهٔ جعلی، QR، نشانی یا لینک ساختگی تولید نکن.")
        poster_sections.append("از نماد، چهره، محصول، لوگو، نشانی وب، شماره تماس یا تخفیفِ فرضی استفاده نکن. اگر تصویر مرجع وجود دارد، فقط طبق حالت انتخابی کاربر از آن استفاده کن. سه واترمارک رسانه فقط روی زمینه/تصویر بدنه، ظریف و کم‌رنگ باقی بمانند و وارد متن اصلی نشوند.")
        form_modules.append(module("قالب اختصاصی پوستر حرفه‌ای", "\n\n".join(poster_sections)))
    elif template == "classifieds":
        raw_ads = content.get("classifiedsJson", "[]")
        try:
            parsed_ads = json.loads(raw_ads) if isinstance(raw_ads, str) else raw_ads
        except (TypeError, json.JSONDecodeError):
            parsed_ads = []
        category_meta = {
            "lost_found": ("گمشده / پیدا شده", "ذره‌بین یا برچسبِ پیدا/گم‌شده"),
            "job_seeker": ("جویای کار", "شخص با رزومه یا کیف کوچک"),
            "hiring": ("استخدام", "کیف کاری با نشان کوچکِ افزودن"),
            "services": ("خدمات", "آچار یا ابزار مینیمال"),
            "housing": ("مسکن", "خانهٔ مینیمال"),
            "other": ("سایر", "سنجاق آگهی مینیمال"),
        }
        ads: list[dict[str, str]] = []
        if isinstance(parsed_ads, list):
            for item in parsed_ads[:4]:
                if not isinstance(item, dict):
                    continue
                category = str(item.get("category") or "other")
                ads.append({
                    "category": category if category in category_meta else "other",
                    "title": str(item.get("title") or "").strip()[:56],
                    "body": str(item.get("body") or "").strip()[:220],
                    "contact": str(item.get("contact") or "").strip()[:96],
                })
        classified_sections = [
            "یک صفحهٔ نیازمندیِ فارسی با روح روزنامهٔ حرفه‌ای و امروزی بساز؛ کاغذ، خط‌کشی بسیار ظریف، گرید منظم، سلسله‌مراتب واضح و حس معتبر داشته باشد، نه روزنامهٔ کهنه، شلوغ یا کپی‌شده. ناحیهٔ امن بالای رسانه را خالی و پیوسته با زمینه نگه دار.",
            f"دقیقاً {fa_number(len(ads))} آگهیِ واقعی زیر را نمایش بده؛ نه آگهی خالی، نه کارت نمونه، نه ستون اضافی و نه متن فرضی. اگر فقط یک آگهی داریم، همان یک آگهی باید با کیفیت و فضای کافی طراحی شود؛ اگر دو تا چهار آگهی داریم، گرید را متناسب با همان تعداد تنظیم کن.",
            "هر آگهی یک کادر مستقل، بسته و کاملاً جدا با مرز/خط ظریف خودش دارد. متن، راه تماس، آیکون یا رنگ هیچ آگهی نباید وارد کادر آگهی دیگر شود. تیتر هر آگهی از متن آن بزرگ‌تر باشد، راه تماس در پایین همان کادر بماند و یک آیکون کوچکِ مرتبط فقط به همان آگهی تعلق داشته باشد. هیچ شماره، راه تماس، عنوان یا آیکون حدسی اضافه نکن.",
        ]
        for index, ad in enumerate(ads, start=1):
            category_label, icon = category_meta[ad["category"]]
            classified_sections.append(
                f"آگهی {fa_number(index)} — دسته: «{category_label}»؛ آیکون مجاز: {icon}. "
                f"تیتر را دقیقاً بنویس: «{ad['title']}». "
                f"متن را دقیقاً بنویس: «{ad['body']}». "
                f"راه ارتباطی را دقیقاً و در پایینِ همان کادر بنویس: «{ad['contact']}»."
            )
        classified_sections.append("پالت روزنامه‌ایِ گرم، خاکستری-کرم و مشکیِ خوانا داشته باش و فقط برای هر دسته یک تأکید رنگی بسیار محدود استفاده کن. تصویر، چهره، آگهی، شماره تلفن، QR، قیمت، لوگو یا نشانی ساختگی تولید نکن. سه واترمارک رسانه را بسیار ظریف و دور از متن آگهی‌ها، فقط در بافت پس‌زمینه قرار بده.")
        form_modules.append(module("قالب اختصاصی آگهی نیازمندی‌ها", "\n\n".join(classified_sections)))
    elif template == "market":
        def market_value(name: str) -> str:
            return str(content.get(name, "")).strip()

        rates = (
            ("دلار", "marketUsdPrice", "marketUsdChange", "تومان"),
            ("یورو", "marketEurPrice", "marketEurChange", "تومان"),
            ("تمام سکه", "marketCoinPrice", "marketCoinChange", "تومان"),
            ("طلای ۱۸ عیار", "marketGold18Price", "marketGold18Change", "تومان"),
            ("بیت‌کوین", "marketBitcoinPrice", "marketBitcoinChange", "دلار آمریکا"),
        )
        date_lines = [item for item in (market_value("marketWeekday"), market_value("marketPersianDate"), market_value("marketGregorianDate"), market_value("marketHijriDate")) if item]
        market_sections = [
            "یک استوری قیمت روز طلا و ارز در سطح یک مجلهٔ اقتصادی ممتاز بساز؛ ظاهر، گرید و آیکون‌ها اختصاصیِ بازار باشند، نه قالب خبر. پالت پایه طلاییِ لوکس، ذغالی تیره و سفید گرم باشد؛ نور کنترل‌شده، شیشه‌های ظریف، بافت فلزی بسیار محدود و فضای تنفس حرفه‌ای داشته باش. از نمودار بورسِ ساختگی، اعداد تصادفی، لوگوی صرافی یا صفحهٔ تریدینگ اجتناب کن.",
            "در بالا یک عنوان شاخص و دقیقاً با فارسی صحیح بنویس: «قیمت روز طلا و ارز». زیر آن تاریخ و زمان را در یک ناحیهٔ ظریف و قابل اسکن درج کن. این داده‌ها را دقیقاً و بدون تغییر بنویس:\n" + "\n".join(f"- {line}" for line in date_lines + ([f"ساعت دریافت: {market_value('marketTime')}" ] if market_value("marketTime") else [])),
            "پنج ویجت نرخ هم‌اندازه اما با هویت آیکونی متفاوت بساز: دلار، یورو، تمام سکه، طلای ۱۸ عیار و بیت‌کوین. هر ویجت باید نام، مبلغ و واحدِ مشخص‌شده را با سلسله‌مراتب خوانای فارسی داشته باشد. هیچ قیمت یا واحدی را حدس نزن و هیچ مورد دیگری به این پنج‌گانه اضافه نکن.",
        ]
        for label, price_key, change_key, unit in rates:
            price = market_value(price_key)
            change = market_value(change_key)
            if not price:
                continue
            rate_line = f"- {label}: مبلغ دقیق «{price} {unit}»"
            if change:
                stripped_change = change.strip().replace("−", "-")
                if stripped_change.startswith("-"):
                    rate_line += f"؛ تغییر ۲۴ساعته دقیق «{change}٪» با فلش کوچک مینیمال قرمز رو به پایین"
                elif stripped_change.startswith("+"):
                    rate_line += f"؛ تغییر ۲۴ساعته دقیق «{change}٪» با فلش کوچک مینیمال سبز رو به بالا"
                else:
                    rate_line += f"؛ تغییر ۲۴ساعته دقیق «{change}٪» با خط افقی مینیمال و رنگ خنثی"
            else:
                rate_line += "؛ هنوز تغییر ۲۴ساعتهٔ تأییدشده نداریم: فلش، درصد، صفر یا برچسب جایگزین نساز"
            market_sections.append(rate_line)
        if market_value("marketSource"):
            market_sections.append(f"در پایین طرح، یک نشان کوچک و محدودِ منبع/زمان بساز و دقیقاً بنویس: «منبع: {market_value('marketSource')}»؛ این نشان فقط به اندازهٔ متن خودش باشد.")
        market_sections.append("روی عکس یا بافتِ اصلیِ بدنه، نه روی ویجت‌ها، سه واترمارک پراکنده، ظریف و کم‌رنگ از آیدی رسانه قرار بده. تصویر خبری، آدم، پولِ واقعی، اسکناس، سکه یا سوژهٔ تصادفی تولید نکن؛ گرافیک بازار باید انتزاعی، حرفه‌ای و در خدمت داده‌های تأییدشده بماند.")
        form_modules.append(module("قالب اختصاصی قیمت روز طلا و ارز", "\n\n".join(market_sections)))
    elif template == "sport":
        def sport_value(name: str) -> str:
            return str(content.get(name, "")).strip()

        mode = sport_value("sportMode")
        mode_label = {"result": "اعلام نتیجه", "league": "نتایج هفتهٔ لیگ", "upcoming": "بازی‌های مهم پیش رو", "news": "خبر ورزشی یا رقابت محلی"}.get(mode, "محتوای ورزشی")
        sport_sections = [
            f"یک استوری ورزشی مدرن، سریع و حرفه‌ای برای «{mode_label}» بساز. گرید نتیجه/برنامه باید بسیار خوانا، پرانرژی و مناسب موبایل باشد؛ از اسکوربورد خیالی، آمار حدسی، لوگوی جعلی تیم یا جام/مدالِ بی‌ربط پرهیز کن.",
        ]
        if sport_value("title"):
            sport_sections.append(f"تیتر را دقیقاً بدون تغییر بنویس: «{sport_value('title')}». هیچ برچسب «تیتر» اضافه نکن.")
        if sport_value("sportResults"):
            sport_sections.append(f"این داده‌های ورزشی تأییدشده را دقیقاً، خط‌به‌خط و بدون تغییر در کارت‌ها/ردیف‌های حرفه‌ای نمایش بده:\n{sport_value('sportResults')}")
        else:
            sport_sections.append("دادهٔ نتیجه یا برنامه وارد نشده است؛ عدد، نتیجه، رتبه، تیم یا نام ورزشکار حدس نزن و فقط یک ترکیب‌بندی بصری مرتبط و جای خالیِ خوانا آماده کن.")
        if sport_value("sportSource"):
            sport_sections.append(f"منبع داده را کوچک و دقیقاً چنین بنویس: «منبع: {sport_value('sportSource')}».")
        form_modules.append(module("قالب اختصاصی استوری ورزشی", "\n\n".join(sport_sections)))
    elif template == "infographic":
        def infographic_value(name: str) -> str:
            return str(content.get(name, "")).strip()

        info_sections = ["یک اینفوگرافی مستقل، حرفه‌ای، قابل‌اسکن و مناسب استوری/پست بساز؛ با گرید روشن، آیکون‌های محدود و دقیق و سلسله‌مراتب دادهٔ واضح. نمودار، عدد یا واقعیتی که در داده‌های کاربر نیست نساز."]
        for label, key in (("روتیتر", "kicker"), ("تیتر", "title"), ("زیرتیتر", "subtitle")):
            if infographic_value(key):
                info_sections.append(f"{label} را دقیقاً و بدون تغییر بنویس: «{infographic_value(key)}».")
        if infographic_value("dataPoints"):
            info_sections.append(f"داده‌های تأییدشده را هر مورد در یک عنصر بصری مستقل و دقیق نمایش بده:\n{infographic_value('dataPoints')}")
        if infographic_value("source"):
            info_sections.append(f"در پایین یک نشان کوچک فقط به اندازهٔ متن منبع بنویس: «منبع: {infographic_value('source')}».")
        form_modules.append(module("قالب اختصاصی اینفوگرافی", "\n\n".join(info_sections)))
    elif template in {"night", "home_tip"}:
        def lifestyle_value(name: str) -> str:
            return str(content.get(name, "")).strip()

        if template == "night":
            kind = {"film": "فیلم", "series": "سریال", "album": "آلبوم موسیقی", "book": "کتاب"}.get(lifestyle_value("nightKind"), "اثر فرهنگی")
            sections = [f"یک استوری شبانهٔ ممتاز برای معرفی {kind} بساز: بنفش عمیق و مشکیِ کنترل‌شده، حس فرهنگی/سینمایی، مدرن و دور از کلیشهٔ نئون یا پوستر تقلیدی."]
        else:
            sections = ["یک استوری ترفند خانه‌داریِ روشن، تمیز، گرم و کاربردی با حس مجلهٔ سبک زندگی بساز. از ادعاهای درمانی، خطرناک یا مواد/نتایج ساختگی پرهیز کن."]
        if lifestyle_value("title"):
            sections.append(f"عنوان را دقیقاً و بدون تغییر بنویس: «{lifestyle_value('title')}».")
        if lifestyle_value("caption"):
            sections.append(f"توضیح کوتاه را دقیقاً و بدون تغییر بنویس: «{lifestyle_value('caption')}».")
        form_modules.append(module("قالب اختصاصی شبانه / خانه‌داری", "\n\n".join(sections)))
    elif template == "editorial_note":
        def note_value(name: str) -> str:
            return str(content.get(name, "")).strip()

        note_title = note_value("title")
        note_body = note_value("caption")
        note_author = note_value("source")
        note_style = note_value("editorialNoteStyle") or "auto"
        body_words = len(note_body.split())
        style_instruction = {
            "modern_statement": "این یک حرف/یادداشت مدرن است: ترکیب‌بندی معاصر، جسور اما آرام، با فضای منفیِ هوشمند و تایپوگرافیِ تحریریه‌ای داشته باشد. آن را به کاغذ، نامه، دفتر، دست‌نوشته یا بافت کاغذی تبدیل نکن.",
            "personal_message": "این یک پیام مستقیم و انسانی است: صمیمیتِ کنترل‌شده، حضور رسانه‌ای معتبر و گرید مینیمال داشته باشد. از قاب نامه، کاغذ، قلم، دفتر یا تزئینات نوستالژیک استفاده نکن.",
            "progress_report": "این یک گزارش عملکرد یا بازدید صفحه است: ظاهر داشبورد رسانه‌ایِ مدرن، دقیق و قابل‌اعتماد با گرید دیجیتال و سلسله‌مراتب داده داشته باشد. آن را به کاغذ، نامه، دفتر، دست‌نوشته یا بافت کاغذی تبدیل نکن. اگر اسکرین‌شات مرجع وجود دارد، همان اسکرین‌شات سند اصلی طرح است؛ نمودار، عدد، رابط کاربری یا آماری خارج از آن نساز.",
            "auto": "حالت بصری را از متن و تصویر مرجع تشخیص بده: می‌تواند یک حرف مدرن، پیام انسانی یا گزارش عملکرد باشد. هرگز به‌صورت پیش‌فرض از کاغذ، نامه، دفتر، دست‌نوشته یا بافت کاغذی استفاده نکن؛ این عناصر فقط وقتی مجازند که کاربر صریحاً درخواست کرده باشد.",
        }.get(note_style, "حالت بصری مدرن و رسانه‌ای باشد؛ از تم کاغذی یا نامه‌ای پیش‌فرض استفاده نکن.")
        note_sections = [
            "یک یادداشت سردبیر/ادمین برای اینستاگرام بساز؛ ظاهر آن بسیار حرفه‌ای، رسانه‌ای، امروزی و متناسب با هدف کاربر باشد، نه خبر فوری، پوستر تبلیغاتی یا نقل‌قول انگیزشی. هویت رنگی رسانه را با زمینهٔ روشن یا تیره، نور کنترل‌شده، گرید مجله‌ای/دیجیتال و رنگ برندِ تأکیدی به‌کار ببر؛ کل صفحه را با یک رنگ سنگین و یکنواخت پُر نکن.",
            style_instruction,
        ]
        if note_title:
            note_sections.append(f"عنوان یادداشت را دقیقاً، بدون هیچ اصلاح، حذف یا افزودن، به‌عنوان قهرمان بصری طرح بنویس: «{note_title}». فارسی آن باید در نمای کوچک کاملاً خوانا باشد و حداکثر دو رنگ داشته باشد. هیچ برچسبی مثل «یادداشت»، «تیتر» یا «سردبیر می‌نویسد» کنار آن ننویس.")
        if note_body:
            if body_words <= 34 and "\n" not in note_body:
                note_sections.append(f"متن یادداشت کوتاه است؛ آن را دقیقاً و خوانا {'به‌عنوان قهرمان اصلی طرح' if not note_title else 'با سلسله‌مراتب پایین‌تر از عنوان'} بنویس: «{note_body}». قرارداد انحصاری: هیچ پنل، باکس یا فضای نوشتنِ خالیِ دیگری برای متن یادداشت نساز.")
            else:
                note_sections.append(f"متن یادداشت طولانی است ({fa_number(body_words)} واژه). قرارداد انحصاری: یک فضای نوشتنِ خالی، بزرگ، تمیز و متناسب با چند پاراگراف در بدنه بساز، اما حتی یک واژه، خلاصه، نقل‌قول، عدد، متن آزمایشی یا خط نمایشی از این متن را روی طرح ننویس. تحریریه متن دقیق را بعداً دستی اضافه می‌کند.")
        if note_author:
            note_sections.append(f"در انتهای یادداشت، یک امضای کوچک و محترمانه، دقیقاً به این شکل بنویس: «{note_author}». آن را منبع خبر یا آیدی شبکه اجتماعی نشان نده.")
        if image_mode == "preserve":
            note_sections.append("تصویر/اسکرین‌شات مرجع یک سند قفل‌شده و جزء اصلی طرح است: خودِ پیکسل‌ها، چهره‌ها، متن‌ها، نمودارها، رابط کاربری، آمار، رنگ‌ها، لوگوهای درون تصویر و معنای آن را دقیقاً حفظ کن. بازسازی، زیباسازیِ مولد، روتوش چهره، تغییر چهره/بدن، تبدیل اسکرین‌شات به رابط خیالی، حذف یا افزودن جزئیات، جایگزینی داده یا تولید تصویر مشابه ممنوع است. فقط جای‌گذاری متناسب، بزرگ/کوچک‌کردنِ نسبی و در صورت ضرورت امتدادِ کاملاً خنثیِ بیرون قاب مجاز است. تصویر مرجع باید واقعاً در خروجی نهایی دیده شود، نه صرفاً الهام آن.")
        elif image_mode in {"generate", "reference"}:
            note_sections.append("در صورت وجود تصویر مرجع، آن باید بخش اصلی یا مکملِ معنادار طرح باشد و خوانایی متن را مختل نکند. " + image_instructions[image_mode])
        else:
            note_sections.append("بدون عکس مرجع، از تصویر، چهره، لوگو یا سوژهٔ تصادفی استفاده نکن؛ با رنگ برند، بافت کنترل‌شده، نور و گرافیک تحریریه‌ایِ ظریف طرح را کامل کن.")
        note_sections.append("سه واترمارک هویت رسانه را فقط روی بافت/تصویر بدنه، بسیار ظریف و کم‌رنگ بگذار؛ هرگز روی تیتر، پنل یادداشت یا امضا قرار نگیرند.")
        form_modules.append(module("قالب اختصاصی یادداشت سردبیر / ادمین", "\n\n".join(note_sections)))
    elif template == "occasion_greeting":
        def occasion_value(name: str) -> str:
            return str(content.get(name, "")).strip()

        tone = occasion_value("occasionTone")
        category = occasion_value("occasionCategory")
        name = occasion_value("occasionName")
        date = occasion_value("occasionDate")
        headline = occasion_value("occasionHeadline")
        message = occasion_value("occasionMessage")
        signature = occasion_value("occasionSignature")
        tone_label = "تبریک" if tone == "congratulation" else "تسلیت"
        category_label = {
            "religious": "مذهبی", "national": "ملی", "global": "جهانی", "public": "عمومی / اجتماعی", "cultural": "فرهنگی / هنری", "custom": "سایر",
        }.get(category, "عمومی")
        occasion_sections = [
            f"این یک طرح {tone_label} برای مناسبت {category_label} است؛ لحن، نور، بافت، عناصر بصری و شدت رنگ باید دقیقاً با همین حس هماهنگ باشد. طراحی فاخر، مدرن، مجله‌ای و محترمانه باشد، نه کارت آماده، پوستر کلیشه‌ای یا طرح تبلیغاتی ارزان.",
        ]
        if name:
            occasion_sections.append(f"مناسبت/مناسبت‌های انتخاب‌شده را دقیقاً و بدون تغییر در سلسله‌مراتب مناسب بنویس: «{name}». هیچ نام شخصیت، نماد یا رویداد دیگری را حدس نزن.")
        if headline:
            occasion_sections.append(f"عنوان اصلی و قهرمان تایپوگرافی را دقیقاً و بدون هیچ تغییر بنویس: «{headline}». این عبارت باید بزرگ، برجسته و نخستین نقطهٔ خوانش طرح باشد.")
        if date:
            occasion_sections.append(f"این عبارت تکمیلی را فقط یک‌بار، کوچک‌تر و دقیقاً بدون تغییر در گرید مناسب بنویس: «{date}».")
        if message:
            message_words = len(message.split())
            if message_words <= 28:
                occasion_sections.append(f"پیام کوتاه را دقیقاً و بدون تغییر، خوانا و پایین‌تر از عبارت اصلی بنویس: «{message}».")
            else:
                occasion_sections.append(f"پیام کاربر طولانی است ({fa_number(message_words)} واژه). یک فضای نوشتنِ خالی، بزرگ، حرفه‌ای و متناسب با چند خط متن در بدنه رزرو کن؛ متن، لورم‌ایپسوم، خط‌های نمایشی یا نسخهٔ خلاصه‌شدهٔ پیام را ننویس تا تحریریه آن را بعداً دقیقاً اضافه کند.")
        if signature:
            occasion_sections.append(f"پایین طرح یک امضای کوچک، آرام و دقیقاً با این عبارت بنویس: «{signature}». این امضا باید از عنوان و پیام کوچک‌تر باشد و با واترمارک اشتباه نشود.")
        if tone == "condolence":
            occasion_sections.append("فضا آرام، باوقار و همدلانه باشد؛ از چهرهٔ ساختگی، تصویر فرد، صحنهٔ سوگواری، شمع، گل یا نماد مذهبی/ملیِ حدسی استفاده نکن. تنها در صورت وجود عکس مرجع، همان عکس با حفظ معنا می‌تواند مبنای تصویر باشد.")
        else:
            occasion_sections.append("فضا باوقار، روشن و امیدوار باشد؛ از بادکنک، کاغذرنگی، کیک، هدیه، پرچم، شخصیت یا نماد حدسی و کودکانه استفاده نکن، مگر آن‌که از عکس مرجع یا توضیحات تکمیلی کاربر صراحتاً برآید.")
        occasion_sections.append("سه واترمارک هویت رسانه را فقط روی بافت یا عکس بدنه، بسیار ظریف و کم‌رنگ بگذار؛ هرگز روی متن اصلی یا فضای نوشتن قرار نگیرند.")
        form_modules.append(module("قالب اختصاصی تبریک / تسلیت مناسبت‌ها", "\n\n".join(occasion_sections)))
    elif template == "studio" or is_studio_image:
        sections = app.studio_image_prompt_sections(studio)
        if hasattr(app, "studio_image_reference_contract"):
            sections.append(app.studio_image_reference_contract(request))
        form_modules.append(module("ساختار اختصاصی تصویر استودیو", "\n\n".join(item for item in sections if item)))
    elif is_news:
        caption_value = str(approved_copy.get("caption") or "").strip()
        caption_words = len(re.findall(r"\S+", caption_value))
        caption_is_long = caption_words > 55 or len(caption_value) > 360
        caption_panel_instruction = (
            "تیتر و عکس خبری، به‌علاوه یک پنل شیشه‌ایِ کاملاً خالی برای افزودن کپشن در مرحلهٔ بعد. "
            + ("کپشن تأییدشده طولانی است؛ بخش تصویر را جمع‌وجورتر نگه دار و پنل خالیِ بزرگ و غالب برای متن چندپاراگرافی بساز. " if caption_is_long else "کپشن تأییدشده کوتاه است؛ یک پنل خالی متناسب و خوانا در نیمهٔ پایین بساز. ")
            + "متن کپشن را فقط برای درک موضوع و اندازهٔ فضا بخوان؛ حتی یک کلمه از آن را در طرح ننویس. داخل پنل هیچ متن، عدد، آیکون یا متن آزمایشی ننویس."
        )
        if is_series_slide and slide_index > 1 and (caption_value or any(key == "caption" for key, _ in series_blank_fields)):
            form_modules.append(module("فضای کپشنِ قطعی این اسلاید", "این اسلاید، صفحهٔ ادامهٔ متنِ سری است. متن کپشنِ داده‌شده را فقط برای درک موضوع، تعداد سطرها و اندازهٔ فضای لازم بخوان؛ آن را، خلاصه‌اش، تیتر جایگزین یا هیچ نوشته‌ای را داخل تصویر ننویس. یک فضای خالیِ واقعی، بزرگ، آرام و متناسب با متن چندسطره در بدنه بساز. این فضا می‌تواند با نور، بافت و گرید طبیعی صحنه تعریف شود، اما باکس توخالی، خط‌کشی، کادر، رنگ جدا، برچسب، آیکون، لورم‌ایپسوم یا متن آزمایشی نداشته باشد. تیتر و تصویر را طوری بچین که وارد این فضای رزروشده نشوند.\n\nمتن کپشنِ فقط برای محاسبهٔ فضا (روی تصویر ننویس):\n«%s»" % series_caption_context))
        else:
            form_modules.append(module("نوع خروجی انتخاب‌شده", {
                "title_photo": "تیتر و عکس خبری؛ هیچ پنل خالی برای کپشن نساز.",
                "title_photo_caption": caption_panel_instruction,
                "title_only": "فقط تیتر؛ هیچ عکس خبری، قاب عکس یا سوژهٔ تصویری مستقل نساز.",
            }[output_kind]))
        form_modules.append(module("صفحه‌بندی انتخاب‌شده", layout_instructions[layout]))
        if template == "news_post":
            form_modules.append(module("استاندارد اختصاصی پست خبری ۴:۵", "این خروجی برای فید اینستاگرام است، نه برش استوری. گرید ۴:۵ را با نقطهٔ کانونی قوی، حاشیهٔ امن واقعی و خوانایی عالی در نمای کوچک فید طراحی کن. حتی با عکس تمام‌صفحه، جای انتخاب‌شدهٔ تیتر (بالا، وسط یا پایین) باید آگاهانه در خود عکس ساخته شود و رنگ/نور/بافتِ پشت متن تضاد لازم را فراهم کند. تیتر را جذاب و متنوع بچین: می‌توانی فقط یک واژهٔ مهم را بزرگ‌تر یا رنگی کنی، زیر یک بخش خط بکشی یا یک تأکید رنگی محدود بسازی، اما از نوار تیترِ تکراری، شلوغی و پوشاندن سوژهٔ مهم بپرهیز.\n\nرفتار هویت و ناحیهٔ امن فقط تابع ماژول فعال همین درخواست است. برای پروفایل شناور یا بدون پروفایل، فضای سربرگ سیستمی رزرو نکن. منبع و تعامل در صورت وجود، کوچک و در گرید مستقل باقی بمانند."))
        if has_news_photo:
            form_modules.append(module("ابعاد عکس خبر در بدنه", photo_frame_instructions[photo_frame]))
            # Crucially, this module is absent for title-only and video work.
            form_modules.append(module("نحوهٔ استفاده از عکس خبر", image_instructions[image_mode]))
            if template == "news_post" and image_mode == "preserve" and photo_frame in {"square", "landscape", "portrait_3_4"}:
                form_modules.append(module("ادامهٔ عکس مرجع تا ناحیهٔ امن بالا", "عکس مرجعِ اصلی را در قاب انتخاب‌شده دقیقاً حفظ کن؛ لبه‌های همان عکس را به‌صورت طبیعی و واقع‌گرایانه به سمت بالا گسترش بده (outpaint/extend) تا رنگ، نور، بافت و محیط همان عکس تا لبهٔ بالایی بوم ادامه یابد. ناحیهٔ بالا را بدون متن، لوگو، خط یا عنصر مهم نگه دار. اگر بالای عکس فضای خالی ندارد، امتداد طبیعی محیط/پس‌زمینه را بساز، ولی سوژه، چهره، لباس، مکان و محتوای اصلی عکس را تغییر نده. هرگونه پس‌زمینهٔ سفید، نوار سفید، کارت رنگی، قاب جدا یا قطع‌شدن عکس ممنوع است."))
            ai_photo_notice = {
                "generate": "عکس این خبر توسط هوش مصنوعی تولید شده است.",
                "reference": "عکس این خبر توسط هوش مصنوعی ویرایش شده است.",
            }.get(image_mode)
            if ai_photo_notice:
                form_modules.append(module("اعلام بسیار ریز دربارهٔ عکس", f"در نیمهٔ پایین طرح، هم‌خط با نشان منبع و در سمت مقابل آن، دقیقاً این عبارت را بنویس: «{ai_photo_notice}» این نوشته یک اطلاع‌رسانی ثانویه است: آن را بسیار کوچک‌تر از منبع، تعامل، روتیتر و هر متن محتوایی دیگر، ظریف، کم‌رنگ اما خوانا قرار بده. هرگز آن را در باکس، کارت، نشان برجسته یا نزدیک تیتر نگذار؛ نباید با تیتر، پنل کپشن یا کارت تعامل تداخل داشته باشد."))
        if video_overlay:
            form_modules.append(module("فضای ویدیو", video_instruction))
            if image_mode == "none":
                form_modules.append(module("پس‌زمینهٔ قالب ویدیو", "هیچ عکس، صحنه یا سوژهٔ شانسی تولید نکن. پس‌زمینه را فقط با رنگ‌ها، نور، بافت و حس بصری هویت رسانه بساز؛ ناحیهٔ امن بالا را بدون نوشته یا نشان نگه دار و لوگوی تازه یا تصویر خبری فرضی نساز."))
            else:
                blur = "عکس زمینه را به‌طور محسوس اما حرفه‌ای محو کن تا ویدیو جدا بماند." if video_background_blur else "عکس زمینه را خوانا و طبیعی نگه دار."
                form_modules.append(module("پس‌زمینهٔ قالب ویدیو", f"{image_instructions[image_mode]} این تصویر فقط پس‌زمینهٔ پشت پنجرهٔ ویدیو است و نباید وارد فضای خالی ویدیو شود. {blur}"))
        if site_link_placeholder:
            form_modules.append(module("محل استیکر لینک سایت", "یک دعوت به اقدام ظریف و مجله‌ای، هماهنگ با گرید انتخاب‌شده طراحی کن. در یک ناحیهٔ خلوت و دارای تضادِ کافی ــ دور از تیتر، منبع، کارت تعامل و در صورت وجود فضای ویدیو ــ یک جای خالیِ افقی با اندازهٔ مناسب برای چسباندن دستیِ استیکر لینک اینستاگرام رزرو کن. این فضا باید در ترکیب‌بندی طبیعی به نظر برسد و متن/آیکون دیگری داخل آن قرار نگیرد. خودِ استیکر، URL، QR، دکمه یا لینک جعلی نساز. بالای آن یا در نزدیک‌ترین سمتِ مناسب، با اندازهٔ کوچک و فارسی درست، دقیقاً بنویس: «جزئیات بیشتر در سایت کلام تازه 👇». جهت اشارهٔ ایموجی باید به محل خالیِ استیکر باشد."))
    else:
        # Non-news templates still receive only the active image behaviour;
        # "none" deliberately has no reference-photo instruction.
        if template == "poster" and image_mode in {"generate", "preserve", "reference"}:
            form_modules.append(module("نحوهٔ استفاده از تصویر پوستر", {
                "generate": "یک تصویر/فضای بصریِ اصیل و کاملاً متناسب با پیام پوستر تولید کن؛ محصول، چهره، نشان یا اطلاعاتی که در فرم نیست نساز.",
                "preserve": "تصویرهای پیوست‌شده داراییِ قطعی پوستر هستند؛ سوژه و محتوای آن‌ها را دقیقاً حفظ کن و فقط نور، کیفیت، برش و ادغام حرفه‌ای مجاز است.",
                "reference": "تصویرهای پیوست‌شده داراییِ قفل‌شدهٔ پوسترند؛ داخل آن‌ها را تغییر نده و فقط در بیرون لبه‌ها برای هماهنگی با بوم گسترش طبیعی انجام بده. دارایی، لوگو یا اطلاعات فرضی اضافه نکن.",
            }[image_mode]))
        elif template == "classifieds" and image_mode in {"generate", "preserve", "reference"}:
            form_modules.append(module("تصویر زمینهٔ نیازمندی‌ها", "تصویر مرجع، در صورت وجود، فقط یک بافت یا جزئیاتِ ثانویهٔ بسیار آرام برای حاشیهٔ صفحه است. کادرهای آگهی و متن‌هایشان اولویت مطلق‌اند؛ تصویر نباید وارد کادرها شود، خوانایی را کم کند یا آگهی/نماد دیگری بسازد."))
        elif image_mode in {"generate", "preserve", "reference"}:
            form_modules.append(module("نحوهٔ استفاده از تصویر", image_instructions[image_mode]))
        elif image_mode == "none":
            form_modules.append(module("تصویر مرجع", "هیچ تصویر مرجع یا لوگوی دیگری وجود ندارد؛ طرح را فقط با عناصر متناسب با قالب کامل کن."))

    copy_modules: list[str] = []
    if is_news:
        if approved_copy.get("kicker"):
            copy_modules.append("روتیتر را کوچک، دقیق و مکمل تیتر اصلی بنویس: «%s»." % approved_copy["kicker"])
        if approved_copy.get("title"):
            copy_modules.append("متن تیتر اصلی را دقیقاً و بدون تغییر بنویس: «%s». تیتر باید بزرگ‌ترین و شاخص‌ترین متنِ بدنه باشد، با وزن و اندازهٔ کافی برای خوانایی فوری در نمای کوچک؛ آن را ریز، هم‌وزن متن‌های فرعی یا فشرده نساز." % approved_copy["title"])
        if approved_copy.get("subtitle"):
            copy_modules.append("زیرتیتر را فقط به‌صورت متن ثانویه و در صورت حفظ خوانایی بنویس: «%s»." % approved_copy["subtitle"])
        if approved_copy.get("source"):
            copy_modules.append("منبع را در یک نشان کوچک شیشه‌ای در پایینِ سمت چپ و بالای کارت تعامل بنویس، دقیقاً به این صورت: «منبع: %s». نشان منبع فقط به اندازهٔ متن خودش باشد." % approved_copy["source"])
        if approved_copy.get("interactionText"):
            copy_modules.append("متن تعامل را در کارت تعاملِ جذابِ پایین طرح، جدا از نشان منبع، دقیقاً این‌گونه بنویس: «%s»." % approved_copy["interactionText"])
    elif approved_copy and template not in {"morning_local", "morning_kalam", "market", "citizen_message", "editorial_note", "occasion_greeting", "poster", "classifieds"}:
        # Other templates have different schemas (weather, prices, prayers,
        # riddles, etc.); retain every entered value without inventing a news
        # hierarchy for them.
        copy_modules.append("داده‌های تأییدشدهٔ این قالب را دقیقاً و فقط در جای مناسب طراحی استفاده کن:\n" + json.dumps(approved_copy, ensure_ascii=False, indent=2))

    if copy_modules:
        form_modules.append(module("متن‌های تأییدشدهٔ فرم", "\n".join(f"- {item}" for item in copy_modules)))
    if is_series_slide:
        if series_blank_fields:
            field_labels = {"title": "عنوان", "subtitle": "زیرتیتر", "caption": "بدنه", "interactionText": "پاورقی/تعامل", "source": "امضا", "citizenMessageText": "متن پیام", "citizenHeadline": "عنوان", "citizenResponse": "پاسخ", "citizenInteraction": "تعامل"}
            blank_lines = "، ".join(f"{field_labels.get(key, key)} ({fa_number(length)} نویسه)" for key, length in series_blank_fields)
            form_modules.append(module("فضای خالیِ متن بلند در اسلاید", f"برای این فیلدهای بلندِ تأییدشده: {blank_lines}، فقط فضای نوشتنِ خالی، واقعی، جادار و متناسب بساز. حتی یک کلمه از متن، خلاصه، بازنویسی، متن آزمایشی، نام‌گذاریِ فیلد، توضیح تحریریه، لورم‌ایپسوم، خط نمایشی یا عبارت جایگزین ننویس. این فضا کاملاً بدون متن، عدد و آیکون بماند تا تحریریه بعداً متن را دستی اضافه کند."))
        form_modules.append(module("قرارداد قطعی متنِ اسلاید", "فقط و فقط عبارت‌هایی را که در ماژول «متن‌های تأییدشدهٔ فرم» به‌صراحت آمده‌اند، روی این اسلاید بنویس. هر فیلدی که در آن ماژول نیامده، خالی بوده یا به‌عنوان متن بلند تعیین شده است، نباید با متن حدسی، جایگزین، راهنما، نقل‌قول، توضیح، عنوان یا برچسب پُر شود. عباراتی مانند «متن کامل…»، «توسط تحریریه…»، «ادامه دارد»، «یادداشت»، «تیتر» یا هر متن نمونه مطلقاً ممنوع‌اند. اگر هیچ متن محتواییِ تأییدشده نداری، فقط هویت سربرگ، واترمارک و نشانگر شمارهٔ اسلاید را نگه دار و باقیِ بدنه را گرافیکی و بدون متن بساز."))
        if is_news:
            if slide_index == 1:
                form_modules.append(module("قرارداد کاورِ اسلاید اول", "این اسلاید فقط کاور سری است. تنها متن‌های مجاز، روتیتر، تیتر، زیرتیتر و عبارت دقیق «ورق بزنید» هستند. متن خبر، کپشن، منبع، نام نویسنده، توضیح، نقل‌قول، شماره، برچسب و هر متن دیگری مطلقاً روی این اسلاید نیاید. عبارت «ورق بزنید» کوچک و خوانا در پایین بدنه باشد و به فضای امن، واترمارک یا نشانگر صفحه وارد نشود."))
            else:
                form_modules.append(module("قرارداد اسلایدهای ادامه", "این اسلاید برای ادامهٔ روایت است. اگر متن کپشن داده شده، موتور باید آن را فقط برای محاسبهٔ فضای خالی بخواند و هرگز آن را روی تصویر ننویسد. فضای متنِ رزروشده باید در ترکیب‌بندی واقعی دیده شود، اما خودش هیچ متن، خط، کادر، رنگ جدا یا نشانهٔ اندازه‌گیری نداشته باشد."))
    elif series_blank_fields:
        field_labels = {"title": "عنوان", "subtitle": "زیرتیتر", "caption": "متن", "interactionText": "تعامل", "citizenMessageText": "متن پیام", "citizenHeadline": "عنوان", "citizenResponse": "پاسخ", "citizenInteraction": "تعامل", "occasionHeadline": "عنوان", "occasionMessage": "پیام"}
        blank_lines = "، ".join(f"{field_labels.get(key, key)} ({fa_number(length)} نویسه)" for key, length in series_blank_fields)
        form_modules.append(module("فضای خالیِ متن بلند", f"برای {blank_lines} فقط فضای نوشتنِ خالی، تمیز و متناسب بساز. متن واقعی، خلاصه، متن آزمایشی، لورم‌ایپسوم، خط نمایشی، برچسب یا عبارت جایگزین ننویس؛ تحریریه متن را بعداً دستی وارد می‌کند."))
    if additional_instructions:
        form_modules.append(module("توضیحات تکمیلی کاربر", additional_instructions))
    if continuity_count or has_user_reference or is_studio_image or design_presenter_ids or record.get("operation") == "visual_edit":
        continuity_rules = [
            "CURRENT-SLIDE USER REFERENCES are authoritative for this slide. Use the attached user image exactly when the brief asks for it; do not replace it with a generated look-alike, redraw its map or screenshot, or invent a substitute.",
            "SERIES CONTINUITY references are previous-slide outputs. They are STYLE/IDENTITY/GRID references only: copy the visual family, camera language, typography rhythm and page-marker geometry, but NEVER copy their text, map, subject, objects, captions or story content into this slide.",
        ]
        if is_studio_image:
            continuity_rules.extend([
                "When presenters are explicitly selected, STUDIO PRESENTER IDENTITY references are locked identity evidence. Preserve each selected person's face, facial geometry, eyes, nose, mouth, skin texture, hairline and recognizable identity exactly; do not blend identities with the previous slide or regenerate a different person. Pose, expression, clothing and camera angle may change only when requested. With no selected presenters, do not invent a person.",
                "Only MONITOR CONTENT references belong inside a monitor. USER REFERENCE files are separate general assets, never implicitly monitor content. Honor the explicit monitor mode: blank means blank, disabled means no monitor, images uses only the dedicated monitor attachments. Never use the previous slide as monitor content.",
            ])
        elif design_presenter_ids:
            continuity_rules.append(
                "PRESENTER IDENTITY references are locked. Each selected presenter must remain the same person: preserve facial geometry, eyes, nose, mouth, jawline, skin texture, hairline, body proportions and recognizable identity exactly. Do not create a generic person, composite two identities, or replace a presenter with a look-alike. Change only the requested pose/action and keep identity fixed."
            )
        if not design_presenter_ids and not (studio.get("presenterIds") if is_studio_image else []):
            continuity_rules.append("No presenter is selected for this slide. Do not import any presenter, face, body, Studio location or monitor from SERIES CONTINUITY. Previous slides supply graphic style only; the subject and scene must come exclusively from this slide's brief and user attachments.")
        if record.get("operation") == "visual_edit":
            continuity_rules.append(
                "FORM EDIT LOCK: the existing parent image is the source of truth. Preserve the presenter's face, body, clothing, hair, proportions, studio and all existing visual identity exactly; edit only the specific fields requested in this form. Do not regenerate the person or reinterpret the scene as a new generic composition."
            )
        if resolved_logo_behavior(record) == "floating_profile":
            continuity_rules.append(
                "FLOATING PROFILE must be art-directed into the composition, not pasted like a sticker: use a deliberate circular crop with clean edge treatment, subtle scene-matched light/shadow or depth, and a placement that participates in the grid without covering the headline, presenter face or monitor. Keep the profile image's internal text and pixels unchanged; never recolor it yellow or redraw it."
            )
        form_modules.append(module("REFERENCE PRIORITY AND SERIES ISOLATION", "\n".join(continuity_rules)))
    if slide_mode in {"multi_story", "carousel"} and slide_count > 1:
        sequence_kind = "استوری چنداسلایدی" if slide_mode == "multi_story" else "کاروسل چنداسلایدی"
        form_modules.append(module("قواعد سریِ یکپارچه", f"این طرح، اسلاید {slide_index} از یک {sequence_kind} با مجموع {slide_count} اسلاید است. همهٔ اسلایدها باید یک سیستم طراحی مشترک داشته باشند: همان ناحیهٔ امن هویت، رنگ‌های اصلی، جنس نور، خانوادهٔ تایپوگرافی، گرید، میزان کارت‌های شیشه‌ای و حس تصویری. قرارداد هر اسلاید این سری نیز دقیقاً این است: {provider_text_start} ترکیب‌بندی هر اسلاید را متناسب با محتوای خودش متفاوت و زنده نگه دار. در پایین طرح، یک نشانگر صفحهٔ مینیمال و حرفه‌ایِ صرفاً گرافیکی بگذار: دقیقاً {slide_count} نقطه/بخش کوچک هم‌ردیف که فقط نقطهٔ شمارهٔ {slide_index} برجسته باشد. هیچ عدد، کلمه، عبارت «صفحه»، «از»، «اسلاید»، یا متن دیگری برای نشانگر ننویس. نشانگر نباید با واترمارک، منبع یا تعامل تداخل داشته باشد."))

    form_edit_changes = record.get("formEditChanges")
    if record.get("operation") == "visual_edit" and isinstance(form_edit_changes, dict):
        form_modules.append(module("ویرایش هوشمندِ کنترل‌شده روی تصویر ورودی", "این تصویر، نسخهٔ آمادهٔ قبلی است و باید پایهٔ ویرایش بماند. فقط تغییرات زیر را اعمال کن؛ هر جزء دیگری ــ از جمله عکس، چهره‌ها، سربرگ، واترمارک، رنگ، گرید، متن‌های بدون تغییر و نسبت تصویر ــ را دقیقاً حفظ کن. طرح را از نو بازطراحی نکن، متنِ تغییرداده‌نشده را بازنویسی نکن و عنصر تازه‌ای اضافه نکن.\nتغییرات واقعی فرم:\n" + json.dumps(form_edit_changes, ensure_ascii=False, indent=2)))

    active_modules = "\n\n".join(item for item in form_modules if item)
    news_render = is_news and template != "sticker"
    art_direction = news_art_direction() if news_render else ""
    watermark_protocol = news_watermark_contract(brand_watermark, has_news_photo) if news_render else ""
    if uses_editorial_header(record):
        identity_protocol = f"""پروتکل ناحیهٔ امن هویت رسانه:
{readable_text_geometry}
در همین مستطیل بالایی، همان عکس، نور، دیوار، آسمان یا پس‌زمینهٔ طبیعی صحنه را بدون بریدگی تا لبهٔ بوم ادامه بده؛ این ناحیه نباید سفید، تخت، یک‌دست، نواری، کارتی یا جدا از بدنه شود. آن را از چهره، سوژهٔ اصلی، متن، نشان و جزئیات مهم خالی نگه دار. در این ناحیه هیچ نوشته، حروف، لوگو، خط، دایره، سربرگ یا عنصر گرافیکی تولید نکن؛ هویت رسمی بعد از تولید، دقیق و فقط یک‌بار اضافه می‌شود.
{'' if news_render else f'سه واترمارک پراکنده، ظریف و کم‌رنگ را دقیقاً با متن لاتین «{brand_watermark}» روی تصویر بگذار.'}"""
        header_integrity_rule = "۴) عکس، تایپوگرافی و عناصر گرافیکی باید یک طرح یکپارچه باشند و ناحیهٔ امن بالای کادر باید امتداد طبیعی همان صحنه بماند؛ هیچ فضای سفید یا تزئین تصادفی نساز."
        header_leak_rule = "۳) ناحیهٔ امن بالای کادر برای مرحلهٔ نهایی رزرو شده است؛ در آن هیچ لوگو، سربرگ، خط، دایره یا متن نساز و پس‌زمینهٔ طبیعی صحنه را قطع نکن."
    elif resolved_logo_behavior(record) == "floating_profile":
        identity_protocol = floating_profile_prompt() + ("" if news_render else f"\nواترمارک ظریف رسانه: {brand_watermark}.")
        header_integrity_rule = "پروفایل دایره‌ای باید با حاشیهٔ تمیز، اندازهٔ خوانا و بدون پوشاندن سوژه یا متن اصلی در خود تصویر قرار بگیرد."
        header_leak_rule = "هیچ سربرگ سیستمی، نوار بالایی، لوگوی تکراری یا تیتر زرد اجباری تولید نکن."
    elif resolved_logo_behavior(record) == "none":
        identity_protocol = "پروتکل بدون پروفایل: هیچ سربرگ، لوگو، پروفایل شناور یا نوار هویتی اضافه نکن." + (" واترمارک خبری فقط مطابق ماژول مستقل خودش اجرا شود." if news_render else " واترمارک رسانه‌ای هم نساز.")
        header_integrity_rule = "هیچ سربرگ یا پروفایل رسانه‌ای تولید نشود."
        header_leak_rule = "لوگو، سربرگ، پروفایل، نوار بالایی و تیتر زرد ساختگی ممنوع است."
    elif template == "sticker":
        identity_protocol = """پروتکل استیکر:
این خروجی PNG شفاف و مستقل است. سربرگ اجتماعی، نوار بالایی، واترمارک خبری، نام رسانه یا صحنهٔ پس‌زمینه نساز؛ فقط خودِ استیکر و عناصر چسبیده به آن مجازند."""
        header_integrity_rule = "۴) فقط سیلوئت استیکر و عناصر وابسته به آن دیده شوند؛ همهٔ پیکسل‌های بیرونی واقعاً شفاف بمانند."
        header_leak_rule = "۳) سربرگ، لوگوی رسانه، واترمارک و پس‌زمینهٔ کامل ممنوع است."
    else:
        identity_protocol = """پروتکل هویت صحنهٔ استودیو:
این خروجی هیچ سربرگ اجتماعی، نوار بالایی، لوگوی شناور، واترمارک خبری یا عنوان رسانه‌ای روی لبهٔ تصویر ندارد. هویت «کلام تازه» فقط باید از لوگوها و عناصر فیزیکیِ موجود در تصاویر مرجع خودِ لوکیشن برداشت شود؛ آن‌ها را تکثیر نکن و سربرگ جداگانه نساز."""
        header_integrity_rule = "۴) صحنه، شخصیت‌ها، تایپوگرافیِ درخواستی و عناصر فیزیکی استودیو باید یکپارچه باشند؛ هیچ سربرگ اجتماعی یا نوار بالایی نساز."
        header_leak_rule = "۳) هیچ سربرگ اجتماعی، لوگوی شناور، خط هدر، دایرهٔ هدر یا واترمارک خبری روی تصویر استودیویی نساز."
    return f"""یک طرح نهایی کامل برای انتشار در رسانهٔ فارسی‌زبان طراحی کن؛ نه فقط پس‌زمینه و نه ماکاپ.

{brief}

خروجی: یک طرح کامل {"استیکر مربع PNG با زمینهٔ شفاف" if template == "sticker" else "پست عمودی ۴:۵" if format_.get("canvas") == "post_1080x1350" else "استوری عمودی ۹:۱۶"}، مدرن، مجله‌ای، حرفه‌ای و در سطح ارسال به جشنوارهٔ طراحی.
{art_direction}
{foundation}
{app.image_style_prompt()}
{news_palette_contract() if news_render else ''}

{identity_protocol}
{watermark_protocol}

قواعد قطعی متن:
۱) متن‌های تأییدشده، به‌ویژه روتیتر، تیتر و زیرتیتر، «دادهٔ قفل‌شده» هستند: پیش از نوشتن، آن‌ها را کاراکتر‌به‌کاراکتر از دادهٔ فرم بخوان و در طرح دقیقاً همان رشته را بنویس. حتی یک حرف، نیم‌فاصله، فاصله، نشانه، عدد یا واژه را اصلاح، جابه‌جا، کوتاه، بلند، بازنویسی یا حدس نزن.
۲) برای تیتر/روتیتر/زیرتیتر، فقط خودِ متن واقعیِ واردشده را نمایش بده؛ هیچ پیشوند یا برچسبی مانند «تیتر:»، «روتیتر:»، «زیرتیتر:»، «خبر:» یا توضیحی به آن اضافه نکن و هیچ بخش آن را حذف نکن. شکست سطرِ گرافیکی مجاز است، اما ترتیب واژه‌ها و املای متن باید کاملاً ثابت بماند.
۳) هر عبارت، عدد، ساعت، تاریخ، واحد و آیدی موجود در دادهٔ تأییدشده را دقیقاً همان‌طور که نوشته شده، با فارسی درست بنویس؛ هیچ‌چیز را ترجمه، خلاصه، بازنویسی، حذف یا اضافه نکن.
۴) خودِ کلمات «تیتر»، «روتیتر»، «زیرتیتر»، «کپشن» یا «کارت» را هرگز در خود طرح ننویس، مگر آن‌که عیناً بخشی از دادهٔ تأییدشدهٔ کاربر باشند.
۵) هیچ متن آزمایشی، لورم‌ایپسوم، غلط املایی، متن انگلیسی ناخواسته، لوگوی ساختگی یا عددِ حدسی تولید نکن.
{header_integrity_rule}
۵) عددهای محتوای فارسی با رقم فارسی «۰۱۲۳۴۵۶۷۸۹» باشند؛ رشته‌های لاتینِ قفل‌شده، آیدی رسانه، کدها و تاریخ میلادی دقیقاً همان دادهٔ تأییدشده باقی بمانند.
۶) در هر قالبی که عنوان/تیتر اصلی دارد، عنوان باید از همهٔ متن‌های محتوایی بزرگ‌تر، پررنگ‌تر و نخستین نقطهٔ خوانش باشد؛ برای خوانایی در نمایش کوچک موبایل فضای کافی به آن بده و آن را فشرده یا هم‌اندازهٔ متن فرعی نساز.
۷) تیتر/عنوان اصلی حداکثر از دو رنگ استفاده کند: یک رنگ پایهٔ خوانا و در صورت نیاز فقط یک رنگ تأکیدی برای یک واژه یا بخش محدود. گرادیان متن، رنگین‌کمانی‌کردن، چندرنگ‌کردن واژه‌ها یا استفاده از بیش از دو رنگ در تیتر ممنوع است.
{persian_glyph_contract()}

قرارداد منع اختراع و نشت ماژول:
۱) فیلد خالی یعنی «نبودن کامل آن عنصر». برای فیلد خالی هیچ جایگزین، placeholder، خط نمایشی، شمارهٔ نمونه، رشتهٔ «۱۲۳۴۵۶۷۸۹»، تاریخ، ساعت، قیمت، نشانی، آیدی، QR، آیکون یا کارت نساز.
۲) فقط ماژول‌هایی مجازند که زیر عنوان «ماژول‌های فعالِ همین درخواست» آمده‌اند. طلا، ارز، سکه، بازار، آب‌وهوا، اوقات شرعی، تقویم و هر ویجت یا موضوع دیگری، مگر آن‌که ماژول فعالِ همین درخواست با دادهٔ غیرخالی باشد، مطلقاً ممنوع است.
{header_leak_rule}
۴) در حالت حفظ/مرجع، بخش پایین شیت ورودی عکس واقعی کاربر است. این عکس مادهٔ تولید عکس مشابه نیست؛ محتوای اصلی آن باید عیناً بماند و تنها بیرون لبه‌هایش می‌تواند برای تکمیل بوم گسترش یابد.
۵) قبل از تحویل، تمام نوشته‌های خروجی را با «متن‌های تأییدشدهٔ فرم» تطبیق بده. هر نوشته‌ای که منبع دقیق در داده‌های فعال ندارد حذف کن؛ هیچ حرف، کلمه یا عددی را کم یا زیاد نکن.

قالب انتخاب‌شده: {template}

ماژول‌های فعالِ همین درخواست:
{active_modules or 'هیچ ماژول محتوایی اضافه‌ای انتخاب نشده است.'}

کنترل نهاییِ اجباری پیش از رندر — این بند بر هر صفحه‌بندی و ماژول دیگری اولویت دارد:
{provider_text_start}
{'تمام نوشته‌ها و واترمارک‌ها باید زیر مرز امن باشند؛ بالای آن فقط ادامهٔ طبیعی صحنه، بدون متن یا سربرگ ساختگی.' if uses_editorial_header(record) else 'از کل بوم با حاشیهٔ تنفس معمول استفاده کن؛ فضای خالیِ اجباری برای سربرگ نساز.'}
"""

def render_size(record: dict) -> str:
    # The AI is now the final renderer, so the provider aspect ratio must
    # match the editor's canvas instead of relying on a later crop.
    canvas = record.get("request", {}).get("format", {}).get("canvas")
    # GPT Image 2.5 accepts arbitrary dimensions when both edges are divisible
    # by 16. 1152×2048 is exact 9:16 and 1280×1600 is exact 4:5.
    # Gemini receives the same intent through gemini_aspect_ratio() below.
    return "1024x1024" if canvas == "sticker_1024x1024" else "1280x1600" if canvas == "post_1080x1350" else "1152x2048"

def canvas_size(record: dict) -> tuple[int, int]:
    canvas = record.get("request", {}).get("format", {}).get("canvas")
    return (1024, 1024) if canvas == "sticker_1024x1024" else (1080, 1350) if canvas == "post_1080x1350" else (1080, 1920)

def selected_image_model(record: dict) -> str:
    """Use the single image-engine choice saved in the request by Gateway.

    Queued work stays reproducible: changing Settings later cannot silently
    change the model of a request that has already been accepted.
    """
    request = record.get("request", {})
    image = request.get("image", {}) if isinstance(request, dict) else {}
    selected = str(image.get("engine", "")) if isinstance(image, dict) else ""
    if selected in {"gemini-3.1-flash-image", "gemini-3.1-flash-lite-image", "gpt-image-2", "gpt-image-2.5-flare", "gpt-image-2.5-sunburst"}:
        return selected
    return AVALAI_IMAGE_FULL_MODEL
