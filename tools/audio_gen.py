"""Erzeugt lizenzfreie Hintergrundmusik und Soundeffekte rein im Code (nur numpy).

Aufruf:
  python3 tools/audio_gen.py music <ausgabe.wav> <sekunden> [stimmung]
  python3 tools/audio_gen.py sfx <ordner>

Stimmungen: sad (Moll, langsam, Klavier), hopeful (Dur, etwas schneller)
"""
import sys
import wave
import numpy as np

SR = 44100


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    stereo = np.stack([x, x], axis=1) if x.ndim == 1 else x
    data = (stereo * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def piano(freq, dur, vel=0.5):
    t = np.arange(int(SR * dur)) / SR
    tone = np.zeros_like(t)
    for h, a in [(1, 1.0), (2, 0.45), (3, 0.22), (4, 0.12), (5, 0.06)]:
        detune = 1 + 0.0007 * h
        tone += a * np.sin(2 * np.pi * freq * h * detune * t) * np.exp(-t * (1.6 + 0.9 * h))
    attack = np.minimum(1, t / 0.006)
    return vel * tone * attack


def pad(freqs, dur, vel=0.08):
    t = np.arange(int(SR * dur)) / SR
    x = sum(np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2.003 * t) for f in freqs)
    env = np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / 1.2)
    return vel * x * env / len(freqs)


def reverb(x, seconds=2.6, mix=0.35):
    n = int(SR * seconds)
    rng = np.random.default_rng(7)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 3.2)
    ir /= np.sqrt(np.sum(ir ** 2))
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    return (1 - mix) * x + mix * wet * 0.6


PROGS = {
    # (Akkorde als MIDI-Grundtöne + Typ, bpm)
    "sad": ([(57, "m"), (53, "M"), (48, "M"), (55, "M")], 68),  # Am F C G
    "hopeful": ([(48, "M"), (55, "M"), (57, "m"), (53, "M")], 76),  # C G Am F
}


def chord(root, kind):
    third = 3 if kind == "m" else 4
    return [root, root + third, root + 7]


def music(seconds, mood="sad"):
    prog, bpm = PROGS.get(mood, PROGS["sad"])
    beat = 60 / bpm
    bar = beat * 4
    total = int(SR * (seconds + 3))
    out = np.zeros(total)

    def add(sig, start):
        i = int(start * SR)
        j = min(total, i + len(sig))
        if i < total:
            out[i:j] += sig[: j - i]

    t, bar_i = 0.0, 0
    pattern = [0, 1, 2, 1, 0, 2, 1, 2]  # Arpeggio in Achteln
    while t < seconds + 1:
        root, kind = prog[bar_i % len(prog)]
        notes = chord(root, kind)
        add(piano(midi(root - 12), bar * 1.2, 0.30), t)  # Basston
        add(pad([midi(n) for n in notes], bar + 1.0, 0.05), t)
        for k, p in enumerate(pattern):
            n = notes[p] + 12
            if bar_i >= 4 and k in (0, 4):  # Melodie kommt nach 4 Takten dazu
                add(piano(midi(notes[(bar_i + k) % 3] + 24), beat * 2, 0.16), t + k * beat / 2)
            add(piano(midi(n), beat * 1.5, 0.13 if k % 2 else 0.17), t + k * beat / 2)
        t += bar
        bar_i += 1
    out = reverb(out)
    out = out[: int(SR * seconds)]
    fade = int(SR * 2.5)
    out[-fade:] *= np.linspace(1, 0, fade)
    out[: int(SR * 0.8)] *= np.linspace(0, 1, int(SR * 0.8))
    return 0.85 * out / np.max(np.abs(out))


def sfx(folder):
    import os

    os.makedirs(folder, exist_ok=True)
    t = lambda d: np.arange(int(SR * d)) / SR
    # Nachricht empfangen: zwei helle Töne (iMessage-ähnlich, aber eigener Klang)
    a = np.sin(2 * np.pi * 1318 * t(0.12)) * np.exp(-t(0.12) * 30)
    b = np.sin(2 * np.pi * 1760 * t(0.25)) * np.exp(-t(0.25) * 18)
    ping = np.concatenate([a, b]) * 0.5
    write_wav(f"{folder}/receive.wav", reverb(ping, 0.8, 0.2))
    # Nachricht senden: kurzes Wusch
    rng = np.random.default_rng(3)
    n = rng.standard_normal(len(t(0.35)))
    sweep = np.cumsum(n)
    sweep = np.diff(sweep, prepend=0) - np.convolve(n, np.ones(40) / 40, "same")
    env = np.sin(np.pi * t(0.35) / 0.35) ** 2
    write_wav(f"{folder}/send.wav", 0.35 * sweep * env / np.max(np.abs(sweep)))
    # Übergang / Flash: tiefer Boom mit Rauschen
    tt = t(1.6)
    boom = np.sin(2 * np.pi * (55 * np.exp(-tt * 1.2)) * tt) * np.exp(-tt * 2.2)
    noise = rng.standard_normal(len(tt)) * np.exp(-tt * 5) * 0.15
    write_wav(f"{folder}/impact.wav", reverb(0.8 * boom + noise, 1.5, 0.3))
    # Riser vor einer Wendung
    tt = t(1.5)
    riser = np.sin(2 * np.pi * (200 + 900 * tt ** 2) * tt) * (tt / 1.5) ** 2 * 0.25
    riser += rng.standard_normal(len(tt)) * (tt / 1.5) ** 3 * 0.12
    write_wav(f"{folder}/riser.wav", reverb(riser, 1.0, 0.3))
    # Tastatur-Tippen (kurze Klicks)
    clicks = np.zeros(int(SR * 1.2))
    for k in range(9):
        i = int(SR * (0.05 + k * 0.12 + rng.uniform(0, 0.04)))
        c = rng.standard_normal(300) * np.exp(-np.arange(300) / 40)
        clicks[i : i + 300] += c * 0.25
    write_wav(f"{folder}/typing.wav", clicks)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "music":
        write_wav(sys.argv[2], music(float(sys.argv[3]), sys.argv[4] if len(sys.argv) > 4 else "sad"))
    elif cmd == "sfx":
        sfx(sys.argv[2])
    else:
        print(__doc__)
