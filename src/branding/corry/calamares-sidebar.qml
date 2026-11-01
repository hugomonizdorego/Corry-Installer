// SPDX-License-Identifier: GPL-3.0-or-later
import io.calamares.ui 1.0
import io.calamares.core 1.0
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
// Corry header: product line and a timeline of the steps, on the light page
// background. Calamares allows at most 128 px for the Corry header (see
// CalamaresWindow.cpp). Colors are replaced per distribution by
// tools/install-profile.sh.
Rectangle {
    id: header
    height: 118
    color: "#edf3fb"
    property color accent: "#6445a4"
    property color accentLight: "#8a6fd0"
    property color tint: "#f0ecf8"
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
            // Logo in a soft white tile.
            Item {
                Layout.preferredWidth: 46; Layout.preferredHeight: 46
                Rectangle { anchors.fill: parent; anchors.topMargin: 3; radius: 15; color: "#cfdbeb"; opacity: 0.55 }
                Rectangle {
                    anchors.fill: parent; radius: 14; color: "#ffffff"
                    Image { anchors.centerIn: parent; source: header.logo; sourceSize.width: 30; sourceSize.height: 30; width: 30; height: 30 }
                }
            }
            ColumnLayout {
                spacing: 1
                Layout.fillWidth: true
                Text { text: qsTr("Install %1").arg(header.product); color: "#1f2a44"; font.pixelSize: 18; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                Text {
                    text: qsTr("Step %1 of %2").arg(ViewManager.currentStepIndex + 1).arg(steps.count) + (header.stepName ? "  ·  " + header.stepName : "")
                    color: "#64748b"; font.pixelSize: 12; elide: Text.ElideRight; Layout.fillWidth: true
                }
            }
            Text { text: "Corry @CORRY_VERSION@"; color: "#94a3b8"; font.pixelSize: 11 }
            Button {
                id: about
                text: qsTr("About")
                flat: true
                onClicked: debug.about()
                Accessible.name: text
                implicitHeight: 30; implicitWidth: 74
                contentItem: Text { text: about.text; color: about.hovered ? header.accent : "#64748b"; font.pixelSize: 12; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Item {
                    Rectangle { anchors.fill: parent; anchors.topMargin: 2; radius: 15; color: "#cfdbeb"; opacity: 0.5 }
                    Rectangle { anchors.fill: parent; radius: 15; color: about.hovered ? header.tint : "#ffffff" }
                }
            }
        }
        // Timeline: white nodes on a line; the current step has a pill label.
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
                    Layout.preferredHeight: 50
                    Rectangle {
                        visible: index > 0
                        x: 0; width: parent.width / 2; y: 11; height: 3; radius: 1.5
                        color: step.done || step.current ? header.accent : "#d9e2ee"
                    }
                    Rectangle {
                        visible: index < steps.count - 1
                        x: parent.width / 2; width: parent.width / 2; y: 11; height: 3; radius: 1.5
                        color: step.done ? header.accent : "#d9e2ee"
                    }
                    // Node shadow, node, dot.
                    Rectangle { width: 26; height: 26; radius: 13; y: 2; anchors.horizontalCenter: parent.horizontalCenter; color: "#c5d2e4"; opacity: 0.6 }
                    Rectangle {
                        id: node
                        width: 26; height: 26; radius: 13
                        anchors.horizontalCenter: parent.horizontalCenter
                        color: step.done ? header.accent : "#ffffff"
                        border.width: step.current ? 2 : 0
                        border.color: header.accent
                        Rectangle {
                            anchors.centerIn: parent; width: 10; height: 10; radius: 5
                            visible: !step.done
                            color: step.current ? header.accent : "#d9e2ee"
                        }
                        Text { anchors.centerIn: parent; visible: step.done; text: "✓"; color: "#ffffff"; font.pixelSize: 13; font.bold: true }
                    }
                    Rectangle {
                        id: pill
                        y: 30
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
                        y: 31
                        width: parent.width - 8
                        anchors.horizontalCenter: parent.horizontalCenter
                        horizontalAlignment: Text.AlignHCenter
                        text: display
                        color: step.current ? "#ffffff" : step.done ? "#475569" : "#94a3b8"
                        font.pixelSize: 11; font.bold: step.current
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }
}
