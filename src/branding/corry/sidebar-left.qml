// SPDX-License-Identifier: GPL-3.0-or-later
import io.calamares.ui 1.0
import io.calamares.core 1.0
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
// Corry sidebar for themes with layout "left": a rounded panel with the
// product logo, a greeting, the steps as a menu of colored tiles, and a small
// card at the bottom. The width is set by CalamaresWindow.cpp.
// Words between two at signs are theme tokens, replaced by tools/corry-branding.py.
Rectangle {
    id: sidebar
    color: "@page@"
    property string product: ""
    property string logo: ""
    property var marks: ["@mark-1@", "@mark-2@", "@mark-3@", "@mark-4@"]
    property var tones: ["@tone-1@", "@tone-2@", "@tone-3@", "@tone-4@"]
    property string stepName: ""
    Component.onCompleted: {
        product = Branding.shortProductName()
        logo = "file:" + Branding.imagePath(Branding.ProductLogo)
    }
    // Soft shadow under the panel.
    Rectangle { anchors.fill: panel; anchors.topMargin: 8; anchors.leftMargin: 4; anchors.rightMargin: 4; anchors.bottomMargin: -6; radius: 32; color: "@shadow@"; opacity: 0.35 }
    Rectangle {
        id: panel
        anchors.fill: parent
        anchors.margins: 14
        anchors.rightMargin: 4
        radius: 30
        gradient: Gradient {
            GradientStop { position: 0; color: Qt.lighter("@nav@", 1.04) }
            GradientStop { position: 1; color: "@nav@" }
        }
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 10
            // Logo in a white circle, with a small status dot.
            Item {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 84; Layout.preferredHeight: 84
                Rectangle { anchors.fill: parent; anchors.topMargin: 5; radius: width / 2; color: "@shadow@"; opacity: 0.45 }
                Rectangle {
                    anchors.fill: parent; radius: width / 2; color: "@surface@"
                    border.width: 4; border.color: Qt.lighter("@nav@", 1.08)
                    Image { anchors.centerIn: parent; source: sidebar.logo; sourceSize.width: 46; sourceSize.height: 46; width: 46; height: 46 }
                }
                Rectangle { width: 18; height: 18; radius: 9; x: parent.width - 20; y: parent.height - 22; color: "@mark-1@"; border.width: 3; border.color: "@surface@" }
            }
            Text {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: qsTr("Hi! Let's install")
                color: "@nav-text@"; font.family: "@font-family@"; font.pixelSize: 17; font.bold: true
                elide: Text.ElideRight
            }
            Text {
                Layout.fillWidth: true
                Layout.topMargin: -8
                horizontalAlignment: Text.AlignHCenter
                text: sidebar.product
                color: "@text-muted@"; font.family: "@font-family@"; font.pixelSize: 13; font.bold: true
                elide: Text.ElideRight
            }
            // The steps, as a menu.
            ListView {
                id: steps
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.topMargin: 4
                clip: true
                spacing: 2
                boundsBehavior: Flickable.StopAtBounds
                // Every step fits: rows shrink from 40 to 30 pixels before the list would scroll.
                readonly property int rowHeight: Math.max(30, Math.min(40, Math.floor(height / Math.max(1, count)) - spacing))
                model: ViewManager
                currentIndex: ViewManager.currentStepIndex
                delegate: Item {
                    id: step
                    width: steps.width
                    height: steps.rowHeight
                    property bool done: index < ViewManager.currentStepIndex
                    property bool current: index === ViewManager.currentStepIndex
                    property color mark: sidebar.marks[index % 4]
                    onCurrentChanged: if (current) { sidebar.stepName = display; steps.positionViewAtIndex(index, ListView.Contain) }
                    Component.onCompleted: if (current) sidebar.stepName = display
                    Rectangle { anchors.fill: row; anchors.topMargin: 3; anchors.bottomMargin: -3; radius: 16; color: "@shadow@"; opacity: step.current ? 0.35 : 0 }
                    Rectangle { id: row; anchors.fill: parent; anchors.bottomMargin: 2; radius: 16; color: step.current ? "@nav-active@" : "transparent" }
                    RowLayout {
                        anchors.fill: row
                        anchors.leftMargin: 8; anchors.rightMargin: 8
                        spacing: 12
                        Rectangle {
                            Layout.preferredWidth: 28; Layout.preferredHeight: 28
                            radius: 10
                            color: step.done || step.current ? step.mark : sidebar.tones[index % 4]
                            Text {
                                anchors.centerIn: parent
                                text: step.done ? "✓" : (index + 1).toString()
                                color: step.done || step.current ? "@on-accent@" : step.mark
                                font.family: "@font-family@"; font.pixelSize: 12; font.bold: true
                            }
                        }
                        Text {
                            Layout.fillWidth: true
                            text: display
                            color: step.current || step.done ? "@nav-text@" : "@text-muted@"
                            font.family: "@font-family@"; font.pixelSize: 13; font.bold: step.current
                            elide: Text.ElideRight
                        }
                    }
                }
            }
            // Bottom card: progress and the About button. Shown only when every step
            // still gets a row of at least 32 pixels next to it (logo block about 170px).
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 128
                visible: panel.height - 32 - 170 - 138 >= steps.count * 34
                radius: 22
                color: "@hero@"
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 4
                    Rectangle {
                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: 34; Layout.preferredHeight: 34
                        radius: 12; color: "@mark-3@"
                        Text { anchors.centerIn: parent; text: "★"; color: "@on-accent@"; font.pixelSize: 16; font.bold: true }
                    }
                    Text {
                        Layout.fillWidth: true
                        horizontalAlignment: Text.AlignHCenter
                        text: qsTr("Step %1 of %2").arg(ViewManager.currentStepIndex + 1).arg(steps.count)
                        color: "@text@"; font.family: "@font-family@"; font.pixelSize: 13; font.bold: true
                    }
                    Button {
                        id: about
                        Layout.fillWidth: true
                        Layout.preferredHeight: 32
                        text: qsTr("About Corry @CORRY_VERSION@")
                        onClicked: debug.about()
                        Accessible.name: text
                        contentItem: Text { text: about.text; color: "@on-accent@"; font.family: "@font-family@"; font.pixelSize: 12; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                        background: Rectangle {
                            radius: 16
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0; color: about.hovered ? "@accent-dark@" : "@accent@" }
                                GradientStop { position: 1; color: about.hovered ? "@accent@" : "@accent-light@" }
                            }
                        }
                    }
                }
            }
        }
    }
}
