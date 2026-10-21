// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.3
import QtQuick.Controls 2.10
Button {
    id: control
    implicitWidth: Math.max(48, contentItem.implicitWidth + 28)
    implicitHeight: 38
    contentItem: Text {
        text: control.text; font.pixelSize: 13; color: control.enabled ? "#272530" : "#aaa5b2"
        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
        radius: 8; color: control.down ? "#e9e5ef" : control.hovered ? "#f3f0f7" : "white"
        border.color: control.activeFocus ? "#6445a4" : "#dcd7e6"
        border.width: control.activeFocus ? 2 : 1
    }
}
