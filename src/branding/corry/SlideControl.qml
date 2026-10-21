// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.3
import QtQuick.Controls 2.10
Button {
    id: control
    implicitWidth: Math.max(48, contentItem.implicitWidth + 28)
    implicitHeight: 38
    contentItem: Text {
        text: control.text; font.pixelSize: 13; color: control.enabled ? "#21343d" : "#aaa5b2"
        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
        radius: 8; color: control.down ? "#d7eae4" : control.hovered ? "#edf6f2" : "white"
        border.color: control.activeFocus ? "#08786f" : "#cbd9dc"
        border.width: control.activeFocus ? 2 : 1
    }
}
