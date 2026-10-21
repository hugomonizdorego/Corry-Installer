// SPDX-License-Identifier: GPL-3.0-or-later
import io.calamares.ui 1.0
import io.calamares.core 1.0
import QtQuick 2.3
import QtQuick.Controls 2.10
import QtQuick.Layouts 1.3
Rectangle {
    id: header
    height: 112
    color: "#ffffff"
    property color accent: "#08786f"
    property color tint: "#e6f4f1"
    property string product: ""
    property string logo: ""
    Component.onCompleted: {
        accent = Branding.styleString(Branding.SidebarTextCurrent)
        tint = Branding.styleString(Branding.SidebarBackgroundCurrent)
        product = Branding.shortProductName()
        logo = "file:" + Branding.imagePath(Branding.ProductLogo)
    }
    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 28; anchors.rightMargin: 28; anchors.topMargin: 12; anchors.bottomMargin: 9
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Image { source: header.logo; Layout.preferredWidth: 28; Layout.preferredHeight: 28 }
            Text { text: "Corry"; color: "#21343d"; font.pixelSize: 21; font.bold: true }
            Text { text: "/  " + header.product; color: "#526970"; font.pixelSize: 14; elide: Text.ElideRight; Layout.fillWidth: true }
            Button { text: qsTr("About"); flat: true; onClicked: debug.about(); Accessible.name: text }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 5
            Repeater {
                model: ViewManager
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 37
                    radius: 7
                    color: index === ViewManager.currentStepIndex ? header.tint : "#f2f7f6"
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 6; spacing: 5
                        Text { text: index < ViewManager.currentStepIndex ? "✓" : (index + 1).toString(); color: index <= ViewManager.currentStepIndex ? header.accent : "#526970"; font.bold: true; font.pixelSize: 12 }
                        Text { text: display; color: index === ViewManager.currentStepIndex ? header.accent : "#526970"; font.pixelSize: 12; elide: Text.ElideRight; Layout.fillWidth: true }
                    }
                }
            }
        }
    }
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#d7e2e1" }
}
