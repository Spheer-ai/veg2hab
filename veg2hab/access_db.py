import enum
import functools
import os.path
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path
from typing import Any, Dict, Tuple, Union

import pandas as pd
import pyodbc

from veg2hab.enums import WelkeTypologie
from veg2hab.vegetatietypen import SBB, rVvN
from veg2hab.vegtypeinfo import VegTypeInfo


class TableNames(enum.Enum):
    ELEMENT = "Element"
    KARTERINGVEGETATIETYPE = "KarteringVegetatietype"
    VEGETATIETYPE = "VegetatieType"
    SBBTYPE = "SbbType"


def connect_to_access(filename: str) -> pyodbc.Connection:
    conn_str = r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};" f"DBQ={filename};"
    return pyodbc.connect(conn_str)


def list_tables(conn: pyodbc.Connection):
    with conn.cursor() as cursor:
        return [i.table_name for i in cursor.tables(tableType="Table")]


@functools.singledispatch
def read_table(
    location, table_name: TableNames, col_names: Dict[str, Any]
) -> pd.DataFrame:
    """Read a table from the access_db"""
    raise NotImplementedError(f"invalide {location}")


@read_table.register
def _(
    conn: pyodbc.Connection, table_name: TableNames, col_names: Dict[str, Any]
) -> pd.DataFrame:
    # the pyodb is not officially suppported by pandas, so we suppress that
    # warning:
    with warnings.catch_warnings():
        warnings.simplefilter(action="ignore", category=UserWarning)
        return pd.read_sql(
            f"SELECT {','.join(col_names.keys())} FROM {table_name.value}",
            conn,
            columns=col_names.keys(),
        ).astype(col_names)


@read_table.register
def _(folder: Path, table_name: TableNames, col_names: Dict[str, Any]) -> pd.DataFrame:
    return pd.read_csv(
        folder / f"{table_name.value}.csv",
        usecols=list(col_names.keys()),
        dtype=col_names,
    )


def _unpack_access_db(access_db_path: str, output_folder: Path):
    assert output_folder.is_dir()
    try:
        subprocess.run(
            ["mdb-export", "--version"],
            check=True,
        )
    except Exception as e:
        raise RuntimeError(
            "mdb-export moet geinstalleerd zijn om .mdb bestanden in te lezen"
        ) from e

    for table_name in TableNames:
        try:
            outputs = subprocess.run(
                [
                    "mdb-export",
                    str(access_db_path),
                    table_name.value,
                ],
                check=True,
                capture_output=True,
            )

            with open(output_folder / f"{table_name.value}.csv", "wb") as f:
                f.write(outputs.stdout)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Er is iets fout gegaan bij het uitpakken van de access database: {e.stderr.decode()}"
            ) from e


def _group_lokale_vegtypen_en_bedekking_to_str(rows: pd.DataFrame) -> str:
    """
    Ontvangt een setje rijen van 1 locatie (vlak) met lokale vegetatietypen en bedekkingspercentages.
    Hier wordt een string van gemaakt uiteindelijk in de output komt zonder verdere bewerkingen.
    """
    assert all(
        col in rows.columns for col in ["Locatie", "Vegetatietype", "Bedekking_num"]
    ), "Locatie, Vegetatietype en Bedekking_num moeten kolommen zijn in _group_lokale_vegtypen_en_bedekking_to_str"

    assert (
        rows["Locatie"].nunique() == 1
    ), "_group_lokale_vegtypen_en_bedekking_to_str moet op een groupby over Locatie uitgevoerd worden; nu is locatie niet hetzelfde in 1 group"

    return_strings = [
        f"{row['Vegetatietype']} ({row['Bedekking_num']}%)"
        for _, row in rows.iterrows()
    ]
    return ", ".join(return_strings)


def read_access_tables(
    acces_mdb: Path, welke_typologie: "WelkeTypologie"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Read the tables from the access database and return them as pandas dataframes"""

    if not acces_mdb.is_file() and not acces_mdb.suffix == ".mdb":
        raise ValueError("Geen geldige access database, verwacht een .mdb bestand.")

    assert welke_typologie in [
        WelkeTypologie.SBB,
        WelkeTypologie.rVvN,
    ], "Accesskarteringen zijn of SBB, of rVvN."

    if sys.platform == "win32":
        temp_dir = None
        locatie: Union[pyodbc.Connection, Path] = connect_to_access(acces_mdb)
    elif sys.platform.startswith("linux"):
        temp_dir = tempfile.TemporaryDirectory()
        locatie: Union[pyodbc.Connection, Path] = Path(temp_dir.name)
        _unpack_access_db(acces_mdb, locatie)

    element = read_table(
        locatie,
        TableNames.ELEMENT,
        {"ElmID": int, "intern_id": int, "Locatietype": str},
    )
    # Uitfilteren van lijnen, selecteer alleen vlakken
    element["Locatietype"] = element["Locatietype"].str.lower()
    element = element[element.Locatietype == "v"][["ElmID", "intern_id"]]

    kart_veg = read_table(
        locatie,
        TableNames.KARTERINGVEGETATIETYPE,
        {"Locatie": int, "Vegetatietype": str, "Bedekking_num": int},
    )
    # BV voor GM2b -> Gm2b (elmid 10219 in ruitenaa2020)
    kart_veg.Vegetatietype = kart_veg.Vegetatietype.str.lower()

    vegetatietype = read_table(
        locatie,
        TableNames.VEGETATIETYPE,
        {"Code": str, "SbbType": int},
    )
    vegetatietype.Code = vegetatietype.Code.str.lower()

    vegtype = read_table(
        locatie,
        TableNames.SBBTYPE,
        {"Cata_ID": int, "Code": str},
    )
    # Code hernoemen want er zit al een "Code" in Vegetatietype.csv
    vegtype = vegtype.rename(columns={"Code": "vegtype"})

    # SBB code toevoegen aan KarteringVegetatietype
    kart_veg = kart_veg.merge(
        vegetatietype,
        left_on="Vegetatietype",
        right_on="Code",
        how="left",
        validate="many_to_one",
    )
    kart_veg = kart_veg.merge(
        vegtype,
        left_on="SbbType",
        right_on="Cata_ID",
        how="left",
        validate="many_to_one",
    )

    # Opschonen vegtypen
    if welke_typologie == WelkeTypologie.SBB:
        kart_veg["vegtype"] = SBB.opschonen_series(kart_veg["vegtype"])
    elif welke_typologie == WelkeTypologie.rVvN:
        kart_veg["vegtype"] = rVvN.opschonen_series(kart_veg["vegtype"])

    # Groeperen van alle verschillende vegtypen per Locatie
    grouped_kart_veg = (
        kart_veg.groupby("Locatie")
        .apply(
            VegTypeInfo.create_vegtypen_list_from_access_rows,
            welke_typologie=welke_typologie,
            perc_col="Bedekking_num",
            vegtype_col="vegtype",
        )
        .reset_index(name="VegTypeInfo")
    )

    lokale_vegtypen = (
        kart_veg.groupby("Locatie")
        .apply(_group_lokale_vegtypen_en_bedekking_to_str)
        .reset_index(name="_LokVegTyp")
    )

    grouped_kart_veg = grouped_kart_veg.merge(lokale_vegtypen, on="Locatie")

    if temp_dir:
        temp_dir.cleanup()

    return element, grouped_kart_veg
