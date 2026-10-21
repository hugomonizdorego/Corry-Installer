// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtMultimedia
Item {
    id: root
    property url source
    signal failed()
    onSourceChanged: if (source.toString() !== "") player.play()
    MediaPlayer {
        id: player
        source: root.source
        loops: MediaPlayer.Infinite
        videoOutput: output
        onErrorOccurred: root.failed()
    }
    VideoOutput { id: output; anchors.fill: parent; fillMode: VideoOutput.PreserveAspectFit }
}
