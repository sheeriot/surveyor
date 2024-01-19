# Create the first Django "SuperUser"

above

---

below

## Start the Docker Container: `surveyor`

Connect to the docker container shell

First, start Docker Surveyor Container.

```bash
docker compose up surveyor
```

Your terminal is now watching the logs from that container. You can use another terminal or add `-d` to your up command.

## Create the Django SuperUser

You will need to create the initial user. Start by connecting to the shell of the (now running) Surveyor container.

```bash
docker compose exec surveyor bash
```

Note that your surveyor container had better to be running if you want to connect to it with `exec`.

**Tip**: You can check the status of your docker containers with:

```bash
docker compose ps
```

Once connected to the docker container, use the django manage command to create the initial superuser.

```bash
./manage.py createsuperuser
```

You can leave the email address blank.

```bash
Username (leave blank to use 'django-actor'): loradmin
Email address:
Password:
Password (again):
Superuser created successfully.
```

You can now login to the web app and `/admin` pages.
