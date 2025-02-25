from importlib.resources import as_file, files

# locaties van de meegepackagde bestanden
TOOLBOX_PYT_PATH = str(files("veg2hab") / "package_data/veg2hab.pyt")
FGR_PATH = str(files("veg2hab") / "package_data/FGR.json")
OUDE_BOSSENKAART_PATH = str(files("veg2hab") / "package_data/Oudebossen.gpkg")
WWL_PATH = str(files("veg2hab") / "package_data/opgeschoonde_waswordt.xlsx")
DEFTABEL_PATH = str(files("veg2hab") / "package_data/opgeschoonde_definitietabel.xlsx")

# checksums van bestanden die op github staan
LBK_CHECKSUM = "93c584abab7199588141c2c184d1bd60"
BODEMKAART_CHECKSUM = "0db8d5877a119700049db582547ef261"
