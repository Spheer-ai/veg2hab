import logging

import click

import veg2hab
from veg2hab import main
from veg2hab.io.cli import (
    CLIAccessDBInputs,
    CLIApplyDefTabelInputs,
    CLIApplyFunctioneleSamenhangInputs,
    CLIApplyMozaiekInputs,
    CLIInterface,
    CLIShapefileInputs,
    CLIStackVegKarteringInputs,
)


@click.group()
@click.version_option(veg2hab.__version__)
@click.option(
    "-v", "--verbose", count=True, help="Increase verbosity, use -vv for debug info"
)
def veg2hab(verbose: int):
    """Veg2Hab: een toolbox voor het omzetten van vegetatiekarteringen naar habitatkaarten.

    De toolbox bestaat uit de volgende stappen:

        1. Inladen van een vegetatiekartering

        2. Optioneel: stapel verschillende vegetatiekarteringen

        3. Definitie tabel en mitsen, inclusief FGR, LBK en Bodemkaart

        4. Mozaiekregels

        5. Functionele samenhange en minimum oppervlak

    Tussentijds kunnen handmatig aanpassingen worden gedaan.
    """
    if verbose == 0:
        log_level = logging.WARNING
    elif verbose == 1:
        log_level = logging.INFO
    else:
        log_level = logging.DEBUG

    CLIInterface.get_instance().instantiate_loggers(log_level)


@veg2hab.command(
    name=CLIAccessDBInputs.label,
    help=CLIAccessDBInputs.get_argument_description(),
)
@CLIAccessDBInputs.click_decorator
def _1a_digitale_standaard(**kwargs):
    params = CLIAccessDBInputs(**kwargs)
    main.run(params)


@veg2hab.command(
    name=CLIShapefileInputs.label,
    help=CLIShapefileInputs.get_argument_description(),
)
@CLIShapefileInputs.click_decorator
def _1b_vector_bestand(**kwargs):
    params = CLIShapefileInputs(**kwargs)
    main.run(params)


@veg2hab.command(
    name=CLIStackVegKarteringInputs.label,
    help=CLIStackVegKarteringInputs.get_argument_description(),
)
@CLIStackVegKarteringInputs.click_decorator
def _2_optioneel_stapel_veg_kart(**kwargs):
    params = CLIStackVegKarteringInputs(**kwargs)
    main.run(params)


@veg2hab.command(
    name=CLIApplyDefTabelInputs.label,
    help=CLIApplyDefTabelInputs.get_argument_description(),
)
@CLIApplyDefTabelInputs.click_decorator
def _3_definitie_tabel_en_mitsen(**kwargs):
    params = CLIApplyDefTabelInputs(**kwargs)
    main.run(params)


@veg2hab.command(
    name=CLIApplyMozaiekInputs.label,
    help=CLIApplyMozaiekInputs.get_argument_description(),
)
@CLIApplyMozaiekInputs.click_decorator
def _4_mozaiekregels(**kwargs):
    params = CLIApplyMozaiekInputs(**kwargs)
    main.run(params)


@veg2hab.command(
    name=CLIApplyFunctioneleSamenhangInputs.label,
    help=CLIApplyFunctioneleSamenhangInputs.get_argument_description(),
)
@CLIApplyFunctioneleSamenhangInputs.click_decorator
def _5_functionele_samenhang(**kwargs):
    params = CLIApplyFunctioneleSamenhangInputs(**kwargs)
    main.run(params)


if __name__ == "__main__":
    # Dit zorgt ervoor dat veg2hab als volgt aangeroepen kan worden:
    # python -m veg2hab <command>
    # veg2hab()

    # TODO remove
    CLIInterface.get_instance().instantiate_loggers(logging.INFO)
    _2_optioneel_stapel_veg_kart(["veg_kart.gpkg", "veg_kart.gpkg"])
