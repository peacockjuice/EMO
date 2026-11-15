# Stream prebuilt frames into the OLED buffer; no full animation bank in RAM.
import asyncio, time
from sample_sequences import SEQUENCES

async def play(o, sequence):
    import bmo
    with open("samples.bin", "rb") as f:
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
