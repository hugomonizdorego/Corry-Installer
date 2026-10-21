// SPDX-License-Identifier: GPL-3.0-or-later
import io.calamares.ui 1.0
import io.calamares.core 1.0
import QtQuick 2.3
import QtQuick.Controls 2.10
import QtQuick.Layouts 1.3
Rectangle {
    color: "#142c3d"
    anchors.fill: parent
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 8
        Image {
            Layout.topMargin: 14
            Layout.preferredWidth: 46
            Layout.preferredHeight: 46
            source: "file:" + Branding.imagePath(Branding.ProductLogo)
        }
        Text { text: "Corry"; color: "white"; font.pixelSize: 28; font.bold: true }
        Text { text: qsTr("A clear path to your desktop."); color: "#bdd0dc"; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 12 }
        Rectangle { Layout.fillWidth: true; height: 1; color: "#345061"; Layout.topMargin: 14; Layout.bottomMargin: 8 }
        ScrollView {
          id: stepsArea
          Layout.fillWidth: true
          Layout.fillHeight: true
          clip: true
          contentWidth: availableWidth
          Column {
           width: stepsArea.availableWidth
           spacing: 5
           Repeater {
            model: ViewManager
            Rectangle {
                width: parent.width
                height: Math.max(48, stepText.implicitHeight + 18)
                radius: 9
                color: index === ViewManager.currentStepIndex ? "#29495b" : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 8
                    Rectangle {
                        width: 25; height: 25; radius: 12
                        color: index < ViewManager.currentStepIndex ? "#88cfc9" : index === ViewManager.currentStepIndex ? "#ee6848" : "#345061"
                        Text { anchors.centerIn: parent; text: index < ViewManager.currentStepIndex ? "✓" : index + 1; color: index < ViewManager.currentStepIndex ? "#142c3d" : "white"; font.pixelSize: 12 }
                    }
                    Text { id: stepText; text: display; color: index === ViewManager.currentStepIndex ? "white" : "#bdd0dc"; wrapMode: Text.WordWrap; font.pixelSize: 13; Layout.fillWidth: true }
                }
            }
        }
          }
        }
        Text { text: qsTr("CORRY • DEVELOPMENT"); color: "#88cfc9"; font.pixelSize: 10; font.letterSpacing: 1 }
        Text { text: qsTr("Review your choices before installing."); color: "#bdd0dc"; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 11 }
        Button { text: qsTr("About"); Layout.fillWidth: true; onClicked: debug.about(); Accessible.name: text }
    }
}
