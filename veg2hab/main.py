import logging
from pathlib import Path
from textwrap import dedent
from typing import Union

import geopandas as gpd
import pandas as pd

import veg2hab
from veg2hab import constants
from veg2hab.bronnen import FGR, LBK, Bodemkaart, OudeBossenkaart, get_datadir
from veg2hab.definitietabel import DefinitieTabel
from veg2hab.io.common import (
    AccessDBInputs,
    ApplyDefTabelInputs,
    ApplyFunctioneleSamenhangInputs,
    ApplyMozaiekInputs,
    Interface,
    ShapefileInputs,
    StackVegKarteringInputs,
)
from veg2hab.vegkartering import Kartering
from veg2hab.waswordtlijst import WasWordtLijst


def installatie_instructies():
    print(
        dedent(
            f"""
    Om veg2hab te kunnen draaien, moet de veg2hab toolbox geïnstalleerd worden in ArcGIS Pro.
    Ga naar "add Python toolbox" in ArcGIS Pro en selecteer het bestand op de volgende locatie:
        {constants.TOOLBOX_PYT_PATH}
"""
        )
    )


def bronbestanden():
    print(
        dedent(
            f"""
    Om veg2hab te kunnen draaien, worden de volgende bestanden gebruikt.
    De eerste vier zijn altijd aanwezig en de laatste twee worden van github gedownload,
    wanneer veg2hab voor het eerst gedraaid wordt. Mogelijk zijn deze dus nog niet beschikbaar.
    - WasWordtLijst: {constants.WWL_PATH}
    - Definitietabel: {constants.DEFTABEL_PATH}
    - FGR: {constants.FGR_PATH}
    - Oude bossenkaart: {constants.OUDE_BOSSENKAART_PATH}
    - Bodemkaart: {get_datadir("veg2hab", "data") / "lbk.gpkg"}
    - LBK: {get_datadir("veg2hab", "data") / "bodemkaart.gpkg"}
    """
        )
    )


def run(
    params: Union[
        AccessDBInputs,
        ShapefileInputs,
        StackVegKarteringInputs,
        ApplyDefTabelInputs,
        ApplyMozaiekInputs,
        ApplyFunctioneleSamenhangInputs,
    ]
):
    logging.info(f"Huidige veg2hab versie: {veg2hab.__version__}")
    logging.info(f"Starting veg2hab met input parameters: {params.json()}")

    if isinstance(params, (AccessDBInputs, ShapefileInputs)):
        return run_1_inladen_vegkartering(params)
    elif isinstance(params, StackVegKarteringInputs):
        return run_2_stack_vegkartering(params)
    elif isinstance(params, ApplyDefTabelInputs):
        return run_3_definitietabel_en_mitsen(params)
    elif isinstance(params, ApplyMozaiekInputs):
        return run_4_mozaiekregels(params)
    elif isinstance(params, ApplyFunctioneleSamenhangInputs):
        return run_5_functionele_samenhang_en_min_opp(params)
    else:
        raise TypeError("INvalid input parameter")


def run_1_inladen_vegkartering(params: Union[AccessDBInputs, ShapefileInputs]):
    filename = Interface.get_instance().shape_id_to_filename(params.shapefile)

    if filename != params.shapefile:
        logging.info(
            f"Tijdelijke versie van {params.shapefile} is opgeslagen in {filename}"
        )

    if isinstance(params, AccessDBInputs):
        kartering = Kartering.from_access_db(
            shape_path=filename,
            shape_elm_id_column=params.elmid_col,
            access_mdb_path=params.access_mdb_path,
            welke_typologie=params.welke_typologie,
            opmerkingen_column=params.opmerking_col,
            datum_column=params.datum_col,
        )
    elif isinstance(params, ShapefileInputs):
        kartering = Kartering.from_shapefile(
            shape_path=filename,
            ElmID_col=params.elmid_col,
            vegtype_col_format=params.vegtype_col_format,
            welke_typologie=params.welke_typologie,
            datum_col=params.datum_col,
            opmerking_col=params.opmerking_col,
            SBB_col=params.sbb_col,
            VvN_col=params.vvn_col,
            rVvN_col=params.rvvn_col,
            split_char=params.split_char,
            perc_col=params.perc_col,
            lok_vegtypen_col=params.lok_vegtypen_col,
        )
    else:
        raise RuntimeError("Something went wrong with the input parameters")

    logging.info(f"Vegetatie kartering is succesvol ingelezen")

    wwl = WasWordtLijst.from_excel(Path(constants.WWL_PATH))

    logging.info(f"WasWordtLijst is ingelezen van {constants.WWL_PATH}")

    kartering.apply_wwl(wwl)

    logging.info(f"Was wordt lijst is toegepast op de vegetatie kartering")

    gdf_vegkart = kartering.to_editable_vegtypes()
    Interface.get_instance().output_shapefile(params.output, gdf_vegkart)


def run_2_stack_vegkartering(params: StackVegKarteringInputs):
    gpkg_files = []

    for single_shapefile in params.shapefile:
        newfilename = Interface.get_instance().shape_id_to_filename(single_shapefile)
        gpkg_files.append(newfilename)

        if newfilename != single_shapefile:
            logging.info(
                f"Tijdelijke versie van {single_shapefile} is opgeslagen in {newfilename}"
            )

    karteringen = []

    for gpkg in gpkg_files:
        karteringen.append(Kartering.from_editable_vegtypes(gpd.read_file(gpkg)))

    logging.info("Karteringen zijn succesvol ingelezen")

    # Lijst reversen zodat de 'bovenste' kartering aan het einde komt
    karteringen.reverse()

    gdf_vegkart = Kartering.combineer_karteringen(karteringen).to_editable_vegtypes()

    logging.info("Karteringen zijn succesvol gestacked")

    Interface.get_instance().output_shapefile(params.output, gdf_vegkart)


def run_3_definitietabel_en_mitsen(params: ApplyDefTabelInputs):
    filename = Interface.get_instance().shape_id_to_filename(params.shapefile)

    if filename != params.shapefile:
        logging.info(
            f"Tijdelijke versie van {params.shapefile} is opgeslagen in {filename}"
        )

    kartering = Kartering.from_editable_vegtypes(gpd.read_file(filename))

    logging.info("Kartering is succesvol ingelezen")

    deftabel = DefinitieTabel.from_excel(Path(constants.DEFTABEL_PATH))
    deftabel.set_override_dict(params.as_override_dict())

    logging.info(f"Definitietabel is ingelezen van {constants.DEFTABEL_PATH}")

    kartering.apply_deftabel(deftabel)

    logging.info(f"Definitietabel is toegepast op de vegetatie kartering")

    fgr = FGR(Path(constants.FGR_PATH))

    logging.info(f"FGR is ingelezen van {constants.FGR_PATH}")

    mask = kartering.get_geometry_mask()

    bodemkaart = Bodemkaart.from_github(mask=mask)

    logging.info(f"Bodemkaart is ingelezen")

    lbk = LBK.from_github(mask=mask)

    logging.info(f"LBK is ingelezen")

    obk = OudeBossenkaart(Path(constants.OUDE_BOSSENKAART_PATH))

    logging.info(f"Oude bossenkaart is ingelezen van {constants.OUDE_BOSSENKAART_PATH}")

    kartering.bepaal_mits_habitatkeuzes(
        fgr,
        bodemkaart,
        lbk,
        obk,
    )

    logging.info(f"Mitsen zijn gecheckt")

    gdf_habkart = kartering.to_editable_habtypes()
    Interface.get_instance().output_shapefile(params.output, gdf_habkart)


def run_4_mozaiekregels(params: ApplyMozaiekInputs):
    filename = Interface.get_instance().shape_id_to_filename(params.shapefile)

    if filename != params.shapefile:
        logging.info(
            f"Tijdelijke versie van {params.shapefile} is opgeslagen in {filename}"
        )

    kartering = Kartering.from_editable_habtypes(gpd.read_file(filename))

    logging.info("Kartering is succesvol ingelezen")

    kartering.bepaal_mozaiek_habitatkeuzes()

    logging.info(f"Mozaiekregels zijn gecheckt")

    gdf_habkart = kartering.to_editable_habtypes()
    Interface.get_instance().output_shapefile(params.output, gdf_habkart)


def run_5_functionele_samenhang_en_min_opp(params: ApplyFunctioneleSamenhangInputs):
    filename = Interface.get_instance().shape_id_to_filename(params.shapefile)

    if filename != params.shapefile:
        logging.info(
            f"Tijdelijke versie van {params.shapefile} is opgeslagen in {filename}"
        )

    kartering = Kartering.from_editable_habtypes(gpd.read_file(filename))

    logging.info("Kartering is succesvol ingelezen")

    kartering.functionele_samenhang()

    logging.info(f"Functionele samenhang en minimum oppervlakken zijn gecheckt")

    final_format = kartering.as_final_format()

    logging.info("Omzetting is successvol, wordt nu weggeschreven naar een geopackage")

    Interface.get_instance().output_shapefile(params.output, final_format)
