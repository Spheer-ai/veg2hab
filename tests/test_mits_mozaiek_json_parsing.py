import json
from pathlib import Path

import pandas as pd
import pytest

from veg2hab.criteria import BeperkendCriterium, GeenCriterium, criteria_from_json
from veg2hab.mozaiek import (
    GeenMozaiekregel,
    NietGeimplementeerdeMozaiekregel,
    StandaardMozaiekregel,
    mozaiekregel_from_json,
)

# Simpelweg elke mits en elke mozaiekregel in de .jsons instancen en dan (hopelijk) merken dat alles werkt


@pytest.fixture
def mitsjson() -> dict:
    p = Path(__file__).resolve().parent / "../data/mitsjson.json"
    with p.open() as f:
        return json.load(f)


@pytest.fixture
def mozaiekjson() -> dict:
    p = Path(__file__).resolve().parent / "../data/mozaiekjson.json"
    with p.open() as f:
        return json.load(f)


def test_mitsjson(mitsjson):
    for value in mitsjson.values():
        criteria_from_json(json.dumps(value))


def test_mozaiekjson(mozaiekjson):
    for value in mozaiekjson.values():
        mozaiekregel_from_json(json.dumps(value))


def test_mozaiekregel_from_json():
    geen_mozaiekregel = GeenMozaiekregel()
    assert (
        mozaiekregel_from_json(geen_mozaiekregel.model_dump_json()) == geen_mozaiekregel
    )

    standaard_mozaiekregel = StandaardMozaiekregel(
        kwalificerend_habtype="H1",
        ook_mozaiekvegetaties=True,
        alleen_goede_kwaliteit=True,
        ook_als_rand_langs=True,
    )
    assert (
        mozaiekregel_from_json(standaard_mozaiekregel.model_dump_json())
        == standaard_mozaiekregel
    )

    niet_geimplementeerde_mozaiekregel = NietGeimplementeerdeMozaiekregel()
    assert (
        mozaiekregel_from_json(niet_geimplementeerde_mozaiekregel.model_dump_json())
        == niet_geimplementeerde_mozaiekregel
    )


def test_evaluation_can_be_serialized():
    criterium = GeenCriterium()
    assert criterium.cached_evaluation is None
    criterium.check(row=pd.Series())
    assert criterium.cached_evaluation is not None

    json_str = criterium.model_dump_json()

    criterium2 = criteria_from_json(json_str)
    assert criterium2.cached_evaluation == criterium.cached_evaluation
