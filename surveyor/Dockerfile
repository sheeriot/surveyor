FROM python:3.10.13-slim-bookworm

# create user to run the apps
RUN adduser --system --no-create-home django-actor

ENV PYTHONUNBUFFERED=1

RUN mkdir -p /opt/app

COPY requirements.txt /opt/app/

# update PIP and install requirements
RUN /usr/local/bin/python -m pip install --upgrade pip
RUN pip install -r /opt/app/requirements.txt

# create docker mount-points

# docker volume for DB persist
RUN mkdir -p /opt/app/db
# file system bind for app code access from host - this is a cheat
RUN mkdir -p /opt/app/surveyor/
# static_root for django to share with nginx
RUN mkdir -p /opt/app/static_files/

# for Mat Plot Lib (no home directory)
RUN mkdir -p /tmp/graph
RUN chown django-actor /tmp/graph
ENV MPLCONFIGDIR=/tmp/graph

# files copied in docker-entrypoint.sh
COPY docker-entrypoint.sh docker-entrypoint-worker.sh /opt/app/
RUN chmod +x /opt/app/docker-entrypoint.sh
RUN chmod +x /opt/app/docker-entrypoint-worker.sh

# copy the app code to a new surveyor directory in the image
COPY webapp /opt/app/surveyor/

RUN chown -R django-actor /opt/app

# home for the app
WORKDIR /opt/app/surveyor

# switch to non-root user
USER django-actor
