import copy
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import MultiPolygon, Polygon

from veg2hab import constants
from veg2hab.criteria import FGRCriterium, OfCriteria, OverrideCriterium
from veg2hab.definitietabel import DefinitieTabel
from veg2hab.enums import FGRType, MaybeBoolean
from veg2hab.vegkartering import VegTypeInfo


@pytest.fixture
def override_geometry():
    return gpd.GeoSeries([Polygon([(0, 0), (0, 3), (2.5, 3), (2.5, 0)])])


@pytest.fixture
def split_override_geometry():
    """
    These polygons are small 0.6 by 0.6 squares inside karting_geometry polygons 1 and 2
    """
    return gpd.GeoSeries(
        [
            Polygon([(1.2, 1.2), (1.2, 1.8), (1.8, 1.8), (1.8, 1.2)]),
            Polygon([(2.2, 1.2), (2.2, 1.8), (2.8, 1.8), (2.8, 1.2)]),
        ]
    )


@pytest.fixture
def kartering_geometry():
    return gpd.GeoDataFrame(
        {
            "data": [0, 1, 2],
            "geometry": [
                Polygon([(1, 1), (1, 2), (2, 2), (2, 1)]),
                Polygon([(2, 1), (2, 2), (3, 2), (3, 1)]),
                Polygon([(3, 1), (3, 2), (4, 2), (4, 1)]),
            ],
        }
    )


@pytest.fixture(scope="module")
def definitietabel():
    return DefinitieTabel.from_excel(Path(constants.DEFTABEL_PATH))


def test_override_criteria_instantiation(override_geometry):
    # non-geometry OverrideCriterium
    crit = OverrideCriterium(mits="mitsemits", truth_value=MaybeBoolean.TRUE)
    assert isinstance(crit, OverrideCriterium)

    # geometry OverrideCriterium
    crit = OverrideCriterium(
        mits="mitsemits",
        truth_value=MaybeBoolean.TRUE,
        override_geometry=override_geometry,
        truth_value_outside=MaybeBoolean.FALSE,
    )
    assert isinstance(crit, OverrideCriterium)

    # geometry OverrideCriterium without truth_value_outside
    with pytest.raises(ValueError):
        crit = OverrideCriterium(
            mits="mitsemits",
            truth_value=MaybeBoolean.TRUE,
            override_geometry=override_geometry,
        )

    # geometry OverrideCriterium without override_geometry
    with pytest.raises(ValueError):
        crit = OverrideCriterium(
            mits="mitsemits",
            truth_value=MaybeBoolean.TRUE,
            truth_value_outside=MaybeBoolean.FALSE,
        )


def test_definitietabel_override_criteria_injection(definitietabel):
    # override_dict maken en setten
    mits = (
        "mits in het binnendijkse kustgebied"  # dit is de tweede match voor VvN 26aa1
    )
    override_crit = OverrideCriterium(mits="mitsemits", truth_value=MaybeBoolean.TRUE)
    override_dict = {mits: override_crit}
    definitietabel.set_override_dict(override_dict)

    # voorstellen krijgen op basis van VegTypeInfo en override_dict
    info = VegTypeInfo.from_str_vegtypes(percentage=100, VvN_strings=["26aa1"])
    voorstellen = definitietabel.find_habtypes(info)

    expected_mits_1 = OfCriteria(
        sub_criteria=[
            FGRCriterium(wanted_fgrtype=FGRType.DU),
            FGRCriterium(wanted_fgrtype=FGRType.GG),
        ]
    )
    expected_mits_2 = override_crit
    assert voorstellen[0].mits == expected_mits_1
    assert voorstellen[1].mits == expected_mits_2


def test_checking_without_shape(kartering_geometry):
    # Test TRUE
    crit = OverrideCriterium(mits="mitsemits", truth_value=MaybeBoolean.TRUE)
    # geometry does not actually matter here
    crit.check(kartering_geometry.iloc[0])
    assert crit.cached_evaluation == MaybeBoolean.TRUE

    # Test FALSE
    crit = OverrideCriterium(mits="mitsemits", truth_value=MaybeBoolean.FALSE)
    # geometry does not actually matter here
    crit.check(kartering_geometry.iloc[0])
    assert crit.cached_evaluation == MaybeBoolean.FALSE

    # Test CANNOT_BE_AUTOMATED
    crit = OverrideCriterium(
        mits="mitsemits", truth_value=MaybeBoolean.CANNOT_BE_AUTOMATED
    )
    # geometry does not actually matter here
    crit.check(kartering_geometry.iloc[0])
    assert crit.cached_evaluation == MaybeBoolean.CANNOT_BE_AUTOMATED


def test_with_single_geometry(override_geometry, kartering_geometry):
    """
    +----------+
    | override |
    |    +---+-|-+---+
    |    | 0 |1|1| 2 | <- kartering_geometry
    |    +---+-|-+---+
    | geometry |
    +----------+
    kartering_geometry[1] is overlapped by override, not split in half
    """
    crit = OverrideCriterium(
        mits="mitsemits",
        truth_value=MaybeBoolean.TRUE,
        override_geometry=override_geometry,
        truth_value_outside=MaybeBoolean.FALSE,
    )
    crit1, crit2, crit3 = copy.copy(crit), copy.copy(crit), copy.copy(crit)
    crit1.check(kartering_geometry.iloc[0])
    crit2.check(kartering_geometry.iloc[1])
    crit3.check(kartering_geometry.iloc[2])

    assert crit1.cached_evaluation == MaybeBoolean.TRUE
    assert crit2.cached_evaluation == MaybeBoolean.TRUE
    assert crit3.cached_evaluation == MaybeBoolean.FALSE


def test_with_multiple_geometries(split_override_geometry, kartering_geometry):
    """
    +-------+-------+-------+
    | 0     | 1     | 2     |
    | +---+ | +---+ |       |
    | | x | | | x | |       |   <- karting_geometry
    | +---+ | +---+ |       |
    +-------+-------+-------+
    x = split_override_geometry
    """
    crit = OverrideCriterium(
        mits="mitsemits",
        truth_value=MaybeBoolean.TRUE,
        override_geometry=split_override_geometry,
        truth_value_outside=MaybeBoolean.FALSE,
    )
    crit1, crit2, crit3 = copy.copy(crit), copy.copy(crit), copy.copy(crit)
    crit1.check(kartering_geometry.iloc[0])
    crit2.check(kartering_geometry.iloc[1])
    crit3.check(kartering_geometry.iloc[2])

    assert crit1.cached_evaluation == MaybeBoolean.TRUE
    assert crit2.cached_evaluation == MaybeBoolean.TRUE
    assert crit3.cached_evaluation == MaybeBoolean.FALSE


def test_with_multipolygon(split_override_geometry, kartering_geometry):
    """
    +-------+-------+-------+
    | 0     | 1     | 2     |
    | +---+ | +---+ |       |
    | | x | | | x | |       |   <- karting_geometry
    | +---+ | +---+ |       |
    +-------+-------+-------+
    x = split_override_geometry
    """
    multi_polygon = gpd.GeoSeries(
        [
            MultiPolygon(
                [
                    split_override_geometry[0],
                    split_override_geometry[1],
                ]
            )
        ]
    )
    crit = OverrideCriterium(
        mits="mitsemits",
        truth_value=MaybeBoolean.TRUE,
        override_geometry=multi_polygon,
        truth_value_outside=MaybeBoolean.FALSE,
    )
    crit1, crit2, crit3 = copy.copy(crit), copy.copy(crit), copy.copy(crit)
    crit1.check(kartering_geometry.iloc[0])
    crit2.check(kartering_geometry.iloc[1])
    crit3.check(kartering_geometry.iloc[2])

    assert crit1.cached_evaluation == MaybeBoolean.TRUE
    assert crit2.cached_evaluation == MaybeBoolean.TRUE
    assert crit3.cached_evaluation == MaybeBoolean.FALSE
