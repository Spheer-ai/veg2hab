# veg2hab
**veg2hab** zet Nederlandse vegetatietypekarteringen automatisch om naar habitattypekarteringen.

Hiervoor gebruikt het de volgende bronbestanden. Deze bestanden worden automatisch mee geinstalleerd bij het installeren van veg2hab en zijn niet aanpasbaar.:
 - WasWordtLijst, dit bestand zet SBB vegetatietypes om naar VvN vegetatietypes
 - DefinitieTabel, dit is een samenvatting van de profieldocumenten.
 - FGR kaart, Fysisch-Geografische Regio's
 - Let op voor nieuwe versies: er komen nog meer bronbestanden bij!

## Installatie instructies

### Installatie binnen ArcGIS
De applicatie staat nu op PyPi. Installatie vanaf PyPi is veruit het eenvoudigst
 1. Open Arcgis en open 'New notebook'
 2. Zorg ervoor dat je een schone conda environment gebruikt (dit mag niet de default environment zijn, deze is readonly)
 3. Installeer veg2hab met `!pip install --upgrade veg2hab`
 4. Gebruik `import veg2hab` en `veg2hab.installatie_instructies()` om de locatie van de toolbox te vinden.
 5. Ga naar 'Add Toolbox (file)' in de command search en voeg de toolbox toe aan het project.
 6. Veg2hab komt met twee opties `digitale_standaard` en `vector_bestand`, afhankelijk van het formaat waarin de vegetatietype beschikbaar is. We willen iedereen aanraden de digitale standaard te gebruiken, wanneer dit mogelijk is.

### Installatie op linux
Op linux heeft veg2hab een extra dependency. Pyodb kan namelijk niet overweg met .mdb files op linux, dus gebruiken we hiervoor de `mdb-export` tool. Deze is te installeren met:
```sh
apt install mdbtools
```
voor meer informatie, zie: https://github.com/mdbtools/mdbtools


## Development
### Lokale ontwikkeling
Download de git repository:
```sh
git clone https://github.com/Spheer-ai/veg2hab
```

En installeer alle lokale (developmment) dependencies met:
```sh
poetry install
```

Linting doen we met isort en black:
```sh
poetry run black .
poetry run isort .
```

Unittests worden gedraaid met pytest:
```sh
poetry run pytest tests/
```

### Nieuwe release
1. Zorg ervoor dat de laatste bronbestanden in package_data staan met `poetry run release.py create_package_data`
2. Maak een nieuwe versie met poetry (minor, major, patch): `poetry version {{rule}}`
3. Pas de [__init__.py](veg2hab/__init__.py) __version__ variabele aan zodat deze overeen komt met de nieuw poetry version
4. Pas toolbox.pyt zodat de nieuwe version in SUPPORTED_VERSIONS staat. Heb je aanpassingen gedaan aan toolbox.pyt sinds de laatste release, zorg er dan voor dat de `SUPPORTED_VERSIONS = [{{new_version}}]` wordt gezet.
5. Draai `python release.py check-versions` om te checken dat je geen fouten hebt gemaakt.
6. Maak een nieuwe tag: `git tag v$(poetry version -s)`
7. Push de tag naar git `git push origin tag v$(poetry version -s)`
8. Github actions zal automatisch de nieuwe versie op PyPI zetten.
