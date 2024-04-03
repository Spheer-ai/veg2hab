# -*- coding: utf-8 -*-

import random
import string
import arcpy
import logging
import os.path


class ArcpyAddMessageHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        if record.levelno >= logging.ERROR:
            arcpy.AddError(msg)
        elif record.levelno >= logging.WARNING:
            arcpy.AddWarning(msg)
        else:
            # this will map debug into info, but that's just
            # the way it is now..
            arcpy.AddMessage(msg)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[ArcpyAddMessageHandler()]
)

try:
    import veg2hab
except ImportError:
    logging.error("veg2hab is not properly installed, please install it using pip")


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "veg2hab"
        self.alias = "veg2hab toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Tool]


class Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "draai_veg2hab"
        self.description = "Draai veg2hab"

    def unpack_parameters(self, parameters):
        return {p.name: p.valueAsText for p in parameters}

    @property
    def default_file_location(self):
        return os.path.abspath(
            os.path.join(arcpy.env.scratchWorkspace, "..")
        )

    def export_feature_geopackage(self, feature_name):
        random_name = f"vegkart_{''.join(random.choices(string.ascii_letters + string.digits, k=8))}.gpkg"
        filename = os.path.join(self.default_file_location, random_name)


    def getParameterInfo(self):
        """Define the tool parameters."""
        params = [
            arcpy.Parameter(
                name="in_features",
                displayName="Input Features",
                datatype="GPFeatureLayer",
                parameterType="Required",
                direction="Input"
            ),
            arcpy.Parameter(
                name="veg_type_column",
                displayName="Vegtype Kolom",
                datatype="Field",
                parameterType="Required",
                direction="Input"
            ),
            arcpy.Parameter(
                name="test_column",
                displayName="Gewoon een testje",
                datatype="Field",
                parameterType="Required",
                direction="Input",
                enabled=True,
            ),
            arcpy.Parameter(
                name="out_features",
                displayName="Habitat Kaart",
                datatype="DEFeatureClass",
                parameterType="Required",
                direction="Output"
            ),
        ]
        params[2].filter.list = ["test1", "test2", "test3"]
        return params

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        # validate that the column exists
        if parameters[0].altered:
            try:
                layer = parameters[0].valueAsText
                fields = [f.name for f in arcpy.ListFields(layer)]
                parameters[1].filter.list = fields
            except Exception as e:
                # hmm, dit doet het nog niet helemaal..
                logging.error(e)


    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        logging.warning(parameters)
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # get the filename for the input package

        logging.warning(type(parameters[0]))
        logging.warning(self.unpack_parameters(parameters))

        # input = output (for now!)
        arcpy.MakeFeatureLayer_management(parameters[0].valueAsText, parameters[-1].valueAsText)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
