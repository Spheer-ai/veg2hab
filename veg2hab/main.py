from textwrap import dedent

import geopandas as gpd
from pkg_resources import resource_filename

from veg2hab.definitietabel import DefinitieTabel
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
    wwl_filepath = resource_filename(
        "veg2hab", "package_data/opgeschoonde_waswordt.xlsx"
    )
    wwl = WasWordtLijst.from_excel(wwl_filepath)

    def_filepath = resource_filename(
        "veg2hab", "package_data/opgeschoonde_definitietabel.xlsx"
    )
    deftabel = DefinitieTabel.from_excel(def_filepath)

    kartering = Kartering.from_shapefile(
        shape_path=params.shapefile,
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

    kartering.apply_wwl(wwl)

    kartering.apply_deftabel(deftabel)

    final_format = kartering.as_final_format()

    Interface.get_instance().output_shapefile("output_name", final_format)
