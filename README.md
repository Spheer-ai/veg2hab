# veg2hab
Vegetatiekarteringen automatisch omzetten naar habitatkarteringen

## Installatie instructies

De applicatie staat nu op PyPi. Installatie vanaf PyPi is veruit het eenvoudigst
 1. Open Arcgis en open 'New notebook'
 2. Zorg ervoor dat je een schone conda environment gebruikt (dit mag niet de default environment zijn, deze is readonly)
 3. Installeer veg2hab met `!pip install --upgrade veg2hab`
 4. Gebruik `import veg2hab` en `veg2hab.installatie_instructies` om de locatie van de toolbox te vinden.
 5. Ga naar 'Add Toolbox (file)' in de command search en voeg de toolbox toe aan het project.
 6. Klik op 'draai veg2hab' om veg2hab te draaien.


### Inladen van vegetatiekarteringen op linux
Op linux heeft veg2hab een extra dependency. Pyodb kan namelijk niet overweg met .mdb files op linux, dus gebruiken we hiervoor de `mdb-export` tool. Deze is te installeren met:
```sh
apt install mdbtools
```
voor meer informatie, zie: https://github.com/mdbtools/mdbtools
