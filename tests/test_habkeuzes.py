import geopandas as gpd
import pytest

from veg2hab.criteria import GeenCriterium, NietCriterium, NietGeautomatiseerdCriterium
from veg2hab.enums import KeuzeStatus, Kwaliteit, MatchLevel
from veg2hab.habitat import HabitatKeuze, HabitatVoorstel, try_to_determine_habkeuze
from veg2hab.io.cli import CLIInterface
from veg2hab.mozaiek import (
    GeenMozaiekregel,
    NietGeimplementeerdeMozaiekregel,
    StandaardMozaiekregel,
)
from veg2hab.vegetatietypen import SBB, VvN

CLIInterface.get_instance()

'''

@dataclass
class HabitatVoorstel:
    """
    Een voorstel voor een habitattype voor een vegetatietype
    """

    onderbouwend_vegtype: Optional[Union[_SBB, _VvN]]
    vegtype_in_dt: Optional[Union[_SBB, _VvN]]
    habtype: str
    kwaliteit: Kwaliteit
    idx_in_dt: Optional[int]
    mits: BeperkendCriterium
    mozaiek: MozaiekRegel
    match_level: MatchLevel
    mozaiek_dict: Optional[dict] = None

    @classmethod
    def H0000_vegtype_not_in_dt(cls, info: "VegTypeInfo"):
        return cls(
            onderbouwend_vegtype=info.VvN[0]
            if info.VvN
            else (info.SBB[0] if info.SBB else None),
            vegtype_in_dt=None,
            habtype="H0000",
            kwaliteit=Kwaliteit.NVT,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.NO_MATCH,
        )

    @classmethod
    def H0000_no_vegtype_present(cls):
        return cls(
            onderbouwend_vegtype=None,
            vegtype_in_dt=None,
            habtype="H0000",
            kwaliteit=Kwaliteit.NVT,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.NO_MATCH,
        )

    @classmethod
    def HXXXX_niet_geautomatiseerd_SBB(cls, info: "VegTypeInfo"):
        assert len(info.SBB) > 0
        return cls(
            onderbouwend_vegtype=info.SBB[0],
            vegtype_in_dt=None,
            habtype="HXXXX",
            kwaliteit=Kwaliteit.NVT,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.NO_MATCH,
        )


@dataclass
class HabitatKeuze:
    status: KeuzeStatus
    habtype: str  # format = "H1123"
    kwaliteit: Kwaliteit
    habitatvoorstellen: List[HabitatVoorstel]  # used as a refence
    opmerking: str = ""
    mits_opmerking: str = ""
    mozaiek_opmerking: str = ""
    debug_info: Optional[str] = ""

    def __post_init__(self):
        # Validatie
        if self.status in [
            KeuzeStatus.DUIDELIJK,
        ]:
            assert self.habtype not in ["HXXXX", "H0000"]
        elif self.status in [
            KeuzeStatus.GEEN_KLOPPENDE_MITSEN,
            KeuzeStatus.VEGTYPEN_NIET_IN_DEFTABEL,
            KeuzeStatus.GEEN_OPGEGEVEN_VEGTYPEN,
        ]:
            assert self.habtype == "H0000"
        elif self.status in [
            KeuzeStatus.WACHTEN_OP_MOZAIEK,
            KeuzeStatus.NIET_GEAUTOMATISEERD_CRITERIUM,
            KeuzeStatus.MEERDERE_KLOPPENDE_MITSEN,
        ]:
            assert self.habtype == "HXXXX"

        if self.habtype in ["H0000", "HXXXX"]:
            assert self.kwaliteit == Kwaliteit.NVT

    @classmethod
    def habitatkeuze_for_postponed_mozaiekregel(
        cls, habitatvoorstellen: List[HabitatVoorstel]
    ):
        return cls(
            status=KeuzeStatus.WACHTEN_OP_MOZAIEK,
            habtype="HXXXX",
            kwaliteit=Kwaliteit.NVT,
            opmerking="Er is een mozaiekregel waarvoor nog te weinig info is om een keuze te maken.",
            habitatvoorstellen=habitatvoorstellen,
            mits_opmerking="",
            mozaiek_opmerking="",
            debug_info="",
        )

    @property
    def zelfstandig(self):
        if self.habtype in ["H0000", "HXXXX"]:
            return True

        return is_mozaiek_type_present(self.habitatvoorstellen, GeenMozaiekregel)
'''


def test_habtype_toegekend():
    voorstel = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB("25a1a"),
            vegtype_in_dt=SBB("25a1a"),
            habtype="H1234",
            kwaliteit=Kwaliteit.NVT,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_SBB,
        )
    ]
    for v in voorstel:
        v.mits.check(gpd.GeoSeries())
        v.mozaiek.check(dict)
    keuze = try_to_determine_habkeuze(voorstel)
    assert keuze.status == KeuzeStatus.HABITATTYPE_TOEGEKEND
    assert keuze.habtype == "H1234"


def test_combine_same_habtype_multiple_voorstellen():
    voorstellen = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB("25a1a"),
            vegtype_in_dt=SBB("25a1a"),
            habtype="H1234",
            kwaliteit=Kwaliteit.GOED,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_SBB,
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=SBB("25a1a"),
            vegtype_in_dt=SBB("25a1a"),
            habtype="H1234",
            kwaliteit=Kwaliteit.GOED,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_SBB,
        ),
    ]
    for v in voorstellen:
        v.mits.check(gpd.GeoSeries())
        v.mozaiek.check(dict)
    keuze = try_to_determine_habkeuze(voorstellen)
    assert keuze.status == KeuzeStatus.HABITATTYPE_TOEGEKEND
    assert keuze.habtype == "H1234"
    assert keuze.kwaliteit == Kwaliteit.GOED


def test_voldoet_aan_meerdere_habtypen():
    voorstellen = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB("25a1a"),
            vegtype_in_dt=SBB("25a1a"),
            habtype="H1234",
            kwaliteit=Kwaliteit.GOED,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_SBB,
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=SBB("25a1a"),
            vegtype_in_dt=SBB("25a1a"),
            habtype="H1235",
            kwaliteit=Kwaliteit.GOED,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_SBB,
        ),
    ]
    for v in voorstellen:
        v.mits.check(gpd.GeoSeries())
        v.mozaiek.check(dict)
    keuze = try_to_determine_habkeuze(voorstellen)
    assert keuze.status == KeuzeStatus.VOLDOET_AAN_MEERDERE_HABTYPEN
    assert keuze.habtype == "HXXXX"
    assert keuze.kwaliteit == Kwaliteit.NVT


def test_voldoet_niet_aan_habtypevoorwaarden():
    voorstellen = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB("25a1a"),
            vegtype_in_dt=SBB("25a1a"),
            habtype="H1234",
            kwaliteit=Kwaliteit.NVT,
            idx_in_dt=None,
            mits=NietCriterium(sub_criterium=GeenCriterium()),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_SBB,
        )
    ]
    for v in voorstellen:
        v.mits.check(gpd.GeoSeries())
        v.mozaiek.check(dict)
    keuze = try_to_determine_habkeuze(voorstellen)
    assert keuze.status == KeuzeStatus.VOLDOET_NIET_AAN_HABTYPEVOORWAARDEN
    assert keuze.habtype == "H0000"
    assert keuze.kwaliteit == Kwaliteit.NVT


def test_vegtypen_niet_in_deftabel():
    voorstellen = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB("25a1a"),
            vegtype_in_dt=SBB("25a1a"),
            habtype="H0000",
            kwaliteit=Kwaliteit.NVT,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.NO_MATCH,
        )
    ]
    for v in voorstellen:
        v.mits.check(gpd.GeoSeries())
        v.mozaiek.check(dict)
    keuze = try_to_determine_habkeuze(voorstellen)
    assert keuze.status == KeuzeStatus.VEGTYPEN_NIET_IN_DEFTABEL
    assert keuze.habtype == "H0000"
    assert keuze.kwaliteit == Kwaliteit.NVT


def test_geen_opgegeven_vegtypen():
    voorstellen = [
        HabitatVoorstel(
            onderbouwend_vegtype=None,
            vegtype_in_dt=None,
            habtype="H0000",
            kwaliteit=Kwaliteit.NVT,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.NO_MATCH,
        )
    ]
    for v in voorstellen:
        v.mits.check(gpd.GeoSeries())
        v.mozaiek.check(dict)
    keuze = try_to_determine_habkeuze(voorstellen)
    assert keuze.status == KeuzeStatus.GEEN_OPGEGEVEN_VEGTYPEN
    assert keuze.habtype == "H0000"
    assert keuze.kwaliteit == Kwaliteit.NVT


def test_niet_geautomatiseerd_vegtype():
    niet_geautomatiseerd_vegtype = (
        CLIInterface.get_instance().get_config().niet_geautomatiseerde_sbb[0]
    )
    voorstellen = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB(niet_geautomatiseerd_vegtype),
            vegtype_in_dt=None,
            habtype="HXXXX",
            kwaliteit=Kwaliteit.NVT,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.NO_MATCH,
        )
    ]
    for v in voorstellen:
        v.mits.check(gpd.GeoSeries())
        v.mozaiek.check(dict)
    keuze = try_to_determine_habkeuze(voorstellen)
    assert keuze.status == KeuzeStatus.NIET_GEAUTOMATISEERD_VEGTYPE
    assert keuze.habtype == "HXXXX"
    assert keuze.kwaliteit == Kwaliteit.NVT


def test_niet_geautomatiseerd_criterium():
    voorstellen = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB("25a1a"),
            vegtype_in_dt=SBB("25a1a"),
            habtype="H1234",
            kwaliteit=Kwaliteit.NVT,
            idx_in_dt=None,
            mits=NietGeautomatiseerdCriterium(
                toelichting="Dit criterium is niet geautomatiseerd"
            ),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_SBB,
        )
    ]
    for v in voorstellen:
        v.mits.check(gpd.GeoSeries())
        v.mozaiek.check(dict)
    keuze = try_to_determine_habkeuze(voorstellen)
    assert keuze.status == KeuzeStatus.NIET_GEAUTOMATISEERD_CRITERIUM
    assert keuze.habtype == "HXXXX"
    assert keuze.kwaliteit == Kwaliteit.NVT
    voorstellen = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB("25a1a"),
            vegtype_in_dt=SBB("25a1a"),
            habtype="H1234",
            kwaliteit=Kwaliteit.NVT,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=NietGeimplementeerdeMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_SBB,
        )
    ]
    for v in voorstellen:
        v.mits.check(gpd.GeoSeries())
        v.mozaiek.check(dict)
    keuze = try_to_determine_habkeuze(voorstellen)
    assert keuze.status == KeuzeStatus.NIET_GEAUTOMATISEERD_CRITERIUM
    assert keuze.habtype == "HXXXX"
    assert keuze.kwaliteit == Kwaliteit.NVT


def test_wachten_op_mozaiek():
    voorstellen = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB("25a1a"),
            vegtype_in_dt=SBB("25a1a"),
            habtype="H1234",
            kwaliteit=Kwaliteit.NVT,
            idx_in_dt=None,
            mits=GeenCriterium(),
            mozaiek=StandaardMozaiekregel(
                habtype="H1234",
                alleen_zelfstandig=True,
                alleen_goede_kwaliteit=False,
                ook_als_rand_langs=False,
            ),
            match_level=MatchLevel.SUBASSOCIATIE_SBB,
        )
    ]
    for v in voorstellen:
        v.mits.check(gpd.GeoSeries())
        v.mozaiek.check({("HXXXX", True, Kwaliteit.NVT): 100})
    keuze = try_to_determine_habkeuze(voorstellen)
    assert keuze.status == KeuzeStatus.WACHTEN_OP_MOZAIEK
    assert keuze.habtype == "HXXXX"
    assert keuze.kwaliteit == Kwaliteit.NVT
