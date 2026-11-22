# Zoids Legacy ROM Hack — Project Handoff

**Last updated:** November 22, 2026  
**Environment:** Windows + WSL2 Ubuntu 24.04  
**Project:** Zoids Legacy (GBA, USA version)  
**Primary goal:** Create a ROM hack with a substantially different story and potentially custom Zoids.

---

## 1. Project goals and direction

The intended project is a story-focused ROM hack that builds on the original Zoids Legacy game.

The current story concept is:

**Working title: Zoids Legacy: Echoes of the Past**

The story begins with the original protagonist and companions, retaining the original world and characters while introducing new characters, locations, and events.

### Established creative decisions

- **Starter Zoid:** Blade Liger.
- **World:** Expanded original world; retain existing locations and characters.
- **Atmosphere:** A mixture of mystery, conflict, adventure, and friendship.
- **Protagonist:** Keep the original protagonist and companions.
- **New faction:** The Obsidian Order (working name).
- **New character:** Raven (working name), a wandering Zoid researcher.

### Story premise

An unusual Zoid Core is connected to forgotten ancient technology. The protagonist's Blade Liger reacts to other Zoid Cores, attracting the attention of a secret organization.

The first chapter, **The Awakening**, is planned around:

1. A mysterious transmission from an old research facility.
2. The protagonist receiving the Blade Liger.
3. An unusual reaction between Zoid Cores.
4. Meeting Raven.
5. Discovering an abandoned research outpost.
6. An encounter with the Obsidian Order.
7. Learning that the Genesis Core is connected to other ancient sites.

The longer-term mystery involves an ancient network that allowed Zoids to communicate with their environment. The Obsidian Order wants to exploit that network.

**Not yet decided:** Raven's exact role, the full nature of the Obsidian Order, and the circumstances in which the protagonist receives the Blade Liger.

---

## 2. Repository architecture and working environment

### Main repository

```text
/home/zadyn/projects/Zoids/ZoidsLegacyDecomp
```

This is the primary development repository.

Git configuration:

- `origin`: `https://github.com/ZadynB/ZoidsLegacyDecomp.git`
- `upstream`: `https://github.com/jmacato/ZoidsLegacyDecomp.git`

The main branch was verified and pushed to the user's fork.

Known-good baseline:

```text
8428637 Complete initial decompilation verification
```

Tag:

```text
verified-baseline
```

The main repository successfully passed all **1,130 region verification checks**.

Do not reset, restore, or otherwise overwrite the main repository's work without first checking its current status.

### Important worktrees

| Directory | Purpose |
|---|---|
| `ZoidsLegacyDecomp` | Main development repository |
| `ZoidsLegacyExtract` | Historical repository/worktree |
| `ZoidsLegacyExtractFinal` | Historical snapshot at `0944042` |
| `ZoidsLegacyExtractMatchedRepo` | Historical snapshot at `4d9bd0b` |
| `ZoidsLegacyExtractMusic` | Historical snapshot at `b9d133c`; successful extractor environment |
| `agbcc` | Required GBA compiler |

The `ZoidsLegacyExtractMusic` worktree is especially important for event extraction. Its source revision matches the extractor's pinned source hashes.

### Original ROM

```text
/home/zadyn/projects/Zoids/ZoidsLegacyDecomp/Zoids Legacy (USA).gba
```

Keep the original ROM as the clean reference for verification and building.

---

## 3. Build and verification decisions

The project uses the existing decompilation/build system rather than introducing a custom game engine or replacing the original runtime.

The main build and verification command is:

```bash
make verify ROM="Zoids Legacy (USA).gba"
```

Single-region verification:

```bash
python3 tools/verify.py --rom "Zoids Legacy (USA).gba" --region sub_08098BB4
```

### Compiler setup

The required `agbcc` revision is:

```text
da598c1d918402c42c0c0d7128ba14567f3175e9
```

The compiler was built using:

```bash
make -C gcc clean
make -C gcc old
cp gcc/old_agbcc old_agbcc

make -C gcc clean
make -C gcc CC=gcc-14
cp gcc/agbcc agbcc
```

### Existing tools

- `tools/insert_vwf.py`: Text insertion builder; also changes the new-game starter Zoid to Blade Liger. It is not a general C recompilation tool.
- `tools/script_editor.py`: Starts the translation editor at `http://127.0.0.1:5097/`.
- `tools/text_fit_check.py`: Checks text fit, for example:

```bash
python3 tools/text_fit_check.py --language eng
```

- `tools/build_site_patch.py`: Builds release patches after setting `VERSION`.

The intended distribution approach is to distribute a BPS/UPS patch rather than a copyrighted ROM.

---

## 4. Existing source modification: Blade Liger starter

The starter Zoid was changed in:

```text
src/game/player_state.h
```

Relevant definition:

```c
enum NewGamePlayerResources {
    NEW_GAME_PLAYER_STATE_RAM = 0x020218E4,
    NEW_GAME_PLAYER_CLEAR_CONTROL = 0x05001A82,
    NEW_GAME_STARTER_ZOID_MODEL = 0x17,
    NEW_GAME_STARTER_ZOID_SLOT = 1,
    NEW_GAME_STARTING_MONEY = 2000
};
```

The initialization code references this value:

```text
src/game/initialize_new_game_player_state.c
```

Specifically:

```c
AddPlayerZoidWithPilot(
    NEW_GAME_STARTER_ZOID_MODEL,
    0,
    PLAYER_PROTAGONIST_PILOT_ID
);
```

The user successfully built and tested the modified ROM.

**Important:** The starter change applies when starting a new game. Existing save files are not retroactively modified.

---

## 5. Event system architecture

The game already has a functioning event interpreter. The plan is to reuse it rather than create a new scripting engine.

Important source files:

```text
src/events/run_event_scripts.c
src/events/event_script.h
src/events/create_field_actor.c
src/events/update_field_actors.c
src/events/update_field_actor_commands.c
src/events/field_actor.h
src/events/begin_event_sprite_movement.c
src/events/run_event_sprite_movement_task.c
```

Relevant command handlers are under:

```text
src/events/commands/
```

Examples:

```text
event_spawn_actor.c
event_set_field_actor_behavior.c
event_queue_field_actor_command.c
event_wait_for_scene_actions.c
event_move_sprite.c
event_create_sprite.c
event_remove_actor.c
event_show_text.c
```

### Important distinction

There are two different movement systems:

1. **Field actors:** Normal map characters/NPCs controlled through actor commands.
2. **Event sprites:** Temporary sprites created and moved independently for scripted visual effects.

For ordinary story cutscenes, field actors are the primary system to use.

### Event interpreter behavior

- There are 70 event script slots.
- The interpreter reads opcodes and dispatches them through `gEventCommandHandlers`.
- `EVENT_CONTINUE` allows the interpreter to continue processing commands.
- `EVENT_YIELD` returns control to the task scheduler.
- `WAIT_FOR_SCENE_ACTIONS` waits for queued actor movement and event sprite actions to finish.

---

## 6. Field actor system findings

Actor definitions are in:

```text
src/events/field_actor.h
```

### Actor limits

```c
FIELD_ACTOR_COUNT = 14
FIELD_ACTOR_MAX_ID = 13
```

Actor IDs are therefore limited to 0–13.

### Actor behaviors

| Value | Behavior |
|---:|---|
| 0 | Player controlled |
| 1 | Wandering |
| 2 | Stationary |
| 3 | Turn only |
| 4 | Direction offset |
| 5 | Map interaction |
| 6 | Scripted camera follow |
| 7 | Scripted |
| 8 | Follower |
| 9 | Follower catch-up |
| 255 | No regular updates |

For scripted cutscene characters, behavior `7` is particularly relevant.

### Directions

| Value | Direction |
|---:|---|
| 0 | North |
| 1 | Northeast |
| 2 | East |
| 3 | Southeast |
| 4 | South |
| 5 | Southwest |
| 6 | West |
| 7 | Northwest |

### Movement commands

| Opcode | Meaning |
|---|---|
| `QUEUE_ACTOR_WAIT` | Wait while facing a direction |
| `QUEUE_ACTOR_MOVE_HALF_SPEED` | Move in a direction slowly |
| `QUEUE_ACTOR_MOVE_NORMAL_SPEED` | Move in a direction normally |
| `QUEUE_ACTOR_MOVE_DOUBLE_SPEED` | Move in a direction quickly |
| `QUEUE_ACTOR_MOVE_TO_HALF_SPEED` | Move to coordinates slowly |
| `QUEUE_ACTOR_MOVE_TO_NORMAL_SPEED` | Move to coordinates normally |
| `QUEUE_ACTOR_MOVE_TO_DOUBLE_SPEED` | Move to coordinates quickly |
| `QUEUE_ACTOR_HOP` | Hop |
| `QUEUE_ACTOR_SPECIAL_ANIMATION` | Play a model-specific animation |

### Known movement argument formats

Directional movement:

```text
[actor_id, direction, duration]
```

For example:

```text
QUEUE_ACTOR_MOVE_DOUBLE_SPEED [1, 4, 8]
```

means actor 1 moves south at double speed for a duration of 8.

The movement timer scales with speed:

- Half speed: duration × 16 ticks.
- Normal speed: duration × 8 ticks.
- Double speed: duration × 4 ticks.

Movement-to-coordinate commands use:

```text
[actor_id, destination_x, destination_y]
```

There is a coordinate scaling detail: the event handler doubles the destination arguments for packed map cells, while the movement updater converts coordinates using 8-pixel units. The resulting destination can therefore correspond to 16-pixel map cells.

Do not assume coordinates are interchangeable between maps until the map's coordinate mode is confirmed.

### Spawning actors

The `SPAWN_ACTOR` command has this argument format:

```text
[actor_id, model_id, x, y, direction, behavior, interaction_flag_id]
```

The handler calls:

```c
CreateFieldActor(
    model_id,
    actor_id,
    world_x_fixed8,
    world_y_fixed8,
    direction,
    0,
    behavior,
    interaction_flag_id
);
```

Spawn coordinates are scaled according to the map mode.

### Synchronizing movement

Use:

```text
WAIT_FOR_SCENE_ACTIONS
```

after queuing movement when the following dialogue or action must wait for the character to finish moving.

---

## 7. Event extraction: successful result

The extractor initially failed in the main repository because its pinned source hashes did not match that checkout.

Several historical revisions were investigated. The working combination was:

- Historical source snapshot: `b9d133c`
- Extractor source copied from the original `ZoidsLegacyExtract` checkout.
- Extractor compiled inside `ZoidsLegacyExtractMusic`.

The successful command was:

```bash
cargo run --release --manifest-path extract/Cargo.toml -- run \
  --rom "../ZoidsLegacyDecomp/Zoids Legacy (USA).gba" \
  --out /tmp/zoids-event-extract
```

The extractor completed successfully.

Important output statistics:

```text
rom bytes           8388608
code bytes          372206
data bytes          8016402
known data bytes    7765670
known data          96.87%
items               17686
unported roots      0
dangling pointers   0
```

Useful extracted files:

```text
/tmp/zoids-event-extract/data/event_script.json
/tmp/zoids-event-extract/data/table.map_event_scripts.json
```

The event extraction contains:

- 1,067 event script items.
- 784 map event script table entries.
- 45,004 known bytes of event script data.
- 1,440 text string items.
- Event command handler and command length tables.

**Important:** The decoded commands are nested under:

```python
script["data"]["commands"]
```

They are not at the top-level `script["commands"]`.

The extracted JSON is currently being used as a reference for understanding original scripts. It is not yet an established editable script-insertion workflow.

---

## 8. Real event script example discovered

A useful extracted script is:

```text
0x0803103C
```

It demonstrates actor spawning, directional movement, waiting, dialogue, and actor removal.

Example sequence:

```text
SPAWN_ACTOR [1, 142, 99, 145, 0, 7, 0]
QUEUE_ACTOR_MOVE_DOUBLE_SPEED [1, 0, 8]
WAIT_FOR_SCENE_ACTIONS
```

This creates actor 1 using model 142, then moves the actor north at double speed.

Another sequence:

```text
SPAWN_ACTOR [2, 126, 99, 139, 4, 7, 0]
QUEUE_ACTOR_MOVE_DOUBLE_SPEED [1, 4, 4]
WAIT_FOR_SCENE_ACTIONS
```

Later:

```text
QUEUE_ACTOR_MOVE_DOUBLE_SPEED [1, 4, 12]
WAIT_FOR_SCENE_ACTIONS
REMOVE_ACTOR [1]
```

This demonstrates a character walking away and disappearing.

The script also shows that dialogue, battle transitions, actor commands, and scene changes can be combined in one event script.

This is a strong reference for constructing new story scenes.

---

## 9. Current bugs and unresolved issues

### Resolved

- Full decompilation verification: all 1,130 regions passed.
- Starter Zoid modification: built and tested successfully.
- GitHub fork authentication: fixed using a personal access token.
- Event extractor source revision mismatch: resolved by using the `b9d133c` worktree.
- Event extraction: completed successfully with zero unported roots and zero dangling pointers.

### No confirmed active build blocker

There is currently no confirmed outstanding build or verification failure.

### Remaining technical unknowns

1. Exact argument semantics for `QUEUE_ACTOR_SPECIAL_ANIMATION`.
2. Exact coordinate behavior across different map types.
3. How to associate actor model IDs with visible character sprites and animations.
4. How to edit, insert, and register newly created event scripts.
5. How map event script pointers and triggers connect to specific maps and interactions.
6. How to add new locations or reuse existing maps safely.
7. Whether all necessary actor models and animation sets can be reused for the new characters.

The historical extractor worktrees are separate from the main development checkout. Avoid assuming that a source change in one worktree is automatically present in another.

---

## 10. Recommended next steps

### Phase 1 — Finish understanding actor commands

Inspect:

```text
src/events/commands/event_queue_field_actor_command.c
src/events/update_field_actor_commands.c
```

Specifically investigate:

- The remainder of special-animation handling.
- The meaning of both arguments for `QUEUE_ACTOR_SPECIAL_ANIMATION`.
- The exact behavior of `QUEUE_ACTOR_WAIT`.
- Coordinate movement and map scaling.

### Phase 2 — Identify actor models

Determine:

- Which model IDs correspond to existing human characters.
- Which IDs correspond to NPCs and enemy characters.
- Which models have special animations.
- How actor graphics are loaded and associated with models.

Use extracted scripts as evidence rather than guessing IDs.

### Phase 3 — Understand map events

Investigate:

```text
src/events/start_map_event_script.c
src/events/run_event_scripts.c
src/events/event_script.h
```

Use:

```text
/tmp/zoids-event-extract/data/table.map_event_scripts.json
/tmp/zoids-event-extract/data/event_script.json
```

Trace how map interactions and triggers lead to specific event script addresses.

### Phase 4 — Build a small test cutscene

Before writing the full story, create a small experimental scene using existing assets:

1. Spawn an existing character.
2. Move the character toward the protagonist.
3. Wait for movement.
4. Display dialogue.
5. Turn the character toward another actor.
6. Play an animation.
7. Move the character away.
8. Remove the actor.

Test the scene in an emulator before expanding it.

### Phase 5 — Implement Chapter 1

Reuse original locations, character sprites, battle systems, and enemy Zoids where possible.

Implement the abandoned research facility scene and the first Obsidian Order encounter before attempting entirely new maps or graphics.

### Phase 6 — Custom Zoids

After the story and event pipeline are working, investigate:

- Zoid model IDs and data tables.
- Battle sprites and animations.
- Palettes and graphics.
- Weapons and abilities.
- Menu references and compatibility tables.
- Save data and Zoid ownership references.

---

## 11. Working conventions for continued development

- Work in the main `ZoidsLegacyDecomp` repository unless a historical extractor task specifically requires another worktree.
- Check `git status` before and after source changes.
- Preserve the verified baseline.
- Build and verify incrementally.
- Test changes in an emulator, preferably starting a new game when testing starter-Zoid changes.
- Inspect existing code and extracted scripts before inventing command formats.
- Keep the original ROM untouched.
- Prefer reusing existing game assets and systems before creating new ones.
- Make changes locally; do not assume an assistant or external tool should directly edit the repository.

**Immediate priority:** Finish documenting the event command formats, then create one small working cutscene. That will establish the technical foundation for implementing the new story.