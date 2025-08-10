import QtQuick 6.0
import QtQuick.Controls 6.0

import UM 1.6 as UM
import Cura 1.1 as Cura

Item {
    id: base
    width: 600
    height: 500

    UM.I18nCatalog { id: catalog; name: "ZParameterEditor" }

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

                // 图表标题
                Text {
                    text: "Z轴参数曲线"
                    color: UM.Theme.getColor("text")
                    font.bold: true
                    font.pixelSize: 16
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

                            if (sortedPoints.length === 2) {
                                ctx.moveTo(chartCanvas.valueToX(sortedPoints[0].value), chartCanvas.heightToY(sortedPoints[0].z))
                                ctx.lineTo(chartCanvas.valueToX(sortedPoints[1].value), chartCanvas.heightToY(sortedPoints[1].z))
                            } else {
                                var segments = 50
                                
                                for (var i = 0; i < sortedPoints.length - 1; i++) {
                                    var p0 = i > 0 ? sortedPoints[i - 1] : sortedPoints[i]
                                    var p1 = sortedPoints[i]
                                    var p2 = sortedPoints[i + 1]
                                    var p3 = i < sortedPoints.length - 2 ? sortedPoints[i + 2] : sortedPoints[i + 1]
                                    
                                    for (var t = 0; t <= segments; t++) {
                                        var u = t / segments
                                        var u2 = u * u
                                        var u3 = u2 * u
                                        
                                        var zInterp = 0.5 * (
                                            (2 * p1.z) +
                                            (-p0.z + p2.z) * u +
                                            (2 * p0.z - 5 * p1.z + 4 * p2.z - p3.z) * u2 +
                                            (-p0.z + 3 * p1.z - 3 * p2.z + p3.z) * u3
                                        )
                                        
                                        var valueInterp = 0.5 * (
                                            (2 * p1.value) +
                                            (-p0.value + p2.value) * u +
                                            (2 * p0.value - 5 * p1.value + 4 * p2.value - p3.value) * u2 +
                                            (-p0.value + 3 * p1.value - 3 * p2.value + p3.value) * u3
                                        )
                                        
                                        var x = chartCanvas.valueToX(valueInterp)
                                        var y = chartCanvas.heightToY(zInterp)
                                        
                                        if (i === 0 && t === 0) {
                                            ctx.moveTo(x, y)
                                        } else {
                                            ctx.lineTo(x, y)
                                        }
                                    }
                                }
                            }
                            ctx.stroke()
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
                                ctx.fillText("(" + cp.z.toFixed(1) + ", " + cp.value.toFixed(0) + ")", x + 10, y - 10)
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            acceptedButtons: Qt.LeftButton | Qt.RightButton

                            onPositionChanged: function(mouse) {
                                if (curveCanvas.dragIndex >= 0) {
                                    var newZ = chartCanvas.yToHeight(mouse.y)
                                    var newValue = chartCanvas.xToValue(mouse.x)
                                    
                                    newZ = Math.max(0, Math.min(chartCanvas.modelHeight, newZ))
                                    newValue = Math.max(chartCanvas.minParamValue, Math.min(chartCanvas.maxParamValue, newValue))
                                    
                                    curveCanvas.controlPoints[curveCanvas.dragIndex].z = newZ
                                    curveCanvas.controlPoints[curveCanvas.dragIndex].value = newValue
                                    curveCanvas.requestPaint()
                                } else {
                                    var oldHoverIndex = curveCanvas.hoverIndex
                                    curveCanvas.hoverIndex = curveCanvas.getControlPointAt(mouse.x, mouse.y)
                                    
                                    if (oldHoverIndex !== curveCanvas.hoverIndex) {
                                        curveCanvas.requestPaint()
                                    }
                                }
                            }

                            onPressed: function(mouse) {
                                if (mouse.button === Qt.LeftButton) {
                                    var pointIndex = curveCanvas.getControlPointAt(mouse.x, mouse.y)
                                    if (pointIndex >= 0) {
                                        curveCanvas.dragIndex = pointIndex
                                    }
                                }
                            }

                            onReleased: function(mouse) {
                                curveCanvas.dragIndex = -1
                            }

                            onClicked: function(mouse) {
                                if (mouse.button === Qt.LeftButton) {
                                    var pointIndex = curveCanvas.getControlPointAt(mouse.x, mouse.y)
                                    if (pointIndex < 0) {
                                        // 添加新控制点
                                        var z = chartCanvas.yToHeight(mouse.y)
                                        var value = chartCanvas.xToValue(mouse.x)
                                        
                                        z = Math.max(0, Math.min(chartCanvas.modelHeight, z))
                                        value = Math.max(chartCanvas.minParamValue, Math.min(chartCanvas.maxParamValue, value))
                                        
                                        curveCanvas.controlPoints.push({z: z, value: value})
                                        curveCanvas.requestPaint()
                                    }
                                } else if (mouse.button === Qt.RightButton) {
                                    var pointIndex = curveCanvas.getControlPointAt(mouse.x, mouse.y)
                                    if (pointIndex >= 0 && curveCanvas.controlPoints.length > 2) {
                                        curveCanvas.controlPoints.splice(pointIndex, 1)
                                        curveCanvas.requestPaint()
                                    }
                                }
                            }
                        }
                    }

                    // Z轴标签
                    Column {
                        anchors.left: parent.left
                        anchors.leftMargin: 5
                        anchors.top: parent.top
                        anchors.topMargin: 20
                        spacing: (parent.height - 50) / 5

                        Repeater {
                            model: 6
                            Text {
                                text: (chartCanvas.modelHeight * (5 - index) / 5).toFixed(1) + "mm"
                                color: UM.Theme.getColor("text")
                                font.pixelSize: 10
                            }
                        }
                    }

                    // 参数值标签
                    Row {
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 5
                        anchors.left: parent.left
                        anchors.leftMargin: 40
                        anchors.right: parent.right
                        anchors.rightMargin: 40

                        Repeater {
                            model: 6
                            Text {
                                text: (chartCanvas.minParamValue + 
                                      (chartCanvas.maxParamValue - chartCanvas.minParamValue) * index / 5).toFixed(0)
                                color: UM.Theme.getColor("text")
                                font.pixelSize: 10
                                width: parent.width / 6
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }
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

                // 标题
                Text {
                    text: "参数设置"
                    color: UM.Theme.getColor("text")
                    font.bold: true
                    font.pixelSize: 14
                }

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
                            ListElement { text: "打印速度比例"; value: "user_speed_ratio_definition"; unit: "%"; minValue: 10; maxValue: 200; defaultValue: 100 }
                            ListElement { text: "层厚度"; value: "user_thickness_definition"; unit: "mm"; minValue: 0.1; maxValue: 0.4; defaultValue: 0.2 }
                            ListElement { text: "打印温度"; value: "user_temperature_definition"; unit: "°C"; minValue: 180; maxValue: 250; defaultValue: 200 }
                        }
                        
                        textRole: "text"
                        currentIndex: 0
                        
                        property string currentParameterKey: model.get(currentIndex).value
                        property string currentUnit: model.get(currentIndex).unit
                        property real currentMinValue: model.get(currentIndex).minValue
                        property real currentMaxValue: model.get(currentIndex).maxValue
                        property real currentDefaultValue: model.get(currentIndex).defaultValue
                        
                        onActivated: function(index) {
                            var item = model.get(index)
                            chartCanvas.minParamValue = item.minValue
                            chartCanvas.maxParamValue = item.maxValue
                            gridCanvas.requestPaint()
                            curveCanvas.requestPaint()
                        }
                        
                        Component.onCompleted: {
                            var item = model.get(0)
                            chartCanvas.minParamValue = item.minValue
                            chartCanvas.maxParamValue = item.maxValue
                        }
                    }
                }

                // 参数范围设置
                Column {
                    width: parent.width
                    spacing: 8

                    Text {
                        text: "参数范围"
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
                                    var value = parseFloat(text)
                                    if (!isNaN(value)) {
                                        chartCanvas.minParamValue = value
                                        gridCanvas.requestPaint()
                                        curveCanvas.requestPaint()
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
                                    var value = parseFloat(text)
                                    if (!isNaN(value)) {
                                        chartCanvas.maxParamValue = value
                                        gridCanvas.requestPaint()
                                        curveCanvas.requestPaint()
                                    }
                                }
                            }
                        }
                    }
                }

                // 控制点操作
                Column {
                    width: parent.width
                    spacing: 8

                    Text {
                        text: "控制点操作"
                        color: UM.Theme.getColor("text")
                        font.bold: true
                    }

                    Text {
                        text: "• 左键点击空白处添加控制点\n• 拖拽控制点移动\n• 右键点击控制点删除"
                        color: UM.Theme.getColor("text")
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                        width: parent.width
                    }

                    Button {
                        text: "重置控制点"
                        width: parent.width
                        height: 30
                        onClicked: {
                            curveCanvas.controlPoints = [
                                {z: 0, value: parameterTypeComboBox.currentDefaultValue},
                                {z: chartCanvas.modelHeight, value: parameterTypeComboBox.currentDefaultValue}
                            ]
                            curveCanvas.requestPaint()
                        }
                        background: Rectangle {
                            color: UM.Theme.getColor("setting_control")
                            border.color: UM.Theme.getColor("setting_control_border")
                            radius: 3
                        }
                    }
                }

                // 应用按钮
                Button {
                    text: "应用到设置"
                    width: parent.width
                    height: 40
                    onClicked: {
                        if (curveCanvas.controlPoints.length < 2) {
                            console.log("需要至少2个控制点")
                            return
                        }

                        var sortedPoints = curveCanvas.controlPoints.slice().sort(function(a, b) { return a.z - b.z })

                        var formattedValue = ""
                        for (var i = 0; i < sortedPoints.length; i++) {
                            var point = sortedPoints[i]
                            formattedValue += "[" + point.z.toFixed(2) + "," + point.value.toFixed(2) + "]"
                        }

                        var parameterKey = parameterTypeComboBox.currentParameterKey

                        console.log("应用设置:", parameterKey, "=", formattedValue)

                        if (UM.ActiveTool && UM.ActiveTool.applyParameterSettings) {
                            UM.ActiveTool.applyParameterSettings(parameterKey, formattedValue)
                        } else {
                            console.log("ActiveTool not available or method not found")
                        }
                    }
                    background: Rectangle {
                        color: UM.Theme.getColor("primary")
                        border.color: UM.Theme.getColor("setting_control_border")
                        radius: 5
                    }
                }
            }
        }
    }
}
