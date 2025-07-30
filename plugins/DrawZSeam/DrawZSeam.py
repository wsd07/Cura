# Copyright (c) 2023 Aldo Hoeben / fieldOfView
# DrawZSeam is released under the terms of the AGPLv3 or higher.

from UM.Tool import Tool
from UM.Event import Event, MouseEvent
from UM.Scene.Selection import Selection
from UM.Scene.SceneNode import SceneNode
from UM.Logger import Logger
from UM.i18n import i18nCatalog
from UM.Version import Version
from PyQt6.QtCore import Qt, QObject
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QVector3D
KeyboardShiftModifier = Qt.KeyboardModifier.ShiftModifier

import json
from collections import OrderedDict
from UM.Extension import Extension
from UM.Application import Application
from UM.Settings.SettingDefinition import SettingDefinition
from UM.Settings.DefinitionContainer import DefinitionContainer
from UM.Settings.ContainerRegistry import ContainerRegistry
from UM.Platform import Platform

from typing import Dict, List, Any

import os.path
from typing import cast, List, Optional
from cura.CuraApplication import CuraApplication
from UM.View.RenderPass import RenderPass
from UM.View.RenderBatch import RenderBatch
from UM.Math.Matrix import Matrix
from UM.Scene.Iterator.DepthFirstIterator import DepthFirstIterator

import os.path
from math import inf
import math

from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from UM.View.GL.ShaderProgram import ShaderProgram

from UM.Mesh.MeshData import MeshData, calculateNormalsFromIndexedVertices
from UM.Scene.ToolHandle import ToolHandle
from UM.Math.Vector import Vector
from UM.View.GL.OpenGL import OpenGL
from UM.Resources import Resources

import trimesh
import numpy

from typing import Optional, TYPE_CHECKING




class DrawZSeam(Tool):
    def __init__(self, parent=None) -> None:
        super().__init__()

        self._application = CuraApplication.getInstance()
        self._controller = self.getController()
        self._measure_passes = []  # type: List[MeasurePass]
        self._measure_passes_dirty = True

        self._toolbutton_item = None  # type: Optional[QObject]
        self._tool_enabled = False
        self._dragging = False
        self._SType = 'add'

        self._from_locked = False
        self._snap_vertices = False

        settings_definition_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "DrawZSeam.def.json"
        )
        try:
            with open(settings_definition_path, "r", encoding="utf-8") as f:
                self._settings_dict = json.load(f, object_pairs_hook=OrderedDict)
        except:
            Logger.logException("e", "Could not load arc welder settings definition")
            return


        Resources.addSearchPath(os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            "resources"
        )))  # Plugin translation file import
        self._i18n_catalog = i18nCatalog("measuretool")

        self._points = []      # 初始化点列表
        self._max_points = 100  # 最大点数
        self._active_point = 0  #
        self._pointScale = 1.0  # 点的放大倍数

        self._handle = (
            DrawZSeamHandle()
        )  # type: DrawZSeamHandle  # Because for some reason MyPy thinks this variable contains Optional[ToolHandle].
        self._handle.setTool(self)

        self.setExposedProperties("FormatPointList", "SType")

        self._application.engineCreatedSignal.connect(self._onEngineCreated)
        Selection.selectionChanged.connect(self._onSelectionChanged)
        self._controller.activeStageChanged.connect(self._onActiveStageChanged)
        self._controller.activeToolChanged.connect(self._onActiveToolChanged)
        self._controller.getScene().sceneChanged.connect(self._onSceneChanged)

        self._selection_tool = None  # type: Optional[Tool]

        self._application.getPreferences().addPreference("DrawZSeam/unit_factor", 1)
        self._application.getPreferences().addPreference("DrawZSeam/settings_made_visible", True)

        ContainerRegistry.getInstance().containerLoadComplete.connect(
            self._onContainerLoadComplete
        )

    def resetPoints(self) -> None:
        self._points = []
        self._active_point = 0
        self.propertyChanged.emit()
        self._controller.getScene().sceneChanged.emit(self._handle)

    def getPoint(self,pointNum) -> QVector3D:
        return self._points[pointNum]

    def getPoints(self) -> [QVector3D]:
        if len(self._points) == 0:
            return [QVector3D()]
        else:
            return self._points

    def getScale(self):
        return self._pointScale

    def setScale(self,scale):
        self._pointScale = scale


    def getActivePoint(self) -> int:
        return self._active_point

    def setActivePoint(self, active_point: int) -> None:
        if active_point != self._active_point:
            self._active_point = active_point
            self.propertyChanged.emit()

    def getFromLocked(self) -> bool:
        return self._from_locked

    def setFromLocked(self, locked) -> None:
        if locked != self._from_locked:
            self._from_locked = locked
            self._active_point = 1
            self.propertyChanged.emit()

    def getSnapVerticesSupported(self) -> bool:
        # Use a dummy postfix, since an equal version with a postfix is considered smaller normally.
        return Version(OpenGL.getInstance().getOpenGLVersion()) >= Version("4.1 dummy-postfix")

    def getSnapVertices(self) -> bool:
        return self._snap_vertices

    def setSnapVertices(self, snap) -> None:
        if snap != self._snap_vertices:
            self._snap_vertices = snap
            self._measure_passes_dirty = True
            self.propertyChanged.emit()

    def format_point(self, point: QVector3D, index):
        # 使用格式化字符串来确保每个坐标占据6个字符的宽度，包括小数点和两位小数
        return f"{index:03}:[{point[0]:6.2f}, {-point[2]:6.2f}, {point[1]:6.2f}]"

    def getFormatPointList(self) -> str:
        formatted_text = ""
        sorted_points = sorted(self._points, key=lambda point: point.y(), reverse=True)
        formatted_lines = [self.format_point(point,i) for i, point in enumerate(sorted_points) if not point.y() <= 0]
        formatted_text = "\n".join(formatted_lines)
        return formatted_text
    def getSType(self) -> bool:
        """
            return: global _SType  as text paramater.
        """
        return self._SType
    def setSType(self, SType: str) -> None:
        """
        param SType: SType as text paramater.
        """
        self._SType = SType
        # Logger.log('d', 'SType : ' + str(SType))

    def _onEngineCreated(self) -> None:
        main_window = self._application.getMainWindow()
        if not main_window:
            return

        self._toolbutton_item = self._findToolbarIcon(main_window.contentItem())
        self._forceToolEnabled()

        main_window.viewportRectChanged.connect(self._createPickingPass)
        main_window.widthChanged.connect(self._createPickingPass)
        main_window.heightChanged.connect(self._createPickingPass)
        self.propertyChanged.emit()

    def _onSelectionChanged(self) -> None:
        if not self._toolbutton_item:
            return
        self._application.callLater(lambda: self._forceToolEnabled())

    def _onActiveStageChanged(self) -> None:
        self._tool_enabled = self._controller.getActiveStage().stageId == "PrepareStage"
        if not self._tool_enabled:
            self._controller.setSelectionTool(self._selection_tool or "SelectionTool")
            self._selection_tool = None
            if self._controller.getActiveTool() == self:
                self._controller.setActiveTool(self._getFallbackTool())
        self._forceToolEnabled()

    def _onActiveToolChanged(self) -> None:
        if self._controller.getActiveTool() != self:
            self._controller.setSelectionTool(self._selection_tool or "SelectionTool")
            self._selection_tool = None

    def _onSceneChanged(self, node: SceneNode) -> None:
        if node == self._handle:
            return

        self._measure_passes_dirty = True

    def _findToolbarIcon(self, rootItem: QObject) -> Optional[QObject]:
        for child in rootItem.childItems():
            class_name = child.metaObject().className()
            if class_name.startswith("ToolbarButton_QMLTYPE") and child.property(
                "text"
            ) == self._i18n_catalog.i18nc("@label", "Measure"):
                return child
            elif (
                class_name.startswith("QQuickItem")
                or class_name.startswith("QQuickColumn")
                or class_name.startswith("Toolbar_QMLTYPE")
            ):
                found = self._findToolbarIcon(child)
                if found:
                    return found
        return None

    def _forceToolEnabled(self, passive=False) -> None:
        if not self._toolbutton_item:
            return
        try:
            if self._tool_enabled:
                self._toolbutton_item.setProperty("enabled", True)
                if self._application._previous_active_tool == "DrawZSeam" and not passive:
                    self._controller.setActiveTool(self._application._previous_active_tool)
            else:
                self._toolbutton_item.setProperty("enabled", False)
                if self._controller.getActiveTool() == self and not passive:
                    self._controller.setActiveTool(self._getFallbackTool())
        except RuntimeError:
            Logger.log("w", "The toolbutton item seems to have gone missing; trying to find it back.")
            main_window = self._application.getMainWindow()
            if not main_window:
                return

            self._toolbutton_item = self._findToolbarIcon(main_window.contentItem())

    def event(self, event: Event) -> bool:
        result = super().event(event)

        if not self._tool_enabled:
            return result

        # overridden from ToolHandle.event(), because we also want to show the handle when there is no selection
        # disabling the tool oon Event.ToolDeactivateEvent is properly handled in ToolHandle.event()
        if event.type == Event.ToolActivateEvent: #激活插件的事件
            if self._handle:
                self._handle.setParent(self.getController().getScene().getRoot())
                self._handle.setEnabled(True)

            self._selection_tool = self._controller._selection_tool
            self._controller.setSelectionTool(None)

            self._application.callLater(lambda: self._forceToolEnabled(passive=True))

        if event.type == Event.ToolDeactivateEvent: #关闭插件的事件
            self._controller.setSelectionTool(self._selection_tool or "SelectionTool")
            self._selection_tool = None

            self._application.callLater(lambda: self._forceToolEnabled(passive=True))

        if (
            event.type == Event.MouseReleaseEvent
            and MouseEvent.LeftButton in cast(MouseEvent, event).buttons
        ):
            self._dragging = False

        if (
            event.type == Event.MousePressEvent
            and MouseEvent.LeftButton in cast(MouseEvent, event).buttons
        ):
            mouse_event = cast(MouseEvent, event)
            # 删除底板上的点
            self._points = [point for point in self._points if not point.y() <= 0]
            if len(self._points) == 0:
                self._points.append(QVector3D())
                self._active_point = 0
            else:
                distances = []  # type: List[float] #屏幕上的距离
                camera = self._controller.getScene().getActiveCamera()
                for point in self._points:
                    if camera.isPerspective():
                        projected_point = camera.project(
                            Vector(point.x(), point.y(), point.z())
                        )
                    else:
                        # Camera.project() does not work for orthographic views in Cura 4.9 and before, so we calculate our own projection
                        projection = camera.getProjectionMatrix()
                        view = camera.getWorldTransformation()
                        view.invert()

                        position = Vector(point.x(), point.y(), point.z())
                        position = position.preMultiply(view)
                        position = position.preMultiply(projection)

                        projected_point = (position.x, position.y)
                    dx = projected_point[0] - (
                        (
                            camera.getWindowSize()[0]
                            * (mouse_event.x + 1)
                            / camera.getViewportWidth()
                        )
                        - 1
                    )
                    dy = projected_point[1] + mouse_event.y
                    distances.append(math.sqrt(dx * dx + dy * dy)*camera.getViewportWidth())

                min_distance = min(distances)
                min_index = distances.index(min_distance)
                if min_distance < 14.0:
                    self._active_point = min_index
                    if self._SType == 'remove':
                        del self._points[min_index]
                        if len(self._points) == 0:
                            self.resetPoints()
                            return result
                        else:
                            self._active_point = 0
                            self._controller.getScene().sceneChanged.emit(self._handle)
                            self.propertyChanged.emit()
                elif self._SType != 'remove':
                    self._points.append(QVector3D())
                    self._active_point = len(self._points)-1
            if self._SType != 'remove':
                self._dragging = True
                result = self._handleMouseEvent(event, result)

            # 顺序排列各个点
            self._points = sorted(self._points, key=lambda point: point.y())
            # 格式化坐标字符串
            formatted_points = ["[{:.2f},{:.2f},{:.2f}]".format(point.x(), -point.z(), point.y()) for point in
                                self._points if not point.y() <= 0]
            new_value = ','.join(formatted_points)
            self._refresh_seam_points(new_value)


        if event.type == Event.MouseMoveEvent:
            if self._dragging:
                result = self._handleMouseEvent(event, result)

        if self._selection_tool:
            self._selection_tool.event(event)

        return result

    def _handleMouseEvent(self, event: Event, result: bool) -> bool:
        if not self._measure_passes:
            self._createPickingPass()
        if not self._measure_passes:
            return False

        picked_coordinate = []
        mouse_event = cast(MouseEvent, event)

        for axis in self._measure_passes:
            if self._measure_passes_dirty:
                axis.render(self._snap_vertices)

            axis_value = axis.getPickedCoordinate(mouse_event.x, mouse_event.y)
            if axis_value == inf:
                return False
            picked_coordinate.append(axis_value)
        self._measure_passes_dirty = False

        self._points[self._active_point] = QVector3D(*picked_coordinate)

        self._controller.getScene().sceneChanged.emit(self._handle)
        self.propertyChanged.emit()

        return result

    def _createPickingPass(self, *args, **kwargs) -> None:
        active_camera = self._controller.getScene().getActiveCamera()
        if not active_camera:
            return
        viewport_width = active_camera.getViewportWidth()
        viewport_height = active_camera.getViewportHeight()

        self._measure_passes.clear()
        try:
            # Create a set of passes for picking a world-space location from the mouse location
            for axis in range(0, 3):
                self._measure_passes.append(
                    DrawZSeamPass(viewport_width, viewport_height, axis)
                )
        except:
            pass

        self._measure_passes_dirty = True

    def _getFallbackTool(self) -> str:
        try:
            return self._controller._fallback_tool
        except AttributeError:
            return "TranslateTool"

    def _onContainerLoadComplete(self, container_id: str) -> None:
        if not ContainerRegistry.getInstance().isLoaded(container_id):
            # skip containers that could not be loaded, or subsequent findContainers() will cause an infinite loop
            return

        try:
            container = ContainerRegistry.getInstance().findContainers(id=container_id)[
                0
            ]
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
            category = container.findDefinitions(key="shell")[0]
        except IndexError:
            Logger.log("e", "Could not find parent category setting to add settings to")
            return

        for setting_key in self._settings_dict.keys():
            setting_definition = SettingDefinition(
                setting_key, container, category, self._i18n_catalog
            )
            setting_definition.deserialize(self._settings_dict[setting_key])

            # add the setting to the already existing blackmagic settingdefinition
            # private member access is naughty, but the alternative is to serialise, nix and deserialise the whole thing,
            # which breaks stuff
            category._children.append(setting_definition)
            container._definition_cache[setting_key] = setting_definition

            self._expanded_categories = self._application.expandedCategories.copy()
            self._updateAddedChildren(container, setting_definition)
            self._application.setExpandedCategories(self._expanded_categories)
            self._expanded_categories.clear()
            container._updateRelations(setting_definition)

        preferences = self._application.getPreferences()
        #if not preferences.getValue("drawZSeam/settings_made_visible"):
        #    setting_keys = self._getAllSettingKeys(self._settings_dict)

        #    visible_settings = preferences.getValue("general/visible_settings")
        #    visible_settings_changed = False
        #    for key in setting_keys:
        #        if key not in visible_settings:
        #            visible_settings += ";%s" % key
        #            visible_settings_changed = True

        #    if visible_settings_changed:
        #        preferences.setValue("general/visible_settings", visible_settings)

         #   preferences.setValue("drawZSeam/settings_made_visible", True)
    def _updateAddedChildren(
        self, container: DefinitionContainer, setting_definition: SettingDefinition
    ) -> None:
        children = setting_definition.children
        if not children or not setting_definition.parent:
            return

        # make sure this setting is expanded so its children show up  in setting views
        if setting_definition.parent.key in self._expanded_categories:
            self._expanded_categories.append(setting_definition.key)

        for child in children:
            container._definition_cache[child.key] = child
            self._updateAddedChildren(container, child)

    def _refresh_seam_points(self, new_value: str):
        scene = self._application.getController().getScene()
        global_container_stack = self._application.getGlobalContainerStack()
        if not global_container_stack:
            Logger.log("w", "No global_container_stack available.")
            return
        try:
            # 更改特定的参数
            global_container_stack.setProperty("draw_z_seam_points", "value", new_value)
            Logger.log("i", "Updated 'draw_z_seam_points' to: {0}".format(new_value))
        except Exception as e:
            Logger.log("e", "Failed to set 'draw_z_seam_points': {0}".format(str(e)))


##  A RenderPass subclass that renders a the distance of selectable objects from the active camera to a texture.
#   The texture is used to map a 2d location (eg the mouse location) to a world space position
#
#   Note that in order to increase precision, the 24 bit depth value is encoded into all three of the R,G & B channels
class DrawZSeamPass(RenderPass):
    def __init__(self, width: int, height: int, axis: int) -> None:
        super().__init__("picking", width, height)

        self._axis = axis

        self._renderer = CuraApplication.getInstance().getRenderer()

        self._shader = None  # type: Optional[ShaderProgram]
        self._scene = CuraApplication.getInstance().getController().getScene()

    def render(self, snap_vertices) -> None:
        if not self._shader:
            self._shader = OpenGL.getInstance().createShaderProgram(
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "resources",
                    "shaders",
                    "coordinates.shader",
                )
            )

        self._shader.setUniformValue("u_axisId", self._axis)
        self._shader.setUniformValue("u_snapVertices", snap_vertices)

        # Create a new batch to be rendered
        batch = RenderBatch(self._shader)

        # Fill up the batch with objects that can be sliced. `
        for node in DepthFirstIterator(
                self._scene.getRoot()):  # type: ignore #Ignore type error because iter() should get called automatically by Python syntax.
            if (
                    node.callDecoration("isSliceable")
                    and node.getMeshData()
                    and node.isVisible()
            ):
                batch.addItem(node.getWorldTransformation(), node.getMeshData())

        z_fight_distance = 0.2  # Distance between buildplate and disallowed area meshes to prevent z-fighting
        buildplate_transform = Matrix()
        buildplate_transform.setToIdentity()
        buildplate_transform.translate(Vector(0, z_fight_distance, 0))
        buildplate_mesh = CuraApplication.getInstance().getBuildVolume()._grid_mesh
        batch.addItem(buildplate_transform, buildplate_mesh)

        width, height = self.getSize()

        self.bind()
        self._gl.glViewport(0, 0, width, height)
        self._gl.glClearColor(1.0, 1.0, 1.0, 0.0)
        self._gl.glClear(self._gl.GL_COLOR_BUFFER_BIT | self._gl.GL_DEPTH_BUFFER_BIT)

        batch.render(self._scene.getActiveCamera())
        self.release()

    ## Get the coordinate along this pass axis in mm.
    def getPickedCoordinate(self, x: int, y: int) -> float:
        output = self.getOutput()

        window_size = self._renderer.getWindowSize()

        px = round((0.5 + x / 2.0) * window_size[0])
        py = round((0.5 + y / 2.0) * window_size[1])

        if px < 0 or px > (output.width() - 1) or py < 0 or py > (output.height() - 1):
            return inf

        value = output.pixel(px, py)  # value in micron, from in r, g & b channels
        if value == 0x00FFFFFF or value == 0x00000000:
            return inf
        value = (
                        (value & 0x00FFFFFF) - 0x00800000
                ) / 1000.0  # drop the alpha channel, correct for signedness and covert to mm

        return value



class DrawZSeamHandle(ToolHandle):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._name = "DrawZSeamHandle"

        self._handle_width = 2
        self._selection_mesh = MeshData()

        self._tool = None  # type: Optional[DrawZSeam]

    def setTool(self, tool: "DrawZSeam") -> None:
        self._tool = tool

    def buildMesh(self) -> None:
        mesh = self._toMeshData(
            trimesh.creation.icosphere(subdivisions=2, radius=self._handle_width / 2)
        )
        self.setSolidMesh(mesh)

    def render(self, renderer) -> bool:
        if not self._shader:
            self._shader = OpenGL.getInstance().createShaderProgram(
                Resources.getPath(Resources.Shaders, "toolhandle.shader")
            )

        if self._auto_scale:
            active_camera = self._scene.getActiveCamera()
            #控制点的显示大小
            if active_camera.isPerspective():
                camera_position = active_camera.getWorldPosition()
                dist = (camera_position - self.getWorldPosition()).length()
                scale = dist / 400
            else:
                view_width = active_camera.getViewportWidth()
                current_size = view_width + (
                    2 * active_camera.getZoomFactor() * view_width
                )
                scale = current_size / view_width * 5
            self._tool.setScale(scale)
            self.setScale(Vector(scale, scale, scale))

        if self._solid_mesh and self._tool:
            #for position in [self._tool.getPointA(), self._tool.getPointB()]:
            for position in self._tool.getPoints():
                self.setPosition(Vector(position.x(), position.y(), position.z()))
                renderer.queueNode(
                    self, mesh=self._solid_mesh, overlay=False, shader=self._shader
                )

        return True

    def _toMeshData(self, tri_node: trimesh.base.Trimesh) -> MeshData:
        tri_faces = tri_node.faces
        tri_vertices = tri_node.vertices

        indices = []
        vertices = []

        index_count = 0
        face_count = 0
        for tri_face in tri_faces:
            face = []
            for tri_index in tri_face:
                vertices.append(tri_vertices[tri_index])
                face.append(index_count)
                index_count += 1
            indices.append(face)
            face_count += 1

        vertices = numpy.asarray(vertices, dtype=numpy.float32)
        indices = numpy.asarray(indices, dtype=numpy.int32)
        normals = calculateNormalsFromIndexedVertices(vertices, indices, face_count)

        mesh_data = MeshData(vertices=vertices, indices=indices, normals=normals)

        return mesh_data



