# Copyright (c) 2024 wsd
# ZParameterEditor is released under the terms of the AGPLv3 or higher.

from UM.Tool import Tool
from UM.Scene.Selection import Selection
from UM.Scene.SceneNode import SceneNode
from UM.Scene.Iterator.DepthFirstIterator import DepthFirstIterator
from UM.Logger import Logger
from UM.i18n import i18nCatalog
from UM.Version import Version
from UM.Event import Event
from PyQt6.QtCore import Qt, QObject, QTimer, pyqtSlot, pyqtSignal
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QVector3D

import json
from collections import OrderedDict
from UM.Application import Application
from UM.Settings.SettingDefinition import SettingDefinition
from UM.Settings.DefinitionContainer import DefinitionContainer
from UM.Settings.ContainerRegistry import ContainerRegistry
from UM.Platform import Platform

from typing import Dict, List, Any, Optional
import os.path
import numpy as np
from cura.CuraApplication import CuraApplication
from UM.Math.Vector import Vector
from UM.Math.Matrix import Matrix
from UM.Math.Color import Color
from UM.Mesh.MeshBuilder import MeshBuilder
from UM.Mesh.MeshData import MeshData
from UM.View.RenderBatch import RenderBatch
from UM.View.GL.OpenGL import OpenGL
from UM.Resources import Resources

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

        # 加载保存的模型参数数据
        self._loadModelParameterData()

        # 初始化默认参数状态（这些将被模型特定数据覆盖）
        self._parameter_states = {}

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

        # 按模型保存参数数据的字典
        self._model_parameter_data = {}  # {model_id: {param_type: data}}
        self._current_model_id = None

        # 3D截线显示相关
        self._cross_section_node = None  # 用于显示截线的场景节点
        self._cross_section_z = 0.0  # 当前截线的Z高度
        self._cross_section_visible = False  # 截线是否可见
        self._shader = None  # 用于渲染截线的着色器

        # 添加信号用于QML通信
        self.parameterDataChanged = pyqtSignal()
        self.currentParameterTypeChanged = pyqtSignal()

        # Connect to scene changes to update model height
        Selection.selectionChanged.connect(self._onSelectionChanged)

        # 监听场景变化以清理删除的模型数据
        self._application.getController().getScene().sceneChanged.connect(self._onSceneChanged)

        # Connect to container registry for parameter injection
        ContainerRegistry.getInstance().containerLoadComplete.connect(
            self._onContainerLoadComplete
        )

        # 全局容器栈和参数监听
        self._global_container_stack = None

        # 监听全局容器栈变化
        self._application.globalContainerStackChanged.connect(self._onGlobalContainerStackChanged)

        # 添加偏好设置键
        self._addPreferenceKeys()

        # 初始化参数监听
        self._setupParameterListening()

    def event(self, event):
        """Handle tool events"""
        super().event(event)

        if event.type == Event.ToolActivateEvent:
            Logger.log("i", "[TOOL_DEBUG] ZParameterEditor tool activated")
            # 更新模型高度和当前模型ID
            self._updateModelHeight()
            self._updateCurrentModelId()
            # 如果没有选中模型，尝试恢复之前的选择
            if not self._current_model_id:
                self._restoreModelSelection()
                # 重新更新模型ID和高度
                self._updateModelHeight()
                self._updateCurrentModelId()
            # 加载当前模型的数据到会话中
            self._loadModelDataToSession()
            # 加载当前模型的数据
            self._loadCurrentModelData()

        if event.type == Event.ToolDeactivateEvent:
            Logger.log("i", "[TOOL_DEBUG] ZParameterEditor tool deactivated")
            # 保存当前模型数据
            self._saveCurrentModelData()

        return False

    def _restoreModelSelection(self):
        """尝试恢复模型选择"""
        Logger.log("i", "[MODEL_DEBUG] ========== _restoreModelSelection called ==========")

        # 获取场景中的所有模型节点
        scene = Application.getInstance().getController().getScene()
        scene_root = scene.getRoot()

        # 查找所有模型节点
        model_nodes = []
        for node in DepthFirstIterator(scene_root):
            if hasattr(node, 'getMeshData') and node.getMeshData():
                model_nodes.append(node)
                Logger.log("i", f"[MODEL_DEBUG] Found model node: {node.getName()}")

        Logger.log("i", f"[MODEL_DEBUG] Found {len(model_nodes)} model nodes")

        # 如果有保存的模型数据，尝试匹配并选择
        if self._model_parameter_data and model_nodes:
            Logger.log("i", f"[MODEL_DEBUG] Available saved models: {list(self._model_parameter_data.keys())}")

            # 尝试找到匹配的模型
            for node in model_nodes:
                node_name = node.getName() if hasattr(node, 'getName') else str(id(node))
                Logger.log("i", f"[MODEL_DEBUG] Checking node: {node_name}")

                if node_name in self._model_parameter_data:
                    Logger.log("i", f"[MODEL_DEBUG] Found matching saved model: {node_name}")
                    # 选择这个节点
                    Selection.clear()
                    Selection.add(node)
                    Logger.log("i", f"[MODEL_DEBUG] Selected model: {node_name}")
                    break
            else:
                # 如果没有匹配的，选择第一个模型
                if model_nodes:
                    Selection.clear()
                    Selection.add(model_nodes[0])
                    Logger.log("i", f"[MODEL_DEBUG] Selected first available model: {model_nodes[0].getName()}")

        Logger.log("i", "[MODEL_DEBUG] ========== _restoreModelSelection end ==========")

    def _addPreferenceKeys(self):
        """添加偏好设置键"""
        try:
            preferences = self._application.getPreferences()
            pref_key = "ZParameterEditor/model_parameter_data"
            Logger.log("i", f"[STORAGE_DEBUG] Checking preference key: {pref_key}")

            # 检查键是否已存在
            try:
                existing_value = preferences.getValue(pref_key)
                Logger.log("i", f"[STORAGE_DEBUG] Preference key already exists with value: {existing_value}")
            except:
                # 键不存在，添加它
                preferences.addPreference(pref_key, "{}")
                Logger.log("i", f"[STORAGE_DEBUG] Added preference key: {pref_key}")

        except Exception as e:
            Logger.log("e", f"[STORAGE_DEBUG] Error adding preference keys: {str(e)}")
            import traceback
            Logger.log("e", f"[STORAGE_DEBUG] Traceback: {traceback.format_exc()}")

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



    def setParameterDataSlot(self, data):
        """QML可调用的设置参数数据槽函数"""
        Logger.log("i", f"[保存] ========== setParameterDataSlot被调用 ==========")
        Logger.log("i", f"[保存] 接收到的数据: {data}")
        Logger.log("i", f"[保存] 数据类型: {type(data)}")

        try:
            # 处理QJSValue对象
            if hasattr(data, 'toVariant'):
                Logger.log("i", f"[保存] 转换QJSValue为Python对象")
                data = data.toVariant()
                Logger.log("i", f"[保存] 转换后的数据: {data}")
                Logger.log("i", f"[保存] 转换后的数据类型: {type(data)}")

            if isinstance(data, dict):
                parameter_key = data.get("parameterKey")
                state_data = data.get("stateData")
                Logger.log("i", f"[保存] 参数键: {parameter_key}")
                Logger.log("i", f"[保存] 状态数据: {state_data}")

                if parameter_key and state_data:
                    Logger.log("i", f"[保存] 调用setParameterData方法")
                    self.setParameterData(parameter_key, state_data)
                    Logger.log("i", f"[保存] setParameterData调用完成")
                    return True
                else:
                    Logger.log("e", f"[保存] 参数键或状态数据为空")
            else:
                Logger.log("e", f"[保存] 数据不是字典类型")
        except Exception as e:
            Logger.log("e", f"[保存] 处理数据时出错: {e}")

        Logger.log("i", f"[保存] ========== setParameterDataSlot结束 ==========")
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
    def applyParameterSettingsSlot(self, combined_params):
        """QML可调用的应用参数设置槽函数"""
        Logger.log("i", f"[APPLY_DEBUG] applyParameterSettingsSlot called with combined_params: {combined_params}")
        try:
            # 解析组合参数
            parts = combined_params.split(",", 1)  # 只分割第一个逗号
            if len(parts) == 2:
                parameter_key = parts[0].strip()
                formatted_value = parts[1].strip()
                Logger.log("i", f"[APPLY_DEBUG] Parsed - key: {parameter_key}, value: {formatted_value}")
                self.applyParameterSettings(parameter_key, formatted_value)
            else:
                Logger.log("e", f"[APPLY_DEBUG] Invalid parameter format: {combined_params}")
        except Exception as e:
            Logger.log("e", f"[APPLY_DEBUG] Error parsing parameters: {e}")
        
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
        """Update model height when selection changes and handle model-specific data"""
        Logger.log("i", "[MODEL_DEBUG] Selection changed")

        # 保存当前模型的数据
        self._saveCurrentModelData()

        # 更新当前选中的模型ID
        self._updateCurrentModelId()

        # 更新模型高度
        self._updateModelHeight()

        # 加载新选中模型的数据
        self._loadCurrentModelData()

    def _onSceneChanged(self, source):
        """场景变化处理 - 清理已删除模型的数据"""
        Logger.log("i", "[MODEL_DEBUG] Scene changed, checking for removed models")
        self._cleanupRemovedModels()
        
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

        # 只有当高度真正改变时才记录
        if abs(old_height - self._model_height) > 0.1:
            Logger.log("i", f"[CORE_DEBUG] Model height changed from {old_height} to {self._model_height}")
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
        """Set property value - Extension不需要propertyChanged信号"""
        if property_name == "CurrentParameterType":
            if value in self._parameter_types:
                self._current_parameter_type = value
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
                return
            else:
                insert_index = i + 1

        data.insert(insert_index, point)

    def removeParameterPoint(self, index):
        """Remove a parameter point by index"""
        if self._current_parameter_type in self._parameter_data:
            data = self._parameter_data[self._current_parameter_type]
            if 0 <= index < len(data):
                data.pop(index)

    def clearParameterData(self):
        """Clear all parameter data for current type"""
        if self._current_parameter_type in self._parameter_data:
            self._parameter_data[self._current_parameter_type] = []

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
            # 根据参数类型确定对应的enable参数（修正参数名称）
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
        else:
            Logger.log("i", f"[DEBUG] No saved state found for: {parameter_type}")

    @pyqtSlot(str)
    def setCurrentParameterTypeSlot(self, parameter_type):
        """设置当前参数类型并恢复状态"""
        Logger.log("i", f"[SWITCH_DEBUG] ========== setCurrentParameterTypeSlot called ==========")
        Logger.log("i", f"[SWITCH_DEBUG] New parameter type: {parameter_type}")
        Logger.log("i", f"[SWITCH_DEBUG] Old parameter type: {self._current_parameter_type}")
        Logger.log("i", f"[SWITCH_DEBUG] Current model ID: {self._current_model_id}")
        Logger.log("i", f"[SWITCH_DEBUG] Current parameter states: {self._parameter_states}")
        Logger.log("i", f"[SWITCH_DEBUG] Current model parameter data: {self._model_parameter_data}")

        # 保存当前参数类型的数据到当前模型
        if self._current_parameter_type and self._current_model_id:
            Logger.log("i", f"[SWITCH_DEBUG] Saving current parameter data before switch")
            self._saveCurrentModelData()
        else:
            Logger.log("i", f"[SWITCH_DEBUG] No current parameter type or model ID, skipping save")

        # 切换到新参数类型
        old_parameter_type = self._current_parameter_type
        self._current_parameter_type = parameter_type
        Logger.log("i", f"[SWITCH_DEBUG] Parameter type changed from {old_parameter_type} to {parameter_type}")

        # 加载新参数类型的数据
        Logger.log("i", f"[SWITCH_DEBUG] Loading data for new parameter type")
        self._loadCurrentModelData()

        Logger.log("i", f"[SWITCH_DEBUG] Final parameter states: {self._parameter_states}")
        Logger.log("i", f"[SWITCH_DEBUG] ========== setCurrentParameterTypeSlot end ==========")

        # Extension不需要发射propertyChanged信号

    @pyqtSlot(str, str)
    def setParameterData(self, parameter_type, data_json):
        """设置参数数据"""
        Logger.log("i", f"[保存] ========== 开始保存参数数据 ==========")
        Logger.log("i", f"[保存] 参数类型: {parameter_type}")
        Logger.log("i", f"[保存] 数据JSON: {data_json}")
        Logger.log("i", f"[保存] 当前模型ID: '{self._current_model_id}'")
        Logger.log("i", f"[保存] 模型ID是否为空: {self._current_model_id is None}")
        Logger.log("i", f"[保存] 模型ID长度: {len(str(self._current_model_id)) if self._current_model_id else 0}")

        try:
            data = json.loads(data_json)
            Logger.log("i", f"[保存] 解析后的数据: {data}")
            Logger.log("i", f"[保存] 控制点数量: {len(data.get('controlPoints', []))}")

            # 保存到当前参数状态中
            self._parameter_states[parameter_type] = data.copy()
            Logger.log("i", f"[保存] 已保存到参数状态")

            # 如果有当前模型，也保存到模型数据中
            if self._current_model_id:
                Logger.log("i", f"[保存] 有模型ID，开始保存到模型数据")
                if self._current_model_id not in self._model_parameter_data:
                    self._model_parameter_data[self._current_model_id] = {}
                    Logger.log("i", f"[保存] 为模型创建新数据条目: {self._current_model_id}")

                self._model_parameter_data[self._current_model_id][parameter_type] = data.copy()
                Logger.log("i", f"[保存] 已保存到模型数据，控制点数: {len(data.get('controlPoints', []))}")
                Logger.log("i", f"[保存] 模型数据: {self._model_parameter_data[self._current_model_id]}")

                # 立即保存到偏好设置
                self._saveModelParameterData()
                Logger.log("i", f"[保存] 已调用持久化保存")
            else:
                Logger.log("e", f"[保存] ❌ 没有当前模型ID，数据未保存到持久化存储！")

            Logger.log("i", f"[保存] ========== 参数数据保存完成 ==========")
        except Exception as e:
            Logger.log("e", f"[保存] 保存参数数据时出错: {str(e)}")
            import traceback
            Logger.log("e", f"[保存] 错误堆栈: {traceback.format_exc()}")

    @pyqtSlot(str, result=str)
    def getParameterData(self, parameter_type):
        """获取参数数据"""
        Logger.log("i", f"[LOAD_DEBUG] ========== getParameterData called ==========")
        Logger.log("i", f"[LOAD_DEBUG] Parameter type: {parameter_type}")
        Logger.log("i", f"[LOAD_DEBUG] Current model ID: {self._current_model_id}")
        Logger.log("i", f"[LOAD_DEBUG] Available parameter states: {list(self._parameter_states.keys())}")
        Logger.log("i", f"[LOAD_DEBUG] Full parameter states: {self._parameter_states}")
        Logger.log("i", f"[LOAD_DEBUG] Model parameter data: {self._model_parameter_data}")

        # 优先从当前模型的保存数据中读取
        if self._current_model_id and self._current_model_id in self._model_parameter_data:
            model_data = self._model_parameter_data[self._current_model_id]
            Logger.log("i", f"[LOAD_DEBUG] Found model data for {self._current_model_id}: {model_data}")
            if parameter_type in model_data:
                data = model_data[parameter_type]
                Logger.log("i", f"[LOAD_DEBUG] Found saved parameter data for {parameter_type}: {data}")
                Logger.log("i", f"[LOAD_DEBUG] Data type: {type(data)}")

                # 同时更新到parameter_states中，保持一致性
                self._parameter_states[parameter_type] = data.copy()
                Logger.log("i", f"[LOAD_DEBUG] Updated parameter_states with saved data")

                result = json.dumps(data)
                Logger.log("i", f"[LOAD_DEBUG] Returning saved JSON: {result}")
                Logger.log("i", f"[LOAD_DEBUG] ========== getParameterData end (from model data) ==========")
                return result
            else:
                Logger.log("i", f"[LOAD_DEBUG] No saved data for parameter {parameter_type} in model {self._current_model_id}")
        else:
            Logger.log("i", f"[LOAD_DEBUG] No model data available - current_model_id: {self._current_model_id}, model_parameter_data keys: {list(self._model_parameter_data.keys()) if self._model_parameter_data else 'None'}")

        # 其次从当前会话的parameter_states中读取
        if parameter_type in self._parameter_states:
            data = self._parameter_states[parameter_type]
            Logger.log("i", f"[LOAD_DEBUG] Found parameter state: {data}")
            Logger.log("i", f"[LOAD_DEBUG] Data type: {type(data)}")
            result = json.dumps(data)
            Logger.log("i", f"[LOAD_DEBUG] Returning session JSON: {result}")
            Logger.log("i", f"[LOAD_DEBUG] ========== getParameterData end (from session) ==========")
            return result
        else:
            Logger.log("i", f"[LOAD_DEBUG] No parameter data found for {parameter_type}")
            Logger.log("i", f"[LOAD_DEBUG] Returning empty object")
            Logger.log("i", f"[LOAD_DEBUG] ========== getParameterData end (not found) ==========")
            return "{}"

    def _loadModelParameterData(self):
        """从偏好设置中加载模型参数数据"""
        Logger.log("i", f"[STORAGE_DEBUG] ========== _loadModelParameterData called ==========")
        try:
            preferences = self._application.getPreferences()
            pref_key = "ZParameterEditor/model_parameter_data"
            Logger.log("i", f"[STORAGE_DEBUG] Preference key: {pref_key}")

            pref_value = preferences.getValue(pref_key)
            Logger.log("i", f"[STORAGE_DEBUG] Raw preference value: {pref_value}")
            Logger.log("i", f"[STORAGE_DEBUG] Preference value type: {type(pref_value)}")

            if pref_value:
                data_json = pref_value
                Logger.log("i", f"[STORAGE_DEBUG] JSON to parse: {data_json}")
                self._model_parameter_data = json.loads(data_json)
                Logger.log("i", f"[STORAGE_DEBUG] Loaded model parameter data: {self._model_parameter_data}")
                Logger.log("i", f"[STORAGE_DEBUG] Number of models: {len(self._model_parameter_data)}")
                for model_id, model_data in self._model_parameter_data.items():
                    Logger.log("i", f"[STORAGE_DEBUG] Model {model_id}: {model_data}")
            else:
                Logger.log("i", "[STORAGE_DEBUG] No saved model parameter data found")
                self._model_parameter_data = {}
            Logger.log("i", f"[STORAGE_DEBUG] ========== _loadModelParameterData end ==========")
        except Exception as e:
            Logger.log("e", f"[STORAGE_DEBUG] Error loading model parameter data: {str(e)}")
            import traceback
            Logger.log("e", f"[STORAGE_DEBUG] Traceback: {traceback.format_exc()}")
            self._model_parameter_data = {}

    def _saveModelParameterData(self):
        """保存模型参数数据到偏好设置"""
        Logger.log("i", f"[STORAGE_DEBUG] ========== _saveModelParameterData called ==========")
        try:
            preferences = self._application.getPreferences()
            pref_key = "ZParameterEditor/model_parameter_data"
            Logger.log("i", f"[STORAGE_DEBUG] Preference key: {pref_key}")
            Logger.log("i", f"[STORAGE_DEBUG] Data to save: {self._model_parameter_data}")
            Logger.log("i", f"[STORAGE_DEBUG] Number of models: {len(self._model_parameter_data)}")

            json_data = json.dumps(self._model_parameter_data)
            Logger.log("i", f"[STORAGE_DEBUG] JSON data: {json_data}")
            Logger.log("i", f"[STORAGE_DEBUG] JSON data length: {len(json_data)}")

            preferences.setValue(pref_key, json_data)
            Logger.log("i", f"[STORAGE_DEBUG] Data saved to preferences")

            # 验证保存是否成功
            saved_value = preferences.getValue(pref_key)
            Logger.log("i", f"[STORAGE_DEBUG] Verification - saved value: {saved_value}")
            Logger.log("i", f"[STORAGE_DEBUG] Verification - matches original: {saved_value == json_data}")
            Logger.log("i", f"[STORAGE_DEBUG] ========== _saveModelParameterData end ==========")
        except Exception as e:
            Logger.log("e", f"[STORAGE_DEBUG] Error saving model parameter data: {str(e)}")
            import traceback
            Logger.log("e", f"[STORAGE_DEBUG] Traceback: {traceback.format_exc()}")

    def _updateCurrentModelId(self):
        """更新当前选中的模型ID"""
        selected_nodes = Selection.getAllSelectedObjects()
        if selected_nodes:
            # 使用第一个选中节点的ID
            node = selected_nodes[0]
            Logger.log("i", f"[MODEL_DEBUG] Processing node: {node}")

            # 使用统一的方法获取模型ID
            model_id = self._getNodeModelId(node)
            Logger.log("i", f"[MODEL_DEBUG] Model ID: '{model_id}'")

            self._current_model_id = model_id
            Logger.log("i", f"[MODEL_DEBUG] Current model ID updated to: '{self._current_model_id}'")

            # 加载该模型的保存数据到当前会话
            self._loadModelDataToSession()
        else:
            self._current_model_id = None
            Logger.log("i", "[MODEL_DEBUG] No selection, current model ID set to None")

    def _loadModelDataToSession(self):
        """将当前模型的保存数据加载到会话中"""
        if not self._current_model_id:
            Logger.log("i", "[LOAD_DEBUG] No current model ID, skipping data load")
            return

        Logger.log("i", f"[LOAD_DEBUG] ========== _loadModelDataToSession called ==========")
        Logger.log("i", f"[LOAD_DEBUG] Loading data for model: {self._current_model_id}")
        Logger.log("i", f"[LOAD_DEBUG] Available model data: {list(self._model_parameter_data.keys())}")

        if self._current_model_id in self._model_parameter_data:
            model_data = self._model_parameter_data[self._current_model_id]
            Logger.log("i", f"[LOAD_DEBUG] Found saved data for model: {model_data}")

            # 将模型数据复制到当前会话的parameter_states中
            for parameter_type, parameter_data in model_data.items():
                self._parameter_states[parameter_type] = parameter_data.copy()
                Logger.log("i", f"[LOAD_DEBUG] Loaded {parameter_type}: {parameter_data}")

            Logger.log("i", f"[LOAD_DEBUG] Updated parameter_states: {self._parameter_states}")
        else:
            Logger.log("i", f"[LOAD_DEBUG] No saved data found for model: {self._current_model_id}")
            # 清空当前会话数据，因为这是一个新模型
            self._parameter_states = {}
            Logger.log("i", f"[LOAD_DEBUG] Cleared parameter_states for new model")

        Logger.log("i", f"[LOAD_DEBUG] ========== _loadModelDataToSession end ==========")

    def _saveCurrentModelData(self):
        """保存当前模型的参数数据"""
        if not self._current_model_id:
            return

        Logger.log("i", f"[MODEL_DEBUG] Saving data for model: {self._current_model_id}")

        # 确保模型数据字典存在
        if self._current_model_id not in self._model_parameter_data:
            self._model_parameter_data[self._current_model_id] = {}

        # 保存当前参数类型的数据
        if self._current_parameter_type in self._parameter_states:
            self._model_parameter_data[self._current_model_id][self._current_parameter_type] = \
                self._parameter_states[self._current_parameter_type].copy()
            Logger.log("i", f"[MODEL_DEBUG] Saved {self._current_parameter_type} data for model {self._current_model_id}")

            # 保存到偏好设置
            self._saveModelParameterData()

    def _loadCurrentModelData(self):
        """加载当前模型的参数数据"""
        Logger.log("i", f"[LOAD_MODEL_DEBUG] ========== _loadCurrentModelData called ==========")
        Logger.log("i", f"[LOAD_MODEL_DEBUG] Current model ID: {self._current_model_id}")
        Logger.log("i", f"[LOAD_MODEL_DEBUG] Current parameter type: {self._current_parameter_type}")
        Logger.log("i", f"[LOAD_MODEL_DEBUG] Available model data: {list(self._model_parameter_data.keys())}")
        Logger.log("i", f"[LOAD_MODEL_DEBUG] Full model parameter data: {self._model_parameter_data}")
        Logger.log("i", f"[LOAD_MODEL_DEBUG] Current parameter states: {self._parameter_states}")

        if not self._current_model_id:
            Logger.log("i", "[LOAD_MODEL_DEBUG] No current model, using default initialization")
            self._initializeParameterWithModelHeight()
            Logger.log("i", f"[LOAD_MODEL_DEBUG] ========== _loadCurrentModelData end (no model) ==========")
            return

        Logger.log("i", f"[LOAD_MODEL_DEBUG] Loading data for model: {self._current_model_id}")

        # 检查是否有保存的数据
        model_has_data = self._current_model_id in self._model_parameter_data
        Logger.log("i", f"[LOAD_MODEL_DEBUG] Model has data: {model_has_data}")

        if model_has_data:
            model_data = self._model_parameter_data[self._current_model_id]
            Logger.log("i", f"[LOAD_MODEL_DEBUG] Model data: {model_data}")
            param_has_data = self._current_parameter_type in model_data
            Logger.log("i", f"[LOAD_MODEL_DEBUG] Parameter has data: {param_has_data}")
        else:
            param_has_data = False

        if model_has_data and param_has_data:
            # 加载保存的数据
            saved_data = self._model_parameter_data[self._current_model_id][self._current_parameter_type]
            Logger.log("i", f"[LOAD_MODEL_DEBUG] Found saved data for parameter: {self._current_parameter_type}")
            Logger.log("i", f"[LOAD_MODEL_DEBUG] Saved data: {saved_data}")
            Logger.log("i", f"[LOAD_MODEL_DEBUG] Saved data type: {type(saved_data)}")

            # Extension不需要设置Tool相关属性，数据已经在_parameter_states中
            self._parameter_states[self._current_parameter_type] = saved_data.copy()
            Logger.log("i", f"[LOAD_MODEL_DEBUG] Loaded saved parameter data to parameter states")
            Logger.log("i", f"[LOAD_MODEL_DEBUG] Parameter states after load: {self._parameter_states}")
        else:
            Logger.log("i", f"[LOAD_MODEL_DEBUG] No saved data found, initializing with model height")
            self._initializeParameterWithModelHeight()

        Logger.log("i", f"[LOAD_MODEL_DEBUG] ========== _loadCurrentModelData end ==========")

    def _initializeParameterWithModelHeight(self):
        """使用模型高度初始化参数数据"""
        Logger.log("i", f"[MODEL_DEBUG] Initializing parameter with model height: {self._model_height}")

        # 获取参数类型信息
        param_info = None
        for _, info in self._parameter_types.items():
            if info["setting_key"] == self._current_parameter_type:
                param_info = info
                break

        if not param_info:
            Logger.log("e", f"[MODEL_DEBUG] Could not find parameter info for {self._current_parameter_type}")
            return

        # 使用模型高度和参数默认值创建初始控制点
        default_value = param_info["default_value"]
        model_height = max(self._model_height, 1.0)  # 确保最小高度为1mm

        initial_data = {
            "controlPoints": [
                {"z": 0, "value": default_value},
                {"z": model_height, "value": default_value}
            ],
            "curveMode": "bezier",
            "minValue": param_info["min_value"],
            "maxValue": param_info["max_value"]
        }

        self._parameter_states[self._current_parameter_type] = initial_data
        Logger.log("i", f"[MODEL_DEBUG] Initialized parameter data: {initial_data}")

    def _getNodeModelId(self, node):
        """获取节点的模型ID，使用与_updateCurrentModelId相同的逻辑"""
        model_id = None
        if hasattr(node, 'getId'):
            node_id = node.getId()
            if node_id and node_id.strip():  # 确保ID不是空字符串
                model_id = node_id

        if not model_id and hasattr(node, 'getName'):
            node_name = node.getName()
            if node_name and node_name.strip():
                model_id = node_name

        if not model_id:
            # 使用对象的内存地址作为唯一标识
            model_id = str(id(node))

        return model_id

    def _cleanupRemovedModels(self):
        """清理已删除模型的数据"""
        if not self._model_parameter_data:
            return

        Logger.log("i", f"[MODEL_DEBUG] ========== _cleanupRemovedModels called ==========")
        Logger.log("i", f"[MODEL_DEBUG] Current model parameter data keys: {list(self._model_parameter_data.keys())}")

        # 获取当前场景中的所有模型ID
        current_model_ids = set()
        for node in DepthFirstIterator(self._application.getController().getScene().getRoot()):
            if hasattr(node, 'getMeshData') and node.getMeshData():
                model_id = self._getNodeModelId(node)
                current_model_ids.add(model_id)
                Logger.log("i", f"[MODEL_DEBUG] Found model in scene: {model_id}")

        Logger.log("i", f"[MODEL_DEBUG] Current scene model IDs: {current_model_ids}")

        # 删除不再存在的模型数据
        models_to_remove = []
        for model_id in self._model_parameter_data.keys():
            if model_id not in current_model_ids:
                models_to_remove.append(model_id)
                Logger.log("i", f"[MODEL_DEBUG] Model to remove: {model_id}")

        for model_id in models_to_remove:
            del self._model_parameter_data[model_id]
            Logger.log("i", f"[MODEL_DEBUG] Cleaned up data for removed model: {model_id}")

        Logger.log("i", f"[MODEL_DEBUG] ========== _cleanupRemovedModels end ==========")
        Logger.log("i", f"[MODEL_DEBUG] Remaining model parameter data keys: {list(self._model_parameter_data.keys())}")

    # 3D截线显示相关方法
    def _createCrossSectionMesh(self, z_height: float) -> MeshData:
        """创建水平截线的网格数据 - 计算模型与平面的交线"""
        Logger.log("i", f"[CROSS_SECTION] Creating cross section mesh at Z={z_height}")

        # 获取选中的模型
        selected_nodes = Selection.getAllSelectedObjects()
        Logger.log("i", f"[CROSS_SECTION] Selected nodes count: {len(selected_nodes)}")
        if not selected_nodes:
            Logger.log("w", "[CROSS_SECTION] No selected nodes found")
            return None

        # 使用第一个选中的模型
        selected_node = selected_nodes[0]
        Logger.log("i", f"[CROSS_SECTION] Using selected node: {selected_node.getName()}")

        # 获取网格数据
        mesh_data = selected_node.getMeshData()
        if not mesh_data:
            Logger.log("w", "[CROSS_SECTION] No mesh data found for selected node")
            return None

        Logger.log("i", f"[CROSS_SECTION] Mesh data vertices count: {mesh_data.getVertexCount()}")
        Logger.log("i", f"[CROSS_SECTION] Mesh data face count: {mesh_data.getFaceCount()}")
        Logger.log("i", f"[CROSS_SECTION] Mesh data has vertices: {mesh_data.getVertices() is not None}")
        Logger.log("i", f"[CROSS_SECTION] Mesh data has indices: {mesh_data.hasIndices()}")

        # 尝试获取变换后的网格数据
        transformation = selected_node.getWorldTransformation()
        Logger.log("i", f"[CROSS_SECTION] Node transformation: {transformation}")

        # 检查是否需要应用变换（简单检查是否为单位矩阵）
        try:
            # 手动检查是否为单位矩阵
            matrix_data = transformation.getData()
            identity_matrix = np.eye(4, dtype=np.float32)
            is_identity = np.allclose(matrix_data, identity_matrix, atol=1e-6)
            Logger.log("i", f"[CROSS_SECTION] Is identity matrix: {is_identity}")
        except Exception as e:
            Logger.log("w", f"[CROSS_SECTION] Error checking transformation: {e}")
            is_identity = True  # 假设是单位矩阵，跳过变换

        if transformation and not is_identity:
            Logger.log("i", "[CROSS_SECTION] Applying transformation to mesh data")
            try:
                mesh_data = mesh_data.getTransformed(transformation)
                Logger.log("i", f"[CROSS_SECTION] Transformed mesh data vertices count: {mesh_data.getVertexCount()}")
            except Exception as e:
                Logger.log("w", f"[CROSS_SECTION] Error applying transformation: {e}")
        else:
            Logger.log("i", "[CROSS_SECTION] Skipping transformation (identity matrix or error)")

        # 计算模型与平面的交线
        intersection_lines = self._calculatePlaneIntersection(mesh_data, z_height)
        Logger.log("i", f"[CROSS_SECTION] Intersection lines count: {len(intersection_lines) if intersection_lines else 0}")
        if not intersection_lines:
            Logger.log("w", "[CROSS_SECTION] No intersection lines found")
            return None

        # 创建线段网格
        builder = MeshBuilder()

        # 为每条线段创建一个小的管状几何体以便可见
        line_width = 1.0  # 加粗线宽
        color = Color(1.0, 0.0, 0.0, 1.0)  # 红色不透明

        for i, line in enumerate(intersection_lines):
            Logger.log("d", f"[CROSS_SECTION] Adding line {i}: {line[0]} -> {line[1]}")
            self._addLineToMesh(builder, line[0], line[1], line_width, color)

        mesh_result = builder.build()
        Logger.log("i", f"[CROSS_SECTION] Built mesh with {mesh_result.getVertexCount() if mesh_result else 0} vertices")
        return mesh_result

    def _calculatePlaneIntersection(self, mesh_data: MeshData, z_height: float):
        """计算网格与水平平面的交线（Y轴截面）"""
        Logger.log("i", f"[CROSS_SECTION] Calculating plane intersection at Y={z_height}")

        vertices = mesh_data.getVertices()
        indices = mesh_data.getIndices()

        Logger.log("i", f"[CROSS_SECTION] Vertices type: {type(vertices)}, value: {vertices is not None}")
        Logger.log("i", f"[CROSS_SECTION] Indices type: {type(indices)}, value: {indices is not None}")

        if vertices is not None:
            Logger.log("i", f"[CROSS_SECTION] Vertices shape: {vertices.shape if hasattr(vertices, 'shape') else 'no shape'}")
        if indices is not None:
            Logger.log("i", f"[CROSS_SECTION] Indices shape: {indices.shape if hasattr(indices, 'shape') else 'no shape'}")

        if vertices is None:
            Logger.log("w", "[CROSS_SECTION] Vertices is None")
            return []

        # 添加调试信息：检查顶点Y范围（Cura中Y轴是高度）
        y_coords = vertices[:, 1]  # 获取所有Y坐标
        min_y = np.min(y_coords)
        max_y = np.max(y_coords)
        Logger.log("i", f"[CROSS_SECTION] Mesh Y range: {min_y:.3f} to {max_y:.3f}, target Y: {z_height:.3f}")

        intersection_lines = []
        triangle_count = 0
        processed_count = 0

        if indices is not None:
            # 有索引的网格 - 使用索引访问顶点
            triangle_count = len(indices) // 3
            Logger.log("i", f"[CROSS_SECTION] Processing indexed mesh with {triangle_count} triangles")

            # 性能优化：每隔一定数量处理一个三角形
            step = max(1, triangle_count // 50000)  # 限制最多处理50000个三角形

            for i in range(0, len(indices), 3 * step):
                # 获取三角形的三个顶点
                v0_idx, v1_idx, v2_idx = indices[i], indices[i+1], indices[i+2]
                v0 = vertices[v0_idx]
                v1 = vertices[v1_idx]
                v2 = vertices[v2_idx]

                # 计算三角形与平面的交线
                line_segment = self._trianglePlaneIntersection(v0, v1, v2, z_height)
                if line_segment:
                    intersection_lines.append(line_segment)
                processed_count += 1
        else:
            # 无索引的网格 - 每3个顶点组成一个三角形
            triangle_count = len(vertices) // 3
            Logger.log("i", f"[CROSS_SECTION] Processing non-indexed mesh with {triangle_count} triangles")

            # 性能优化：每隔一定数量处理一个三角形
            step = max(1, triangle_count // 50000)  # 限制最多处理50000个三角形

            for i in range(0, len(vertices), 3 * step):
                if i + 2 >= len(vertices):
                    break

                # 获取三角形的三个顶点
                v0 = vertices[i]
                v1 = vertices[i+1]
                v2 = vertices[i+2]

                # 计算三角形与平面的交线
                line_segment = self._trianglePlaneIntersection(v0, v1, v2, z_height)
                if line_segment:
                    intersection_lines.append(line_segment)
                processed_count += 1

        Logger.log("i", f"[CROSS_SECTION] Processed {processed_count}/{triangle_count} triangles, found {len(intersection_lines)} intersection line segments")

        # 简化线段：合并相近的线段，减少数量
        simplified_lines = self._simplifyIntersectionLines(intersection_lines)
        Logger.log("i", f"[CROSS_SECTION] Simplified to {len(simplified_lines)} line segments")

        return simplified_lines

    def _createCrossSectionPlane(self, z_height: float):
        """创建水平截面平面"""
        Logger.log("i", f"[CROSS_SECTION] Creating cross section plane at Z={z_height}")

        # 获取选中的模型
        selected_nodes = Selection.getAllSelectedObjects()
        if not selected_nodes:
            Logger.log("w", "[CROSS_SECTION] No selected objects")
            return None

        # 获取模型的边界框
        node = selected_nodes[0]
        bounding_box = node.getBoundingBox()
        if not bounding_box:
            Logger.log("w", "[CROSS_SECTION] No bounding box")
            return None

        # 计算平面大小（稍微大于模型）
        min_x = bounding_box.minimum.x - 10
        max_x = bounding_box.maximum.x + 10
        min_z = bounding_box.minimum.z - 10
        max_z = bounding_box.maximum.z + 10

        # 将Z高度转换为Y坐标（因为我们使用Y轴作为高度）
        y_pos = z_height

        # 创建半透明的矩形平面
        builder = MeshBuilder()

        # 定义平面的四个顶点
        v1 = Vector(min_x, y_pos, min_z)
        v2 = Vector(max_x, y_pos, min_z)
        v3 = Vector(max_x, y_pos, max_z)
        v4 = Vector(min_x, y_pos, max_z)

        # 添加两个三角形组成矩形（双面渲染）
        # 正面
        builder.addFaceByPoints(v1.x, v1.y, v1.z, v2.x, v2.y, v2.z, v3.x, v3.y, v3.z)
        builder.addFaceByPoints(v1.x, v1.y, v1.z, v3.x, v3.y, v3.z, v4.x, v4.y, v4.z)

        # 反面（确保双面可见）
        builder.addFaceByPoints(v1.x, v1.y, v1.z, v3.x, v3.y, v3.z, v2.x, v2.y, v2.z)
        builder.addFaceByPoints(v1.x, v1.y, v1.z, v4.x, v4.y, v4.z, v3.x, v3.y, v3.z)

        mesh_result = builder.build()
        Logger.log("i", f"[CROSS_SECTION] Created cross section plane with {mesh_result.getVertexCount() if mesh_result else 0} vertices")
        return mesh_result

    def _simplifyIntersectionLines(self, intersection_lines):
        """简化交线：合并相近的线段，减少数量"""
        if not intersection_lines:
            return []

        # 设置简化参数
        min_distance = 1.0  # 最小线段长度（mm）
        merge_distance = 0.5  # 合并距离阈值（mm）

        simplified = []

        for line in intersection_lines:
            p1, p2 = line

            # 计算线段长度
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            dz = p2[2] - p1[2]
            length = (dx*dx + dy*dy + dz*dz) ** 0.5

            # 过滤太短的线段
            if length < min_distance:
                continue

            # 检查是否可以与现有线段合并
            merged = False
            for i, existing_line in enumerate(simplified):
                ep1, ep2 = existing_line

                # 检查端点是否相近
                if (self._pointDistance(p1, ep1) < merge_distance and self._pointDistance(p2, ep2) < merge_distance) or \
                   (self._pointDistance(p1, ep2) < merge_distance and self._pointDistance(p2, ep1) < merge_distance):
                    # 合并线段：使用更长的线段
                    existing_length = self._pointDistance(ep1, ep2)
                    if length > existing_length:
                        simplified[i] = (p1, p2)
                    merged = True
                    break

            if not merged:
                simplified.append((p1, p2))

        # 进一步减少线段数量：每隔一定距离采样
        if len(simplified) > 1000:  # 如果线段太多，进行采样
            step = len(simplified) // 500  # 最多保留500条线段
            simplified = simplified[::step]

        return simplified

    def _pointDistance(self, p1, p2):
        """计算两点之间的距离"""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dz = p2[2] - p1[2]
        return (dx*dx + dy*dy + dz*dz) ** 0.5

    def _trianglePlaneIntersection(self, v0, v1, v2, z_height):
        """计算三角形与水平平面的交线（Y轴截面）"""
        # 检查顶点相对于平面的位置（使用Y坐标）
        d0 = v0[1] - z_height  # Y坐标与平面的距离
        d1 = v1[1] - z_height
        d2 = v2[1] - z_height

        # 如果所有顶点都在平面同一侧，没有交线
        if (d0 > 0 and d1 > 0 and d2 > 0) or (d0 < 0 and d1 < 0 and d2 < 0):
            return None

        # 如果所有顶点都在平面上，忽略（退化情况）
        if abs(d0) < 1e-6 and abs(d1) < 1e-6 and abs(d2) < 1e-6:
            return None

        # 找到与平面相交的边
        intersection_points = []

        # 检查边 v0-v1
        if (d0 > 0) != (d1 > 0) and abs(d0 - d1) > 1e-6:  # 边跨越平面
            t = d0 / (d0 - d1)
            point = [
                v0[0] + t * (v1[0] - v0[0]),
                z_height,  # Y坐标固定为截面高度
                v0[2] + t * (v1[2] - v0[2])
            ]
            intersection_points.append(point)

        # 检查边 v1-v2
        if (d1 > 0) != (d2 > 0) and abs(d1 - d2) > 1e-6:  # 边跨越平面
            t = d1 / (d1 - d2)
            point = [
                v1[0] + t * (v2[0] - v1[0]),
                z_height,  # Y坐标固定为截面高度
                v1[2] + t * (v2[2] - v1[2])
            ]
            intersection_points.append(point)

        # 检查边 v2-v0
        if (d2 > 0) != (d0 > 0) and abs(d2 - d0) > 1e-6:  # 边跨越平面
            t = d2 / (d2 - d0)
            point = [
                v2[0] + t * (v0[0] - v2[0]),
                z_height,  # Y坐标固定为截面高度
                v2[2] + t * (v0[2] - v2[2])
            ]
            intersection_points.append(point)

        # 如果有两个交点，返回线段
        if len(intersection_points) == 2:
            return (intersection_points[0], intersection_points[1])

        return None

    def _addLineToMesh(self, builder: MeshBuilder, p1, p2, width: float, color: Color):
        """将线段添加到网格中，创建一个加粗的管状几何体"""
        # 计算线段方向
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dz = p2[2] - p1[2]
        length = (dx*dx + dy*dy + dz*dz) ** 0.5

        if length < 1e-6:
            return

        # 标准化方向向量
        dx /= length
        dy /= length
        dz /= length

        # 创建两个垂直向量来形成圆形截面
        if abs(dz) < 0.9:
            # 如果不是垂直线，使用Z轴叉积
            perp1_x = -dy
            perp1_y = dx
            perp1_z = 0
        else:
            # 如果是垂直线，使用X轴叉积
            perp1_x = 1
            perp1_y = 0
            perp1_z = 0

        # 标准化第一个垂直向量
        perp1_length = (perp1_x*perp1_x + perp1_y*perp1_y + perp1_z*perp1_z) ** 0.5
        if perp1_length > 1e-6:
            perp1_x /= perp1_length
            perp1_y /= perp1_length
            perp1_z /= perp1_length

        # 创建第二个垂直向量（与第一个垂直向量和方向向量都垂直）
        perp2_x = dy * perp1_z - dz * perp1_y
        perp2_y = dz * perp1_x - dx * perp1_z
        perp2_z = dx * perp1_y - dy * perp1_x

        # 创建八边形截面的顶点（更圆滑的效果）
        half_width = width * 0.5
        segments = 8  # 八边形

        for i in range(segments):
            angle1 = 2 * 3.14159 * i / segments
            angle2 = 2 * 3.14159 * (i + 1) / segments

            # 当前段的顶点
            cos1, sin1 = np.cos(angle1), np.sin(angle1)
            cos2, sin2 = np.cos(angle2), np.sin(angle2)

            # 起点的顶点
            v1_start = Vector(
                p1[0] + (perp1_x * cos1 + perp2_x * sin1) * half_width,
                p1[1] + (perp1_y * cos1 + perp2_y * sin1) * half_width,
                p1[2] + (perp1_z * cos1 + perp2_z * sin1) * half_width
            )
            v2_start = Vector(
                p1[0] + (perp1_x * cos2 + perp2_x * sin2) * half_width,
                p1[1] + (perp1_y * cos2 + perp2_y * sin2) * half_width,
                p1[2] + (perp1_z * cos2 + perp2_z * sin2) * half_width
            )

            # 终点的顶点
            v1_end = Vector(
                p2[0] + (perp1_x * cos1 + perp2_x * sin1) * half_width,
                p2[1] + (perp1_y * cos1 + perp2_y * sin1) * half_width,
                p2[2] + (perp1_z * cos1 + perp2_z * sin1) * half_width
            )
            v2_end = Vector(
                p2[0] + (perp1_x * cos2 + perp2_x * sin2) * half_width,
                p2[1] + (perp1_y * cos2 + perp2_y * sin2) * half_width,
                p2[2] + (perp1_z * cos2 + perp2_z * sin2) * half_width
            )

            # 添加四边形的两个三角形
            builder.addFaceByPoints(v1_start.x, v1_start.y, v1_start.z,
                                  v2_start.x, v2_start.y, v2_start.z,
                                  v1_end.x, v1_end.y, v1_end.z)
            builder.addFaceByPoints(v2_start.x, v2_start.y, v2_start.z,
                                  v2_end.x, v2_end.y, v2_end.z,
                                  v1_end.x, v1_end.y, v1_end.z)

        # 使用传入的颜色（避免未使用变量警告）
        Logger.log("d", f"[CROSS_SECTION] Adding line segment with color: {color}")

    def _createCrossSectionNode(self) -> SceneNode:
        """创建截面指示器场景节点"""
        if self._cross_section_node:
            # 如果已存在，先移除
            self._removeCrossSectionNode()

        # 创建新的场景节点
        self._cross_section_node = SceneNode()
        self._cross_section_node.setSelectable(False)

        # 设置节点属性（使用默认渲染）
        Logger.log("i", "[CROSS_SECTION] Created cross section indicator node")

        # 添加到场景根节点
        scene = self._controller.getScene()
        scene.getRoot().addChild(self._cross_section_node)

        return self._cross_section_node

    def _removeCrossSectionNode(self):
        """移除截线场景节点"""
        if self._cross_section_node:
            if self._cross_section_node.getParent():
                self._cross_section_node.getParent().removeChild(self._cross_section_node)
            self._cross_section_node = None

    def _updateCrossSection(self, z_height: float):
        """更新截面指示器位置"""
        self._cross_section_z = z_height

        if not self._cross_section_visible:
            return

        # 创建水平截面平面
        mesh_data = self._createCrossSectionPlane(z_height)
        if not mesh_data:
            return

        # 如果截面节点不存在，创建它
        if not self._cross_section_node:
            self._createCrossSectionNode()

        # 更新网格数据
        self._cross_section_node.setMeshData(mesh_data)

        # 触发场景更新
        scene = self._controller.getScene()
        scene.sceneChanged.emit(self._cross_section_node)

    @pyqtSlot(float)
    def showCrossSection(self, z_height: float):
        """显示截线"""
        Logger.log("i", f"[CROSS_SECTION] Showing cross section at Z={z_height}")
        self._cross_section_visible = True
        self._updateCrossSection(z_height)

    @pyqtSlot(str)
    def hideCrossSection(self, dummy_param=""):
        """隐藏截线"""
        Logger.log("i", "[CROSS_SECTION] Hiding cross section")
        Logger.log("d", f"[CROSS_SECTION] Dummy param: {dummy_param}")  # 避免未使用变量警告
        self._cross_section_visible = False
        self._removeCrossSectionNode()
