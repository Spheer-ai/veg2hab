import os.path
import re
import warnings
from collections import defaultdict
from numbers import Number
from typing import Dict, List, Optional

import geopandas as gpd
import pandas as pd
from typing_extensions import Literal


def _remove_duplicated_but_keep_order(lst: List[str]) -> List[str]:
    seen = set()
    return [x for x in lst if not (x in seen or seen.add(x))]


def _calc_percentages_if_missing(
    habtypes: List[str],
    how_to_handle_missing_percentages: Literal["split_equally", "select_first"],
) -> Dict[str, Number]:
    """Calculates the percentages if they are missing

    Example:
        >>> _calc_percentages_if_missing(["H123", "H234", "H345"], "split_equally")
        {"H123": 33.33, "H234": 33.33, "H345": 33.33}
        >>> _calc_percentages_if_missing(["H123", "H234", "H345"], "select_first")
        {"H123": 100}
    """
    if len(habtypes) == 0:
        return dict()

    if how_to_handle_missing_percentages == "split_equally":
        habtypes = _remove_duplicated_but_keep_order(habtypes)
        return {hab: 100 / len(habtypes) for hab in habtypes}

    if how_to_handle_missing_percentages == "select_first":
        return {habtypes[0]: 100}

    raise ValueError(
        "how_to_handle_missing_percentages must be one of 'split_equally', 'select_first'"
    )


def _convert_row_to_dict(
    row: pd.Series,
    habtype_colnames: List[str],
    percentage_colnames: Optional[List[str]],
    how_to_handle_missing_percentages: Literal[None, "split_equally", "select_first"],
):
    """Converts a row of a dataframe into a dictionary of habitat types and their percentages

    Example:
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

    # TODO valideren dat alle habtypes anders zijn.
    if len(ret_values) == 0:
        warnings.warn(f"No non-null habitat types found, returning 100% of H0000")
        return {"H0000": 100}

    if abs(sum(ret_values.values()) - 100) > 0.1:
        warnings.warn(
            f"Percentages do not add up to 100% for row: {row.name}, result: {ret_values}"
        )

    return ret_values


def parse_habitat_percentages(
    gdf: gpd.GeoDataFrame,
    habtype_cols: str = "Habtype",
    percentage_cols: Optional[str] = "Perc",
    how_to_handle_missing_percentages: Literal[
        None, "split_equally", "select_first"
    ] = None,
):
    """
    Args:
        gdf: A GeoDataFrame containing habitat types and their percentages
        habtype_cols: The name that the column should start with e.g. Habtype to match Habtype1, Habtype2, Habtype3
        percentage_cols: The name that percentage column should start
        how_to_handle_missing_percentages: How to handle missing percentages. If None, the function will raise an error if there are missing percentages. If "split_equally", the function will split the remaining percentage equally among the missing percentages.
    """
    if (percentage_cols is not None) == (
        how_to_handle_missing_percentages is not None
    ):  # xor
        raise ValueError(
            "You should specify exactly one of percentage_cols or how_to_handle_missing_percentages, not both"
        )

    habtype_cols = [c for c in gdf.columns if re.fullmatch(f"{habtype_cols}\d+", c)]
    if len(habtype_cols) == 0:
        raise ValueError(
            f"Expected nonzero of habitat and percentage columns, but found {len(habtype_cols)} hab columns"
        )
    if percentage_cols is not None:
        percentage_cols = [
            c for c in gdf.columns if re.fullmatch(f"{percentage_cols}\d+", c)
        ]
        gdf[percentage_cols] = gdf[percentage_cols].apply(pd.to_numeric, errors="raise")

        if len(habtype_cols) != len(percentage_cols):
            raise ValueError(
                f"Expected same number of habitat and percentage columns, but found {len(habtype_cols)} hab columns and {len(percentage_cols)} percentage columns"
            )

    return gpd.GeoDataFrame(
        data={
            "hab_perc": gdf.apply(
                lambda row: _convert_row_to_dict(
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


def spatial_join(gdf_pred, gdf_true, how: Literal["intersection", "include_uncharted"]):
    """Joins the two dataframes
    Use include uncharted to create a new Habtype "ONGEKARTEERD" with 100% for all uncharted areas
    """
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

    mask = overlayed.area < 1
    if mask.sum() > 0:
        warnings.warn(
            f"Dropping {mask.sum()} rows based on area (presumed rounding errors) with a combined area of {overlayed[mask].area.sum()} m²"
        )
        overlayed = overlayed[~mask]

    colnames = ["pred_hab_perc", "true_hab_perc"]
    total_non_matched_mask = overlayed[colnames].isnull().any(axis=1)
    if total_non_matched_mask.sum() > 0:
        assert (
            how == "union"
        ), "Combination of how=union with unmatched polygons should not be possible."
        warnings.warn(
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


def voeg_correctheid_toe_aan_df(df: gpd.GeoDataFrame):
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

    Example:
        >>> bereken_percentage_confusion_matrix({"H123": 80, "H234": 20}, {"H123": 50, "H234": 50})
        pred_hab true_hab  percentage
        H123     H123      50.0
        H234     H234      20.0
        H123     H234      30.0
    """
    # we'll be editing the dictionaries in place, so let's first make a copy
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
    # alle matchende zitten nu in de outputes

    # we houden de volgorde aan van onze prediction
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

    # TODO add some validation here!!
    # willen we hier nog valideren met percentages?
    #     if percentage > 1e-10:
    #         warnings.warn("Non matching percentages in conf matrix, too much pred %?")
    # if true_percentage > 1e-10:
    #     warnings.warn("Non matching percentages in conf matrix, too much true %?")

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
