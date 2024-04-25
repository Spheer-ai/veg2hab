from pkg_resources import resource_filename

# locaties van de meegepackagde bestanden
TOOLBOX_PYT_PATH = resource_filename("veg2hab", "package_data/toolbox.pyt")
FGR_PATH = resource_filename("veg2hab", "package_data/FGR.json")
WWL_PATH = resource_filename("veg2hab", "package_data/opgeschoonde_waswordt.xlsx")
DEFTABEL_PATH = resource_filename(
    "veg2hab", "package_data/opgeschoonde_definitietabel.xlsx"
)
