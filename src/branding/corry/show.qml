// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.3
import QtQuick.Layouts 1.3
Rectangle {
    color: "#f6f8fb"
    function onActivate() {}
    function onLeave() {}
    ColumnLayout {
        anchors.centerIn: parent
        width: parent.width * 0.85
        spacing: 20
        Image { source: "welcome.svg"; Layout.fillWidth: true; Layout.preferredHeight: 180; fillMode: Image.PreserveAspectFit }
        Text { text: qsTr("Your desktop is taking shape."); color: "#20394b"; font.pixelSize: 25; font.bold: true; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        Text { text: qsTr("Corry is applying your choices. Keep the computer connected to power until installation finishes."); color: "#526a7b"; font.pixelSize: 15; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    }
}
