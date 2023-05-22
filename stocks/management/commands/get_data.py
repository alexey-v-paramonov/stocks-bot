# coding=utf-8
import math
import requests
from django.utils import timezone
import cPickle
from sklearn.externals import joblib

from datetime import datetime, timedelta
from sklearn.linear_model import LogisticRegression
import numpy as np

from bs4 import BeautifulSoup

from django.core.management import BaseCommand
from django.db.models import Avg

from stocks.models import (
    Instrument,
    InstrumentTASummary,
    InstrumentTAHistory,
    PositionState,
    notify,
    PriceHistory,
)

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

INTERVAL = 3600

class Command(BaseCommand):

    def handle(self, *args, **options):

        print "###################################"
	if timezone.now().date().weekday() > 4:
	    print "Weekend!"
	    exit()

        for instrument in Instrument.objects.all():
            print "\nFetching {0} from {1}...".format(
                instrument.symbol, instrument.get_url()
            ),

            try:
                r = requests.get(instrument.get_url(), headers=headers, timeout=20)
            except:
                print "Failed!"
                continue
            else:
                print "Done!"

            soup = BeautifulSoup(r.text, "lxml")
	    #print r.text
	    if not soup: continue
            pre_summary = soup.find(
                "div", { "class" : "summary" }
            )
	    if not pre_summary: continue
	    summary = pre_summary.find(
                "span"
            )

            closed = soup.find("div", {"id": "quotes_summary_current_data"}).find(
                "div", { "class" : ["bottom", "lighterGrayFont", "arial_11"] }
            ).text.find("Closed") >= 0

            if closed:
		        print "Market closed"
		        continue

            last_price = float(soup.find(id="last_last").text.replace(",", ""))

            position = InstrumentTASummary.mapping[summary.text.upper()]
            #action = instrument.needs_update(position)
            #print "Summary: ", summary.text, action

            #if action == PositionState.BUY:
            #    instrument.buy(last_price)
            #elif action == PositionState.SELL:
            #    instrument.sell(last_price)
            #elif action == PositionState.CLOSED:
            #    instrument.close(last_price)
            #    action = instrument.needs_update(position)
            #    if action == PositionState.BUY:
            #        instrument.buy(last_price)
            #    elif action == PositionState.SELL:
            #        instrument.sell(last_price)

            instrument.last_price = last_price
            instrument.save()

            PriceHistory.objects.create(
                instrument = instrument,
                price = last_price
            )
            # Save TA data
            ta_table = soup.find("table", {"class": "technicalIndicatorsTbl"})
            ACTIONS = {
                "sell": -1,
                "buy": 1,
		"overbought": 2,
		"oversold": -2,
            }
            if ta_table:
                ta_rows = ta_table.findAll("tr")[1:-1]
                values = []
                actions = []
                if ta_rows:
                    for tr in ta_rows:
                        tds = tr.findAll("td")
                        val, act = float(tds[1].text), ACTIONS.get(tds[2].find("span").text.strip().lower(), 0)
                        values.append(val)
                        actions.append(act)
                else:
                    print "TA table rows not found, continue"
                    continue

                (
                    rsi_14_val,
                    stoch_9_6_val,	
                    stochrsi_14_val,
                    macd_12_26_val,
                    adx_14_val,	
                    williams_val,
                    cci_14_val,
                    atr_14_val,
                    highs_lows_14_val,
                    ultimate_oscillator_val,
                    roc_val,
                    bb_power_val
                ) = values 	

                (
                    rsi_14_act,
                    stoch_9_6_act,	
                    stochrsi_14_act,
                    macd_12_26_act,
                    adx_14_act,	
                    williams_act,
                    cci_14_act,
                    atr_14_act,
                    highs_lows_14_act,
                    ultimate_oscillator_act,
                    roc_act,
                    bb_power_act
                ) = actions 
	
            ma_table = soup.find("table", {"class": "movingAvgsTbl"})
            if ma_table:
                ma_rows = ma_table.findAll("tr")[1:-1]
                if ma_rows:
                    ma_actions = []
                    for tr in ma_rows:
                        tds = tr.findAll("td")
                        act = ACTIONS.get(tds[2].find("span").text.strip().lower(), 0)
                        ma_actions.append(act)
                else:
                    print "Moving average table rows not found"
                    continue                
                (ma5, ma10, ma20, ma50, ma100, ma200) = ma_actions
            else:
                print "Moving averages table not found!"

	    (s3, s2, s1, r1, r2, r3) = 6*[0]
	    pivot_table = soup.find("table", {"id": "curr_table"})
	    if pivot_table:
                classic_row = pivot_table.findAll("tr")[1]
		tds = classic_row.findAll("td")
		if len(tds) == 8:
		    (s3, s2, s1, r1, r2, r3) = (
					tds[1].text.strip(),
					tds[2].text.strip(),
					tds[3].text.strip(),
					tds[5].text.strip(),
					tds[6].text.strip(),
					tds[7].text.strip(),
					)
		    (s3, s2, s1, r1, r2, r3) = map(float, (s3, s2, s1, r1, r2, r3))


            # Got all TA and MA data
            X = [                
                    rsi_14_act,
                    stoch_9_6_act,	
                    stochrsi_14_act,
                    macd_12_26_act,
                    adx_14_act,		
                    williams_act,
                    cci_14_act,
                    #atr_14_act,
                    highs_lows_14_act,
                    ultimate_oscillator_act,
                    roc_act,
                    bb_power_act,
                    ma5, 
                    ma10,
                    ma20,
                    ma50, 
                    ma100, 
                    ma200
            ]

            InstrumentTAHistory.objects.create(                
                    instrument = instrument,
                    rsi_14_val = rsi_14_val,
                    rsi_14_act = rsi_14_act,
                    stoch_9_6_val = stoch_9_6_val,
                    stoch_9_6_act = stoch_9_6_act,	
                    stochrsi_14_val = stochrsi_14_val,
                    stochrsi_14_act = stochrsi_14_act,
                    macd_12_26_val = macd_12_26_val,
                    macd_12_26_act = macd_12_26_act,
                    adx_14_val = adx_14_val,
                    adx_14_act = adx_14_act,		
                    williams_val =williams_val,
                    williams_act = williams_act,
                    cci_14_val = cci_14_val,
                    cci_14_act = cci_14_act,
                    atr_14_val = atr_14_val,
                    atr_14_act = atr_14_act,
                    highs_lows_14_val = highs_lows_14_val,
                    highs_lows_14_act = highs_lows_14_act,
                    ultimate_oscillator_val = ultimate_oscillator_val,
                    ultimate_oscillator_act = ultimate_oscillator_act,
                    roc_val = roc_val,
                    roc_act = roc_act,
                    bb_power_val = bb_power_val,
                    bb_power_act = bb_power_act,
                    ma5 = ma5, 
                    ma10 = ma10,
                    ma20 = ma20,
                    ma50 = ma50, 
                    ma100 = ma100, 
                    ma200 = ma200,
		    s1 = s1,
		    s2 = s2,
		    s3 = s3,
		    r1 = r1,
		    r2 = r2,
		    r3 = r3,
                    price = last_price
            )
            #print X
	    if instrument.id in [5, 13,14,15]:
		X.append(-1 if last_price < s1 else 1 if last_price > r1 else 0)
		X.append(-1 if last_price < s2 else 1 if last_price > r2 else 0)
		X.append(-1 if last_price < s3 else 1 if last_price > r3 else 0)

	    price_history = PriceHistory.objects.filter(instrument=instrument, dttm__lte=datetime.now()).order_by('-dttm').values('price')[:60]
	    price_history = map(lambda p: p['price'], price_history)[::-1]
	    price_direction = 0
	    #print price_history
	    #price_history = [1 if p2 > p1 else -1 if p2 < p1 else 0 for p1, p2 in zip(price_history, price_history[1:])]
	    pos = 0
	    neg = 0
	    for pair in zip(price_history, price_history[1:]):
		d = pair[1] - pair[0]
		if d < 0:
		    neg += d
		else:
		    pos += d
	    if int(abs(pos) > abs(neg)):
		price_direction = 1
	    elif int(abs(pos) < abs(neg)):
		price_direction = -1

	    '''
	    positive = price_history.count(1)
	    negative = price_history.count(-1)
	    percent_pos = float(positive)/float(len(price_history))*100.
	    percent_neg = float(negative)/float(len(price_history))*100.
	    diff = abs(percent_pos - percent_neg)
	    if positive > negative and diff > 5.:
		price_direction = 1
	    elif negative > positive and diff > 5.:
		price_direction = -1
	    '''
	    #if price_history.count(1) > price_history.count(-1):
	    #			price_direction = 1
	    #elif price_history.count(-1) > price_history.count(1):
	    #	price_direction = -1
	    #if [p2>=p1 for p1, p2 in zip(price_history, price_history[1:])].count(True) >= 20:
	    #	price_direction = 1

	    print price_history, "Direction: ", price_direction
	    print "Support: ", [s1, s2, s3]
	    print "Support: ", map(lambda x: -1 if x else 0 , [last_price < s1, last_price < s2, last_price < s3])
	    print "Resistance: ", [r1, r2, r3]
	    print "Resistance: ", map(int, [last_price > r1, last_price > r2, last_price > r3])
	    X.append(price_direction)
	    #for p in price_history:
	    #	print p.dttm, p.price
	    print X
	    X2 = map(lambda x: 0.5 if x == -2 else x, X)
	    X2 = map(lambda x: -0.5 if x == 2 else x, X2)
	    X = map(lambda x: 0 if x in(2,-2) else x, X)
	    #X = map(lambda x: 0.5 if x == -2 else else x, X)
            result = last_price - instrument.open_price - instrument.spread if instrument.is_bullish() else  instrument.open_price - last_price - instrument.spread
            if instrument.is_closed():
        	result = 0
            print "Current price: ", last_price, " open price: ", instrument.open_price, " position: ", instrument.position, " direction:", instrument.direction, " result: ", result, " spread: ", instrument.spread
            income = result
            #print X
            #X = np.array(X).reshape((len(X), 1))
            
            #X = np.array(X, dtype=int)

            X = np.array(X).reshape((1, len(X)))
            #print X
            #print "^^^"
            #with open("/root/stocks-bot/models/%s.pkl" % instrument.symbol, 'rb') as fid:
            #    model = cPickle.load(fid)
            try:
                model = joblib.load("/root/stocks-bot/models/%s_jpd.pkl" % instrument.symbol)
            except:
        	continue
            result = int(model.predict(X)[0])
	    #X2 = X

	    print "X2:", X2
	    X2 = np.array(X2).reshape((1, len(X2)))
            result2 = model.predict(X2)
	    p2 = model.predict_proba(X2)
            probabilities2 = p2.tolist()[0]
            p_i2 = model.classes_.tolist().index(result2)
	    P2 = probabilities2[p_i2]
	    print "Result2:", result2, P2
            p = model.predict_proba(X)
            probabilities = p.tolist()[0]
            p_i = model.classes_.tolist().index(result)
            #i = model.classes_.index(result)
            #print "# OUTCOME:", instrument.symbol, result, " P: ", p[model.classes_.tolist()[0].index(result)],p, model.classes_
            P = probabilities[p_i]
            print "Coef:", model.coef_
            print "# OUTCOME:", instrument.symbol, result, " P: ", P, instrument.min_probability
            #if instrument.position != result:
            #    instrument.close(last_price)
            #    if result == PositionState.BUY:
            #        instrument.buy(last_price)
            #    elif result == PositionState.SELL:
            #        instrument.sell(last_price)

            income_coeff = 0.001
            #if instrument.direction != result:
	    #	print "IDIOT!!"
    	    #print instrument.direction == result
	    c1 = 3
	    c2 = 3
	    #print "WTF??", result, instrument.direction, type(result), type(instrument.direction)
            if int(instrument.direction) != result and P >= (instrument.min_probability or 55)/100.:
        	print "### Instrument direction changed from {0} to {1}: income:  {2} {3} probability: {4}".format(instrument.direction, result, income, instrument.symbol, P)
                if not instrument.is_closed():
            	    instrument.close(last_price)
                if result == PositionState.BUY:
                    instrument.buy(last_price, P)
                elif result == PositionState.SELL:
                    instrument.sell(last_price, P)
            elif 0 and income > 0 and income >= last_price*income_coeff*c1 and not instrument.is_closed():
    	    	print "### Fixing income!!!", income, last_price*income_coeff*c1, instrument.symbol
    	    	instrument.close(last_price)

            elif 0 and income < 0 and abs(income) > last_price*income_coeff*c2 and not instrument.is_closed():
    	    	print "### Stop loss!!!", income, last_price*income_coeff*c2, instrument.symbol
    	    	instrument.close(last_price)
    
            #elif ((instrument.is_bullish() and last_price - instrument.spread*3 >= instrument.open_price) or (instrument.is_bearish() and last_price + instrument.spread*3 <= instrument.open_price)) and not instrument.is_closed():
    	    #	print "### Fixing income!!!"
    	    #	instrument.close(last_price)
