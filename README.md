scrapers-lametro
=====================

DataMade's source for municipal scrapers feeding [boardagendas.metro.net](https://boardagendas.metro.net).

## Development

### Making changes to this repository

Make your changes to the scraper code here.

Merge your PR to push to `main` and publish a `main` tag of the scraper image.

To publish a `production` tag of the scraper image, sync the `main` branch with the
`deploy` branch:

```bash
git push origin main:deploy
```

### Testing locally with councilmatic

In order to test what you have locally with your local dev instance of councilmatic, make two small temporary changes to councilmatic's docker-compose and Dockerfile.

For the **docker-compose**, comment out the remote image to start. Then have the scrapers build from the Dockerfile within this repo, while changing the context to be able to find this. The example below works if your scrapers repo lives in the same directory as your councilmatic repo:

```yml
# docker-compose.yml

scrapers:
    # image: ghcr.io/metro-records/scrapers-lametro:deploy
    build:
      dockerfile: Dockerfile
      context: ../scrapers-lametro
      ...
```

Now that the context has changed to be able to find this repo, add a line to the **Dockerfile** to copy its contents into the container:

```docker
# Dockerfile

COPY ./requirements.txt /app/requirements.txt

COPY ./scrapers-lametro /app/scrapers-lametro
# ^^^ new line

RUN pip install pip==24.0 && \
...
```

Run `docker-compose build app` to rebuild the councilmatic container with these scrapers. Now you'll be able to use your scraper commands on that container and have your local dev scrapers handle them!

### Scheduling

The LA Metro scrapers are scheduled via Airflow. The production Airflow instance
is located at [la-metro-dashboard.datamade.us](https://la-metro-dashboard.datamade.us/).
DataMade staff can find login credentials under the Metro support email in
LastPass. The underlying code is in the [`datamade/la-metro-dashboard` repository](https://github.com/datamade/la-metro-dashboard).
