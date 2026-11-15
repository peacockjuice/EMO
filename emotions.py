# Stream prebuilt frames into the OLED buffer; no full animation bank in RAM.
import asyncio, time
import random
from emotion_sequences import SEQUENCES, ALIASES

async def play(o, sequence):
    import bmo
    with open("emotions.bin", "rb") as f:
        for index, duration in sequence:
            if bmo.S["ver"] != bmo._v:
                raise bmo.Changed
            started = time.ticks_ms()
            f.seek(index * 1024)
            if f.readinto(o.buffer) != 1024:
                raise ValueError("Truncated animation frame")
            o.show()
            while True:
                remaining = duration - time.ticks_diff(time.ticks_ms(), started)
                if remaining <= 0: break
                await asyncio.sleep_ms(min(40, remaining))
                if bmo.S["ver"] != bmo._v:
                    raise bmo.Changed

def install(moods):
    def make(sequence):
        async def cycle(o):
            await play(o, sequence)
        return cycle
    for name, sequence in SEQUENCES.items():
        moods[name] = make(sequence)

    for alias, target in ALIASES.items():
        moods[alias] = moods[target]
    import behaviour
    async def named(o,key):
        await play(o,SEQUENCES[key])
    def scene_mode(key):
        async def run(o):
            await behaviour.manual(o,key,named)
        return run
    for key in behaviour.SCENES:
        moods[key]=scene_mode(key)
    async def auto(o):
        await behaviour.automatic(o,named)
    moods["auto"] = auto
    import showcase
    async def demo(o):
        await showcase.run(o,play)
    moods["demo"] = demo

