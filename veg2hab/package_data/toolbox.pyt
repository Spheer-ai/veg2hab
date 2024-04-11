# -*- coding: utf-8 -*-

import arcpy
import logging
import veg2hab.io.arcgis
import veg2hab.main

interface = veg2hab.io.arcgis.ArcGISInterface.get_instance()
interface.instantiate_loggers()


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

    def getParameterInfo(self):
        """Define the tool parameters."""
        return veg2hab.io.arcgis.ArcGISParameters.to_parameter_list()

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        # TODO: we could do some more validation here
        # and or make some parameters dependent on others
        # validate that the column exists
        # if parameters[0].altered:
        #     try:
        #         layer = parameters[0].valueAsText
        #         fields = [f.name for f in arcpy.ListFields(layer)]
        #         parameters[1].filter.list = fields
        #     except Exception as e:
        #         # hmm, dit doet het nog niet helemaal..
        #         logging.error(e)

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""

    def execute(self, parameters, messages):
        """The source code of the tool."""
        input_params = veg2hab.io.arcgis.ArcGISParameters.from_parameter_list(parameters)
        veg2hab.main.run(input_params)

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
