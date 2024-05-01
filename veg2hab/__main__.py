import logging
import subprocess
from pathlib import Path

import click

import veg2hab
from veg2hab import constants, main
from veg2hab.definitietabel import opschonen_definitietabel
from veg2hab.io.cli import CLIAccessDBInputs, CLIInterface, CLIShapefileInputs
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
    name=CLIAccessDBInputs.label,
    help=CLIAccessDBInputs.get_argument_description(),
)
@CLIAccessDBInputs.click_decorator
def digitale_standaard(**kwargs):
    params = CLIAccessDBInputs(**kwargs)
    main.run(params)


@main.command(
    name=CLIShapefileInputs.label,
    help=CLIShapefileInputs.get_argument_description(),
)
@CLIShapefileInputs.click_decorator
def vector_bestand(**kwargs):
    params = CLIShapefileInputs(**kwargs)
    main.run(params)


if __name__ == "__main__":
    main()
