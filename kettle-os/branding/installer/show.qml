/* Slideshow shown while Kettle Linux installs */
import QtQuick 2.0;
import calamares.slideshow 1.0;

Presentation
{
    id: presentation

    function onActivate() { }
    function onLeave() { }

    Timer {
        interval: 7000
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: presentation.goToNextSlide()
    }

    Slide {
        Rectangle {
            anchors.fill: parent
            color: "#17142b"
            Column {
                anchors.centerIn: parent
                spacing: 16
                Image {
                    anchors.horizontalCenter: parent.horizontalCenter
                    source: "kettle-logo.png"
                    width: 110; height: 110
                    fillMode: Image.PreserveAspectFit
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Kettle Linux is boiling onto your disk..."
                    color: "white"; font.pixelSize: 22
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Grab a cup of tea. This takes a few minutes."
                    color: "#c9bfe8"; font.pixelSize: 15
                }
            }
        }
    }

    Slide {
        Rectangle {
            anchors.fill: parent
            color: "#17142b"
            Column {
                anchors.centerIn: parent
                spacing: 12
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Make your own apps"; color: "#ffb347"; font.pixelSize: 24; font.bold: true }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Kettle Studio shows your app live while you type,"; color: "white"; font.pixelSize: 15 }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "and Publish shares it on the Kettle Store."; color: "white"; font.pixelSize: 15 }
            }
        }
    }

    Slide {
        Rectangle {
            anchors.fill: parent
            color: "#17142b"
            Column {
                anchors.centerIn: parent
                spacing: 12
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Games and apps, one click away"; color: "#ffb347"; font.pixelSize: 24; font.bold: true }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Steam, Minecraft, Discord, Spotify, LibreOffice and more"; color: "white"; font.pixelSize: 15 }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "are in the Kettle Store under Popular Apps."; color: "white"; font.pixelSize: 15 }
            }
        }
    }
}
