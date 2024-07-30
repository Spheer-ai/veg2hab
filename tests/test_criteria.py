import pandas as pd
import pytest

from veg2hab.criteria import (
    BodemCriterium,
    EnCriteria,
    FGRCriterium,
    GeenCriterium,
    LBKCriterium,
    NietCriterium,
    NietGeautomatiseerdCriterium,
    OfCriteria,
)
from veg2hab.enums import BodemType, FGRType, LBKType, MaybeBoolean

# For "tests" of criteria.get_opm, please see demo_criteria_opmerkingen.py


def test_GeenCriterium():
    crit = GeenCriterium()
    crit.check(pd.Series())
    assert crit.evaluation == MaybeBoolean.TRUE


def test_FGRCriterium():
    crit = FGRCriterium(wanted_fgrtype=FGRType.DU)
    assert crit.wanted_fgrtype == FGRType.DU
    row = pd.Series({"fgr": FGRType.DU})
    crit.check(row)
    assert crit.evaluation == MaybeBoolean.TRUE
    row = pd.Series({"fgr": FGRType.LV})
    crit.check(row)
    assert crit.evaluation == MaybeBoolean.FALSE


def test_LBKCriterium_enkel_negatieven():
    crit = LBKCriterium(wanted_lbktype=LBKType.HOOGVEEN)
    assert crit.wanted_lbktype == LBKType.HOOGVEEN
    row = pd.Series({"lbk": "HzHL"})
    crit.check(row)
    assert crit.wanted_lbktype.enkel_negatieven == True
    assert crit.evaluation == MaybeBoolean.CANNOT_BE_AUTOMATED
    row = pd.Series({"lbk": "Abcd"})
    crit.check(row)
    assert crit.evaluation == MaybeBoolean.FALSE


def test_LBKCriterium_enkel_positieven():
    crit = LBKCriterium(wanted_lbktype=LBKType.HOOGVEENLANDSCHAP)
    assert crit.wanted_lbktype == LBKType.HOOGVEENLANDSCHAP
    row = pd.Series({"lbk": "HzHL"})
    crit.check(row)
    assert crit.wanted_lbktype.enkel_positieven == True
    assert crit.evaluation == MaybeBoolean.TRUE
    row = pd.Series({"lbk": "Abcd"})
    crit.check(row)
    assert crit.evaluation == MaybeBoolean.CANNOT_BE_AUTOMATED


def test_BodemCriterium_normaal():
    crit = BodemCriterium(wanted_bodemtype=BodemType.LEEMARME_HUMUSPODZOLGRONDEN)
    assert crit.wanted_bodemtype == BodemType.LEEMARME_HUMUSPODZOLGRONDEN
    row = pd.Series({"bodem": ["Hn21"]})
    crit.check(row)
    assert crit.wanted_bodemtype.enkel_negatieven == False
    assert crit.evaluation == MaybeBoolean.TRUE
    row = pd.Series({"bodem": ["Abcd"]})
    crit.check(row)
    assert crit.evaluation == MaybeBoolean.FALSE
    row = pd.Series({"bodem": ["Abcd", "Hn21"]})
    crit.check(row)
    assert crit.evaluation == MaybeBoolean.CANNOT_BE_AUTOMATED


def test_BodemCriterium_enkel_negatieven():
    crit = BodemCriterium(wanted_bodemtype=BodemType.LEEMARME_VAAGGRONDEN_H9190)
    assert crit.wanted_bodemtype == BodemType.LEEMARME_VAAGGRONDEN_H9190
    row = pd.Series({"bodem": ["Zn21"]})
    crit.check(row)
    assert crit.wanted_bodemtype.enkel_negatieven == True
    assert crit.evaluation == MaybeBoolean.CANNOT_BE_AUTOMATED
    row = pd.Series({"bodem": ["Abcd"]})
    crit.check(row)
    assert crit.evaluation == MaybeBoolean.FALSE


def test_EnCriteria():
    crit = EnCriteria(
        sub_criteria=[
            FGRCriterium(wanted_fgrtype=FGRType.DU),
            FGRCriterium(wanted_fgrtype=FGRType.LV),
        ]
    )
    row = pd.Series({"fgr": FGRType.DU})
    crit.check(row)
    assert crit.evaluation == MaybeBoolean.FALSE
    crit = EnCriteria(
        sub_criteria=[
            FGRCriterium(wanted_fgrtype=FGRType.DU),
            FGRCriterium(wanted_fgrtype=FGRType.DU),
        ]
    )
    row = pd.Series({"fgr": FGRType.DU})
    crit.check(row)
    assert crit.evaluation == MaybeBoolean.TRUE


def test_OfCriteria():
    crit = OfCriteria(
        sub_criteria=[
            FGRCriterium(wanted_fgrtype=FGRType.DU),
            FGRCriterium(wanted_fgrtype=FGRType.LV),
        ]
    )
    row = pd.Series({"fgr": FGRType.DU})
    crit.check(row)
    assert crit.evaluation == MaybeBoolean.TRUE
    crit = OfCriteria(
        sub_criteria=[
            FGRCriterium(wanted_fgrtype=FGRType.DU),
            FGRCriterium(wanted_fgrtype=FGRType.DU),
        ]
    )
    row = pd.Series({"fgr": FGRType.LV})
    crit.check(row)
    assert crit.evaluation == MaybeBoolean.FALSE


def test_NietCriterium():
    crit = NietCriterium(sub_criterium=FGRCriterium(wanted_fgrtype=FGRType.DU))
    row = pd.Series({"fgr": FGRType.DU})
    crit.check(row)
    assert crit.evaluation == MaybeBoolean.FALSE
    row = pd.Series({"fgr": FGRType.LV})
    crit.check(row)
    assert crit.evaluation == MaybeBoolean.TRUE


def test_NietGeautomatiseerdCriterium():
    crit = NietGeautomatiseerdCriterium(toelichting="test")
    crit.check(pd.Series())
    assert crit.evaluation == MaybeBoolean.CANNOT_BE_AUTOMATED
