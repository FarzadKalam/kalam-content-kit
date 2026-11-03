"""Generated offline Studio rules. See sources.json. No service imports."""
from __future__ import annotations
import re, json, hashlib, copy
from http import HTTPStatus
from pathlib import Path
import html
from html.parser import HTMLParser

MORNING_CITIES = {
    "golbahar": {"label": "گلبهار", "latitude": 36.56976, "longitude": 59.19040},
    "chenaran": {"label": "چناران", "latitude": 36.64546, "longitude": 59.12123},
}

PERSIAN_MONTHS = ("فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند")

PERSIAN_WEEKDAYS = ("دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یکشنبه")

PERSIAN_CALENDAR_WEEKDAYS = ("شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه")

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    """Exact arithmetic conversion used for the Iranian civil calendar."""
    month_days = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
    gy2 = gy + 1 if gm > 2 else gy
    days = 355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) + gd + month_days[gm - 1]
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm, jd = 1 + (days // 31), 1 + (days % 31)
    else:
        jm, jd = 7 + ((days - 186) // 30), 1 + ((days - 186) % 30)
    return jy, jm, jd

def weather_label(code: int | None) -> str:
    labels = {0: "صاف", 1: "عمدتاً صاف", 2: "نیمه‌ابری", 3: "ابری", 45: "مه‌آلود", 48: "مه یخ‌زن", 51: "نم‌نم باران", 53: "نم‌نم باران", 55: "نم‌نم باران", 61: "بارانی", 63: "بارانی", 65: "باران شدید", 71: "برفی", 73: "برفی", 75: "برف شدید", 80: "رگبار", 81: "رگبار", 82: "رگبار شدید", 95: "رعدوبرق"}
    return labels.get(code, "متغیر")

def compact_number(value: object) -> str:
    number = float(value)
    return str(int(number)) if number.is_integer() else f"{number:.1f}".rstrip("0").rstrip(".")

def attire_for_temperature(value: object) -> str:
    temperature = float(value)
    if temperature < 10:
        return "کاپشن"
    if temperature < 18:
        return "ژاکت سبک"
    if temperature < 26:
        return "پیراهن آستین‌بلند"
    return "تی‌شرت"

SPORT_COMPETITIONS = {
    "iran_pro": {"leagueId": "4742", "label": "لیگ برتر ایران", "sport": "فوتبال", "provider": "TheSportsDB"},
    "afc_champions": {"leagueId": "4719", "label": "لیگ نخبگان آسیا", "sport": "فوتبال", "provider": "TheSportsDB"},
    "premier_league": {"leagueId": "4328", "label": "لیگ برتر انگلیس", "sport": "فوتبال", "provider": "TheSportsDB"},
    "la_liga": {"leagueId": "4335", "label": "لالیگا", "sport": "فوتبال", "provider": "TheSportsDB"},
    "serie_a": {"leagueId": "4332", "label": "سری آ", "sport": "فوتبال", "provider": "TheSportsDB"},
    "bundesliga": {"leagueId": "4331", "label": "بوندس‌لیگا", "sport": "فوتبال", "provider": "TheSportsDB"},
    "champions_league": {"leagueId": "4480", "label": "لیگ قهرمانان اروپا", "sport": "فوتبال", "provider": "TheSportsDB"},
    # The following editorial selections stay visible now.  They are enabled
    # automatically when the upstream has a current season; no unrelated
    # competitions are fetched in their place.
    "club_world_cup": {"leagueId": "", "label": "جام باشگاه‌های جهان", "sport": "فوتبال", "provider": "TheSportsDB"},
    "world_cup": {"leagueId": "", "label": "جام جهانی", "sport": "فوتبال", "provider": "TheSportsDB"},
    "euro": {"leagueId": "", "label": "یورو", "sport": "فوتبال", "provider": "TheSportsDB"},
    "asian_cup": {"leagueId": "", "label": "جام ملت‌های آسیا", "sport": "فوتبال", "provider": "TheSportsDB"},
    "iran_national": {"leagueId": "", "label": "تیم‌های ملی ایران و رقابت‌های مهم", "sport": "چندرشته‌ای", "provider": "منبع رسمی در حال اتصال"},
    "olympics": {"leagueId": "", "label": "المپیک", "sport": "چندرشته‌ای", "provider": "منبع رسمی در حال اتصال"},
}

SPORT_FA_NAMES = {
    "Esteghlal": "استقلال", "Esteghlal Khuzestan": "استقلال خوزستان", "Persepolis": "پرسپولیس", "Sepahan": "سپاهان", "Tractor": "تراکتور", "Foolad Khuzestan": "فولاد خوزستان", "Zob Ahan": "ذوب‌آهن", "Malavan": "ملوان", "Gol Gohar Sirjan": "گل‌گهر سیرجان", "Aluminium Arak": "آلومینیوم اراک", "Kheybar Khorramabad": "خیبر خرم‌آباد", "Shams Azar Qazvin": "شمس‌آذر قزوین", "Nassaji Mazandaran": "نساجی مازندران", "Paykan": "پیکان", "Fajr Sepasi Shiraz": "فجر سپاسی شیراز", "Sanat Naft": "صنعت نفت", "Mes Shahr-e Babak": "مس شهر بابک", "Chadormalou Ardakan": "چادرملو اردکان",
    "Arsenal": "آرسنال", "Chelsea": "چلسی", "Liverpool": "لیورپول", "Manchester City": "منچسترسیتی", "Manchester United": "منچستریونایتد", "Tottenham": "تاتنهام", "Newcastle": "نیوکاسل", "Aston Villa": "استون ویلا", "Real Madrid": "رئال مادرید", "Barcelona": "بارسلونا", "Atletico Madrid": "اتلتیکو مادرید", "Juventus": "یوونتوس", "Inter": "اینتر", "AC Milan": "آث میلان", "Bayern Munich": "بایرن مونیخ", "Borussia Dortmund": "بوروسیا دورتموند", "Paris Saint-Germain": "پاری‌سن‌ژرمن", "Iran": "ایران",
}

def sport_fa_name(value: object) -> str:
    name = str(value or "").strip()
    return SPORT_FA_NAMES.get(name, name)

PERSIAN_DIGITS_TO_ASCII = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

def normalise_calendar_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip(" -–—\u200c")

class MonthlyCalendarRowParser(HTMLParser):
    """Extract event spans without being confused by nested religious spans."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.events: list[str] = []
        self._event_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._event_depth:
            self._event_depth += 1
            return
        if tag == "span" and dict(attrs).get("class") == "M6":
            self._event_depth = 1
            self._parts = []

    def handle_endtag(self, tag: str) -> None:
        if not self._event_depth:
            return
        self._event_depth -= 1
        if self._event_depth == 0:
            event = re.sub(r"\s+", " ", "".join(self._parts)).strip()
            if event:
                self.events.append(event)

    def handle_data(self, data: str) -> None:
        if self._event_depth:
            self._parts.append(data)
