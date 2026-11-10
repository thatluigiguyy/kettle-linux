// Kettle Linux default desktop layout.
// Plasma runs this once, the first time each user logs in.

// ---- Wallpaper on every screen ----
var desktopsArray = desktopsForActivity(currentActivity());
for (var i = 0; i < desktopsArray.length; i++) {
    var d = desktopsArray[i];
    d.wallpaperPlugin = "org.kde.image";
    d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    d.writeConfig("Image", "file:///usr/share/wallpapers/Kettle/");
    d.writeConfig("FillMode", 2); // scaled and cropped
}

// ---- Floating, centred dock-style panel ----
var panel = new Panel;
panel.location = "bottom";
panel.height = 2 * Math.floor(gridUnit * 2.75 / 2);
try { panel.floating = true; } catch (e) {}
try { panel.lengthMode = "fit"; } catch (e) {}
try { panel.alignment = "center"; } catch (e) {}
try { panel.hiding = "none"; } catch (e) {}

var launcher = panel.addWidget("org.kde.plasma.kickoff");
launcher.currentConfigGroup = ["General"];
launcher.writeConfig("icon", "kettle-logo");
launcher.currentConfigGroup = ["Shortcuts"];
launcher.writeConfig("global", "Alt+F1");

var tasks = panel.addWidget("org.kde.plasma.icontasks");
tasks.currentConfigGroup = ["General"];
tasks.writeConfig("launchers", [
    "applications:org.kde.dolphin.desktop",
    "applications:firefox-esr.desktop",
    "applications:org.kde.konsole.desktop",
    "applications:org.kde.kate.desktop",
    "applications:org.kettle.studio.desktop",
    "applications:org.kettle.store.desktop",
    "applications:org.kde.discover.desktop",
    "applications:systemsettings.desktop"
]); // must be a real list: a comma-joined string becomes one broken launcher

panel.addWidget("org.kde.plasma.marginsseparator");
panel.addWidget("org.kde.plasma.systemtray");
var clock = panel.addWidget("org.kde.plasma.digitalclock");
clock.currentConfigGroup = ["Appearance"];
clock.writeConfig("showDate", true);
clock.writeConfig("dateFormat", "shortDate");
