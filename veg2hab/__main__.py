import logging
import subprocess
from pathlib import Path

import click

import veg2hab
from veg2hab import constants
from veg2hab.definitietabel import opschonen_definitietabel
from veg2hab.io.cli import AccessDBInputs, CLIInterface, ShapefileInputs
from veg2hab.waswordtlijst import opschonen_waswordtlijst


@click.group(name="veg2hab")
@click.version_option(veg2hab.__version__)
@click.option("-v", "--verbose", count=True)
def main(verbose: int):
    if verbose == 0:
        log_level = logging.WARNING
    elif verbose == 1:
        log_level = logging.INFO
    else:
        log_level = logging.DEBUG

    CLIInterface.get_instance().instantiate_loggers(log_level)


@main.command(
    name=AccessDBInputs.label,
    help=AccessDBInputs.description,
)
def digitale_standaard():
    pass


@main.command(
    name=ShapefileInputs.label,
    help=ShapefileInputs.description,
)
def vector_bestand():
    """"""
    pass


@click.group()
def veg2hab_internal():
    """Used for checking versions and preparing the python release."""


@veg2hab_internal.command()
def check_versions():
    """Check that the versions in poetry, toolbox.py and __version__ match"""
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

    top_level_namespace = runpy.run_path(constants.TOOLBOX_PYT_PATH)

    if poetry_version not in top_level_namespace["SUPPORTED_VERSIONS"]:
        raise ValueError(
            f"Version {poetry_version} is not in {top_level_namespace['SUPPORTED_VERSIONS']}"
        )


@veg2hab_internal.command()
def create_package_data():
    path_in_wwl = (
        Path(__file__).parent
        / ".."
        / "data"
        / "5. Was-wordt-lijst-vegetatietypen-en-habitattypen-09-02-2021.xlsx"
    )
    path_out_wwl = Path(__file__).parent / "package_data" / "opgeschoonde_waswordt.xlsx"
    opschonen_waswordtlijst(path_in_wwl, path_out_wwl)

    path_in_dt = (
        Path(__file__).parent
        / ".."
        / "data"
        / "definitietabel habitattypen (versie 24 maart 2009)_0.xls"
    )
    path_in_mitsjson = Path(__file__).parent / ".." / "data" / "mitsjson.csv"
    path_in_mozaiekjson = Path(__file__).parent / ".." / "data" / "mozaiekjson.csv"
    path_out_dt = (
        Path(__file__).parent / "package_data" / "opgeschoonde_definitietabel.xlsx"
    )
    opschonen_definitietabel(
        path_in_dt, path_in_mitsjson, path_in_mozaiekjson, path_out_dt
    )


if __name__ == "__main__":
    check_versions()
