from pathlib import Path

import pandas as pd
import pytest

from veg2hab.definitietabel import DefinitieTabel, opschonen_definitietabel
from veg2hab.vegkartering import VegTypeInfo

path_in = Path("data/definitietabel habitattypen (versie 24 maart 2009)_0.xls")
path_out = Path("testing/opgeschoonde_definitietabel.xlsx")
opschonen_definitietabel(path_in, path_out)
dt = DefinitieTabel.from_excel(path_out)


def test_perfect_match_VvN():
    pre = VegTypeInfo.from_str_vegtypes(100, VvN=["25aa3"])
    post = VegTypeInfo.from_str_vegtypes(100, VvN=["25aa3"], habtype=["H1310_A"])
    assert dt.add_habtype_to_VegTypeInfo(pre) == post

def test_match_to_less_specific_VvN():
    pre = VegTypeInfo.from_str_vegtypes(100, VvN=["5ca2a"])
    post = VegTypeInfo.from_str_vegtypes(100, VvN=["5ca2a"], habtype=["H3260_A"])
    # Should match with 5ca2
    assert dt.add_habtype_to_VegTypeInfo(pre) == post

def test_gemeenschap_perfect_match_VvN():
    pre = VegTypeInfo.from_str_vegtypes(100, VvN=["5rg8"])
    post = VegTypeInfo.from_str_vegtypes(100, VvN=["5rg8"], habtype=["H3260_A"]) #kwaliteit="M"
    assert dt.add_habtype_to_VegTypeInfo(pre) == post

def test_match_to_multiple_perfect_matches_VvN():
    pre = VegTypeInfo.from_str_vegtypes(100, VvN=["14bb2a"])
    post = VegTypeInfo.from_str_vegtypes(100, VvN=["14bb2a"], habtype=["H6120", "H2330"])
    # Should match with 5ca2
    assert dt.add_habtype_to_VegTypeInfo(pre) == post



def test_perfect_match_SBB():
    pre = VegTypeInfo.from_str_vegtypes(100, SBB=["9b1"])
    post = VegTypeInfo.from_str_vegtypes(100, SBB=["9b1"], habtype=["H3160"])
    assert dt.add_habtype_to_VegTypeInfo(pre) == post