import hashlib
import logging
import sys
import urllib.request
from pathlib import Path
from typing import Optional

import geopandas as gpd
import pandas as pd
from typing_extensions import Self

import veg2hab.constants
from veg2hab.enums import FGRType, OBKWaarden

# TODO: Op het moment doen we bij sjoin predicate "within", zodat karteringvlakken die niet volledig
#       binnen een bronvlak liggen NaN krijgen. Beter zou zijn dat ze alles krijgen waar ze op liggen, en als
#       dat steeds dezelfde is, het karteringvlak alsnog dat type krijgt. Dit kan voorkomen bij LBK en bij
#       de bodemkaart, omdat hier regelmatig vlakken met dezelfde typering toch naast elkaar liggen, omdat ze
#       verschillen in zaken waar wij niet naar kijken. Het kan ook zijn dat 1 vlak in 2 bronvlakken ligt, en
#       dat beide bronvlakken andere typeringen hebben die toch onder dezelfde categorie vallen.


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


def sjoin_largest_overlap(
    kartering_gdf: gpd.GeoDataFrame, bron_gdf: gpd.GeoDataFrame, bron_col_name: str
) -> gpd.GeoDataFrame:
    """
    Zoekt voor elk karteringvlak de bronvlakken waar het het meeste mee overlapt.

    Geeft een geodataframe terug met daarin voor ieder vlak in kartering_gdf
    de info uit bron_gdf waar het het meeste mee overlapt (in kolom bron_col_name)
    en het percentage van het karteringvlak dat overlapt met het bronvlak.
    """
    assert (
        bron_col_name in bron_gdf.columns
    ), f"Kolom {bron_col_name} moet in bron_gdf zitten"
    # assert index is unique
    assert len(kartering_gdf.index) == len(
        kartering_gdf.index.unique()
    ), "Index moet uniek zijn"
    if bron_col_name in kartering_gdf.columns:
        kartering_gdf = kartering_gdf.drop(columns=[bron_col_name])

    # Extra kolom met de geometry zodat deze blijft bestaan na de sjoin
    bron_gdf["geometry_bron"] = bron_gdf["geometry"]

    joined = gpd.sjoin(kartering_gdf, bron_gdf, how="left", predicate="intersects")
    joined["overlap_area"] = joined.geometry.intersection(joined.geometry_bron).area

    def _retain_largest_overlap_area_row(group):
        assert len(group) > 0, "Group mag niet leeg zijn"

        # Als er maar 1 is hoeven we niks te doen
        if len(group) == 1:
            return group

        highest_overlap_area = group["overlap_area"].max()
        # Enkel de eerste teruggeven voor het geval er meerdere met dezelfde area zijn
        if len(group[group["overlap_area"] == highest_overlap_area]) > 1:
            logging.warning(
                f"Meerdere bronvlakken met dezelfde overlap area gevonden; alleen de eerste wordt gebruikt"
            )
        return group[group["overlap_area"] == highest_overlap_area].iloc[[0]]

    # Groupby index, zodat we groepen maken per karteringvlak
    grouped = joined.groupby(level=0, group_keys=False)
    only_largest_overlaps = grouped.apply(_retain_largest_overlap_area_row)
    only_largest_overlaps[f"{bron_col_name}_percentage"] = (
        only_largest_overlaps["overlap_area"]
        / only_largest_overlaps["geometry"].area
        * 100
    )

    bron_gdf = bron_gdf.drop(columns=["geometry_bron"])

    assert len(only_largest_overlaps) == len(
        kartering_gdf
    ), "DF met bronvlakcodes moet even lang zijn als de kartering_gdf"

    return only_largest_overlaps[[bron_col_name, f"{bron_col_name}_percentage"]]


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
        local_path = get_datadir("veg2hab", "data") / "lbk.gpkg"
        remote_path = f"https://github.com/Spheer-ai/veg2hab/releases/download/v{veg2hab.__version__}/lbk.gpkg"

        if (
            not local_path.is_file()
            or get_checksum(local_path) != veg2hab.constants.LBK_CHECKSUM
        ):
            logging.warning(
                "Lokale versie LBK komt niet overeen of bestaat nog niet. Downloaden van github kan enkele minuten duren. Even geduld aub."
            )
            logging.debug(f"Download LBK van {remote_path} naar {local_path}")
            local_path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(remote_path, local_path)

        return cls.from_file(local_path, mask)

    def for_geometry(self, other_gdf: gpd.GeoDataFrame) -> gpd.GeoSeries:
        """
        Returns LBK codes voor de gegeven geometrie
        """
        assert "geometry" in other_gdf.columns
        return sjoin_largest_overlap(other_gdf, self.gdf, "lbk")


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
        return sjoin_largest_overlap(other_gdf, self.gdf, "fgr")


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
        # Samenvoegen meerdere bodemtypen voor 1 vlak/maparea_id
        soil_units_table = (
            soil_units_table.groupby("maparea_id")["soilunit_code"]
            .apply(list)
            .reset_index()
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
        return sjoin_largest_overlap(other_gdf, self.gdf, "bodem")


class OudeBossenkaart:
    def __init__(self, path: Path, mask: Optional[gpd.GeoDataFrame] = None):
        self.gdf = gpd.read_file(path, mask=mask, include_fields=["h9120", "h9190"])

        # Validatie van de waarden gebeurt in het instantieren van OBKWaarden
        self.gdf["obk"] = self.gdf.apply(
            lambda row: OBKWaarden(H9120=row.h9120, H9190=row.h9190), axis=1
        )
        self.gdf = self.gdf.drop(columns=["h9120", "h9190"])

    def for_geometry(self, other_gdf: gpd.GeoDataFrame) -> gpd.GeoSeries:
        """
        Returns oude bossenkaart codes voor de gegeven geometrie
        """
        assert "geometry" in other_gdf.columns
        return sjoin_largest_overlap(other_gdf, self.gdf, "obk")
