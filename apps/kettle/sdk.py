"""The Kettle SDK: things a Kettle app (plain QML) can't do by itself.

Every app gets a `kettle` object:

    kettle.playNote(60, "piano")          play a note (MIDI number, instrument)
    kettle.playDrum("kick")               kick, snare, hat or clap
    kettle.playSong(json)                 mix a whole song and play it
    kettle.stop()                         stop the song
    kettle.exportSong(json, "My Song")    save it as MP3 (or WAV) in ~/Music
    kettle.save("key", "text")            remember something for next time
    kettle.load("key")                    read it back ("" if nothing saved)
    kettle.canMp3                         true when MP3 export is available

Signals: playbackStarted(durationMs), playbackFinished(), exportFinished(path, error)

A song is JSON: {"bpm": 120, "steps": 32,
                 "notes": [{"step": 0, "pitch": 60, "length": 1, "inst": "piano"}],
                 "drums": [{"step": 0, "kind": "kick"}]}
Each step is a 16th note.
"""
import array
import json
import math
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import wave
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

import common

RATE = 22050
TMP = Path(tempfile.gettempdir()) / "kettle-sound"

# instrument: (partials as (frequency multiple, loudness), how fast it fades)
INSTRUMENTS = {
    "piano": ([(1, 1.0), (2, 0.45), (3, 0.22), (4, 0.11), (5, 0.05)], 3.0),
    "synth": ([(1, 1.0), (3, 0.33), (5, 0.2), (7, 0.14), (9, 0.11)], 1.4),
    "bell":  ([(1, 1.0), (2.76, 0.5), (5.4, 0.25), (8.93, 0.12)], 1.8),
    "organ": ([(0.5, 0.5), (1, 1.0), (2, 0.6), (4, 0.3)], 0.25),
}
DRUMS = ("kick", "snare", "hat", "clap")


# ------------------------------------------------------------ synth --

_cache = {}


def tone(midi, inst="piano", seconds=0.8):
    key = (int(midi), inst, round(seconds, 2))
    if key in _cache:
        return _cache[key]
    partials, fade = INSTRUMENTS.get(inst, INSTRUMENTS["piano"])
    freq = 440.0 * 2 ** ((int(midi) - 69) / 12)
    n = int(seconds * RATE)
    attack = int(0.005 * RATE)
    release = int(0.03 * RATE)
    env = [math.exp(-fade * i / RATE) * min(1.0, i / attack if attack else 1.0)
           * min(1.0, (n - i) / release) for i in range(n)]
    out = array.array("f", bytes(4 * n))
    for mult, amp in partials:
        w = 2 * math.pi * freq * mult / RATE
        if w >= math.pi:          # above what 22 kHz audio can hold
            continue
        for i in range(n):
            out[i] += amp * env[i] * math.sin(w * i)
    _cache[key] = out
    return out


def drum(kind):
    key = ("drum", kind)
    if key in _cache:
        return _cache[key]
    rnd = random.Random(kind)
    if kind == "kick":
        n = int(0.35 * RATE)
        out, phase = array.array("f", bytes(4 * n)), 0.0
        for i in range(n):
            t = i / RATE
            phase += 2 * math.pi * (45 + 75 * math.exp(-30 * t)) / RATE
            out[i] = 1.4 * math.sin(phase) * math.exp(-9 * t)
    elif kind == "snare":
        n = int(0.22 * RATE)
        out = array.array("f", bytes(4 * n))
        for i in range(n):
            t = i / RATE
            out[i] = (0.7 * rnd.uniform(-1, 1) * math.exp(-20 * t)
                      + 0.5 * math.sin(2 * math.pi * 185 * t) * math.exp(-28 * t))
    elif kind == "hat":
        n = int(0.07 * RATE)
        out, prev = array.array("f", bytes(4 * n)), 0.0
        for i in range(n):
            x = rnd.uniform(-1, 1)
            out[i] = 0.45 * (x - prev) * math.exp(-70 * i / RATE)
            prev = x
    else:  # clap: three quick bursts and a tail
        n = int(0.2 * RATE)
        out = array.array("f", bytes(4 * n))
        for i in range(n):
            t = i / RATE
            burst = max(math.exp(-180 * abs(t - s)) for s in (0.0, 0.011, 0.022))
            out[i] = 0.7 * rnd.uniform(-1, 1) * max(burst, 0.4 * math.exp(-25 * t))
    _cache[key] = out
    return out


def render(song):
    bpm = max(40, min(240, int(song.get("bpm", 120))))
    step = 60.0 / bpm / 4
    steps = int(song.get("steps", 32))
    total = int((steps * step + 1.5) * RATE)
    mix = array.array("f", bytes(4 * total))

    def add(sound, at):
        start = int(at * RATE)
        for i in range(min(len(sound), total - start)):
            mix[start + i] += sound[i]

    for note in song.get("notes", []):
        length = max(1, int(note.get("length", 1)))
        add(tone(note["pitch"], note.get("inst", "piano"), max(0.5, length * step + 0.35)),
            int(note["step"]) * step)
    for hit in song.get("drums", []):
        if hit.get("kind") in DRUMS:
            add(drum(hit["kind"]), int(hit["step"]) * step)

    peak = max((abs(x) for x in mix), default=0.0) or 1.0
    scale = 0.9 * 32767 / peak
    pcm = array.array("h", (int(x * scale) for x in mix))
    return pcm, steps * step


def write_wav(path, samples):
    if samples.typecode == "f":
        peak = max((abs(x) for x in samples), default=0.0) or 1.0
        samples = array.array("h", (int(x / peak * 0.8 * 32767) for x in samples))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(samples.tobytes())
    return path


# ----------------------------------------------------------- player --

MAX_NOTES = 6        # how many short sounds may play at once


class Player:
    """Plays WAV files with whatever the computer has (PipeWire on Kettle).

    Every sound is killed shortly after it should have ended, so a stuck sound card
    (it happens in virtual machines) can't pile up players that never stop.
    """

    def __init__(self):
        self.song = None
        self.notes = []

    @staticmethod
    def _command(path):
        for cmd in (["pw-play", str(path)], ["paplay", str(path)], ["aplay", "-q", str(path)]):
            if shutil.which(cmd[0]):
                return cmd
        return None

    @staticmethod
    def _kill(proc):
        if proc and proc.poll() is None:
            proc.kill()

    def play(self, path, song=False, seconds=1.0):
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            return None
        cmd = self._command(path)
        if not cmd:
            return None
        if song:
            self.stop()
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if song:
            self.song = proc
        else:
            self.notes = [p for p in self.notes if p.poll() is None]
            while len(self.notes) >= MAX_NOTES:
                self._kill(self.notes.pop(0))
            self.notes.append(proc)
        # safety net: never let a sound outlive its length by more than a second
        timer = threading.Timer(seconds + 1.0, self._kill, args=(proc,))
        timer.daemon = True
        timer.start()
        return proc

    def stop(self):
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(None, 0)
        self._kill(self.song)
        self.song = None
        for p in self.notes:
            self._kill(p)
        self.notes = []


# -------------------------------------------------------------- SDK --

def _safe_name(text, default="My Song"):
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", text or "").strip(" .")
    return name[:60] or default


class KettleSDK(QObject):
    playbackStarted = Signal(int, arguments=["durationMs"])
    playbackFinished = Signal()
    exportFinished = Signal(str, str, arguments=["path", "error"])

    def __init__(self, app_id="app", parent=None):
        super().__init__(parent)
        self.app_id = common.slugify(app_id)
        self.player = Player()
        self._song_id = 0
        TMP.mkdir(parents=True, exist_ok=True)

    # ---- sounds
    @Slot(int, str)
    def playNote(self, pitch, inst="piano"):
        path = TMP / f"note-{inst}-{int(pitch)}.wav"
        if not path.exists():
            write_wav(path, tone(pitch, inst))
        self.player.play(path, seconds=0.8)

    @Slot(str)
    def playDrum(self, kind):
        if kind not in DRUMS:
            return
        path = TMP / f"drum-{kind}.wav"
        if not path.exists():
            write_wav(path, drum(kind))
        self.player.play(path, seconds=0.4)

    @Slot(str)
    def playSong(self, song_json):
        self._song_id += 1
        my_id = self._song_id

        def work():
            pcm, seconds = render(json.loads(song_json))
            if my_id != self._song_id:        # stop was pressed while mixing
                return
            path = write_wav(TMP / "song.wav", pcm)
            proc = self.player.play(path, song=True, seconds=len(pcm) / RATE)
            self.playbackStarted.emit(int(seconds * 1000))
            if proc:
                proc.wait()
                if my_id == self._song_id:
                    self.playbackFinished.emit()
        threading.Thread(target=work, daemon=True).start()

    @Slot()
    def stop(self):
        self._song_id += 1
        self.player.stop()

    # ---- export
    @Property(bool, constant=True)
    def canMp3(self):
        return shutil.which("lame") is not None

    @Slot(str, str)
    def exportSong(self, song_json, name):
        def work():
            try:
                pcm, _ = render(json.loads(song_json))
                music = common.HOME / "Music"
                music.mkdir(parents=True, exist_ok=True)
                base = music / _safe_name(name)
                wav = write_wav(base.with_suffix(".wav"), pcm)
                if shutil.which("lame"):
                    mp3 = base.with_suffix(".mp3")
                    subprocess.run(["lame", "--quiet", "-V2", str(wav), str(mp3)], check=True)
                    wav.unlink()
                    self.exportFinished.emit(str(mp3), "")
                else:
                    self.exportFinished.emit(str(wav), "")
            except Exception as exc:
                self.exportFinished.emit("", str(exc))
        threading.Thread(target=work, daemon=True).start()

    # ---- remembering things
    def _store(self):
        return common.DATA / "kettle" / "data" / f"{self.app_id}.json"

    def _read(self):
        try:
            return json.loads(self._store().read_text("utf-8"))
        except (OSError, ValueError):
            return {}

    @Slot(str, str)
    def save(self, key, value):
        data = self._read()
        data[key] = value
        self._store().parent.mkdir(parents=True, exist_ok=True)
        self._store().write_text(json.dumps(data), "utf-8")

    @Slot(str, result=str)
    def load(self, key):
        value = self._read().get(key, "")
        return value if isinstance(value, str) else json.dumps(value)
