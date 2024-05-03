from collections import defaultdict

import geopandas as gpd
import pytest

from veg2hab.enums import KeuzeStatus, Kwaliteit
from veg2hab.habitat import HabitatKeuze, apply_minimum_oppervlak
from veg2hab.vegkartering import VegTypeInfo

#
# Deze test is voor minimum oppervlak **zonder** enige vorm van functionele samenhang
#
# De minimum oppervlakken zijn in MIN_AREA nog even hier gedefinieerd (met dezelfde waarden als in habitat.py),
# maar moeten in de toekomst naar een mooie config file.
#

# TODO: dit naar config

MIN_AREA = defaultdict(lambda: 100)
for habtype in ["H6110", "H7220"]:
    MIN_AREA[habtype] = 10
for habtype in [
    "H2180_A",
    "H2180_B",
    "H2180_C",
    "H9110",
    "H9120",
    "H9160_A",
    "H9160_B",
    "H9190",
    "H91D0",
    "H91E0_A",
    "H91E0_B",
    "H91E0_C",
    "H91F0",
]:
    MIN_AREA[habtype] = 1000


@pytest.fixture
def gdf():
    '''
    Er zijn 3 thresholds; 10, 100 en 1000 m². (Zie MIN_AREA (TODO: zie config))

    5 vlakken
    
    1. 100% H7220, 10 m²
    2. 100% H1234, 80 m²
    4. 50% H1234, 50% H4321, 100 m²
    5. 100% H9110, 1000 m²
    '''
    return gpd.GeoDataFrame(
        {
            "area": [MIN_AREA["H6110"], MIN_AREA["H1234"] * 0.8, MIN_AREA["H1234"], MIN_AREA["H2180_A"]],
            "VegTypeInfo": [
                [VegTypeInfo(SBB=[], VvN=[], percentage=100)],
                [VegTypeInfo(SBB=[], VvN=[], percentage=100)],
                [VegTypeInfo(SBB=[], VvN=[], percentage=60), VegTypeInfo(SBB=[], VvN=[], percentage=40)],
                [VegTypeInfo(SBB=[], VvN=[], percentage=100)],
            ],
            "HabitatKeuze": [
                [
                    HabitatKeuze(
                        status=KeuzeStatus.DUIDELIJK,
                        habtype="H7220",
                        kwaliteit=Kwaliteit.GOED,
                        zelfstandig=True,
                        habitatvoorstellen=[],
                    )
                ],
                [
                    HabitatKeuze(
                        status=KeuzeStatus.DUIDELIJK,
                        habtype="H1234",
                        kwaliteit=Kwaliteit.GOED,
                        zelfstandig=True,
                        habitatvoorstellen=[],
                    )
                ],
                [
                    HabitatKeuze(
                        status=KeuzeStatus.DUIDELIJK,
                        habtype="H1234",
                        kwaliteit=Kwaliteit.GOED,
                        zelfstandig=True,
                        habitatvoorstellen=[],
                    ),
                    HabitatKeuze(
                        status=KeuzeStatus.DUIDELIJK,
                        habtype="H4321",
                        kwaliteit=Kwaliteit.GOED,
                        zelfstandig=True,
                        habitatvoorstellen=[],
                    )
                ],
                [
                    HabitatKeuze(
                        status=KeuzeStatus.DUIDELIJK,
                        habtype="H9110",
                        kwaliteit=Kwaliteit.GOED,
                        zelfstandig=True,
                        habitatvoorstellen=[],
                    )
                ],
            ],
        }
    )


def extract_habtypen(gdf):
    return [[keuze.habtype for keuze in keuzelist] for keuzelist in gdf["HabitatKeuze"]]


def test_generic_habtype_minimum_area(gdf):
    # Te klein
    subset = gdf.iloc[[1]]
    gecheckt = apply_minimum_oppervlak(subset)
    assert [["H0000"]] == extract_habtypen(gecheckt)
    
    # Groot genoeg
    subset = gdf.iloc[[1]].copy()
    subset["area"] = MIN_AREA["H1234"] * 1.1
    gecheckt = apply_minimum_oppervlak(subset)
    assert [["H1234"]] == extract_habtypen(gecheckt)


def test_small_large_minimum_area(gdf):
    # Precies groot genoeg
    subset = gdf.iloc[0, 3]
    gecheckt = apply_minimum_oppervlak(subset)
    assert [["H7220", "H9110"]] == extract_habtypen(gecheckt)

    # Omgewisseld; alleen H7220 is groot genoeg
    subset = gdf.iloc[0, 3].copy()
    subset["HabitatKeuze"] = subset.iloc[[1, 0]].HabitatKeuze
    gecheckt = apply_minimum_oppervlak(subset)
    assert [["H0000", "H7220"]] == extract_habtypen(gecheckt)


def test_complex_minimum_area(gdf):
    # Precies groot genoeg voor 1, maar door complex te klein
    subset = gdf.iloc[[2]]
    gecheckt = apply_minimum_oppervlak(subset)
    assert [["H0000", "H0000"]] == extract_habtypen(gecheckt)

    # Dubbel zo groot vlak, dus 60% is nu groot genoeg
    subset = gdf.iloc[[2]].copy()
    subset["area"] = MIN_AREA["H1234"] * 2
    gecheckt = apply_minimum_oppervlak(subset)
    assert [["H1234", "H0000"]] == extract_habtypen(gecheckt)

    # Drie keer zo groot vlak, dus 60% en 40% zijn nu groot genoeg
    subset["area"] = MIN_AREA["H1234"] * 3
    gecheckt = apply_minimum_oppervlak(subset)
    assert [["H1234", "H4321"]] == extract_habtypen(gecheckt)


def test_all_minimum_area(gdf):
    # Alles is groot genoeg
    gecheckt = apply_minimum_oppervlak(gdf)
    assert [["H7220"], ["H1234"], ["H0000", "H0000"], ["H9110"]] == extract_habtypen(gecheckt)

