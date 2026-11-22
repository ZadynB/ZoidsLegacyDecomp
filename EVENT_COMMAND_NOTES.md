# Field actor event command notes

Findings from the decompiled handlers, ROM-extracted scripts, and map code.

## Actor command arguments

`SPAWN_ACTOR` uses `[actor_id, model_id, x, y, direction, behavior, interaction_flag]`. The handler multiplies the x/y arguments by 8 on regular maps and by 16 on packed-cell maps before passing pixel positions to `CreateFieldActor`. Actor ids 0 through 12 are accepted by the command (id 13 is separately used for the follower).

All queued actor commands begin with the actor id. The remaining arguments are:

| Command | Arguments after actor id | Handler behavior |
|---|---|---|
| `QUEUE_ACTOR_WAIT` | `[direction, duration]` | Faces the direction, pauses movement, timer = duration × 16 ticks. |
| `QUEUE_ACTOR_MOVE_HALF_SPEED` | `[direction, duration]` | Moves directionally; timer = duration × 16 ticks. |
| `QUEUE_ACTOR_MOVE_NORMAL_SPEED` | `[direction, duration]` | Moves directionally; timer = duration × 8 ticks. |
| `QUEUE_ACTOR_MOVE_DOUBLE_SPEED` | `[direction, duration]` | Moves directionally; timer = duration × 4 ticks. |
| `QUEUE_ACTOR_MOVE_TO_*` | `[x, y]` | Moves to a coordinate target; speed controls duration. |
| `QUEUE_ACTOR_HOP` | no meaningful arguments | Runs a fixed 14-tick hop. |
| `QUEUE_ACTOR_SPECIAL_ANIMATION` | `[animation_set_index]` | Index 0–7 into the special animation set for that actor model. |

For ordinary directional movement, the speed vectors are the normal map movement velocities scaled by 1/2, 1, or 2. (The decompiled half-speed branch sets movement mode 2, but uses half the directional velocity; the resulting command speed is still half speed.)

The second stored argument for special animation is not consumed by the general animation selection code. One actor-model-specific path checks it: model `0x36` checks for the value 1 and applies a position/sprite adjustment. Avoid treating that field as a general animation parameter.

## Coordinate units

The coordinate move handler scales each argument by 8 to produce a pixel target. For packed-cell maps (`map id 0`), the event queue first doubles both arguments, so the effective target spacing is 16 pixels. Spawn coordinates use the same map-mode distinction. This is separate from the actor's fixed-point world position and from map-cell lookup, which uses 16-pixel cells on packed maps and 8-pixel cells on regular maps. Confirm the map mode before reusing coordinates from another map.

## Synchronization and script flow

`WAIT_FOR_SCENE_ACTIONS` waits until field actor command queues are empty, temporary event sprite movements finish, and camera movement ends. Put it after queued movement when later dialogue or actions depend on arrival. The event interpreter then resumes the following command.

The extracted script at `0x0803103C` demonstrates the live command format. It moves actor 0 to `[99, 136]`, waits facing south for duration 0, then waits for scene actions. Later it spawns actor 1 with `[1, 142, 99, 145, 0, 7, 0]`, moves north at double speed for duration 8, and synchronizes.

## Integration status and next technical step

The runtime event interpreter and map-script table are decompiled (`src/events/run_event_scripts.c`, `src/events/start_map_event_script.c`, `src/events/commands/event_end.c`). Extracted event scripts are available in `/tmp/zoids-event-extract/data/event_script.json`, and the extracted map table is `/tmp/zoids-event-extract/data/table.map_event_scripts.json`.

The current main checkout does not contain a source-side editable event-script asset or an established script insertion tool. The extracted JSON is a reference, not an insertion format. The map script pointer table has 196 entries at ROM offset `0x007A0BF8` (GBA address `0x087A0BF8`).

An initial disposable-ROM experiment builder is now available at `tools/build_test_cutscene_rom.py`. It expands a clean 8 MiB ROM to 16 MiB, writes a short spawn/move/wait/remove script at offset `0x00800000`, and wraps one selected map's root script to also start the test scene. It requires separate `--rom` and `--out` paths and never changes the input.

The current test target is **map 4, Cebu Town**, which the supplied prologue recording reaches. The map is 92×64 cells; the map-0 warp into town places the player at `(49, 61)`. The test scene is gated by Cebu's original one-time entrance flag 1, so it only runs on the prologue visit and does not add actors or event threads on later visits. On that first visit, the test actor uses free actor id 7 and field model 30 (Bit Cloud; confirmed by the prologue scene script at `0x08073C4F`), spawning at `(52, 59)`, then walking north for 6 double-speed duration units. It uses scripted behavior 7 while moving, waits locally for `duration * 4 + 8` frames, then changes to stationary behavior 2. The scene then starts a separate listener script with `IF_INTERACTED_ACTOR` for actor 7; it displays “Hello there!” and uses `RESTART` to unlock the actor and listen again. Keep the interaction check at the start of its own script: on a failed check, the runtime resets that script to its start and yields. Combining the check after spawn/movement commands would repeat those commands every frame and can fill the actor movement queue. Avoid `WAIT_FOR_SCENE_ACTIONS` here: it waits for unrelated map queues, camera movement, and event sprites, which can remain pending during story transitions.

Example:

```bash
python3 tools/build_test_cutscene_rom.py \
  --rom "Zoids Legacy (USA).gba" \
  --out /tmp/zoids-cutscene-test.gba
```

The tool still accepts `--map-id`, `--x`, `--y`, `--duration`, `--actor-id`, and `--model-id` overrides. It wraps the selected map's existing root script and starts it with the Bit scene and listener, preserving the original startup flow. Coordinates differ between packed-cell and regular maps. The builder preserves the GBA header's required fixed byte at `0xB2` and recalculates the complement checksum; ROM expansion does not use a size byte there. The Bit interaction build still needs emulator testing. Do not use this prototype for release builds; the long-term workflow should represent script data and map table changes in the project build itself.
