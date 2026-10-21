// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.3
import QtMultimedia 6.0
Item {
    id: backend
    property url sourceUrl: ""
    property bool video: true
    property bool muted: false
    property real volume: 0.2
    property bool loop: false
    readonly property bool playing: player.playbackState === MediaPlayer.PlayingState
    readonly property bool failed: player.error !== MediaPlayer.NoError
    readonly property int position: player.position
    readonly property int duration: player.duration
    function play() { player.play() }
    function pause() { player.pause() }
    function stop() { player.stop() }
    MediaPlayer {
        id: player
        source: backend.sourceUrl
        loops: backend.loop ? MediaPlayer.Infinite : 1
        videoOutput: backend.video ? screen : null
        audioOutput: AudioOutput { volume: backend.volume; muted: backend.muted }
    }
    VideoOutput {
        id: screen
        anchors.fill: parent
        visible: backend.video
        fillMode: VideoOutput.PreserveAspectFit
    }
    Component.onDestruction: player.stop()
}
