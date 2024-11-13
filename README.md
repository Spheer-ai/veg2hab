# veg2hab

- [veg2hab](#veg2hab)
  - [Introductie](#introductie)
    - [Disclaimer](#disclaimer)
  - [Installatie van veg2hab in ArcGIS Pro](#installatie-van-veg2hab-in-arcgis-pro)
    - [Installatie instructies voor admin-gebruikers](#installatie-instructies-voor-admin-gebruikers)
    - [Installatie instructies voor gebruik onder IT beheer](#installatie-instructies-voor-gebruik-onder-it-beheer)
      - [Installatiestappen voor de IT afdeling](#installatiestappen-voor-de-it-afdeling)
        - [Troubleshooting](#troubleshooting)
      - [Installatiestappen voor gebruiker](#installatiestappen-voor-gebruiker)
  - [Aanvullende installatie instructies](#aanvullende-installatie-instructies)
    - [Installatie .mdb drivers op Windows](#installatie-mdb-drivers-op-windows)
    - [Installatie veg2hab op linux](#installatie-veg2hab-op-linux)
  - [Gebruikershandleiding](#gebruikershandleiding)
    - [Gebruik in ArcGIS Pro](#gebruik-in-arcgis-pro)
      - [Sequentiële omzetstappen](#sequentiële-omzetstappen)
      - [Beperkende criteria handmatig instellen](#beperkende-criteria-handmatig-instellen)
      - [Overige handmatige correctie van de omzetting](#overige-handmatige-correctie-van-de-omzetting)
      - [Exporteren van habitattypekaart](#exporteren-van-habitattypekaart)
    - [Gebruik via de Command Line Interface (CLI)](#gebruik-via-de-command-line-interface-cli)
      - [Installatie](#installatie)
      - [Gebruik](#gebruik)
      - [Voorbeeld voor het draaien van stap1 - 5 in volgorde](#voorbeeld-voor-het-draaien-van-stap1---5-in-volgorde)
  - [Interpretatie van de output-habitattypekartering](#interpretatie-van-de-output-habitattypekartering)
    - [Algemene kolommen voor het hele vlak](#algemene-kolommen-voor-het-hele-vlak)
    - [Kolommen per deel van het complex](#kolommen-per-deel-van-het-complex)
  - [Bronbestanden die veg2hab gebruikt](#bronbestanden-die-veg2hab-gebruikt)
  - [Handleiding voor ontwikkelaars](#handleiding-voor-ontwikkelaars)
    - [Lokale ontwikkeling](#lokale-ontwikkeling)
    - [Nieuwe release](#nieuwe-release)

## Introductie

**veg2hab** zet Nederlandse vegetatietypekarteringen automatisch om naar habitattypekarteringen. De library kan op 2 manieren gebruikt worden:

- Als functionaliteit binnen andere (python) software;
- Vanuit ArcGIS Pro.

veg2hab wordt gedistribueerd via [PyPI](https://pypi.org/project/veg2hab/), waar alle toekomstige versies aan toe worden gevoegd.

### Disclaimer

Veg2hab is bedoeld als hulpmiddel om sneller vegetatiekarteringen om te zetten naar concept habitattypekaarten. Na de omzetting door veg2hab is over het algemeen nog handwerk van de gebruiker nodig, omdat sommige beperkende criteria niet te automatiseren zijn en expert judgment vereisen. Veg2hab geeft vlakken die het niet automatisch een habittatype (of `H0000`) kan toekennen de code `HXXXX`, en beschrijft in de output welke controles de gebruiker handmatig moet doen.

Het wordt gebruikers sterk aangeraden om:
- het rapport van een vegetatiekartering door te lezen, om te controleren of er zaken expliciet afwijken van de typologie vertalingen in de was-wordt lijst, de profieldocumenten of de omzetregels uit het methodiekdocument.
- De output van veg2hab steekproefsgewijs na te lopen, om te zien of de omzetting strookt met de verwachting en kennis over het gebied.
- Na het toepassen van de beperkende criteria het tussenproduct na te lopen en handmatig `HXXXX` om te zetten naar `H0000` of een habitattype, om pas daarna de mozaiekregels en functionele samenhang toe te passen.

## Installatie van veg2hab in ArcGIS Pro

Veg2hab is ontwikkeld voor en getest in ArcGIS Pro versie 3.0 en hoger. De installatie-instructies in deze sectie maken gebruik van installatie van veg2hab vanaf PyPI.

- Gebruikers die administator-rechten hebben, kunnen veg2hab zelf installeren via de stappen in [Installatie binnen ArcGIS Pro](#installatie-instructies-voor-admin-gebruikers).
- Gebruikers met een ArcGIS Pro omgeving die beheerd wordt door de organisatie, kunnen veg2hab niet zelf installeren. Volg in dit geval sectie [Installatie instructies voor IT beheer](#installatie-instructies-voor-gebruik-onder-it-beheer).


### Installatie instructies voor admin-gebruikers
 1. Open ArcGIS Pro.
 2. Maak een nieuwe python environment aan voor veg2hab (de default conda environment is read-only en niet geschikt om veg2hab in te installeren):
    - Open de 'Package Manager'.
        
        <img src="https://github.com/Spheer-ai/veg2hab/raw/master/images/package_manager.png" alt="package manager" width="400"/>
    - Klik op het tandwiel naast 'Active Environment'.
    - Maak een nieuwe environment aan op een locatie naar keuze. Gebruik als 'Source' de default Environment.
        
        <img src="https://github.com/Spheer-ai/veg2hab/raw/master/images/new_environment.png" alt="new python environment" width="400"/>
        <img src="https://github.com/Spheer-ai/veg2hab/raw/master/images/environment_location.png" alt="location of new environment" width="400"/>
    - Selecteer de environment en druk op 'OK'.
    - **Let op**: het aanmaken van een nieuwe environment kan langer dan 5 minuten duren. De status van het aanmaken kan bekeken worden onder `Tasks` rechtsonderin de Package Manager.
 3. Start ArcGIS Pro opnieuw op.
 4. Download en installeer veg2hab:
    - Klik op 'New notebook' en wacht tot deze is opgestart. Dit kan tot een minuut duren.
        
        <img src="https://github.com/Spheer-ai/veg2hab/raw/master/images/new_notebook.png" alt="new notebook" width="400"/>
    - Download veg2hab met het commando `!conda run pip install veg2hab`. Het uitvoeren van een commandoregel in het notebook kan gedaan worden met `Control`+`Enter` of door te klikken op de `Run` knop. Tijdens het uitvoeren staat er links naast de commandoregel `[*]`. Dit sterretje verandert in een getal wanneer het notebook klaar is. Het installeren van veg2hab kan enkele minuten duren. Wil je veg2hab upgraden naar de laatste versie, gebruik dan `!conda run pip install --upgrade veg2hab`.
        
        <img src="https://github.com/Spheer-ai/veg2hab/raw/master/images/notebook_prompts.png" alt="prompts in notebook to install veg2hab" width="400"/>
 5. Activeer veg2hab in het notebook met het commando `import veg2hab`.
 6. Installeer de veg2hab Python Toolbox:
    - Gebruik het commando `veg2hab.installatie_instructies()` om de locatie van de toolbox te vinden.
    - Ga naar 'Add Toolbox (file)' en voeg de toolbox toe vanaf deze locatie.
        
        <img src="https://github.com/Spheer-ai/veg2hab/raw/master/images/add_toolbox.png" alt="adding the veg2hab Python Toolbox" width="400"/>
    - **LET OP:** deze laatste stap ('Add Toolbox') moet eenmalig worden uitgevoerd bij het aanmaken van een nieuw project.
 7. Als het goed is, wordt de veg2hab toolbox nu getoond in de Geoprocessing tab. 
   
    <img src="https://github.com/Spheer-ai/veg2hab/raw/master/images/geoprocessing_tab.png" alt="geoprocessing tab" width="400"/> 
 8. Wanneer veg2hab geïmporteerd is en de toolbox is toegevoegd, kan deze instelling bewaard worden door het project op te slaan. Bij opnieuw openen van het project zal veg2hab direct beschikbaar zijn.


### Installatie instructies voor gebruik onder IT beheer

In organisaties waarin de gebruikers van veg2hab geen volledige local admin rechten hebben binnen ArcGIS Pro, moet een groot deel van de installatiestappen door IT- of applicatiebeheer doorgevoerd worden. 

#### Installatiestappen voor de IT afdeling
1. Zorg ervoor dat de IP adressen van de volgende websites niet door de firewall geblokkeerd worden:
   - repo.anaconda.com *(eenmalig nodig, voor het aanmaken van een nieuwe conda omgeving)*
   - conda.anaconda.org *(eenmalig nodig, voor het aanmaken van een nieuwe conda omgeving)*
   - files.pythonhosted.org *(nodig voor iedere update van veg2hab)*
   - pypi.org *(nodig voor iedere update van veg2hab)*
2. Doorloop stap 1 tot en met 4 uit de sectie [Installatie instructies voor admin-gebruikers](#installatie-instructies-voor-admin-gebruikers). Het is het veiligst om de conda environment niet meer te verplaatsen nadat deze is gecloned. Het liefst clone je deze naar de plek, waar deze ook voor de gebruikers komt te staan. 


##### Troubleshooting
- Voorheen werd aangeraden veg2hab te installeren met het commando `!pip install veg2hab`, dit kon soms voor problemen zorgen, wanneer er meer dan 1 Python installatie aanwezig was op het systeem. Dit zorgde er onder andere voor, dat na het installeren van veg2hab, bepaalde dependencies, zoals geopandas niet beschikbaar waren. Het installatie commando `!conda run pip install veg2hab` lijkt dit in veruit de meeste gevallen op te lossen.
- bij het clonen van de conda omgeving lijken er soms problemen met de gebruikersrechten te ontstaan, waarbij de folder andere rechten heeft dan de files binnen deze folders. Het kan dus zijn dat de rechten voor de bestanden nog goed gezet moeten worden (bijvoorbeeld met inheritance). De foutmelding die dit opleverde bij de gebruiker, was: `notebook not found at the requested URL`.
- De gebruiker rechten nodig om data te downloaden voor het gebruik van veg2hab. De eerste keer dat een gebruiker veg2hab gebruikt, zal deze enkele kaarten downloaden van `https://github.com/Spheer-ai/veg2hab/releases/download/...`. Deze worden vervolgens opgeslagen in `$HOME \ AppData \ Roaming \ veg2hab`.

#### Installatiestappen voor gebruiker
 1. Open ArcGIS Pro.
 2. Activeer de juiste conda omgeving **voordat** je een project opent.
    -  Open de 'Package Manager'.
        
        <img src="https://github.com/Spheer-ai/veg2hab/raw/master/images/package_manager.png" alt="package manager" width="400"/>
    - Kijk of de veg2hab environment in de lijst met environments staat, zonee, klik dan op de knop "add existing environment" rechts bovenin.
    - De locatie van de environment om in te laden, wordt door IT-beheer ingesteld. Vraag IT-beheer wanneer je deze niet kunt vinden.
    - Als de conda environment niet al geactiveerd is (te zien door het groene vinkje), activeer deze dan door op "Activate" te klikken
    - Open nu een ArcGIS project naar keuze.
 3. Voeg de veg2hab-toolbox toe aan het project. Dit is slechts 1 keer per project nodig.
    - Klik op 'New notebook' en wacht tot deze is opgestart. Dit kan tot een minuut duren.
        
        <img src="https://github.com/Spheer-ai/veg2hab/raw/master/images/new_notebook.png" alt="new notebook" width="400"/>
    - Activeer veg2hab in het notebook met het commando `import veg2hab`.
    - Gebruik het commando `veg2hab.installatie_instructies()` om de locatie van de toolbox te vinden.
    - Ga naar 'Add Toolbox (file)' en voeg de toolbox toe vanaf deze locatie.
      
      <img src="https://github.com/Spheer-ai/veg2hab/raw/master/images/add_toolbox.png" alt="adding the veg2hab Python Toolbox" width="400"/>


## Aanvullende installatie instructies
### Installatie .mdb drivers op Windows
Veg2hab heeft 64-bit drivers nodig voor het openen van Microsoft Access Database bestanden (.mdb). Meestal zijn deze drivers al geïnstalleerd. Dit kan gecontroleerd worden in de `ODBC Data Source Administrator`:

<img src="https://github.com/Spheer-ai/veg2hab/raw/master/images/odbc_drivers.png" alt="ODBC Drivers window" width="400"/>


Als er nog geen driver voor .mdb files is geïnstalleerd, kunnen de volgende stappen gevolgd worden (zie ook [deze video](https://www.youtube.com/watch?v=biSjA8ms_Wk)):

1. Open het ODBC Data Sources window voor 64 bit.
2. Klik op `Add...`
3. Selecteer `Microsoft Access Driver (*.mdb, *.accdb)` en klik op `Finish`.
4. Geef de source een naam naar keuze en klik op `OK`.

**Let op**: Wanneer de gebruiker Microsoft Access 32-bit heeft geïnstalleerd, zorgt het installeren van 64-bit drivers wellicht voor problemen. Er is sinds kort een versie van de digitale standaard beschikbaar voor Access 64-bit, zodat gebruikers van Microsoft Access 32-bit kunnen overstappen naar de 64-bit versie.


### Installatie veg2hab op linux
Op linux heeft veg2hab een extra dependency. Pyodbc kan namelijk niet overweg met .mdb files op linux, dus gebruiken we hiervoor de `mdb-export` tool. Deze is te installeren met:
```sh
sudo apt install unixodbc
```

 en daarna

```sh
sudo apt install mdbtools
```
Voor meer informatie, zie: https://github.com/mdbtools/mdbtools


## Gebruikershandleiding

### Gebruik in ArcGIS Pro

#### Sequentiële omzetstappen

De omzetting van vegetatiekarteringen naar habitattypekaarten gebeurt via de Python Toolbox `veg2hab.pyt`. De gehele omzetting verloopt via een aantal sequentiële stappen:

<img src="https://github.com/Spheer-ai/veg2hab/raw/master/images/toolbox_components.png" alt="new notebook" width="400"/>

In iedere stap dient de gebruiker in ieder geval twee dingen aan te geven:
- `Vegetatiekartering (geovectorbestand / shapefile)`: een vectorbestand (zoals een shapefile of geopackage). Dit is een bestandslocatie buiten ArcGIS Pro, óf een kaart die reeds ingeladen is in ArcGIS Pro. Voor stappen 2-5 dient dit een kaart uit een eerdere stap te zijn.
- `Output bestand`: De naam en locatie waar de output van de stap wordt opgeslagen. Als de gebruiker niets opgeeft, genereert veg2hab een unieke (maar weinig informatieve) naam. Het resultaat wordt automatisch toegevoegd als nieuwe laag in ArcGIS Pro.

Beschrijving van de omzetstappen en aanvullende inputvelden:
- `1a_digitale_standaard`: laadt een vegetatiekartering in die de landelijke digitale standaard gebruikt. De volgende inputvelden worden gevraagd:
  - `Kolomnaam van de ElementID`: de kolom die per vegetatievlak een unieke code bevat, die de link vormt met de access database.
  - `Bestandslocatie van de .mdb file`: het access database bestand (.mdb) dat hoort bij de kartering.
  - `Typologie van de kartering`: gebruikt de access database SBB of rVvN?
  - `Datum kolom (optioneel)`: de kolom in de kartering waar de datum in staat aangegeven.
  - `Opmerking kolom (optioneel)`: de kolom in de kartering waar opmerkingen in staan aangegeven.
- `1b_vector_bestand`: laadt een vegetatiekartering in die alle benodigde informatie in het vectorbestand (zoals een shape file of geopackage) zelf heeft staan. Deze bevat dezelfde inputvelden als `1a`, maar heeft daarnaast extra informatie nodig, omdat vectorbestanden geen standaard format hebben:
  - `single / multi`: zit informatie over complexen in één kolom of in meerdere kolommen?
  - `VvN / SBB`: gebruikt de kartering SBB, VvN of beide als landelijke typologie?
  - `SBB- / VvN-kolommen`: uit welke kolom moet veg2hab de vegetatiecodes halen?
  - `Percentage kolom (optioneel)`: in welke kolom(men) staat het percentage voor complexen?
  - `Lokale vegetatietypen kolom (optioneel)`: welke kolom(men) bevatten informatie over het lokale vegetatietype.
  - `Splits karakter`: Indien er complexinformatie in één enkele kolom staat, welke karakter moet veg2hab gebruiken om de complexdelen te splitsen?
- `2_optioneel_stapel_veg`: optionele stap voor het combineren van meerdere vegetatiekarteringen die samen tot één habitattypekaart moeten leiden.
  - `Vegetatiekarteringen`: Twee of meer vegetatiekarteringen; eerst geselecteerde karteringen overschrijven bij overlap later geselecteerde karteringen.
  - Deze karteringen *moeten* output van stap 1 zijn.
- `3_definitietabel_en_mitsen`: zoekt bij alle vlakken (of complexe vlakdelen) alle habitattypen die volgens de definitietabel (i.e. de profieldocumenten) op het vlak van toepassing kunnen zijn, en controleert de beperkende criteria die bij deze definitietabelregels horen.
  - Input *moet* output van stap 1 of 2 zijn.
- `4_mozaiekregels`: Controleert voor alle relevante vlakken de mozaiekregels.
  - Input *moet* output van stap 3 zijn.
- `5_functionele_samenhang_en_min_opp`: Controleert de functionele samenhang tussen vlakken of complexe vlakdelen, en past vervolgens de vereisten voor minimum oppervlakte toe.
  - Input *moet* output van stap 4 zijn.

**Let op:**
- Wanneer de gebruiker beschikt over een access database, raden wij aan `digitale_standaard` omzetting te gebruiken, ook als de shapefile alle informatie bevat. Hierbij is de kans op handmatige fouten kleiner.
- Velden die beginnen met `EDIT` kunnen door de gebruiker worden aangepast en hebben effect op de vervolgstappen van veg2hab. Velden die beginnen met `INTERN` zijn boekhoudvelden die veg2hab nodig heeft, en mogen niet door de gebruiker worden aangepast. Overige velden kunnen door de gebruiker veranderd worden, maar dit heeft geen effect op veg2hab.
- ArcGIS Pro (en veg2hab) kan niet goed omgaan met velden die beginnen met een getal of speciaal teken. Als inladen van een vegetatiekartering met stap 1 niet goed lukt, controleer dan of de gebruikte velden met een letter beginnen. Zo niet, pas dit dan aan. **let op:** dat de naam van de velden moet worden aangepast, niet alleen de alias. Dit kan bijvoorbeeld via de Alter Fields tool (Geoprocessing/Tools > Data Management Tools > Fields > Alter Field). Of voeg een nieuw veld toe en kopieer de data hiernaar.

    <img src="https://github.com/Spheer-ai/veg2hab/raw/master/images/alter_fields.PNG" alt="overwrite mitsen manually" width="400"/>
- Vegetatiekarteringen die omgezet worden met `vector_bestand` moeten beschikken over een landelijke typologie: SBB, VvN of rVvN.
- De eerste keer dat (een nieuwe versie van) veg2hab gebruikt wordt, worden er automatisch een aantal grote bestanden gedownload, waaronder de Landelijke Bodem Kaart (LBK). Deze download kan enkele minuten duren, afhankelijk van de internetverbinding.
- Wanneer veg2hab bezig is met een omzetting, dient de gebruiker het Map-venster in ArcGIS geopend te houden. Andere vensters openen kan resulteren in een fout van veg2hab, met de foutcode `ERROR - 'NoneType' object has no attribute 'addLayer'`.
- Tip: Wanneer de gebruiker wil achterhalen welke keuzes veg2hab voor een specifiek vlak heeft gemaakt, raden we aan de velden van dit vlak in het *Pop-up*-venster te bekijken. Dit venster bevat dezelfde informatie als de *Attribute table*, maar geeft de informatie overzichtelijker weer.

Een uitgebreidere uitleg met details over de omzetstappen, en onderbouwing van de hierin gemaakte keuzes, is te vinden in document [Omzetstappen](./docs/OMZETSTAPPEN.md) te vinden.

#### Beperkende criteria handmatig instellen

Veel beperkende criteria zijn door veg2hab niet automatisch te controleren, om verschillende redenen waar in [Omzetstappen](./docs/OMZETSTAPPEN.md#handmatig-controleren-van-beperkende-criteria) op wordt ingegaan. Deze criteria worden door veg2hab in de output van stap 3 aangegeven met `NIET_GEAUTOMATISEERD_CRITERIUM`.

Stap 3 geeft gebruikers de mogelijkheid om voor iedere mits-regel uit de definitietabel (sommige bestaan uit meerdere beperkende criteria) de controle door veg2hab te overschrijven, en handmatig een vaste waarde aan deze mits toe te kennen, zie de figuur hieronder. 
  
  <img src="https://github.com/Spheer-ai/veg2hab/raw/master/images/manual_mits_overwrite.png" alt="overwrite mitsen manually" width="400"/>

De gebruiker:
1. selecteert een mits uit een lijst met alle bestaande mitsen;
2. geeft een waarde aan die geldt voor deze mits: `WAAR`, `ONWAAR` of `ONDUIDELIJK`;
3. geeft aan of deze waarde geldt voor de gehele kartering (in dat geval levert de gebruiker geen geometrie aan), of dat het alleen voor vlakken binnen een aangeleverde geometrie geldt;
4. indien de gebruiker een geometrie aanlevert, kiest hij ook een waarde die geldt voor de vlakken buiten de geometrie: `WAAR`, `ONWAAR` of `ONDUIDELIJK`.

**LET OP:**
- De gebruiker kan meerdere mitsen overschrijven. Wanneer de eerste overschrijving is geconfigureerd verschijnt vanzelf een veld voor een eventuele tweede (derde, etc.) te overschrijven mits.
- Het weer verwijderen van overschrijvingen kan door het veld `Mits naam {i} (zie definitietabel)` aan te klikken en leeg te maken (bijvoorbeeld door op de `delete` knop te drukken). 

#### Overige handmatige correctie van de omzetting

Het opdelen van de omzetting in sequentiële stappen zorgt ervoor dat de gebruiker tussentijds aanpassingen kan aanbrengen in de bevindingen van veg2hab. veg2hab is zo gebouwd, dat het deze veranderingen opmerkt, en in de vervolgstappen meeneemt. Velden die beginnen met `EDIT_` mogen door de gebruiker na iedere stap van veg2hab aangepast worden. Wanneer andere velden worden aangepast, kan dit ervoor zorgen dat de vervolgstappen niet goed werken.

Voorbeelden:
- De vegetatiekartering hanteert een vertaling van SBB naar VvN die afwijkt van de waswordt lijst. In dit geval kan de gebruiker na het inladen van de kartering in stap 1 handmatig VvN codes in veld `VvN{i}` aanpassen. In de vervolgstappen gebruikt veg2hab de handmatige VvN-codes om op te zoeken in de definitie.
- veg2hab kan in stap 3 niet alle beperkende criteria succesvol controleren, waardoor veel vlakken op Hxxxx blijven staan. Dit zorgt ervoor dat ook veel vlakken met een mozaiekregel niet goed gecontroleerd kunnen worden in stap 4. De gebruiker kan handmatig vlakken omzetten van Hxxxx naar H0000 of een habitattype, en pas daarna verder gaan met stap 4.

#### Exporteren van habitattypekaart

Wanneer een vegetatietypekaart naar tevredenheid is omgezet, kan de habitattypekaart vanuit ArcGIS Pro worden geëxporteerd als File GeoDataBase (.gdb), het format dat vereist is voor de NDVH. De habitatkaart uit veg2hab kan toegevoegd worden aan een bestaande geodatabase, of de gebruiker kan hiervoor een nieuwe geodatabase aanmaken. Het aanmaken van een nieuwe File GeoDataBase kan op de volgende manier:
- Ga naar het Catalog venster.
- Ga naar Folders, en naar de gewenste locatie voor de nieuwe geodatabase.
- Rechtermuis klik op de folder, en selecteer New -> File GeoDataBase.
  
  <img src="https://github.com/Spheer-ai/veg2hab/raw/master/images/new_geodatabase.png" alt="open geoprocessing pane" width="400"/>

Om de habitattypekaart aan een geodatabase toe te voegen, volgt de gebruiker de volgende stappen:
- Ga naar het Geoprocessing venster. Deze wordt geopend door in de Analytics balk te klikken op Tools. 
  
  <img src="https://github.com/Spheer-ai/veg2hab/raw/master/images/export_tools.png" alt="open geoprocessing pane" width="400"/>
- Zoek naar de tool 'Feature Class to Geodatabase'.
  
  <img src="https://github.com/Spheer-ai/veg2hab/raw/master/images/export_geoprocessingpane.png" alt="feature class to geodatabase functie" width="400"/>
- Selecteer de kaartlaag die je wilt exporteren, en kies de locatie van de de File Geodatabase waar de kaartlaag in opgeslagen dient te worden. Druk op 'Run'.
  
  <img src="https://github.com/Spheer-ai/veg2hab/raw/master/images/export_to_gdb.png" alt="selecteer te exporteren kaartlaag" width="400"/>


### Gebruik via de Command Line Interface (CLI)

Veg2hab is ook beschikbaar als CLI (command line interface) tool. Dit kan handig zijn voor het automatiseren, maar het vergt enige kennis van terminals.

#### Installatie

Voor installatie kan veg2hab geinstalleerd worden vanuit [PYPI](https://pypi.org/project/veg2hab/). De beste manier om dit te doen is via `pipx`, maar uiteraard kan het ook gewoon via `pip` geinstalleerd worden.

```sh
pipx install veg2hab
```

#### Gebruik

Om te zien welke stappen gedraaid kunnen worden, zie:

```sh
veg2hab --help
```

Om te kunnen zien welke parameters allemaal worden verwacht door een stap:

```sh
veg2hab {{stap}} --help
# bijvoorbeeld voor stap 1a, draai:
veg2hab 1a_digitale_standaard --help
```

De stappen komen exact overeen met de stappen welke ook vanuit ArcGIS kunnen worden gedraaid. Zie de [Omzetstappen](./docs/OMZETSTAPPEN.md) om hier meer over te lezen.

Optionele argumenten welke meerdere waardes kunnen meekrijgen, zoals de `sbb_col` bij omzetstap `1b_vector_bestand` kunnen als volgt worden meegegeven:

```sh
 --sbb_col kolom1 --sbb_col kolom2
```

De `--overschrijf-criteria` wordt als volgt meegegeven. Wanneer men deze functie vanuit de CLI wil gebruiken, moet er na elke `--overschrijf-criteria` vier waardes worden meegegeven, in de volgende volgorderde:
 1. Naam van de mits, zoals deze voorkomt in de deftabel
 2. Nieuwe mits uitkomst: "WAAR", "ONWAAR", of "ONDUIDELIJK"
 3. Geometrie, waarbinnen deze mits van toepassing is. (Deze waarde is optioneel). Indien niet gegeven wordt deze mits.
 4. Mits uitkomst buiten de geometrie. Indien 3 wordt meegegeven, wordt deze waarde ook verwacht.

Waardes 3 en 4 zijn optioneel, dit wordt in de CLI opgelost, door een lege string mee te geven:
```sh
 --overschrijf-criteria "mits in vochtige duinvalleien" WAAR "path_to_shapefile.gpkg" ONWAAR
# of
 --overschrijf-criteria "mits in vochtige duinvalleien" WAAR "" ""
```

#### Voorbeeld voor het draaien van stap1 - 5 in volgorde

Dit voorbeeld draait stap 1-5 o.b.v. de digitale standaard. Stap 2 wordt overgeslagen omdat we geen kaarten samenvoegen, deze stap is optioneel.

```sh
veg2hab 1a_digitale_standaard data/notebook_data/Rottige_Meenthe_Brandemeer_2013/vlakken.shp ElmID data/notebook_data/Rottige_Meenthe_Brandemeer_2013/864_RottigeMeenthe2013.mdb --output output_stap1.gpkg

veg2hab 3_definitietabel_en_mitsen output_stap1.gpkg --output output_stap3.gpkg

veg2hab 4_mozaiekregels output_stap3.gpkg --output output_stap4.gpkg

veg2hab 5_functionele_samenhang_en_min_opp output_stap4.gpkg --output output_stap5.gpkg
```

## Interpretatie van de output-habitattypekartering

De habitattypekaarten die door veg2hab gemaakt worden, bevatten twee soorten attribute kolommen:
- Kolommen die vanuit het Gegevens Leverings Protol verplicht zijn.
- Kolommen die informatie bevatten over de omzetting naar habitattypen. Deze velden beginnen met een *underscore*-teken `_` (of `f_` in ArcGIS Pro) en zijn nuttig voor het controleren van een omzetting, of wanneer er nog een handmatige stap noodzakelijk is.

Verder zijn er een aantal kolommen die gelden voor het hele vlak, en kolommen die een deel van een complex beschrijven. Deze laatsten eindigen altijd op een cijfer, om het deel van het complex aan te geven. In geval van een niet-complex vlak, zijn alleen de kolommen `<kolomnaam>1` ingevuld.

### Algemene kolommen voor het hele vlak
**Area**: Oppervlakte van het vlak in m2.

**Opm**: Opmerkingen bij het vlak, overgenomen uit de bronkartering. Hiervoor moet de gebruiker expliciet een opmerkingenkolom selecteren bij het draaien van stap 1.

**Datum**: Datum waarop een vlak is ingetekend, overgenomen uit de bronkartering. Hiervoor moet de gebruiker expliciet een datumkolom selecteren bij het draaien van stap 1.

**ElmID**: Een uniek ID voor ieder vlak. De waardes worden overgenomen uit de bronkartering, tenzij deze niet voor ieder vlak uniek zijn; in dat geval wordt een warning gegeven en is er een nieuw uniek ID voor ieder vlak aangemaakt.

**f_Samnvttng**: Verkorte weergave met toegekende habitattypen en hun percentages in het complex. Dit is een combinatie van alle kolommen `Habtype{i}` en `Perc{i}`.

**f_LokVegTyp**: Het in de bronkartering opgegeven lokale vegetatietype, als er een lokaal vegetatietype kolom is opgegeven.

**f_LokVrtNar**: De landelijke typologie waar lokale vegetatietypen in de bronkartering naar zijn vertaald (SBB, VvN, SBB+VvN of rVvN).
- Indien SBB, zijn de bijbehorende VvN-typen door veg2hab uit de waswordtlijst gehaald.
- Indien rVvN, zijn de vegcodes met de waswordtlijst omgezet naar SBB en/of VvN.
- Indien VvN of SBB+VvN, is vertaling met de waswordtlijst overgeslagen.

**f_state**: De huidige status van de kartering. Deze veranderd afhankelijk van de uitgevoerde tool (1a/1b/2 = `POST_WWL`, 3 = `MITS_HABKEUZES`, 4 = `MOZAIEK_HABKEUZES`, 5 = `FUNC_SAMENHANG`). Deze is voornamelijk voor intern gebruik.


### Kolommen per deel van het complex
**Habtype{i}**: Habitattype dat door veg2hab is toegekend aan dit complex-deel. HXXXX betekent dat er nog geen eenduidig habitattype kan worden toegekend. Hiervoor is nog een vervolgstap in veg2hab of handmatige correctie nodig.

**Perc{i}**: Percentage van het vlak dat door dit complex-deel wordt bedekt.

**Opp{i}**: Oppervlakte van dit complex-deel in m2.

**Kwal{i}**: Kwaliteit van het habitattype van dit complex-deel. Dit kan zijn G (goed), M (matig) of X (nvt).

**VvN{i}**/**SBB{i}**: De VvN- en/of SBB-code die door de bronkartering aan het complex-deel zijn toegekend. Een waarde `Null` of `None` betekent dat in de bronkartering voor deze typologie geen vegcode is opgegeven, en dat de waswordtlijst ook geen vertaling bevat.

**_VvNdftbl{i}**/**_SBBdftbl{i}**: Deze kolommen bevatten een lijst met alle vegetatietypen (inlcusief Nederlandse naam) die voor dit vlak zijn teruggevonden in de definitietabel, welke regel van de definitietabel het betreft, en naar welk habitattype (inclusief Nederlandse naam) het vlak mogelijk vertaalt. Een waarde `None` in `_VvNdftbl` betekent dat de regel is gevonden op SBB-code, en vice-versa.


**f_Mits_info{i}**/**f_Mozk_info{i}**: Informatie over beperkende criteria en mozaiekregels van alle definitietabelregels die mogelijk op het vlak van toepassing zijn. Voor ieder beperkend criterium en mozaiekregel is weergegeven of deze klopt (`TRUE` / `T`), niet klopt (`FALSE` / `F`), of niet door veg2hab beoordeeld kan worden (`CANNOT_BE_AUTOMATED` / `C`). Een mozaiekregel kan ook nog uitgesteld zijn (`POSTPONE`); in dit geval is er te weinig informatie over de habitattypen van omliggende vlakken (i.e. teveel HXXXX), of stap 4 is nog niet uitgevoerd.

**f_V2H_bronnen_info{i}**: Informatie over bronkaarten zoals de Fysisch Geografische Regiokaart en Bodemkaart die veg2hab heeft gecheckt voor het controleren van beperkende criteria.

**f_MozkPerc{i}**: Als dit complex-deel een mozaiekregel heeft, zijn hier de omringingspercentages van aangenzende habitattypen weergegeven. De getoonde percentages zijn diegene die gebruikt zijn om de mozaiekregel te beoordelen. Aangezien het mogelijk is dat een mozaiekregel beoordeeld kan worden voordat alle omliggende vlakken al een habitattype hebben gekregen (bijvoorbeeld als er al 50% van een verkeerd habitattype omheen ligt), kloppen deze soms niet met wat uiteindelijk om het vlak ligt (er kan meer HXXXX staan dan in de output kartering zo is).

**f_Status{i}**/**f_Uitleg{i}**: Beslissings-status en uitleg van veg2hab voor dit complex-deel. Mogelijke statussen en hun uitleg zijn:
- `HABITATTYPE_TOEGEKEND`: veg2hab heeft één habitattype gevonden waaraan dit vlak voldoet.
- `VOLDOET_AAN_MEERDERE_HABTYPEN`: veg2hab heeft meerdere habitattypen gevonden waaraan dit vlak voldoet. De gebruiker moet hierin een keuze maken.
- `VOLDOET_NIET_AAN_HABTYPEVOORWAARDEN`: Het vlak voldoet niet aan de beperkende criteria en/of mozaiekregels voor de habitattypen die mogelijk van toepassing zijn. veg2hab kent aan dit vlak H0000 toe.
- `VEGTYPEN_NIET_IN_DEFTABEL`: De vegetatietypen van het vlak zijn op geen enkel syntaxonomisch niveau in de definitietabel gevonden en leiden dus niet tot een habitattype. veg2hab kent aan dit vlak H0000 toe.
- `GEEN_OPGEGEVEN_VEGTYPEN`: Er zijn in de vegetatiekartering geen vegetatietypen opgegeven voor dit vlak. veg2hab kent aan dit vlak H0000 toe.
- `NIET_GEAUTOMATISEERD_VEGTYPE`: Het vlak heeft een vegetatietype dat niet geautomatiseerd kan worden omgezet naar een habitattype. De gebruiker moet hier een handmatige controle uitvoeren.
- `NIET_GEAUTOMATISEERD_CRITERIUM`: Er zijn niet-geautomatiseerde mitsen/mozaiekregels gevonden; deze kunnen niet door veg2hab worden gecontroleerd. De gebruiker moet hier een handmatige controle uitvoeren.
- `WACHTEN_OP_MOZAIEK`: De mozaiekregels zijn nog niet toegepast, of er is te weinig informatie over de habitattypen van omliggende vlakken (teveel HXXXX).
- `MINIMUM_OPP_NIET_GEHAALD`: het vlak voldoet aan de voorwaarden voor een habitattype, maar haalt (in functionele samenhang) niet het minimum benodigde oppervlak.


## Bronbestanden die veg2hab gebruikt

Veg2hab is afhankelijk van verschillende bronbestanden tijdens het omzetten van vegetatiekarteringen. Deze bestanden worden automatisch mee geïnstalleerd met veg2hab en zijn niet aanpasbaar door de gebruiker:

 - [WasWordtLijst](./data/5.%20Was-wordt-lijst-vegetatietypen-en-habitattypen-09-02-2021.xlsx) (versie 09-feb-2021): dit bestand wordt uitsluitend gebruikt om landelijke vegetatietypologieën in elkaar om te zetten. Informatie over beperkende criteria en omzetting naar habitattype wordt genegeerd (want niet vastgesteld), en uitsluitende gehaald uit de:
 - [DefinitieTabel](./data/definitietabel%20habitattypen%20(versie%2024%20maart%202009)_0.xls) (versie 24 maart 2009): dit is een samenvatting van de profieldocumenten.
 - [Fysisch-Geografische Regio kaart (afgekort tot FGR)](./data/bronbestanden/FGR.json) (versie 2013, [link naar origineel op Nationaal georegister](https://nationaalgeoregister.nl/geonetwork/srv/dut/catalog.search#/metadata/c8b5668f-c354-42f3-aafc-d15ae54cf170)).
 - [Landschappelijke Bodem Kaart (afgekort tot LBK)](https://bodemdata.nl/downloads) (versie 2023): dit bestand wordt gebruikt voor het controleren van beperkende criteria met betrekking tot sommige bodemtypen en hoogveen.
 - [Bodemkaart van Nederland](https://www.atlasleefomgeving.nl/bodemkaart-van-nl-150000) (versie 2021): dit bestand wordt gebruikt voor het controleren van beperkende criteria met betrekking tot bodemtypen.
 - [Oude Bossenkaart](./data/bronbestanden/Oudebossen.gpkg): dit bestand wordt gebruikt voor het controleren van beperkende criteria met betrekking tot bosgroeiplaatsen ouder dan 1850.


De locatie van de bronbestanden op je eigen PC zijn te achterhalen door de volgende code uit te voeren binnen een notebook:
```python
import veg2hab
veg2hab.bronbestanden()
```
Vanuit deze locatie kunnen bronkaarten door de gebruiker worden ingeladen in ArcGIS. Zo kan de gebruiker inspecteren hoe veg2hab keuzes heeft gemaakt. De laatste versie van de bronbestanden zijn ook altijd te vinden in github [hier](https://github.com/Spheer-ai/veg2hab/tree/master/veg2hab/package_data) en [hier](https://github.com/Spheer-ai/veg2hab/tree/master/data/bronbestanden).


**Let op:**
- De LBK en Bodemkaart worden gedownload wanneer stap 3 voor het eerst gebruikt wordt; dit kan een aantal minuten duren. Als deze stap nog niet is gedraaid zijn deze kaarten nog niet te vinden op je eigen PC.
- Bij volgende versies van veg2hab komen er mogelijk meer bronbestanden bij.


## Handleiding voor ontwikkelaars
### Lokale ontwikkeling
Download de git repository:
```sh
git clone https://github.com/Spheer-ai/veg2hab
```

En installeer alle lokale (developmment) dependencies met:
```sh
poetry install
```

Installeer de drivers die je nodig hebt om veg2hab te draaien, zie de [aanvullende installatie instructies](#aanvullende-installatie-instructies).

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
1. Zorg ervoor dat de laatste bronbestanden in package_data staan met `poetry run python release.py create-package-data`
2. Maak een nieuwe versie met poetry (major, minor, patch): `poetry version {{rule}}`
3. Pas de [\_\_init\_\_.py](veg2hab/__init__.py) __version__ variabele aan zodat deze overeen komt met de nieuw poetry version.
4. Pas [veg2hab.pyt](veg2hab/package_data/veg2hab.pyt) zodat de nieuwe version in SUPPORTED_VERSIONS staat. Heb je aanpassingen gedaan aan veg2hab.pyt sinds de laatste release, zorg er dan voor dat de `SUPPORTED_VERSIONS = [{{new_version}}]` wordt gezet.
5. Draai `poetry run python release.py check-versions` om te checken dat je geen fouten hebt gemaakt.
6. Push nu eerst je nieuwe wijzigingen (mochten die er zijn), naar github: (`git add`, `git commit`, `git push`)
7. Maak een nieuwe tag: `git tag v$(poetry version -s)`
8. Push de tag naar git `git push origin tag v$(poetry version -s)`
9. Github actions zal automatisch de nieuwe versie op PyPI zetten.
