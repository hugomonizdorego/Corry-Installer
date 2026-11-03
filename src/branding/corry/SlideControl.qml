// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.15
import QtQuick.Controls 2.15
// A raised pill button, used by the slideshow controls.
// Words between two at signs are theme tokens, replaced by tools/corry-branding.py.
Button {
    id: control
    implicitWidth: Math.max(44, contentItem.implicitWidth + 30)
    implicitHeight: 38
    contentItem: Text {
        text: control.text; font.family: "@font-family@"; font.pixelSize: 13; font.bold: true
        color: !control.enabled ? "@text-faint@" : control.hovered ? "@accent-dark@" : "@text@"
        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
    }
    background: Item {
        Rectangle { anchors.fill: parent; anchors.leftMargin: -2; anchors.topMargin: -2; anchors.rightMargin: 2; anchors.bottomMargin: 2; radius: 19; color: "@highlight@"; opacity: control.enabled ? 0.8 : 0 }
        Rectangle { anchors.fill: parent; anchors.topMargin: 3; anchors.leftMargin: 2; anchors.rightMargin: -2; anchors.bottomMargin: -3; radius: 19; color: "@shadow@"; opacity: control.enabled ? 0.5 : 0 }
        Rectangle {
            anchors.fill: parent; radius: 19
            color: control.down ? "@surface-alt@" : control.hovered ? "@tint@" : "@surface@"
            border.color: control.activeFocus ? "@accent@" : "transparent"
            border.width: control.activeFocus ? 2 : 0
        }
    }
}
