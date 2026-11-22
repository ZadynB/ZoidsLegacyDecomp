#!/usr/bin/env python3
"""Build a disposable ROM with an interactable Bit Cloud scene on one map.

This adds an entrance movement and an interaction listener alongside the
selected map's existing startup scripts in the output ROM. It is for validating
event command execution only, not for release builds.
"""

import argparse
from pathlib import Path
import struct

from dialogue import encode_text


ROM_BASE = 0x08000000
MAP_SCRIPT_TABLE_OFFSET = 0x007A0BF8
MAP_COUNT = 196
SCRIPT_OFFSET = 0x00800000
EXPANDED_ROM_SIZE = 0x01000000
GBA_HEADER_FIXED_VALUE = 0x96
EVENT_START_SCRIPTS = 0x09
EVENT_IF_FLAG_CLEAR = 0x17
EVENT_SET_FIELD_ACTOR_BEHAVIOR = 0x07
EVENT_IF_INTERACTED_ACTOR = 0x13
EVENT_RESTART = 0x0B
EVENT_TEXT = 0x20
EVENT_WAIT_FRAMES = 0x0D


def build_script(actor_id: int, model_id: int, x: int, y: int,
                 direction: int, duration: int, talk_address: int) -> bytes:
    """Run only during the prologue entry, walk Bit, then start talk listener."""
    # Behavior 7 processes queued movement. The scene changes it to stationary
    # behavior 2 after the queue finishes so the actor can be interacted with.
    values = (actor_id, model_id, x, y, direction, 7, 0)
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("spawn arguments must fit in one byte")
    if actor_id > 12:
        raise ValueError("use actor id 0..12; id 13 is reserved for the follower")
    if not 0 <= direction <= 7:
        raise ValueError("direction must be 0..7")
    if not 0 <= duration <= 0xFF:
        raise ValueError("duration must fit in one byte")
    script = bytearray()
    # Cebu's original one-time prologue entrance sets flag 1. On later visits,
    # this condition yields at the script start without adding test actors.
    script.extend((EVENT_IF_FLAG_CLEAR, 1))
    script.extend((0x05, *values))                    # SPAWN_ACTOR
    script.extend((0x3B, actor_id, direction, duration))  # MOVE_DOUBLE_SPEED
    # A local timer lets this actor finish without waiting on unrelated map
    # sprites/queues, which can remain active during later story transitions.
    script.extend((EVENT_WAIT_FRAMES, min(0xFF, duration * 4 + 8)))
    script.extend((EVENT_SET_FIELD_ACTOR_BEHAVIOR, actor_id, 2))
    script.extend((EVENT_START_SCRIPTS, 1))
    script.extend(struct.pack("<I", talk_address))
    script.append(0x00)                              # END
    return bytes(script)


def build_talk_script(actor_id: int) -> bytes:
    """Wait for an interaction at this script's start, say hello, and end."""
    text = encode_text(
        "{01 02}Ｂｉｔ\n{01 00}“Ｈｅｌｌｏ　ｔｈｅｒｅ！”"
    )
    return (bytes((EVENT_IF_INTERACTED_ACTOR, actor_id, EVENT_TEXT)) + text +
            bytes((EVENT_RESTART,)))


def build_startup_wrapper(scripts: list[int]) -> bytes:
    """Start the original map scripts and the prologue-gated test scene."""
    if len(scripts) > 0xFF:
        raise ValueError("too many startup scripts")
    wrapper = bytearray((EVENT_START_SCRIPTS, len(scripts)))
    wrapper.extend(struct.pack(f"<{len(scripts)}I", *scripts))
    wrapper.append(0x00)  # END
    while len(wrapper) % 4:
        wrapper.append(0x00)
    return bytes(wrapper)


def update_header_checksum(rom: bytearray) -> None:
    if rom[0xB2] != GBA_HEADER_FIXED_VALUE:
        raise ValueError("input ROM has an invalid GBA header fixed byte at 0xB2")
    rom[0xBD] = (-sum(rom[0xA0:0xBD]) - 0x19) & 0xFF


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", required=True, type=Path,
                        help="clean input ROM; this file is never modified")
    parser.add_argument("--out", required=True, type=Path,
                        help="separate output path for the disposable test ROM")
    parser.add_argument("--map-id", type=int, default=4,
                        help="map index 0..195 (default: 4, Cebu Town from the prologue)")
    parser.add_argument("--x", type=int, default=52,
                        help="actor spawn x coordinate (default: 52, in the clear entrance)")
    parser.add_argument("--y", type=int, default=59,
                        help="actor spawn y coordinate (default: 59, in the clear entrance)")
    parser.add_argument("--actor-id", type=int, default=7)
    parser.add_argument("--model-id", type=int, default=30,
                        help="field actor sprite/model (default: 30, Bit Cloud)")
    parser.add_argument("--direction", type=int, default=0,
                        help="movement direction: 0 north through 7 northwest")
    parser.add_argument("--duration", type=int, default=6,
                        help="double-speed movement duration (default: 6)")
    args = parser.parse_args()

    source = args.rom.resolve()
    destination = args.out.resolve()
    if source == destination:
        parser.error("--out must be different from --rom")
    if not 0 <= args.map_id < MAP_COUNT:
        parser.error(f"--map-id must be in 0..{MAP_COUNT - 1}")
    if not source.is_file():
        parser.error(f"input ROM does not exist: {source}")

    original = source.read_bytes()
    if len(original) != 0x00800000:
        parser.error(f"expected an 8 MiB USA ROM, got {len(original)} bytes")
    if MAP_SCRIPT_TABLE_OFFSET + MAP_COUNT * 4 > len(original):
        parser.error("map script table lies outside the input ROM")

    rom = bytearray(original)
    rom.extend(b"\xFF" * (EXPANDED_ROM_SIZE - len(rom)))
    original_script_pointer = struct.unpack_from(
        "<I", original, MAP_SCRIPT_TABLE_OFFSET + args.map_id * 4
    )[0]
    wrapper_size = (2 + 2 * 4 + 1 + 3) & ~3
    scene_offset = SCRIPT_OFFSET + wrapper_size
    talk_script = build_talk_script(args.actor_id)
    # Script length includes 2-byte flag condition, 8-byte spawn, 4-byte move,
    # 2-byte local wait, 3-byte behavior command, 6-byte nested start, END.
    talk_offset = (scene_offset + 26 + 3) & ~3
    movement_script = build_script(args.actor_id, args.model_id, args.x, args.y,
                                   args.direction, args.duration,
                                   ROM_BASE + talk_offset)
    wrapper = build_startup_wrapper([
        original_script_pointer,
        ROM_BASE + scene_offset,
    ])
    rom[SCRIPT_OFFSET:SCRIPT_OFFSET + len(wrapper)] = wrapper
    rom[scene_offset:scene_offset + len(movement_script)] = movement_script
    rom[talk_offset:talk_offset + len(talk_script)] = talk_script
    pointer_offset = MAP_SCRIPT_TABLE_OFFSET + args.map_id * 4
    struct.pack_into("<I", rom, pointer_offset, ROM_BASE + SCRIPT_OFFSET)
    update_header_checksum(rom)

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(rom)
    print(f"Wrote disposable test ROM: {destination}")
    print(f"Map {args.map_id} starts wrapper 0x{ROM_BASE + SCRIPT_OFFSET:08X}.")
    print(f"Original map script 0x{original_script_pointer:08X} is preserved.")
    print(f"Bit entrance scene starts at 0x{ROM_BASE + scene_offset:08X}.")
    print(f"Bit talk listener starts at 0x{ROM_BASE + talk_offset:08X} when flag 1 is clear.")


if __name__ == "__main__":
    main()
