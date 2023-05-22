# coding=utf-8
from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.core.mail import send_mail
from django.db.models import Max, Min
from sklearn.externals import joblib
import numpy as np


def notify(action, symbol, price):
    return
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

    direction = models.SmallIntegerField(
        _("Instrument direction"),
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

    open_price = models.FloatField(
        default=0.,
        null=True,
        blank=True
    )

    spread = models.FloatField(
        default=0.,
        null=True,
        blank=True
    )

    min_probability = models.SmallIntegerField(
        default=0.,
        null=False,
        blank=True
    )

    def __unicode__(self):
	return self.symbol

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

    def buy(self, price, p = 0):

        if self.position == PositionState.BUY:
            return

        Transaction.objects.create(
            instrument=self,
            position=PositionState.BUY,
            price=price,
            probability=p
        )

        self.position = PositionState.BUY
        self.direction = PositionState.BUY
        self.open_price = price
        self.save()

        print "Buy {0}:{1}".format(self.symbol, price)
        notify("Buy", self.symbol, price)

    def sell(self, price, p = 0):

        if self.position == PositionState.SELL:
            return

        Transaction.objects.create(
            instrument=self,
            position=PositionState.SELL,
            price=price,
            probability=p
        )
        self.position = PositionState.SELL
        self.direction = PositionState.SELL
        self.open_price = price
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
        prev_time = 0
        prev_pos = PositionState.CLOSED
        total = 0
        correct = 0
        max_income = 0
	max_income_vector = []
        p = 0
	pmax_instance = None
	income_percents = []
	#prev_pos = -10
        for t in Transaction.objects.filter(instrument=self).order_by('dttm'):
            d = 0
            if t.position == PositionState.CLOSED:
        	#print prev_prob
                if prev_pos == PositionState.BUY:
                    #res += t.price - prev_p - t.price*0.001
                    # d = t.price - prev_p - t.price*0.001
                    d = t.price - prev_p - t.instrument.spread
                    #res += result
		    pmax = 0
		    range_data = PriceHistory.objects.filter(instrument=self, dttm__gt=prev_time, dttm__lt=t.dttm)
		    for dd in range_data:
			if dd.price > pmax:
			    pmax = dd.price
			    pmax_instance = dd
		    
                    #pmax = PriceHistory.objects.filter(instrument=self, dttm__gt=prev_time, dttm__lt=t.dttm).aggregate(Max('price'))['price__max']
                    if pmax:
                        max_income = pmax  - prev_p
			'''
			mmax = PriceHistory.objects.filter(instrument=self, dttm__gt=prev_time, dttm__lt=t.dttm).order_by('-price')[0]
			print mmax
			mmax_ta = InstrumentTAHistory.objects.filter(instrument=self, dttm__lt=mmax.dttm).order_by('-dttm')[0]
			print mmax_ta
			print mmax_ta.get_x()
			model = joblib.load("/root/stocks-bot/models/%s_jpd.pkl" % self.symbol)
			X = np.array(mmax_ta.get_x()).reshape((1, len(mmax_ta.get_x())))
			print "WTF1"
			result = int(model.predict(X)[0])
			
			p = model.predict_proba(X)
	                probabilities = p.tolist()[0]
        		p_i = model.classes_.tolist().index(result)
			P = probabilities[p_i]
			print result, P
			'''


                	#print "P MAX: ", pmax, max_income, t.price, prev_p
                #if prev_pos == PositionState.SELL and prev_prob > .65:
                if prev_pos == PositionState.SELL:
                    #res += prev_p - t.price - t.price*0.001
                    #d = prev_p - t.price - t.price*0.001
                    d = prev_p - t.price - t.instrument.spread
                    pmin = PriceHistory.objects.filter(instrument=self, dttm__gt=prev_time, dttm__lt=t.dttm).aggregate(Min('price'))['price__min']
                    if pmin:
                        max_income = prev_p - pmin
			'''
			mmin = PriceHistory.objects.filter(instrument=self, dttm__gt=prev_time, dttm__lt=t.dttm).order_by('price')[0]
			print mmin
			mmin_ta = InstrumentTAHistory.objects.filter(instrument=self, dttm__lt=mmin.dttm).order_by('-dttm')[0]
			print mmin_ta
			print mmin_ta.get_x()
			print "WTF2"
			model = joblib.load("/root/stocks-bot/models/%s_jpd.pkl" % self.symbol)
			X = np.array(mmax_ta.get_x()).reshape((1, len(mmax_ta.get_x())))
			result = int(model.predict(X)[0])
			p = model.predict_proba(X)
	                probabilities = p.tolist()[0]
        		p_i = model.classes_.tolist().index(result)
			P = probabilities[p_i]
			print result, P
			'''

                res += d
        	#else:
                total += 1
		if prev_pos == PositionState.CLOSED:
		    print "!!!!", t.id
            if d > 0:
                correct += 1
            if t.position == PositionState.CLOSED:
		income_percent = float(max_income - t.instrument.spread)/float(t.price)*100.
		if income_percent > 0:
    		    income_percents.append(income_percent)
        	print t, t.dttm, t.price, t.position, "Income: ", d, "Max income:", max_income, "(", max_income - t.instrument.spread, ")", float(max_income - t.instrument.spread)/float(t.price)*100.
    	    else:
    		print t, t.dttm, t.price, t.position, t.probability
            prev_p = t.price
            prev_time = t.dttm
            prev_pos = t.position
            prev_prob = t.probability
            #total += 1

        #if not self.is_closed():
        #    if self.is_bullish():
        #        res += self.last_price - prev_p
	#
        #    elif self.is_bearish():
        #        res += prev_p - self.last_price
	if not total:
	    return 0,0
        if total > 0 and correct > 0:
            p = (float(correct)/float(total) * 100.)
        print "Last price:", self.last_price
	print "Average max income percent:", reduce(lambda x, y: x + y, income_percents) / len(income_percents)
        return res, p

    class Meta:
        pass


class PriceHistory(models.Model):

    dttm = models.DateTimeField(auto_now_add=True, db_index=True)
    instrument = models.ForeignKey(Instrument)
    price = models.FloatField(
        default=0.,
        null=True,
        blank=True
    )
    def __unicode__(self):
	return "{} {}: {}".format(self.instrument, self.dttm, self.price)

    class Meta:
        unique_together = ("instrument", "dttm")

class InstrumentTAHistory(models.Model):

    instrument = models.ForeignKey(Instrument)
    dttm = models.DateTimeField(auto_now_add=True)

    # RSI
    rsi_14_val = models.FloatField(default=0)
    rsi_14_act = models.SmallIntegerField(default=PositionState.CLOSED)

    # STOCH(9,6)
    stoch_9_6_val = models.FloatField(default=0)
    stoch_9_6_act = models.SmallIntegerField(default=PositionState.CLOSED)

    # STOCHRSI(14)	
    stochrsi_14_val = models.FloatField(default=0)
    stochrsi_14_act = models.SmallIntegerField(default=PositionState.CLOSED)

    # MACD(12,26)	
    macd_12_26_val = models.FloatField(default=0)
    macd_12_26_act = models.SmallIntegerField(default=PositionState.CLOSED)

    # ADX(14)	
    adx_14_val = models.FloatField(default=0)
    adx_14_act = models.SmallIntegerField(default=PositionState.CLOSED)

    # Williams %R	
    williams_val = models.FloatField(default=0)
    williams_act = models.SmallIntegerField(default=PositionState.CLOSED)

    # CCI(14)	
    cci_14_val = models.FloatField(default=0)
    cci_14_act = models.SmallIntegerField(default=PositionState.CLOSED)

    # ATR(14)	
    atr_14_val = models.FloatField(default=0)
    atr_14_act = models.SmallIntegerField(default=PositionState.CLOSED)

    # Highs/Lows(14)
    highs_lows_14_val = models.FloatField(default=0)
    highs_lows_14_act = models.SmallIntegerField(default=PositionState.CLOSED)

    # Ultimate Oscillator
    ultimate_oscillator_val = models.FloatField(default=0)
    ultimate_oscillator_act = models.SmallIntegerField(default=PositionState.CLOSED)

    # ROC
    roc_val = models.FloatField(default=0)
    roc_act = models.SmallIntegerField(default=PositionState.CLOSED)

    # Bull/Bear Power(13)
    bb_power_val = models.FloatField(default=0)
    bb_power_act = models.SmallIntegerField(default=PositionState.CLOSED)	
    
    # Moving avegares
    ma5 = models.SmallIntegerField(default=PositionState.CLOSED)
    ma10 = models.SmallIntegerField(default=PositionState.CLOSED)
    ma50 = models.SmallIntegerField(default=PositionState.CLOSED)
    ma20 = models.SmallIntegerField(default=PositionState.CLOSED)
    ma100 = models.SmallIntegerField(default=PositionState.CLOSED)
    ma200 = models.SmallIntegerField(default=PositionState.CLOSED)
    price = models.FloatField(
        default=0.,
        null=True,
        blank=True
    )

    # Pivot points
    s1 = models.FloatField(null=True, blank=True)
    s2 = models.FloatField(null=True, blank=True)
    s3 = models.FloatField(null=True, blank=True)
    r1 = models.FloatField(null=True, blank=True)
    r2 = models.FloatField(null=True, blank=True)
    r3 = models.FloatField(null=True, blank=True)

    price_direction = models.SmallIntegerField(
        default=0.,
        null=True,
        blank=True
    )

    avg_price_later = models.FloatField(
        default=0.,
        null=True,
        blank=True
    )
    def get_x(self):
	return [
                self.rsi_14_act,
                self.stoch_9_6_act,
                self.stochrsi_14_act,
                self.macd_12_26_act,
                self.adx_14_act,
                self.williams_act,
                self.cci_14_act,
                #atr_14_act,
                self.highs_lows_14_act,
                self.ultimate_oscillator_act,
                self.roc_act,
                self.bb_power_act,
                self.ma5,
                self.ma10,
                self.ma20,
                self.ma50,
                self.ma100,
                self.ma200,
		self.price_direction
        ]

    #price = models.ForeignKey(PriceHistory, default=None)
    def __unicode__(self):
	return "{} {}".format(self.instrument, self.dttm)




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
    probability = models.FloatField(default=0., null=True, blank=True)
    def __unicode__(self):
        c = {
           1: u"Buy",
           0: u"Close",
           -1: u"Sell",
        }
        return u"{0}:: {1}".format(self.instrument.symbol, c[self.position])

class ExperimentalTransaction(models.Model):

    instrument = models.ForeignKey(Instrument)
    dttm = models.DateTimeField(auto_now_add=True)

    position = models.SmallIntegerField(
        _("Transaction state"),
        default=PositionState.CLOSED,
        choices=PositionState.choices
    )

    price = models.FloatField(default=0., null=False, blank=False)
    probability = models.FloatField(default=0., null=True, blank=True)
    def __unicode__(self):
        c = {
           1: u"Buy",
           0: u"Close",
           -1: u"Sell",
        }
        return u"{0}:: {1}".format(self.instrument.symbol, c[self.position])
    
