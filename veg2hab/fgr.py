from enum import Enum
from pathlib import Path

import geopandas as gpd


# NOTE: als ik alle typen toch wil valideren, is er een enum van maken dan een goede manier? dan is het meteen mooi gegarandeerd matchend met eventuele input
class FGRType(Enum):
    DU = 'Duinen'
    GG = 'Getijdengebied'
    HL = 'Heuvelland'
    HZ = 'Hogere Zandgronden'
    LV = 'Laagveengebied'
    NI = 'Niet indeelbaar'
    RI = 'Rivierengebied'
    ZK = 'Zeekleigebied'
    AZ = 'Afgesloten Zeearmen'
    NZ = 'Noordzee'
        

class FGR():

    def __init__(self, path: Path):
        # inladen
        self.gdf = gpd.read_file(path)
        self.gdf = self.gdf[["fgr", "geometry"]]

        # omzetten naar enum (validatie)
        self.gdf["fgr"] = self.gdf["fgr"].apply(FGRType)

    def get_fgr_for_shape(self, shape):
        """
        Geeft de FGR voor een gegeven shape
        """
        overlapping_fgr = self.gdf[self.gdf.geometry.intersects(shape)].fgr.tolist()
        return overlapping_fgr
        
