# Surveyor Setup

## System Requirements
- Docker version ??
- Minimum RAM ??
- Expected ports ??

Note: These instructions are under continual revision.

Surveyor is typically deployed on a Linux VM using Docker and Docker Compose.
A front-end NGINX host is normally used to terminate SSL and proxy traffic
to the Django container.

------------------------------------------------------------

## Clone Repository

git clone https://github.com/sheeriot/surveyor.git
cd surveyor

------------------------------------------------------------

## Django Environment Configuration

Create the Django environment configuration.

cd env
cp django-sample.env django.env
vi django.env

The Django server allows two hostnames.

Set the allowed hosts in django.env.

Example:

surveyor.name.one
surveyor2.name.ns

These names must match the DNS names configured for the server.

SSL certificates and NGINX configuration are handled in the
companion repository:

webhost

------------------------------------------------------------

## Setup DNS CNAME Records for Two SSL Certificates

Create DNS records that point to the host running Surveyor.

Example:

surveyor.example.com
surveyor2.example.com

These should match the values configured in django.env.

------------------------------------------------------------

## Docker Compose for Service Management

Docker Compose is the recommended method for running Surveyor
containers on a single Linux VM.

Docker Compose requires two configuration steps.

------------------------------------------------------------

### Create the docker-compose environment file

cp compose.env-sample .env
vi .env

Set values such as:

COMPOSE_PROJECT_NAME
TCP_PORT

------------------------------------------------------------

### Create docker override symlink

ln -s docker-compose-prod.override.yml docker-compose.override.yml

This allows the correct environment configuration to be selected.

------------------------------------------------------------

## Start the Containers

docker-compose up

To run in the background:

docker-compose up -d

------------------------------------------------------------

## Docker Compose Operations

Start services

docker-compose up

Stop services

docker-compose down

View logs

docker-compose logs

Check container status

docker-compose ps

Restart services

docker-compose restart

------------------------------------------------------------

## After Startup

Access the web interface through the configured domain.

Admin console:

https://mysurveyor.domain.name/admin

------------------------------------------------------------

## Disclaimer – Web Access

By default the Surveyor web application is exposed behind the
NGINX web frontend.

Adjust firewall rules and access control as appropriate.

Take reasonable precautions to protect the server from internet abuse.

Use strong passwords and keep credentials private.

Operators are responsible for their deployment environment.
