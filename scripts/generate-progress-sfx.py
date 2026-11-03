"""Reproduce the kit's authored progress cue without services or dependencies."""
from pathlib import Path
import math
import struct
import wave

dest = Path(__file__).resolve().parents[1] / 'assets/sfx/progress-rise.wav'
rate, seconds = 48000, 1.6
phase = 0.0
samples = bytearray()
for i in range(round(rate * seconds)):
    t = i / rate
    phase += 2 * math.pi * (260 + 560 * (t / seconds) ** 1.4) / rate
    envelope = min(1.0, t / .06, (seconds - t) / .12)
    value = .24 * envelope * (.85 * math.sin(phase) + .15 * math.sin(2 * phase))
    samples.extend(struct.pack('<h', round(value * 32767)))
with wave.open(str(dest), 'wb') as output:
    output.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
    output.writeframes(samples)
