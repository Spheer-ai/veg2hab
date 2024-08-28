import pickle
from typing import List, Set, Tuple

import geopandas as gpd
import pandas as pd

from veg2hab.enums import FuncSamenhangID, KeuzeStatus, Kwaliteit
from veg2hab.io.common import Interface


class UnionFind:
    """
    Implementatie van de Union-Find/Disjoint-Set datastructuur
    https://en.wikipedia.org/wiki/Disjoint-set_data_structure
    https://www.youtube.com/watch?v=ayW5B2W9hfo

    Wordt gebruikt om paren van items te clusteren op basis van gemeenschappelijke elementen
    [1, 2], [2, 3], [2, 4], [5, 5]          ->  [1, 2, 3, 4], [5]
    [1, 2], [3, 4], [5, 6], [2, 3]          ->  [1, 2, 3, 4], [5, 6]
    [1, 2], [2, 3], [4, 5], [1, 6], [4, 7]  ->  [1, 2, 3, 6], [4, 5, 7]
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
    def cluster_pairs(
        pairs: Set[Tuple[FuncSamenhangID, FuncSamenhangID]]
    ) -> List[List[FuncSamenhangID]]:
        """
        Clustert paren op basis van gemene elementen
        """
        uf = UnionFind()

        # Maken van de union-bomen
        for pair in pairs:
            if pair[0] not in uf.parent_mapper:
                uf.parent_mapper[pair[0]] = pair[0]
                uf.rank[pair[0]] = 0
            if pair[1] not in uf.parent_mapper:
                uf.parent_mapper[pair[1]] = pair[1]
                uf.rank[pair[1]] = 0
            uf.union(pair[0], pair[1])

        # Voor ieder item de root vinden, en op basis daar van clusters maken
        clusters = {}
        for item in uf.parent_mapper:
            root = uf.find_root(item)
            if root not in clusters:
                clusters[root] = []
            clusters[root].append(item)

        return list(clusters.values())


def _cluster_vlakken(gdf: gpd.GeoDataFrame) -> List[List[FuncSamenhangID]]:
    """
    Bepaald clusters van vlakken op basis van distance tuples bestaande uit een minimum percentage en een buffer distance
    Werkt op (een subset van) het resultaat van _extract_elmid_perc_habtype

    Afhankelijk van het percentage van een complexdeel wordt er gebufferd, en daarna adhv overlap in de GeoDataFrame clusters bepaald;
    Als A overlapt met B en B met C, dan is [A, B, C] een cluster

    Output is een lijst met lijsten van (ElmID, complexdeelindex), waarbij iedere sublijst een cluster is,
    en er geen gemene elementen zijn tussen sublijsten.
    """
    assert (
        "identifier" in gdf.columns
    ), "identifier moet een kolom zijn in de gegeven GeoDataFrame"
    assert (
        "percentage" in gdf.columns
    ), "percentage moet een kolom zijn in de gegeven GeoDataFrame"
    assert (
        "habtype" in gdf.columns
    ), "habtype moet een kolom zijn in de gegeven GeoDataFrame"
    assert (
        "geometry" in gdf.columns
    ), "geometry moet een kolom zijn in de gegeven GeoDataFrame"

    distance_tuples = (
        Interface.get_instance().get_config().functionele_samenhang_buffer_distances
    )
    intersection_pairs = set()
    for distance_tuple in distance_tuples:
        min_perc, buffer_distance = distance_tuple
        current_subset = gdf[gdf.percentage >= min_perc].copy()
        current_subset["geometry"] = current_subset.buffer(buffer_distance)

        # Bepalen overlap-paren
        overlaps = gpd.sjoin(
            current_subset, current_subset, how="inner", predicate="intersects"
        )
        overlaps = list(
            zip(
                overlaps["identifier_left"].tolist(),
                overlaps["identifier_right"].tolist(),
            )
        )
        intersection_pairs.update(overlaps)

    clusters = UnionFind.cluster_pairs(intersection_pairs)

    # Alle elementen die niet aan de laagste percentage-eis voldoen moeten als zelfstandige nog steeds wel
    # meegenomen worden in de rest van het minimum-oppervlak-proces, dus die voegen we als individuen toe
    lowest_perc = min(distance_tuples, key=lambda x: x[0])[0]
    unclusterables = gdf[gdf.percentage < lowest_perc]
    clusters.extend(
        [[identifier] for identifier in unclusterables["identifier"].tolist()]
    )

    return clusters


def _extract_elmid_perc_habtype(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Trekt uit de vegkartering gdf de benodigde informatie voor het bepalen van clusters
    Ieder complexdeel/HabitatKeuze krijgt een eigen rij in de output, met de identifier (ElmID, complex-deel-index)
    Als er meerdere complexdelen met hetzelfde habtype in een vlak zitten, worden deze samengevoegd
    """

    def apply_func(row: pd.Series, vegetatiekundig_identiek: dict) -> pd.DataFrame:
        # identifier (Elmid, [cmplxdeel_n]) | percentage | habitattype | geometry
        identifier = []
        percentage = []
        habtype = []
        geometry = []
        for idx, keuze in enumerate(row["HabitatKeuze"]):
            # Dit stelt ons in staat weer terug te gaan naar de originele habitatkeuze
            identifier.append(FuncSamenhangID(row["ElmID"], (idx,)))
            # Nodig voor het bepalen van de buffergrootte
            percentage.append(row.VegTypeInfo[idx].percentage)
            # We clusteren binnen ieder habtype
            habtype.append(
                keuze.habtype
                if keuze.habtype not in vegetatiekundig_identiek.keys()
                else vegetatiekundig_identiek[keuze.habtype]
            )
            # We kunnen niet clusteren zonder geometrie
            geometry.append(row.geometry)

        gdf = gpd.GeoDataFrame(
            {
                "identifier": identifier,
                "percentage": percentage,
                "habtype": habtype,
                "geometry": geometry,
            }
        )

        # Checken op meerdere complexdelen met hetzelfde habtype binnen het huidige vlak
        if len(set(habtype)) != len(habtype):
            non_unique_habtypes = set(
                habtype[i] for i in range(len(habtype)) if habtype.count(habtype[i]) > 1
            )
            # We vervangen alle rijen met hetzelfde habtype door 1 rij met gecombineerde identifier
            # en de som van de percentages
            for type in non_unique_habtypes:
                all_rows_of_type = gdf[gdf.habtype == type].copy()
                identifiers = all_rows_of_type["identifier"].tolist()
                new_row = gpd.GeoDataFrame(
                    {
                        "identifier": [
                            (
                                identifiers[0].ElmID,
                                tuple(
                                    identifier.indices[0] for identifier in identifiers
                                ),
                            )
                        ],
                        "percentage": [sum(all_rows_of_type.percentage)],
                        "habtype": [type],
                        "geometry": [all_rows_of_type.geometry.iloc[0]],
                    }
                )
                gdf = gdf[gdf.habtype != type]
                gdf = pd.concat([gdf, new_row], ignore_index=True)

        return gdf

    vegetatiekundig_identiek = (
        Interface.get_instance()
        .get_config()
        .functionele_samenhang_vegetatiekundig_identiek
    )
    extracted = gdf.apply(apply_func, axis=1, args=(vegetatiekundig_identiek,))
    extracted = pd.concat(extracted.to_list(), ignore_index=True)
    return extracted


def _remove_habtypen_due_to_minimum_oppervlak(
    gdf: gpd.GeoDataFrame, to_be_edited: Set[FuncSamenhangID]
) -> gpd.GeoDataFrame:
    """
    Past HabitatKeuzes aan op basis van de (ElmID, complex-deel-index) tuples die in to_be_edited zitten

    De status van de HabitatKeuze wordt aangepast naar KeuzeStatus.MINIMUM_OPP_NIET_GEHAALD
    HabitatKeuze.info wordt aangepast naar "Was {oud_habtype}, maar oppervlak was te klein. {oude_info}"
    Het habitattype wordt aangepast naar "H0000"
    """
    for func_samenhang_id in to_be_edited:
        ElmID, indices = func_samenhang_id
        keuzes = gdf.loc[gdf.ElmID == ElmID, "HabitatKeuze"].iloc[0]
        for index in indices:
            keuze_to_be_edited = keuzes[index]
            assert not keuze_to_be_edited.habtype in [
                "H0000",
                "HXXXX",
            ], "H0000 en HXXXX vlakken zouden uitgesloten moeten zijn van functionele samenhang"
            assert keuze_to_be_edited.kwaliteit in [
                Kwaliteit.GOED,
                Kwaliteit.MATIG,
            ], "Functionele Samenhangvlak kwaliteit moet GOED of MATIG zijn"

            keuze_to_be_edited.status = KeuzeStatus.MINIMUM_OPP_NIET_GEHAALD
            keuze_to_be_edited.info = (
                "Was {} {}, maar oppervlak was te klein.{}".format(
                    keuze_to_be_edited.habtype,
                    "(" + keuze_to_be_edited.kwaliteit.as_letter() + ")",
                    f" {keuze_to_be_edited.info}"
                    if keuze_to_be_edited.info is not None
                    else "",
                )
            )
            keuze_to_be_edited.habtype = "H0000"
            keuze_to_be_edited.kwaliteit = Kwaliteit.NVT

    return gdf


def debug_visualize_clusters(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Maakt een dataframe met enkel geometries, Habitattypen, ElmID's en een cluster-index ter visualisatie van clusters
    Er wordt enkel gekeken naar de eerste HabitatKeuze per vlak (en dus niet naar (ElmID, niet-0-index) cluster entries)
    """
    all_clusters = []

    extracted = _extract_elmid_perc_habtype(gdf)
    all_present_habtypen = extracted["habtype"].unique()
    for habtype in all_present_habtypen:
        habtype_vlakken = extracted[extracted.habtype == habtype]
        all_clusters.extend(_cluster_vlakken(habtype_vlakken))

    new_gdf = gdf[["ElmID", "geometry"]].copy()
    new_gdf["cluster_id"] = None
    new_gdf["habtype"] = None
    for idx, cluster in enumerate(all_clusters):
        for identifier in cluster:
            ElmID, complex_deel_index = identifier
            if 0 not in complex_deel_index:
                continue
            new_gdf.loc[new_gdf.ElmID == ElmID, "cluster_id"] = idx
            new_gdf.loc[new_gdf.ElmID == ElmID, "habtype"] = extracted.loc[
                extracted.identifier == identifier, "habtype"
            ].iloc[0]

    return new_gdf


def apply_functionele_samenhang(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
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

    min_opp_lookup_func = (
        Interface.get_instance().get_config().get_minimum_oppervlak_for_habtype
    )

    # Extracten van ElmID + complex-deel-index, percentage en habitattype
    extracted = _extract_elmid_perc_habtype(gdf)

    # Niet heel netjes maar nu is de originele gdf 100% zeker niet aangepast
    edited_gdf = pickle.loads(pickle.dumps(gdf))
    all_present_habtypen = extracted["habtype"].unique()
    for habtype in all_present_habtypen:
        if habtype in ["H0000", "HXXXX"]:
            # Deze hoeven we niks mee
            continue
        habtype_vlakken = extracted[extracted.habtype == habtype]
        clusters = _cluster_vlakken(habtype_vlakken)
        assert len(habtype_vlakken) == sum(
            len(cluster) for cluster in clusters
        ), "Clusters bevatten niet alle vlakken of dubbele vlakken"
        for cluster in clusters:
            extracted_subset = extracted[extracted.identifier.isin(cluster)]
            areas = extracted_subset.area * (extracted_subset.percentage / 100)
            if areas.sum() > min_opp_lookup_func(habtype):
                continue
            edited_gdf = _remove_habtypen_due_to_minimum_oppervlak(edited_gdf, cluster)

    return edited_gdf
