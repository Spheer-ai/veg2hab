#!/usr/bin/env python
import subprocess
from pathlib import Path
from typing import Optional

import click

import veg2hab.constants
from veg2hab.bronnen import get_checksum
from veg2hab.definitietabel import opschonen_definitietabel
from veg2hab.waswordtlijst import opschonen_waswordtlijst


@click.group()
def veg2hab_internal():
    """Used for checking versions and preparing the python release."""


@veg2hab_internal.command()
@click.argument("tag_version", required=False, default=None)
def check_versions(tag_version: Optional[str]):
    """Check that the versions in poetry, toolbox.py and __version__ match"""
    if tag_version is not None:
        if tag_version != f"v{veg2hab.__version__}":
            raise ValueError(
                f"Tag {tag_version} does not match veg2hab.__version__ v{veg2hab.__version__}"
            )

    # get the version of the software from poetry
    poetry_version = (
        subprocess.check_output(["poetry", "version", "--short"])
        .decode("utf-8")
        .strip()
    )

    if poetry_version != veg2hab.__version__:
        raise ValueError(
            f"Versions do not match: {poetry_version} != {veg2hab.__version__}"
        )

    import runpy

    top_level_namespace = runpy.run_path(veg2hab.constants.TOOLBOX_PYT_PATH)

    if poetry_version not in top_level_namespace["SUPPORTED_VERSIONS"]:
        raise ValueError(
            f"Version {poetry_version} is not in {top_level_namespace['SUPPORTED_VERSIONS']}"
        )
    print("Versions are valid")

    # check checksums
    lbk_checksum = get_checksum(
        Path(__file__).parent / "data" / "bronbestanden" / "lbk.gpkg"
    )
    if lbk_checksum != veg2hab.constants.LBK_CHECKSUM:
        raise ValueError(
            f"Checksum of lbk.gpkg does not match, replace veg2hab.constants.LBK_CHECKSUM with:\n{lbk_checksum}"
        )

    bodemkaart_checksum = get_checksum(
        Path(__file__).parent / "data" / "bronbestanden" / "bodemkaart.gpkg"
    )
    if bodemkaart_checksum != veg2hab.constants.BODEMKAART_CHECKSUM:
        raise ValueError(
            f"Checksum of bodemkaart.gpkg does not match, replace veg2hab.constants.BODEMKAART_CHECKSUM with:\n{bodemkaart_checksum}"
        )

    print("Checksums match correctly")


@veg2hab_internal.command()
def create_package_data():
    path_in_wwl = (
        Path(__file__).parent
        / "data"
        / "5. Was-wordt-lijst-vegetatietypen-en-habitattypen-09-02-2021.xlsx"
    )
    path_out_wwl = (
        Path(__file__).parent
        / "veg2hab"
        / "package_data"
        / "opgeschoonde_waswordt.xlsx"
    )
    opschonen_waswordtlijst(path_in_wwl, path_out_wwl)

    path_in_dt = (
        Path(__file__).parent
        / "data"
        / "definitietabel habitattypen (versie 24 maart 2009)_0.xls"
    )
    path_in_mitsjson = Path(__file__).parent / "data" / "mitsjson.csv"
    path_in_mozaiekjson = Path(__file__).parent / "data" / "mozaiekjson.csv"
    path_out_dt = (
        Path(__file__).parent
        / "veg2hab"
        / "package_data"
        / "opgeschoonde_definitietabel.xlsx"
    )
    opschonen_definitietabel(
        path_in_dt, path_in_mitsjson, path_in_mozaiekjson, path_out_dt
    )


if __name__ == "__main__":
    veg2hab_internal()
