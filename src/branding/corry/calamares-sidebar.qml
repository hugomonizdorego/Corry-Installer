// SPDX-License-Identifier: GPL-3.0-or-later
import io.calamares.ui 1.0
import io.calamares.core 1.0
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
// Corry header: product title and a horizontal stepper. Calamares allows at
// most 128 px for the Corry header (see CalamaresWindow.cpp).
Rectangle {
    id: header
    height: 116
    color: "#ffffff"
    property color accent: "#6445a4"
    property color tint: "#f0ecf8"
    property string product: ""
    property string logo: ""
    property string stepName: ""
    Component.onCompleted: {
        accent = Branding.styleString(Branding.SidebarTextCurrent)
        tint = Branding.styleString(Branding.SidebarBackgroundCurrent)
        product = Branding.shortProductName()
        logo = "file:" + Branding.imagePath(Branding.ProductLogo)
    }
    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 32; anchors.rightMargin: 32; anchors.topMargin: 14; anchors.bottomMargin: 10
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Image { source: header.logo; sourceSize.width: 34; sourceSize.height: 34; Layout.preferredWidth: 34; Layout.preferredHeight: 34 }
            ColumnLayout {
                spacing: 1
                Layout.fillWidth: true
                Text { text: qsTr("Install %1").arg(header.product); color: "#1d2129"; font.pixelSize: 17; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                Text {
                    text: qsTr("Step %1 of %2").arg(ViewManager.currentStepIndex + 1).arg(steps.count) + (header.stepName ? "  ·  " + header.stepName : "")
                    color: "#6b7280"; font.pixelSize: 12; elide: Text.ElideRight; Layout.fillWidth: true
                }
            }
            Text { text: "Corry @CORRY_VERSION@"; color: "#9ca3af"; font.pixelSize: 11 }
            Button {
                id: about
                text: qsTr("About")
                flat: true
                onClicked: debug.about()
                Accessible.name: text
                contentItem: Text { text: about.text; color: about.hovered ? header.accent : "#6b7280"; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { radius: 14; color: about.hovered ? header.tint : "transparent"; border.color: "#e5e7eb" }
            }
        }
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
                    Layout.preferredHeight: 44
                    Rectangle {
                        visible: index > 0
                        x: 0; width: parent.width / 2; y: 10; height: 2
                        color: step.done || step.current ? header.accent : "#e5e7eb"
                    }
                    Rectangle {
                        visible: index < steps.count - 1
                        x: parent.width / 2; width: parent.width / 2; y: 10; height: 2
                        color: step.done ? header.accent : "#e5e7eb"
                    }
                    Rectangle {
                        width: 22; height: 22; radius: 11
                        anchors.horizontalCenter: parent.horizontalCenter
                        color: step.done ? header.accent : step.current ? header.tint : "#f3f4f6"
                        border.width: step.current ? 2 : 0
                        border.color: header.accent
                        Text {
                            anchors.centerIn: parent
                            text: step.done ? "✓" : (index + 1).toString()
                            color: step.done ? "#ffffff" : step.current ? header.accent : "#9ca3af"
                            font.pixelSize: 11; font.bold: true
                        }
                    }
                    Text {
                        y: 27
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        text: display
                        color: step.current ? header.accent : step.done ? "#374151" : "#9ca3af"
                        font.pixelSize: 11; font.bold: step.current
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#e5e7eb" }
}
