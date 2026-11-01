// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "slides/Slides.js" as Content
import "media.js" as Media
// Shown while the system is being installed, inside Corry's white page card.
// Accent colors are replaced per distribution by tools/install-profile.sh.
Rectangle {
    id: presentation
    color: "#ffffff"
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
        anchors.fill: parent; anchors.margins: 8; spacing: 36
        // Slide images are shown in a 16:9 card (about 600x338 in the 1120x780
        // window). Recommended images: 1600x900 JPEG/PNG, or SVG with a 16:9 viewBox.
        Item {
            id: frame
            Layout.fillWidth: true; Layout.preferredWidth: 3
            Layout.preferredHeight: Math.round(width * 9 / 16)
            Layout.maximumHeight: parent.height
            Layout.alignment: Qt.AlignVCenter
            // Soft shadow under the picture card.
            Rectangle { anchors.fill: parent; anchors.topMargin: 10; anchors.leftMargin: 6; anchors.rightMargin: 6; radius: 24; color: "#c5d2e4"; opacity: 0.35 }
            Rectangle { anchors.fill: parent; anchors.topMargin: 5; anchors.leftMargin: 3; anchors.rightMargin: 3; radius: 23; color: "#c5d2e4"; opacity: 0.35 }
            Rectangle {
                anchors.fill: parent
                radius: 22; color: "#f5f8fd"
                Image {
                    anchors.fill: parent; anchors.margins: 14
                    source: Qt.resolvedUrl("slides/" + presentation.slide.image)
                    fillMode: Image.PreserveAspectFit; asynchronous: true; smooth: true; mipmap: true
                }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 2
            spacing: 14
            Item { Layout.fillHeight: true }
            Rectangle {
                radius: 11; height: 22; width: eyebrow.implicitWidth + 22; color: "#f0ecf8"
                Text { id: eyebrow; anchors.centerIn: parent; text: qsTr("INSTALLING"); font.pixelSize: 10; font.bold: true; font.letterSpacing: 1.4; color: "#4e3585" }
            }
            Text { text: presentation.slide.title; textFormat: Text.PlainText; font.pixelSize: 26; font.bold: true; color: "#1f2a44"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Text { text: presentation.slide.description; textFormat: Text.PlainText; font.pixelSize: 15; lineHeight: 1.25; color: "#64748b"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Row {
                spacing: 6
                Repeater {
                    model: presentation.slides.length
                    Rectangle {
                        width: index === presentation.currentSlide ? 24 : 8; height: 8; radius: 4
                        color: index === presentation.currentSlide ? "#6445a4" : "#d9e2ee"
                        Behavior on width { NumberAnimation { duration: 180 } }
                    }
                }
            }
            Item { Layout.fillHeight: true }
            RowLayout {
                spacing: 10
                SlideControl { text: "←"; Accessible.name: qsTr("Previous image"); enabled: presentation.slides.length > 1; onClicked: presentation.advance(-1) }
                SlideControl { text: presentation.paused ? qsTr("Play") : qsTr("Pause"); onClicked: presentation.paused = !presentation.paused }
                SlideControl { text: "→"; Accessible.name: qsTr("Next image"); enabled: presentation.slides.length > 1; onClicked: presentation.advance(1) }
                SlideControl {
                    visible: sound.active
                    text: presentation.muted ? qsTr("♪ Sound off") : qsTr("♪ Sound on")
                    Accessible.name: presentation.muted ? qsTr("Turn the music on") : qsTr("Mute the music")
                    onClicked: presentation.muted = !presentation.muted
                }
                Text { text: presentation.slides.length ? (presentation.currentSlide + 1) + " / " + presentation.slides.length : ""; color: "#94a3b8"; leftPadding: 6 }
            }
        }
    }
}
