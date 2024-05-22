import logging
from pathlib import Path
from textwrap import dedent
from typing import Union

import geopandas as gpd

from veg2hab import constants
from veg2hab.definitietabel import DefinitieTabel
from veg2hab.fgr import FGR
from veg2hab.io.common import AccessDBInputs, Interface, ShapefileInputs
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


def run(params: Union[AccessDBInputs, ShapefileInputs]):
    logging.info(f"Starting veg2hab met input parameters: {params.json()}")

    wwl = WasWordtLijst.from_excel(Path(constants.WWL_PATH))

    logging.info(f"WasWordtLijst is ingelezen van {constants.WWL_PATH}")

    deftabel = DefinitieTabel.from_excel(Path(constants.DEFTABEL_PATH))

    logging.info(f"Definitietabel is ingelezen van {constants.DEFTABEL_PATH}")

    fgr = FGR(Path(constants.FGR_PATH))

    logging.info(f"FGR is ingelezen van {constants.FGR_PATH}")

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
            opmerkingen_column=params.opmerking_col,
            datum_column=params.datum_col,
        )
    elif isinstance(params, ShapefileInputs):
        kartering = Kartering.from_shapefile(
            shape_path=filename,
            ElmID_col=params.elmid_col,
            vegtype_col_format=params.vegtype_col_format,
            sbb_of_vvn=params.sbb_of_vvn,
            datum_col=params.datum_col,
            opmerking_col=params.opmerking_col,
            SBB_col=params.sbb_col,
            VvN_col=params.vvn_col,
            split_char=params.split_char,
            perc_col=params.perc_col,
            lok_vegtypen_col=params.lok_vegtypen_col,
        )
    else:
        raise RuntimeError("Something went wrong with the input parameters")

    logging.info(f"Vegetatie kartering is succesvol ingelezen")

    kartering.apply_wwl(wwl)

    logging.info(f"Was wordt lijst is toegepast op de vegetatie kartering")

    kartering.apply_deftabel(deftabel)

    logging.info(f"Definitietabel is toegepast op de vegetatie kartering")

    kartering.bepaal_habitatkeuzes(fgr)

    logging.info(f"Mitsen zijn gecheckt")

    final_format = kartering.as_final_format()

    logging.info("Omzetting is successvol, wordt nu weggeschreven naar een geopackage")

    Interface.get_instance().output_shapefile(params.output, final_format)
