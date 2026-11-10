// Kettle Linux login splash (shown while the desktop loads)
import QtQuick

Rectangle {
    id: root
    color: "#0a0f24"
    property int stage

    Image {
        anchors.fill: parent
        source: "file:///usr/share/wallpapers/Kettle/contents/images/1920x1080.png"
        fillMode: Image.PreserveAspectCrop
    }

    Column {
        anchors.centerIn: parent
        spacing: 28

        Image {
            id: logo
            anchors.horizontalCenter: parent.horizontalCenter
            source: "file:///usr/share/icons/hicolor/scalable/apps/kettle-logo.svg"
            width: 150; height: 150
            sourceSize: Qt.size(300, 300)
            SequentialAnimation on opacity {
                loops: Animation.Infinite
                NumberAnimation { to: 0.55; duration: 900; easing.type: Easing.InOutSine }
                NumberAnimation { to: 1.0;  duration: 900; easing.type: Easing.InOutSine }
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Kettle Linux"
            color: "white"
            font.family: "Inter"
            font.pixelSize: 38
            font.weight: Font.Light
            font.letterSpacing: 2
        }

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 240; height: 4; radius: 2
            color: "#33ffffff"
            Rectangle {
                height: parent.height; radius: 2
                color: "#ffb347"
                width: parent.width * Math.min(1, root.stage / 6)
                Behavior on width { NumberAnimation { duration: 450; easing.type: Easing.OutCubic } }
            }
        }
    }
}
