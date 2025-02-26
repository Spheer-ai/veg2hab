import os
from collections import defaultdict
from pathlib import Path

import pandas as pd
import pytest

from veg2hab.definitietabel import DefinitieTabel, opschonen_definitietabel
from veg2hab.enums import Kwaliteit, MaybeBoolean
from veg2hab.io.cli import CLIInterface
from veg2hab.mozaiek import StandaardMozaiekregel
from veg2hab.vegetatietypen import SBB, VvN

CLIInterface.get_instance()
os.environ["VEG2HAB_MOZAIEK_THRESHOLD"] = "95.0"
os.environ["VEG2HAB_MOZAIEK_ALS_RAND_THRESHOLD"] = "25.0"
os.environ["VEG2HAB_MOZAIEK_MINIMUM_BEDEKKING"] = "90.0"


@pytest.fixture(scope="module")
def dt():
    path_in = (
        Path(__file__).resolve().parent
        / "../data/definitietabel habitattypen (versie 24 maart 2009)_0.xls"
    )
    path_mitsjson = Path(__file__).resolve().parent / "../data/mitsjson.json"
    path_mozaiekjson = Path(__file__).resolve().parent / "../data/mozaiekjson.json"
    path_out = (
        Path(__file__).resolve().parent / "../testing/opgeschoonde_definitietabel.xlsx"
    )
    path_out.parent.mkdir(exist_ok=True)
    opschonen_definitietabel(path_in, path_mitsjson, path_mozaiekjson, path_out)
    return DefinitieTabel.from_excel(path_out)


def test_determine_kwalificerende_vegtypen_normal_case(dt):
    regel = StandaardMozaiekregel(
        kwalificerend_habtype="H2130_C",
        ook_mozaiekvegetaties=True,
        alleen_goede_kwaliteit=True,
        ook_als_rand_langs=False,
    )
    # Normal case
    regel.determine_kwalificerende_vegtypen(
        dt.df[dt.df["Habitattype"] == regel.kwalificerend_habtype]
    )
    assert set(regel.kwalificerende_vegtypen) == {
        VvN.from_code("19aa3"),
        VvN.from_code("19rg1"),
        SBB.from_code("19a-c"),
        SBB.from_code("50c"),
    }


def test_determine_kwalificerende_vegtypen_unfiltered_dt_df(dt):
    regel = StandaardMozaiekregel(
        kwalificerend_habtype="H2130_C",
        ook_mozaiekvegetaties=True,
        alleen_goede_kwaliteit=True,
        ook_als_rand_langs=False,
    )
    with pytest.raises(AssertionError):
        regel.determine_kwalificerende_vegtypen(dt.df)


def test_1_omringend_100_procent_kwalificerend_habtype():
    regel = StandaardMozaiekregel(
        kwalificerend_habtype="H1",
        ook_mozaiekvegetaties=False,
        alleen_goede_kwaliteit=True,
        ook_als_rand_langs=False,
    )
    omringd_door_df = pd.DataFrame(
        {
            "ElmID": [1],
            "habtype": ["H1"],
            "kwaliteit": [Kwaliteit.GOED],
            "vegtypen": [[SBB.from_code("1a1a")]],
            "complexdeel_percentage": [100],
            "omringing_percentage": [100],
        }
    )
    # 1 complexdeel
    regel.check(omringd_door_df)
    assert regel.evaluation == MaybeBoolean.TRUE

    # 2 complexdelen
    omringd_door_df = pd.DataFrame(
        {
            "ElmID": [1, 1],
            "habtype": ["H1", "H1"],
            "kwaliteit": [Kwaliteit.GOED, Kwaliteit.GOED],
            "vegtypen": [[SBB.from_code("1a1a")], [SBB.from_code("2a1a")]],
            "complexdeel_percentage": [50, 50],
            "omringing_percentage": [100, 100],
        }
    )
    regel.check(omringd_door_df)
    assert regel.evaluation == MaybeBoolean.TRUE


def test_1_omringend_50_kwalificerend_50_niet_kwalificerend():
    regel = StandaardMozaiekregel(
        kwalificerend_habtype="H1",
        ook_mozaiekvegetaties=False,
        alleen_goede_kwaliteit=True,
        ook_als_rand_langs=False,
    )
    omringd_door_df = pd.DataFrame(
        {
            "ElmID": [1, 1],
            "habtype": ["H1", "H2"],
            "kwaliteit": [Kwaliteit.GOED, Kwaliteit.GOED],
            "vegtypen": [[SBB.from_code("1a1a")], [SBB.from_code("2a1a")]],
            "complexdeel_percentage": [50, 50],
            "omringing_percentage": [100, 100],
        }
    )
    regel.check(omringd_door_df)
    assert regel.evaluation == MaybeBoolean.FALSE


def test_1_omringend_50_kwalificerend_50_HXXXX():
    regel = StandaardMozaiekregel(
        kwalificerend_habtype="H1",
        ook_mozaiekvegetaties=False,
        alleen_goede_kwaliteit=True,
        ook_als_rand_langs=False,
    )
    omringd_door_df = pd.DataFrame(
        {
            "ElmID": [1, 1],
            "habtype": ["H1", "HXXXX"],
            "kwaliteit": [Kwaliteit.GOED, Kwaliteit.GOED],
            "vegtypen": [[SBB.from_code("1a1a")], [SBB.from_code("2a1a")]],
            "complexdeel_percentage": [50, 50],
            "omringing_percentage": [100, 100],
        }
    )
    regel.check(omringd_door_df)
    assert regel.evaluation == MaybeBoolean.POSTPONE


def test_1_omringend_100_procent_kwalificerend_vegtype(dt):
    regel = StandaardMozaiekregel(
        kwalificerend_habtype="H2130_C",
        ook_mozaiekvegetaties=True,
        alleen_goede_kwaliteit=True,
        ook_als_rand_langs=False,
    )
    omringd_door_df = pd.DataFrame(
        {
            "ElmID": [1],
            "habtype": ["H1"],
            "kwaliteit": [Kwaliteit.GOED],
            "vegtypen": [[VvN.from_code("19aa3")]],
            "complexdeel_percentage": [100],
            "omringing_percentage": [100],
        }
    )
    # 1 complexdeel
    regel.determine_kwalificerende_vegtypen(
        dt.df[dt.df["Habitattype"] == regel.kwalificerend_habtype]
    )
    regel.check(omringd_door_df)
    assert regel.evaluation == MaybeBoolean.TRUE


def test_1_omringend_50_kwalificerend_vegtype_50_kwalificerend_habtype(dt):
    regel = StandaardMozaiekregel(
        kwalificerend_habtype="H2130_C",
        ook_mozaiekvegetaties=True,
        alleen_goede_kwaliteit=True,
        ook_als_rand_langs=False,
    )
    omringd_door_df = pd.DataFrame(
        {
            "ElmID": [1, 1],
            "habtype": ["H2130_C", "HXXXX"],
            "kwaliteit": [Kwaliteit.GOED, Kwaliteit.GOED],
            "vegtypen": [[SBB.from_code("1a1a")], [VvN.from_code("19aa3")]],
            "complexdeel_percentage": [50, 50],
            "omringing_percentage": [100, 100],
        }
    )
    regel.determine_kwalificerende_vegtypen(
        dt.df[dt.df["Habitattype"] == regel.kwalificerend_habtype]
    )
    regel.check(omringd_door_df)
    assert regel.evaluation == MaybeBoolean.TRUE


def test_1_omringend_100_procent_kwalificerend_habtype_goed_matig():
    regel = StandaardMozaiekregel(
        kwalificerend_habtype="H1",
        ook_mozaiekvegetaties=False,
        alleen_goede_kwaliteit=True,
        ook_als_rand_langs=False,
    )
    omringd_door_df = pd.DataFrame(
        {
            "ElmID": [1],
            "habtype": ["H1"],
            "kwaliteit": [Kwaliteit.MATIG],
            "vegtypen": [[SBB.from_code("1a1a")]],
            "complexdeel_percentage": [100],
            "omringing_percentage": [100],
        }
    )

    # Goede kwaliteit vereist, matige in de omringing
    regel.check(omringd_door_df)
    assert regel.evaluation == MaybeBoolean.FALSE

    # Goede kwaliteit niet vereist, matige in de omringing
    regel.alleen_goede_kwaliteit = False
    regel.check(omringd_door_df)
    assert regel.evaluation == MaybeBoolean.TRUE

    # Goede kwaliteit niet vereist, goede in de omringing
    omringd_door_df.iloc[0, omringd_door_df.columns.get_loc("kwaliteit")] = (
        Kwaliteit.GOED
    )
    regel.check(omringd_door_df)
    assert regel.evaluation == MaybeBoolean.TRUE


def test_2_omringend_beide_100_procent_kwalificerend_habtype():
    regel = StandaardMozaiekregel(
        kwalificerend_habtype="H1",
        ook_mozaiekvegetaties=False,
        alleen_goede_kwaliteit=True,
        ook_als_rand_langs=False,
    )
    omringd_door_df = pd.DataFrame(
        {
            "ElmID": [1, 2],
            "habtype": ["H1", "H1"],
            "kwaliteit": [Kwaliteit.GOED, Kwaliteit.GOED],
            "vegtypen": [[SBB.from_code("1a1a")], [SBB.from_code("2a1a")]],
            "complexdeel_percentage": [100, 100],
            "omringing_percentage": [50, 50],
        }
    )
    regel.check(omringd_door_df)
    assert regel.evaluation == MaybeBoolean.TRUE


def test_2_omringend_eentje_kwalificerend_eentje_niet():
    regel = StandaardMozaiekregel(
        kwalificerend_habtype="H1",
        ook_mozaiekvegetaties=False,
        alleen_goede_kwaliteit=True,
        ook_als_rand_langs=False,
    )
    omringd_door_df = pd.DataFrame(
        {
            "ElmID": [1, 2],
            "habtype": ["H1", "H2"],
            "kwaliteit": [Kwaliteit.GOED, Kwaliteit.GOED],
            "vegtypen": [[SBB.from_code("1a1a")], [SBB.from_code("2a1a")]],
            "complexdeel_percentage": [100, 100],
            "omringing_percentage": [50, 50],
        }
    )
    regel.check(omringd_door_df)
    assert regel.evaluation == MaybeBoolean.FALSE


def test_2_omringend_eentje_kwalificerend_eentje_HXXXX():
    regel = StandaardMozaiekregel(
        kwalificerend_habtype="H1",
        ook_mozaiekvegetaties=False,
        alleen_goede_kwaliteit=True,
        ook_als_rand_langs=False,
    )
    omringd_door_df = pd.DataFrame(
        {
            "ElmID": [1, 2],
            "habtype": ["H1", "HXXXX"],
            "kwaliteit": [Kwaliteit.GOED, Kwaliteit.GOED],
            "vegtypen": [[SBB.from_code("1a1a")], [SBB.from_code("2a1a")]],
            "complexdeel_percentage": [100, 100],
            "omringing_percentage": [50, 50],
        }
    )
    regel.check(omringd_door_df)
    assert regel.evaluation == MaybeBoolean.POSTPONE


def test_als_rand_langs():
    regel = StandaardMozaiekregel(
        kwalificerend_habtype="H1",
        ook_mozaiekvegetaties=False,
        alleen_goede_kwaliteit=True,
        ook_als_rand_langs=False,
    )
    omringd_door_df = pd.DataFrame(
        {
            "ElmID": [1],
            "habtype": ["H1"],
            "kwaliteit": [Kwaliteit.GOED],
            "vegtypen": [[SBB.from_code("1a1a")]],
            "complexdeel_percentage": [100],
            "omringing_percentage": [70],
        }
    )
    # Niet ook_als_rand_langs
    regel.check(omringd_door_df)
    assert regel.evaluation == MaybeBoolean.FALSE

    # Ook ook_als_rand_langs
    regel.ook_als_rand_langs = True
    regel.check(omringd_door_df)
    assert regel.evaluation == MaybeBoolean.TRUE
