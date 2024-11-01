# scrapers-lametro

DataMade's source for municipal scrapers feeding [boardagendas.metro.net](https://boardagendas.metro.net).

For more on development, debugging, deployment, and more, [consult the documentation](https://metro-records.github.io/scrapers-lametro/)!

## Updating the documentation

To make changes to the documentation, [install Quarto](https://quarto.org/docs/get-started/).

Next, create a virtual environment, and install the documentation's Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r docs/requirements.txt
```

(Remember to activate your virtual environment with `source .venv/bin/activate` next time you want to work on the docs!)

Then, run the following in your terminal:

```bash
quarto preview docs
```

Make your changes to the `.qmd` files in the `docs/` directory. They will be automatically
reflected in your local version of the docs.

For more on authoring docs with Quarto, see [their Getting Started guide](https://quarto.org/docs/get-started/authoring/text-editor.html) and [documentation](https://quarto.org/docs/guide/).

The GitHub Pages site will rebuild automatically when your documentation changes are
merged into `main`.