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


## Interpretatie van de output-habitattypekartering

*Deze sectie is nog niet af en zal in de toekomst vast verplaatst worden, maar bij deze begin ik alvast aan wat uiteindelijk toch geschreven moet worden*

*Ook wellicht nuttig voor als we mensen veg2hab gaan laten gebruiken, een basic naslagwerk*

*TODO: Ik benoem in de uitleg hieronder enkele keren de "specifiekheid" van regels in de definitietabel. Ik weet niet of dit door een ecoloog begrepen wordt of dat hier toch een andere oplossing voor gevonden moet worden.* 

### Vlakbrede kolommen
**Area**: Oppervlakte van het gehele vlak in m2.

**Opm**: Opmerkingen bij dit vlak vanuit de bronkartering, als hier een opmerkingenkolom bij is opgegeven.

**Datum**: Datum vanuit de bronkartering, als hier een datumkolom bij is opgegeven.

**ElmID**: Een voor ieder vlak uniek ID. Deze kan vanuit de bronkartering komen, maar kan ook nieuw zijn gegenereerd. Dit gebeurt de als ElmID (of een ElmID equivalent zoals OBJECTID) in de bronkartering niet voor ieder vlak uniek is; als dit het geval is is hierover een warning gegeven.

**_Samnvttng**: Weergave van hoeveel procent van het vlak bedekt is met welk habitattype. Dit is een combinatie van alle kolommen `Habtype{i}` en `Perc{i}`.

**_LokVegTyp**: Het in de bronkartering opgegeven lokale vegetatietype, als er een lokaal vegetatietype kolom is opgegeven.

**_LokVrtNar**: Of de oorspronkelijk opgegeven lokale vegetatietypen in de bronkartering primair is vertaald naar SBB, VvN of beide. Als er naar SBB is vertaald, zijn er bijbehorende VvN uit de waswordtlijst gehaald. Als er naar VvN of naar beide is vertaald, is dit niet gedaan. 

### Complex-deel-specifieke kolommen
**Habtype{i}**: Habitattype van het complex-deel. HXXXX hier betekend dat er menselijk oordeel nodig is over dit complex-deel. 

**Perc{i}**: Percentage van het gehele vlak wat door dit complex-deel wordt bedekt.

**Opp{i}**: Oppervlakte van dit complex-deel in m2.

**Kwal{i}**: Kwaliteit van dit complex-deel. Dit kan zijn G (goed), M (matig) of X (nvt).

**Opm{i}**: Korte uitleg van hoe Veg2Hab tot het habitattype van dit complex-deel is gekomen.

**VvN{i}**/**SBB{i}**: De VvN/SBB-code die het gegeven habitattype onderbouwd, als deze er is. Dit is normaal gesproken het vegetatietype wat in de definitietabel tot het gegeven habitattype leidt. Als H0000 gegeven is, zullen alle in de definitietabel gevonden vegetatietypen weergegeven zijn. In het geval van HXXXX worden hier vegetatietypen vermeld van het meest specifieke niveau wat in de definitietabel is gevonden.

**_Status{i}**: Interne beslissings-status van Veg2Hab voor dit complex-deel. Wat de opgegeven status betekend is samengevat in `_Uitleg{i}`. Mogelijke statussen en hun uitleg zijn:
- `DUIDELIJK`: Als alle regels gevolgd worden is er 1 duidelijke optie; er is maar 1 habitatvoorstel met kloppende mits/mozaiek.
- `GEEN_KLOPPENDE_MITSEN`: Er is geen habitatvoorstel met kloppende mits/mozaiek. Er kan dus geen habitattype toegekend worden.
- `VEGTYPEN_NIET_IN_DEFTABEL`: De vegetatietypen van het vlak zijn niet in de definitietabel gevonden en leiden dus niet tot een habitattype.
- `GEEN_OPGEGEVEN_VEGTYPEN`: Er zijn in de vegetatiekartering geen (habitatwaardige)vegetatietypen opgegeven voor dit vlak. Er is dus geen habitattype toe te kennen.
- `MEERDERE_KLOPPENDE_MITSEN`: Er zijn meerdere habitatvoorstellen met kloppende mits/mozaiek. Er is geen duidelijke keuze te maken.
- `PLACEHOLDER`: Er zijn placeholder mitsen/mozaiekregels gevonden; deze kunnen (nog) niet door Veg2Hab worden gecontroleerd.
- `WACHTEN_OP_MOZAIEK`: Er is te weinig informatie over de habitattypen van omliggende vlakken (teveel HXXXX)

**_Uitleg{i}**: Uitleg van de status van dit complex-deel.

**_VgTypInf{i}**: De SBB en VvN typen van dit complex-deel uit de bronkartering. Als de bronkartering geen VvN had, zijn deze er via de waswordtlijst bijgezocht.

**_Mits_opm{i}**/**_Mozk_opm{i}**: Hier staat informatie over de mitsen/mozaiekregels die in definitietabelregels gevonden zijn. Wat hier staat hangt af van de status van het complex-deel:
- `DUIDELIJK`: Hier staat de mits/mozaiekregel weergegeven die tot het habitattype heeft geleid. Deze kloppen beide.
- `GEEN_KLOPPENDE_MITSEN`: Hier staan de mitsen/mozaiekregels van alle definitietabelregels die gevonden zijn in de definitietabel. Deze zijn in dit geval allemaal niet kloppend.
- `VEGTYPEN_NIET_IN_DEFTABEL`: Er zijn geen regels in de definitietabel gevonden voor de huidige vegetatietypen, dus er worden ook geen mitsen/mozaiekregels weergegeven.
- `GEEN_OPGEGEVEN_VEGTYPEN`: Er zijn geen vegetatietypen opgegeven voor dit vlak, dus er worden ook geen mitsen/mozaiekregels weergegeven.
- `MEERDERE_KLOPPENDE_MITSEN`: Hier staan alle kloppende mitsen/mozaiekregels van het meest specifieke niveau waar kloppende definitietabelregels voor gevonden zijn.
- `PLACEHOLDER`: Hier staan alle mitsen/mozaiekregels van definitietabelregels die maximaal even specifiek zijn als de meest specifieke placeholder mits.
- `WACHTEN_OP_MOZAIEK`: Hier staan alle mitsen/mozaiekregels van definitietabelregels die maximaal even specifiek zijn als de meest specifieke mozaiekregel.

In alle gevallen is achter elke mits weergegeven of deze klopt (`TRUE`), niet klopt (`FALSE`), of niet door Veg2Hab beoordeeld kan worden (`CANNOT_BE_AUTOMATED`). Een moziekregel kan ook nog uitgesteld zijn (`POSTPONE`); in dit geval is er te weinig informatie over de habitattypen van omliggende vlakken, omdat deze nog te veel HXXXX hebben om een mozaiekregeloordeel te kunnen vellen.

**_MozkPerc{i}**: Als dit complex-deel een mozaiekregel heeft, zijn hier de omringingspercentages van aangenzende habitattypen weergegeven. De getoonde percentages zijn diegene die gebruikt zijn om de mozaiekregel te beoordelen. Aangezien het mogelijk is dat een mozaiekregel beoordeeld kan worden voordat alle omliggende vlakken al een habitattype hebben gekregen (bijvoorbeeld als er al 50% van een verkeerd habitattype omheen ligt), kloppen deze soms niet met wat uiteindelijk om het vlak ligt (er kan meer HXXXX staan dan in de output kartering zo is).

**_VvNdftbl{i}**/**_SBBdftbl{i}**: Dit zijn de regels in de definitietabel waar de opgegeven mitsen/mozaiekregels te vinden zijn, opgesplitst in VvN en SBB regels.





