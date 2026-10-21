// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.3
import QtQuick.Controls 2.10
import QtQuick.Layouts 1.3
import "Brand.js" as Brand
Rectangle {
    id: frame
    color: "#102e2d"; radius: 14
    property bool active: true
    property bool muted: Brand.config.welcome.videoMuted
    property string videoSource: Brand.config.welcome.video
    property bool configured: !!videoSource
    readonly property bool mediaFailed: player.status === Loader.Error || (player.item ? player.item.failed : false)
    readonly property bool isPlaying: player.item ? player.item.playing : false
    function togglePlayback() {
        if (!player.item || mediaFailed) return
        if (player.item.playing) player.item.pause(); else { active = true; player.item.play() }
    }
    function onActivate() { active = true }
    function onLeave() { active = false; if (player.item) player.item.stop() }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 10; spacing: 8
        Item {
            Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 140
            Image { anchors.fill: parent; source: Qt.resolvedUrl(Brand.config.welcome.image); fillMode: Image.PreserveAspectFit; visible: !frame.isPlaying }
            Loader {
                id: player
                anchors.fill: parent
                active: frame.configured
                source: "MediaBackend" + corryQtMajorVersion + ".qml"
                onLoaded: {
                    item.sourceUrl = Qt.binding(function() { return frame.videoSource ? Qt.resolvedUrl(frame.videoSource) : "" })
                    item.muted = Qt.binding(function() { return frame.muted })
                    item.volume = 0.5
                    if (Brand.config.welcome.videoAutoplay && frame.active) item.play()
                }
                visible: frame.isPlaying
            }
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 8
            SlideControl { text: frame.isPlaying ? qsTr("Pause") : qsTr("Play video"); enabled: frame.configured && !frame.mediaFailed; onClicked: frame.togglePlayback() }
            Text { text: frame.mediaFailed ? qsTr("Video unavailable") : frame.configured ? qsTr("Welcome to your next desktop") : qsTr("Welcome"); color: "#d4e8e0"; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            SlideControl { text: frame.muted ? qsTr("Sound off") : qsTr("Sound on"); enabled: frame.configured && !frame.mediaFailed; onClicked: frame.muted = !frame.muted }
        }
    }
}
