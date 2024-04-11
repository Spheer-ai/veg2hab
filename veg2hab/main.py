from pathlib import Path
from textwrap import dedent

from pkg_resources import resource_filename
from pydantic import BaseModel, Field
from pydantic.fields import ModelField
from typing_extensions import Literal

from veg2hab.definitietabel import DefinitieTabel
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


def run():
    wwl_filepath = resource_filename(
        "veg2hab", "package_data/opgeschoonde_waswordt.xlsx"
    )
    wwl = WasWordtLijst.from_excel(wwl_filepath)

    def_filepath = resource_filename(
        "veg2hab", "package_data/opgeschoonde_definitietabel.xlsx"
    )
    deftabel = DefinitieTabel.from_excel(def_filepath)

    kartering = Kartering.from_shapefile(
        shp_path,
        "elmid",
        vegtype_col_format="single",
        sbb_of_vvn="sbb",
        SBB_col="SBBTYPE",
        split_char="+",
    ).gdf


if __name__ == "__main__":
    run()
