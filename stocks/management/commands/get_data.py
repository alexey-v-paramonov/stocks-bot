# coding=utf-8
import math
import requests
from bs4 import BeautifulSoup

from django.core.management import BaseCommand

from stocks.models import (
    Instrument,
    InstrumentTASummary,
    PositionState,
    notify,
    PriceHistory,
)


class Command(BaseCommand):

    def handle(self, *args, **options):

        for instrument in Instrument.objects.all():

            print "Fetching {0} from {1}...".format(
                instrument.symbol, instrument.get_url()
            ),

            try:
                r = requests.get(instrument.get_url())
            except:
                print "Failed!"
                continue
            else:
                print "Done!"

            soup = BeautifulSoup(r.text)
            summary = soup.find(
                "div", { "class" : "studySummary" }
            ).find(
                "span", { "class" : "studySummaryOval" }
            )
            
            last_price = float(soup.find(id="last_last").text.replace(",", ""))

            position = InstrumentTASummary.mapping[summary.text]
            action = instrument.needs_update(position)
            print "Summary: ", summary.text

            if action == PositionState.BUY:
                instrument.buy(last_price)
            elif action == PositionState.SELL:
                instrument.sell(last_price)
            elif action == PositionState.CLOSED:
                instrument.close(last_price)
                action = instrument.needs_update(position)
                if action == PositionState.BUY:
                    instrument.buy(last_price)
                elif action == PositionState.SELL:
                    instrument.sell(last_price)



            instrument.last_price = last_price
            instrument.save()

            PriceHistory.objects.create(
                instrument = instrument,
                price = last_price
            )
