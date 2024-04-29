# veg2hab
Vegetatiekarteringen automatisch omzetten naar habitatkarteringen

## Installatie instructies

De applicatie staat nog niet op PyPi. Dus de installatie instructies zijn nog wat omslachtig (ze zullen redelijk omslachtig blijven, maar dat is niet anders):
 1. Bouw de Python package met `poetry build`. Deze bouwt de applicatie in de folder ./dist
 2. Open Arcgis en open 'New notebook'
 3. Zorg ervoor dat je een schone conda environment gebruikt (dit mag niet de default environment zijn, deze is readonly)
 4. Installeer veg2hab met `!pip install {path_to_veg2hab_wheel}`
 5. Gebruik `import veg2hab` en `veg2hab.installatie_instructies` om de locatie van de toolbox te vinden.
 6. Ga naar 'Add Toolbox (file)' in de command search en voeg de toolbox toe aan het project.
 7. Klik op 'draai veg2hab' om veg2hab te draaien.


## Inladen van vegetatiekarteringen

### .mdb naar .csv
Verschillende vegetatiekarteringen hebben informatie over de landelijke typologie in een MS Access database zitten.

Binnen het project zijn onderstaande stappen gevolgd om deze data in te lezen:
- Clone de volgende repo: https://github.com/pavlov99/mdb-export-all
- Gebruik het bash script om .mdb files om te zetten naar een map met csv bestanden
- De SBB-codes staan in Element.csv
