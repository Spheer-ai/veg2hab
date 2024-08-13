import json
import os

from veg2hab.io.cli import CLIInterface


def test_combineer_karteringen_weglaten_threshold():
    initial_value = CLIInterface.get_instance().get_config().combineer_karteringen_weglaten_threshold
    os.environ["VEG2HAB_COMBINEER_KARTERINGEN_WEGLATEN_THRESHOLD"] = str(initial_value + 1)
    assert (
        CLIInterface.get_instance()
        .get_config()
        .combineer_karteringen_weglaten_threshold
        == initial_value + 1
    )
    os.environ["VEG2HAB_COMBINEER_KARTERINGEN_WEGLATEN_THRESHOLD"] = str(initial_value)
    assert (
        CLIInterface.get_instance()
        .get_config()
        .combineer_karteringen_weglaten_threshold
        == initial_value
    )


def test_mozaiek_threshold():
    initial_value = CLIInterface.get_instance().get_config().mozaiek_threshold
    os.environ["VEG2HAB_MOZAIEK_THRESHOLD"] = str(initial_value + 1)
    assert CLIInterface.get_instance().get_config().mozaiek_threshold == initial_value + 1
    os.environ["VEG2HAB_MOZAIEK_THRESHOLD"] = str(initial_value)
    assert CLIInterface.get_instance().get_config().mozaiek_threshold == initial_value


def test_mozaiek_als_rand_langs_threshold():
    initial_value = CLIInterface.get_instance().get_config().mozaiek_als_rand_threshold
    os.environ["VEG2HAB_MOZAIEK_ALS_RAND_THRESHOLD"] = str(initial_value + 1)
    assert CLIInterface.get_instance().get_config().mozaiek_als_rand_threshold == initial_value + 1
    os.environ["VEG2HAB_MOZAIEK_ALS_RAND_THRESHOLD"] = str(initial_value)
    assert CLIInterface.get_instance().get_config().mozaiek_als_rand_threshold == initial_value


def test_mozaiek_minimum_bedekking():
    initial_value = CLIInterface.get_instance().get_config().mozaiek_minimum_bedekking
    os.environ["VEG2HAB_MOZAIEK_MINIMUM_BEDEKKING"] = str(initial_value + 1)
    assert CLIInterface.get_instance().get_config().mozaiek_minimum_bedekking == initial_value + 1
    os.environ["VEG2HAB_MOZAIEK_MINIMUM_BEDEKKING"] = str(initial_value)
    assert CLIInterface.get_instance().get_config().mozaiek_minimum_bedekking == initial_value


def test_niet_geautomatiseerde_sbb():
    initial_value = CLIInterface.get_instance().get_config().niet_geautomatiseerde_sbb
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
    os.environ["VEG2HAB_NIET_GEAUTOMATISEERDE_SBB"] = json.dumps(initial_value)


def test_niet_geautomatiseerde_rvvn():
    initial_value = CLIInterface.get_instance().get_config().niet_geautomatiseerde_rvvn
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
    os.environ["VEG2HAB_NIET_GEAUTOMATISEERDE_RVVN"] = json.dumps(initial_value)


def test_minimum_oppervlak():
    initial_default = CLIInterface.get_instance().get_config().minimum_oppervlak_default
    initial_exceptions = CLIInterface.get_instance().get_config().minimum_oppervlak_exceptions
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
    os.environ["VEG2HAB_MINIMUM_OPPERVLAK_DEFAULT"] = str(initial_default)
    os.environ["VEG2HAB_MINIMUM_OPPERVLAK_EXCEPTIONS"] = json.dumps(initial_exceptions)


def test_functionele_samenhang():
    initial_buffer_distances = CLIInterface.get_instance().get_config().functionele_samenhang_buffer_distances
    initial_vegetatiekundig_identiek = CLIInterface.get_instance().get_config().functionele_samenhang_vegetatiekundig_identiek
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
    os.environ["VEG2HAB_FUNCTIONELE_SAMENHANG_BUFFER_DISTANCES"] = json.dumps(initial_buffer_distances)
    os.environ["VEG2HAB_FUNCTIONELE_SAMENHANG_VEGETATIEKUNDIG_IDENTIEK"] = json.dumps(initial_vegetatiekundig_identiek)
