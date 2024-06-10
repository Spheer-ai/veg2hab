from typing import List, Tuple

import geopandas as gpd
import pandas as pd

from veg2hab.enums import KeuzeStatus, Kwaliteit
from veg2hab.habitat import HabitatKeuze
from veg2hab.io.common import Interface


class _UnionFind:
    """
    Implementatie van de Union-Find/Disjoint-Set datastructuur
    https://en.wikipedia.org/wiki/Disjoint-set_data_structure
    https://www.youtube.com/watch?v=ayW5B2W9hfo

    Wordt gebruikt om groepen van items te clusteren op basis van gemeenschappelijke elementen
    [1, 2, 3], [2, 4], [5]                      ->  [1, 2, 3, 4], [5]
    [1, 2], [3, 4], [5, 6], [2, 3]              ->  [1, 2, 3, 4], [5, 6]
    [1, 2], [2, 3], [4, 5], [1, 6], [4, 7, 8]   ->  [1, 2, 3, 6], [4, 5, 7, 8]
    """

    def __init__(self):
        self.parent_mapper = {}
        self.rank = {}

    def find_root(self, item) -> int:
        """
        Doorloopt de boom van item via de parent_mapper en geeft de root terug
        """
        if self.parent_mapper[item] != item:
            self.parent_mapper[item] = self.find_root(self.parent_mapper[item])
        return self.parent_mapper[item]

    def union(self, item1, item2) -> None:
        """
        Combineert de bomen van item1 en item2
        """
        root1 = self.find_root(item1)
        root2 = self.find_root(item2)
        if root1 != root2:
            if self.rank[root1] > self.rank[root2]:
                self.parent_mapper[root2] = root1
            elif self.rank[root1] < self.rank[root2]:
                self.parent_mapper[root1] = root2
            else:
                self.parent_mapper[root2] = root1
                self.rank[root1] += 1

    @staticmethod
    def cluster_lists(groups: List[List]) -> List[List]:
        """
        Clustert groepen (sublists) op basis van gemene elementen
        """

        uf = _UnionFind()

        # Maken van de union-bomen
        for group in groups:
            prev = None
            for item in group:
                # Nieuwe items krijgen altijd eerst een eigen boom
                if item not in uf.parent_mapper:
                    uf.parent_mapper[item] = item
                    uf.rank[item] = 0
                # Alle andere items in de groep worden geunioneerd met het vorige item in de groep
                if prev is not None:
                    uf.union(prev, item)
                prev = item

        # Voor ieder item de root vinden, en op basis daar van clusters maken
        clusters = {}
        for item in uf.parent_mapper:
            root = uf.find_root(item)
            if root not in clusters:
                clusters[root] = []
            clusters[root].append(item)

        return list(clusters.values())


def _cluster_vlakken(gdf: gpd.GeoDataFrame) -> List[List]:
    """
    Bepaald clusters van vlakken op basis van overlap in de GeoDataFrame;
    Als A overlapt met B en B met C, dan is [A, B en C] een cluster

    Output is een lijst met lijsten van ElmID's, waarbij iedere sublijst een cluster is,
    en er geen gemene elementen zijn tussen sublijsten.
    """
    assert (
        "VegTypeInfo" in gdf.columns
    ), "VegTypeInfo moet een kolom zijn in de gegeven GeoDataFrame"
    assert (
        "ElmID" in gdf.columns
    ), "ElmID moet een kolom zijn in de gegeven GeoDataFrame"

    distance_tuples = (
        Interface.get_instance().get_config().functionele_samenhang_buffer_distances
    )
    clusters = []
    for distance_tuple in distance_tuples:
        min_perc, buffer_distance = distance_tuple
        current_subset = gdf[
            gdf.apply(lambda row: min_perc <= row["VegTypeInfo"].percentage, axis=1)
        ]
        current_subset["geometry"] = current_subset.buffer(buffer_distance)

        # Bepalen overlap-paren
        overlaps = gpd.sjoin(
            current_subset, current_subset, how="inner", op="intersects"
        )
        overlaps = list(overlaps[["ElmID_left", "ElmID_right"]].to_numpy())

        # Clustering van de vlakken
        ElmID_clusters = _UnionFind.cluster_lists(overlaps)
        clusters.extend(ElmID_clusters)

    return _UnionFind.cluster_lists(clusters)


def _extract_elmid_perc_habtype(row: gpd.GeoSeries) -> gpd.GeoDataFrame:
    # (Elmid, cmplxdeel_n) | percentage | habitattype
    identifier = []
    percentage = []
    habtype = []
    geometry = []
    for idx, keuze in enumerate(row["HabitatKeuze"]):
        identifier.append((row["ElmID"], idx))
        percentage.append(row.VegTypeInfo[idx].percentage)
        habtype.append(keuze.habtype)
        geometry.append(row.geometry)
    return pd.DataFrame(
        {
            "identifier": identifier,
            "percentage": percentage,
            "habitattype": habtype,
            "geometry": geometry,
        }
    )


def apply_functionele_samenhang(gdf: gpd.GeoDataFrame) -> pd.Series:
    """
    Past de minimum oppervlak en functionele samenhang regels toe
    """
    assert (
        "ElmID" in gdf.columns
    ), "ElmID moet een kolom zijn in de gegeven GeoDataFrame"
    assert (
        "VegTypeInfo" in gdf.columns
    ), "VegTypeInfo moet een kolom zijn in de gegeven GeoDataFrame"
    assert (
        "HabitatKeuze" in gdf.columns
    ), "HabitatKeuze moet een kolom zijn in de gegeven GeoDataFrame"

    # Extracten van ElmID + complex-deel-index, percentage en habitattype
    extracted = gdf.apply(_extract_elmid_perc_habtype, axis=1)
    extracted = pd.concat(extracted.to_list(), ignore_index=True)

    grouped_by_habtype = extracted.groupby("habitattype")

    # general idea:
    # group by habtype
    # for habtype in all_present_habtypen:
    #     habtype_vlakken = get_vlakken_with_habtype(habtype)
    #     clusters = _cluster_vlakken(habtype_vlakken)
    #     for cluster in clusters:
    #         if cluster opp < minimum:
    #             habtype = "H0000"
    #             status = KeuzeStatus.MINIMUM_OPPERVLAK
    #             ergens iets met t oude habtype zodat we die niet kwijtraken
