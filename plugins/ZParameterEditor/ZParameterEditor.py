# Copyright (c) 2024 wsd
# ZParameterEditor is released under the terms of the AGPLv3 or higher.

from UM.Tool import Tool
from UM.Event import Event, MouseEvent
from UM.Scene.Selection import Selection
from UM.Scene.SceneNode import SceneNode
from UM.Logger import Logger
from UM.i18n import i18nCatalog
from UM.Version import Version
from PyQt6.QtCore import Qt, QObject, QTimer, pyqtSlot
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QVector3D

import json
from collections import OrderedDict
from UM.Extension import Extension
from UM.Application import Application
from UM.Settings.SettingDefinition import SettingDefinition
from UM.Settings.DefinitionContainer import DefinitionContainer
from UM.Settings.ContainerRegistry import ContainerRegistry
from UM.Platform import Platform

from typing import Dict, List, Any, Optional
import os.path
from cura.CuraApplication import CuraApplication
from UM.Math.Vector import Vector

from cura.Settings.ExtruderManager import ExtruderManager
from cura.Settings.GlobalStack import GlobalStack

i18n_catalog = i18nCatalog("ZParameterEditor")


class ZParameterEditor(Tool):
    def __init__(self):
        super().__init__()

        self._application = CuraApplication.getInstance()
        self._controller = self._application.getController()

        # Parameter data storage
        self._parameter_data = {}
        self._current_parameter_type = "temperature"
        self._model_height = 0.0
        self._layer_height = 0.2

        # Available parameter types
        self._parameter_types = {
            "temperature": {
                "label": "Temperature Profile",
                "setting_key": "user_temperature_definition",
                "enable_key": "user_temperature_definition_enable",
                "unit": "°C",
                "min_value": 150,
                "max_value": 300,
                "default_value": 200
            },
            "speed_ratio": {
                "label": "Speed Ratio Profile",
                "setting_key": "user_speed_ratio_definition",
                "enable_key": "user_speed_ratio_definition_enable",
                "unit": "%",
                "min_value": 10,
                "max_value": 200,
                "default_value": 100
            },
            "thickness": {
                "label": "Layer Thickness Profile",
                "setting_key": "user_thickness_definition",
                "enable_key": "user_thickness_definition_enable",
                "unit": "mm",
                "min_value": 0.1,
                "max_value": 0.4,
                "default_value": 0.2
            }
        }

        # Initialize parameter data
        for param_type in self._parameter_types:
            self._parameter_data[param_type] = []

        self.setExposedProperties(
            "ParameterTypes",
            "CurrentParameterType",
            "ParameterData",
            "ModelHeight",
            "LayerHeight",
            "CurrentParameterInfo",
            "FormatParameterData"
        )

        # Connect to scene changes to update model height
        Selection.selectionChanged.connect(self._onSelectionChanged)
        
    def event(self, event):
        """Handle tool events"""
        # Currently no event handling needed
        return False
        
    def _onSelectionChanged(self):
        """Update model height when selection changes"""
        self._updateModelHeight()
        
    def _updateModelHeight(self):
        """Calculate the height of the selected model"""
        selected_nodes = Selection.getAllSelectedObjects()
        if selected_nodes:
            # Get the first selected node
            node = selected_nodes[0]
            if node and hasattr(node, 'getBoundingBox'):
                bounding_box = node.getBoundingBox()
                if bounding_box:
                    self._model_height = bounding_box.height
                    # 不要在这里发射信号，避免无限递归
        else:
            self._model_height = 0.0
            # 不要在这里发射信号，避免无限递归
            
    def _updateLayerHeight(self):
        """Get current layer height from global settings"""
        global_stack = self._application.getGlobalContainerStack()
        if global_stack:
            layer_height = global_stack.getProperty("layer_height", "value")
            if layer_height:
                self._layer_height = float(layer_height)
                # 不要在这里发射信号，避免无限递归
    
    # Property getters for Cura's property system
    def getParameterTypes(self):
        """Return available parameter types for QML"""
        return self._parameter_types

    def getCurrentParameterType(self):
        """Return current parameter type"""
        return self._current_parameter_type

    def getParameterData(self):
        """Return parameter data for current type"""
        return self._parameter_data.get(self._current_parameter_type, [])

    def getModelHeight(self):
        """Return model height"""
        self._updateModelHeight()
        return self._model_height

    def getLayerHeight(self):
        """Return layer height"""
        self._updateLayerHeight()
        return self._layer_height

    def getCurrentParameterInfo(self):
        """Return info for current parameter type"""
        return self._parameter_types.get(self._current_parameter_type, {})

    def getFormatParameterData(self):
        """Return formatted parameter data for display"""
        data = self._parameter_data.get(self._current_parameter_type, [])
        return [f"H:{point['height']:.1f}mm V:{point['value']:.0f}{self._parameter_types.get(self._current_parameter_type, {}).get('unit', '')}" for point in data]

    def setProperty(self, property_name, value):
        """Set property value - required for Cura's property system"""
        if property_name == "CurrentParameterType":
            if value in self._parameter_types:
                self._current_parameter_type = value
                self.propertyChanged.emit()
        # Add other settable properties as needed

    def triggerAction(self, action_name, args=None):
        """Trigger action from QML - required for Cura's action system"""
        if args is None:
            args = []

        if action_name == "addParameterPoint" and len(args) >= 2:
            self.addParameterPoint(args[0], args[1])
        elif action_name == "removeParameterPoint" and len(args) >= 1:
            self.removeParameterPoint(args[0])
        elif action_name == "clearParameterData":
            self.clearParameterData()
        elif action_name == "applyParameterData":
            self.applyParameterData()
        else:
            Logger.log("w", f"Unknown action: {action_name}")
    
    # QML callable methods
    def setCurrentParameterType(self, param_type):
        """Set current parameter type"""
        if param_type in self._parameter_types:
            self._current_parameter_type = param_type
            self.propertyChanged.emit()

    def addParameterPoint(self, height, value):
        """Add a parameter point"""
        if self._current_parameter_type not in self._parameter_data:
            self._parameter_data[self._current_parameter_type] = []

        # Insert point in sorted order by height
        point = {"height": float(height), "value": float(value)}
        data = self._parameter_data[self._current_parameter_type]

        # Find insertion point
        insert_index = 0
        for i, existing_point in enumerate(data):
            if existing_point["height"] > height:
                insert_index = i
                break
            elif existing_point["height"] == height:
                # Replace existing point at same height
                data[i] = point
                self.propertyChanged.emit()
                return
            else:
                insert_index = i + 1

        data.insert(insert_index, point)
        self.propertyChanged.emit()

    def removeParameterPoint(self, index):
        """Remove a parameter point by index"""
        if self._current_parameter_type in self._parameter_data:
            data = self._parameter_data[self._current_parameter_type]
            if 0 <= index < len(data):
                data.pop(index)
                self.propertyChanged.emit()

    def clearParameterData(self):
        """Clear all parameter data for current type"""
        if self._current_parameter_type in self._parameter_data:
            self._parameter_data[self._current_parameter_type] = []
            self.propertyChanged.emit()

    def applyParameterData(self):
        """Apply parameter data to Cura settings"""
        param_info = self._parameter_types.get(self._current_parameter_type)
        if not param_info:
            return

        data = self._parameter_data.get(self._current_parameter_type, [])

        # Convert to the format expected by CuraEngine: [[height, value], ...]
        formatted_data = [[point["height"], point["value"]] for point in data]
        json_data = json.dumps(formatted_data)

        # Get global container stack
        global_stack = self._application.getGlobalContainerStack()
        if global_stack:
            # Enable the parameter
            global_stack.setProperty(param_info["enable_key"], "value", True)
            # Set the parameter data
            global_stack.setProperty(param_info["setting_key"], "value", json_data)

            Logger.log("i", f"Applied {self._current_parameter_type} parameter data: {json_data}")

    @pyqtSlot(str, str)
    def applyParameterSettings(self, parameter_key, formatted_value):
        """Apply parameter settings from QML interface"""
        Logger.log("i", f"Applying parameter settings: {parameter_key} = {formatted_value}")

        # Get global container stack
        global_stack = self._application.getGlobalContainerStack()
        if not global_stack:
            Logger.log("e", "No global container stack available")
            return

        # Find the parameter info by key
        param_info = None
        for _, info in self._parameter_types.items():
            if info.get("setting_key") == parameter_key:
                param_info = info
                break

        if not param_info:
            Logger.log("e", f"Unknown parameter key: {parameter_key}")
            return

        try:
            # Enable the parameter first
            enable_key = param_info.get("enable_key")
            if enable_key:
                global_stack.setProperty(enable_key, "value", True)
                Logger.log("i", f"Enabled parameter: {enable_key}")

            # Set the parameter value
            global_stack.setProperty(parameter_key, "value", formatted_value)
            Logger.log("i", f"Set parameter {parameter_key} to: {formatted_value}")

        except Exception as e:
            Logger.log("e", f"Error applying parameter settings: {str(e)}")
