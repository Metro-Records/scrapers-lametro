# scrapers-lametro

DataMade's source for municipal scrapers feeding [boardagendas.metro.net](https://boardagendas.metro.net).

For more on development, debugging, deployment, and more, [consult the documentation](https://metro-records.github.io/scrapers-lametro/)!

## Updating the documentation

To make changes to the documentation, [install Quarto](https://quarto.org/docs/get-started/).
Then, run the following in your terminal:

```bash
quarto preview docs
```

Make your changes to the `.qmd` files in the `docs/` directory. They will be automatically
reflected in your local version of the docs.

For more on authoring docs with Quarto, see [their Getting Started guide](https://quarto.org/docs/get-started/authoring/text-editor.html) and [documentation](https://quarto.org/docs/guide/).

The GitHub Pages site will rebuild automatically when your documentation changes are
merged into `main`.