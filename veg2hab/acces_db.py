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

# __all__ = ["read_access_tables"]


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
def read_table(location, table_name: str, col_names: Dict[str, Any]) -> pd.DataFrame:
    """Read a table from the access_db"""
    pass


@read_table.register
def _(
    conn: pyodbc.Connection, table_name: str, col_names: Dict[str, Any]
) -> pd.DataFrame:
    # the pyodb is not officially suppported by pandas, so we suppress that
    # warning:
    with warnings.catch_warnings():
        warnings.simplefilter(action="ignore", category=UserWarning)
        return pd.read_sql(
            f"SELECT {','.join(col_names.keys())} FROM {table_name}",
            conn,
            dtype=col_names,
        )


@read_table.register
def _(folder: Path, table_name: str, col_names: Dict[str, Any]) -> pd.DataFrame:
    # the pyodb is not officially suppported by pandas, so we suppress that
    # warning:
    return pd.read_csv(
        folder / f"{table_name}.csv",
        usecols=list(col_names.keys()),
        dtype=col_names,
    )


def unpack_access_db(access_db_path: str, output_folder: Path):
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


def read_access_tables(acces_mdb: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Read the tables from the access database and return them as pandas dataframes"""
    # TODO fix circular imports
    from veg2hab.vegetatietypen import SBB as _SBB
    from veg2hab.vegkartering import VegTypeInfo

    if not acces_mdb.is_file() and not acces_mdb.suffix == ".mdb":
        raise ValueError("Geen geldige access database, verwacht een .mdb bestand.")

    if sys.platform == "win32":
        temp_dir = None
        locatie: Union[pyodbc.Connection, Path] = connect_to_access(acces_mdb)
    elif sys.platform.startswith("linux"):
        temp_dir = tempfile.TemporaryDirectory()
        locatie: Union[pyodbc.Connection, Path] = Path(temp_dir.name)
        unpack_access_db(acces_mdb, locatie)

    element = read_table(
        locatie,
        "Element",
        {"ElmID": int, "intern_id": int, "Locatietype": str},
    )
    # Uitfilteren van lijnen, selecteer alleen vlakken
    element["Locatietype"] = element["Locatietype"].str.lower()
    element = element[element.Locatietype == "v"][["ElmID", "intern_id"]]

    kart_veg = read_table(
        locatie,
        "KarteringVegetatietype",
        {"Locatie": int, "Vegetatietype": str, "Bedekking_num": int},
    )
    # BV voor GM2b -> Gm2b (elmid 10219 in ruitenaa2020)
    kart_veg.Vegetatietype = kart_veg.Vegetatietype.str.lower()

    vegetatietype = read_table(
        locatie,
        "VegetatieType",
        {"Code": str, "SbbType": int},
    )
    vegetatietype.Code = vegetatietype.Code.str.lower()

    sbbtype = read_table(
        locatie,
        "SbbType",
        {"Cata_ID": int, "Code": str},
    )
    # Code hernoemen want er zit al een "Code" in Vegetatietype.csv
    sbbtype = sbbtype.rename(columns={"Code": "Sbb"})

    # SBB code toevoegen aan KarteringVegetatietype
    kart_veg = kart_veg.merge(
        vegetatietype, left_on="Vegetatietype", right_on="Code", how="left"
    )
    kart_veg = kart_veg.merge(
        sbbtype, left_on="SbbType", right_on="Cata_ID", how="left"
    )

    # Opschonen SBB codes
    kart_veg["Sbb"] = _SBB.opschonen_series(kart_veg["Sbb"])

    # Groeperen van alle verschillende SBBs per Locatie
    grouped_kart_veg = (
        kart_veg.groupby("Locatie")
        .apply(
            VegTypeInfo.create_vegtypen_list_from_access_rows,
            perc_col="Bedekking_num",
            SBB_col="Sbb",
        )
        .reset_index(name="VegTypeInfo")
    )

    if temp_dir:
        temp_dir.cleanup()

    return element, grouped_kart_veg
