# coding=utf-8
import re
import math
import requests
import datetime
from pytz import timezone

from bs4 import BeautifulSoup
from django.conf import settings

from django.core.management import BaseCommand

from stocks.models import CalendarData, CalendarDataState

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

class Command(BaseCommand):

    def handle(self, *args, **options):

        print "Fetching calendar"

        try:
            r = requests.get(settings.CALENDAR_URL, headers=headers, timeout=20)
        except:
            print "Failed!"
            return "ERROR"
        else:
            print "Done!"

        #soup = BeautifulSoup(r.text)
        soup = BeautifulSoup(r.text, "lxml")

        event_rows = soup.findAll("tr", {"id" : re.compile('eventRowId.*')})
        date_div = soup.find("div", {"id" : "widgetFieldDateRange"})
        to_digits = lambda s: filter(lambda x: x.isdigit() or x in ['.', '-'], s)

        now = datetime.datetime.now()
        month, day, year = ( now.month, now.day, now.year )

        score = {}

        for er in event_rows:
            result = has_result = 0
	    print er
            #time = er.find("td", {'class': 'time'}).attrs['evtstrttime'].strip()
	    time = er.find("td", {'class': 'time'}).text.strip()
            zone_td = er.find("td", {'class': 'flagCur'})
            region = zone_td.find("span").attrs['title'].strip()
            currency = zone_td.text.strip()
            importance = len(er.find("td", {'class': 'sentiment'}).findAll("i", {'class': 'grayFullBullishIcon'}))
            title = er.find("td", {'class': 'event'}).text.strip()

            actual_elm = er.find("td", {'class': 'act'})
	    if not actual_elm: continue
	    print actual_elm.text
            actual = to_digits(actual_elm.text.strip())
            forecast = to_digits(er.find("td", {'class': 'fore'}).text.strip())
            previous = to_digits(er.find("td", {'class': 'prev'}).text.strip())

            if actual and forecast and previous:
                map(float, (actual, forecast, previous))
                result = importance * -1 if actual < forecast else 1
                has_result = True

            elif actual and previous:
                map(float, (actual, previous))
                result = importance * -1 if actual < previous else 1
                has_result = True

	    from django.utils import timezone

            dttm = datetime.datetime(year, month, day, int(time.split(':')[0]), int(time.split(':')[1]))
            #dttm = dttm.replace(tzinfo=timezone('UTC'))
            #dttm = dttm.replace(tzinfo=timezone(settings.TIME_ZONE))
	    dt_aware = timezone.make_aware(dttm, timezone.get_current_timezone())
    

	    print dttm, dt_aware
            if has_result:

                sentiment = CalendarDataState.NEUTRAL
                actual_data_class = actual_elm.attrs['class']

                if 'greenFont' in actual_data_class:
                    sentiment = CalendarDataState.POSITIVE

                elif 'redFont' in actual_data_class:
                    sentiment = CalendarDataState.NEGATIVE

                CalendarData.objects.get_or_create(
                    region = region,
                    currency = currency,
                    importance = importance,
                    title = title, 
                    actual = float(actual), 
                    forecast = float(forecast) if forecast else None,
                    previous = float(previous),
                    sentiment = sentiment,
                    dttm = dttm,
                )

            if has_result:
                try:
                    score[region] += result
                except:
                    score[region] = result
