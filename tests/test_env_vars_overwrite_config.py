import os

from veg2hab.io.cli import CLIInterface

CLIInterface.get_instance()


def test_mozaiek_threshold():
    os.environ["VEG2HAB_MOZAIEK_THRESHOLD"] = "99.0"
    assert CLIInterface.get_instance().get_config().mozaiek_threshold == 99.0
    os.environ["VEG2HAB_MOZAIEK_THRESHOLD"] = "98.0"
    assert CLIInterface.get_instance().get_config().mozaiek_threshold == 98.0


def test_mozaiek_als_rand_langs_threshold():
    os.environ["VEG2HAB_MOZAIEK_ALS_RAND_LANGS_THRESHOLD"] = "49.0"
    assert (
        CLIInterface.get_instance().get_config().rand_threshold
        == 49.0
    )
    os.environ["VEG2HAB_MOZAIEK_ALS_RAND_LANGS_THRESHOLD"] = "48.0"
    assert (
        CLIInterface.get_instance().get_config().rand_threshold
        == 48.0
    )


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
