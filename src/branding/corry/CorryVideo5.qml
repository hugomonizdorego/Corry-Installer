// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.15
import QtMultimedia 5.9
Item {
    id: root
    property url source
    signal failed()
    MediaPlayer {
        id: player
        source: root.source
        autoPlay: true
        muted: true
        loops: MediaPlayer.Infinite
        onError: root.failed()
    }
    VideoOutput { anchors.fill: parent; source: player; fillMode: VideoOutput.PreserveAspectFit }
}
