### This is temporary documentation while wrapping up all #TODO's and #NOTE's in the codebase
This can and should be removed once everything is resolved

X = verwijderd/al gedaan/niet meer nodig
! = moet gebeuren
V = gebeurd
? = weet ik niet
- = laten staan


`test_arcgis_parameters.py`
- TODO dit kan netter. Moeten even kijken hoe dit makkelijker kan.
- voor Mark - veranderd

`test_editable_vegtypen.py`
V NOTE: Ideally this is a temporary test until the opmerkingen discrepancy (see xfail reason above) is fixed later on,
      then the original test (test_equivalency_habkart) should pass and this is no longer needed
- nog bekijken - opmerkingen/infos zijn veranderd

X TODO: Needs test that tests changing something in between step 1/3/4 will carry forward until end of step 5
      The tool_by_tool_walkthrough notebook shows it working in practice though
- Zit in test_tool_by_tool_walkthrough.py

`test_io_interface.py`
? TODO: order of tests matter here. It would be nice
if the different tests would run in different
processes, or something.
- voor Mark
- voor beide ticket maken voor mij

? NOTE: temporary fix
- voor Mark
- voor beide ticket maken voor mij

`test_vegetatietypen.py`
X NOTE: is dit een logische manier om score te geven? Match to self
      geeft 5 zodat de ranking met minder specifieke ssb niet de
      voorkeur krijgt.
- Lijkt uberhaubt niet meer te kloppen, dus weggehaald

`access_db.py`
? TODO fix circular imports
- voor Mark / is het niet stiekem gewoon goed zo?
- vegtypeinfo in vegetatietypen/eigen file

V TODO validate="one_to_one"? (x2)
- ben ik wel voor - gedaan (many to one)

`bronnen.py`
X TODO: Op het moment doen we bij sjoin predicate "within", zodat karteringvlakken die niet volledig
      binnen een bronvlak liggen NaN krijgen. Beter zou zijn dat ze alles krijgen waar ze op liggen, en als
      dat steeds dezelfde is, het karteringvlak alsnog dat type krijgt. Dit kan voorkomen bij LBK en bij
      de bodemkaart, omdat hier regelmatig vlakken met dezelfde typering toch naast elkaar liggen, omdat ze
      verschillen in zaken waar wij niet naar kijken. Het kan ook zijn dat 1 vlak in 2 bronvlakken ligt, en
      dat beide bronvlakken andere typeringen hebben die toch onder dezelfde categorie vallen.
- nu doen we biggest overlap

`criteria.py`
X NOTE: wanneer is het niet een beperkendcriterium? TODO Mark vragen
- vragen waarom dit zo is, kan daarna weg

! NOTE: Als dit niet meer in de opmerkingen kolom komt, moet dit dan nog opm heten?
- opmerkingen terminologie overhaulen

X NOTE: Mogelijk een GeoCriteria baseclass maken FGR/LBK/Bodem/OBK criteria?
- prio laag, wat mij betreft kannie weg

`definitietabel.py`
X TODO: Om deze isinstance heenwerken voor modulariteit
- Is nog van toen ik ooit relaties tussen files in kaart bracht - heeft dit waarde?

X TODO: Idealiter komt dit een een soort post_init (https://stackoverflow.com/questions/66571079/alter-field-after-instantiation-in-pydantic-basemodel-class)
- Ik zie niet zo goed hoe dit in een post init kan, want je hebt data uit de deftabel nodig

`enums.py`
X TODO: Deze definities even checken met Jakko
- doen - gedaan en gereviseerd

X NOTE: Ik heb dit weggehaald want ik ben NVT en ONBEKEND door mekaar wezen halen, en eigenlijk past NVT ook wel bij HXXXX
- enkel NVT is dikke prima

X TODO: Misschien een "enkel_bij_habtype" veld in te tuple om de 2 H9190 specifieke te forceren?
- Leuk idee maar niet nodig, mitsen weten niet voor welk habtype ze zijn, dus dat moet dan ook geregeld worden

`functionele_samenhang.py`
? NOTE: Ik wil eigenlijk niet dat deze functie in place is, maar ik kan geen goeie (deep)copy maken
      Wat er nu staat is vooral voor de vorm, de originele gdf wordt via de HabitatKeuzes alsnog aangepast
      pickle.loads(pickle.dumps(gdf)) zou mogelijk een optie zijn?
- even met Mark checken, maar zoals het nu is is niet echt erg denk ik
- Ik probeer wel pickle dingen

`habitat.py`
X TODO dit is niet zo netjes, met de json.loads en json.dumps
maar v.dict() werkte volgens mij niet lekker met enums. (2x)
- Dit hebben we stiekem gewoon geaccepteerd toch?

`main.py`
X TODO: ik ben niet zo blij met dit lijstje isinstance.
- Kan wel weg toch? Of miss een dict ofzo?

X TODO: Dit testen in ArcGIS, maar zou moeten werken (haha famous last words)
- getest, werkte! (bijna de eerste keer)

`mozaiek.py`
X NOTE: Mogelijk kunnen we in de toekomst van deze structuur af en met maar 1 type mozaiekregel werken
- geen- en nietgeimplementeerde-regels zijn wel nodig

X NOTE: wanneer is het niet een MozaiekRegel? TODO Mark vragen
- mark vragen, dan weg

- NOTE: Enkele van de volgende checks kunnen mogelijk geoptimaliseerd worden
      door ze te vervangen voor set operaties (set.issubset/set.intersection etc)
- Kan weg denk ik? We zijn tevreden genoeg volgensmij over de snelheid

X NOTE: Deze buffered_ prefix wordt ook in calc_mozaiek_percentages_from_overlay_gdf gebruikt
- is nog van toen mozaiekregelchecks anders werkten

`validation.py`
! TODO: If there are duplicates it now splits H1/H1/H2 into 50/50 we might want to split this into 66%,33%
- Ben er wel voor dit te veranderen

X TODO valideren dat alle habtypes anders zijn. (in ret_values denk ik)
- Het zijn keys in een dict, ze zijn altijd uniek

! TODO add some validation here!!
- Ik snap niet zo goed wat de voorgestelde validaties valideren
- doen (max 15 min)

`vegetatietypen.py`
X TODO: dit zou heel mooi naar een config kunnen later
- niet-geautomaitseerde codes zijn nu al in de config

`vegkartering.py`
? TODO: Naam van de kartering, voegen we later toe (x2)
- Willen we dit? Vragen aan jakko

X TODO: Doen we voor nu nog even niet
- LokVegTyp is al geregeld elders

X TODO clean this up!
- Wordt nu netter gedaan met states

X NOTE: evt iets van self.stage = lokaal/sbb/vvn ofzo? Enum? Misschien een dict met welke stappen gedaan zijn?
- States zijn er nu

X NOTE: Als dit te langzaam blijkt is een steekproef wss ook voldoende
- wwl matching duurt nooit echt lang dus is dikke prima zo

X NOTE NOTE: Als we zowel SBB en VvN uit de kartering hebben, willen we dan nog wwl doen voor de SBB zonder al meegegeven VvN?
- even dubbel checken met jakko - kan weg

X NOTE: Hier iets wat vast stelt dat er tenminste 1 VegTypeInfo met een VvN is, zo niet geef warning? (want dan is wwl wss niet gedaan)
- afgevangen met state checking

X NOTE: Moeten fgr/bodemkaart/lbk optional zijn?
- Nee :D

X TODO: zelfstandigheid/mozaiekvegetaties wordt nog niet goed afgehandeld.
- is nu wel geregeld

- TODO: Nu check ik hier heel handmatig of de keuze gemaakt is, en dat moet op dezelfde manier als in
      calc_nr_of_unresolved_habitatkeuzes_per_row() gedaan worden :/
      Na de demo moet dit even netten, een extra kolommetje in de gdf ofzo
      Voor nu zijn er belangrijker dingen te doen :)
- gereviseerd en laten staan

`waswordtlijst.py`
X NOTE: kunnen we ook alle rows met een NA gewoon verwijderen? Als we of geen VvN of
      geen SBB hebben dan kunnen we het toch niet gebruiken voor het omzetten
- opzich waar, maar niet zo veel reden om er mee te gaan lopen klooien

X NOTE: Dus we nemen de "Opmerking vertaling" kolom niet mee? Even checken nog.
- Doen we niet

`arcgis.py`
X TODO use shapefile_id as output
- Gebeurt nu toch? Checken met mark

- TODO: ik heb het idee dat dit niks doet, maar moet nog even checken.
- Voor mark

