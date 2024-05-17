import json
import os
from collections import defaultdict

import geopandas as gpd
import pytest

from veg2hab.enums import KeuzeStatus, Kwaliteit
from veg2hab.habitat import HabitatKeuze, apply_minimum_oppervlak
from veg2hab.io.cli import CLIInterface
from veg2hab.vegkartering import VegTypeInfo

#
# Deze test is voor minimum oppervlak **zonder** enige vorm van functionele samenhang
#
# De minimum oppervlakken zijn in min_area nog even hier gedefinieerd (met dezelfde waarden als in habitat.py),
# maar moeten in de toekomst naar een mooie config file.
#


@pytest.fixture
def gdf():
    """
    Er zijn 3 thresholds; 10, 100 en 1000 m². (Zie min_area (TODO: zie config))

    5 vlakken

    1. 100% H7220, 10 m²
    2. 100% H1234, 80 m²
    4. 50% H1234, 50% H4321, 100 m²
    5. 100% H9110, 1000 m²
    """
    # Deze heb ik hier hard gecode omdat anders de test_env_vars_overwrite_config mijn min_area en min_area_default overschrijft
    os.environ["VEG2HAB_MINIMUM_OPPERVLAK_EXCEPTIONS"] = json.dumps(
        {
            "H6110": 10,
            "H7220": 10,
            "H2180_A": 1000,
            "H2180_B": 1000,
            "H2180_C": 1000,
            "H9110": 1000,
            "H9120": 1000,
            "H9160_A": 1000,
            "H9160_B": 1000,
            "H9190": 1000,
            "H91D0": 1000,
            "H91E0_A": 1000,
            "H91E0_B": 1000,
            "H91E0_C": 1000,
            "H91F0": 1000,
        }
    )
    os.environ["VEG2HAB_MINIMUM_OPPERVLAK_DEFAULT"] = "100"
    min_area = CLIInterface.get_instance().get_config().minimum_oppervlak
    min_area_default = (
        CLIInterface.get_instance().get_config().minimum_oppervlak_default
    )

    return gpd.GeoDataFrame(
        {
            "Opp": [
                min_area.get("H6110", min_area_default),
                min_area.get("H1234", min_area_default) * 0.8,
                min_area.get("H1234", min_area_default),
                min_area.get("H2180_A", min_area_default),
            ],
            "VegTypeInfo": [
                [VegTypeInfo(SBB=[], VvN=[], percentage=100)],
                [VegTypeInfo(SBB=[], VvN=[], percentage=100)],
                [
                    VegTypeInfo(SBB=[], VvN=[], percentage=60),
                    VegTypeInfo(SBB=[], VvN=[], percentage=40),
                ],
                [VegTypeInfo(SBB=[], VvN=[], percentage=100)],
            ],
            "HabitatKeuze": [
                [
                    HabitatKeuze(
                        status=KeuzeStatus.DUIDELIJK,
                        habtype="H7220",
                        kwaliteit=Kwaliteit.GOED,
                        habitatvoorstellen=[],
                    )
                ],
                [
                    HabitatKeuze(
                        status=KeuzeStatus.DUIDELIJK,
                        habtype="H1234",
                        kwaliteit=Kwaliteit.GOED,
                        habitatvoorstellen=[],
                    )
                ],
                [
                    HabitatKeuze(
                        status=KeuzeStatus.DUIDELIJK,
                        habtype="H1234",
                        kwaliteit=Kwaliteit.GOED,
                        habitatvoorstellen=[],
                    ),
                    HabitatKeuze(
                        status=KeuzeStatus.DUIDELIJK,
                        habtype="H4321",
                        kwaliteit=Kwaliteit.GOED,
                        habitatvoorstellen=[],
                    ),
                ],
                [
                    HabitatKeuze(
                        status=KeuzeStatus.DUIDELIJK,
                        habtype="H9110",
                        kwaliteit=Kwaliteit.GOED,
                        habitatvoorstellen=[],
                    )
                ],
            ],
        }
    )


def extract_habtypen(gdf):
    return [[keuze.habtype for keuze in keuzelist] for keuzelist in gdf["HabitatKeuze"]]


def test_generic_habtype_minimum_area(gdf):
    min_area = CLIInterface.get_instance().get_config().minimum_oppervlak
    min_area_default = (
        CLIInterface.get_instance().get_config().minimum_oppervlak_default
    )
    # Te klein
    subset = gdf.iloc[[1]].copy()
    subset["HabitatKeuze"] = apply_minimum_oppervlak(subset)
    assert [["H0000"]] == extract_habtypen(subset)

    # Groot genoeg
    subset = gdf.iloc[[1]].copy()
    subset["Opp"] = min_area.get("H1234", min_area_default) * 1.1
    subset["HabitatKeuze"] = apply_minimum_oppervlak(subset)
    assert [["H1234"]] == extract_habtypen(subset)


def test_special_cases_minimum_area(gdf):
    # Precies groot genoeg
    subset = gdf.iloc[[0, 3]].copy()
    subset["HabitatKeuze"] = apply_minimum_oppervlak(subset)
    assert [["H7220"], ["H9110"]] == extract_habtypen(subset)

    # Omgewisseld; alleen H7220 is groot genoeg
    subset = gdf.iloc[[0, 3]].copy()
    subset.HabitatKeuze.at[0], subset.HabitatKeuze.at[3] = (
        subset.HabitatKeuze.at[3],
        subset.HabitatKeuze.at[0],
    )
    subset["HabitatKeuze"] = apply_minimum_oppervlak(subset)
    assert [["H0000"], ["H7220"]] == extract_habtypen(subset)


def test_complex_minimum_area(gdf):
    min_area = CLIInterface.get_instance().get_config().minimum_oppervlak
    min_area_default = (
        CLIInterface.get_instance().get_config().minimum_oppervlak_default
    )
    # Precies groot genoeg voor 1 habtype, maar door complex te klein
    subset = gdf.iloc[[2]].copy()
    subset["HabitatKeuze"] = apply_minimum_oppervlak(subset)
    assert [["H0000", "H0000"]] == extract_habtypen(subset)

    # Dubbel zo groot vlak, dus 60% is nu groot genoeg
    subset = gdf.iloc[[2]].copy()
    subset["Opp"] = min_area.get("H1234", min_area_default) * 2
    subset["HabitatKeuze"] = apply_minimum_oppervlak(subset)
    assert [["H1234", "H0000"]] == extract_habtypen(subset)

    # Drie keer zo groot vlak, dus 60% en 40% zijn nu groot genoeg
    subset = gdf.iloc[[2]].copy()
    subset["Opp"] = min_area.get("H1234", min_area_default) * 3
    subset["HabitatKeuze"] = apply_minimum_oppervlak(subset)
    assert [["H1234", "H4321"]] == extract_habtypen(subset)


def test_all_minimum_area(gdf):
    gdf["HabitatKeuze"] = apply_minimum_oppervlak(gdf)
    assert [["H7220"], ["H0000"], ["H0000", "H0000"], ["H9110"]] == extract_habtypen(
        gdf
    )
