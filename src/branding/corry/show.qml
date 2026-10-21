// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.3
import QtQuick.Controls 2.10
import QtQuick.Layouts 1.3
import "slides/Slides.js" as Content
Rectangle {
    id: presentation
    color: "#faf9fc"
    property var slides: Content.slides
    property int currentSlide: 0
    property bool active: false
    property bool paused: false
    property var slide: slides.length ? slides[currentSlide] : ({title: qsTr("Your system is taking shape"), description: qsTr("Keep the computer connected to power until installation finishes."), image: "welcome.svg"})
    function advance(offset) { if (slides.length) currentSlide = (currentSlide + offset + slides.length) % slides.length }
    function onActivate() { active = true; currentSlide = 0 }
    function onLeave() { active = false }
    Timer { interval: 9000; repeat: true; running: presentation.active && !presentation.paused && presentation.slides.length > 1; onTriggered: presentation.advance(1) }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 24; spacing: 12
        Text { text: qsTr("A NEW START IS ON ITS WAY"); font.pixelSize: 11; font.letterSpacing: 1.5; color: "#74717c"; Layout.fillWidth: true }
        Image {
            Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 120
            source: Qt.resolvedUrl("slides/" + presentation.slide.image)
            fillMode: Image.PreserveAspectFit; asynchronous: true
        }
        Text { text: presentation.slide.title; textFormat: Text.PlainText; font.pixelSize: 26; font.bold: true; color: "#272530"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        Text { text: presentation.slide.description; textFormat: Text.PlainText; font.pixelSize: 15; color: "#74717c"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        RowLayout {
            Layout.fillWidth: true
            Button { text: "←"; Accessible.name: qsTr("Previous image"); enabled: presentation.slides.length > 1; onClicked: presentation.advance(-1) }
            Button { text: presentation.paused ? qsTr("Play") : qsTr("Pause"); onClicked: presentation.paused = !presentation.paused }
            Text { text: presentation.slides.length ? (presentation.currentSlide + 1) + " / " + presentation.slides.length : qsTr("Preparing your system"); color: "#74717c"; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true }
            Button { text: "→"; Accessible.name: qsTr("Next image"); enabled: presentation.slides.length > 1; onClicked: presentation.advance(1) }
        }
    }
}
