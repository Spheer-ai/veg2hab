import logging
import re
from collections import defaultdict
from numbers import Number
from typing import Dict, List, Optional

import geopandas as gpd
import pandas as pd
from typing_extensions import Literal

from veg2hab.enums import Kwaliteit

MIN_AREA_THRESHOLD = 1


def _remove_duplicated_but_keep_order(lst: List[str]) -> List[str]:
    seen = set()
    return [x for x in lst if not (x in seen or seen.add(x))]


def _calc_percentages_if_missing(
    keys: List[str],
    how_to_handle_missing_percentages: Literal["split_equally", "select_first"],
) -> Dict[str, Number]:
    """
    Berekend missende percentages

    Voorbeeld:
        >>> _calc_percentages_if_missing(["H123", "H234", "H345"], "split_equally")
        {"H123": 33.33, "H234": 33.33, "H345": 33.33}
        >>> _calc_percentages_if_missing(["H123", "H234", "H345"], "select_first")
        {"H123": 100}
    """
    if len(keys) == 0:
        return dict()

    # TODO: If there are duplicates it now splits H1/H1/H2 into 50/50
    # we might want to split this into 66%,33%
    if how_to_handle_missing_percentages == "split_equally":
        keys = _remove_duplicated_but_keep_order(keys)
        return {key: 100 / len(keys) for key in keys}

    if how_to_handle_missing_percentages == "select_first":
        return {keys[0]: 100}

    raise ValueError(
        "how_to_handle_missing_percentages must be one of 'split_equally', 'select_first'"
    )


def _convert_row_to_habtype_dict(
    row: pd.Series,
    habtype_colnames: List[str],
    percentage_colnames: Optional[List[str]],
    how_to_handle_missing_percentages: Literal[None, "split_equally", "select_first"],
) -> Dict[str, Number]:
    """
    Schrijft de habitat types en percentages van een rij van een dataframe naar een dictionary

    Voorbeeld:
        >>> ser = gpd.GeoSeries(data = {"Habtype1": "H123", "Habtype2": "H234", "Habtype3": "H345", "Perc1": 80, "Perc2": 20, "Perc3": 0})
        >>> _convert_row_to_dict(ser, ["Habtype1", "Habtype2", "Habtype3"], ["Perc1", "Perc2", "Perc3"])
        {"H123": 80, "H234": 20, "H345": 0}
    """
    if percentage_colnames is not None and len(habtype_colnames) != len(
        percentage_colnames
    ):
        raise ValueError("The number of habitat types and percentages must be equal")

    ret_values = defaultdict(lambda: 0)
    if percentage_colnames is not None:
        for hab, perc in zip(row[habtype_colnames], row[percentage_colnames]):
            if pd.notnull(hab):
                ret_values[hab] += perc
    else:
        habs = [hab for hab in row[habtype_colnames] if pd.notnull(hab)]
        ret_values = _calc_percentages_if_missing(
            habs, how_to_handle_missing_percentages=how_to_handle_missing_percentages
        )

    if len(ret_values) == 0:
        logging.warning(f"No non-null habitat types found, returning 100% of H0000")
        return {"H0000": 100}

    if abs(sum(ret_values.values()) - 100) > 0.1:
        logging.warning(
            f"Percentages do not add up to 100% for row: {row.name}, result: {ret_values}"
        )

    return ret_values


def _convert_row_to_kwaliteit_dict(
    row: pd.Series, kwal_colnames: List[str], perc_colnames: List[str]
) -> Dict[str, Number]:
    """
    Schrijft de toegekende kwaliteiten van een rij van een dataframe naar een dictionary

    Voorbeeld:
        >>> ser = gpd.GeoSeries(data = {"Kwal1": "G", "Kwal2": "M", "Kwal3": "X", perc1": 60, "perc2": 20, "perc3": 0})
        >>> _convert_row_to_kwaliteit_dict(ser)
        {"Goed": 60, "Matig": 20, "Nvt": 0}
    """

    ret_values = defaultdict(lambda: 0)
    for kwal, perc in zip(row[kwal_colnames], row[perc_colnames]):
        if pd.notnull(kwal):
            ret_values[Kwaliteit.from_letter(kwal).value] += perc

    if len(ret_values) == 0:
        logging.warning(f"No non-null kwaliteiten found, returning 100% of Nvt")
        return {Kwaliteit.NVT.value: 100}

    if abs(sum(ret_values.values()) - 100) > 0.1:
        logging.warning(
            f"Percentages do not add up to 100% for row: {row.name}, result: {ret_values}"
        )

    return ret_values


def clean_up_habtypen(gdf: gpd.GeoDataFrame, habtype_cols: List[str]):
    """
    Schoont habitattypecodes op

    Haalt _ weg zodat H2130_B en H2130B als dezelfde worden gezien
    """
    for col in habtype_cols:
        gdf[col] = gdf[col].str.replace("_", "")
    return gdf


def parse_habitat_percentages(
    gdf: gpd.GeoDataFrame,
    habtype_cols_regex: str = "Habtype\d+",
    percentage_cols_regex: Optional[str] = "Perc\d+",
    how_to_handle_missing_percentages: Literal[
        None, "split_equally", "select_first"
    ] = None,
    add_kwaliteit: bool = False,
) -> gpd.GeoDataFrame:
    """
    Args:
        gdf: Een geodataframe met kolommen voor de habitat types en hun percentages
        habtype_cols: De string waarmee de habitattypekolommen moeten beginnen, bijvoorbeeld Habtype voor Habtype1, Habtype2, Habtype3
        percentage_cols: De string waarmee de percentagekolommen moeten beginnen
        how_to_handle_missing_percentages: Hoe om te gaan met ontbrekende percentages.
                                           Bij None zal de functie een foutmelding geven als er ontbrekende percentages zijn.
                                           Bij "split_equally" zal de ieder habitattype een gelijk percentage krijgen (100/n_habtypes).
                                           Bij "select_first" zal enkel het eerste habitattype gebruikt worden; deze krijgt dan ook 100%.
        add_kwaliteit: Voeg naast een kolom met percentages van habitattypen ook een kolom met percentages kwaliteit toe.
                       Dit is bedoeld voor veg2hab habitatkarteringen met Kwal1/Kwal2/... en Perc1/Perc2/... kolommen.
    """
    if (percentage_cols_regex is not None) == (
        how_to_handle_missing_percentages is not None
    ):  # xor
        raise ValueError(
            "You should specify exactly one of percentage_cols or how_to_handle_missing_percentages, not both"
        )

    habtype_cols = [c for c in gdf.columns if re.fullmatch(habtype_cols_regex, c)]
    if len(habtype_cols) == 0:
        raise ValueError(
            f"Expected nonzero of habitat and percentage columns, but found {len(habtype_cols)} hab columns"
        )

    if percentage_cols_regex is not None:
        percentage_cols = [
            c for c in gdf.columns if re.fullmatch(percentage_cols_regex, c)
        ]
        gdf[percentage_cols] = gdf[percentage_cols].apply(pd.to_numeric, errors="raise")

        if len(habtype_cols) != len(percentage_cols):
            raise ValueError(
                f"Expected same number of habitat and percentage columns, but found {len(habtype_cols)} hab columns and {len(percentage_cols)} percentage columns"
            )
    else:
        percentage_cols = None

    gdf = clean_up_habtypen(gdf, habtype_cols)

    return_gdf = gpd.GeoDataFrame(
        data={
            "hab_perc": gdf.apply(
                lambda row: _convert_row_to_habtype_dict(
                    row,
                    habtype_cols,
                    percentage_cols,
                    how_to_handle_missing_percentages,
                ),
                axis=1,
            )
        },
        geometry=gdf.geometry,
    )

    if add_kwaliteit:
        if add_kwaliteit:
            kwaliteit_cols = [c for c in gdf.columns if re.fullmatch("Kwal\d+", c)]
            if len(kwaliteit_cols) == 0:
                raise ValueError("No kwaliteit columns found (Kwal1, Kwal2, ...)")

            percentage_cols = [
                c for c in gdf.columns if re.fullmatch(percentage_cols_regex, c)
            ]
            if len(kwaliteit_cols) != len(percentage_cols):
                raise ValueError(
                    "The number of kwaliteit and percentage columns must be equal"
                )

            return_gdf["kwal_perc"] = gdf.apply(
                lambda row: _convert_row_to_kwaliteit_dict(
                    row, kwaliteit_cols, percentage_cols
                ),
                axis=1,
            )

    return return_gdf


def spatial_join(
    gdf_pred: gpd.GeoDataFrame,
    gdf_true: gpd.GeoDataFrame,
    how: Literal["intersection", "include_uncharted"],
) -> gpd.GeoDataFrame:
    """
    Joint twee geodataframes zodat ze op het overlappende deel dezelfde geometrieen hebben
    Als how "intersection" is, dan komt alleen het overlappende deel in de output
    Als how "include_uncharted" is, dan komt ook het niet-overlappende deel in de output - ongekarteerde gebieden krijgen dan voor 100% habitattype "ONGEKARTEERD"
    """
    # Kwaliteit is niet meer nodig, dus kan weg
    if "kwal_perc" in gdf_pred.columns:
        gdf_pred = gdf_pred.drop(columns=["kwal_perc"])

    assert (
        gdf_pred.columns.tolist()
        == gdf_true.columns.tolist()
        == ["hab_perc", "geometry"]
    )
    assert gdf_pred.notnull().all(axis=None) and gdf_true.notnull().all(axis=None)

    how = {"intersection": "intersection", "include_uncharted": "union"}[how]
    overlayed = gpd.overlay(
        gdf_pred, gdf_true, how=how, keep_geom_type=False
    )  # allow polygon => multipolygon
    overlayed = overlayed.rename(
        columns={"hab_perc_1": "pred_hab_perc", "hab_perc_2": "true_hab_perc"}
    )

    mask = overlayed.area < MIN_AREA_THRESHOLD
    if mask.sum() > 0:
        logging.warning(
            f"Dropping {mask.sum()} rows based on area (presumed rounding errors) with a combined area of {overlayed[mask].area.sum()} m²"
        )
        overlayed = overlayed[~mask]

    colnames = ["pred_hab_perc", "true_hab_perc"]
    total_non_matched_mask = overlayed[colnames].isnull().any(axis=1)
    if total_non_matched_mask.sum() > 0:
        assert (
            how == "union"
        ), "Combination of how=union with unmatched polygons should not be possible."
        logging.warning(
            f"Found {total_non_matched_mask.sum()} polygons, that were only present in one of the two geodataframes. Filling these with {{'ONGEKARTEERD: 100'}}"
        )

        overlayed[colnames] = overlayed[colnames].where(
            pd.notnull, other={"ONGEKARTEERD": 100}
        )

    assert overlayed.columns.tolist() == colnames + ["geometry"]
    return overlayed


def bereken_percentage_correct(
    habs_pred: Dict[str, Number], habs_true: Dict[str, Number]
) -> Number:
    """Berekent percentage correct"""
    keys_in_both = set(habs_pred.keys()) & set(habs_true.keys())
    return sum(min(habs_pred[k], habs_true[k]) for k in keys_in_both)


def voeg_correctheid_toe_aan_df(df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Voegt twee nieuwe kolommen toe aan de dataframe:
    percentage_correct en oppervlakte_correct
    """
    df["percentage_correct"] = df.apply(
        lambda row: bereken_percentage_correct(
            row["pred_hab_perc"], row["true_hab_perc"]
        ),
        axis=1,
    )
    df["oppervlakte_correct"] = df["percentage_correct"] * df.area
    return df


def bereken_percentage_confusion_matrix(
    habs_pred: Dict[str, Number], habs_true: Dict[str, Number]
) -> pd.DataFrame:
    """huilie huilie

    Voorbeeld:
        >>> bereken_percentage_confusion_matrix({"H123": 80, "H234": 20}, {"H123": 50, "H234": 50})
        pred_hab true_hab  percentage
        H123     H123      50.0
        H234     H234      20.0
        H123     H234      30.0
    """
    # We passen de dictionaries in place aan, dus we maken eerst een kopie
    habs_pred = habs_pred.copy()
    habs_true = habs_true.copy()

    outputs = []
    for pred_hab, pred_percentage in habs_pred.items():
        if pred_hab in habs_true:
            percentage_correct = min(pred_percentage, habs_true[pred_hab])
            outputs.append(
                {
                    "pred_hab": pred_hab,
                    "true_hab": pred_hab,
                    "percentage": percentage_correct,
                }
            )
            habs_pred[pred_hab] -= percentage_correct
            habs_true[pred_hab] -= percentage_correct
    # Alle matchende zitten nu in de outputes

    # We houden de volgorde aan van onze prediction
    habs_pred = {k: v for k, v in habs_pred.items() if v > 0}
    for pred_hab, pred_percentage in habs_pred.items():
        habs_true = {k: v for k, v in habs_true.items() if v > 0}
        for true_hab, true_percentage in habs_true.items():
            percentage = min(pred_percentage, true_percentage)
            outputs.append(
                {
                    "pred_hab": pred_hab,
                    "true_hab": true_hab,
                    "percentage": percentage,
                }
            )
            habs_true[true_hab] -= percentage
            pred_percentage -= percentage
            if pred_percentage == 0:
                break

    # TODO: Some extra validation here would be nice, with warnings if pred/true percentages do not match

    return pd.DataFrame(outputs, columns=["pred_hab", "true_hab", "percentage"])


def bereken_volledige_conf_matrix(
    gdf: gpd.GeoDataFrame, method: Literal["percentage", "area"] = "area"
) -> pd.DataFrame:
    """Berekent de volledige confusion matrix
    Geeft een vierkant pandas dataframe terug met identieke kolommen en rijen

    method="percentage" geeft het aantal shapes terug dat correct is geclassificeerd. Waarbij
        wordt gekeken naar percentages
    method="area" geeft het aantal hectaren terug dat correct is geclassificeerd.
    """
    assert method in {"percentage", "area"}

    def _func(row, method):
        df = bereken_percentage_confusion_matrix(
            row["pred_hab_perc"], row["true_hab_perc"]
        )
        if method == "area":
            df["percentage"] *= row.geometry.area / 100
            df = df.rename(columns={"percentage": "oppervlakte"})
        return df

    df = pd.concat([_func(row, method) for _, row in gdf.iterrows()])

    confusion_matrix = df.groupby(["pred_hab", "true_hab"]).sum()
    confusion_matrix = confusion_matrix.unstack().fillna(0)
    confusion_matrix.columns = confusion_matrix.columns.droplevel(0)

    # square it up
    indices = list(sorted(set(confusion_matrix.index) | set(confusion_matrix.columns)))
    confusion_matrix = confusion_matrix.reindex(
        index=indices, columns=indices, fill_value=0
    )

    # scale outputs
    if method == "percentage":
        confusion_matrix /= 100  # return outputs in values from 0 to 1
    if method == "area":
        confusion_matrix /= 10_000  # return outputs in ha

    return confusion_matrix


def bereken_totaal_succesvol_omgezet(
    gdf: gpd.GeoDataFrame, method: Literal["percentage", "area"] = "area"
):
    """
    gdf input:
                 pred_hab_perc                               geometry        en andere kolommen
                 {'H123': 100}  POLYGON ((0 0,  10 0,  10 10,  0 10))
     {'H123': 70, 'HXXXX': 30}  POLYGON ((0 0,  10 0,  10 10,  0 10))
    {'H0000': 50, 'HXXXX': 50}  POLYGON ((0 0,  10 0,  10 10,  0 10))

    De method telt alle oppervlakten (of percentages) op die volledig zijn geclassificeerd (dus niet HXXXX zijn).

    output (percentage):
    2.2
    """
    assert all(
        colname in gdf.columns for colname in ["pred_hab_perc", "geometry"]
    ), "Input gdf does not have the correct columns"

    def _func(row, method):
        total = 0

        for habtype, percentage in row["pred_hab_perc"].items():
            if habtype != "HXXXX":
                if method == "area":
                    total += (
                        row.geometry.area * (percentage / 100)
                    ) / 10_000  # convert to ha
                if method == "percentage":
                    total += percentage / 100

        return total

    return gdf.apply(_func, axis=1, method=method).sum()


def bereken_totaal_from_dict_col(
    gdf: gpd.GeoDataFrame, dict_col: str, method: Literal["percentage", "area"] = "area"
):
    """
    gdf input:
                      dict_col                               geometry        en andere kolommen
                    {'A': 100}  POLYGON ((0 0,  10 0,  10 10,  0 10))
            {'A': 70, 'B': 30}  POLYGON ((0 0,  10 0,  10 10,  0 10))
            {'C': 50, 'B': 50}  POLYGON ((0 0,  10 0,  10 10,  0 10))

    Deze method maakt een samenvattende Dict[str, Number] van de meegegeven dict_col.
    Hierin staan alle gevonden keys in de kolom met de som van de percentages/oppervlakten die daarbij horen.

    output (percentage):
    {"A": 1.7, "B": 0.8, "C": 0.5}
    """
    assert (
        dict_col in gdf.columns
    ), f"Input gdf does not have the expected column {dict_col}"
    if method == "area":
        assert "geometry" in gdf.columns, "Input gdf does not have a geometry column"

    answer_dict = {}

    for _, row in gdf.iterrows():
        for habtype, percentage in row[dict_col].items():
            if habtype not in answer_dict:
                answer_dict[habtype] = 0

            if method == "area":
                answer_dict[habtype] += (
                    row.geometry.area * (percentage / 100)
                ) / 10_000  # convert to ha
            if method == "percentage":
                answer_dict[habtype] += percentage / 100

    return answer_dict


def bereken_F1_per_habtype(
    df: pd.DataFrame, method: Literal["percentage", "area"] = "area"
) -> Dict[str, Number]:
    """
    Berekend de F1 metric per habitat type en geeft dit in een dict terug.

    input format (confusion matrix van bereken_volledige_conf_matrix):
    true_hab   H0000  H6430A  H7140A  HXXXX
    pred_hab
    H0000        3.0     1.0     1.0    0.0
    H6430A       0.0     3.0     0.0    0.0
    H7140A       0.0     0.0     3.0    0.0
    HXXXX        4.0     1.0     1.0    0.0

    output format:
    {"H1234": 0.5, "H2345": 0.5}
    """

    answer_dict = {}

    for habtype in df.index:
        # HXXXX is nooit correct, dus F1 is altijd 0
        if habtype == "HXXXX":
            continue
        true_pos = df.loc[habtype, habtype]
        false_pos = df.loc[habtype].sum() - true_pos
        false_neg = df[habtype].sum() - true_pos

        if true_pos == 0:
            answer_dict[habtype] = 0
        else:
            precision = true_pos / (true_pos + false_pos)
            recall = true_pos / (true_pos + false_neg)
            answer_dict[habtype] = 2 * (precision * recall) / (precision + recall)

    return answer_dict


def bereken_gemiddelde_F1(
    df: pd.DataFrame, method: Literal["percentage", "area"] = "area"
) -> float:
    """
    Berekend de het gemmidelde van de F1 metric per habitat type en geeft dit terug.
    """
    F1s = bereken_F1_per_habtype(df, method)
    return sum(F1s.values()) / len(F1s)
