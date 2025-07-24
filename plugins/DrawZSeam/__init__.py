# Copyright (c) 2023 Aldo Hoeben / fieldOfView
# MeasureTool is released under the terms of the AGPLv3 or higher.

from . import DrawZSeam

from UM.Version import Version
from UM.Application import Application
from UM.i18n import i18nCatalog

i18n_catalog = i18nCatalog("measuretool")


def getMetaData():

    tool_icon_path = "resources/icons/tool_icon.svg"
    tool_panel_path = "resources/qml/DrawZSeam.qml"
    metadata = {
        "tool": {
            "name": i18n_catalog.i18nc("@label", "Draw Z Seam"),
            "description": i18n_catalog.i18nc(
                "@info:tooltip", "Adds a set of seam point."
            ),
            "icon": tool_icon_path,
            "tool_panel": tool_panel_path,
            "weight": 6,
        }
    }

    return metadata

def register(app):
    return {"tool": DrawZSeam.DrawZSeam()}
