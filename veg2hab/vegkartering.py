import geopandas as gpd


class Geometrie:
    """Een shape uit de vegetatiekartering.
    Deze bevat of een VvN of een SBB code en een geometrie.
    """

    data: gpd.GeoSeries  # (pandas series?)

    def __init__(self, data: gpd.GeoSeries):
        self.data = data


class Veg2HabKartering:
    """
    Een vegetatiekartering is klaar om gekoppeld te worden aan de definitietabel
    DWZ dat voor zover mogelijk de was-wordt lijst al is toegepast (en evt handmatig is gecorrigeerd)
    """

    def __init__(self, gdf: gpd.GeoDataFrame):
        self.gdf = gdf

        # Validation van de gdf
        self.validate()

    def __len__(self):
        return len(self.gdf)

    def __getitem__(self, item):
        return Geometrie(self.gdf.iloc[item])

    def validate(self):
        pass
        # Validation error als t foute boel is

        # Validate aanwezigheid vvn/sbb/geometry kolommen (en evt nog andere die nodig zijn)

        # Validate dat we of vvn of sbb hebben

        # Validate dat het valide codes zijn

        # Validate dat de geometrie een 2D multipolygon is

        # Validate dat de geometrie valide is (geen overlap, geen self intersection, etc)

        # Validate dat t rijksdriehoek is


class LokaleKartering:
    def __init__(self, gdf: gpd.GeoDataFrame):
        self.gdf = gdf

        # Validation van de gdf
        self.validate()

    @classmethod
    def from_access_db(cls, shape_path, access_path, join_parameters):
        pass

    @classmethod
    def from_shapefile(cls, shape_path):
        pass

    def __len__(self):
        return len(self.gdf)

    def __getitem__(self, item):
        return Geometrie(self.gdf.iloc[item])

    def validate(self):
        pass
        # Validation error als t foute boel is

        # Validate aanwezigheid vvn/sbb/geometry kolommen (en evt nog andere die nodig zijn)

        # Validate dat we of vvn of sbb hebben

        # Validate dat het valide codes zijn

        # Validate dat de geometrie een 2D multipolygon is

        # Validate dat de geometrie valide is (geen overlap, geen self intersection, etc)

        # Validate dat t rijksdriehoek is
