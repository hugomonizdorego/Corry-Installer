// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.15
import QtQuick.Controls 2.15
// A white pill button with a soft shadow, used by the slideshow controls.
Button {
    id: control
    implicitWidth: Math.max(44, contentItem.implicitWidth + 30)
    implicitHeight: 38
    contentItem: Text {
        text: control.text; font.pixelSize: 13; font.bold: true
        color: !control.enabled ? "#94a3b8" : control.hovered ? "#4e3585" : "#1f2a44"
        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
    }
    background: Item {
        Rectangle { anchors.fill: parent; anchors.topMargin: 3; radius: 19; color: "#c5d2e4"; opacity: control.enabled ? 0.55 : 0 }
        Rectangle {
            anchors.fill: parent; radius: 19
            color: control.down ? "#e3e9f2" : control.hovered ? "#f0ecf8" : "#ffffff"
            border.color: control.activeFocus ? "#6445a4" : "transparent"
            border.width: control.activeFocus ? 2 : 0
        }
    }
}
