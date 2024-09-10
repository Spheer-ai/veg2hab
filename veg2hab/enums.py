from dataclasses import dataclass
from enum import Enum, IntEnum, auto
from typing import List, NamedTuple, Tuple, Union

from pydantic import BaseModel, Field


class BodemTuple(NamedTuple):
    string: str
    codes: List[str]
    enkel_negatieven: bool


class OBKWaarden(BaseModel):
    """
    H9120 en H9190 waarden van de Oude Bossenkaart
    0 = bos in dit vlak komt niet in aanmerking voor dit habitattype
    1/2 = bos in dit vlak komt mogelijk in aanmerking voor dit habitattype
    """

    H9120: int = Field(ge=0, le=2)
    H9190: int = Field(ge=0, le=2)


NumberType = Union[int, float]


@dataclass
class LBKTypeInfo:
    string: str
    codes: List[str]
    enkel_negatieven: bool
    enkel_positieven: bool

    def __post_init__(self):
        if self.enkel_negatieven and self.enkel_positieven:
            raise ValueError(
                "Een LBKTypeInfo kan niet enkel negatieven en enkel positieven zijn"
            )


class KarteringState(Enum):
    # Na from_access of from_shapefile
    PRE_WWL = "PRE_WWL"

    # Na toepassen waswordtlijst (na stap 1a/1b en na stap 2)
    POST_WWL = "POST_WWL"

    # Na het maken van HabitatVoorstellen met de definitietabel
    POST_DEFTABEL = "POST_DEFTABEL"

    # Na het maken van habkeuzes obv enkel mitsen (na stap 3)
    MITS_HABKEUZES = "MITS_HABKEUZES"

    # Na het maken van habkeuzes ook op basis can mozaiek (na stap 4)
    MOZAIEK_HABKEUZES = "MOZAIEK_HABKEUZES"

    # Na het checken van de minimum oppervlakte van habitattypen (na stap 5)
    FUNC_SAMENHANG = "FUNC_SAMENHANG"


class WelkeTypologie(Enum):
    SBB = "SBB"
    VvN = "VvN"
    SBB_en_VvN = "SBB en VvN"
    rVvN = "rVvN"


class FuncSamenhangID(NamedTuple):
    ElmID: int
    indices: Tuple[int, ...]


class MaybeBoolean(Enum):
    FALSE = 1

    # MAYBE = 2

    # Voor dingen die niet geautomatiseerd kunnen worden (bijv. NietGeautomatiseerdCriterium)
    CANNOT_BE_AUTOMATED = 3

    # Voor als evaluatie later nog eens geprobeerd moet worden (bijv. mozaiekregels waar nog
    # onvoldoende omliggende vlakken een habitattype hebben)
    POSTPONE = 4

    TRUE = 5

    def __invert__(self):
        if self == MaybeBoolean.TRUE:
            return MaybeBoolean.FALSE
        elif self == MaybeBoolean.FALSE:
            return MaybeBoolean.TRUE
        else:
            return self

    def __bool__(self):
        raise RuntimeError("Cannot convert MaybeBoolean to bool")

    def __and__(self, other):
        and_order = {
            MaybeBoolean.FALSE: 1,
            MaybeBoolean.POSTPONE: 2,
            MaybeBoolean.CANNOT_BE_AUTOMATED: 3,
            MaybeBoolean.TRUE: 4,
        }
        and_resolver = {v: k for k, v in and_order.items()}
        if not isinstance(other, MaybeBoolean):
            return NotImplemented
        return and_resolver[min(and_order[self], and_order[other])]

    def __or__(self, other):
        or_order = {
            MaybeBoolean.FALSE: 1,
            MaybeBoolean.CANNOT_BE_AUTOMATED: 2,
            MaybeBoolean.POSTPONE: 3,
            MaybeBoolean.TRUE: 4,
        }
        or_resolver = {v: k for k, v in or_order.items()}
        if not isinstance(other, MaybeBoolean):
            return NotImplemented
        return or_resolver[max(or_order[self], or_order[other])]

    def __str__(self):
        return self.name

    def as_letter(self):
        return {
            MaybeBoolean.FALSE: "F",
            MaybeBoolean.POSTPONE: "P",
            MaybeBoolean.CANNOT_BE_AUTOMATED: "C",
            MaybeBoolean.TRUE: "T",
        }[self]


class Kwaliteit(Enum):
    NVT = "Nvt"  # bijvoorbeeld in het geval van H0000 en HXXXX
    GOED = "Goed"
    MATIG = "Matig"

    @classmethod
    def from_letter(cls, letter: str) -> "Kwaliteit":
        if letter == "G":
            return cls.GOED
        elif letter == "M":
            return cls.MATIG
        elif letter == "X":
            return cls.NVT
        else:
            raise ValueError("Letter moet G, M of X zijn")

    def as_letter(self) -> str:
        if self == Kwaliteit.GOED:
            return "G"
        elif self == Kwaliteit.MATIG:
            return "M"
        elif self == Kwaliteit.NVT:
            return "X"
        else:
            raise ValueError("GoedMatig is niet Goed of Matig")


class MatchLevel(IntEnum):
    """
    Enum voor de match levels van VvN en SBB
    """

    NO_MATCH = 0
    KLASSE_VVN = 1
    KLASSE_SBB = 2
    ORDE_VVN = 3
    VERBOND_VVN = 4
    VERBOND_SBB = 5
    ASSOCIATIE_VVN = 6
    ASSOCIATIE_SBB = 7
    SUBASSOCIATIE_VVN = 8
    SUBASSOCIATIE_SBB = 9
    GEMEENSCHAP_VVN = 10
    GEMEENSCHAP_SBB = 11


class KeuzeStatus(Enum):
    # 1 Habitatvoorstel met kloppende mits
    HABITATTYPE_TOEGEKEND = auto()

    # Er is wel een keuze gemaakt, maar de minimum oppervlakte van het habitattype is niet gehaald
    MINIMUM_OPP_NIET_GEHAALD = auto()

    # Geen habitatvoorstel met kloppende mits
    VOLDOET_NIET_AAN_HABTYPEVOORWAARDEN = auto()

    # Vegtypen niet in deftabel gevonden
    VEGTYPEN_NIET_IN_DEFTABEL = auto()

    # Vlak heeft uit de kartering geen vegetatietypen
    GEEN_OPGEGEVEN_VEGTYPEN = auto()

    # Meerdere even specifieke habitatvoorstellen met kloppende mitsen
    VOLDOET_AAN_MEERDERE_HABTYPEN = auto()

    # Er zijn NietGeautomatiseerdCriteriums, dus handmatige controle
    NIET_GEAUTOMATISEERD_CRITERIUM = auto()

    # Er is een vegetatietype dat we niet kunnen omzetten
    NIET_GEAUTOMATISEERD_VEGTYPE = auto()

    # Er is meer dan threshold % HXXXX in de omliggende vlakken
    WACHTEN_OP_MOZAIEK = auto()

    # habitat type is handmatig toegewezen
    HANDMATIG_TOEGEKEND = auto()

    _toelichting = {
        "HABITATTYPE_TOEGEKEND": "veg2hab heeft één habitattype gevonden waaraan dit vlak voldoet.",
        "MINIMUM_OPP_NIET_GEHAALD": "Het vlak voldoet aan de voorwaarden voor een habitattype, maar haalt (in functionele samenhang) niet de minimum benodigde oppervlakte.",
        "VOLDOET_NIET_AAN_HABTYPEVOORWAARDEN": "Het vlak voldoet niet aan de beperkende criteria en/of mozaiekregels voor de habitattypen die mogelijk van toepassing zijn. veg2hab kent aan dit vlak H0000 toe.",
        "VEGTYPEN_NIET_IN_DEFTABEL": "De vegetatietypen van het vlak zijn op geen enkel syntaxonomisch niveau in de definitietabel gevonden en leiden dus niet tot een habitattype. veg2hab kent aan dit vlak H0000 toe.",
        "GEEN_OPGEGEVEN_VEGTYPEN": "Er zijn in de vegetatiekartering geen vegetatietypen opgegeven voor dit vlak. veg2hab kent aan dit vlak H0000 toe.",
        "VOLDOET_AAN_MEERDERE_HABTYPEN": "veg2hab heeft meerdere habitattypen gevonden waaraan dit vlak voldoet. De gebruiker moet hierin een keuze maken.",
        "NIET_GEAUTOMATISEERD_CRITERIUM": "Er zijn niet-geautomatiseerde mitsen/mozaiekregels gevonden; deze kunnen niet door veg2hab worden gecontroleerd. De gebruiker moet hier een handmatige controle uitvoeren.",
        "NIET_GEAUTOMATISEERD_VEGTYPE": "Het vlak heeft een vegetatietype dat niet geautomatiseerd kan worden omgezet naar een habitattype. De gebruiker moet hier een handmatige controle uitvoeren.",
        "WACHTEN_OP_MOZAIEK": "De mozaiekregels zijn nog niet toegepast, of er is te weinig informatie over de habitattypen van omliggende vlakken (teveel HXXXX).",
        "HANDMATIG_TOEGEKEND": "Het habitattype is handmatig aangepast in een van de tussentijdse resultaten.",
    }

    @property
    def toelichting(self):
        return self._toelichting.value[self.name]


class FGRType(Enum):
    """
    Typen uit de Fysisch Geografische Regio's kaart van Nederland (https://www.atlasnatuurlijkkapitaal.nl/fysisch-geografische-regios)
    """

    DU = "Duinen"
    GG = "Getijdengebied"
    HL = "Heuvelland"
    HZ = "Hogere Zandgronden"
    LV = "Laagveengebied"
    NI = "Niet indeelbaar"
    RI = "Rivierengebied"
    ZK = "Zeekleigebied"
    AZ = "Afgesloten Zeearmen"
    NZ = "Noordzee"


class BodemType(Enum):
    """
    Categorieen bodemtypen uit de Bodemkaart van Nederland (https://bodemdata.nl/basiskaarten)

    We hebben meerdere dingen op te slaan per bodemtype
        - __str__ string
        - De kwalificerende codes
        - Is dit type sluitend of is het enkel voor negatieven?
    """

    LEEMARME_HUMUSPODZOLGRONDEN = "Leemarme humuspodzolgronden"
    LEMIGE_HUMUSPODZOLGRONDEN = "Lemige humuspodzolgronden"
    VAAGGRONDEN = "Vaaggronden"
    LEEMARME_VAAGGRONDEN_H9190 = "Leemarme vaaggronden (H9190)"
    PODZOLGRONDEN_MET_EEN_ZANDDEK_H9190 = "Podzolgronden met een zanddek (H9190)"
    MODERPODZOLGRONDEN = "Moderpodzolgronden"
    OUDE_KLEIGRONDEN = "Oude kleigronden"
    LEEMGRONDEN = "Leemgronden"

    _tuple_dict = {
        "LEEMARME_HUMUSPODZOLGRONDEN": BodemTuple(
            string="Leemarme humuspodzolgronden",
            codes=[
                "Hn21",
                "Hn30",
                "Hd21",
                "Hd30",
                "cHn21",
                "cHn30",
                "cHd21",
                "cHd30",
            ],
            enkel_negatieven=False,
        ),
        "LEMIGE_HUMUSPODZOLGRONDEN": BodemTuple(
            string="Lemige humuspodzolgronden",
            codes=["Hn23", "cHn23", "Hd23", "cHd23"],
            enkel_negatieven=False,
        ),
        "VAAGGRONDEN": BodemTuple(
            string="Vaaggronden",
            codes=[
                # Kalkloze zandgronden -> Vaaggronden
                "Zn21",
                "Zn23",
                "Zn30",
                "Zd21",
                "Zd23",
                "Zd30",
                "Zb21",
                "Zb23",
                "Zb30",
                # Kalkhoudende zandgronden -> Vaaggronden
                "Zn10A",
                "Zn30A",
                "Zn40A",
                "Zn50A",
                "Zn30Ab",
                "Zn50Ab",
                "Zd20A",
                "Zd30A",
                "Zd20Ab",
                "Zb20A",
                "Zb30A",
                # Kalkhoudende bijzondere lutumarme gronden -> Vlakvaaggronden
                "Sn13A",
                "Sn14A",
                # Niet-gerijpte minerale gronden -> Slikvaaggronden/Gorsvaaggronden
                "MOo02",
                "MOo05",
                "ROo02",
                "ROo05",
                "MOb12",
                "MOb15",
                "MOb72",
                "MOb75",
                "ROb12",
                "ROb15",
                "ROb72",
                "ROb75",
                # Zeekleigronden -> Vaaggronden
                "Mv51A",
                "Mv81A",
                "Mv61C",
                "Mv41C",
                "Mo10A",
                "Mo20A",
                "Mo80A",
                "Mo50C",
                "Mo80C",
                "Mn12A",
                "Mn15A",
                "Mn22A",
                "Mn25A",
                "Mn35A",
                "Mn45A",
                "Mn56A",
                "Mn82A",
                "Mn86A",
                "Mn15C",
                "Mn25C",
                "Mn52C",
                "Mn56C",
                "Mn82C",
                "Mn86C",
                "Mn85C",
                "gMn15C",
                "gMn25C",
                "gMn52C",
                "gMn53C",
                "gMn58C",
                "gMn82C",
                "gMn83C",
                "gMn88C",
                "gMn85C",
                "kMn63C",
                "kMn68C",
                "kMn43C",
                "kMn48C",
                # Rivierkleigronden -> Vaaggronden
                "Rv01A",
                "Rv01C",
                "Ro40A",
                "Ro60A",
                "Ro40C",
                "Ro60C",
                "Rn15A",
                "Rn46A",
                "Rn45A",
                "Rn52A",
                "Rn66A",
                "Rn82A",
                "Rn95A",
                "Rn14C",
                "Rn15C",
                "Rn42C",
                "Rn44C",
                "bRn46C",
                "Rn47C",
                "Rn45C",
                "Rn62C",
                "Rn67C",
                "Rn94C",
                "Rn95C",
                "Rd10A",
                "Rd90A",
                "Rd40A",
                "Rd10C",
                "Rd90C",
                "Rd40C",
                # Oude zeekleigronden -> Vaaggronden
                "KRn1",
                "KRn2",
                "KRn8",
                "KRd1",
                "KRd7",
                # Leemgronden -> Vaaggronden
                "Ln5",
                "Lnd5",
                "Lnh5",
                "Ln6",
                "Lnd6",
                "Lnh6",
                "Lh5",
                "Lh6",
                "Ld5",
                "Ldd5",
                "Ldh5",
                "Ld6",
                "Ldd6",
                "Ldh6",
            ],
            enkel_negatieven=False,
        ),
        "LEEMARME_VAAGGRONDEN_H9190": BodemTuple(
            string="Leemarme vaaggronden",
            codes=["Zn21", "Zd21", "Zb21", "Zn30", "Zd30", "Zb30"],
            enkel_negatieven=True,
        ),
        "PODZOLGRONDEN_MET_EEN_ZANDDEK_H9190": BodemTuple(
            string="Podzolgronden met een zanddek",
            codes=["zY21", "zhY21", "zY21g", "zY30", "zhY30", "zY30g"],
            enkel_negatieven=False,
        ),
        "MODERPODZOLGRONDEN": BodemTuple(
            string="Moderpodzolgronden",
            codes=[
                "Y21",
                "Y23",
                "Y30",
                "Y21b",
                "Y23b",
                "cY21",
                "cY23",
                "cY30",
            ],
            enkel_negatieven=False,
        ),
        "OUDE_KLEIGRONDEN": BodemTuple(
            string="Oude kleigronden",
            codes=["KT", "KX"],
            enkel_negatieven=False,
        ),
        "LEEMGRONDEN": BodemTuple(
            string="Leemgronden",
            codes=[
                "pLn5",
                "pLn6",
                "Ln5",
                "Lnd5",
                "Lnh5",
                "Ln6",
                "Lnd6",
                "Lnh6",
                "Lh5",
                "Lh6",
                "Ld5",
                "Ldd5",
                "Ldh5",
                "Ld6",
                "Ldd6",
                "Ldh6",
            ],
            enkel_negatieven=False,
        ),
    }

    def __str__(self):
        return BodemType._tuple_dict.value[self.name].string

    @property
    def codes(self):
        return BodemType._tuple_dict.value[self.name].codes

    @property
    def enkel_negatieven(self):
        return BodemType._tuple_dict.value[self.name].enkel_negatieven


class LBKType(Enum):
    """
    Categorieen uit de Landschappelijke Bodemkaart (LBK) (https://bodemdata.nl/themakaarten)

    Per LBK type definieren we:
        - __str__ string
        - De kwalificerende codes
        - Is dit type sluitend of is het enkel voor negatieven?
    """

    HOOGVEENLANDSCHAP = "Hoogveenlandschap"
    HOOGVEEN = "Hoogveen"
    HERSTELLEND_HOOGVEEN = "Herstellend hoogveen"
    ZANDVERSTUIVING = "Zandverstuiving"
    ONDER_INVLOED_VAN_BEEK_OF_RIVIER = "Onder invloed van beek of rivier"

    _tuple_dict = {
        "HOOGVEENLANDSCHAP": LBKTypeInfo(
            string="Hoogveenlandschap",
            codes=["HzHL", "HzHD", "HzHO", "HzHK"],
            enkel_negatieven=False,
            enkel_positieven=True,
        ),
        "HOOGVEEN": LBKTypeInfo(
            string="Hoogveen",
            codes=["HzHL", "HzHD", "HzHO", "HzHK"],
            enkel_negatieven=True,
            enkel_positieven=False,
        ),
        "HERSTELLEND_HOOGVEEN": LBKTypeInfo(
            string="Herstellend hoogveen",
            codes=["HzHL", "HzHD", "HzHO", "HzHK"],
            enkel_negatieven=True,
            enkel_positieven=False,
        ),
        "ZANDVERSTUIVING": LBKTypeInfo(
            string="Zandverstuiving",
            codes=["HzSD", "HzSDa", "HzSF", "HzSFa", "HzSL", "HzSLa", "HzSX", "HzSXa"],
            enkel_negatieven=True,
            enkel_positieven=False,
        ),
        "ONDER_INVLOED_VAN_BEEK_OF_RIVIER": LBKTypeInfo(
            string="Onder invloed van beek of rivier",
            codes=["HzBB", "HzBN", "HzBV", "HzBW", "HzBL", "HzBD", "HlDB", "HlDD"],
            enkel_negatieven=False,
            enkel_positieven=True,
        ),
    }

    def __str__(self):
        return LBKType._tuple_dict.value[self.name].string

    @property
    def codes(self):
        return LBKType._tuple_dict.value[self.name].codes

    @property
    def enkel_negatieven(self):
        return LBKType._tuple_dict.value[self.name].enkel_negatieven

    @property
    def enkel_positieven(self):
        return LBKType._tuple_dict.value[self.name].enkel_positieven


STR_MITSEN = sorted(
    [
        "mits in de grofzandige delen van FGR Getijdengebied of FGR Noordzee, voorzover gelegen tussen de -20 meter-dieptelijn en de op Lowest Astronomical Tide gebaseerde laagwaterlijn, inclusief de tussenliggende diepere laagten en geulen",
        "mits in de grofzandige delen van FGR Getijdengebied of FGR Noordzee, voorzover gelegen tussen de op Lowest Astronomical Tide gebaseerde laagwaterlijn en de gemiddelde hoogwaterlijn",
        "mits in de slikkige en fijnzandige delen van FGR Getijdengebied of FGR Noordzee, voorzover gelegen tussen de -20 meter-dieptelijn en de op Lowest Astronomical Tide gebaseerde laagwaterlijn, inclusief de tussenliggende diepere laagten en geulen, en mits geen onderdeel van H1130 en H1160",
        "mits in de FGR Getijdengebied en mits gelegen in het verlengde van een rivier waarvan het water een sterke en continue invloed op het habitattype heeft, voorzover gelegen onder de gemiddelde hoogwaterlijn; potentieel",
        "mits in de slikkige en fijnzandige delen van FGR Getijdengebied of FGR Noordzee, voorzover gelegen tussen de op Lowest Astronomical Tide gebaseerde laagwaterlijn en de gemiddelde hoogwaterlijn, en mits geen onderdeel van H1130 en H1160",
        "mits in de FGR Getijdengebied en mits in een inham met gedempt getij en geen sterke invloed van rivierwater; potentieel",
        "mits in de FGR Getijdengebied en mits gelegen in het verlengde van een rivier waarvan het water een sterke en continue invloed op het habitattype heeft, voorzover gelegen onder de gemiddelde hoogwaterlijn",
        "mits in de FGR Getijdengebied en mits in een inham met gedempt getij en geen sterke invloed van rivierwater",
        "mits niet in fijnschalig mozaïek met goede zelfstandige vegetaties van H3130",
        "mits in vochtige duinvalleien",
        "mits niet in vochtige duinvalleien",
        "mits in vlakvormige wateren, of in lijnvormige wateren voorzover de begroeiing aansluit bij die van het aangrenzende vlakvormige water",
        "mits in beken of riviertjes en mits met waterranonkel- of sterrenkroossoorten",
        "mits in rivieren of nevengeulen",
        "mits in vlakvormige wateren, of in lijnvormige wateren voorzover de begroeiing aansluit bij die van het aangrenzende vlakvormige water, en minstens één van de volgende plantensoorten aanwezig is: doorgroeid fonteinkruid, gegolfd fonteinkruid, glanzig fonteinkruid of langstengelig fonteinkruid",
        "mits in beken of riviertjes en mits met waterrankel- of sterrenkroossoorten",
        "mits in beken of riviertjes",
        "mits niet in lijnvormige wateren",
        "mits niet in vochtige duinvalleien en niet in lijnvormige wateren",
        "mits in combinatie met andere vegetaties van H3130 en niet in lijnvormige wateren",
        "mits in vennen en in combinatie met andere vegetaties van H3160",
        "mits het Hoogveenmos-verbond aanwezig is, het onderdeel van een hoogveenlandschap is en een acrotelm aanwezig is",
        "mits in herstellend hoogveen",
        "mits niet in mozaïek met vegetaties van H3110 en mits geen onderdeel van H7120 en niet in lijnvormige wateren",
        "mits in vennen en niet in mozaïek met vegetaties van H3130",
        "mits in het open water van vochtige duinvalleien",
        "mits tussen hoge moerasplanten in vochtige duinvalleien",
        "mits op oevers van rivieren of nevengeulen",
        "mits geen onderdeel van H7110_A",
        "mits in het kustgebied",
        "mits in kwelgebied",
        "mits minstens één van de volgende plantensoorten aanwezig is: breed wollegras, gele zegge, schubzegge, tweehuizige zegge, veenzegge",
        "mits niet in het kustgebied",
        "mits op vochtige plaatsen in het kustgebied en kruipwilg dominant",
        "mits in het kustgebied en kruipwilg niet dominant",
        "mits in vennen",
        "mits in vennen en niet droogvallend",
        "mits droogvallend en niet in hoogveen",
        "mits in vennen en met alleen wilde inheemse witte waterlelies",
        "mits in herstellend hoogveen en veenmosbedekking > 20%",
        "mits in herstellend hoogveen en veenmosbedekking < 20%",
        "mits in FGR Laagveengebied",
        "mits niet in hoogveen",
        "mits in FGR Hogere zandgronden zonder hoogveen",
        "mits in het kustgebied en kraaihei aanwezig",
        "mits in het kustgebied en kraaihei afwezig",
        "mits het onderdeel van een hoogveenlandschap is en een acrotelm aanwezig is",
        "mits niet in een hoogveenlandschap en mits een acrotelm aanwezig is of een vergelijkbaar hoogveenvormend proces",
        "mits in zandverstuiving",
        "mits op oeverwallen van rivieren of riviertjes",
        "mits in het kustgebied en niet in mozaïek met zelfstandige vegetaties van H2130_A",
        "mits langs rivieren of riviertjes",
        "mits in het kustgebied, op een standplaats als van andere vegetaties van H2130_A",
        "mits in het kustgebied, op een standplaats als van andere vegetaties van H2130_B",
        "mits in het kustgebied en op een standplaats als van andere vegetaties van H2130_B",
        "mits langs rivieren of riviertjes en minstens twee van de volgende kenmerkende typische plantensoorten aanwezig zijn: brede ereprijs, cipreswolfsmelk, handjesgras, kaal breukkruid, kleine ruit, liggende ereprijs, rivierduinzegge, rode bremraap, sikkelklaver, steenanjer, tripmadam, veldsalie, wilde averuit, zacht vetkruid, zandwolfsmelk",
        "mits kruipwilg niet dominant",
        "mits in het kustgebied en op een standplaats als van andere vegetaties van H2130_A en niet in struweel",
        "mits in het kustgebied en op een standplaats als van andere vegetaties van H2130_B en niet in struweel",
        "mits niet voldoend aan de criteria voor H7230",
        "mits in kwelgebied en niet in het kustgebied en minstens drie van de volgende plantensoorten aanwezig zijn: armbloemige waterbies, bonte paardenstaart, groenknolorchis, grote muggenorchis, knopbies, moeraswespenorchis, parnassia, rechte rus, vleeskleurige orchis, vetblad; echt vetmos, geveerd diknerfmos, goudsikkelmos, groen schorpioenmos, groot staartjesmos, kammos, sterrengoudmos, trilveenveenmos, vierkantsmos, wolfsklauwmos",
        "mits minstens drie van de volgende plantensoorten aanwezig zijn: blauwe knoop, blauwe zegge, gevlekte orchis, ruw walstro, tormentil, veelbloemige veldbies",
        "mits een vlakvormig, al dan niet nabeweid, hooiland",
        "mits in FGR Heuvelland",
        "mits een vlakvormig, al dan niet nabeweid, hooiland en niet in FGR Heuvelland",
        "mits niet in mozaïek met vegetaties van H7230",
        "mits bochtige smele minder dan 25%",
        "mits in het kustgebied en niet in mozaïek met vegetaties van H6230",
        "mits op vaaggronden en niet in het kustgebied en kraaihei niet dominant",
        "mits niet op vaaggronden en niet in het kustgebied en kraaihei niet dominant",
        "mits kraaihei dominant en niet in het kustgebied",
        "mits op vaaggronden en kraaihei niet dominant",
        "mits kraaihei dominant",
        "mits kraaihei niet dominant",
        "mits op een standplaats als van andere vegetaties van H2130_A en kraaihei afwezig",
        "mits op een standplaats als van andere vegetaties van H2130_B en kraaihei afwezig",
        "mits op droge plaatsen in het kustgebied en kraaihei aanwezig",
        "mits op vochtige plaatsen in het kustgebied",
        "mits in de buitenduinen",
        "mits in de buitenduinen en mits niet in mozaïek met vegetaties van H2130",
        "mits in het buitendijkse kustgebied",
        "mits in het binnendijkse kustgebied",
        "mits minstens één niet-algemene plantensoort van zoom of ruigte aanwezig is",
        "mits de constante typische soort moerasspirea aanwezig is",
        "mits de constante typische soort moerasmelkdistel aanwezig is",
        "mits in FGR Duinen en zachte berk dominant",
        "mits het struweel minimaal 1 are groot is, met minimaal 10 jeneverbesstruiken die minimaal 30% bedekken",
        "mits in het kustgebied en duindoorn aanwezig",
        "mits op alluviale bodem en onder invloed van beek of rivier",
        "mits in FGR Duinen",
        "mits met veenmosbedekking > 20%",
        "mits buiten H7110_A en H7120",
        "mits niet in FGR Duinen en buiten H7110_A en H7120",
        "mits niet in FGR Duinen en buiten H7120",
        "mits op leemarme humuspodzolgronden, leemarme vaaggronden of podzolgronden met een zanddek en mits onderdeel van een minimaal honderdjarige opstand van zomereik of op een bosgroeiplaats ouder dan 1850 en mits niet in FGR Duinen",
        "mits op moderpodzolgronden, lemige humuspodzolgronden, oude kleigronden of leemgronden en mits op een bosgroeiplaats ouder dan 1850 of in een daaraan grenzende minimaal honderdjarige bosopstand en mits niet in FGR Duinen",
        "mits in FGR Rivierengebied",
        "mits in FGR Duinen, op een standplaats als van andere vegetaties van H2180_A",
        "mits in FGR Duinen, in vochtige of te vernatten valleien",
        "mits in FGR Duinen, op een standplaats als van andere vegetaties van H2180_C",
        "mits in FGR Hogere zandgronden",
        "mits op moderpodzolgronden, lemige humuspodzolgronden, oude kleigronden of leemgronden zonder hydromorfe kenmerken en mits op een bosgroeiplaats ouder dan 1850 of in een daaraan grenzende minimaal honderdjarige bosopstand en mits niet in FGR Heuvelland of FGR Duinen",
        "mits op hydromorfe bodems in FGR Hogere zandgronden",
        "mits in vennen en niet in kwelgebied en niet in mozaïek met vegetaties van H3130",
        "mits in kwelgebied en niet in vennen",
        "mits in vochtige duinvalleien en niet droogvallend",
        "mits in het kustgebied en droogvallend",
        "alleen in mozaïek met zelfstandige vegetaties van H7140_A",
        "mits droogvallend",
        "mits tufvorming plaatsvindt",
    ]
)
