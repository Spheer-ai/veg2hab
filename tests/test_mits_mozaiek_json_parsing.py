import json
from pathlib import Path

import pytest

from veg2hab.criteria import BeperkendCriterium
from veg2hab.io.cli import CLIInterface
from veg2hab.mozaiek import MozaiekRegel

CLIInterface.get_instance()

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
