from __future__ import annotations
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import public_data as data

NOW=dt.datetime(2026,11,3,22,0,tzinfo=dt.timezone.utc)
DAY=dt.date(2026,11,4)
class FakeClient:
    def __init__(self,payloads,root=None):
        self.payloads=payloads;self.now=NOW;self.sources=[];self.cache=Path(root) if root else Path(tempfile.gettempdir())/'unused'
    def get(self,url,**kwargs):
        self.sources.append({'url':url,'retrievedAt':data.iso(NOW),'sha256':'0'*64})
        for key,value in self.payloads.items():
            if key in url:
                if isinstance(value,Exception):raise value
                return copy.deepcopy(value)
        raise data.DataError('fixture has no response for '+url)

def aladhan():
    return {'code':200,'data':{'date':{'gregorian':{'date':'04-11-2026'},'hijri':{'day':'24','month':{'number':5},'year':'1448'}},
      'meta':{'latitude':36.56976,'longitude':59.19040,'timezone':'Asia/Tehran','method':{'id':0}},
      'timings':dict(zip(['Fajr','Sunrise','Dhuhr','Sunset','Maghrib','Midnight'],['04:30','06:00','11:30','17:00','17:20','23:30']))}}
def weather():
    return {'timezone':'Asia/Tehran','current':{'time':'2026-11-04T01:15','temperature_2m':12,'apparent_temperature':11,
      'weather_code':3,'wind_speed_10m':5,'relative_humidity_2m':60},
      'daily':{'time':['2026-11-04'],'temperature_2m_min':[8],'temperature_2m_max':[18],
        'weather_code':[3],'wind_speed_10m_max':[9],'relative_humidity_2m_max':[75],'apparent_temperature_max':[17]}}
def event(**kwargs):
    return {'idEvent':'123','idLeague':'4328','strSeason':'2026-2027','strHomeTeam':'Arsenal','strAwayTeam':'Chelsea',
      'dateEvent':'2026-11-03','strTime':'22:30:00','strTimestamp':'2026-11-03T22:30:00','strStatus':'NS',
      'intHomeScore':None,'intAwayScore':None,**kwargs}
def sports_client(events):
    return FakeClient({'lookupleague':{'leagues':[{'idLeague':'4328','strCurrentSeason':'2026-2027'}]},'eventsseason':{'events':events}})
def month_page(rows=''):
    return '<title>تقویم آبان ۱۴۰۵</title><table id="bahesab-time">'+''.join(f'<td class="{"Ho" if day==13 else ""}">{day}<br><small>1</small></td>' for day in range(1,31))+'</table>'+rows

class PublicDataTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
    def test_iran_day_is_not_the_utc_date(self):
        self.assertEqual(data.target_date('today',NOW),DAY)
        self.assertIn('۱۴۰۵',data.base_dates(DAY)['morningPersianDate'])
        self.assertEqual(data.base_dates(dt.date(2026,3,21))['morningPersianDate'],'۱ فروردین ۱۴۰۵')
    def test_date_and_all_six_prayers_use_same_city_and_day(self):
        client=FakeClient({'aladhan':aladhan()})
        date=data.fetch('date',now=NOW,client=client)
        prayer=data.fetch('prayer',now=NOW,client=client)
        self.assertEqual(date['status'],'ready');self.assertIn('جمادی‌الاول',date['values']['morningHijriDate'])
        self.assertEqual(len(prayer['values']),6);self.assertEqual(prayer['values']['morningMidnight'],'۲۳:۳۰')
        self.assertTrue(all('04-11-2026' in source['url'] for source in prayer['sources']))
    def test_wrong_prayer_date_or_city_is_blocked(self):
        for change in ['date','city','method']:
            payload=aladhan()
            if change=='date':payload['data']['date']['gregorian']['date']='03-11-2026'
            if change=='city':payload['data']['meta']['latitude']=40
            if change=='method':payload['data']['meta']['method']['id']=3
            result=data.fetch('prayer',now=NOW,client=FakeClient({'aladhan':payload}))
            self.assertEqual(result['status'],'blocked');self.assertEqual(result['values'],{})
    def test_weather_has_provenance_and_rejects_old_observation(self):
        result=data.fetch('weather',now=NOW,client=FakeClient({'open-meteo':weather()}))
        self.assertEqual(result['status'],'ready');self.assertEqual(result['values']['morningMinTemperature'],'۸')
        self.assertEqual(result['meta']['timeZone'],'Asia/Tehran');self.assertTrue(result['sources'])
        payload=weather();payload['current']['time']='2026-11-03T10:00'
        self.assertEqual(data.fetch('weather',now=NOW,client=FakeClient({'open-meteo':payload}))['status'],'blocked')
    def test_future_weather_uses_forecast_not_current_conditions(self):
        payload=weather();payload['daily']['time']=['2026-11-05'];payload['current']['weather_code']=95
        result=data.fetch('weather',date='2026-11-05',now=NOW,client=FakeClient({'open-meteo':payload}))
        self.assertEqual(result['status'],'ready');self.assertTrue(result['meta']['forecast'])
        self.assertEqual(result['values']['morningWeatherCondition'],'ابری')
    def test_monthly_calendar_parses_nested_events_and_holidays(self):
        page='<li class="totall-m"><span class="M2">۱۳ آبان</span><span class="M6"><span class="M4">مناسبت اول</span></span><span class="M6">مناسبت دوم</span></li>'
        events,holiday=data.monthly_events(page,13)
        self.assertEqual(events,['مناسبت اول','مناسبت دوم']);self.assertTrue(holiday)
        with self.assertRaises(data.DataError):data.monthly_events('<html>broken</html>',13)
    def test_week_calendar_includes_saturday_to_friday_and_public_holiday(self):
        page=month_page()
        result=data.fetch('kalam-calendar',now=NOW,client=FakeClient({'bahesab':page}))
        self.assertEqual(result['status'],'ready');self.assertEqual(result['meta']['todayIndex'],5)
        self.assertIn(5,result['meta']['holidayIndexes']);self.assertIn(7,result['meta']['holidayIndexes'])
    def test_calendar_merges_global_events_without_replacing_local(self):
        page=month_page('<li class="totall-m"><span class="M1">۱۳ آبان</span><span class="M6">مناسبت محلی</span></li>')
        global_data={'data':[{'type':'International','calendar':'Gregorian','rule':'simple','month':11,'day':4,'title':'مناسبت جهانی'}]}
        result=data.fetch('occasions',now=NOW,client=FakeClient({'bahesab':page,'events.json':global_data}))
        self.assertEqual(result['values']['morningLocalOccasion'],'مناسبت محلی\nمناسبت جهانی')
    def test_match_time_crosses_midnight_to_tehran_and_preserves_teams(self):
        result=data.fetch('sports',competition='premier_league',mode='upcoming',now=NOW,client=sports_client([event()]))
        self.assertEqual(result['status'],'ready');game=result['meta']['events'][0]
        self.assertEqual(game['date'],'2026-11-04');self.assertEqual(game['time'],'02:00')
        self.assertEqual(game['home'],'آرسنال');self.assertIn('وقت تهران',result['values']['sportResults'])
    def test_sports_do_not_replace_empty_schedule_with_old_or_unrelated_games(self):
        for events in [[],[event(strSeason='2025-2026')],[event(strStatus='Match Postponed')]]:
            result=data.fetch('sports',competition='premier_league',mode='upcoming',now=NOW,client=sports_client(events))
            self.assertEqual(result['status'],'blocked')
        result=data.fetch('sports',competition='world_cup',now=NOW,client=FakeClient({}))
        self.assertEqual(result['status'],'blocked');self.assertEqual(result['fallback']['type'],'host-web')
    def test_in_progress_score_is_not_published_as_a_final_result(self):
        result=data.fetch('sports',competition='premier_league',mode='result',now=NOW,
          client=sports_client([event(strStatus='1H',intHomeScore='1',intAwayScore='0')]))
        self.assertEqual(result['status'],'blocked')
    def test_tgju_fallback_converts_rial_to_toman_but_does_not_invent_quote_date(self):
        page=''.join(f'<tr data-market-row="{name}" data-price="1000"><td>1000</td><td>۱۹:۲۵:۰۰</td></tr>' for name in data.TGJU_ROWS)
        page+='<tr data-market-row="crypto-bitcoin" data-price=""><td>209000000000</td><td>1000</td></tr>'
        client=FakeClient({'baha24':data.DataError('HTTP 401'),'tgju':page},self.base)
        result=data.fetch('rates',now=NOW,client=client)
        self.assertEqual(result['status'],'needs-review')
        self.assertEqual(result['values']['marketUsdPrice'],'۱۰۰');self.assertEqual(data.numeric(result['values']['marketBitcoinPrice']),data.Decimal(1000))
        self.assertEqual(result['values']['marketUsdChange'],'');self.assertFalse((self.base/'market-history.json').exists())
    def test_real_baseline_is_required_for_a_24_hour_change(self):
        client=FakeClient({},self.base)
        before=data.changes({'marketUsdPrice':data.Decimal(100)},'test',client)
        self.assertEqual(before['marketUsdChange'],'')
        client.now=NOW+dt.timedelta(hours=24)
        after=data.changes({'marketUsdPrice':data.Decimal(110)},'test',client)
        self.assertEqual(after['marketUsdChange'],'+۱۰.۰۰')
        unrelated=data.changes({'marketUsdPrice':data.Decimal(110)},'another-provider',client)
        self.assertEqual(unrelated['marketUsdChange'],'')
    def test_stale_cache_never_becomes_fresh_after_network_failure(self):
        client=data.Client(self.base,NOW)
        url='https://api.open-meteo.com/v1/forecast';key=hashlib.sha256(url.encode()).hexdigest()
        data.write_json(self.base/f'{key}.json',{'retrievedAt':data.iso(NOW-dt.timedelta(days=1)),'body':'{"old": true}'})
        with mock.patch('urllib.request.build_opener') as build:
            build.return_value.open.side_effect=TimeoutError('offline')
            with self.assertRaises(data.DataError):client.get(url)
    def test_transport_rejects_unapproved_or_non_https_destinations(self):
        for url in ['http://api.open-meteo.com/','https://evil.example/','https://user:pass@api.aladhan.com/']:
            with self.assertRaises(data.DataError):data.allowed_url(url)
    def test_reviewed_web_requires_actual_sources_timestamp_and_matching_context(self):
        binding={'id':'weather','task':'weather','city':'golbahar','date':'today'}
        values=data.fetch('weather',now=NOW,client=FakeClient({'open-meteo':weather()}))['values']
        payload={'task':'weather','reviewed':True,'reviewNote':'منبع و زمان بررسی شدند','values':values,
          'meta':{'date':str(DAY),'city':'golbahar','timeZone':'Asia/Tehran','observedAt':data.iso(NOW)},
          'sources':[{'url':'https://example.org/weather','retrievedAt':data.iso(NOW),'excerpt':'دما و باد برای روز انتخاب‌شده'}]}
        good=data.reviewed_web_result(payload,binding,NOW);self.assertEqual(good['status'],'ready')
        bad=copy.deepcopy(payload);bad['sources']=[]
        with self.assertRaises(data.DataError):data.reviewed_web_result(bad,binding,NOW)
        bad=copy.deepcopy(payload);bad['meta']['city']='chenaran'
        with self.assertRaises(data.DataError):data.reviewed_web_result(bad,binding,NOW)
    def test_evidence_expires_at_tehran_midnight_and_detects_tampering(self):
        near_midnight=dt.datetime(2026,11,4,20,29,50,tzinfo=dt.timezone.utc)
        binding={'id':'a','task':'weather','city':'golbahar','date':'today'}
        result=data.fetch('weather',now=NOW,client=FakeClient({'open-meteo':weather()}))
        result.update({'fetchedAt':data.iso(near_midnight),'expiresAt':data.iso(near_midnight+dt.timedelta(seconds=10))})
        with self.assertRaises(data.DataError):data.validate_result(result,binding,near_midnight+dt.timedelta(seconds=11))
        file=self.base/'weather.json';data.write_json(file,result);raw=file.read_bytes()
        spec={'dataRequests':[binding],'dataEvidence':{'a':{'path':'weather.json','sha256':hashlib.sha256(raw).hexdigest()}}}
        file.write_text('{}')
        with self.assertRaisesRegex(data.DataError,'تغییر'):data.validate_evidence(spec,self.base,near_midnight)
    def test_catalog_has_no_news_discovery_task(self):
        catalog=data.catalog();self.assertFalse(catalog['newsDiscovery'])
        self.assertEqual(set(catalog['tasks']),data.TASKS)
    def test_fresh_host_web_evidence_is_reused_instead_of_refetching_a_failed_provider(self):
        binding={'id':'weather','task':'weather','target':'context','city':'golbahar','date':'today'}
        result=data.fetch('weather',now=NOW,client=FakeClient({'open-meteo':weather()}))
        file=self.base/'evidence.json';data.write_json(file,result)
        spec={'kind':'text','brand':'golbahar','dataRequests':[binding],'dataEvidence':{'weather':{'path':'evidence.json','sha256':hashlib.sha256(file.read_bytes()).hexdigest()}}}
        with mock.patch('public_data.fetch',side_effect=AssertionError('must reuse evidence')):
            output=data.batch(spec,self.base,now=NOW)
        self.assertEqual(output[0]['result']['status'],'ready')
    def test_empty_events_in_a_verified_full_month_are_a_valid_day(self):
        result=data.fetch('occasions',now=NOW,client=FakeClient({'bahesab':month_page(),'events.json':{'data':[]}}))
        self.assertEqual(result['status'],'ready');self.assertEqual(result['values']['morningLocalOccasion'],'')

if __name__=='__main__':unittest.main()
