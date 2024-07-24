import json
from pathlib import Path

import pandas as pd
import pytest

from veg2hab.criteria import BeperkendCriterium, GeenCriterium
from veg2hab.mozaiek import MozaiekRegel

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
        BeperkendCriterium.parse_raw(json.dumps(value))


def test_mozaiekjson(mozaiekjson):
    for value in mozaiekjson.values():
        MozaiekRegel.parse_raw(json.dumps(value))


def test_evaluation_can_be_serialized():
    criterium = GeenCriterium()
    assert criterium.cached_evaluation is None
    criterium.check(row=pd.Series())
    assert criterium.cached_evaluation is not None

    json_str = criterium.json()

    criterium2 = BeperkendCriterium(**json.loads(json_str))
    assert criterium2.cached_evaluation == criterium.cached_evaluation
