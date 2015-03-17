# coding=utf-8
import math
import requests
from bs4 import BeautifulSoup

from django.core.management import BaseCommand
from django.utils import timezone

from stocks.models import Instrument, InstrumentTASummary, PositionState


class Command(BaseCommand):

    def handle(self, *args, **options):

        total = 0
        for instrument in Instrument.objects.all():

            print "Summary {0} ({1}):".format(instrument.symbol, instrument.last_price)
            income = instrument.get_income()
            print income
            total += income

        print "Total: ", total
