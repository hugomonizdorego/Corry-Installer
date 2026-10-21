// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.3
import QtQuick.Controls 2.10
Button {
    id: control
    implicitWidth: Math.max(44, contentItem.implicitWidth + 28)
    implicitHeight: 38
    contentItem: Text {
        text: control.text; font.pixelSize: 13; color: control.enabled ? "#1d2129" : "#9ca3af"
        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
        radius: 19; color: control.down ? "#f0ecf8" : control.hovered ? "#f9fafb" : "#ffffff"
        border.color: control.activeFocus || control.hovered ? "#6445a4" : "#d1d5db"
        border.width: control.activeFocus ? 2 : 1
    }
}
