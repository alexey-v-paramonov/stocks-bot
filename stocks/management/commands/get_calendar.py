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


class Command(BaseCommand):

    def handle(self, *args, **options):

        print "Fetching calendar"

        try:
            r = requests.get(settings.CALENDAR_URL)
        except:
            print "Failed!"
            return "ERROR"
        else:
            print "Done!"

        soup = BeautifulSoup(r.text)

        event_rows = soup.findAll("tr", {"id" : re.compile('eventRowId.*')})
        date_div = soup.find("div", {"id" : "widgetFieldDateRange"})
        to_digits = lambda s: filter(lambda x: x.isdigit() or x in ['.', '-'], s)

        now = datetime.datetime.now()
        month, day, year = ( now.month, now.day, now.year )

        score = {}

        for er in event_rows:
            result = has_result = 0
            time = er.find("td", {'class': 'time'}).attrs['evtstrttime'].strip()
            zone_td = er.find("td", {'class': 'flagCur'})
            region = zone_td.find("span").attrs['title'].strip()
            currency = zone_td.text.strip()
            importance = len(er.find("td", {'class': 'sentiment'}).findAll("i", {'class': 'grayFullBullishIcon'}))
            title = er.find("td", {'class': 'event'}).text.strip()

            actual_elm = er.find("td", {'class': 'act'})
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

            dttm = datetime.datetime(year, month, day, int(time.split(':')[0]), int(time.split(':')[1]))
            dttm = dttm.replace(tzinfo=timezone('UTC'))
            dttm = dttm.replace(tzinfo=timezone(settings.TIME_ZONE))

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
