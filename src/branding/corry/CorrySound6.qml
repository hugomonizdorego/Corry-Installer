// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtMultimedia
Item {
    id: root
    property url source
    property real volume: 0.3
    property bool playing: false
    signal failed()
    onPlayingChanged: playing ? player.play() : player.pause()
    MediaPlayer {
        id: player
        source: root.source
        loops: MediaPlayer.Infinite
        audioOutput: AudioOutput { volume: root.volume }
        onErrorOccurred: root.failed()
    }
}
