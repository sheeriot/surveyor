## Setup Surveyor

## Create django.env settings file
Create the ~surveyor/env/django.env file
* INFLUX_USER=influxadmin
* INFLUX_PASS=Y01rP@ssword
* INFLUX_HOST=your-host-name
* SQLITE_FILE=/opt/app/surveyor/db/db.sqlite3

### Setup settings.py
Settings in ~surveyor/webapp/surveyor/settings.py
* ALLOWED_HOSTS = ['host1name.domain.name','host2.domain2.nm']
