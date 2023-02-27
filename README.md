scrapers-lametro
=====================

DataMade's source for municipal scrapers feeding [boardagendas.metro.net](https://boardagendas.metro.net).

## Development

### Making changes to this repository

Make your changes to the scraper code here.

Merge your PR to push to `main` and publish a `staging` tag of the scraper image.

To publish a `production` tag of the scraper image, sync the `main` branch with the
`deploy` branch:

```bash
git push origin main:deploy
```

### Scheduling

The LA Metro scrapers are scheduled via Airflow. The production Airflow instance
is located at [la-metro-dashboard.datamade.us](https://la-metro-dashboard.datamade.us/).
DataMade staff can find login credentials under the Metro support email in
LastPass. The underlying code is in the [`datamade/la-metro-dashboard` repository](https://github.com/datamade/la-metro-dashboard).
