import pytest

from veg2hab.io.arcgis import ArcGISInterface
from veg2hab.io.common import Interface


def test_abstract_base_class():
    with pytest.raises(TypeError):
        i = Interface()


# TODO: order of tests matter here. It would be nice
# if the different tests would run in different
# processes, or something.
@pytest.mark.xfail
def test_first_time_get_instance():
    with pytest.raises(TypeError):
        i = Interface.get_instance()


def test_singleton():
    i1 = ArcGISInterface.get_instance()
    i2 = ArcGISInterface.get_instance()
    assert i1 is i2

    # after constructing the ArcGIS interface it
    # can be accessed through the Interface class
    i3 = Interface.get_instance()
    assert i1 is i3
