// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.15
import "media.js" as Media
// Corry welcome page media: a muted, looping product video over the welcome
// image, in a soft card. Without a video, or without QtMultimedia, only the
// image is shown. Shown in a fixed 560x315 (16:9) frame. Recommended video:
// 1280x720 WebM.
Item {
    id: root
    implicitWidth: 560
    implicitHeight: 315
    property url poster: typeof corryPoster !== "undefined" ? corryPoster : Qt.resolvedUrl(Media.media.poster)
    property url video: Media.media.video ? Qt.resolvedUrl(Media.media.video) : ""
    // Soft shadow under the card.
    Rectangle { anchors.fill: card; anchors.topMargin: 10; anchors.leftMargin: 6; anchors.rightMargin: 6; radius: 24; color: "#c5d2e4"; opacity: 0.35 }
    Rectangle { anchors.fill: card; anchors.topMargin: 5; anchors.leftMargin: 3; anchors.rightMargin: 3; radius: 23; color: "#c5d2e4"; opacity: 0.35 }
    Rectangle {
        id: card
        anchors.fill: parent
        anchors.bottomMargin: 10
        radius: 22; color: "#f5f8fd"
        Image {
            id: posterImage
            anchors.fill: parent; anchors.margins: 12
            source: root.poster
            fillMode: Image.PreserveAspectFit; smooth: true; mipmap: true
        }
        Loader {
            id: player
            anchors.fill: posterImage
            active: root.video.toString() !== ""
            // Qt 6 first; the Qt 5 variant needs a versioned import.
            source: "CorryVideo6.qml"
            onStatusChanged: {
                if (status === Loader.Error) {
                    if (source.toString().indexOf("CorryVideo6") >= 0) source = "CorryVideo5.qml"
                    else active = false
                }
            }
            onLoaded: {
                item.failed.connect(function() { player.active = false })
                item.source = root.video
            }
        }
    }
}
