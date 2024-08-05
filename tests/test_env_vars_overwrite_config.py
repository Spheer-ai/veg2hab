import json
import os

from veg2hab.io.cli import CLIInterface


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


def test_mozaiek_minimum_bedekking():
    os.environ["VEG2HAB_MOZAIEK_MINIMUM_BEDEKKING"] = "91.0"
    assert CLIInterface.get_instance().get_config().mozaiek_minimum_bedekking == 91.0
    os.environ["VEG2HAB_MOZAIEK_MINIMUM_BEDEKKING"] = "90.0"
    assert CLIInterface.get_instance().get_config().mozaiek_minimum_bedekking == 90.0


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


def test_niet_geautomatiseerde_rvvn():
    os.environ[
        "VEG2HAB_NIET_GEAUTOMATISEERDE_RVVN"
    ] = '["r100","r200","r300","r400","r500"]'
    assert CLIInterface.get_instance().get_config().niet_geautomatiseerde_rvvn == [
        "r100",
        "r200",
        "r300",
        "r400",
        "r500",
    ]
    os.environ["VEG2HAB_NIET_GEAUTOMATISEERDE_RVVN"] = '["r100","r200","r300","r400"]'
    assert CLIInterface.get_instance().get_config().niet_geautomatiseerde_rvvn == [
        "r100",
        "r200",
        "r300",
        "r400",
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
    assert (
        CLIInterface.get_instance().get_config().minimum_oppervlak_exceptions["H6110"]
        == 10
    )
    assert (
        CLIInterface.get_instance().get_config().minimum_oppervlak_exceptions["H9110"]
        == 1000
    )
    assert (
        CLIInterface.get_instance()
        .get_config()
        .get_minimum_oppervlak_for_habtype("not_an_exception")
        == 100
    )
    assert (
        CLIInterface.get_instance()
        .get_config()
        .get_minimum_oppervlak_for_habtype("H6110")
        == 10
    )
    assert (
        CLIInterface.get_instance()
        .get_config()
        .get_minimum_oppervlak_for_habtype("H9110")
        == 1000
    )
    os.environ["VEG2HAB_MINIMUM_OPPERVLAK_DEFAULT"] = "200"
    os.environ["VEG2HAB_MINIMUM_OPPERVLAK_EXCEPTIONS"] = json.dumps(
        {
            "H6110": 20,
            "H9110": 2000,
        }
    )
    assert CLIInterface.get_instance().get_config().minimum_oppervlak_default == 200
    assert (
        CLIInterface.get_instance().get_config().minimum_oppervlak_exceptions["H6110"]
        == 20
    )
    assert (
        CLIInterface.get_instance().get_config().minimum_oppervlak_exceptions["H9110"]
        == 2000
    )
    assert (
        CLIInterface.get_instance()
        .get_config()
        .get_minimum_oppervlak_for_habtype("not_an_exception")
        == 200
    )
    assert (
        CLIInterface.get_instance()
        .get_config()
        .get_minimum_oppervlak_for_habtype("H6110")
        == 20
    )
    assert (
        CLIInterface.get_instance()
        .get_config()
        .get_minimum_oppervlak_for_habtype("H9110")
        == 2000
    )


def test_functionele_samenhang():
    os.environ["VEG2HAB_FUNCTIONELE_SAMENHANG_BUFFER_DISTANCES"] = json.dumps(
        [
            [100, 10.01],
            [90, 5.01],
            [50, 0.01],
        ]
    )
    assert (
        CLIInterface.get_instance().get_config().functionele_samenhang_buffer_distances
        == [
            (100, 10.01),
            (90, 5.01),
            (50, 0.01),
        ]
    )
    os.environ["VEG2HAB_FUNCTIONELE_SAMENHANG_BUFFER_DISTANCES"] = json.dumps(
        [
            [101, 10.02],
            [91, 5.02],
            [51, 0.02],
        ]
    )
    assert (
        CLIInterface.get_instance().get_config().functionele_samenhang_buffer_distances
        == [
            (101, 10.02),
            (91, 5.02),
            (51, 0.02),
        ]
    )
    os.environ["VEG2HAB_FUNCTIONELE_SAMENHANG_VEGETATIEKUNDIG_IDENTIEK"] = json.dumps(
        {
            "H2130": "H2130/H4030",
            "H4030": "H2130/H4030",
        }
    )
    assert (
        CLIInterface.get_instance()
        .get_config()
        .functionele_samenhang_vegetatiekundig_identiek
        == {
            "H2130": "H2130/H4030",
            "H4030": "H2130/H4030",
        }
    )
    os.environ["VEG2HAB_FUNCTIONELE_SAMENHANG_VEGETATIEKUNDIG_IDENTIEK"] = json.dumps(
        {
            "H2130": "H4030/H2130",
            "H4030": "H4030/H2130",
        }
    )
    assert (
        CLIInterface.get_instance()
        .get_config()
        .functionele_samenhang_vegetatiekundig_identiek
        == {
            "H2130": "H4030/H2130",
            "H4030": "H4030/H2130",
        }
    )
