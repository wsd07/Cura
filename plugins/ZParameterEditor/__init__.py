# Copyright (c) 2024 wsd
# ZParameterEditor is released under the terms of the AGPLv3 or higher.

from . import ZParameterEditor

from UM.Version import Version
from UM.Application import Application
from UM.i18n import i18nCatalog

i18n_catalog = i18nCatalog("ZParameterEditor")


def getMetaData():
    tool_icon_path = "resources/icons/tool_icon.svg"
    tool_panel_path = "resources/qml/ZParameterEditor.qml"
    metadata = {
        "tool": {
            "name": i18n_catalog.i18nc("@label", "Z Parameter Editor"),
            "description": i18n_catalog.i18nc(
                "@info:tooltip", "Visual editor for Z-height dependent parameters like temperature and speed profiles."
            ),
            "icon": tool_icon_path,
            "tool_panel": tool_panel_path,
            "weight": 7,
        }
    }

    return metadata

def register(app):
    return {"tool": ZParameterEditor.ZParameterEditor()}
