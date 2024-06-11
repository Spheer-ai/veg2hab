import hashlib
import logging
import sys
import urllib.request
from pathlib import Path
from typing import Optional

import geopandas as gpd
from typing_extensions import Self

import veg2hab.constants
from veg2hab.enums import FGRType

# TODO: Op het moment doen we bij sjoin predicate "within", zodat karteringvlakken die niet volledig
#       binnen een bronvlak liggen NaN krijgen. Beter zou zijn dat ze alles krijgen waar ze op liggen, en als
#       dat steeds dezelfde is, het karteringvlak alsnog dat type krijgt. Dit kan voorkomen bij LBK en bij
#       de bodemkaart, omdat hier regelmatig vlakken met dezelfde typering toch naast elkaar liggen, omdat ze
#       verschillen in zaken waar wij niet naar kijken.


def get_checksum(path: Path) -> str:
    assert path.is_file()
    chunk_size = 8192

    with path.open("rb") as f:
        file_hash = hashlib.md5()
        chunk = f.read(chunk_size)
        while chunk:
            file_hash.update(chunk)
            chunk = f.read(chunk_size)
    return file_hash.hexdigest()


def get_datadir(app_author: str, app_name: str) -> Path:
    """
    Returns a parent directory path where persistent application data can be stored.

    - linux: ~/.local/share
    - windows: C:/Users/<USER>/AppData/Roaming
    """

    home = Path.home()

    if sys.platform == "win32":
        p = home / "AppData" / "Roaming"
    elif sys.platform.startswith("linux"):
        p = home / ".local" / "share"
    else:
        raise ValueError("Unsupported platform")

    return p / app_author / app_name


class LBK:
    def __init__(self, gdf: gpd.GeoDataFrame):
        if set(gdf.columns) != {"geometry", "lbk"}:
            raise ValueError(
                "The GeoDataFrame should have columns 'geometry' and 'lbk'"
            )
        self.gdf = gdf

    @classmethod
    def from_file(cls, path: Path, mask: Optional[gpd.GeoDataFrame] = None) -> Self:
        return cls(
            gpd.read_file(path, mask=mask, include_fields=["Serie"]).rename(
                columns={"Serie": "lbk"}
            )
        )

    @classmethod
    def from_github(cls, mask: Optional[gpd.GeoDataFrame] = None) -> Self:
        local_path = get_datadir("veg2hab", "data", veg2hab.__version__) / "lbk.gpkg"
        remote_path = f"https://github.com/Spheer-ai/veg2hab/releases/download/v{veg2hab.__version__}/lbk.gpkg"

        if (
            not local_path.is_file()
            or get_checksum(local_path) != veg2hab.constants.LBK_CHECKSUM
        ):
            logging.warning(
                "Lokale versie LBK kaart komt niet overeen of bestaat nog niet. Downloaden van github kan enkele minuten duren. Even geduld aub."
            )
            logging.debug(f"Download bodemkaart van {remote_path} naar {local_path}")
            local_path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(remote_path, local_path)

        return cls.from_file(local_path, mask)

    def for_geometry(self, other_gdf: gpd.GeoDataFrame) -> gpd.GeoSeries:
        """
        Returns bodemkaart codes voor de gegeven geometrie
        """
        assert "geometry" in other_gdf.columns
        return gpd.sjoin(other_gdf, self.gdf, how="left", predicate="within").lbk


class FGR:
    def __init__(self, path: Path):
        # inladen
        self.gdf = gpd.read_file(path)
        self.gdf = self.gdf[["fgr", "geometry"]]

        # omzetten naar enum (validatie)
        self.gdf["fgr"] = self.gdf["fgr"].apply(FGRType)

    def for_geometry(self, other_gdf: gpd.GeoDataFrame) -> gpd.GeoSeries:
        """
        Returns fgr codes voor de gegeven geometrie
        """
        assert "geometry" in other_gdf.columns
        return gpd.sjoin(other_gdf, self.gdf, how="left", predicate="within").fgr


class Bodemkaart:
    def __init__(self, gdf: gpd.GeoDataFrame):
        if set(gdf.columns) != {"geometry", "bodem"}:
            raise ValueError(
                "The GeoDataFrame should have columns 'geometry' and 'bodem'"
            )
        self.gdf = gdf

    @classmethod
    def from_file(cls, path: Path, mask: Optional[gpd.GeoDataFrame] = None) -> Self:
        # inladen
        soil_area = gpd.read_file(
            path, layer="soilarea", mask=mask, include_fields=["maparea_id"]
        )
        soil_units_table = gpd.read_file(
            path,
            layer="soilarea_soilunit",
            include_fields=["maparea_id", "soilunit_code"],
            ignore_geometry=True,
        )
        gdf = soil_area.merge(soil_units_table, on="maparea_id")[
            ["geometry", "soilunit_code"]
        ]
        gdf = gdf.rename(columns={"soilunit_code": "bodem"})
        return cls(gdf)

    @classmethod
    def from_github(cls, mask: Optional[gpd.GeoDataFrame] = None) -> Self:
        local_path = get_datadir("veg2hab", "data") / "bodemkaart.gpkg"
        remote_path = f"https://github.com/Spheer-ai/veg2hab/releases/download/v{veg2hab.__version__}/bodemkaart.gpkg"

        if (
            not local_path.is_file()
            or get_checksum(local_path) != veg2hab.constants.BODEMKAART_CHECKSUM
        ):
            logging.warning(
                "Lokale versie bodemkaart komt niet overeen of bestaat nog niet. Downloaden van github kan enkele minuten duren. Even geduld aub."
            )
            logging.debug(f"Download bodemkaart van {remote_path} naar {local_path}")
            local_path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(remote_path, local_path)

        return cls.from_file(local_path, mask)

    def for_geometry(self, other_gdf: gpd.GeoDataFrame) -> gpd.GeoSeries:
        """
        Returns bodemkaart codes voor de gegeven geometrie
        """
        assert "geometry" in other_gdf.columns
        bodemtypen_per_index = gpd.sjoin(
            other_gdf, self.gdf, how="left", predicate="within"
        ).bodem
        # Vlakken kunnen meer dan 1 bodemtype krijgen, die gevallen moeten gecombineerd worden
        bodemtypen_per_index = bodemtypen_per_index.groupby(
            bodemtypen_per_index.index
        ).apply(lambda bodemtypen: [bodemtype for bodemtype in bodemtypen])
        return bodemtypen_per_index
