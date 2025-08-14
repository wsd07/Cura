import QtQuick 6.0
import QtQuick.Controls 6.0

import UM 1.6 as UM
import Cura 1.1 as Cura

Item {
    id: base
    width: 600
    height: 500

    UM.I18nCatalog { id: catalog; name: "ZParameterEditor" }

    // 组件生命周期管理
    Component.onCompleted: {
        console.log("[CHART_DEBUG] ZParameterEditor component completed")

        // 首先初始化参数模型
        initializeParameterModel()

        // 检查当前模型高度
        console.log("[CHART_DEBUG] Component completed, will update model height via timer")

        // 组件加载完成时，加载第一个参数的状态
        if (parameterTypeComboBox.model && parameterTypeComboBox.model.count > 0) {
            var firstItem = parameterTypeComboBox.model.get(0)
            console.log("[CHART_DEBUG] Loading first parameter state:", firstItem.value)
            loadParameterState(firstItem.value)
        }

        // 再次检查图表高度设置
        console.log("[CHART_DEBUG] Final chart canvas model height:", chartCanvas.modelHeight)

        // 初始化时更新模型高度
        updateModelHeight()

        // 延迟再次更新，确保工具完全初始化
        heightUpdateTimer.start()
    }

    // 强制更新模型高度的函数
    function forceUpdateModelHeight() {
        console.log("[CHART_DEBUG] forceUpdateModelHeight called")

        // 直接调用后端获取模型高度
        var result = callZParameterEditorMethodNoArgs("getModelHeight")
        console.log("[CHART_DEBUG] Backend getModelHeight result:", result)

        if (result !== undefined && result !== null) {
            var newHeight = parseFloat(result)
            console.log("[CHART_DEBUG] Got model height from backend:", newHeight)
            console.log("[CHART_DEBUG] Current chart model height:", chartCanvas.modelHeight)

            // 强制更新图表高度
            chartCanvas.modelHeight = newHeight
            console.log("[CHART_DEBUG] Updated chart model height to:", chartCanvas.modelHeight)

            // 重新绘制图表
            gridCanvas.requestPaint()
            curveCanvas.requestPaint()
            console.log("[CHART_DEBUG] Chart repaint requested")
        } else {
            console.log("[CHART_DEBUG] Failed to get model height from backend")
        }
    }

    // 更新模型高度的函数
    function updateModelHeight() {
        console.log("[CHART_DEBUG] updateModelHeight called")

        // 直接调用后端获取模型高度
        var result = callZParameterEditorMethodNoArgs("getModelHeight")
        console.log("[CHART_DEBUG] Backend getModelHeight result:", result)

        if (result !== undefined && result !== null) {
            var newHeight = parseFloat(result)
            console.log("[CHART_DEBUG] Got model height from backend:", newHeight)
            console.log("[CHART_DEBUG] Current chart model height:", chartCanvas.modelHeight)

            // 强制更新图表高度
            console.log("[CHART_DEBUG] Force updating chart model height from", chartCanvas.modelHeight, "to", newHeight)
            var oldHeight = chartCanvas.modelHeight
            chartCanvas.modelHeight = newHeight

            // 自动调整控制点范围
            adjustControlPointsToNewHeight(oldHeight, newHeight)

            // 重新绘制图表
            gridCanvas.requestPaint()
            curveCanvas.requestPaint()
            console.log("[CHART_DEBUG] Chart repaint requested")
        } else {
            console.log("[CHART_DEBUG] Failed to get model height from backend")
        }
    }

    // 调整控制点到新的高度范围
    function adjustControlPointsToNewHeight(oldHeight, newHeight) {
        console.log("[CHART_DEBUG] Adjusting control points from height", oldHeight, "to", newHeight)

        if (oldHeight <= 0 || newHeight <= 0) {
            console.log("[CHART_DEBUG] Invalid height values, skipping adjustment")
            return
        }

        // 如果控制点只有默认的两个点（起始和结束），则直接调整结束点
        if (curveCanvas.controlPoints.length === 2) {
            var startPoint = curveCanvas.controlPoints[0]
            var endPoint = curveCanvas.controlPoints[1]

            // 检查是否是默认配置（起始点在z=0，结束点在旧的模型高度）
            if (Math.abs(startPoint.z - 0) < 0.1 && Math.abs(endPoint.z - oldHeight) < 0.1) {
                console.log("[CHART_DEBUG] Detected default control points, adjusting end point to new height")
                curveCanvas.controlPoints[1].z = newHeight
                console.log("[CHART_DEBUG] Adjusted end point z from", oldHeight, "to", newHeight)
                updatePreview()
                saveCurrentState()
                return
            }
        }

        // 对于其他情况，按比例调整所有控制点
        for (var i = 0; i < curveCanvas.controlPoints.length; i++) {
            var point = curveCanvas.controlPoints[i]
            if (point.z > newHeight) {
                console.log("[CHART_DEBUG] Clamping control point", i, "z from", point.z, "to", newHeight)
                curveCanvas.controlPoints[i].z = newHeight
            }
        }

        updatePreview()
        saveCurrentState()
    }

    // 定时器用于延迟更新模型高度
    Timer {
        id: heightUpdateTimer
        interval: 200
        repeat: false
        onTriggered: {
            console.log("[CHART_DEBUG] Height update timer triggered")
            forceUpdateModelHeight()
        }
    }

    Component.onDestruction: {
        // 组件销毁时保存当前状态
        saveCurrentState()
    }

    // 调用ZParameterEditor工具的方法
    function callZParameterEditorMethod(methodName, data) {
        var result = UM.Controller.callToolMethod("ZParameterEditor", methodName, data)

        if (result !== null) {
            console.log("[TOOL_DEBUG] Successfully called", methodName, "on ZParameterEditor tool")
            return result
        } else {
            console.log("[TOOL_DEBUG] Failed to call", methodName, "on ZParameterEditor tool")
            return null
        }
    }

    // 调用ZParameterEditor工具的无参数方法
    function callZParameterEditorMethodNoArgs(methodName) {
        try {
            // 直接通过callToolMethod调用，传递空字符串作为参数
            var result = UM.Controller.callToolMethod("ZParameterEditor", methodName, "")
            console.log("[TOOL_DEBUG] Successfully called", methodName, "on ZParameterEditor tool")
            return result
        } catch (e) {
            console.log("[TOOL_DEBUG] Error calling", methodName, ":", e)
            return null
        }
    }

    // 获取默认参数值
    function getDefaultParameterValue(parameterType) {
        try {
            var result = UM.Controller.callToolMethod("ZParameterEditor", "getDefaultParameterValue", parameterType)
            console.log("[PARAM_DEBUG] Got default value for", parameterType, ":", result)
            return result
        } catch (e) {
            console.log("[PARAM_DEBUG] Error getting default value for", parameterType, ":", e)
            return 100.0
        }
    }

    // 初始化参数模型
    function initializeParameterModel() {
        console.log("[PARAM_DEBUG] Initializing parameter model")

        // 清空现有模型
        parameterModel.clear()

        // 速度比例参数
        var speedDefault = 100.0
        parameterModel.append({
            "text": "打印速度比例",
            "value": "user_speed_ratio_definition",
            "unit": "%",
            "defaultValue": speedDefault,
            "minValue": 0,
            "maxValue": speedDefault * 2  // 0-200%
        })

        // 层厚参数
        var thicknessDefault = getDefaultParameterValue("user_thickness_definition")
        parameterModel.append({
            "text": "层厚度",
            "value": "user_thickness_definition",
            "unit": "mm",
            "defaultValue": thicknessDefault,
            "minValue": 0,
            "maxValue": thicknessDefault * 2  // 0到默认值的2倍
        })

        // 温度参数
        var tempDefault = getDefaultParameterValue("user_temperature_definition")
        parameterModel.append({
            "text": "打印温度",
            "value": "user_temperature_definition",
            "unit": "°C",
            "defaultValue": tempDefault,
            "minValue": tempDefault - 20,  // 默认值-20度
            "maxValue": tempDefault + 20   // 默认值+20度
        })

        console.log("[PARAM_DEBUG] Parameter model initialized with", parameterModel.count, "items")
    }

    // 状态保存和加载函数
    function saveCurrentState() {
        console.log("[SAVE_DEBUG] saveCurrentState called")
        if (parameterTypeComboBox.currentParameterKey) {
            var state = {
                "controlPoints": curveCanvas.controlPoints,
                "curveMode": chartCanvas.curveMode,
                "minValue": chartCanvas.minParamValue,
                "maxValue": chartCanvas.maxParamValue
            }
            console.log("[SAVE_DEBUG] Saving state for:", parameterTypeComboBox.currentParameterKey)
            console.log("[SAVE_DEBUG] State data:", JSON.stringify(state))
            console.log("[SAVE_DEBUG] Control points count:", curveCanvas.controlPoints.length)

            // 调用工具的保存方法
            var result = callZParameterEditorMethod("setParameterDataSlot", {
                "parameterKey": parameterTypeComboBox.currentParameterKey,
                "stateData": JSON.stringify(state)
            })

            if (result !== null) {
                console.log("[SAVE_DEBUG] Successfully saved parameter state")
            } else {
                console.log("[SAVE_DEBUG] Failed to save parameter state")
            }
        } else {
            console.log("[SAVE_DEBUG] No current parameter key, cannot save state")
        }
    }

    function loadParameterState(parameterKey) {
        console.log("[SAVE_DEBUG] Loading parameter state for:", parameterKey)

        // 获取当前参数的默认值
        var currentItem = null
        for (var i = 0; i < parameterTypeComboBox.model.count; i++) {
            var item = parameterTypeComboBox.model.get(i)
            if (item.value === parameterKey) {
                currentItem = item
                break
            }
        }

        if (!currentItem) {
            console.log("[SAVE_DEBUG] No item found for parameter:", parameterKey)
            return
        }

        console.log("[SAVE_DEBUG] Found parameter item:", JSON.stringify(currentItem))

        // 设置默认值，使用当前模型高度
        var modelHeight = chartCanvas.modelHeight || 50
        var defaultControlPoints = [
            {"z": 0, "value": currentItem.defaultValue},
            {"z": modelHeight, "value": currentItem.defaultValue}
        ]
        console.log("[SAVE_DEBUG] Default control points:", JSON.stringify(defaultControlPoints))

        var stateJson = ""
        var result = callZParameterEditorMethod("getParameterDataSlot", parameterKey)
        if (result !== null) {
            stateJson = result
            console.log("[SAVE_DEBUG] Retrieved state JSON:", stateJson)
        } else {
            console.log("[SAVE_DEBUG] Failed to retrieve parameter state")
        }

        if (stateJson && stateJson !== "{}") {
            console.log("[SAVE_DEBUG] Parsing saved state")
            try {
                var state = JSON.parse(stateJson)
                console.log("[SAVE_DEBUG] Parsed state:", JSON.stringify(state))
                console.log("[SAVE_DEBUG] Applying saved control points:", JSON.stringify(state.controlPoints))
                curveCanvas.controlPoints = state.controlPoints || defaultControlPoints
                chartCanvas.curveMode = state.curveMode || "bezier"
                chartCanvas.minParamValue = state.minValue || currentItem.minValue
                chartCanvas.maxParamValue = state.maxValue || currentItem.maxValue
                console.log("[SAVE_DEBUG] Applied saved state successfully")
            } catch (e) {
                console.log("[SAVE_DEBUG] Error loading parameter state:", e)
                // 使用默认值
                curveCanvas.controlPoints = defaultControlPoints
                chartCanvas.curveMode = "bezier"
                chartCanvas.minParamValue = currentItem.minValue
                chartCanvas.maxParamValue = currentItem.maxValue
                console.log("[SAVE_DEBUG] Applied default values due to error")
            }
        } else {
            // 没有保存的状态，使用默认值
            console.log("[SAVE_DEBUG] No saved state found, using default values")
            curveCanvas.controlPoints = defaultControlPoints
            chartCanvas.curveMode = "bezier"
            chartCanvas.minParamValue = currentItem.minValue
            chartCanvas.maxParamValue = currentItem.maxValue
            console.log("[SAVE_DEBUG] Applied default values")
        }

        // 更新界面
        console.log("[SAVE_DEBUG] Updating UI elements")
        minValueInput.text = chartCanvas.minParamValue.toString()
        maxValueInput.text = chartCanvas.maxParamValue.toString()
        console.log("[SAVE_DEBUG] Final control points:", JSON.stringify(curveCanvas.controlPoints))
        updatePreview()
        gridCanvas.requestPaint()
        curveCanvas.requestPaint()
        console.log("[SAVE_DEBUG] loadParameterState completed")
    }

    function updatePreview() {
        console.log("[UI_DEBUG] updatePreview called - control points count:", curveCanvas.controlPoints.length)
        if (curveCanvas.controlPoints.length < 2) {
            console.log("[UI_DEBUG] Insufficient control points, clearing preview")
            previewText.text = ""
            return
        }
        console.log("[UI_DEBUG] Control points:", JSON.stringify(curveCanvas.controlPoints))

        var sortedPoints = curveCanvas.controlPoints.slice().sort(function(a, b) { return a.z - b.z })
        var finalPoints = []

        // 获取插值设置
        var interpolationCount = parseInt(interpolationPointsInput.text) || 10
        var useControlPoints = useControlPointsCheckbox.checked

        // 获取Z范围
        var minZ = sortedPoints[0].z
        var maxZ = sortedPoints[sortedPoints.length - 1].z

        // 添加插值点
        if (interpolationCount > 0 && maxZ > minZ) {
            for (var i = 0; i < interpolationCount; i++) {
                var z = minZ + (maxZ - minZ) * i / (interpolationCount - 1)
                var value = evaluateCurveAtZ(z, sortedPoints)
                finalPoints.push({z: z, value: value})
            }
        }

        // 如果使用控制点，添加控制点
        if (useControlPoints) {
            for (var j = 0; j < sortedPoints.length; j++) {
                var controlPoint = sortedPoints[j]
                // 检查是否已经存在相同Z值的点
                var exists = false
                for (var k = 0; k < finalPoints.length; k++) {
                    if (Math.abs(finalPoints[k].z - controlPoint.z) < 0.01) {
                        exists = true
                        break
                    }
                }
                if (!exists) {
                    finalPoints.push({z: controlPoint.z, value: controlPoint.value})
                }
            }
        }

        // 按Z值排序
        finalPoints.sort(function(a, b) { return a.z - b.z })

        // 格式化输出
        var formattedValue = ""
        for (var m = 0; m < finalPoints.length; m++) {
            var point = finalPoints[m]
            var valueStr = parameterTypeComboBox.currentParameterKey === "user_thickness_definition" ?
                          point.value.toFixed(2) : point.value.toFixed(0)
            formattedValue += "[" + point.z.toFixed(1) + "," + valueStr + "]"
        }
        previewText.text = formattedValue
    }

    // 计算曲线在指定Z值处的参数值
    function evaluateCurveAtZ(targetZ, sortedPoints) {
        if (sortedPoints.length < 2) return 0

        // 如果目标Z在范围外，返回边界值
        if (targetZ <= sortedPoints[0].z) return sortedPoints[0].value
        if (targetZ >= sortedPoints[sortedPoints.length - 1].z) return sortedPoints[sortedPoints.length - 1].value

        if (chartCanvas.curveMode === "line") {
            // 折线模式：线性插值
            for (var i = 0; i < sortedPoints.length - 1; i++) {
                var p1 = sortedPoints[i]
                var p2 = sortedPoints[i + 1]
                if (targetZ >= p1.z && targetZ <= p2.z) {
                    var t = (targetZ - p1.z) / (p2.z - p1.z)
                    return p1.value + t * (p2.value - p1.value)
                }
            }
        } else {
            // 曲线模式：Catmull-Rom插值
            // 找到目标Z所在的段
            for (var i = 0; i < sortedPoints.length - 1; i++) {
                var p1 = sortedPoints[i]
                var p2 = sortedPoints[i + 1]
                if (targetZ >= p1.z && targetZ <= p2.z) {
                    var p0 = i > 0 ? sortedPoints[i - 1] : p1
                    var p3 = i < sortedPoints.length - 2 ? sortedPoints[i + 2] : p2

                    var t = (targetZ - p1.z) / (p2.z - p1.z)
                    var t2 = t * t
                    var t3 = t2 * t

                    // Catmull-Rom插值公式
                    var value = 0.5 * (
                        (2 * p1.value) +
                        (-p0.value + p2.value) * t +
                        (2 * p0.value - 5 * p1.value + 4 * p2.value - p3.value) * t2 +
                        (-p0.value + 3 * p1.value - 3 * p2.value + p3.value) * t3
                    )
                    return value
                }
            }
        }

        return 0
    }

    Row {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 15

        // 左侧图表区域
        Rectangle {
            id: chartArea
            width: parent.width * 0.65
            height: parent.height
            color: UM.Theme.getColor("main_background")
            border.color: UM.Theme.getColor("setting_control_border")
            border.width: 2
            radius: 8

            Column {
                anchors.fill: parent
                anchors.margins: 15
                spacing: 10

                // 图表标题和模式切换按钮
                Row {
                    width: parent.width
                    spacing: 10

                    Text {
                        text: "Z轴参数曲线"
                        color: UM.Theme.getColor("text")
                        font.bold: true
                        font.pixelSize: 16
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Item {
                        width: parent.width - titleText.width - modeButtons.width - 20
                        height: 1
                        Text { id: titleText; visible: false; text: "Z轴参数曲线"; font.bold: true; font.pixelSize: 16 }
                    }

                    // 曲线模式切换按钮
                    Row {
                        id: modeButtons
                        spacing: 5
                        anchors.verticalCenter: parent.verticalCenter

                        Button {
                            id: bezierModeButton
                            text: "曲线"
                            width: 50
                            height: 25
                            checkable: true
                            checked: chartCanvas.curveMode === "bezier"
                            onClicked: {
                                console.log("[MOUSE_DEBUG] Bezier mode button clicked")
                                chartCanvas.curveMode = "bezier"
                                lineModeButton.checked = false
                                curveCanvas.requestPaint()
                                saveCurrentState()
                                console.log("[MOUSE_DEBUG] Bezier mode activated, curve mode:", chartCanvas.curveMode)
                            }
                            background: Rectangle {
                                color: bezierModeButton.checked ? UM.Theme.getColor("primary") :
                                       (bezierModeButton.hovered ? UM.Theme.getColor("setting_control_highlight") : UM.Theme.getColor("setting_control"))
                                border.color: UM.Theme.getColor("setting_control_border")
                                border.width: 1
                                radius: UM.Theme.getSize("setting_control_radius").width
                            }
                            contentItem: Text {
                                text: bezierModeButton.text
                                color: bezierModeButton.checked ? UM.Theme.getColor("primary_text") : UM.Theme.getColor("text")
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                font: UM.Theme.getFont("default")
                            }
                        }

                        Button {
                            id: lineModeButton
                            text: "折线"
                            width: 50
                            height: 25
                            checkable: true
                            checked: chartCanvas.curveMode === "line"
                            onClicked: {
                                console.log("[MOUSE_DEBUG] Line mode button clicked")
                                chartCanvas.curveMode = "line"
                                bezierModeButton.checked = false
                                curveCanvas.requestPaint()
                                saveCurrentState()
                                console.log("[MOUSE_DEBUG] Line mode activated, curve mode:", chartCanvas.curveMode)
                            }
                            background: Rectangle {
                                color: lineModeButton.checked ? UM.Theme.getColor("primary") :
                                       (lineModeButton.hovered ? UM.Theme.getColor("setting_control_highlight") : UM.Theme.getColor("setting_control"))
                                border.color: UM.Theme.getColor("setting_control_border")
                                border.width: 1
                                radius: UM.Theme.getSize("setting_control_radius").width
                            }
                            contentItem: Text {
                                text: lineModeButton.text
                                color: lineModeButton.checked ? UM.Theme.getColor("primary_text") : UM.Theme.getColor("text")
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                font: UM.Theme.getFont("default")
                            }
                        }
                    }
                }

                // 图表绘制区域
                Rectangle {
                    id: chartCanvas
                    width: parent.width
                    height: parent.height - 40
                    color: UM.Theme.getColor("setting_category")
                    border.color: UM.Theme.getColor("setting_control_border")
                    border.width: 1
                    radius: 4

                    property real modelHeight: 25.0
                    property real minParamValue: 10
                    property real maxParamValue: 200
                    property string curveMode: "bezier"

                    onModelHeightChanged: {
                        console.log("[UI_DEBUG] Model height changed to:", modelHeight)
                    }

                    onMinParamValueChanged: {
                        console.log("[UI_DEBUG] Min parameter value changed to:", minParamValue)
                    }

                    onMaxParamValueChanged: {
                        console.log("[UI_DEBUG] Max parameter value changed to:", maxParamValue)
                    }

                    onCurveModeChanged: {
                        console.log("[UI_DEBUG] Curve mode changed to:", curveMode)
                    }

                    // 监听模型高度变化 - 暂时禁用，使用定时器更新
                    /*
                    Connections {
                        target: null  // 暂时禁用
                        function onPropertyChanged() {
                            console.log("[CHART_DEBUG] Tool property changed event triggered")
                            updateModelHeight()
                            if (tool) {
                                var newHeight = tool.modelHeight || 25.0
                                console.log("[CHART_DEBUG] Tool model height:", tool.modelHeight, "newHeight:", newHeight)
                                console.log("[CHART_DEBUG] Current chart model height:", chartCanvas.modelHeight)
                                if (Math.abs(newHeight - chartCanvas.modelHeight) > 0.1) {
                                    console.log("[CHART_DEBUG] Model height changed from", chartCanvas.modelHeight, "to", newHeight)
                                    console.log("[CHART_DEBUG] Updating chart model height...")
                                    chartCanvas.modelHeight = newHeight
                                    console.log("[CHART_DEBUG] Chart model height updated to:", chartCanvas.modelHeight)

                                    // 调整控制点的Z坐标范围
                                    console.log("[CHART_DEBUG] Adjusting control points for new height...")
                                    for (var i = 0; i < curveCanvas.controlPoints.length; i++) {
                                        if (curveCanvas.controlPoints[i].z > newHeight) {
                                            console.log("[CHART_DEBUG] Adjusting control point", i, "z from", curveCanvas.controlPoints[i].z, "to", newHeight)
                                            curveCanvas.controlPoints[i].z = newHeight
                                        }
                                    }

                                    console.log("[CHART_DEBUG] Requesting chart repaint...")
                                    gridCanvas.requestPaint()
                                    curveCanvas.requestPaint()
                                    updatePreview()
                                    saveCurrentState()
                                    console.log("[CHART_DEBUG] Chart update completed")
                                } else {
                                    console.log("[CHART_DEBUG] Height change too small, skipping update")
                                }
                            } else {
                                console.log("[CHART_DEBUG] No tool available")
                            }
                        }
                    }
                    */

                    // 监听选择变化
                    Connections {
                        target: UM.Selection
                        function onSelectionChanged() {
                            console.log("[SELECTION_DEBUG] Selection changed event triggered")

                            // 强制更新模型高度
                            forceUpdateModelHeight()
                        }
                    }

                    // 坐标转换函数
                    function heightToY(height) {
                        return chartCanvas.height - 30 - (height / modelHeight) * (chartCanvas.height - 60)
                    }

                    function yToHeight(y) {
                        return (chartCanvas.height - 30 - y) * modelHeight / (chartCanvas.height - 60)
                    }

                    function valueToX(value) {
                        return 40 + (value - minParamValue) / (maxParamValue - minParamValue) * (chartCanvas.width - 80)
                    }

                    function xToValue(x) {
                        return minParamValue + (x - 40) * (maxParamValue - minParamValue) / (chartCanvas.width - 80)
                    }

                    // 网格背景
                    Canvas {
                        id: gridCanvas
                        anchors.fill: parent

                        onPaint: {
                            console.log("[CHART_DEBUG] GridCanvas onPaint called")
                            console.log("[CHART_DEBUG] Chart model height:", chartCanvas.modelHeight)
                            console.log("[CHART_DEBUG] Chart min param value:", chartCanvas.minParamValue)
                            console.log("[CHART_DEBUG] Chart max param value:", chartCanvas.maxParamValue)

                            var ctx = getContext("2d")
                            ctx.clearRect(0, 0, width, height)

                            // 绘制网格
                            ctx.strokeStyle = UM.Theme.getColor("setting_control_border")
                            ctx.lineWidth = 0.5

                            // 垂直网格线
                            for (var x = 40; x <= width - 40; x += (width - 80) / 10) {
                                ctx.beginPath()
                                ctx.moveTo(x, 20)
                                ctx.lineTo(x, height - 30)
                                ctx.stroke()
                            }

                            // 水平网格线
                            for (var y = 20; y <= height - 30; y += (height - 50) / 10) {
                                ctx.beginPath()
                                ctx.moveTo(40, y)
                                ctx.lineTo(width - 40, y)
                                ctx.stroke()
                            }

                            // 绘制坐标轴
                            ctx.strokeStyle = UM.Theme.getColor("text")
                            ctx.lineWidth = 2

                            // Y轴
                            ctx.beginPath()
                            ctx.moveTo(40, 20)
                            ctx.lineTo(40, height - 30)
                            ctx.stroke()

                            // X轴
                            ctx.beginPath()
                            ctx.moveTo(40, height - 30)
                            ctx.lineTo(width - 40, height - 30)
                            ctx.stroke()

                            // 绘制坐标轴标签
                            ctx.fillStyle = UM.Theme.getColor("text")
                            ctx.font = "10px Arial"
                            ctx.textAlign = "center"

                            // Y轴标签 (Z高度)
                            var modelHeight = chartCanvas.modelHeight || 50
                            for (var i = 0; i <= 5; i++) {
                                var zValue = (modelHeight / 5) * i
                                var yPos = height - 30 - (i * (height - 50) / 5)
                                ctx.fillText(zValue.toFixed(1) + "mm", 20, yPos + 3)
                            }

                            // X轴标签 (参数值)
                            var minParam = chartCanvas.minParamValue || 0
                            var maxParam = chartCanvas.maxParamValue || 100
                            for (var j = 0; j <= 5; j++) {
                                var paramValue = minParam + (maxParam - minParam) * j / 5
                                var xPos = 40 + j * (width - 80) / 5
                                ctx.fillText(paramValue.toFixed(1), xPos, height - 10)
                            }
                        }
                    }

                    // 曲线绘制层
                    Canvas {
                        id: curveCanvas
                        anchors.fill: parent

                        property var controlPoints: [
                            {z: 0, value: 100},
                            {z: chartCanvas.modelHeight, value: 100}
                        ]
                        property int dragIndex: -1
                        property int hoverIndex: -1
                        property bool nearCurve: false

                        // Catmull-Rom插值函数
                        function drawInterpolatedCurve(ctx) {
                            if (controlPoints.length < 2) return

                            var sortedPoints = controlPoints.slice().sort(function(a, b) { return a.z - b.z })

                            ctx.strokeStyle = UM.Theme.getColor("primary")
                            ctx.lineWidth = 3
                            ctx.beginPath()

                            if (chartCanvas.curveMode === "line" || sortedPoints.length === 2) {
                                // 折线模式或只有两个点，直接连线
                                ctx.moveTo(chartCanvas.valueToX(sortedPoints[0].value), chartCanvas.heightToY(sortedPoints[0].z))
                                for (var i = 1; i < sortedPoints.length; i++) {
                                    ctx.lineTo(chartCanvas.valueToX(sortedPoints[i].value), chartCanvas.heightToY(sortedPoints[i].z))
                                }
                            } else {
                                // 曲线模式：给定Z值范围，计算对应的value值
                                var minZ = sortedPoints[0].z
                                var maxZ = sortedPoints[sortedPoints.length - 1].z
                                var segments = 100

                                ctx.moveTo(chartCanvas.valueToX(sortedPoints[0].value), chartCanvas.heightToY(sortedPoints[0].z))

                                for (var i = 1; i <= segments; i++) {
                                    var z = minZ + (maxZ - minZ) * i / segments
                                    var value = evaluateCurveAtZ(z, sortedPoints)

                                    var x = chartCanvas.valueToX(value)
                                    var y = chartCanvas.heightToY(z)
                                    ctx.lineTo(x, y)
                                }
                            }
                            ctx.stroke()
                        }

                        // 绘制插值点（灰色，不可编辑）
                        function drawInterpolationPoints(ctx) {
                            if (controlPoints.length < 2) return

                            var sortedPoints = controlPoints.slice().sort(function(a, b) { return a.z - b.z })
                            var interpolationCount = parseInt(interpolationPointsInput.text) || 10
                            var useControlPoints = useControlPointsCheckbox.checked

                            // 获取Z范围
                            var minZ = sortedPoints[0].z
                            var maxZ = sortedPoints[sortedPoints.length - 1].z

                            if (maxZ <= minZ) return

                            // 计算插值点
                            var interpolationPoints = []
                            for (var i = 0; i < interpolationCount; i++) {
                                var z = minZ + (maxZ - minZ) * i / (interpolationCount - 1)
                                var value = evaluateCurveAtZ(z, sortedPoints)
                                interpolationPoints.push({z: z, value: value})
                            }

                            // 绘制插值点
                            ctx.fillStyle = "#888888" // 灰色
                            for (var j = 0; j < interpolationPoints.length; j++) {
                                var point = interpolationPoints[j]
                                var x = chartCanvas.valueToX(point.value)
                                var y = chartCanvas.heightToY(point.z)

                                // 检查是否与控制点重叠
                                var isControlPoint = false
                                if (useControlPoints) {
                                    for (var k = 0; k < sortedPoints.length; k++) {
                                        if (Math.abs(sortedPoints[k].z - point.z) < 0.01) {
                                            isControlPoint = true
                                            break
                                        }
                                    }
                                }

                                // 只绘制非控制点的插值点
                                if (!isControlPoint) {
                                    ctx.beginPath()
                                    ctx.arc(x, y, 3, 0, 2 * Math.PI)
                                    ctx.fill()

                                    // 灰色边框
                                    ctx.strokeStyle = "#666666"
                                    ctx.lineWidth = 1
                                    ctx.stroke()
                                }
                            }
                        }

                        function getControlPointAt(x, y) {
                            for (var i = 0; i < controlPoints.length; i++) {
                                var point = controlPoints[i]
                                var px = chartCanvas.valueToX(point.value)
                                var py = chartCanvas.heightToY(point.z)
                                var distance = Math.sqrt((x - px) * (x - px) + (y - py) * (y - py))
                                if (distance <= 8) {
                                    return i
                                }
                            }
                            return -1
                        }

                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.clearRect(0, 0, width, height)

                            if (controlPoints.length === 0) return

                            // 绘制曲线
                            drawInterpolatedCurve(ctx)

                            // 绘制插值点（灰色，不可编辑）
                            drawInterpolationPoints(ctx)

                            // 绘制控制点
                            for (var j = 0; j < controlPoints.length; j++) {
                                var cp = controlPoints[j]
                                var x = chartCanvas.valueToX(cp.value)
                                var y = chartCanvas.heightToY(cp.z)

                                // 控制点颜色
                                if (j === hoverIndex || j === dragIndex) {
                                    ctx.fillStyle = UM.Theme.getColor("text")
                                } else {
                                    ctx.fillStyle = UM.Theme.getColor("primary")
                                }

                                ctx.beginPath()
                                ctx.arc(x, y, 6, 0, 2 * Math.PI)
                                ctx.fill()

                                // 白色边框
                                ctx.strokeStyle = "#ffffff"
                                ctx.lineWidth = 2
                                ctx.stroke()

                                // 显示坐标
                                ctx.fillStyle = UM.Theme.getColor("text")
                                ctx.font = "10px Arial"
                                var valueDecimals = parameterTypeComboBox.currentParameterKey === "user_thickness_definition" ? 2 : 0
                                ctx.fillText("(" + cp.z.toFixed(1) + ", " + cp.value.toFixed(valueDecimals) + ")", x + 10, y - 10)
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            acceptedButtons: Qt.LeftButton | Qt.RightButton

                            onPositionChanged: function(mouse) {
                                if (curveCanvas.dragIndex >= 0) {
                                    console.log("[MOUSE_DEBUG] Position changed - mouse.x:", mouse.x, "mouse.y:", mouse.y, "dragIndex:", curveCanvas.dragIndex)
                                    var newZ = chartCanvas.yToHeight(mouse.y)
                                    var newValue = chartCanvas.xToValue(mouse.x)
                                    console.log("[MOUSE_DEBUG] Calculated newZ:", newZ, "newValue:", newValue, "modelHeight:", chartCanvas.modelHeight)

                                    newZ = Math.max(0, Math.min(chartCanvas.modelHeight, newZ))
                                    newValue = Math.max(chartCanvas.minParamValue, Math.min(chartCanvas.maxParamValue, newValue))
                                    console.log("[MOUSE_DEBUG] Clamped newZ:", newZ, "newValue:", newValue, "minParam:", chartCanvas.minParamValue, "maxParam:", chartCanvas.maxParamValue)

                                    curveCanvas.controlPoints[curveCanvas.dragIndex].z = newZ
                                    curveCanvas.controlPoints[curveCanvas.dragIndex].value = newValue
                                    console.log("[MOUSE_DEBUG] Updated control point", curveCanvas.dragIndex, "to z:", newZ, "value:", newValue)
                                    curveCanvas.requestPaint()
                                    updatePreview()
                                } else {
                                    var oldHoverIndex = curveCanvas.hoverIndex
                                    curveCanvas.hoverIndex = curveCanvas.getControlPointAt(mouse.x, mouse.y)

                                    if (oldHoverIndex !== curveCanvas.hoverIndex) {
                                        console.log("[MOUSE_DEBUG] Hover index changed from", oldHoverIndex, "to", curveCanvas.hoverIndex)
                                        curveCanvas.requestPaint()
                                    }
                                }
                            }

                            onPressed: function(mouse) {
                                console.log("[MOUSE_DEBUG] Mouse pressed - button:", mouse.button, "x:", mouse.x, "y:", mouse.y)
                                if (mouse.button === Qt.LeftButton) {
                                    var pointIndex = curveCanvas.getControlPointAt(mouse.x, mouse.y)
                                    console.log("[MOUSE_DEBUG] Control point at position:", pointIndex)
                                    if (pointIndex >= 0) {
                                        curveCanvas.dragIndex = pointIndex
                                        console.log("[MOUSE_DEBUG] Started dragging control point", pointIndex)
                                    } else {
                                        curveCanvas.dragIndex = -1
                                        console.log("[MOUSE_DEBUG] No control point found, dragIndex set to -1")
                                    }
                                }
                            }

                            onReleased: function(mouse) {
                                console.log("[MOUSE_DEBUG] Mouse released - button:", mouse.button, "x:", mouse.x, "y:", mouse.y, "dragIndex:", curveCanvas.dragIndex)
                                if (curveCanvas.dragIndex >= 0) {
                                    console.log("[MOUSE_DEBUG] Saving state after drag operation")
                                    saveCurrentState()
                                }
                                curveCanvas.dragIndex = -1
                                console.log("[MOUSE_DEBUG] Drag operation ended")
                            }

                            onClicked: function(mouse) {
                                console.log("[MOUSE_DEBUG] Mouse clicked - button:", mouse.button, "x:", mouse.x, "y:", mouse.y)
                                if (mouse.button === Qt.LeftButton) {
                                    var pointIndex = curveCanvas.getControlPointAt(mouse.x, mouse.y)
                                    console.log("[MOUSE_DEBUG] Left click - control point index:", pointIndex)
                                    if (pointIndex < 0) {
                                        // 添加新控制点
                                        var z = chartCanvas.yToHeight(mouse.y)
                                        var value = chartCanvas.xToValue(mouse.x)
                                        console.log("[MOUSE_DEBUG] Adding new control point - raw z:", z, "raw value:", value)

                                        z = Math.max(0, Math.min(chartCanvas.modelHeight, z))
                                        value = Math.max(chartCanvas.minParamValue, Math.min(chartCanvas.maxParamValue, value))
                                        console.log("[MOUSE_DEBUG] Adding new control point - clamped z:", z, "clamped value:", value)

                                        curveCanvas.controlPoints.push({z: z, value: value})
                                        console.log("[MOUSE_DEBUG] New control point added, total points:", curveCanvas.controlPoints.length)
                                        curveCanvas.requestPaint()
                                        updatePreview()
                                        saveCurrentState()
                                    }
                                } else if (mouse.button === Qt.RightButton) {
                                    var pointIndex = curveCanvas.getControlPointAt(mouse.x, mouse.y)
                                    console.log("[MOUSE_DEBUG] Right click - control point index:", pointIndex, "total points:", curveCanvas.controlPoints.length)
                                    if (pointIndex >= 0 && curveCanvas.controlPoints.length > 2) {
                                        console.log("[MOUSE_DEBUG] Removing control point", pointIndex)
                                        curveCanvas.controlPoints.splice(pointIndex, 1)
                                        console.log("[MOUSE_DEBUG] Control point removed, remaining points:", curveCanvas.controlPoints.length)
                                        curveCanvas.requestPaint()
                                        updatePreview()
                                        saveCurrentState()
                                    }
                                }
                            }
                        }
                    }

                    // 移除重复的坐标轴标签，只保留gridCanvas中的绘制
                }
            }
        }

        // 右侧控制面板
        Rectangle {
            id: controlPanel
            width: parent.width * 0.35 - 15
            height: parent.height
            color: UM.Theme.getColor("setting_control")
            border.color: UM.Theme.getColor("setting_control_border")
            border.width: 1
            radius: 5

            Column {
                anchors.fill: parent
                anchors.margins: 15
                spacing: 15



                // 参数类型选择
                Column {
                    width: parent.width
                    spacing: 8

                    Text {
                        text: "参数类型"
                        color: UM.Theme.getColor("text")
                        font.bold: true
                    }

                    Cura.ComboBox {
                        id: parameterTypeComboBox
                        width: parent.width
                        height: UM.Theme.getSize("setting_control").height
                        
                        model: ListModel {
                            id: parameterModel
                            // 初始化时会被动态填充
                        }
                        
                        textRole: "text"
                        currentIndex: 0

                        property string currentParameterKey: model.count > 0 ? model.get(currentIndex).value : ""
                        property string currentUnit: model.count > 0 ? model.get(currentIndex).unit : ""
                        property real currentMinValue: model.count > 0 ? model.get(currentIndex).minValue : 0
                        property real currentMaxValue: model.count > 0 ? model.get(currentIndex).maxValue : 100
                        property real currentDefaultValue: model.count > 0 ? model.get(currentIndex).defaultValue : 100
                        
                        onActivated: function(index) {
                            console.log("[UI_DEBUG] Parameter type changed to index:", index)
                            var item = model.get(index)
                            console.log("[UI_DEBUG] New parameter type:", item.value)
                            console.log("[UI_DEBUG] New parameter range:", item.minValue, "to", item.maxValue, "default:", item.defaultValue)

                            // 先保存当前状态
                            console.log("[UI_DEBUG] Saving current state before parameter switch")
                            saveCurrentState()

                            // 加载新参数的状态
                            console.log("[UI_DEBUG] Loading state for new parameter:", item.value)
                            loadParameterState(item.value)

                            // 更新界面
                            console.log("[UI_DEBUG] Updating UI with new parameter values")
                            chartCanvas.minParamValue = item.minValue
                            chartCanvas.maxParamValue = item.maxValue
                            minValueInput.text = item.minValue.toString()
                            maxValueInput.text = item.maxValue.toString()

                            // 重新绘制
                            console.log("[UI_DEBUG] Requesting repaint after parameter change")
                            gridCanvas.requestPaint()
                            curveCanvas.requestPaint()
                            updatePreview()
                        }
                        
                        Component.onCompleted: {
                            // 参数模型已在主组件中初始化，这里不需要额外操作
                            console.log("[PARAM_DEBUG] ComboBox completed, model count:", model.count)
                        }
                    }
                }

                // 参数范围设置
                Column {
                    width: parent.width
                    spacing: 8

                    Text {
                        text: "参数范围 (" + parameterTypeComboBox.currentUnit + ")"
                        color: UM.Theme.getColor("text")
                        font.bold: true
                    }

                    Row {
                        width: parent.width
                        spacing: 10

                        Column {
                            width: (parent.width - 10) / 2
                            spacing: 5

                            Text {
                                text: "下限"
                                color: UM.Theme.getColor("text")
                                font.pixelSize: 12
                            }

                            TextField {
                                id: minValueInput
                                width: parent.width
                                height: 25
                                text: parameterTypeComboBox.currentMinValue.toString()
                                onTextChanged: {
                                    console.log("[UI_DEBUG] Min value input changed to:", text)
                                    var value = parseFloat(text)
                                    if (!isNaN(value)) {
                                        console.log("[UI_DEBUG] Setting min parameter value to:", value)
                                        chartCanvas.minParamValue = value
                                        gridCanvas.requestPaint()
                                        curveCanvas.requestPaint()
                                        updatePreview()
                                        saveCurrentState()
                                    } else {
                                        console.log("[UI_DEBUG] Invalid min value input:", text)
                                    }
                                }
                            }
                        }

                        Column {
                            width: (parent.width - 10) / 2
                            spacing: 5

                            Text {
                                text: "上限"
                                color: UM.Theme.getColor("text")
                                font.pixelSize: 12
                            }

                            TextField {
                                id: maxValueInput
                                width: parent.width
                                height: 25
                                text: parameterTypeComboBox.currentMaxValue.toString()
                                onTextChanged: {
                                    console.log("[UI_DEBUG] Max value input changed to:", text)
                                    var value = parseFloat(text)
                                    if (!isNaN(value)) {
                                        console.log("[UI_DEBUG] Setting max parameter value to:", value)
                                        chartCanvas.maxParamValue = value
                                        gridCanvas.requestPaint()
                                        curveCanvas.requestPaint()
                                        updatePreview()
                                        saveCurrentState()
                                    } else {
                                        console.log("[UI_DEBUG] Invalid max value input:", text)
                                    }
                                }
                            }
                        }
                    }
                }

                // 重置按钮
                Column {
                    width: parent.width
                    spacing: 8

                    Button {
                        text: "重置控制点"
                        width: parent.width
                        height: 30
                        onClicked: {
                            console.log("[MOUSE_DEBUG] Reset button clicked")
                            console.log("[MOUSE_DEBUG] Current parameter:", parameterTypeComboBox.currentParameterKey, "default value:", parameterTypeComboBox.currentDefaultValue, "model height:", chartCanvas.modelHeight)
                            curveCanvas.controlPoints = [
                                {z: 0, value: parameterTypeComboBox.currentDefaultValue},
                                {z: chartCanvas.modelHeight, value: parameterTypeComboBox.currentDefaultValue}
                            ]
                            console.log("[MOUSE_DEBUG] Control points reset to:", JSON.stringify(curveCanvas.controlPoints))
                            curveCanvas.requestPaint()
                            updatePreview()
                            saveCurrentState()
                        }
                        background: Rectangle {
                            color: parent.hovered ? UM.Theme.getColor("setting_control_highlight") : UM.Theme.getColor("setting_control")
                            border.color: UM.Theme.getColor("setting_control_border")
                            border.width: 1
                            radius: UM.Theme.getSize("setting_control_radius").width
                        }
                        contentItem: Text {
                            text: parent.text
                            color: UM.Theme.getColor("text")
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font: UM.Theme.getFont("default")
                        }
                    }
                }

                // 插值设置
                Column {
                    width: parent.width
                    spacing: 8

                    Text {
                        text: "插值设置"
                        color: UM.Theme.getColor("text")
                        font.bold: true
                    }

                    Row {
                        width: parent.width
                        spacing: 10

                        Text {
                            text: "插值点数量"
                            color: UM.Theme.getColor("text")
                            font.pixelSize: 12
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        TextField {
                            id: interpolationPointsInput
                            width: 60
                            height: 25
                            text: "10"
                            validator: IntValidator { bottom: 1; top: 100 }
                            onTextChanged: updatePreview()
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 10

                        CheckBox {
                            id: useControlPointsCheckbox
                            checked: true
                            onCheckedChanged: updatePreview()
                        }

                        Text {
                            text: "使用控制点"
                            color: UM.Theme.getColor("text")
                            font.pixelSize: 12
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }

                // 参数预览
                Column {
                    width: parent.width
                    spacing: 8

                    Text {
                        text: "参数预览"
                        color: UM.Theme.getColor("text")
                        font.bold: true
                    }

                    ScrollView {
                        width: parent.width
                        height: 80
                        clip: true

                        // 禁用横向滚动，只允许纵向滚动
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        ScrollBar.vertical.policy: ScrollBar.AsNeeded

                        Rectangle {
                            width: parent.width
                            height: Math.max(80, previewText.contentHeight + 20)
                            color: UM.Theme.getColor("setting_category")
                            border.color: UM.Theme.getColor("setting_control_border")
                            border.width: 1
                            radius: 3

                            Text {
                                id: previewText
                                anchors.fill: parent
                                anchors.margins: 10
                                text: ""
                                color: UM.Theme.getColor("text")
                                font.family: "monospace"
                                font.pixelSize: 11
                                wrapMode: Text.Wrap
                                verticalAlignment: Text.AlignTop
                            }
                        }
                    }
                }

                // 应用按钮
                Button {
                    text: "应用到设置"
                    width: parent.width
                    height: 40
                    onClicked: {
                        console.log("[CORE_DEBUG] Apply button clicked")
                        console.log("[CORE_DEBUG] Control points count:", curveCanvas.controlPoints.length)
                        console.log("[CORE_DEBUG] Model height:", chartCanvas.modelHeight)
                        console.log("[CORE_DEBUG] Parameter range:", chartCanvas.minParamValue, "to", chartCanvas.maxParamValue)

                        if (curveCanvas.controlPoints.length < 2) {
                            console.log("[CORE_DEBUG] Insufficient control points, need at least 2")
                            return
                        }

                        // 直接使用预览文本的内容
                        var formattedValue = previewText.text
                        var parameterKey = parameterTypeComboBox.currentParameterKey

                        console.log("[CORE_DEBUG] Applying settings:", parameterKey, "=", formattedValue)
                        console.log("[CORE_DEBUG] Control points:", JSON.stringify(curveCanvas.controlPoints))
                        console.log("[CORE_DEBUG] Preview text length:", formattedValue.length)

                        // 直接调用后端方法
                        console.log("[CORE_DEBUG] Calling applyParameterSettingsSlot...")
                        try {
                            // 使用正确的参数格式调用
                            var result = UM.Controller.callToolMethod("ZParameterEditor", "applyParameterSettingsSlot", parameterKey + "," + formattedValue)
                            console.log("[CORE_DEBUG] applyParameterSettingsSlot result:", result)
                        } catch (e) {
                            console.log("[CORE_DEBUG] Error calling applyParameterSettingsSlot:", e)
                        }
                    }
                    background: Rectangle {
                        color: parent.hovered ? UM.Theme.getColor("primary_hover") : UM.Theme.getColor("primary")
                        border.color: UM.Theme.getColor("primary")
                        border.width: 1
                        radius: UM.Theme.getSize("default_radius").width
                    }
                    contentItem: Text {
                        text: parent.text
                        color: UM.Theme.getColor("primary_text")
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font: UM.Theme.getFont("default_bold")
                    }
                }
            }
        }
    }
}
