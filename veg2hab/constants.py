from pkg_resources import resource_filename

# locaties van de meegepackagde bestanden
TOOLBOX_PYT_PATH = resource_filename("veg2hab", "package_data/veg2hab.pyt")
FGR_PATH = resource_filename("veg2hab", "package_data/FGR.json")
OUDE_BOSSENKAART_PATH = resource_filename("veg2hab", "package_data/Oudebossen.gpkg")
WWL_PATH = resource_filename("veg2hab", "package_data/opgeschoonde_waswordt.xlsx")
DEFTABEL_PATH = resource_filename(
    "veg2hab", "package_data/opgeschoonde_definitietabel.xlsx"
)


# checksums van bestanden die op github staan
LBK_CHECKSUM = "93c584abab7199588141c2c184d1bd60"
BODEMKAART_CHECKSUM = "0db8d5877a119700049db582547ef261"
