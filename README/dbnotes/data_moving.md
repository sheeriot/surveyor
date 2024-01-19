# DB Hacks

## Django Dump some Models

```bash
# one model in the auth app
./manage.py dumpdata auth.user --format=yaml > xfer/out/users.yaml
# all models in the device app (endnode, surveyor_org, influx_source, bucket_device)
./manage.py dumpdata device --format=yaml > xfer/out/devices.yaml
```

This dumps all the tables (models) in the **device** app.

### Dump one table at a time

Follow this sampel to backup your five surveyor database tables as YAML:

```bash
    1  ./manage.py dumpdata auth.user --format=yaml > xfer/out/users.yaml
    2  ./manage.py dumpdata device.org --format=yaml > xfer/out/device_orgs.yaml
    3  ./manage.py dumpdata device.influxsource --format=yaml > xfer/out/device_influxsourcess.yaml
    4  ./manage.py dumpdata device.endnode --format=yaml > xfer/out/device_endnodes.yaml
    5  ./manage.py dumpdata device.bucketdevice --format=yaml > xfer/out/device_bucketdevices.yaml
```

## Restore DB from Backup

Here is a quick tip to restore a backed up DB on the Docker volume. The Docker Compose stack should be down (obviously, we are moving databases around.)

```bash
# from host shell, become root user (with env)
$ sudo su -
# change to the docker volume location on host
> cd /var/lib/docker/volumes/surveyor1_local-db/_data
# dump the test DB
> rm db.sqlite3
# bring back the old DB
> cp db.sqlite3.20240116 db.sqlite3
# fix the permissions for the docker container
> chown systemd-network:nogroup db.sqlite3
> chmod 644 db.sqlite3
# leave root user
> exit
```bash

# These commands can dump the distinct Surveyor DB tables from the docker shell (exec bash).
# best to have pyyaml installed (added to requirements.txt)

./manage.py dumpdata auth.user --format=yaml > xfer/out/users.yaml
./manage.py dumpdata device --format=yaml > xfer/out/device.yaml

# some linux chown/chmod is needed to fix permissions between host OS and Docker OS (runs as django-actor)

# read in those files
./manage.py loaddata xfer/fixtures/prod/users

./manage.py loaddata xfer/fixtures/prod/devices
```

```bash
# in this example, the file was broken into tables for a refactor.

# try surveyororgs
./manage.py loaddata xfer/fixtures/prod/device_surveyororgs

# Now influxsources
./manage.py loaddata xfer/fixtures/prod/device_influxsources

# great, keep going, add the endnodes used by single device reports
./manage.py loaddata xfer/fixtures/prod/device_endnodes

# add any bucketdevices info (locations)
./manage.py loaddata xfer/fixtures/prod/device_bucketdevices
```

### Sample Connect and Import (loaddata)

```bash
host$ docker compose exec surveyor bash
container$ # prompt from docker container

# import endnodes
container$ ./manage.py loaddata xfer/fixtures/prod/device_endnodes
Installed 135 object(s) from 1 fixture(s)

# import bucketdevices (locations)
container> ./manage.py loaddata xfer/fixtures/prod/device_bucketdevices
Installed 3927 object(s) from 1 fixture(s)
```

Using `dumpdata` and `loaddata`is a great way to move data between deployments.
