# coding=utf-8
import math
import requests
from django.utils import timezone
import cPickle
from sklearn.externals import joblib
from sklearn import svm

from datetime import datetime, timedelta
from sklearn.linear_model import LogisticRegression
import numpy as np
from django.db.models import Max, Min
#from treeinterpreter import treeinterpreter as ti
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
#from catboost import CatBoostClassifier
import collections

import operator

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
#hours = 2
#INTERVAL = 3600*hours
HOURS = {
    1: 1,
    2: 1,
    4: 1,
    5: 3,
    7: 1,
    8: 3,
    9: 3,
    10: 3,
    13: 1,
    14: 1,
    15: 1,
}
class Command(BaseCommand):

    def handle(self, *args, **options):
	if timezone.now().date().weekday() > 4:
	    print "Weekend!"
	    exit()
        for instrument in Instrument.objects.all():
	    #for instrument in Instrument.objects.exclude(pk=5):
	    #for instrument in Instrument.objects.filter(pk__in=(8,9,10,13,14,15)):
	    hours = HOURS[instrument.pk]
	    INTERVAL = 3600*hours

	    #if 0:
            print instrument.symbol, hours
            lastDttm = datetime.now() - timedelta(seconds = INTERVAL)
            firstDttm = datetime.now() - timedelta(days = 360)
            print firstDttm, lastDttm

            trainX = []
            trainY = []
            #pos = 0
            #neg = 0
	    price_history = 60*[0]
	    ta_samples = InstrumentTAHistory.objects.filter(
                instrument=instrument,
                dttm__gt=firstDttm,
                dttm__lt=lastDttm,
		#avg_price_later__isnull=True
                ).order_by('dttm')
	    number = 0
	    total = len(ta_samples)
            for ta_data in ta_samples:
		number +=1 
                x = [
                    ta_data.rsi_14_act,
                    ta_data.stoch_9_6_act,
                    ta_data.stochrsi_14_act,
                    ta_data.macd_12_26_act,
                    ta_data.adx_14_act,
                    ta_data.williams_act,
                    ta_data.cci_14_act,
                    #ta_data.atr_14_act,
                    ta_data.highs_lows_14_act,
                    ta_data.ultimate_oscillator_act,
                    ta_data.roc_act,
                    ta_data.bb_power_act,
                    ta_data.ma5,
                    ta_data.ma10,
                    ta_data.ma20,
                    ta_data.ma50,
                    ta_data.ma100,
                    ta_data.ma200,
                ]
		if instrument.id in [5,13,14,15]:
		    x.append(-1 if ta_data.price < ta_data.s1 else 1 if ta_data.price > ta_data.r1 else 0)
		    x.append(-1 if ta_data.price < ta_data.s2 else 1 if ta_data.price > ta_data.r2 else 0)
		    x.append(-1 if ta_data.price < ta_data.s3 else 1 if ta_data.price > ta_data.r3 else 0)

                #price = PriceHistory.objects.filter(instrument=instrument, dttm__lt=ta_data.dttm).order_by('-dttm').first()
		price = ta_data.price
		if not price:
		    continue
		#ta_data.price = price.price
		#ta_data.save()
		#continue
		price_history.pop(0)
		price_history.append(price)
		price_direction = 0
		ph = [1 if p2 > p1 else -1 if p2 < p1 else 0 for p1, p2 in zip(price_history, price_history[1:])]
		neg = 0.0
		pos = 0.0

		for pair in zip(price_history, price_history[1:]):
		    d = pair[1] - pair[0]
		    if d < 0:
			neg += d
    		    else:
			pos += d
		
		#print pos, neg, abs(pos-neg)
		if abs(pos) > abs(neg):
		    price_direction = 1
		elif abs(pos) < abs(neg):
		    price_direction = -1
		
		'''
		positive = ph.count(1)
		negative = ph.count(-1)
		percent_pos = float(positive)/float(len(price_history))*100.
		percent_neg = float(negative)/float(len(price_history))*100.
		diff = abs(percent_pos - percent_neg)
		#print percent_pos, percent_neg, ph
		if positive > negative and diff > 5.:
		    price_direction = 1
		elif negative > positive and diff > 5.:
		    price_direction = -1
		'''
		#if [p2>=p1 for p1, p2 in zip(price_history, price_history[1:])].count(True) >= 20:
		#    price_direction = 1
		#if price_direction == -1:
		#    print price_history, price_direction, price_history[0] < price_history[-1]
		#    #raise

                intervalEndDttm = ta_data.dttm + timedelta(seconds = INTERVAL)
		avg_price_after = ta_data.avg_price_later
		if not avg_price_after:
		    #if 1:
		    #continue
		    #print len(PriceHistory.objects.filter(instrument=instrument, dttm__gt=ta_data.dttm, dttm__lt=intervalEndDttm))
		    q = PriceHistory.objects.filter(instrument=instrument, dttm__gt=ta_data.dttm, dttm__lt=intervalEndDttm)
		    #q = PriceHistory.objects.filter(instrument=instrument, dttm__gt=ta_data.dttm)[:240].aggregate(Avg('price'))['price__avg']
		    if q.count() > 40*hours:
            		avg_price_after = q.aggregate(Avg('price'))['price__avg']
		    else:
			avg_price_after = None
		    #avg_price_after1 = PriceHistory.objects.filter(instrument=instrument, pk__gt=ta_data.pk, dttm__lt=intervalEndDttm).aggregate(Avg('price'))['price__avg']
		    #avg_price_after = PriceHistory.objects.filter(instrument=instrument, pk__gt=ta_data.pk)[:60].aggregate(Avg('price'))['price__avg']
		    ta_data.avg_price_later = avg_price_after
		    ta_data.price_direction = price_direction
		    #print PriceHistory.objects.filter(instrument=instrument, dttm__gt=ta_data.dttm, dttm__lt=intervalEndDttm).count(), avg_price_after
		    #print avg_price_after, avg_price_after1
		    #raise
		    ta_data.save()
		#elif ta_data.price_direction is None:
		#    #else:
		#    ta_data.price_direction = price_direction
		#    ta_data.save()
		#if 1:
		#    ta_data.price_direction = price_direction
		#    ta_data.save()

                #pmax = PriceHistory.objects.filter(instrument=instrument, dttm__gt=ta_data.dttm, dttm__lt=intervalEndDttm).aggregate(Max('price'))['price__max']
                #pmin = PriceHistory.objects.filter(instrument=instrument, dttm__gt=ta_data.dttm, dttm__lt=intervalEndDttm).aggregate(Min('price'))['price__min']
                #if pmax is None or pmin is None:
            	#    continue
                #mmax = pmax - price.price
                #mmin = price.price - pmin
                # print mmax, mmin
                # Based on min/max
                #y = -1 if mmin > mmax else 1
                # Based on average price
                #y = -1 if avg_price_after < price.price else 1
		# !!!!!!!!!!!!!!!!!
		if not avg_price_after:
		    continue

		y = -1 if avg_price_after < price else 1
		#if y == -1:
		#    neg += 1
		#else:
		#    pos += 1
		x.append(price_direction)
		x = map(lambda xx: 0 if xx in(2,-2) else xx, x)
                trainX.append(x)
                trainY.append(y)
		percent = float(number)/float(total)*100.
		#print percent,percent % 5 
		#if int(percent) % 5 == 0:
		if number % 1000 == 0:
		    print "{} {} of {} ({}%) processed".format(instrument.symbol, number, total, round(percent, 2))
		#print ta_data.dttm
	    #if pos > neg:
	    #	diff = pos - neg
	    #	while diff > 0:
	    #	    diff = diff -1
	    #print neg
	    #print pos
	    #raise
            print "Train samples: ", len(trainY)
            #return
            if (len(trainY)< 100):
                print "No train data for", instrument.symbol
                continue
            XX = np.array(trainX, dtype=int)
            YY = np.array(trainY, dtype=int)
            #model = LogisticRegression(tol=0.00000000001, n_jobs=-1, verbose=1, solver='newton-cg')
	    #model = LogisticRegression(tol= 1e-6, n_jobs=-1, verbose=1, max_iter=10000, class_weight='balanced')
	    # Test nasdaq
	    #if instrument.id == 7 or instrument.id == 5:
	    #	model = LogisticRegression(tol= 1e-6, n_jobs=-1, verbose=1, max_iter=10000, class_weight='balanced')
	    #else:
	    #	model = LogisticRegression(tol= 1e-6, n_jobs=-1, verbose=1, max_iter=10000)
	    model = LogisticRegression(tol= 1e-6, n_jobs=-1, verbose=1, max_iter=10000)

	    #‘lbfgs’, ‘liblinear’, ‘sag’, newton-cg
	    #model = LogisticRegression(class_weight='balanced')
	    #model = LogisticRegression()
	    #model = svm.SVC(kernel='linear', class_weight='balanced', probability=True)
	    #model = RandomForestRegressor()
            model = model.fit(XX, YY)
	    
	    
	    
            score = model.score(XX, YY)*100
            print "Score: ", score
            print "Coef:", model.coef_
            #print "SUM:", sum(model.coef_.tolist()[0])
            with open("/root/stocks-bot/models/%s_pd.pkl" % instrument.symbol, 'wb') as fid:
                cPickle.dump(model, fid)

            _ = joblib.dump(model, "/root/stocks-bot/models/%s_jpd.pkl" % instrument.symbol, compress=9)

	#for instrument in Instrument.objects.all().exclude(pk__in=(13,14,15)):
	#    for instrument in Instrument.objects.all():
	for instrument in Instrument.objects.exclude(pk=5):
	    #for instrument in Instrument.objects.filter(pk__in=(8,9,10,13,14,15)):
	    #if instrument.id == 10:
	    ##	instrument.min_probability = 58
	    #    instrument.save()
	    #	continue

	    #for instrument in Instrument.objects.filter(pk=2):
	    #try:
	    model = joblib.load("/root/stocks-bot/models/%s_jpd.pkl" % instrument.symbol)
	    #except:
	    #	continue
	    probabilities = (51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70)
	    H = collections.OrderedDict()
	    start_date = datetime.now() - timedelta(days=700)
	    print "###################################",  instrument.symbol
	    TA = InstrumentTAHistory.objects.filter(dttm__gte=start_date, instrument=instrument).order_by('dttm')
	    for p in probabilities:
		PPP = p/100.

    		direction = 0
		my_direction = 0
		price = 0
		total_income = 0
		prev_P = 0

    		print "###################################",  instrument.symbol, PPP
		
		total_trasactions = 0
		total_correct_trasactions = 0
    		for ta_sum in TA:

    		    X = [
            		ta_sum.rsi_14_act,
            		ta_sum.stoch_9_6_act,
            		ta_sum.stochrsi_14_act,
            		ta_sum.macd_12_26_act,
            		ta_sum.adx_14_act,
            		ta_sum.williams_act,
            		ta_sum.cci_14_act,
            		ta_sum.highs_lows_14_act,
            		ta_sum.ultimate_oscillator_act,
            		ta_sum.roc_act,
            		ta_sum.bb_power_act,
            		ta_sum.ma5,
            		ta_sum.ma10,
            		ta_sum.ma20,
            		ta_sum.ma50,
            		ta_sum.ma100,
            		ta_sum.ma200,
			#ta_sum.price_direction if ta_sum.price_direction is not None else 0
        	    ]
		    if instrument.id in [5, 13,14,15]:
			X.append(-1 if ta_sum.price < ta_sum.s1 else 1 if ta_sum.price > ta_sum.r1 else 0)
			X.append(-1 if ta_sum.price < ta_sum.s2 else 1 if ta_sum.price > ta_sum.r2 else 0)
			X.append(-1 if ta_sum.price < ta_sum.s3 else 1 if ta_sum.price > ta_sum.r3 else 0)

		    X.append(ta_sum.price_direction if ta_sum.price_direction is not None else 0)


		    ta_price = ta_sum.price

        	    X = np.array(X).reshape((1, len(X)))
        	    result = int(model.predict(X)[0])
        	    pr = model.predict_proba(X)
        	    probabilities = pr.tolist()[0]
        	    p_i = model.classes_.tolist().index(result)
        	    P = probabilities[p_i]
		    income =0

        	    if result != direction and ta_price:
        	
        		if direction != 0:
        		    if result == -1 and P >= PPP:
        			if my_direction != 0:
        			    income = ta_price - price - instrument.spread
        			    total_income += income
        			#print "# Sell! prev: ", price, " current: ",  ta_price, " income: ",  income, " total: ", total_income, P, ta_sum.dttm, " spread: ", instrument.spread
        			my_direction = direction = result
        			price = ta_price
        			prev_P = P
        			prev_Time = ta_sum.dttm
				total_trasactions += 1
				if income > 0:
				    total_correct_trasactions += 1
				#if total_trasactions > 0 and total_correct_trasactions > 0:
				#    print "Percent: ", float(total_correct_trasactions)/float(total_trasactions)*100.
        		    elif result == 1 and P > PPP:
        	    		if my_direction != 0:
        			    income = price - ta_price - instrument.spread
        			    total_income += income
        			#print "# Buy! prev: ", price, " current: ",  ta_price, " income: ", income, " total: ", total_income, P, ta_sum.dttm, " spread: ", instrument.spread
        			my_direction = direction = result
        			price = ta_price
        			prev_P = P
        			prev_Time = ta_sum.dttm
				if income > 0:
				    total_correct_trasactions += 1
				total_trasactions += 1
				#if total_trasactions > 0 and total_correct_trasactions > 0:
				#    print "Percent: ", float(total_correct_trasactions)/float(total_trasactions)*100.

            		else:
        		    price = ta_price
        		    direction = result
		#print ta_sum.price
		if my_direction != 0:
		    #print "Still open: ", my_direction, " open price: ", price, " last price: ", ta_sum.price
		    if my_direction == 1:
			total_income += ta_sum.price - price
		    if my_direction == -1:
			total_income += price - ta_sum.price
		print "Income:", total_income
		print "Transactions: ", total_trasactions
		if total_income > 0 and total_trasactions > 20:
		    H[PPP] = {
			'income': total_income,
		        'trasactions': total_trasactions,
			#'percent': float(total_correct_trasactions)/float(total_trasactions)*100.
		    }
		if total_trasactions < 15:
		    break
	    if len(H) > 0:
		for p, i in H.items():
		    print p,i
	    
		m = max(H.iteritems(), key=operator.itemgetter(1))[0]
		instrument.min_probability = int(round(m * 100, 2)) 
	        instrument.save()
	    print "MAX:", m, instrument.min_probability
