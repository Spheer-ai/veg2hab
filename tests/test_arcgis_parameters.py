import sys
from unittest.mock import MagicMock, patch

import pytest

from veg2hab.io.arcgis import ArcGISParameters


def test_to_parameter_list():
    # TODO dit kan netter. Moeten even kijken hoe dit makkelijker kan.
    arcpy_mock = MagicMock()
    sys.modules["arcpy"] = arcpy_mock

    arcpy_mock.Parameter.return_value = MagicMock(name="Parameter")

    param_list = ArcGISParameters.to_parameter_list()

    assert len(param_list) == 10