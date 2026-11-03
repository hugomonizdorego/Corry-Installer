// SPDX-License-Identifier: GPL-3.0-or-later
import io.calamares.ui 1.0
import io.calamares.core 1.0
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
// Corry header for themes with layout "top": logo, product line and a timeline
// of the steps, in soft raised (neumorphic) shapes on the page background.
// Calamares allows at most 128 px for this header (see CalamaresWindow.cpp).
// Words between two at signs are theme tokens, replaced by tools/corry-branding.py.
Rectangle {
    id: header
    height: 120
    color: "@nav@"
    property color accent: "@accent@"
    property color accentLight: "@accent-light@"
    property color shadow: "@shadow@"
    property color highlight: "@highlight@"
    property color raised: "@surface@"
    property string product: ""
    property string logo: ""
    property string stepName: ""
    Component.onCompleted: {
        product = Branding.shortProductName()
        logo = "file:" + Branding.imagePath(Branding.ProductLogo)
    }
    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 38; anchors.rightMargin: 38; anchors.topMargin: 12; anchors.bottomMargin: 2
        spacing: 6
        RowLayout {
            Layout.fillWidth: true
            spacing: 14
            // Logo in a raised tile: light edge up-left, shadow down-right.
            Item {
                Layout.preferredWidth: 46; Layout.preferredHeight: 46
                Rectangle { anchors.fill: parent; anchors.leftMargin: -3; anchors.topMargin: -3; anchors.rightMargin: 3; anchors.bottomMargin: 3; radius: 15; color: header.highlight; opacity: 0.9 }
                Rectangle { anchors.fill: parent; anchors.leftMargin: 3; anchors.topMargin: 4; anchors.rightMargin: -3; anchors.bottomMargin: -4; radius: 15; color: header.shadow; opacity: 0.55 }
                Rectangle {
                    anchors.fill: parent; radius: 14; color: header.raised
                    Image { anchors.centerIn: parent; source: header.logo; sourceSize.width: 30; sourceSize.height: 30; width: 30; height: 30 }
                }
            }
            ColumnLayout {
                spacing: 1
                Layout.fillWidth: true
                Text { text: qsTr("Install %1").arg(header.product); color: "@nav-text@"; font.family: "@font-family@"; font.pixelSize: 18; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                Text {
                    text: qsTr("Step %1 of %2").arg(ViewManager.currentStepIndex + 1).arg(steps.count) + (header.stepName ? "  ·  " + header.stepName : "")
                    color: "@text-muted@"; font.family: "@font-family@"; font.pixelSize: 12; elide: Text.ElideRight; Layout.fillWidth: true
                }
            }
            Text { text: "Corry @CORRY_VERSION@"; color: "@text-faint@"; font.family: "@font-family@"; font.pixelSize: 11 }
            Button {
                id: about
                text: qsTr("About")
                flat: true
                onClicked: debug.about()
                Accessible.name: text
                implicitHeight: 30; implicitWidth: 74
                contentItem: Text { text: about.text; color: about.hovered ? header.accent : "@text-muted@"; font.family: "@font-family@"; font.pixelSize: 12; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Item {
                    Rectangle { anchors.fill: parent; anchors.leftMargin: -2; anchors.topMargin: -2; anchors.rightMargin: 2; anchors.bottomMargin: 2; radius: 15; color: header.highlight; opacity: 0.9 }
                    Rectangle { anchors.fill: parent; anchors.topMargin: 3; anchors.leftMargin: 2; anchors.rightMargin: -2; anchors.bottomMargin: -3; radius: 15; color: header.shadow; opacity: 0.5 }
                    Rectangle { anchors.fill: parent; radius: 15; color: about.hovered ? "@tint@" : header.raised }
                }
            }
        }
        // Timeline: raised nodes on a groove; the current step has a pill label.
        RowLayout {
            Layout.fillWidth: true
            spacing: 0
            Repeater {
                id: steps
                model: ViewManager
                Item {
                    id: step
                    property bool done: index < ViewManager.currentStepIndex
                    property bool current: index === ViewManager.currentStepIndex
                    onCurrentChanged: if (current) header.stepName = display
                    Component.onCompleted: if (current) header.stepName = display
                    Layout.fillWidth: true
                    Layout.preferredHeight: 52
                    Rectangle {
                        visible: index > 0
                        x: 0; width: parent.width / 2; y: 12; height: 4; radius: 2
                        color: step.done || step.current ? header.accent : "@border@"
                    }
                    Rectangle {
                        visible: index < steps.count - 1
                        x: parent.width / 2; width: parent.width / 2; y: 12; height: 4; radius: 2
                        color: step.done ? header.accent : "@border@"
                    }
                    Rectangle { width: 28; height: 28; radius: 14; x: (parent.width - width) / 2 - 2; y: -2; color: header.highlight; opacity: 0.9 }
                    Rectangle { width: 28; height: 28; radius: 14; x: (parent.width - width) / 2 + 2; y: 3; color: header.shadow; opacity: 0.6 }
                    Rectangle {
                        id: node
                        width: 28; height: 28; radius: 14
                        anchors.horizontalCenter: parent.horizontalCenter
                        color: step.done ? header.accent : header.raised
                        border.width: step.current ? 2 : 0
                        border.color: header.accent
                        Rectangle {
                            anchors.centerIn: parent; width: 10; height: 10; radius: 5
                            visible: !step.done
                            color: step.current ? header.accent : "@border@"
                        }
                        Text { anchors.centerIn: parent; visible: step.done; text: "✓"; color: "@on-accent@"; font.pixelSize: 13; font.bold: true }
                    }
                    Rectangle {
                        id: pill
                        y: 32
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: Math.min(parent.width - 4, label.implicitWidth + 16); height: 20; radius: 10
                        visible: step.current
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0; color: header.accent }
                            GradientStop { position: 1; color: header.accentLight }
                        }
                    }
                    Text {
                        id: label
                        y: 33
                        width: parent.width - 8
                        anchors.horizontalCenter: parent.horizontalCenter
                        horizontalAlignment: Text.AlignHCenter
                        text: display
                        color: step.current ? "@on-accent@" : step.done ? "@text@" : "@text-faint@"
                        font.family: "@font-family@"; font.pixelSize: 11; font.bold: step.current
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }
}
