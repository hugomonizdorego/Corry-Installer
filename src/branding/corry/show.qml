// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.3
import QtQuick.Controls 2.10
import QtQuick.Layouts 1.3
import "Brand.js" as Brand
Rectangle {
    id: presentation
    color: "#f5f8f8"
    property var slides: Brand.config.installation.slides
    property int currentSlide: 0
    property bool active: false
    property bool paused: false
    property bool musicEnabled: Brand.config.installation.musicEnabled
    property real musicVolume: Brand.config.installation.musicVolume / 100
    readonly property bool musicFailed: music.status === Loader.Error || (music.item ? music.item.failed : false)
    readonly property bool musicPlaying: music.item ? music.item.playing : false
    property var slide: slides[currentSlide]
    function advance(offset) { currentSlide = (currentSlide + offset + slides.length) % slides.length }
    function syncMusic() {
        if (!music.item) return
        if (!active) music.item.stop(); else if (musicEnabled) music.item.play(); else music.item.pause()
    }
    function onActivate() { active = true; currentSlide = 0; syncMusic() }
    function onLeave() { active = false; syncMusic() }
    onMusicEnabledChanged: syncMusic()
    Loader {
        id: music
        active: presentation.active && !!Brand.config.installation.music
        source: "MediaBackend" + corryQtMajorVersion + ".qml"
        onLoaded: {
            item.video = false; item.loop = true
            item.sourceUrl = Qt.resolvedUrl(Brand.config.installation.music)
            item.volume = Qt.binding(function() { return presentation.musicVolume })
            presentation.syncMusic()
        }
    }
    Timer { interval: Brand.config.installation.slideInterval; repeat: true; running: presentation.active && !presentation.paused && presentation.slides.length > 1; onTriggered: presentation.advance(1) }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 20; spacing: 10
        Text { text: Brand.config.installation.eyebrow; textFormat: Text.PlainText; font.pixelSize: 11; font.letterSpacing: 1.5; color: "#526970"; Layout.fillWidth: true }
        Image { Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 100; source: Qt.resolvedUrl(presentation.slide.image); fillMode: Image.PreserveAspectFit; asynchronous: true }
        Text { text: presentation.slide.title; textFormat: Text.PlainText; font.pixelSize: 24; font.bold: true; color: "#21343d"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        Text { text: presentation.slide.description; textFormat: Text.PlainText; font.pixelSize: 14; color: "#526970"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        RowLayout {
            Layout.fillWidth: true
            SlideControl { text: "←"; Accessible.name: qsTr("Previous image"); enabled: presentation.slides.length > 1; onClicked: presentation.advance(-1) }
            SlideControl { text: presentation.paused ? qsTr("Play slides") : qsTr("Pause slides"); onClicked: presentation.paused = !presentation.paused }
            Text { text: (presentation.currentSlide + 1) + " / " + presentation.slides.length; color: "#526970"; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true }
            SlideControl { text: "→"; Accessible.name: qsTr("Next image"); enabled: presentation.slides.length > 1; onClicked: presentation.advance(1) }
        }
        RowLayout {
            Layout.fillWidth: true
            CheckBox { text: presentation.musicFailed ? qsTr("Music unavailable") : qsTr("Background music"); checked: presentation.musicEnabled; enabled: !!Brand.config.installation.music && !presentation.musicFailed; onClicked: presentation.musicEnabled = checked }
            Slider { from: 0; to: 1; value: presentation.musicVolume; Layout.fillWidth: true; enabled: presentation.musicEnabled && !presentation.musicFailed; onMoved: presentation.musicVolume = value; Accessible.name: qsTr("Music volume") }
            Text { text: Math.round(presentation.musicVolume * 100) + "%"; color: "#526970"; font.pixelSize: 12 }
        }
    }
}
