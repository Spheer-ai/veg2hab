import logging
from pathlib import Path
from textwrap import dedent

import geopandas as gpd
from pkg_resources import resource_filename

from veg2hab.definitietabel import DefinitieTabel
from veg2hab.fgr import FGR
from veg2hab.io.common import InputParameters, Interface
from veg2hab.vegkartering import Kartering
from veg2hab.waswordtlijst import WasWordtLijst


def installation_instructions():
    data_file_path = resource_filename("veg2hab", "package_data/toolbox.pyt")
    print(
        dedent(
            f"""
    To install the veg2hab toolbox, go to add Python toolbox in ArcGIS Pro and select the file at the following location:
        {data_file_path}
"""
        )
    )


def run(params: InputParameters):
    logging.info(f"Starting veg2hab met input parameters: {params.json()}")

    wwl_filepath = resource_filename(
        "veg2hab", "package_data/opgeschoonde_waswordt.xlsx"
    )
    wwl = WasWordtLijst.from_excel(wwl_filepath)

    logging.info(f"WasWordtLijst is ingelezen van {wwl_filepath}")

    def_filepath = resource_filename(
        "veg2hab", "package_data/opgeschoonde_definitietabel.xlsx"
    )
    deftabel = DefinitieTabel.from_excel(def_filepath)

    logging.info(f"Definitietabel is ingelezen van {def_filepath}")

    fgr = FGR(Path(resource_filename("veg2hab", "package_data/FGR.json")))

    logging.info(f"FGR is ingelezen")

    filename = Interface.get_instance().shape_id_to_filename(params.shapefile)

    logging.info(
        f"Tijdelijke versie van {params.shapefile} is opgeslagen in {filename}"
    )

    kartering = Kartering.from_shapefile(
        shape_path=filename,
        ElmID_col=params.ElmID_col,
        vegtype_col_format=params.vegtype_col_format,
        sbb_of_vvn=params.sbb_of_vvn,
        datum_col=params.datum_col,
        opmerking_col=params.opmerking_col,
        SBB_col=params.SBB_col,
        VvN_col=params.VvN_col,
        split_char=params.split_char,
        perc_col=params.perc_col,
    )

    logging.info(f"Vegetatie kartering is succesvol ingelezen")

    kartering.apply_wwl(wwl)

    logging.info(f"Was wordt lijst is toegepast op de vegetatie kartering")

    kartering.apply_deftabel(deftabel)

    logging.info(f"Definitietabel is toegepast op de vegetatie kartering")

    kartering.check_mitsen(fgr)

    logging.info(f"Mitsen zijn gecheckt")

    final_format = kartering.as_final_format()

    logging.info("Omzetting is successvol, wordt nu weggeschreven naar .gpkg")

    Interface.get_instance().output_shapefile("output_name", final_format)