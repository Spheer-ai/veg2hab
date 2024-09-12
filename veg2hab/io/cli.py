import logging
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Callable, Dict, Optional

import click
from geopandas.geodataframe import GeoDataFrame
from pydantic import validator
from typing_extensions import override

from veg2hab.criteria import OverrideCriterium

from .. import enums
from .common import (
    AccessDBInputs,
    ApplyDefTabelInputs,
    ApplyFunctioneleSamenhangInputs,
    ApplyMozaiekInputs,
    Interface,
    ShapefileInputs,
    StackVegKarteringInputs,
)


class CLIInterface(Interface):
    @override
    def output_shapefile(self, shapefile_id: Optional[Path], gdf: GeoDataFrame) -> None:
        if shapefile_id is None:
            shapefile_id = Path(
                f"./kaart_{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%S')}.gpkg"
            )
        gdf.to_file(shapefile_id, driver="GPKG", layer="main")

    @override
    def instantiate_loggers(self, log_level: int) -> None:
        logging.basicConfig(level=log_level)


def _decorate_click(func: Callable, param_schema: Dict):
    for field_name, field_info in reversed(list(param_schema["properties"].items())):
        is_required = field_name in param_schema["required"]

        if field_info.get("format", "") == "path":
            writable = field_name == "output"
            param_type = click.Path(exists=False, writable=writable)
        elif "enum" in field_info:
            param_type = click.Choice(field_info["enum"])
        elif field_name == "welke_typologie":
            # NOTE: did is niet zo netjes en zou mooier kunnen
            ref_name = field_info.get("allOf")[0].get("$ref").split("/")[-1]
            param_type = click.Choice(param_schema["definitions"][ref_name]["enum"])
        else:
            param_type = str

        if field_name == "override_dict":
            func = click.option(
                "--overschrijf-criteria",
                "override_dict",
                help=field_info.get("description"),
                type=click.Tuple([str, str, str, str]),
                required=False,
                multiple=True,  # allow multiple values
            )(func)
        elif is_required:
            func = click.argument(
                field_name,
                type=param_type,
                required=is_required,
                # allow multiple values in case of the step_2_stacking
                nargs=-1 if field_info.get("type") == "array" else 1,
            )(func)
        else:
            func = click.option(
                f"--{field_name}",
                help=field_info.get("description"),
                type=param_type,
                required=is_required,
                multiple=field_info.get("type") == "array",
            )(func)

    return func


def _get_argument_description(description: str, param_schema: Dict):
    description += "\n\nArguments:\n\n"
    for field_name, field_info in param_schema["properties"].items():
        if field_name in param_schema["required"]:
            description += (
                f"  {field_name.upper()}: {field_info.get('description', '')}\n\n"
            )
    return description


class CLIMixin:
    @classmethod
    def click_decorator(cls, func):
        return _decorate_click(func, cls.schema())

    @classmethod
    def get_argument_description(cls):
        return _get_argument_description(cls.description, cls.schema())


class CLIAccessDBInputs(AccessDBInputs, CLIMixin):
    pass


class CLIShapefileInputs(ShapefileInputs, CLIMixin):
    pass


class CLIStackVegKarteringInputs(StackVegKarteringInputs, CLIMixin):
    pass


class CLIApplyDefTabelInputs(ApplyDefTabelInputs, CLIMixin):
    pass


class CLIApplyMozaiekInputs(ApplyMozaiekInputs, CLIMixin):
    pass


class CLIApplyFunctioneleSamenhangInputs(ApplyFunctioneleSamenhangInputs, CLIMixin):
    pass
