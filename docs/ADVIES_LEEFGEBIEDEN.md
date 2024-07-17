# Van veg2hab naar veg2leef

Habitattypen vormen de basis voor leefgebieden van beschermde diersoorten in de Vogel- en Habitatrichtlijn (VHR-soorten). Deze leefgebieden kunnen echter groter zijn; vegetatietypen die niet kwalificeren voor een habitattype, kunnen wel onderdeel zijn van het leefgebied van een VHR-soort. Deze aanvullende gebieden worden LG-typen genoemd.

Dit document beschrijft welke stappen in het bepalen van LG-typen overlap vertonen met veg2hab, welke modules hergebruikt kunnen worden, en welke stappen er nodig zijn om het vervaardigen van leefgebiedkaarten te automatiseren. In andere worden: hoe kan `veg2hab` uitgebreid worden naar `veg2leef`?


## Bronnen
We baseren ons voor het onderstaande op:
- Het *Methodendocument begrenzing en afbakening LG-typen M17, versie 21-09-2016*. Omdat het een conceptversie betreft, is dit document (nog) niet online beschikbaar.
- De *Toelichting Leefgebiedenkaart Dwingelderveld T0, versie 07-dec-2023 (N2K_LK_30_Dwingelderveld_T0_231207)*, opgemaakt door Prolander. Ook dit document is niet online beschikbaar.
- [Rapport Sovon Leefgebiedenkaarten N2000 en PAS](https://www.bij12.nl/wp-content/uploads/2023/11/Rapport-Sovon-2016-21-Leefgebiedenkaarten-N2000-PAS.pdf)


## Leefgebieden VHR-soorten en LG-typen
Habitattypen en LG-typen vormen samen de leefgebieden voor VHR-soorten. LG-typen vormen een aanvulling op habitattypen; een karteervlak(deel) heeft nooit tegelijkertijd een habitattype én een LG-type, deze sluiten elkaar uit.

Het Methodendocument begrenzing en afbakening LG-typen M17 (dit document is nog in concept, en niet officieel vastgesteld) definieert 14 LG-typen. Voor ieder LG-type beschrijft dit document:
- welke beschermde VHR-soorten er leven;
- op welk(e) habitattype(n) dit LG-type een aanvulling is;
- welke plantengemeenschappen (i.e. VvN-typen) er tot het type behoren;
- in welke FGR gebieden de plantengemeenschap moet liggen om tot het type te behoren. Deze voorwaarde geldt in feite als een beperkend criterium;
- aanvullende abiotische en ruimtelijke criteria. Deze criteria zijn met name relevant voor aquatische typen. Methodendocument: *"In het geval van terrestrische vegetaties zijn plantengemeenschappen [...] veelal wel als zuivere bron bruikbaar."*

N.B.: De plantengemeenschappen uit het Methodendocument zijn later aangevuld met extra vegetatietypen. Ook zijn er door Prolander voor het maken van leefgebiedenkaarten voor Dwingelderveld extra LG-typen aan toegevoegd (LG4010 en LG4030). Onduidelijk is of dit landelijk geldende typen zijn, of dat ze alleen op Dwingelderveld van toepassing zijn.


## Stappenplan automatiseren LG-typenkaart veg2leef
Veg2hab kan met kleine aanpassingen ook gebruikt worden voor het maken van LG-typekaarten:
- Voor het inlezen van vegetatiekarteringen kan `stap 1` uit veg2hab onveranderd gebruikt worden. Het methodendocument definieert LG-typen op basis van VvN-codes, stap 1 van veg2hab voorziet hierin.
  - De was-wordt-lijst die gebruikt wordt in veg2hab is direct bruikbaar voor veg2leef, omdat deze uitsluitend wordt gebruikt voor het vertalen tussen landelijke typologieën.
- `stap 2` uit veg2hab kan zonder aanpassingen gebruikt worden om vegetatiekarteringen samen te voegen voordat de LG-typen bepaald worden.
- Voor het omzetten van vegetatiekaarten naar LG-typenkaarten, kan met een klein aanpassing `stap 3` gebruikt worden:
  - Er moet een **definitietabel LG-typen** gemaakt worden, in dezelfde vorm als de definitietabel habitattypen: regels die omschrijven welke vegetatietypen leiden tot welk LG-type, aangevuld met criteria met betrekking tot Fysisch Geografische Regio's. Al deze informatie is beschikbaar in het Methodendocument;
  - In de code moet verwezen worden naar de *definitietabel LG-typen* in plaats van de *definitietabel habitattypen*. Handigst is als de gebruiker bij het aanroepen van stap 3 kan aangeven of er een habitattypekaart of LG-typenkaart gemaakt moet worden.
  - We doen hier de aanname dat complexe vegetatietypen op vergelijkbare manier als bij habitattypen omgezet worden naar complexe LG-typen. Als daarvoor in het geval van LG-typen andere regels gelden, zijn er meer aanpassingen nodig.
- Van mozaïekregels lijkt bij LG-typen geen sprake, dus `stap 4` kan worden overgeslagen.
- Het methodendocument noemt per LG-type een minimumareaal, maar zegt niet over functionele samenhang. In de huidige vorm is `stap 5` uit veg2hab daarom niet bruikbaar. 
  - Om stap 5 voor veg2leef bruikbaar te maken, kan het beste de module gekopieerd worden, de functionele samenhang eruit gehaald, en minimumoppervlaktes aangepast naar de drempelwaardes van LG-gebieden.


## Samenvoegen habitattypen en LG-typen tot leefgebiedenkaarten
Voor het maken van leefgebiedenkaarten kunnen per leefgebied de relevante habitattypen en LG-typen bij elkaar opgeteld worden. Dit kan handmatig gedaan worden, maar een extra omzetstap is ook een mogelijkheid, om automatisch alle leefgebiedkaarten in één keer te vervaardigen met een druk op de knop.

Mogelijk zijn er vegetatietypen die, wanneer ze niet door de beperkende criteria voor een habitattype komen, alsnog kunnen kwalificeren voor een LG-type. In dat geval kunnen deze aan de definitietabel LG-typen worden toegevoegd, en kan de LG-typenkaart na vervaardiging bijgeknipt worden met de habitattypenkaart, om te voorkomen dat een vlak(deel) tegelijkertijd als LG-type en habitattype wordt aangemerkt.
