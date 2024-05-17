import json
import os

from veg2hab.io.cli import CLIInterface

CLIInterface.get_instance()


def test_mozaiek_threshold():
    os.environ["VEG2HAB_MOZAIEK_THRESHOLD"] = "99.0"
    assert CLIInterface.get_instance().get_config().mozaiek_threshold == 99.0
    os.environ["VEG2HAB_MOZAIEK_THRESHOLD"] = "98.0"
    assert CLIInterface.get_instance().get_config().mozaiek_threshold == 98.0


def test_mozaiek_als_rand_langs_threshold():
    os.environ["VEG2HAB_MOZAIEK_ALS_RAND_THRESHOLD"] = "49.0"
    assert CLIInterface.get_instance().get_config().mozaiek_als_rand_threshold == 49.0
    os.environ["VEG2HAB_MOZAIEK_ALS_RAND_THRESHOLD"] = "48.0"
    assert CLIInterface.get_instance().get_config().mozaiek_als_rand_threshold == 48.0


def test_niet_geautomatiseerde_sbb():
    os.environ["VEG2HAB_NIET_GEAUTOMATISEERDE_SBB"] = '["100","200","300","400","500"]'
    assert CLIInterface.get_instance().get_config().niet_geautomatiseerde_sbb == [
        "100",
        "200",
        "300",
        "400",
        "500",
    ]
    os.environ["VEG2HAB_NIET_GEAUTOMATISEERDE_SBB"] = '["100","200","300","400"]'
    assert CLIInterface.get_instance().get_config().niet_geautomatiseerde_sbb == [
        "100",
        "200",
        "300",
        "400",
    ]


def test_minimum_oppervlak():
    os.environ["VEG2HAB_MINIMUM_OPPERVLAK_DEFAULT"] = "100"
    os.environ["VEG2HAB_MINIMUM_OPPERVLAK_EXCEPTIONS"] = json.dumps(
        {
            "H6110": 10,
            "H9110": 1000,
        }
    )
    assert CLIInterface.get_instance().get_config().minimum_oppervlak_default == 100
    assert CLIInterface.get_instance().get_config().minimum_oppervlak["H6110"] == 10
    assert CLIInterface.get_instance().get_config().minimum_oppervlak["H9110"] == 1000
    os.environ["VEG2HAB_MINIMUM_OPPERVLAK_DEFAULT"] = "200"
    os.environ["VEG2HAB_MINIMUM_OPPERVLAK_EXCEPTIONS"] = json.dumps(
        {
            "H6110": 20,
            "H9110": 2000,
        }
    )
    assert CLIInterface.get_instance().get_config().minimum_oppervlak_default == 200
    assert CLIInterface.get_instance().get_config().minimum_oppervlak["H6110"] == 20
    assert CLIInterface.get_instance().get_config().minimum_oppervlak["H9110"] == 2000
