from enum import Enum, IntEnum, auto


class MaybeBoolean(Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    MAYBE = "MAYBE"
    # POSTPONE = "POSTPONE" # Used for when evaluation needs to be postponed
    # CANNOT_BE_AUTOMATED = "CANNOT_BE_AUTOMATED"  # Used when manual action is required

    # TODO: kloppende MaybeBoolean.MAYBE en MaybeBoolean.CANNOT_BE_AUTOMATED logic

    def __invert__(self):
        if self == MaybeBoolean.TRUE:
            return MaybeBoolean.FALSE
        elif self == MaybeBoolean.FALSE:
            return MaybeBoolean.TRUE
        else:
            return self


class Kwaliteit(Enum):
    NVT = "Nvt"  # bijvoorbeeld in het geval van H000
    ONBEKEND = "Onbekend"  # bijvoorbeeld in het geval van HXXXX
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
        elif self in [Kwaliteit.NVT, Kwaliteit.ONBEKEND]:
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

    # Geen habitatvoorstel met kloppende mits
    GEEN_KLOPPENDE_MITSEN = auto()

    # Vegtypen niet in deftabel gevonden
    VEGTYPEN_NIET_IN_DEFTABEL = auto()

    # Vlak heeft uit de kartering geen vegetatietypen
    GEEN_OPGEGEVEN_VEGTYPEN = auto()

    # Meerdere even specifieke habitatvoorstellen met kloppende mitsen
    MEERDERE_KLOPPENDE_MITSEN = auto()

    # Er zijn PlaceholderCriteriums, dus handmatige controle
    PLACEHOLDER_CRITERIA = auto()

    # Dit gaat Veg2Hab niet op kunnen lossen
    HANDMATIGE_CONTROLE = auto()

    # Er moet gewacht worden totdat alle zelfstandige habitatwaardige vegetaties
    # zijn bepaald, pas dan kunnen de mozaiekregels worden toegepast
    WACHTEN_OP_MOZAIEK = auto()

    def toelichting(self):
        if self == KeuzeStatus.DUIDELIJK:
            return "Als alle regels gevolgd worden is er 1 duidelijke optie; er is maar 1 habitatvoorstel met kloppende mits/mozaiek."
        elif self == KeuzeStatus.GEEN_KLOPPENDE_MITSEN:
            return "Er is geen habitatvoorstel met kloppende mits/mozaiek. Er kan dus geen habitattype toegekend worden."
        elif self == KeuzeStatus.VEGTYPEN_NIET_IN_DEFTABEL:
            return "De vegetatietypen van het vlak zijn niet in de definitietabel gevonden en leiden dus niet tot een habitattype."
        elif self == KeuzeStatus.GEEN_OPGEGEVEN_VEGTYPEN:
            return "Er zijn in de vegetatiekartering geen vegetatietypen opgegeven voor dit vlak. Er is dus geen habitattype toe te kennen."
        elif self == KeuzeStatus.MEERDERE_KLOPPENDE_MITSEN:
            return "Er zijn meerdere habitatvoorstellen met kloppende mits/mozaiek. Er is geen duidelijke keuze te maken."
        elif self == KeuzeStatus.PLACEHOLDER_CRITERIA:
            return "Er zijn placeholder criteria gevonden; deze kunnen (nog) niet door Veg2Hab worden gecontroleerd."
        elif self == KeuzeStatus.HANDMATIGE_CONTROLE:
            assert (
                False
            ), "Bij KeuzeStatus.HANDMATIGE_CONTROLE moet nog een mooie toelichting, maar ik weet nu nog niet hoe of wat precies."
        elif self == KeuzeStatus.WACHTEN_OP_MOZAIEK:
            return "Veg2Hab kan nog geen mozaiekregels checken"
