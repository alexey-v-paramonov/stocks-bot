# coding=utf-8
from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.core.mail import send_mail

# Create your models here.


def notify(action, symbol, price):

    subj = message = "{0} {1} @ {2}".format(action, symbol, price)
    send_mail(
        subj,
        message,
        'info@radio-tochka.com',
        ['info@radio-tochka.com'],
        fail_silently=False
    )


class InstrumentTASummary(object):

    STRONG_SELL = -2
    SELL = -1
    NEUTRAL = 0
    BUY = 1
    STRONG_BUY = 2

    mapping = {
        u'STRONG SELL': STRONG_SELL,
        u'SELL': SELL,
        u'NEUTRAL': NEUTRAL,
        u'BUY': BUY,
        u'STRONG BUY': STRONG_BUY,
    }


class PositionState(object):

    BUY = 1
    SELL = -1
    CLOSED = 0

    choices = (
        (BUY, 'buy'),
        (SELL, 'sell'),
        (CLOSED, 'closed'),
    )

class CalendarDataState(object):

    NEGATIVE = -1
    POSITIVE = 1
    NEUTRAL = 0

    choices = (
        (NEGATIVE, 'Negative'),
        (POSITIVE, 'Positive'),
        (NEUTRAL, 'Neutral'),
    )


class Instrument(models.Model):

    trader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Trader"),
        blank=True,
        null=True,
    )

    symbol = models.CharField(
        'Instrument symbol',
        max_length=255,
        blank=False,
        null=True,
    )

    url = models.URLField(
        'Instrument url',
        blank=False,
        null=True,
    )

    interval = models.PositiveIntegerField(
        default=18000,
        blank=True,
        null=False
    )

    position = models.SmallIntegerField(
        _("Instrument state"),
        default=PositionState.CLOSED,
        choices=PositionState.choices
    )

    ta_summary = models.SmallIntegerField(
        _("Instrument TA summary"),
        default=PositionState.CLOSED,
        choices=PositionState.choices
    )

    calendar_summary = models.SmallIntegerField(
        _("Instrument calendar summary"),
        default=PositionState.CLOSED,
        choices=PositionState.choices
    )

    calendar_summary_dttm = models.DateTimeField(
        null=True
    )

    sentiment_summary = models.SmallIntegerField(
        _("Instrument sentiment summary"),
        default=PositionState.CLOSED,
        choices=PositionState.choices
    )

    last_price = models.FloatField(
        default=0.,
        null=True,
        blank=True
    )

    def get_url(self):
        return "{0}?period={1}".format(self.url, self.interval)

    def is_closed(self):
        return self.position == PositionState.CLOSED

    def is_bearish(self):
        return self.position == PositionState.SELL

    def is_bullish(self):
        return self.position == PositionState.BUY

    def needs_update(self, position):

        if self.is_closed():
            if (position == InstrumentTASummary.STRONG_BUY):
                return PositionState.BUY
            elif (position == InstrumentTASummary.STRONG_SELL):
                return PositionState.SELL
            else:
                return PositionState.CLOSED

        elif self.is_bullish():
            if position in (
                    InstrumentTASummary.STRONG_SELL, InstrumentTASummary.SELL
            ):
                return PositionState.CLOSED

        elif self.is_bearish():
            if position in (
                    InstrumentTASummary.STRONG_BUY, InstrumentTASummary.BUY
            ):
                return PositionState.CLOSED

    def buy(self, price):

        if self.position == PositionState.BUY:
            return

        Transaction.objects.create(
            instrument=self,
            position=PositionState.BUY,
            price=price
        )

        self.position = PositionState.BUY
        self.save()

        print "Buy {0}:{1}".format(self.symbol, price)
        notify("Buy", self.symbol, price)

    def sell(self, price):

        if self.position == PositionState.SELL:
            return

        Transaction.objects.create(
            instrument=self,
            position=PositionState.SELL,
            price=price
        )
        self.position = PositionState.SELL
        self.save()

        print "Sell {0}:{1}".format(self.symbol, price)
        notify("Sell", self.symbol, price)

    def close(self, price):

        if self.position == PositionState.CLOSED:
            return

        Transaction.objects.create(
            instrument=self,
            position=PositionState.CLOSED,
            price=price
        )
        self.position = PositionState.CLOSED
        self.save()

        print "Close {0}:{1}".format(self.symbol, price)
        notify("Close", self.symbol, price)

    def get_income(self):

        res = 0
        prev_p = 0
        prev_pos = PositionState.CLOSED

        for t in Transaction.objects.filter(instrument=self).order_by('dttm'):
            if t.position == PositionState.CLOSED:

                if prev_pos == PositionState.BUY:
                    res += t.price - prev_p - t.price*0.001

                if prev_pos == PositionState.SELL:
                    res += prev_p - t.price - t.price*0.001

            print t, t.dttm, t.price, t.position
            prev_p = t.price
            prev_pos = t.position

        if not self.is_closed():
            if self.is_bullish():
                res += self.last_price - prev_p

            elif self.is_bearish():
                res += prev_p - self.last_price

        return res


class PriceHistory(models.Model):

    dttm = models.DateTimeField(auto_now_add=True)
    instrument = models.ForeignKey(Instrument)
    price = models.FloatField(
        default=0.,
        null=True,
        blank=True
    )


class CalendarData(models.Model):

    dttm = models.DateTimeField(
        blank=False,
        null=False,
    )

    region = models.CharField(
        'Region',
        max_length=255,
        blank=False,
        null=True,
    )

    currency = models.CharField(
        'Currency',
        max_length=5,
        blank=False,
        null=True,
    )

    importance = models.PositiveIntegerField(
        default=1,
        blank=True,
        null=False
    )

    title = models.CharField(
        'Data title',
        max_length=255,
        blank=False,
        null=True,
    )

    data_type = models.SmallIntegerField(
        "Data type",
        null=True
    )

    actual = models.FloatField(
        null=True,
        blank=True
    )

    forecast = models.FloatField(
        null=True,
        blank=True
    )

    previous = models.FloatField(
        null=True,
        blank=True
    )

    sentiment = models.SmallIntegerField(
        _("Calendar data sentiment"),
        default=CalendarDataState.NEUTRAL,
        choices=CalendarDataState.choices
    )

    class Meta:
        unique_together = ( "dttm", "region", "currency", "title")


class Transaction(models.Model):

    instrument = models.ForeignKey(Instrument)
    dttm = models.DateTimeField(auto_now_add=True)

    position = models.SmallIntegerField(
        _("Transaction state"),
        default=PositionState.CLOSED,
        choices=PositionState.choices
    )

    price = models.FloatField(default=0., null=False, blank=False)
