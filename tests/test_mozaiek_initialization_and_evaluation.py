from collections import defaultdict

from veg2hab.enums import Kwaliteit, MaybeBoolean
from veg2hab.mozaiek import StandaardMozaiekregel


def test_key_determination_zelfstandig_goed():
    regel = StandaardMozaiekregel(
        habtype="H1", alleen_zelfstandig=True, alleen_goede_kwaliteit=True, threshold=90
    )
    regel.determine_keys()
    assert regel.keys == [("H1", True, Kwaliteit.GOED)]

def test_key_determination_mozaiek_matig():
    regel = StandaardMozaiekregel(
        habtype="H1", alleen_zelfstandig=False, alleen_goede_kwaliteit=False, threshold=90
    )
    regel.determine_keys()
    assert regel.keys == [
        ("H1", True, Kwaliteit.GOED),
        ("H1", False, Kwaliteit.GOED),
        ("H1", True, Kwaliteit.MATIG),
        ("H1", False, Kwaliteit.MATIG),
    ]

def test_100_percent_requested_true():
    regel = StandaardMozaiekregel(
        habtype="H1", alleen_zelfstandig=True, alleen_goede_kwaliteit=True, threshold=90
    )
    regel.determine_keys()
    habtype_percentage_dict = defaultdict(int)
    habtype_percentage_dict[("H1", True, Kwaliteit.GOED)] = 100
    regel.check(habtype_percentage_dict)
    assert regel.evaluation == MaybeBoolean.TRUE

def test_50_percent_requested_50_percent_unknown_postpone():
    regel = StandaardMozaiekregel(
        habtype="H1", alleen_zelfstandig=True, alleen_goede_kwaliteit=True, threshold=90
    )
    regel.determine_keys()
    habtype_percentage_dict = defaultdict(int)
    # Omdat we een threshold van 90 moeten halen, en we daar nog niet zijn,
    # maar we het in de toekomst nog wel zouden kunnen halen, doen we POSTPONE
    habtype_percentage_dict[("H1", True, Kwaliteit.GOED)] = 50
    habtype_percentage_dict[("HXXXX", True, Kwaliteit.NVT)] = 50
    regel.check(habtype_percentage_dict)
    assert regel.evaluation == MaybeBoolean.POSTPONE

def test_100_percent_unrequested_false():
    regel = StandaardMozaiekregel(
        habtype="H1", alleen_zelfstandig=True, alleen_goede_kwaliteit=True, threshold=90
    )
    regel.determine_keys()
    habtype_percentage_dict = defaultdict(int)
    # Omdat we een threshold van 90 moeten halen, en meer dan dat al in de dict
    # zit, doen we FALSE
    habtype_percentage_dict[("H2", False, Kwaliteit.MATIG)] = 100
    regel.check(habtype_percentage_dict)
    assert regel.evaluation == MaybeBoolean.FALSE

def test_50_percent_requested_50_percent_unrequested_false():
    regel = StandaardMozaiekregel(
        habtype="H1", alleen_zelfstandig=True, alleen_goede_kwaliteit=True, threshold=90
    )
    regel.determine_keys()
    habtype_percentage_dict = defaultdict(int)
    # Omdat we een threshold van 90 moeten halen, en 50 procent al een ongevraagd
    # habtype is, zullen we nooit 90 halen, en doen we FALSE
    habtype_percentage_dict[("HXXXX", True, Kwaliteit.NVT)] = 50
    habtype_percentage_dict[("H2", False, Kwaliteit.MATIG)] = 50
    regel.check(habtype_percentage_dict)
    assert regel.evaluation == MaybeBoolean.FALSE

def test_matig_mozaiek_true():
    regel = StandaardMozaiekregel(
        habtype="H1", alleen_zelfstandig=False, alleen_goede_kwaliteit=False, threshold=90
    )
    regel.determine_keys()
    habtype_percentage_dict = defaultdict(int)
    habtype_percentage_dict[("H1", False, Kwaliteit.MATIG)] = 100
    regel.check(habtype_percentage_dict)
    assert regel.evaluation == MaybeBoolean.TRUE


def test_addition_of_acceptable_habtypen():
    regel = StandaardMozaiekregel(
        habtype="H1", alleen_zelfstandig=True, alleen_goede_kwaliteit=False, threshold=90
    )
    habtype_percentage_dict = defaultdict(int)
    habtype_percentage_dict[("H1", True, Kwaliteit.GOED)] = 50
    habtype_percentage_dict[("H1", True, Kwaliteit.MATIG)] = 50
    regel.determine_keys()
    regel.check(habtype_percentage_dict)
    assert regel.evaluation == MaybeBoolean.TRUE


def test_exclusion_of_unacceptable_habtypen():
    regel = StandaardMozaiekregel(
        habtype="H1", alleen_zelfstandig=True, alleen_goede_kwaliteit=False, threshold=90
    )
    habtype_percentage_dict = defaultdict(int)
    habtype_percentage_dict[("H1", True, Kwaliteit.MATIG)] = 50
    habtype_percentage_dict[("H1", False, Kwaliteit.MATIG)] = 50
    regel.determine_keys()
    regel.check(habtype_percentage_dict)
    assert regel.evaluation == MaybeBoolean.FALSE
