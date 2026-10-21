// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "slides/Slides.js" as Content
import "media.js" as Media
// Shown while the system is being installed. Accent colors are replaced per
// distribution by tools/install-profile.sh.
Rectangle {
    id: presentation
    color: "#f6f7f9"
    property var slides: Content.slides
    property int currentSlide: 0
    property bool active: false
    property bool paused: false
    property bool muted: false
    property url music: Media.media.sound ? Qt.resolvedUrl(Media.media.sound) : ""
    property var slide: slides.length ? slides[currentSlide] : ({title: qsTr("Your system is taking shape"), description: qsTr("Keep the computer connected to power until installation finishes."), image: "welcome.svg"})
    function advance(offset) { if (slides.length) currentSlide = (currentSlide + offset + slides.length) % slides.length }
    function onActivate() { active = true; currentSlide = 0 }
    function onLeave() { active = false }
    // Background music while installing; muted with the speaker button.
    Loader {
        id: sound
        active: presentation.music.toString() !== ""
        source: "CorrySound6.qml"
        onStatusChanged: {
            if (status === Loader.Error) {
                if (source.toString().indexOf("CorrySound6") >= 0) source = "CorrySound5.qml"
                else active = false
            }
        }
        onLoaded: {
            item.failed.connect(function() { sound.active = false })
            item.volume = Media.media.volume
            item.source = presentation.music
            item.playing = Qt.binding(function() { return presentation.active && !presentation.muted })
        }
    }
    Timer { interval: 9000; repeat: true; running: presentation.active && !presentation.paused && presentation.slides.length > 1; onTriggered: presentation.advance(1) }
    RowLayout {
        anchors.fill: parent; anchors.margins: 24; spacing: 32
        Rectangle {
            Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 3; Layout.minimumHeight: 160
            radius: 20; color: "#ffffff"; border.color: "#e5e7eb"
            Image {
                anchors.fill: parent; anchors.margins: 16
                source: Qt.resolvedUrl("slides/" + presentation.slide.image)
                fillMode: Image.PreserveAspectFit; asynchronous: true; smooth: true; mipmap: true
            }
        }
        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 2
            spacing: 14
            Item { Layout.fillHeight: true }
            Text { text: qsTr("INSTALLING"); font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.6; color: "#6445a4" }
            Text { text: presentation.slide.title; textFormat: Text.PlainText; font.pixelSize: 26; font.bold: true; color: "#1d2129"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Text { text: presentation.slide.description; textFormat: Text.PlainText; font.pixelSize: 15; lineHeight: 1.2; color: "#4b5563"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Row {
                spacing: 6
                Repeater {
                    model: presentation.slides.length
                    Rectangle { width: index === presentation.currentSlide ? 22 : 8; height: 8; radius: 4; color: index === presentation.currentSlide ? "#6445a4" : "#d1d5db" }
                }
            }
            Item { Layout.fillHeight: true }
            RowLayout {
                spacing: 8
                SlideControl { text: "←"; Accessible.name: qsTr("Previous image"); enabled: presentation.slides.length > 1; onClicked: presentation.advance(-1) }
                SlideControl { text: presentation.paused ? qsTr("Play") : qsTr("Pause"); onClicked: presentation.paused = !presentation.paused }
                SlideControl { text: "→"; Accessible.name: qsTr("Next image"); enabled: presentation.slides.length > 1; onClicked: presentation.advance(1) }
                SlideControl {
                    visible: sound.active
                    text: presentation.muted ? qsTr("♪ Sound off") : qsTr("♪ Sound on")
                    Accessible.name: presentation.muted ? qsTr("Turn the music on") : qsTr("Mute the music")
                    onClicked: presentation.muted = !presentation.muted
                }
                Text { text: presentation.slides.length ? (presentation.currentSlide + 1) + " / " + presentation.slides.length : ""; color: "#6b7280"; leftPadding: 6 }
            }
        }
    }
}
