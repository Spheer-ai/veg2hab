import geopandas as gpd
import pandas as pd

onze = gpd.read_file("testing/omgezette_vegetatiekarteringen/GR/NM vegetatiekartering RuitenAa2020.shp")[["Habtype1", "Habtype2", "Habtype3", "geometry"]]
hab = gpd.read_file("/mnt/c/Users/JordydeLange/Spheer AI/Spheer AI - General/Projecten/Veg_2_Hab/Data/Habitatkarteringen/Habitattypekaarten Gr/NaamGebied_Ruiten Aa.gpkg")[["geometry", "Habtype1", "Habtype2", "Habtype3"]]

def spatial_join(gdf1, gdf2):
    overlayed = gpd.overlay(gdf1, gdf2, how="intersection")
    mask = overlayed.area > 1
    print(f"Dropping {(~mask).sum()} rows (presumed rounding errors) with a combined area of {overlayed[~mask].area.sum()} m²")
    return overlayed[overlayed.area > 1]

spatial_join(onze, hab)
