"""Starter apps for Kettle Studio's "New App" dialog."""

HELLO = '''import QtQuick
import QtQuick.Controls

// Welcome to Kettle Studio!
// Change anything below and the preview on the right updates by itself.
// Try changing the colours, the text or the emoji.

Rectangle {
    id: root
    width: 480
    height: 360
    gradient: Gradient {
        GradientStop { position: 0.0; color: "#1b1442" }
        GradientStop { position: 1.0; color: "#3a1f4a" }
    }

    Column {
        anchors.centerIn: parent
        spacing: 16

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "\U0001FAD6"
            font.pixelSize: 64
        }

        Text {
            id: greeting
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Hello, Kettle!"
            color: "white"
            font.pixelSize: 32
            font.bold: true
        }

        Button {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Boil it"
            onClicked: greeting.text = "Wheeeee! \U0001F389"
        }
    }
}
'''

COUNTER = '''import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    width: 420
    height: 360
    color: "#1b1442"

    property int count: 0

    Column {
        anchors.centerIn: parent
        spacing: 20

        Text {
            id: number
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.count
            color: "#ffb347"
            font.pixelSize: 96
            font.bold: true
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 12
            Button { text: "-"; onClicked: root.count-- }
            Button { text: "+"; onClicked: { root.count++; bump.restart() } }
            Button { text: "Reset"; onClicked: root.count = 0 }
        }
    }

    // a little bounce every time you press +
    SequentialAnimation {
        id: bump
        NumberAnimation { target: number; property: "scale"; to: 1.25; duration: 90 }
        NumberAnimation { target: number; property: "scale"; to: 1.0; duration: 140 }
    }
}
'''

CLOCK = '''import QtQuick

Rectangle {
    id: root
    width: 480
    height: 300
    gradient: Gradient {
        GradientStop { position: 0.0; color: "#0a0f24" }
        GradientStop { position: 1.0; color: "#341a47" }
    }

    property date now: new Date()

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: root.now = new Date()
    }

    Column {
        anchors.centerIn: parent
        spacing: 6

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: Qt.formatTime(root.now, "hh:mm:ss")
            color: "white"
            font.pixelSize: 72
            font.weight: Font.Light
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: Qt.formatDate(root.now, "dddd, d MMMM yyyy")
            color: "#c9bfe8"
            font.pixelSize: 20
        }
    }
}
'''

PAINT = '''import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    width: 520
    height: 420
    color: "#f7f3ea"

    property color pen: "#e8573a"

    Canvas {
        id: canvas
        anchors.fill: parent
        property real lastX: 0
        property real lastY: 0
        property bool clearing: false

        onPaint: {
            var ctx = getContext("2d")
            if (clearing) {
                ctx.reset()
                clearing = false
                return
            }
            ctx.lineWidth = 6
            ctx.lineCap = "round"
            ctx.strokeStyle = root.pen
            ctx.beginPath()
            ctx.moveTo(lastX, lastY)
            lastX = area.mouseX
            lastY = area.mouseY
            ctx.lineTo(lastX, lastY)
            ctx.stroke()
        }

        MouseArea {
            id: area
            anchors.fill: parent
            onPressed: { canvas.lastX = mouseX; canvas.lastY = mouseY }
            onPositionChanged: canvas.requestPaint()
        }
    }

    // colour palette and clear button
    Row {
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottomMargin: 12
        spacing: 10

        Repeater {
            model: ["#e8573a", "#ffb347", "#3fd0c9", "#7b5cff", "#222222"]
            Rectangle {
                width: 32; height: 32; radius: 16
                color: modelData
                border.width: root.pen === color ? 3 : 1
                border.color: "white"
                MouseArea { anchors.fill: parent; onClicked: root.pen = parent.color }
            }
        }

        Button {
            text: "Clear"
            onClicked: { canvas.clearing = true; canvas.requestPaint() }
        }
    }
}
'''

TEA_TIMER = '''import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    width: 420
    height: 480
    color: "#17123d"

    property int total: 180
    property int left: total
    property bool running: false

    Timer {
        interval: 1000
        repeat: true
        running: root.running
        onTriggered: {
            if (root.left > 0) root.left -= 1
            if (root.left === 0) root.running = false
        }
    }

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 18

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "Tea Timer"
            color: "white"
            font.pixelSize: 26
            font.bold: true
        }

        Item {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 220
            Layout.preferredHeight: 220

            Canvas {
                id: ring
                anchors.fill: parent
                property real progress: root.total > 0 ? root.left / root.total : 0
                onProgressChanged: requestPaint()
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.reset()
                    var c = width / 2, r = c - 12
                    ctx.lineWidth = 14
                    ctx.lineCap = "round"
                    ctx.strokeStyle = "#2c2560"
                    ctx.beginPath()
                    ctx.arc(c, c, r, 0, 2 * Math.PI)
                    ctx.stroke()
                    ctx.strokeStyle = "#ffb347"
                    ctx.beginPath()
                    ctx.arc(c, c, r, -Math.PI / 2, -Math.PI / 2 + 2 * Math.PI * progress)
                    ctx.stroke()
                }
            }

            Text {
                anchors.centerIn: parent
                property int secs: root.left % 60
                text: root.left === 0 ? "\U0001F375"
                      : Math.floor(root.left / 60) + ":" + (secs < 10 ? "0" : "") + secs
                color: "white"
                font.pixelSize: root.left === 0 ? 64 : 48
                font.bold: true
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 8
            Repeater {
                model: [
                    { name: "Green", secs: 120 },
                    { name: "Black", secs: 240 },
                    { name: "Herbal", secs: 300 }
                ]
                Button {
                    text: modelData.name
                    onClicked: {
                        root.running = false
                        root.total = modelData.secs
                        root.left = modelData.secs
                    }
                }
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 8
            Button {
                text: root.running ? "Pause" : "Start"
                enabled: root.left > 0
                onClicked: root.running = !root.running
            }
            Button {
                text: "Reset"
                onClicked: { root.running = false; root.left = root.total }
            }
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: root.left === 0 ? "Your tea is ready!"
                  : root.running ? "Brewing..." : "Pick a tea and press Start"
            color: "#c9bfe8"
            font.pixelSize: 16
        }
    }
}
'''

BLANK = '''import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    width: 480
    height: 360
    color: "#1b1442"

    // Start building your app here!
}
'''

# key: (shown in the New App dialog, in this order)
TEMPLATES = {
    "hello":   {"title": "Hello Kettle", "icon": "\U0001FAD6", "qml": HELLO,
                "description": "A friendly first app with a button."},
    "counter": {"title": "Counter", "icon": "\U0001F522", "qml": COUNTER,
                "description": "Count up and down with a bouncy number.", "width": 420},
    "clock":   {"title": "Clock", "icon": "\U0001F552", "qml": CLOCK,
                "description": "A big live clock with the date.", "height": 300},
    "paint":   {"title": "Paint", "icon": "\U0001F3A8", "qml": PAINT,
                "description": "Draw with your mouse in five colours.", "width": 520, "height": 420},
    "tea":     {"title": "Tea Timer", "icon": "\U0001F375", "qml": TEA_TIMER,
                "description": "Count down the perfect cup of tea.", "width": 420, "height": 480},
    "blank":   {"title": "Blank", "icon": "✨", "qml": BLANK,
                "description": "An empty app. Build anything!"},
}
