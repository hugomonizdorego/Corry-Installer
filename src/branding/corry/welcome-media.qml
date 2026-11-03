// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick 2.15
import "media.js" as Media
// Corry welcome page picture, in a soft card. Shown in a fixed 560x315 (16:9)
// frame; recommended image: 1600x900 PNG/JPEG or an SVG with a 16:9 viewBox.
// Words between two at signs are theme tokens, replaced by tools/corry-branding.py.
Item {
    id: root
    implicitWidth: 560
    implicitHeight: 315
    property url poster: typeof corryPoster !== "undefined" ? corryPoster : Qt.resolvedUrl(Media.media.poster)
    // Light edge (neumorphic themes) and soft shadow under the card.
    Rectangle { anchors.fill: card; anchors.leftMargin: -4; anchors.topMargin: -4; anchors.rightMargin: 4; anchors.bottomMargin: 4; radius: 24; color: "@highlight@"; opacity: 0.8 }
    Rectangle { anchors.fill: card; anchors.topMargin: 10; anchors.leftMargin: 6; anchors.rightMargin: -2; anchors.bottomMargin: -6; radius: 24; color: "@shadow@"; opacity: 0.45 }
    Rectangle {
        id: card
        anchors.fill: parent
        anchors.bottomMargin: 10
        radius: 22; color: "@surface@"
        Image {
            anchors.fill: parent; anchors.margins: 12
            source: root.poster
            fillMode: Image.PreserveAspectFit; smooth: true; mipmap: true
        }
    }
}
