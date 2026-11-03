"""Public editorial data, without model APIs, accounts or news discovery."""
from __future__ import annotations
import argparse
import concurrent.futures
import datetime as dt
from decimal import Decimal, InvalidOperation
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import tempfile
from html.parser import HTMLParser
import urllib.error
import urllib.parse
import urllib.request
try:
    from zoneinfo import ZoneInfo
    TEHRAN=ZoneInfo('Asia/Tehran')
except (ImportError,KeyError):
    TEHRAN=dt.timezone(dt.timedelta(hours=3,minutes=30))  # Iran has no DST since 2023.

ROOT=Path(__file__).resolve().parents[1]
rule_spec=importlib.util.spec_from_file_location('data_rules',ROOT/'vendor/studio/data_rules.py')
rules=importlib.util.module_from_spec(rule_spec);rule_spec.loader.exec_module(rules)
UTC=dt.timezone.utc
HOSTS={'api.open-meteo.com','api.aladhan.com','www.thesportsdb.com','www.bahesab.ir',
       'raw.githubusercontent.com','pnldev.com','baha24.com','www.tgju.org','tgju.org'}
TASKS={'date','market-date','weather','prayer','kalam-calendar','occasions','kalam-occasions','sports','rates'}
HIJRI_MONTHS=('محرم','صفر','ربیع‌الاول','ربیع‌الثانی','جمادی‌الاول','جمادی‌الثانی','رجب','شعبان','رمضان','شوال','ذی‌القعده','ذی‌الحجه')
RATE_FIELDS={'marketUsdPrice':'USD','marketEurPrice':'EUR','marketCoinPrice':'AZADI1','marketGold18Price':'GOL18','marketBitcoinPrice':'BITCOIN'}
TGJU_ROWS={'price_dollar_rl':'marketUsdPrice','price_eur':'marketEurPrice','sekee':'marketCoinPrice','geram18':'marketGold18Price','crypto-bitcoin':'marketBitcoinPrice'}
PREFIXES={'date':('morningWeekday','morningPersianDate','morningGregorianDate','morningHijriDate'),
 'market-date':('marketWeekday','marketPersianDate','marketGregorianDate','marketHijriDate','marketTime'),
 'weather':('morningWeatherCondition','morningMinTemperature','morningMaxTemperature','morningWindSpeed','morningHumidity','morningAttire'),
 'prayer':('morningFajr','morningSunrise','morningNoon','morningSunset','morningMaghrib','morningMidnight'),
 'kalam-calendar':('morningKalamWeekLabel','morningKalamTodayIndex',*[f'morningKalamDay{i}' for i in range(1,8)]),
 'occasions':('morningLocalOccasion',),'kalam-occasions':('morningKalamOccasion',),
 'sports':('sportCompetition','sportResults','sportSource','sportEventIds','sportVisualAssets'),
 'rates':(*RATE_FIELDS,*[k.replace('Price','Change') for k in RATE_FIELDS],'marketSource','marketTime')}

class DataError(ValueError):pass
def now_utc():return dt.datetime.now(UTC)
def iso(value):return value.astimezone(UTC).isoformat()
def parse_time(value):
    stamp=dt.datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if stamp.tzinfo is None:raise DataError('زمان داده باید منطقهٔ زمانی داشته باشد.')
    return stamp
def target_date(value,now):
    return now.astimezone(TEHRAN).date() if value in (None,'','today') else dt.date.fromisoformat(value)
def fa(value):return str(value).translate(rules.FA_DIGITS)
def numeric(value):
    try:number=Decimal(str(value).translate(rules.PERSIAN_DIGITS_TO_ASCII).replace(',','').replace('٬',''))
    except InvalidOperation as exc:raise DataError('مقدار عددی منبع معتبر نیست.') from exc
    if not number.is_finite():raise DataError('مقدار عددی منبع معتبر نیست.')
    return number
def write_json(file,value):
    file.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=file.parent,delete=False) as tmp:
        json.dump(value,tmp,ensure_ascii=False,indent=2);tmp.write('\n');name=tmp.name
    Path(name).replace(file)
def allowed_url(url):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or parsed.hostname not in HOSTS or parsed.username or parsed.password or parsed.port not in (None,443):
        raise DataError('نشانی دریافت داده خارج از منابع عمومی تعریف‌شده است.')
    return url
class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return super().redirect_request(req,fp,code,msg,headers,allowed_url(newurl))

class Client:
    def __init__(self,cache=None,now=None,force=False):
        self.now=now or now_utc();self.cache=Path(cache) if cache else ROOT/'.cache/public-data';self.force=force;self.sources=[]
    def get(self,url,ttl=900,json_data=True):
        allowed_url(url)
        key=hashlib.sha256(url.encode()).hexdigest();file=self.cache/f'{key}.json';cached=None
        for ancestor in [file.parent,*file.parent.parents]:
            if ancestor.is_symlink():raise DataError('کش داده نباید symlink باشد.')
        if file.is_file():
            try:cached=json.loads(file.read_text(encoding='utf-8'))
            except (OSError,ValueError):pass
        age=(self.now-parse_time(cached['retrievedAt'])).total_seconds() if isinstance(cached,dict) and 'retrievedAt' in cached else float('inf')
        if not self.force and 0<=age<ttl:
            body=cached['body'];retrieved=cached['retrievedAt'];hit=True
        else:
            try:
                request=urllib.request.Request(url,headers={'User-Agent':'KalamContentKit/0.2 (public editorial data)','Accept':'application/json,text/html'})
                with urllib.request.build_opener(SafeRedirect()).open(request,timeout=12) as response:
                    body=response.read(8*1024*1024+1)
                if len(body)>8*1024*1024:raise DataError('پاسخ منبع بیش از حد بزرگ است.')
                body=body.decode('utf-8');retrieved=iso(self.now);hit=False
                if json_data:json.loads(body)
                write_json(file,{'url':url,'retrievedAt':retrieved,'body':body})
            except (urllib.error.URLError,TimeoutError,OSError,ValueError) as exc:
                self.sources.append({'url':url,'attemptedAt':iso(self.now),'status':'failed','error':str(exc)})
                raise DataError(f'دریافت {urllib.parse.urlsplit(url).hostname} ناموفق بود: {exc}') from exc
        self.sources.append({'url':url,'retrievedAt':retrieved,'sha256':hashlib.sha256(body.encode()).hexdigest(),'cached':hit})
        try:return json.loads(body) if json_data else body
        except ValueError as exc:raise DataError('ساختار پاسخ منبع معتبر نیست.') from exc

def city_info(city):
    if city not in rules.MORNING_CITIES:raise DataError('شهر را از گلبهار یا چناران انتخاب کنید.')
    return rules.MORNING_CITIES[city]
def base_dates(day):
    y,m,d=rules.gregorian_to_jalali(day.year,day.month,day.day)
    return {'morningWeekday':rules.PERSIAN_WEEKDAYS[day.weekday()],
      'morningPersianDate':fa(f'{d} {rules.PERSIAN_MONTHS[m-1]} {y}'),
      'morningGregorianDate':f'{day.day} {day.strftime("%B")} {day.year}'}
def aladhan(client,city,day):
    info=city_info(city);query=urllib.parse.urlencode({**{k:info[k] for k in ['latitude','longitude']},'method':0,'timezonestring':'Asia/Tehran'})
    payload=client.get(f'https://api.aladhan.com/v1/timings/{day:%d-%m-%Y}?{query}',ttl=12*3600)
    data=payload.get('data') if isinstance(payload,dict) else None
    if payload.get('code')!=200 or not isinstance(data,dict) or data.get('date',{}).get('gregorian',{}).get('date')!=day.strftime('%d-%m-%Y'):
        raise DataError('تاریخ پاسخ اوقات شرعی با روز درخواستی یکسان نیست.')
    meta=data.get('meta',{})
    if meta.get('timezone')!='Asia/Tehran' or meta.get('method',{}).get('id')!=0:raise DataError('روش یا منطقهٔ زمانی اوقات شرعی نادرست است.')
    for key in ['latitude','longitude']:
        if abs(float(meta.get(key,999))-info[key])>0.1:raise DataError('مختصات پاسخ اوقات شرعی نادرست است.')
    return data
def dates(client,city,day,market=False):
    values=base_dates(day);data=aladhan(client,city,day);h=data['date']['hijri'];month=int(h['month']['number'])
    if not 1<=month<=12:raise DataError('ماه قمری معتبر نیست.')
    values['morningHijriDate']=fa(f"{h['day']} {HIJRI_MONTHS[month-1]} {h['year']}")
    if market:
        values={k.replace('morning','market',1):v for k,v in values.items()};values['marketTime']=fa(client.now.astimezone(TEHRAN).strftime('%H:%M'))
    return values,{},['تاریخ قمری از AlAdhan است؛ تطبیق مناسبت مذهبی با تقویم رسمی ایران جدا انجام می‌شود.']
def prayers(client,city,day):
    data=aladhan(client,city,day);keys=['Fajr','Sunrise','Dhuhr','Sunset','Maghrib','Midnight'];values={}
    for field,key in zip(PREFIXES['prayer'],keys):
        value=str(data.get('timings',{}).get(key,'')).split(' ')[0]
        if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',value):raise DataError('شش زمان اوقات شرعی به‌طور کامل دریافت نشد.')
        values[field]=fa(value)
    return values,{'method':'Shia Ithna-Ashari (AlAdhan 0)'},[]
def weather(client,city,day):
    distance=(day-client.now.astimezone(TEHRAN).date()).days
    if not 0<=distance<=15:raise DataError('پیش‌بینی هوا فقط برای امروز تا پانزده روز آینده است.')
    info=city_info(city);query={k:info[k] for k in ['latitude','longitude']}
    query.update({'timezone':'Asia/Tehran','start_date':str(day),'end_date':str(day),
      'daily':'weather_code,temperature_2m_max,temperature_2m_min,apparent_temperature_max,wind_speed_10m_max,relative_humidity_2m_max'})
    if distance==0:query['current']='temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m'
    payload=client.get('https://api.open-meteo.com/v1/forecast?'+urllib.parse.urlencode(query),ttl=900)
    if payload.get('timezone')!='Asia/Tehran':raise DataError('منطقهٔ زمانی هواشناسی نادرست است.')
    daily=payload.get('daily',{});index=daily.get('time',[]).index(str(day))
    value=lambda key:daily[key][index]
    minimum,maximum=numeric(value('temperature_2m_min')),numeric(value('temperature_2m_max'))
    if minimum>maximum or not -90<=minimum<=65 or not -90<=maximum<=65:raise DataError('مقادیر دما نامعتبرند.')
    current=payload.get('current',{}) if distance==0 else {}
    code=current.get('weather_code',value('weather_code'))
    humidity=current.get('relative_humidity_2m',value('relative_humidity_2m_max'))
    wind=current.get('wind_speed_10m',value('wind_speed_10m_max'))
    apparent=current.get('apparent_temperature',value('apparent_temperature_max'))
    if not 0<=numeric(humidity)<=100 or numeric(wind)<0:raise DataError('رطوبت یا سرعت باد نامعتبر است.')
    meta={'forecast':distance>0}
    if current:
        observed=dt.datetime.fromisoformat(current['time']).replace(tzinfo=TEHRAN)
        age=(client.now-observed).total_seconds()
        if not -900<=age<=3*3600:raise DataError('مشاهدهٔ هواشناسی قدیمی است.')
        meta['observedAt']=iso(observed)
    else:meta['observationType']='پیش‌بینی روزانه؛ باد و رطوبت بیشینه‌اند'
    values={'morningWeatherCondition':rules.weather_label(int(code)),
      'morningMinTemperature':fa(rules.compact_number(minimum)),'morningMaxTemperature':fa(rules.compact_number(maximum)),
      'morningWindSpeed':fa(rules.compact_number(wind))+' km/h','morningHumidity':fa(rules.compact_number(humidity))+'٪',
      'morningAttire':rules.attire_for_temperature(apparent)}
    return values,meta,[]

def monthly_events(page,day):
    """Read actual calendar rows. An empty event list is a valid day, not a failure."""
    for row in re.findall(r'<li\s+class="totall-m"[^>]*>(.*?)</li>',page,re.S|re.I):
        match=re.search(r'<span\s+class="M([12])[^\"]*">(.*?)</span>',row,re.S|re.I)
        if not match:continue
        digits=re.search(r'\d+',rules.normalise_calendar_text(match[2]).translate(rules.PERSIAN_DIGITS_TO_ASCII))
        if digits and int(digits[0])==day:
            parser=rules.MonthlyCalendarRowParser();parser.feed(row)
            return list(dict.fromkeys(rules.normalise_calendar_text(e).replace('«تعطیل»','').strip() for e in parser.events if rules.normalise_calendar_text(e))),match[1]=='2'
    raise DataError('روز در صفحهٔ تقویم پیدا نشد؛ ساختار منبع نیاز به بررسی دارد.')
class MonthGrid(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.inside=False;self.cell=None;self.days={};self.collect=False
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='table' and attrs.get('id')=='bahesab-time':self.inside=True
        if self.inside and tag=='td':self.cell={'text':'','holiday':'Ho' in attrs.get('class','').split()};self.collect=True
        if tag in {'br','small'}:self.collect=False
    def handle_data(self,text):
        if self.inside and self.cell is not None and self.collect:self.cell['text']+=text
    def handle_endtag(self,tag):
        if tag=='td' and self.cell is not None:
            value=self.cell['text'].strip().translate(rules.PERSIAN_DIGITS_TO_ASCII)
            if re.fullmatch(r'\d{1,2}',value) and 1<=int(value)<=31:self.days[int(value)]=self.cell['holiday']
            self.cell=None;self.collect=False
        if tag=='table':self.inside=False
def month_grid(page,year,month):
    titles=re.findall(r'<title>(.*?)</title>',page,re.S|re.I)
    title=rules.normalise_calendar_text(titles[0]).translate(rules.PERSIAN_DIGITS_TO_ASCII) if titles else ''
    if str(year) not in title or rules.PERSIAN_MONTHS[month-1] not in title:raise DataError('سال یا ماه صفحهٔ تقویم با درخواست یکسان نیست.')
    grid=MonthGrid();grid.feed(page)
    if len(grid.days)<29:raise DataError('جدول کامل روزهای ماه در منبع تقویم پیدا نشد.')
    return grid.days
def occasion_data(client,day):
    y,m,d=rules.gregorian_to_jalali(day.year,day.month,day.day);warnings=[];holiday=None
    try:
        page=client.get(f'https://www.bahesab.ir/time/{y}{m:02d}/',ttl=12*3600,json_data=False)
        grid=month_grid(page,y,m)
        if d not in grid:raise DataError('روز در تقویم ماه وجود ندارد.')
        try:events,_=monthly_events(page,d)
        except DataError:events=[]  # The complete published grid contains this day; no event is listed.
        holiday=grid[d]
    except (DataError,ValueError) as exc:
        warnings.append(str(exc))
        payload=client.get('https://pnldev.com/api/calender?'+urllib.parse.urlencode({'year':y,'month':m,'day':d,'holiday':'false'}),ttl=12*3600)
        result=payload.get('result',{})
        if not payload.get('status') or not isinstance(result.get('event'),list):raise DataError('پاسخ پشتیبان تقویم معتبر نیست.')
        events=[rules.normalise_calendar_text(str(x)) for x in result['event']];warnings.append('منبع پشتیبان PNLdev؛ تقویم رسمی مستقل تأیید نشده است.')
    try:
        payload=client.get('https://raw.githubusercontent.com/persian-calendar/events/master/events.json',ttl=12*3600)
        if not isinstance(payload.get('data'),list):raise DataError('ساختار مناسبت‌های جهانی معتبر نیست.')
        events += [e['title'] for e in payload['data'] if isinstance(e,dict) and e.get('type')=='International' and e.get('calendar')=='Gregorian' and e.get('rule')=='simple' and (e.get('month'),e.get('day'))==(day.month,day.day) and e.get('title')]
    except DataError as exc:warnings.append('مناسبت‌های جهانی کامل دریافت نشد: '+str(exc))
    return list(dict.fromkeys(events)),holiday,warnings
def calendar(client,day):
    start=day-dt.timedelta(days=(day.weekday()-5)%7);y,m,_=rules.gregorian_to_jalali(day.year,day.month,day.day)
    values={'morningKalamWeekLabel':fa(f'{rules.PERSIAN_MONTHS[m-1]} {y}'),'morningKalamTodayIndex':str((day-start).days+1)};holidays=[];warnings=[];complete=True
    pages={}
    for i in range(7):
        date=start+dt.timedelta(days=i);jy,jm,jd=rules.gregorian_to_jalali(date.year,date.month,date.day)
        values[f'morningKalamDay{i+1}']=fa(jd);values[f'morningKalamWeekday{i+1}']=rules.PERSIAN_CALENDAR_WEEKDAYS[i]
        if date.weekday()==4:holidays.append(i+1)
        try:
            if (jy,jm) not in pages:
                page=client.get(f'https://www.bahesab.ir/time/{jy}{jm:02d}/',ttl=12*3600,json_data=False)
                pages[(jy,jm)]=month_grid(page,jy,jm)
            if jd not in pages[(jy,jm)]:raise DataError('روز در جدول ماهانه پیدا نشد.')
            holiday=pages[(jy,jm)][jd]
            if holiday and i+1 not in holidays:holidays.append(i+1)
        except DataError as exc:
            complete=False
            if str(exc) not in warnings:warnings.append(str(exc))
    return values,{'todayIndex':(day-start).days+1,'holidayIndexes':sorted(holidays),'holidaysComplete':complete},warnings

def event_view(event):
    stamp=str(event.get('strTimestamp') or '').strip();date=str(event.get('dateEvent') or '');time=str(event.get('strTime') or '')
    when=None
    try:
        if stamp:when=dt.datetime.fromisoformat(stamp.replace('Z','+00:00'))
        elif date and time:when=dt.datetime.fromisoformat(date+'T'+time)
        if when and when.tzinfo is None:when=when.replace(tzinfo=UTC)  # TheSportsDB strTime/strTimestamp are UTC.
    except ValueError:when=None
    home,away=rules.sport_fa_name(event.get('strHomeTeam')),rules.sport_fa_name(event.get('strAwayTeam'))
    if not home or not away or not event.get('idEvent'):raise DataError('اطلاعات تیم یا شناسهٔ مسابقه ناقص است.')
    scores=[event.get('intHomeScore'),event.get('intAwayScore')];played=all(v is not None and str(v)!='' for v in scores)
    status=str(event.get('strStatus') or '')
    final=status.lower() in {'ft','aet','pen','match finished','finished','after pen.','after extra time'}
    if played and any(not re.fullmatch(r'\d+',str(v)) for v in scores):raise DataError('نتیجهٔ مسابقه نامعتبر است.')
    local=when.astimezone(TEHRAN) if when else None
    score=fa(f'{scores[0]} - {scores[1]}') if played else '—'
    local_date=str(local.date()) if local else date;local_time=local.strftime('%H:%M') if local else ''
    return {'eventId':str(event['idEvent']),'home':home,'away':away,'date':local_date,'time':local_time,
      'startsAt':iso(when) if when else None,'timeZone':'Asia/Tehran','timeKnown':bool(when),
      'round':str(event.get('intRound') or ''),'status':status,'played':played,'final':final,'score':score,
      'label':f'{home} {score} {away} | {local_date}'+('، '+fa(local_time)+' به وقت تهران' if local_time else '؛ ساعت تأیید نشده'),
      'homeBadge':str(event.get('strHomeTeamBadge') or ''),'awayBadge':str(event.get('strAwayTeamBadge') or '')}
def sports(client,competition,mode,day):
    item=rules.SPORT_COMPETITIONS.get(competition)
    if not item:raise DataError('رقابت را از فهرست انتخاب کنید.')
    if not item['leagueId']:raise DataError('این رقابت در Studio هم منبع زندهٔ متصل ندارد؛ از وب رسمی با ثبت مدرک وارد شود.')
    if mode not in {'result','league','upcoming'}:raise DataError('حالت ورزشی نامعتبر است.')
    root='https://www.thesportsdb.com/api/v1/json/123/'
    league=client.get(root+'lookupleague.php?id='+item['leagueId'],ttl=3600)
    rows=league.get('leagues') or []
    if not rows or str(rows[0].get('idLeague'))!=item['leagueId']:raise DataError('هویت لیگ با پاسخ منبع یکسان نیست.')
    season=str(rows[0].get('strCurrentSeason') or '')
    if not re.fullmatch(r'\d{4}(?:-\d{4})?',season):raise DataError('فصل فعلی رقابت دریافت نشد.')
    payload=client.get(root+'eventsseason.php?'+urllib.parse.urlencode({'id':item['leagueId'],'s':season}),ttl=600)
    if not isinstance(payload.get('events'),list):raise DataError('رویدادهای فصل دریافت نشد.')
    events=[]
    for event in payload['events']:
        if str(event.get('idLeague'))!=item['leagueId'] or str(event.get('strSeason'))!=season:raise DataError('رویداد نامرتبط در پاسخ منبع است.')
        value=event_view(event)
        if mode=='upcoming':
            if value['played'] or not value['timeKnown'] or value['date']!=str(day) or parse_time(value['startsAt'])<client.now:continue
            if any(s in value['status'].lower() for s in ['cancel','postpon','abandon']):continue
        elif not value['final'] or not value['played'] or not value['timeKnown'] or value['date']!=str(day) or parse_time(value['startsAt'])>client.now:continue
        events.append(value)
    events.sort(key=lambda e:e['startsAt'],reverse=mode!='upcoming')
    if mode=='league' and events:
        last=max(int(e['round'] or 0) for e in events);events=[e for e in events if int(e['round'] or 0)==last]
    events=events[:20]
    if not events:raise DataError('مسابقهٔ معتبر برای تاریخ و حالت انتخاب‌شده در منبع پیدا نشد؛ از وب رسمی بررسی شود.')
    source='TheSportsDB؛ '+season+'؛ ساعت‌ها به وقت تهران'
    return ({'sportCompetition':competition,'sportResults':'\n'.join(e['label'] for e in events),
      'sportSource':source,'sportEventIds':json.dumps([e['eventId'] for e in events]),'sportVisualAssets':'[]'},
      {'competition':item['label'],'competitionId':competition,'season':season,'events':events,'mode':mode},[])

class MarketRows(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.rows={};self.active=None;self.cell=None
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='tr':
            name=attrs.get('data-market-row');self.active={'attrs':attrs,'cells':[]} if name in TGJU_ROWS else None
            if self.active and attrs.get('data-price') and (name not in self.rows or not self.rows[name]['attrs'].get('data-price')):self.rows[name]=self.active
        if tag=='td' and self.active is not None:self.cell=[]
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag=='td' and self.cell is not None:
            self.active['cells'].append(' '.join(''.join(self.cell).split()));self.cell=None
        if tag=='tr':self.active=None;self.cell=None
def changes(rates,provider,client):
    file=client.cache/'market-history.json';history=[]
    if file.is_file():
        try:history=json.loads(file.read_text())
        except ValueError:pass
    values={};now=client.now.timestamp()
    for field,amount in rates.items():
        candidates=[x for x in history if x.get('provider')==provider and 18*3600<=now-x.get('at',now)<=30*3600 and field in x.get('rates',{})]
        change=''
        if candidates:
            previous=min(candidates,key=lambda x:abs(now-x['at']-86400));baseline=numeric(previous['rates'][field])
            if baseline>0:change=fa(f'{(amount-baseline)/baseline*100:+.2f}')
        values[field.replace('Price','Change')]=change
    history.append({'at':now,'provider':provider,'rates':{k:str(v) for k,v in rates.items()}})
    write_json(file,history[-240:]);return values
def market(client):
    warnings=[];review=False;meta={}
    try:
        payload=client.get('https://baha24.com/api/v1/price',ttl=300)
        if not isinstance(payload,list):raise DataError('ساختار نرخ بازار معتبر نیست.')
        feed={str(x.get('symbol','')).upper():x for x in payload if isinstance(x,dict)}
        rates={key:numeric(feed[symbol]['sell']) for key,symbol in RATE_FIELDS.items()}
        provider='Baha24';dates=[]
        for symbol in RATE_FIELDS.values():
            value=feed[symbol].get('last_update','')
            try:stamp=parse_time(value)
            except (ValueError,TypeError):review=True;continue
            if not -300<=(client.now-stamp).total_seconds()<=36*3600:raise DataError('نرخ بازار قدیمی است.')
            dates.append(iso(stamp))
        meta['observedAtByQuote']=dates
    except (DataError,KeyError,TypeError,ValueError) as exc:
        warnings.append(str(exc));provider='TGJU';review=True
        parser=MarketRows();parser.feed(client.get('https://www.tgju.org/',ttl=300,json_data=False));rates={};quote_times={}
        for row,key in TGJU_ROWS.items():
            data=parser.rows.get(row)
            if not data or not data['attrs'].get('data-price'):raise DataError('پنج نرخ لازم در صفحهٔ TGJU پیدا نشد.')
            # Studio's fixed render contract is toman for four Iranian quotes, USD for BTC.
            rates[key]=numeric(data['attrs']['data-price'])/(Decimal(1) if key=='marketBitcoinPrice' else Decimal(10))
            quote_times[key]=[x for x in data['cells'] if re.fullmatch(r'[۰-۹0-9]{2}:[۰-۹0-9]{2}(?::[۰-۹0-9]{2})?',x)]
        meta['quoteClockTimes']=quote_times;meta['observationTimePrecision']='time-only; quote dates require web verification'
        warnings.append('صفحهٔ TGJU نرخ دارد ولی تاریخ کامل هر نرخ مشخص نیست؛ پیش از اعمال، تاریخ و تازگی از وب بررسی شود.')
    if any(value<=0 for value in rates.values()):raise DataError('نرخ بازار باید مثبت باشد.')
    values={key:fa(f'{amount:,.0f}' if amount==amount.to_integral() else f'{amount:,.2f}') for key,amount in rates.items()}
    # Do not turn an undated quote into a verified daily baseline.
    values.update({k.replace('Price','Change'):'' for k in RATE_FIELDS} if review else changes(rates,provider,client))
    values.update({'marketTime':fa(client.now.astimezone(TEHRAN).strftime('%H:%M')),'marketSource':provider})
    meta.update({'units':{k:('USD' if k=='marketBitcoinPrice' else 'toman') for k in RATE_FIELDS},'requiresReview':review})
    return values,meta,warnings

def fetch(task,*,city='golbahar',date='today',competition='',mode='result',cache=None,now=None,force=False,client=None):
    now=now or now_utc();client=client or Client(cache,now,force);day=target_date(date,now)
    result={'schemaVersion':1,'task':task,'status':'ready','values':{},'meta':{'city':city,'date':str(day),'timeZone':'Asia/Tehran'},
      'fetchedAt':iso(now),'expiresAt':iso(min(now+dt.timedelta(seconds=600 if task in {'sports','rates'} else 1800),dt.datetime.combine(now.astimezone(TEHRAN).date()+dt.timedelta(days=1),dt.time(),TEHRAN))),
      'sources':[],'warnings':[]}
    try:
        if task in {'date','market-date'}:values,meta,warnings=dates(client,city,day,task=='market-date')
        elif task=='weather':values,meta,warnings=weather(client,city,day)
        elif task=='prayer':values,meta,warnings=prayers(client,city,day)
        elif task=='kalam-calendar':values,meta,warnings=calendar(client,day)
        elif task in {'occasions','kalam-occasions'}:
            events,holiday,warnings=occasion_data(client,day);values={PREFIXES[task][0]:'\n'.join(events)};meta={'holiday':holiday}
        elif task=='sports':values,meta,warnings=sports(client,competition,mode,day)
        elif task=='rates':values,meta,warnings=market(client)
        else:raise DataError('نوع داده شناخته‌شده نیست.')
        result['values']=values;result['meta'].update(meta);result['warnings']=warnings
        if meta.get('requiresReview') or meta.get('holidaysComplete') is False:result['status']='needs-review'
    except (DataError,KeyError,IndexError,TypeError,ValueError) as exc:
        result['status']='blocked';result['error']=str(exc);result['fallback']={'type':'host-web','task':task,
          'instruction':'از منبع عمومی معتبر برای همین روز/شهر/رقابت بررسی و با URL، زمان کامل داده و نقل مستند وارد شود؛ داده حدس زده نشود.'}
    result['sources']=client.sources
    return result

def catalog():
    return {'schemaVersion':1,'cities':rules.MORNING_CITIES,'competitions':rules.SPORT_COMPETITIONS,
      'tasks':{task:{'fields':list(fields),'requiresModelApi':False} for task,fields in PREFIXES.items()},
      'timeZone':'Asia/Tehran','newsDiscovery':False,'hosts':sorted(HOSTS)}
def effective_binding(spec,binding):
    result=dict(binding);target=binding.get('target','request');request={}
    if target=='request':request=spec.get('request',{})
    elif isinstance(target,int) and not isinstance(target,bool):
        slides=spec.get('slides',[])
        if not 0<=target<len(slides):raise DataError('شمارهٔ اسلاید داده معتبر نیست.')
        request=slides[target]
    elif target!='context':raise DataError('مقصد داده معتبر نیست.')
    content=request.get('content',{})
    result['city']=binding.get('city') or content.get('morningCity') or ('chenaran' if spec.get('brand')=='chenaran' else 'golbahar')
    result['competition']=binding.get('competition') or content.get('sportCompetition','')
    result['mode']=binding.get('mode') or content.get('sportMode','result')
    return result
def batch(spec,base=None,**kwargs):
    bindings=[x for x in spec.get('dataRequests',[]) if x.get('enabled',True)]
    if len(bindings)>40:raise DataError('تعداد درخواست داده بیش از حد مجاز است.')
    if len({b['id'] for b in bindings})!=len(bindings) or any(b['task'] not in TASKS for b in bindings):raise DataError('شناسه یا نوع درخواست داده معتبر نیست.')
    def run(binding):
        binding=effective_binding(spec,binding)
        if base and not kwargs.get('force'):
            try:
                result=read_evidence(spec,binding,base)
                validate_result(result,binding,kwargs.get('now'))
                return {'id':binding['id'],'target':binding.get('target','request'),'required':binding.get('required',True),'result':result}
            except (DataError,ValueError,KeyError,OSError):pass
        result=fetch(binding['task'],city=binding.get('city','golbahar'),date=binding.get('date','today'),
          competition=binding.get('competition',''),mode=binding.get('mode','result'),**kwargs)
        return {'id':binding['id'],'target':binding.get('target','request'),'required':binding.get('required',True),'result':result}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:return list(pool.map(run,bindings))

def validate_result(result,binding,now=None):
    now=now or now_utc()
    if result.get('task')!=binding['task'] or result.get('status')!='ready':raise DataError('دادهٔ موردنیاز آماده یا تأییدشده نیست: '+binding['task'])
    if not parse_time(result['fetchedAt'])-dt.timedelta(seconds=60)<=now<parse_time(result['expiresAt']):raise DataError('دادهٔ روز منقضی شده؛ به‌روزرسانی لازم است.')
    meta=result.get('meta',{})
    if meta.get('date')!=str(target_date(binding.get('date','today'),now)) or meta.get('timeZone')!='Asia/Tehran':raise DataError('تاریخ یا منطقهٔ زمانی مدرک با سفارش یکسان نیست.')
    if binding['task'] in {'date','market-date','prayer','weather'} and meta.get('city')!=binding.get('city','golbahar'):raise DataError('شهر مدرک با سفارش یکسان نیست.')
    if binding['task']=='sports' and (meta.get('competitionId')!=binding.get('competition') or meta.get('mode')!=binding.get('mode','result')):raise DataError('رقابت یا حالت مدرک با سفارش یکسان نیست.')
    if binding['task']=='weather' and not meta.get('forecast'):
        if not -900<=(now-parse_time(meta.get('observedAt'))).total_seconds()<=3*3600:raise DataError('زمان مشاهدهٔ هواشناسی قدیمی است.')
    if binding['task']=='rates':
        observations=meta.get('observedAtByQuote') or [meta.get('observedAt')]
        if not observations or any(not -300<=(now-parse_time(v)).total_seconds()<=36*3600 for v in observations):raise DataError('زمان مشاهدهٔ نرخ قدیمی است.')
    if not isinstance(result.get('values'),dict) or set(result['values'])-set(PREFIXES[binding['task']])-{f'morningKalamWeekday{i}' for i in range(1,8)}:raise DataError('فیلدهای داده با نوع درخواست یکسان نیست.')
    required=set(RATE_FIELDS) if binding['task']=='rates' else set(PREFIXES[binding['task']])
    if required-set(result['values']) or any(not isinstance(v,str) for v in result['values'].values()):raise DataError('فیلدهای الزامی داده کامل نیستند.')
    if binding['task'] not in {'occasions','kalam-occasions'} and any(not result['values'][field].strip() for field in required):raise DataError('فیلد الزامی داده خالی است.')
    if binding['task']=='kalam-calendar' and (meta.get('holidaysComplete') is not True or not isinstance(meta.get('todayIndex'),int) or not 1<=meta['todayIndex']<=7 or not isinstance(meta.get('holidayIndexes'),list) or any(type(i) is not int or not 1<=i<=7 for i in meta['holidayIndexes'])):raise DataError('اطلاعات تعطیلی و روز تقویم کامل نیست.')

def read_evidence(spec,binding,base):
    evidence=spec.get('dataEvidence',{}).get(binding['id'])
    if not evidence:raise DataError('دادهٔ روز دریافت نشده است: '+binding['id'])
    relative=Path(evidence.get('path',''));path=(base/relative).resolve()
    if relative.is_absolute() or '..' in relative.parts or not path.is_relative_to(base.resolve()) or not path.is_file():raise DataError('مسیر مدرک داده معتبر نیست.')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=evidence.get('sha256'):raise DataError('مدرک داده تغییر کرده است.')
    return json.loads(raw)

def validate_evidence(spec,base,now=None):
    for binding in spec.get('dataRequests',[]):
        if not binding.get('enabled',True):continue
        binding=effective_binding(spec,binding)
        if not binding.get('required',True):
            if binding['id'] not in spec.get('dataEvidence',{}):continue
            result=read_evidence(spec,binding,base)
            if result.get('status')!='ready':continue
        else:result=read_evidence(spec,binding,base)
        validate_result(result,binding,now)

def reviewed_web_result(payload,binding,now=None):
    """Accept evidence extracted with the host's web tool; no arbitrary URL is fetched."""
    now=now or now_utc()
    if payload.get('reviewed') is not True or not str(payload.get('reviewNote','')).strip():raise DataError('ورود از وب به مدرک و یادداشت بازبینی واقعی عامل نیاز دارد.')
    if payload.get('task')!=binding['task']:raise DataError('نوع دادهٔ وب با درخواست یکسان نیست.')
    sources=payload.get('sources',[])
    if not sources:raise DataError('نشانی و نقل مستند منبع وب لازم است.')
    for source in sources:
        url=urllib.parse.urlsplit(source.get('url',''))
        if url.scheme!='https' or not url.hostname or url.username or url.password or not str(source.get('excerpt','')).strip():raise DataError('منبع وب باید HTTPS و نقل مستند داشته باشد.')
        age=(now-parse_time(source.get('retrievedAt'))).total_seconds()
        if not -60<=age<=3600:raise DataError('مدرک جست‌وجوی وب قدیمی است.')
    result={**payload,'schemaVersion':1,'status':'ready','fetchedAt':iso(now),
      'expiresAt':iso(min(now+dt.timedelta(minutes=10 if binding['task'] in {'rates','sports'} else 30),dt.datetime.combine(now.astimezone(TEHRAN).date()+dt.timedelta(days=1),dt.time(),TEHRAN)))}
    result['meta']={**payload.get('meta',{}),'provider':'host-web','reviewNote':payload['reviewNote']}
    validate_result(result,binding,now)
    if binding['task'] in {'rates','weather'}:
        observed=parse_time(result['meta'].get('observedAt'))
        if not -300<=(now-observed).total_seconds()<=(36*3600 if binding['task']=='rates' else 3*3600):raise DataError('زمان مشاهدهٔ وب قدیمی یا نامعتبر است.')
    if binding['task']=='rates':
        values=dict(result['values']);units=result['meta'].get('units',{})
        for field in RATE_FIELDS:
            if field not in values:raise DataError('پنج نرخ بازار لازم است.')
            amount=numeric(values[field]);unit=units.get(field)
            if amount<=0:raise DataError('نرخ باید مثبت باشد.')
            if field=='marketBitcoinPrice' and unit!='USD':raise DataError('واحد بیت‌کوین باید دلار آمریکا باشد.')
            if field!='marketBitcoinPrice':
                if unit=='IRR':amount/=10
                elif unit!='toman':raise DataError('واحد نرخ ایرانی باید ریال یا تومان مشخص باشد.')
            values[field]=fa(f'{amount:,.0f}' if amount==amount.to_integral() else f'{amount:,.2f}')
            units[field]='USD' if field=='marketBitcoinPrice' else 'toman'
            values[field.replace('Price','Change')]=''  # A daily website percentage is not a verified 24h delta.
        values['marketSource']=str(payload['sources'][0]['url']);values['marketTime']=fa(now.astimezone(TEHRAN).strftime('%H:%M'))
        result['values']=values;result['meta']['units']=units
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['catalog','fetch','batch','validate','review-web']);p.add_argument('value',nargs='?')
    p.add_argument('--evidence');p.add_argument('--binding')
    p.add_argument('--city',default='golbahar');p.add_argument('--date',default='today');p.add_argument('--competition',default='');p.add_argument('--mode',default='result');p.add_argument('--force',action='store_true')
    args=p.parse_args()
    if args.command=='catalog':result=catalog()
    elif args.command=='fetch':result=fetch(args.value,city=args.city,date=args.date,competition=args.competition,mode=args.mode,force=args.force)
    else:
        path=Path(args.value);spec=json.loads(path.read_text(encoding='utf-8'))
        if args.command=='batch':result=batch(spec,path.resolve().parent,force=args.force)
        elif args.command=='review-web':
            binding=next((b for b in spec.get('dataRequests',[]) if b['id']==args.binding),None)
            if not binding:raise DataError('درخواست داده پیدا نشد.')
            binding=effective_binding(spec,binding)
            result=reviewed_web_result(json.loads(Path(args.evidence).read_text(encoding='utf-8')),binding)
        else:validate_evidence(spec,path.resolve().parent);result={'valid':True}
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
    try:main()
    except (DataError,ValueError,KeyError,OSError) as exc:raise SystemExit(str(exc))
