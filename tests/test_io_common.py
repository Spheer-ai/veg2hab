import os.path

import pytest

from veg2hab.enums import MaybeBoolean
from veg2hab.io.common import OverrideCriteriumIO


def test_override_criterium_io_validation():
    # Test valid input
    criterium = OverrideCriteriumIO(
        mits="mits in vochtige duinvalleien",
        truth_value="WAAR",
        override_geometry="some_geometry",
        truth_value_outside="ONWAAR",
    )
    assert criterium.mits == "mits in vochtige duinvalleien"
    assert criterium.truth_value == "WAAR"
    assert criterium.override_geometry == "some_geometry"
    assert criterium.truth_value_outside == "ONWAAR"

    # Test invalid mits
    with pytest.raises(ValueError):
        OverrideCriteriumIO(
            mits="invalid_mits",
            truth_value="WAAR",
            override_geometry="some_geometry",
            truth_value_outside="ONWAAR",
        )

    # Test empty override_geometry
    criterium = OverrideCriteriumIO(
        mits="mits in vochtige duinvalleien",
        truth_value="WAAR",
        override_geometry="",
        truth_value_outside="ONWAAR",
    )
    assert criterium.override_geometry is None

    # Test empty truth_value_outside
    criterium = OverrideCriteriumIO(
        mits="mits in vochtige duinvalleien",
        truth_value="WAAR",
        override_geometry="some_geometry",
        truth_value_outside="",
    )
    assert criterium.truth_value_outside is None


def test_override_criterium_io_from_strings():
    values = [
        ("mits in vochtige duinvalleien", "WAAR", "geometry1", "ONWAAR"),
        ("mits in vochtige duinvalleien", "ONWAAR", "", ""),
    ]
    criteriums = OverrideCriteriumIO.from_strings(values)
    assert len(criteriums) == 2

    assert criteriums[0].mits == "mits in vochtige duinvalleien"
    assert criteriums[0].truth_value == "WAAR"
    assert criteriums[0].override_geometry == "geometry1"
    assert criteriums[0].truth_value_outside == "ONWAAR"

    assert criteriums[1].mits == "mits in vochtige duinvalleien"
    assert criteriums[1].truth_value == "ONWAAR"
    assert criteriums[1].override_geometry == None
    assert criteriums[1].truth_value_outside == None


def test_override_criterium_io_to_override_criterium():
    criterium = OverrideCriteriumIO(
        mits="mits in vochtige duinvalleien",
        truth_value="WAAR",
        override_geometry=os.path.dirname(__file__)
        + "/../data/notebook_data/Rottige_Meenthe_Brandemeer_2013/vlakken.shp",
        truth_value_outside="ONWAAR",
    )

    override_criterium = criterium.to_override_criterium()
    assert override_criterium.mits == "mits in vochtige duinvalleien"
    assert override_criterium.truth_value == MaybeBoolean.TRUE
    assert override_criterium.override_geometry is not None
    assert override_criterium.truth_value_outside == MaybeBoolean.FALSE

    criterium = OverrideCriteriumIO(
        mits="mits in vochtige duinvalleien",
        truth_value="WAAR",
        override_geometry=None,
        truth_value_outside=None,
    )
    override_criterium = criterium.to_override_criterium()
    assert override_criterium.mits == "mits in vochtige duinvalleien"
    assert override_criterium.truth_value == MaybeBoolean.TRUE
    assert override_criterium.override_geometry is None
    assert override_criterium.truth_value_outside is None
