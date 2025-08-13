//-----------------------------------------------------------------------------
// Copyright (c) 2022 5@xes
// 
// proterties values
//   "SSize"       : Support Size in mm
//   "MSize"       : Support Maximum Size in mm
//   "ISize"       : Support Interior Size in mm
//   "AAngle"      : Support Angle in °
//   "AsModel"      : Cylindrical Support created as Model
//   "YDirection"  : Support Y direction (Abutment)
//   "EHeights"    : Equalize heights (Abutment)
//   "SMain"       : Scale Main direction (Freeform)
//   "SType"       : Support Type ( Cylinder/Tube/Cube/Abutment/Freeform/Custom ) 
//   "SubType"     : Support Freeform Type ( Cross/Section/Pillar/Bridge/Custom ) 
//   "SOrient"     : Support Automatic Orientation for Freeform Type
//   "SMirror"     : Support Mirror for Freeform Type
//   "SMsg"        : Text for the Remove All Button
//-----------------------------------------------------------------------------

import QtQuick 6.0
import QtQuick.Controls 6.0

import UM 1.6 as UM
import Cura 1.0 as Cura

Item
{
    id: base
    width: childrenRect.width
    height: childrenRect.height
    UM.I18nCatalog { id: catalog; name: "customsupport"}
	
    property var s_size: UM.ActiveTool.properties.getValue("ActivePoint")
    property var pointList: UM.ActiveTool.properties.getValue("FormatPointList")
	property int localwidth: 120

    function setSType(type)
    {
        console.log("[DRAWZSEAM_DEBUG] setSType called with type:", type)
        // set checked state of mesh type buttons
		addPoint.checked = type === 'add'
		removePoint.checked = type === 'remove'
        console.log("[DRAWZSEAM_DEBUG] Setting property SType to:", type)
        UM.ActiveTool.setProperty("SType", type)
        console.log("[DRAWZSEAM_DEBUG] setSType completed")
    }
	
    Column
    {
        id: sTypeItems
        anchors.top: parent.top
        anchors.left: parent.left
        spacing: UM.Theme.getSize("default_margin").height

        Row // Mesh type buttons
        {
            id: sTypeButtonsSup
            spacing: UM.Theme.getSize("default_margin").width * 1.8

            UM.ToolbarButton
            {
                id: addPoint
                text: catalog.i18nc("@label", "Add Point")
				toolItem: UM.ColorImage
				{
					source: Qt.resolvedUrl("../icons/add_point.svg")
					color: UM.Theme.getColor("icon")
				}
                property bool needBorder: true
                checkable:true
                onClicked: {
                    console.log("[DRAWZSEAM_DEBUG] Add Point button clicked")
                    setSType('add')
                }
                checked: UM.ActiveTool.properties.getValue("SType") === 'add'
                z: 3 // Depth position 
            }

            UM.ToolbarButton
            {
                id: removePoint
                text: catalog.i18nc("@label", "Remove Point")
				toolItem: UM.ColorImage
				{
					source: Qt.resolvedUrl("../icons/remove_point.svg")
					color: UM.Theme.getColor("icon")
				}
                property bool needBorder: true
                checkable:true
                onClicked: {
                    console.log("[DRAWZSEAM_DEBUG] Remove Point button clicked")
                    setSType('remove')
                }
                checked: UM.ActiveTool.properties.getValue("SType") === 'remove'
                z: 2 // Depth position 
            }
			
            UM.ToolbarButton
            {
                id: resetPoints
                text: catalog.i18nc("@label", "Reset")
				toolItem: UM.ColorImage
                {
                    source: UM.Theme.getIcon("ArrowReset")
                    color: UM.Theme.getColor("icon")
                }
                property bool needBorder: true
                onClicked: {
                    console.log("[DRAWZSEAM_DEBUG] Reset button clicked")
                    UM.ActiveTool.triggerAction("resetPoints")
                }
                z: 1 // Depth position 
            }


        }
    }


    Label
    {
        id: textBoxLabel
        anchors.top: sTypeItems.bottom
        height: UM.Theme.getSize("setting_control").height
        text: catalog.i18nc("@label","Point List:")
        font: UM.Theme.getFont("default")
        color: UM.Theme.getColor("text")
        verticalAlignment: Text.AlignVCenter
        renderType: Text.NativeRendering
    }

    Cura.ReadOnlyTextArea
    {
        id: textBox
        anchors.top: textBoxLabel.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.topMargin: 0
        height: 150

        readOnly: true  // 设置为只读
        text: pointList
    }
}
