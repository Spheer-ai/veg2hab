import pytest

from veg2hab.io.arcgis import ArcGISInterface
from veg2hab.io.common import Interface


@pytest.fixture
def remove_and_reset_Interface():
    original_instance = Interface._instance
    Interface._instance = None

    yield 

    Interface._instance = original_instance

def test_abstract_base_class():
    with pytest.raises(TypeError):
        i = Interface()


def test_first_time_get_instance(remove_and_reset_Interface):
    with pytest.raises(TypeError):
        i = Interface.get_instance()

def test_singleton(remove_and_reset_Interface):
    i1 = ArcGISInterface.get_instance()
    i2 = ArcGISInterface.get_instance()
    assert i1 is i2

    i3 = Interface.get_instance()
    assert i1 is i3
