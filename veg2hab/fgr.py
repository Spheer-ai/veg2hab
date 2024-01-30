from enum import Enum

from geopandas import GeoDataFrame


class FGRType(Enum):
    DUINEN = 'Duinen'
    GETIJDENGEBIED ='Getijdengebied'
    HEUVELLAND = 'Heuvelland'
    HOGERE_ZANDGRONDEN = 'Hogere Zandgronden'
    LAAGVEENGEBIED = 'Laagveengebied'
    NIET_INDEELBAAR = 'Niet indeelbaar'
    RIVIERENGEBIED = 'Rivierengebied'
    ZEEKLEIGEBIED = 'Zeekleigebied'
    AFGESLOTEN_ZEEARMEN = 'Afgesloten Zeearmen'
    NOORDZEE = 'Noordzee'

    @classmethod
    def from_string(cls, string):
        try:
            return cls[string]
        except KeyError:
            raise ValueError(f'String moet een van de volgende waarden zijn: {", ".join(cls.__members__.keys())}')