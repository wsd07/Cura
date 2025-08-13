# Copyright (c) 2024 wsd
# ZParameterEditor is released under the terms of the AGPLv3 or higher.

from UM.Tool import Tool
from UM.Event import Event, MouseEvent
from UM.Scene.Selection import Selection
from UM.Scene.SceneNode import SceneNode
from UM.Logger import Logger
from UM.i18n import i18nCatalog
from UM.Version import Version
from PyQt6.QtCore import Qt, QObject, QTimer, pyqtSlot, pyqtSignal
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
from UM.Scene.Iterator.DepthFirstIterator import DepthFirstIterator

i18n_catalog = i18nCatalog("ZParameterEditor")


class ZParameterEditor(Tool):
    def __init__(self):
        super().__init__()

        self._application = CuraApplication.getInstance()
        self._controller = self._application.getController()

        # 加载设置定义
        self._settings_dict = {}
        self._loadSettingsDefinition()

        # Parameter data storage
        self._parameter_data = {}
        self._current_parameter_type = "user_speed_ratio_definition"  # 默认为速度比例
        self._model_height = 0.0
        self._layer_height = 0.2

        # Parameter states storage for persistence
        self._parameter_states = {}

        # 加载保存的参数状态
        self._loadParameterStates()

        # 为每个参数类型初始化默认控制点和曲线模式
        self._parameter_states = {
            "user_speed_ratio_definition": {
                "controlPoints": [{"z": 0, "value": 100}, {"z": 25.0, "value": 100}],
                "curveMode": "bezier",
                "minValue": 10,
                "maxValue": 200
            },
            "user_thickness_definition": {
                "controlPoints": [{"z": 0, "value": 0.2}, {"z": 25.0, "value": 0.2}],
                "curveMode": "bezier",
                "minValue": 0.1,
                "maxValue": 0.4
            },
            "user_temperature_definition": {
                "controlPoints": [{"z": 0, "value": 200}, {"z": 25.0, "value": 200}],
                "curveMode": "bezier",
                "minValue": 180,
                "maxValue": 250
            }
        }

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
            "ParameterDataForCurrentType",
            "ModelHeight",
            "LayerHeight",
            "CurrentParameterInfo",
            "FormatParameterData"
        )

        # 添加信号用于QML通信
        self.parameterDataChanged = pyqtSignal()
        self.currentParameterTypeChanged = pyqtSignal()

        # Connect to scene changes to update model height
        Selection.selectionChanged.connect(self._onSelectionChanged)

        # Connect to container registry for parameter injection
        ContainerRegistry.getInstance().containerLoadComplete.connect(
            self._onContainerLoadComplete
        )

        # 全局容器栈和参数监听
        self._global_container_stack = None

        # 监听全局容器栈变化
        self._application.globalContainerStackChanged.connect(self._onGlobalContainerStackChanged)

        # 初始化参数监听
        self._setupParameterListening()

    def _loadSettingsDefinition(self):
        """加载设置定义文件"""
        settings_definition_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "ZParameterEditor.def.json"
        )
        try:
            with open(settings_definition_path, "r", encoding="utf-8") as f:
                self._settings_dict = json.load(f, object_pairs_hook=OrderedDict)
                Logger.log("i", "Loaded ZParameterEditor settings definition")
        except Exception as e:
            Logger.log("e", f"Could not load ZParameterEditor settings definition: {str(e)}")
            self._settings_dict = {}

    def _onContainerLoadComplete(self, container_id: str) -> None:
        """当容器加载完成时，将我们的参数注入到设置定义中"""
        if not ContainerRegistry.getInstance().isLoaded(container_id):
            # skip containers that could not be loaded, or subsequent findContainers() will cause an infinite loop
            return

        try:
            container = ContainerRegistry.getInstance().findContainers(id=container_id)[0]
        except IndexError:
            # the container no longer exists
            return

        if not isinstance(container, DefinitionContainer):
            # skip containers that are not definitions
            return
        if container.getMetaDataEntry("type") == "extruder":
            # skip extruder definitions
            return

        try:
            # 找到experimental分组作为父分类
            category = container.findDefinitions(key="experimental")[0]
        except IndexError:
            Logger.log("e", "Could not find experimental category setting to add settings to")
            return

        # 为每个设置创建SettingDefinition并添加到容器中
        for setting_key in self._settings_dict.keys():
            # 检查设置是否已经存在，避免重复添加
            if container.findDefinitions(key=setting_key):
                continue

            setting_definition = SettingDefinition(
                setting_key, container, category, i18n_catalog
            )
            setting_definition.deserialize(self._settings_dict[setting_key])

            # add the setting to the already existing settingdefinition
            # private member access is naughty, but the alternative is to serialise, nix and deserialise the whole thing,
            # which breaks stuff
            category._children.append(setting_definition)
            container._definition_cache[setting_key] = setting_definition

            self._expanded_categories = self._application.expandedCategories.copy()
            self._updateAddedChildren(container, setting_definition)
            self._application.setExpandedCategories(self._expanded_categories)
            self._expanded_categories.clear()
            container._updateRelations(setting_definition)

        Logger.log("i", f"ZParameterEditor settings injected into container {container_id}")

    def _updateAddedChildren(
        self, container: DefinitionContainer, setting_definition: SettingDefinition
    ) -> None:
        """递归更新添加的子设置"""
        children = setting_definition.children
        if not children or not setting_definition.parent:
            return

        # make sure this setting is expanded so its children show up in setting views
        if setting_definition.parent.key in self._expanded_categories:
            self._expanded_categories.append(setting_definition.key)

        for child in children:
            container._definition_cache[child.key] = child
            self._updateAddedChildren(container, child)

    def event(self, event):
        """Handle tool events"""
        # Currently no event handling needed
        return False

    def setParameterDataSlot(self, data):
        """QML可调用的设置参数数据槽函数"""
        if isinstance(data, dict):
            parameter_key = data.get("parameterKey")
            state_data = data.get("stateData")
            if parameter_key and state_data:
                Logger.log("i", f"[SAVE_DEBUG] setParameterDataSlot called with key: {parameter_key}")
                self.setParameterData(parameter_key, state_data)
                return True
        return False

    def getParameterDataSlot(self, parameter_type):
        """QML可调用的获取参数数据槽函数"""
        Logger.log("i", f"[SAVE_DEBUG] getParameterDataSlot called with: {parameter_type}")
        return self.getParameterData(parameter_type)

    @pyqtSlot(str, result="float")
    def getModelHeight(self, dummy_param=""):
        """QML可调用的获取模型高度函数"""
        Logger.log("i", f"[CHART_DEBUG] getModelHeight called, current height: {self._model_height}")
        return float(self._model_height)

    @pyqtSlot(str, result="float")
    def getDefaultParameterValue(self, parameter_type):
        """获取指定参数类型的默认值"""
        try:
            machine_manager = Application.getInstance().getMachineManager()
            global_stack = machine_manager.activeMachine

            if not global_stack:
                Logger.log("w", f"[PARAM_DEBUG] No active machine found")
                return 100.0

            if parameter_type == "user_speed_ratio_definition":
                # 速度比例默认是100%
                return 100.0
            elif parameter_type == "user_thickness_definition":
                # 获取层厚设置
                layer_height = global_stack.getProperty("layer_height", "value")
                Logger.log("i", f"[PARAM_DEBUG] Got layer_height: {layer_height}")
                return float(layer_height) if layer_height is not None else 0.2
            elif parameter_type == "user_temperature_definition":
                # 获取打印温度设置
                print_temp = global_stack.getProperty("material_print_temperature", "value")
                if print_temp is None:
                    print_temp = global_stack.getProperty("default_material_print_temperature", "value")
                Logger.log("i", f"[PARAM_DEBUG] Got print temperature: {print_temp}")
                return float(print_temp) if print_temp is not None else 200.0
            else:
                Logger.log("w", f"[PARAM_DEBUG] Unknown parameter type: {parameter_type}")
                return 100.0

        except Exception as e:
            Logger.log("e", f"[PARAM_DEBUG] Error getting default parameter value: {e}")
            return 100.0

    @pyqtSlot(str)
    def setCurrentParameterTypeSlot(self, parameter_type):
        """QML可调用的设置当前参数类型槽函数"""
        self.setCurrentParameterType(parameter_type)

    @pyqtSlot(str, str)
    def applyParameterSettingsSlot(self, parameter_key, formatted_value):
        """QML可调用的应用参数设置槽函数"""
        self.applyParameterSettings(parameter_key, formatted_value)
        
    def _setupParameterListening(self):
        """设置参数变化监听"""
        Logger.log("i", "[PARAM_DEBUG] Setting up parameter listening")
        self._global_container_stack = self._application.getGlobalContainerStack()
        if self._global_container_stack:
            Logger.log("i", "[PARAM_DEBUG] Connecting to global container stack property changes")
            self._global_container_stack.propertyChanged.connect(self._onParameterChanged)

            # 监听所有挤出机的参数变化
            for extruder_stack in self._global_container_stack.extruderList:
                Logger.log("i", f"[PARAM_DEBUG] Connecting to extruder {extruder_stack.getId()} property changes")
                extruder_stack.propertyChanged.connect(self._onParameterChanged)

    def _onGlobalContainerStackChanged(self):
        """当全局容器栈变化时重新设置监听"""
        Logger.log("i", "[PARAM_DEBUG] Global container stack changed")
        if self._global_container_stack:
            try:
                self._global_container_stack.propertyChanged.disconnect(self._onParameterChanged)
                for extruder_stack in self._global_container_stack.extruderList:
                    extruder_stack.propertyChanged.disconnect(self._onParameterChanged)
            except TypeError:
                pass  # 忽略未连接的错误

        self._setupParameterListening()

    def _onParameterChanged(self, key: str, property_name: str):
        """监听参数变化"""
        if property_name == "value":
            Logger.log("i", f"[PARAM_DEBUG] Parameter {key} value changed")
            # 检查是否是我们关心的参数
            target_params = ["user_speed_ratio_definition", "user_thickness_definition", "user_temperature_definition"]
            if key in target_params:
                global_stack = self._application.getGlobalContainerStack()
                if global_stack:
                    new_value = global_stack.getProperty(key, "value")
                    Logger.log("i", f"[PARAM_DEBUG] Our parameter {key} changed to: {new_value}")

    def _onSelectionChanged(self):
        """Update model height when selection changes"""
        Logger.log("i", "[PARAM_DEBUG] Selection changed, updating model height")
        self._updateModelHeight()
        
    def _updateModelHeight(self):
        """Calculate the height of the selected model"""
        Logger.log("i", "[CORE_DEBUG] Updating model height")
        selected_nodes = Selection.getAllSelectedObjects()
        Logger.log("i", f"[CORE_DEBUG] Selected nodes count: {len(selected_nodes)}")
        old_height = self._model_height
        Logger.log("i", f"[CORE_DEBUG] Previous model height: {old_height}")

        if selected_nodes:
            # Get the first selected node
            node = selected_nodes[0]
            Logger.log("i", f"[CORE_DEBUG] Processing node: {node}")
            if node and hasattr(node, 'getBoundingBox'):
                bounding_box = node.getBoundingBox()
                Logger.log("i", f"[CORE_DEBUG] Bounding box: {bounding_box}")
                if bounding_box:
                    # 获取模型的Z范围，确保从0开始（不包含负值）
                    min_z = max(0.0, bounding_box.bottom)  # 不允许负值
                    max_z = bounding_box.top
                    self._model_height = max_z - min_z
                    Logger.log("i", f"[CORE_DEBUG] Model bounds - min_z: {min_z}, max_z: {max_z}, calculated height: {self._model_height}")
                else:
                    Logger.log("w", "[CORE_DEBUG] Node has no bounding box")
            else:
                Logger.log("w", "[CORE_DEBUG] Node is None or has no getBoundingBox method")
        else:
            self._model_height = 25.0  # 默认高度，而不是0
            Logger.log("i", "[CORE_DEBUG] No selection, model height set to default 25.0")

        # 只有当高度真正改变时才发射信号
        if abs(old_height - self._model_height) > 0.1:
            Logger.log("i", f"[CORE_DEBUG] Model height changed from {old_height} to {self._model_height}")
            Logger.log("i", "[CORE_DEBUG] Emitting propertyChanged signal")
            self.propertyChanged.emit()
        else:
            Logger.log("i", f"[CORE_DEBUG] Model height unchanged: {self._model_height}")
            
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

    def getParameterDataForCurrentType(self):
        """Return parameter data for current type"""
        return self._parameter_data.get(self._current_parameter_type, [])



    def getLayerHeight(self):
        """Return layer height"""
        self._updateLayerHeight()
        return self._layer_height

    def getCurrentParameterInfo(self):
        """Return info for current parameter type"""
        return self._parameter_types.get(self._current_parameter_type, {})

    @pyqtSlot(str, result=str)
    def getParameterState(self, parameter_key):
        """获取指定参数的状态"""
        import json
        state = self._parameter_states.get(parameter_key, {})
        return json.dumps(state)

    @pyqtSlot(str, str)
    def saveParameterState(self, parameter_key, state_json):
        """保存指定参数的状态"""
        import json
        try:
            state = json.loads(state_json)
            self._parameter_states[parameter_key] = state
            Logger.log("i", f"Saved state for parameter {parameter_key}")
        except Exception as e:
            Logger.log("e", f"Error saving parameter state: {str(e)}")

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
        Logger.log("i", f"[PARAM_DEBUG] Applying parameter settings: {parameter_key} = {formatted_value}")

        # Get global container stack
        global_stack = self._application.getGlobalContainerStack()
        if not global_stack:
            Logger.log("e", "[PARAM_DEBUG] No global container stack available")
            return

        Logger.log("i", f"[PARAM_DEBUG] Global stack ID: {global_stack.getId()}")

        try:
            # 根据参数类型确定对应的enable参数
            enable_key = None
            if parameter_key == "user_speed_ratio_definition":
                enable_key = "user_speed_ratio_enable"
            elif parameter_key == "user_thickness_definition":
                enable_key = "user_thickness_enable"
            elif parameter_key == "user_temperature_definition":
                enable_key = "user_temperature_enable"

            Logger.log("i", f"[PARAM_DEBUG] Enable key: {enable_key}")

            # 首先启用参数
            if enable_key:
                # 检查参数是否存在
                if global_stack.hasProperty(enable_key, "value"):
                    current_enable_value = global_stack.getProperty(enable_key, "value")
                    Logger.log("i", f"[PARAM_DEBUG] Current enable value for {enable_key}: {current_enable_value}")
                    global_stack.setProperty(enable_key, "value", True)
                    Logger.log("i", f"[PARAM_DEBUG] Enabled parameter: {enable_key}")
                else:
                    Logger.log("w", f"[PARAM_DEBUG] Enable parameter {enable_key} not found in stack")

            # 检查主参数是否存在
            Logger.log("i", f"[PARAM_DEBUG] Checking if parameter {parameter_key} exists in stack")
            if global_stack.hasProperty(parameter_key, "value"):
                Logger.log("i", f"[PARAM_DEBUG] Parameter {parameter_key} found in stack")

                # 获取当前值
                current_value = global_stack.getProperty(parameter_key, "value")
                Logger.log("i", f"[PARAM_DEBUG] Current value: {current_value}")

                # 设置参数值
                Logger.log("i", f"[PARAM_DEBUG] Setting parameter {parameter_key} to: {formatted_value}")
                global_stack.setProperty(parameter_key, "value", formatted_value)

                # 验证设置是否成功
                actual_value = global_stack.getProperty(parameter_key, "value")
                Logger.log("i", f"[PARAM_DEBUG] Verification - actual value: {actual_value}")

                if str(actual_value) == str(formatted_value):
                    Logger.log("i", f"[PARAM_DEBUG] Parameter {parameter_key} successfully set")
                else:
                    Logger.log("w", f"[PARAM_DEBUG] Parameter {parameter_key} value mismatch - expected: {formatted_value}, actual: {actual_value}")
            else:
                Logger.log("e", f"[PARAM_DEBUG] Parameter {parameter_key} not found in stack")
                # 列出所有可用的参数
                all_keys = global_stack.getAllKeys()
                Logger.log("i", f"[PARAM_DEBUG] Available parameters count: {len(all_keys)}")
                # 查找相似的参数名
                similar_keys = [key for key in all_keys if parameter_key.lower() in key.lower()]
                if similar_keys:
                    Logger.log("i", f"[PARAM_DEBUG] Similar parameter keys found: {similar_keys}")

        except Exception as e:
            Logger.log("e", f"[PARAM_DEBUG] Error applying parameter settings: {str(e)}")
            import traceback
            Logger.log("e", f"[PARAM_DEBUG] Traceback: {traceback.format_exc()}")

    @pyqtSlot(str)
    def saveParameterStateByType(self, parameter_type):
        """保存指定参数类型的状态"""
        Logger.log("i", f"[DEBUG] Saving parameter state for: {parameter_type}")
        if parameter_type in self._parameter_data:
            self._parameter_states[parameter_type] = self._parameter_data[parameter_type].copy()
            Logger.log("i", f"[DEBUG] Saved state: {self._parameter_states[parameter_type]}")

    @pyqtSlot(str)
    def restoreParameterState(self, parameter_type):
        """恢复参数状态"""
        Logger.log("i", f"[DEBUG] Restoring parameter state for: {parameter_type}")
        if parameter_type in self._parameter_states:
            self._parameter_data[parameter_type] = self._parameter_states[parameter_type].copy()
            Logger.log("i", f"[DEBUG] Restored state: {self._parameter_data[parameter_type]}")
            self.propertyChanged.emit()
        else:
            Logger.log("i", f"[DEBUG] No saved state found for: {parameter_type}")

    @pyqtSlot(str)
    def setCurrentParameterTypeSlot(self, parameter_type):
        """设置当前参数类型并恢复状态"""
        Logger.log("i", f"[DEBUG] Setting current parameter type: {parameter_type}")
        # 保存当前参数状态
        if self._current_parameter_type:
            self.saveParameterStateByType(self._current_parameter_type)

        # 切换到新参数类型
        self._current_parameter_type = parameter_type

        # 恢复新参数类型的状态
        self.restoreParameterState(parameter_type)

        self.propertyChanged.emit()

    @pyqtSlot(str, str)
    def setParameterData(self, parameter_type, data_json):
        """设置参数数据"""
        Logger.log("i", f"[SAVE_DEBUG] Setting parameter data for {parameter_type}")
        Logger.log("i", f"[SAVE_DEBUG] Data JSON: {data_json}")
        try:
            data = json.loads(data_json)
            Logger.log("i", f"[SAVE_DEBUG] Parsed data: {data}")
            # 保存到状态中
            self._parameter_states[parameter_type] = data.copy()
            Logger.log("i", f"[SAVE_DEBUG] Saved to parameter states")
            # 保存到偏好设置
            self._saveParameterStates()
            Logger.log("i", f"[SAVE_DEBUG] Parameter data saved successfully to preferences")
        except Exception as e:
            Logger.log("e", f"[SAVE_DEBUG] Error setting parameter data: {str(e)}")
            import traceback
            Logger.log("e", f"[SAVE_DEBUG] Traceback: {traceback.format_exc()}")

    @pyqtSlot(str, result=str)
    def getParameterData(self, parameter_type):
        """获取参数数据"""
        Logger.log("i", f"[SAVE_DEBUG] Getting parameter data for {parameter_type}")
        Logger.log("i", f"[SAVE_DEBUG] Available parameter states: {list(self._parameter_states.keys())}")
        if parameter_type in self._parameter_states:
            data = self._parameter_states[parameter_type]
            Logger.log("i", f"[SAVE_DEBUG] Found parameter state: {data}")
            result = json.dumps(data)
            Logger.log("i", f"[SAVE_DEBUG] Returning JSON: {result}")
            return result
        else:
            Logger.log("i", f"[SAVE_DEBUG] No parameter state found for {parameter_type}, returning empty object")
            return "{}"

    def _loadParameterStates(self):
        """从偏好设置中加载参数状态"""
        try:
            preferences = self._application.getPreferences()
            for param_type in ["user_speed_ratio_definition", "user_thickness_definition", "user_temperature_definition"]:
                pref_key = f"ZParameterEditor/{param_type}_state"
                if preferences.getValue(pref_key):
                    state_json = preferences.getValue(pref_key)
                    state = json.loads(state_json)
                    self._parameter_states[param_type] = state
                    Logger.log("i", f"[DEBUG] Loaded saved state for {param_type}: {state}")
                else:
                    Logger.log("i", f"[DEBUG] No saved state found for {param_type}, using defaults")
        except Exception as e:
            Logger.log("e", f"[DEBUG] Error loading parameter states: {str(e)}")

    def _saveParameterStates(self):
        """保存参数状态到偏好设置"""
        try:
            preferences = self._application.getPreferences()
            for param_type, state in self._parameter_states.items():
                if state:  # 只保存非空状态
                    pref_key = f"ZParameterEditor/{param_type}_state"
                    preferences.setValue(pref_key, json.dumps(state))
                    Logger.log("i", f"[DEBUG] Saved state for {param_type}: {state}")
        except Exception as e:
            Logger.log("e", f"[DEBUG] Error saving parameter states: {str(e)}")
