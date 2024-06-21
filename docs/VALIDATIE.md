# Validatie van veg2hab

De repository bevat functies en notebooks die gebruikt kunnen worden om te controleren en te kwantificeren in hoeverre een habitattypekaart die is gemaakt door veg2hab overeenkomt met een handmatige omzetting van een vegetatiekartering (bijvoorbeeld een T0 of een T1 kaart). De output van deze analyse is een confusion matrix die laat zien hoe vaak twee habitattypekaarten overeenkomen, en hoe vaak ze het niet eens zijn, en voor welke habitattypen.

De python functies die gebruikt worden om habitattypekarteringehiervoor staan [hier]('../veg2hab/validation.py').

Een notebook dat voor één kartering toont hoe de validatie werkt staat [hier](../notebooks/validate_single_kartering.ipynb). Dit notebook laat stap voor stap zien hoe twee habitattypekaarten met elkaar vergeleken kunnen worden.

### Aanvullende opmerkingen

- De validatiemodule kan twee verschillende confusion matrices berekenen:
  - Een die de habitattypekaarten vergelijkt in oppervlak (`validation.bereken_volledige_conf_matrix(..., method="area")`) 
  - Een die de habitattypekaarten vergelijkt in aantal shapes (`validation.bereken_volledige_conf_matrix(gdf_combined, method="percentage")`). In het geval van complexen geeft validatie fractionele vlakken terug.
- Validatie kan alleen tussen twee karteringen die exact dezelfde shapes bevat. Dit is vaak niet het geval. `validation.py` heeft functionaliteit om karteringen bij te snijden met elkaars grenzen. Hierbij kunnen vlakken met een zeer klein oppervlak ontstaan. We raden aan hierom altijd de vergelijking in oppervlak te gebruiken.