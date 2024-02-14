import geopandas as gpd
import pandas as pd
import os.path

gdf = gpd.GeoDataFrame(data = {
    "Habtype1": ["H123", "H234", "H345", "H456"],
    "Perc1": [80, 20, 40, 40],
    "Habtype2": ["H123", "H234", "H345", "H456"],
    "Perc2": [80, 20, 40, 40],
    "Habtype3": [None, None, None, "H456"],
    "Perc3": [0, 0, 0, 100]
    },
    geometry=gpd.points_from_xy([0, 1, 2, 3], [0, 1, 2, 3])
)

# onze = gpd.read_file("testing/omgezette_vegetatiekarteringen/GR/NM vegetatiekartering RuitenAa2020.shp")[["Habtype1", "Habtype2", "Habtype3", "geometry"]]
hab = gpd.read_file("/mnt/c/Users/MarkBoer/OneDrive - Spheer AI/General/Projecten/Veg_2_Hab/Data/Habitatkarteringen/Habitattypekaarten Gr/NaamGebied_Ruiten Aa.gpkg")



# def spatial_join(gdf1, gdf2):
#     overlayed = gpd.overlay(gdf1, gdf2, how="intersection")
#     mask = overlayed.area > 1
#     print(f"Dropping {(~mask).sum()} rows (presumed rounding errors) with a combined area of {overlayed[~mask].area.sum()} m²")
#     return overlayed[overlayed.area > 1]

# spatial_join(onze, hab)
