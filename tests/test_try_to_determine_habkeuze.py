import geopandas as gpd

from veg2hab.criteria import GeenCriterium, NietCriterium, NietGeautomatiseerdCriterium
from veg2hab.enums import KeuzeStatus, Kwaliteit, MatchLevel
from veg2hab.habitat import HabitatVoorstel, try_to_determine_habkeuze
from veg2hab.io.cli import CLIInterface
from veg2hab.mozaiek import (
    GeenMozaiekregel,
    NietGeimplementeerdeMozaiekregel,
    StandaardMozaiekregel,
)
from veg2hab.vegetatietypen import SBB


def test_habtype_toegekend():
    voorstel = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB.from_code("25a1a"),
            vegtype_in_dt=SBB.from_code("25a1a"),
            habtype="H1234",
            kwaliteit=Kwaliteit.NVT,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_SBB,
        )
    ]
    for v in voorstel:
        v.mits.check(gpd.GeoSeries())
        v.mozaiek.check(dict())
    keuze = try_to_determine_habkeuze(voorstel)
    assert keuze.status == KeuzeStatus.HABITATTYPE_TOEGEKEND
    assert keuze.habtype == "H1234"


def test_combine_same_habtype_multiple_voorstellen():
    voorstellen = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB.from_code("25a1a"),
            vegtype_in_dt=SBB.from_code("25a1a"),
            habtype="H1234",
            kwaliteit=Kwaliteit.GOED,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_SBB,
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=SBB.from_code("25a1a"),
            vegtype_in_dt=SBB.from_code("25a1a"),
            habtype="H1234",
            kwaliteit=Kwaliteit.GOED,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_SBB,
        ),
    ]
    for v in voorstellen:
        v.mits.check(gpd.GeoSeries())
        v.mozaiek.check(dict())
    keuze = try_to_determine_habkeuze(voorstellen)
    assert keuze.status == KeuzeStatus.HABITATTYPE_TOEGEKEND
    assert keuze.habtype == "H1234"
    assert keuze.kwaliteit == Kwaliteit.GOED


def test_voldoet_aan_meerdere_habtypen():
    voorstellen = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB.from_code("25a1a"),
            vegtype_in_dt=SBB.from_code("25a1a"),
            habtype="H1234",
            kwaliteit=Kwaliteit.GOED,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_SBB,
        ),
        HabitatVoorstel(
            onderbouwend_vegtype=SBB.from_code("25a1a"),
            vegtype_in_dt=SBB.from_code("25a1a"),
            habtype="H1235",
            kwaliteit=Kwaliteit.GOED,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_SBB,
        ),
    ]
    for v in voorstellen:
        v.mits.check(gpd.GeoSeries())
        v.mozaiek.check(dict())
    keuze = try_to_determine_habkeuze(voorstellen)
    assert keuze.status == KeuzeStatus.VOLDOET_AAN_MEERDERE_HABTYPEN
    assert keuze.habtype == "HXXXX"
    assert keuze.kwaliteit == Kwaliteit.NVT


def test_voldoet_niet_aan_habtypevoorwaarden():
    voorstellen = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB.from_code("25a1a"),
            vegtype_in_dt=SBB.from_code("25a1a"),
            habtype="H1234",
            kwaliteit=Kwaliteit.NVT,
            mits=NietCriterium(sub_criterium=GeenCriterium()),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_SBB,
        )
    ]
    for v in voorstellen:
        v.mits.check(gpd.GeoSeries())
        v.mozaiek.check(dict())
    keuze = try_to_determine_habkeuze(voorstellen)
    assert keuze.status == KeuzeStatus.VOLDOET_NIET_AAN_HABTYPEVOORWAARDEN
    assert keuze.habtype == "H0000"
    assert keuze.kwaliteit == Kwaliteit.NVT


def test_vegtypen_niet_in_deftabel():
    voorstellen = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB.from_code("25a1a"),
            vegtype_in_dt=SBB.from_code("25a1a"),
            habtype="H0000",
            kwaliteit=Kwaliteit.NVT,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.NO_MATCH,
        )
    ]
    for v in voorstellen:
        v.mits.check(gpd.GeoSeries())
        v.mozaiek.check(dict())
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
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.NO_MATCH,
        )
    ]
    for v in voorstellen:
        v.mits.check(gpd.GeoSeries())
        v.mozaiek.check(dict())
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
            onderbouwend_vegtype=SBB.from_code(niet_geautomatiseerd_vegtype),
            vegtype_in_dt=None,
            habtype="HXXXX",
            kwaliteit=Kwaliteit.NVT,
            mits=GeenCriterium(),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.NO_MATCH,
        )
    ]
    for v in voorstellen:
        v.mits.check(gpd.GeoSeries())
        v.mozaiek.check(dict())
    keuze = try_to_determine_habkeuze(voorstellen)
    assert keuze.status == KeuzeStatus.NIET_GEAUTOMATISEERD_VEGTYPE
    assert keuze.habtype == "HXXXX"
    assert keuze.kwaliteit == Kwaliteit.NVT


def test_niet_geautomatiseerd_criterium():
    voorstellen = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB.from_code("25a1a"),
            vegtype_in_dt=SBB.from_code("25a1a"),
            habtype="H1234",
            kwaliteit=Kwaliteit.NVT,
            mits=NietGeautomatiseerdCriterium(
                toelichting="Dit criterium is niet geautomatiseerd"
            ),
            mozaiek=GeenMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_SBB,
        )
    ]
    for v in voorstellen:
        v.mits.check(gpd.GeoSeries())
        v.mozaiek.check(dict())
    keuze = try_to_determine_habkeuze(voorstellen)
    assert keuze.status == KeuzeStatus.NIET_GEAUTOMATISEERD_CRITERIUM
    assert keuze.habtype == "HXXXX"
    assert keuze.kwaliteit == Kwaliteit.NVT
    voorstellen = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB.from_code("25a1a"),
            vegtype_in_dt=SBB.from_code("25a1a"),
            habtype="H1234",
            kwaliteit=Kwaliteit.NVT,
            mits=GeenCriterium(),
            mozaiek=NietGeimplementeerdeMozaiekregel(),
            match_level=MatchLevel.SUBASSOCIATIE_SBB,
        )
    ]
    for v in voorstellen:
        v.mits.check(gpd.GeoSeries())
        v.mozaiek.check(dict())
    keuze = try_to_determine_habkeuze(voorstellen)
    assert keuze.status == KeuzeStatus.NIET_GEAUTOMATISEERD_CRITERIUM
    assert keuze.habtype == "HXXXX"
    assert keuze.kwaliteit == Kwaliteit.NVT


def test_wachten_op_mozaiek():
    voorstellen = [
        HabitatVoorstel(
            onderbouwend_vegtype=SBB.from_code("25a1a"),
            vegtype_in_dt=SBB.from_code("25a1a"),
            habtype="H1234",
            kwaliteit=Kwaliteit.NVT,
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
