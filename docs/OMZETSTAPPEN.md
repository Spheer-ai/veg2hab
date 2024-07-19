# Omzetstappen veg2hab

Dit document geeft in detail uitleg over de omzetstappen in veg2hab, en zet uiteen welke keuzes er gemaakt zijn in het automatiseren van de omzetting.

De omzetstappen in veg2hab zijn zo nauw mogelijk gebaseerd op het [Methodiekdocument](https://www.bij12.nl/wp-content/uploads/2023/11/Methodiekdocument-Habitattypekartering.pdf). 

## Stap 1: Inlezen van vegetatiekarteringen

#### Gebruik van de was-wordt-lijst
De was-wordt-lijst wordt in veg2hab enkel gebruikt om landelijke typologieën in elkaar om te zetten. Voor het opzoeken welke vegetatietypen in aanmerking komen voor een habitattype, en aan welke voorwaarden dan voldaan moet worden, wordt uitsluitend de definitietabel gebruikt. Hiervoor zijn twee redenen: 
1. de was-wordt-lijst en definitietabel spreken elkaar op plekken tegen. Omdat de definitietabel een samenvatting is van de rechtsgeldige profieldocumenten, is besloten deze te gebruiken. 
2. In de was-wordt-lijst ontbreken details over beperkende criteria, die nodig zijn voor veg2hab.

#### Omzetting tussen landelijke vegetatie typologieën
In Nederlandse karteringen worden drie landelijk geldende vegetatie typologieën gebruikt: 
- de Staatsbosbeheer typologie (SBB)
- de Vegetatie van Nederland (VvN)
- de Revisie Vegetatie van Nederland (rVvN)

Voor geautomatiseerde omzetting in veg2hab speelden de volgende problemen op: 
- De typologieën zijn niet één-op-één (zelfs niet zuiver één-op-veel) in elkaar om te zetten;
- Sommige codes die in de één typologie bestaan, hebben geen code in een andere typologie;
- rVvN wordt gebruikt in karteringen, maar er bestaan geen profieldocumenten die omschrijven welke rVvN-codes bij een habitattype horen.
- In de meeste vegetatiekarteringen wordt de lokale typologie vertaald naar een SBB-code (de digitale standaard werkt ook primair met SBB). De definitietabel linkt echter primair VvN-codes aan habitattypen (SBB-codes worden hierin slechts genoemd als ze niet vertalen naar een VvN-code, of in sommige gevallen worden ze beide genoemd). Sommige SBB-codes vertalen naar meerdere VvN-codes, en zonder menselijke intuitie is niet te bepalen welke vertaling voor een vlak relevant is. 

Veg2hab zet typologieën als volgt in elkaar om:
- Karteringen die de rVvN typologie hanteren, worden omgezet naar SBB;
- Bij het inladen van een kartering met digitale standaard (stap `1a_digitale_standaard`), geeft de gebruiker aan of de digitale standaard rVvN of SBB gebruikt:
  1. In het geval van SBB, wordt aan iedere SBB-code een lijst met alle bijhorende VvN-codes uit de was-wordt-lijst toegevoegd.
  2. In het geval van rVvN, wordt deze eerst omgezet naar SBB, waarna aan iedere SBB-code een lijst met alle bijhorende VvN-codes uit de was-wordt-lijst wordt toegevoegd.
- Bij het inladen van een kartering zonder digitale standaard (stap `1b_vector_bestand`) kan de gebruiker aangeven of de kartering SBB, VvN of beide bevat:
  1. In het geval van SBB, wordt aan iedere SBB-code een lijst met alle bijhorende VvN-codes uit de was-wordt-lijst toegevoegd.
  2. In het geval van beide, wordt SBB niet automatisch vertaald naar VvN maar wordt de VvN-code uit de kartering gebruikt.
  3. In het geval van VvN, worden door veg2hab helemaal geen SBB-codes gebruikt.

Na consultatie met meerdere ecologen is de aanname gemaakt dat VvN-codes die voor een vlak niet relevant zijn, in stap 3 bij het controleren van de beperkende criteria vanzelf diskwalificeren.


## Stap 2: Samenvoegen van vegetatiekarteringen

Stap 2 laat de gebruiker meerdere karteringen samenvoegen tot één, om deze door de vervolgstappen van veg2hab te halen. Dit maakt het mogelijk om een habitattypekaart te maken op basis van meerdere vegetatiekaarten. 

- Alle vegetatiekarteringen die gebruikt worden in stap 2, moeten eerst met stap 1 worden ingeladen. Dit zorgt ervoor dat de karteringen hetzelfde format hanteren, en met elkaar gecombineerd kunnen worden.
- De gebruiker geeft bij het samenvoegen een volgorde van prioriteit aan. Deze prioriteit bepaalt welke kartering gebruikt wordt wanneer er sprake is van overlap tussen karteringen.
- Vlakken die door bijsnijden zijn veranderd in multipolygonen, worden omgezet naar meerdere polygonen.



## Stap 3: Opzoeken van mogelijke habitattypen, en het controleren van beperkende criteria

veg2hab gebruikt de definitietabel om te bepalen welke vegetatiecodes in aanmerking komen voor een habitattype, en welke beperkende criteria er gelden. 

#### Aanvullingen op de definitietabel
De definitietabel bevat tientallen regels voor het vegetatietype 'vegetatieloos'. Deze regels gelden voor vlakken met een SBB-code 50A, 50B of 50C, maar deze codes worden niet als vegetatiecode genoemd. Voor veg2hab zijn, in samenspraak met een ecoloog, deze codes toegevoegd aan de definitietabel voor de regels waar deze relevant werden geacht.

#### Opzoeken van mogelijke habitattypen
Veg2hab matcht de vegetatiecodes van een vlak(deel) als volgt met regels in de definitietabel:
- Zowel de SBB-code als alle VvN-codes van het vlak(deel) worden in de definitietabel opgezocht;
- De definitietabel wordt niet alleen doorzocht op het syntaxonomisch niveau van de vegetatiecode, maar ook op alle algemenere niveau's. De aanname hierbij is dat specifieke vegetatietypen ook op een algemener niveau in aanmerking kunnen komen voor een habitattype. Andersom geldt dit niet. In het geval van romp- of derivaatgemeenschappen wordt er enkel gekeken naar exacte matches.
  - Voorbeeld 1: subassociatie 32Aa01a staat niet in de definitietabel, maar kan gezien worden als specifiek voorbeeld van verbond 32Aa, dat wel in de definitietabel staat.
  - Voorbeeld 2: verbond 35Aa staat niet in de definitietabel (de klasse en orde ook niet), maar associatie 35Aa03 wel. Er kan echter niet van uitgegaan worden dat het verbond voldoet aan de specifieke eisen voor de associatie, dus in dit geval wordt er niets gevonden in de definitietabel en krijgt het vlak(deel) H0000 toegekend.
  - Voorbeeld 3: Rompgemeenschap 36Aa1-a staat niet in de definitietabel, maar de klasse 36Aa1 wel. Aangezien rompgemeenschappen en derivaatgemeenschappen exact moeten matchen, wordt er in dit geval niks gevonden in de definitietabel en krijgt het vlak H0000 toegekend.

Iedere match met de definitietabel wordt door veg2hab intern omgezet naar een `HabitatVoorstel`, met beperkende criteria en mozaïekregels die gecontroleerd moeten worden; stap 3 controleert voor ieder habitatvoorstel of er wordt voldaan aan de beperkende criteria en de mozaïekregels worden behandeld in stap 4. Omdat een vlak(deel) meerdere SBB- en VvN-codes kan hebben, kan het ook meerdere habitatvoorstellen hebben en daarmee potentieel kwalificeren voor meerdere habitattypen. In praktijk zal na het controleren van de beperkende criteria hiervan slechts één (of geen) overblijven.

#### Automatisch controleren van beperkende criteria
Veg2hab kan een aantal beperkende criteria (soms slechts deels) controleren op basis van landelijke bronkaarten. Wanneer deze kaarten van toepassing zijn, geeft veg2hab in de output van stap 3 aan welke informatie in de bronkaarten is gevonden. Voor veel vlakken geldt dat ze niet geheel binnen één vlak van een bronkaart vallen. In dat geval wordt gekeken met welk vlak van de bronkaart er het meest overlap is, en dit bronkaartvlak gekozen. Het percentage overlap wordt gemeld in de output.

**Bodemkaart** -
De bodemkaart wordt gebruikt om de volgende termen in beperkende criteria te controleren:
- *Leemarme humuspodzolgronden*; Dit mitsdeel wordt als TRUE beschouwd als het vlak in een van de volgende bodemtypen ligt, en als FALSE als dat niet zo is:
  - Hn21, Hn30, Hd21, Hd30, cHn21, cHn30, cHd21, cHd30
- *Lemige humuspodzolgronden*; Dit mitsdeel wordt als TRUE beschouwd als het vlak in een van de volgende bodemtypen ligt, en als FALSE als dat niet zo is:
  - Hn23, cHn23, Hd23, cHd23
- *Vaaggronden*; Dit mitsdeel wordt als TRUE beschouwd als het vlak in een van de volgende bodemtypen ligt, en als FALSE als dat niet zo is:
  - *Vaaggronden van kalkloze zandgronden*: Zn21, Zn23, Zn30, Zd21, Zd23, Zd30, Zb21, Zb23, Zb30
  - *Vaaggronden van kalkhoudende zandgronden*: Zn10A, Zn30A, Zn40A, Zn50A, Zn30Ab, Zn50Ab, Zd20A, Zd30A, Zd20Ab, Zb20A, Zb30A
  - *Vlakvaaggronden van kalkhoudende bijzondere lutumarme gronden*: Sn13A, Sn14A
  - *Niet-gerijpte minerale gronden van slikvaaggronden/gorsvaaggronden*: MOo02, MOo05, ROo02, ROo05, MOb12, MOb15, MOb72, MOb75, ROb12, ROb15, ROb72, ROb75
  - *Vaaggronden van zeekleigronden*: Mv51A, Mv81A, Mv61C, Mv41C, Mo10A, Mo20A, Mo80A, Mo50C, Mo80C, Mn12A, Mn15A, Mn22A, Mn25A, Mn35A, Mn45A, Mn56A, Mn82A, Mn86A, Mn15C, Mn25C, Mn52C, Mn56C, Mn82C, Mn86C, Mn85C, gMn15C, gMn25C, gMn52C, gMn53C, gMn58C, gMn82C, gMn83C, gMn88C, gMn85C, kMn63C, kMn68C, kMn43C, kMn48C
  - *Vaaggronden van rivierkleigronden*: Rv01A, Rv01C, Ro40A, Ro60A, Ro40C, Ro60C, Rn15A, Rn46A, Rn45A, Rn52A, Rn66A, Rn82A, Rn95A, Rn14C, Rn15C, Rn42C, Rn44C, bRn46C, Rn47C, Rn45C, Rn62C, Rn67C, Rn94C, Rn95C, Rd10A, Rd90A, Rd40A, Rd10C, Rd90C, Rd40C
  - *Vaaggronden van oude zeekleigronden*: KRn1, KRn2, KRn8, KRd1, KRd7
  - *Vaaggronden van leemgronden*: pLn5, pLn6, Ln5, Lnd5, Lnh5, Ln6, Lnd6, Lnh6, Lh5, Lh6, Ld5, Ldd5, Ldh5, Ld6, Ldd6, Ldh6
- *Leemarme vaaggronden*; Dit mitsdeel wordt als CANNOT_BE_AUTOMATED beschouwd als het vlak een van de volgende bodemtypen ligt, en als FALSE als het er niet in ligt:
  - Zn21, Zd21, Zb21, Zn30, Zd30, Zb30
- *Podzolgronden met een zanddek*; Dit mitsdeel wordt als TRUE beschouwd als het vlak in een van de volgende bodemtypen ligt, en als FALSE als dat niet zo is:
  - zY21, zhY21, zY21g, zY30, zhY30, zY30g
- *Moderpodzolgronden*; Dit mitsdeel wordt als TRUE beschouwd als het vlak in een van de volgende bodemtypen ligt, en als FALSE als dat niet zo is:
  - Y21, Y23, Y30, Y21b, Y23b, cY21, cY23, cY30
- *Oude kleigronden*; Dit mitsdeel wordt als TRUE beschouwd als het vlak in een van de volgende bodemtypen ligt, en als FALSE als dat niet zo is:
  - KT, KX
- *Leemgronden*; Dit mitsdeel wordt als TRUE beschouwd als het vlak in een van de volgende bodemtypen ligt, en als FALSE als dat niet zo is:
  - pLn5, pLn6, Ln5, Lnd5, Lnh5, Ln6, Lnd6, Lnh6, Lh5, Lh6, Ld5, Ldd5, Ldh5, Ld6, Ldd6, Ldh6

**Landelijke bodemkaart (LBK)** -
De LBK wordt gebruikt om de volgende termen in beperkende criteria te controleren:
- *Hoogveenlandschap*; Dit mitsdeel wordt als TRUE beschouwd als het vlak in een van de volgende LBK-typen ligt, en als CANNOT_BE_AUTOMATED als dat niet zo is:
  - HzHL, HzHD, HzHO, HzHK
- *Hoogveen*; Dit mitsdeel wordt als CANNOT_BE_AUTOMATED beschouwd als het vlak in een van de volgende LBK-typen ligt, en als FALSE als dat niet zo is:
  - HzHL, HzHD, HzHO, HzHK
- *Herstellend hoogveen*; Dit mitsdeel wordt als CANNOT_BE_AUTOMATED beschouwd als het vlak in een van de volgende LBK-typen ligt, en als FALSE als dat niet zo is:
  - HzHL, HzHD, HzHO, HzHK
- *Zandverstuiving*; Dit mitsdeel wordt als CANNOT_BE_AUTOMATED beschouwd als het vlak in een van de volgende LBK-typen ligt, en als FALSE als dat niet zo is:
  - HzSD, HzSDa, HzSF, HzSFa, HzSL, HzSLa, HzSX, HzSXa
- *Onder invloed van beek of rivier*; Dit mitsdeel wordt als TRUE beschouwd als het vlak in een van de volgende LBK-typen ligt, en als CANNOT_BE_AUTOMATED als dat niet zo is:
  - HzBB, HzBN, HzBV, HzBW, HzBL, HzBD, HlDB, HlDD


**Fysisch Geografische Regiokaart (FGR)** -
De FGR kaart wordt gebruikt om alle beperkende criteria te controleren die:
- expliciet verwijzen naar een FGR-gebiedstype, zoals `mits in FGR Duinen`;
- impliciet verwijzen naar een FGR-gebiedstype, als dit beschreven is in het methodiekdocument, zoals `mits in het kustgebied`.

**De Oude-Bossen kaart** -
Beperkende criteria met betrekking tot oude bossen, zoals `mits op een bosgroeiplaats ouder dan 1850 ...`, worden gecontroleerd met de Oude-Bossen kaart van Alterra. Deze bestaat uit vlakken van 500 bij 500 meter, die voor zowel H9120 en H9190 een code 0, 1 of 2 krijgen toegewezen.
- Een vegetatievlak met een oude-bossen-criterium dat buiten de 500m vlakken valt, komt niet door het criterium;
- Een vegetatievlak met een oude-bossen-criterium dat binnen een 500m hok valt, wordt gecontroleerd op de cijfercode bij het voor dat vlak relevante habitattype:
  - is de cijfercode 0, dan komt het vlak niet door het criterium;
  - is de cijfercode 1 of 2, dan krijgt het vlak de status `NIET_GEAUTOMATISEERD_CRITERIUM` en moet de gebruiker het handmatig beoordelen. Dit omdat niet alle grond binnen het 500m-vlak zeker voldoet aan het criterium. 

#### Handmatig controleren van beperkende criteria
Een aantal beperkende criteria is niet of slechts deels te automatiseren. Hiervoor zijn verschillende oorzaken:
- De benodigde informatie is niet landelijk beschikbaar, of veroudert te snel om er landelijke kaarten voor te maken (bijvoorbeeld acrotelm-kaarten);
- De benodigde informatie is niet structureel (of niet in een standaard vorm) opgenomen in de vegetatiekartering, bijvoorbeeld het voorkomen en bedekkingsgraad van bepaalde plantensoorten zoals `kraaihei afwezig` of `veenmosbedekking < 20%`.
- Een criterium is voor mensen zeer intuïtief, maar laat zich moeilijk vangen in harde regels, bijvoorbeeld `onder invloed van beek of rivier`. 
- Het controleren van een criterium vereist expertkennis, bijvoorbeeld `mits een acrotelm aanwezig is of een vergelijkbaar hoogveenvormend proces`.
- Een criterium kan wel automatisch gefalsificeerd, maar niet gevalideerd worden, of vice versa. Zie oude-bossen-criteria hierboven.

Alle criteria die niet automatisch gecontroleerd kunnen worden, worden door veg2hab in de output van stap 3 aangegeven met `NIET_GEAUTOMATISEERD_CRITERIUM`. De gebruiker dient deze criteria zelf na te lopen en een keuze te maken. Om dit te vergemakkelijken, geeft veg2hab de optie om bij het uitvoeren van stap 3 beperkende criteria te selecteren en aan te geven:
- dat een criterium voor een kartering *altijd* waar of niet-waar is.
- dat een criterium voor een deel van de een gebied waar is, en niet-waar op de overige plekken, of andersom. Hiervoor dient de gebruiker zelf een kaart aan te leveren. Van deze kaart gebruikt veg2hab uitsluitend de geopolygonen, waarvan wordt uitgegaan dat ze de gebieden representeren waar het criterium geldt / niet-geldt.

Tip: de gebruiker kan eerst stap 3 uitvoeren zonder handmatig criteria aan te geven. In de output kan de gebruiker vervolgens zien welke criteria niet automatisch gecontroleerd konden worden. Voor deze criteria kan de gebruiker vervolgens kaarten intekenen, en stap 3 nogmaals draaien.


## Stap 4: Mozaiekregels

Veg2hab gebruikt voor het controleren van mozaiekregels de volgende methode:
- Het neemt het vlak waarvoor de mozaiekregel gecontroleerd moet worden;
- Het blaast het vlak een heel klein beetje op (0.1 meter) en controleert met welke andere vlakken de omtrek overlapt. De kleine opblazing zorgt ervoor dat geometrische foutjes en afrondingen geen probleem vormen; 
- Het controleert of de omliggende vlakken het juiste habitattype/mozaiëkvegetatietype bevatten, en in welke hoeveelheid.

#### Normale mozaiekregels
Voor het controleren van de standaard mozaiekregels `alleen in mozaïek met (goede) zelfstandige vegetaties van H....` volgt veg2hab het methodiekdocument nauwgezet:
- De omtrek moet voor minimaal 95% in vlakken liggen die het benodigde habitattype bevatten; Dit heeft als consequentie dat vlakken die aan de rand van een kartering liggen (vrijwel) nooit door deze regel heen komen;
- Omliggende vlakken waarbij het benodigde habitattype minder dan 90% van het complex bedekken, worden hierbij niet meegeteld.

#### Aan de rand van
Voor het controleren van mozaiekregels `als rand langs zelfstandige vegetaties van H....`, gebruikt veg2hab dezelfde stappen als hierboven, maar met een minimum van 25% in plaats van 95%. Dit percentage is gekozen vanuit de gedachte dat een vierkant vlak met een mozaiekregel die met 1 zijde grenst aan een zelfstandige vegetatie nog nèt gezien kan worden als 'rand langs'. 

#### Mozaiekregels binnen en tussen complexe vlakken
Hier wijkt veg2hab sterk af van het methodiekdocument. Voor het beoordelen van de mozaiekregels binnen een complex vlak, dient de omzetter volgens het methodiekdocument onderscheid te maken tussen complexdelen die met elkaar in een 'fijnmazig patroon' bestaan of die elkaar 'omsluiten'. *"Er kan niet zonder meer van uitgegaan worden dat verschillende vegetaties die als complex in één vlak zijn gekarteerd een fijnmazig patroon vormen [...] in feite moet dit tijdens het karteren aangegeven worden en anders zo goed mogelijk gecontroleerd met de luchtfoto"*. Veg2hab heeft geen mogelijkheid om dit te beoordelen, en kijkt in het geval van een complexdeel met een mozaiekregel uitsluitend naar de omliggende vlakken in de kartering.


## Stap 5: Functionele samenhang en minimumoppervlak

Veg2hab bekijkt per habitattype welke vlakken met elkaar in functionele samenhang zijn, en controleert daarna voor deze samenhangende vlakken of ze voldoen aan de minimumoppervlakte. In het geval van een complex vlak, wordt alleen het percentage met het relevante habitattype meegeteld voor de minimumoppervlakte. 

Voor het bepalen van functionele samenhang, volgt veg2hab nauw de omschrijving van het methodiekdocument. Bij het controleren van afstand tussen vlakken, wordt hierbij de kortste afstand gemeten. In het geval van complexen, gaat veg2hab uit van een egale verdeling (i.e. er worden dus geen luchtfoto's geraadpleegd om de verdeling binnen het complex te bepalen).