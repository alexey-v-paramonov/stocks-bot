# stocks-bot

This simple bot gets technical indicators for the main world indexes from Investing.com.

Also it has an ability to get calendar data with the main economic events.

Setup:

Create bot/settings_local.py with the database & smtp parameters:

```
DATABASES = {

    'default': {
        'ENGINE': 'django.db.backends.mysql', # or whatever you use
        'NAME': 'stocks_bot',
        'USER': 'stocks_bot',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}

EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.xxx.xx'
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = 587 # or 25
```

Run 
```
mysql -u<DB_USERNANE> -p<DB_PASS> -e "DROP DATABASE IF EXISTS stocks_bot"
mysql -u<DB_USERNANE> -p<DB_PASS> -e "CREATE DATABASE stocks_bot"
./manage.py syncdb --noinput
./manage.py loaddata instruments.json
```

The last command fills your database with the most common indexes such as S&P500.

Add cron jobs to fetch technical indicators and calendar data parsing
```
*/1 * * * * stocksb /home/stocksb/manage.py get_data 1>/dev/null 2>/dev/null
*/1 * * * * stocksb /home/stocksb/manage.py get_calendar 1>/dev/null 2>/dev/null
```

Bot simulates simple trading according to technical indicators.

Use 
```
./manage.py summary
```
to see all it's transactions.


