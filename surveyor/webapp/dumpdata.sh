#!/bin/bash

# These commands can dump the distinct Surveyor DB tables from the docker shell (exec bash).
# best to have pyyaml installed (added to requirements.txt)

./manage.py dumpdata auth.user --format=yaml > xfer/out/users.yaml
./manage.py dumpdata device --format=yaml > xfer/out/devices.yaml

# some linux chown/chmod is needed to fix permissions between host OS and Docker OS (runs as django-actor)
