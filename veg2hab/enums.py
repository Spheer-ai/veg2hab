from enum import Enum, IntEnum, auto


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


class Kwaliteit(Enum):
    NVT = "Nvt"  # bijvoorbeeld in het geval van H0000 en HXXXX
    # NOTE: Ik heb dit weggehaald want ik ben NVT en ONBEKEND door mekaar wezen halen, en eigenlijk past NVT ook wel bij HXXXX
    # ONBEKEND = "Onbekend"  # bijvoorbeeld in het geval van HXXXX
    GOED = "Goed"
    MATIG = "Matig"

    @classmethod
    def from_letter(cls, letter: str) -> "Kwaliteit":
        if letter == "G":
            return cls.GOED
        elif letter == "M":
            return cls.MATIG
        else:
            raise ValueError("Letter moet G of M zijn")

    def as_letter(self) -> str:
        if self == Kwaliteit.GOED:
            return "G"
        elif self == Kwaliteit.MATIG:
            return "M"
        elif self in [Kwaliteit.NVT]:
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
    DUIDELIJK = auto()

    # Er is wel een keuze gemaakt, maar de minimum oppervlakte van het habitattype is niet gehaald
    MINIMUM_OPP_NIET_GEHAALD = auto()

    # Geen habitatvoorstel met kloppende mits
    GEEN_KLOPPENDE_MITSEN = auto()

    # Vegtypen niet in deftabel gevonden
    VEGTYPEN_NIET_IN_DEFTABEL = auto()

    # Vlak heeft uit de kartering geen vegetatietypen
    GEEN_OPGEGEVEN_VEGTYPEN = auto()

    # Meerdere even specifieke habitatvoorstellen met kloppende mitsen
    MEERDERE_KLOPPENDE_MITSEN = auto()

    # Er zijn NietGeautomatiseerdCriteriums, dus handmatige controle
    NIET_GEAUTOMATISEERD_CRITERIUM = auto()

    # Er is een vegetatietype dat we niet kunnen omzetten
    NIET_GEAUTOMATISEERD_VEGTYPE = auto()

    # Er is meer dan threshold % HXXXX in de omliggende vlakken
    WACHTEN_OP_MOZAIEK = auto()

    __toelichting = {
        "DUIDELIJK": "Als alle regels gevolgd worden is er 1 duidelijke optie; er is maar 1 habitatvoorstel met kloppende mits/mozaiek.",
        "MINIMUM_OPP_NIET_GEHAALD": "Er is een habitatvoorstel met kloppende mits/mozaiek, maar de minimum oppervlakte van het habitattype is niet gehaald.",
        "GEEN_KLOPPENDE_MITSEN": "Er is geen habitatvoorstel met kloppende mits/mozaiek. Er kan dus geen habitattype toegekend worden.",
        "VEGTYPEN_NIET_IN_DEFTABEL": "De vegetatietypen van het vlak zijn niet in de definitietabel gevonden en leiden dus niet tot een habitattype.",
        "GEEN_OPGEGEVEN_VEGTYPEN": "Er zijn in de vegetatiekartering geen (habitatwaardige)vegetatietypen opgegeven voor dit vlak. Er is dus geen habitattype toe te kennen.",
        "MEERDERE_KLOPPENDE_MITSEN": "Er zijn meerdere habitatvoorstellen met kloppende mits/mozaiek. Er is geen duidelijke keuze te maken.",
        "NIET_GEAUTOMATISEERD_CRITERIUM": "Er zijn niet-geautomatiseerde mitsen/mozaiekregels gevonden; deze kunnen niet door Veg2Hab worden gecontroleerd.",
        "NIET_GEAUTOMATISEERD_VEGTYPE": "Er is een vegetatietype dat niet geautomatiseerd kan worden omgezet naar een habitattype.",
        "WACHTEN_OP_MOZAIEK": "Er is te weinig informatie over de habitattypen van omliggende vlakken (teveel HXXXX)",
    }

    @property
    def toelichting(self):
        return self.__toelichting.value[self.name]


class FGRType(Enum):
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
