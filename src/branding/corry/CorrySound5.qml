// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.15
import QtMultimedia 5.9
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
        volume: root.volume
        loops: MediaPlayer.Infinite
        onError: root.failed()
    }
}
