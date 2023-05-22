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
	#i = Instrument.objects.all().exclude(pk__in=(13,14,15))
	i = Instrument.objects.all()
	max_price = 0

        for instrument in i:
	    print instrument
	    if instrument.last_price > max_price:
		max_price = instrument.last_price
	print max_price

        for instrument in i:
	    print instrument
	    if instrument.last_price > max_price:
		max_price = instrument.last_price
	print max_price
    
        for instrument in i:
	    print instrument.symbol,instrument.last_price
	    print round(max_price/instrument.last_price)
	    instrument.num = round(max_price/instrument.last_price)
	print max_price
	#max_price = 
        for instrument in i:
            print "Summary {0} ({1}):".format(instrument.symbol, instrument.last_price)
            income, p = instrument.get_income()
            #print income*instrument.num, p
            total += income*instrument.num
            print income, p
            total += income

        print "Total: ", total
