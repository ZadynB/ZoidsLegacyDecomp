# Zoids Legacy ROM Hack — Progress Log

**Updated:** 2026-11-22  
**Working branch:** `codex/zoids-legacy-progress`  
**Base:** `main` at `8428637` (`verified-baseline`)

## Current state

- The verified `main` branch has not been modified. This work is on `codex/zoids-legacy-progress`.
- The user confirmed that the Bit Cloud test scene works on the initial Cebu Town entrance, Bit can be talked to repeatedly, and gating the test scene to Cebu's original prologue flag resolved the later re-entry black screen.
- The latest reproducible ROM is `build/ZoidsLegacy-CebuTown-Bit-prologue-only.gba`. ROMs under `build/` are ignored by Git and are local test artifacts.
- The original ROM remains the clean input: `Zoids Legacy (USA).gba`.
- No release ROM or patch has been produced. The experiment builder is a disposable ROM tool, not a project-integrated event-script pipeline.

## Change history

### Existing project work

- The repository's verified baseline is commit `8428637`, tagged `verified-baseline`.
- The new-game starter Zoid was changed to Blade Liger in `src/game/player_state.h`; the handoff notes that the user built and tested this change.
- Event command and map actor behavior research was recorded in `EVENT_COMMAND_NOTES.md`.

### Cebu Town Bit Cloud test scene

- Added `tools/build_test_cutscene_rom.py`. It takes a clean 8 MiB USA ROM, expands a separate output to 16 MiB, wraps one map's event pointer, and leaves its input untouched.
- Targeted map 4, Cebu Town, which is reached during the prologue and avoids needing an existing save.
- Identified Bit's field actor model as **30** from the existing prologue scene at `0x08073C4F`. Model 106 was incorrect; model 142 was an earlier movement test.
- The test actor uses field actor ID 7 at `(52, 59)`. It spawns with scripted behavior 7 so queued movement runs, then a local frame wait is followed by behavior 2 so the actor can be interacted with.
- The talk listener starts at its own script entry with `IF_INTERACTED_ACTOR`, displays “Hello there!”, and runs `RESTART` so the player can talk again. Keeping the interaction check at the listener's start avoids re-running spawn and movement commands on each unsuccessful poll.
- The test scene is gated by Cebu's original event flag 1. It runs on the prologue visit only; later Cebu visits use the game's original map startup flow. The listener is started only by that gated scene.
- The builder preserves the GBA fixed header byte at `0xB2` and updates the header complement checksum after writing the map pointer.

### Issues found and resolved during emulator feedback

1. An early movement test used the wrong large actor model and initially corrupted the map transition. Running movement asynchronously without a blocking scene wait restored the normal transition.
2. Model 106 was not Bit. Model 30 is the character shown in the current test build.
3. Making Bit stationary before movement prevented the actor-command updater from processing his queued walk and left him blocking the entrance. The build now keeps him scripted during movement and switches him to stationary afterward.
4. Placing `IF_INTERACTED_ACTOR` after the spawn commands caused failed interaction checks to restart the whole script and repeat actor commands. The listener was split into its own script.
5. A one-shot listener locked the player on a second interaction. `RESTART` now clears the interaction lock and re-arms the listener.
6. Waiting for all scene actions could be affected by unrelated actor, camera, or event-sprite work. The entrance uses a local frame timer instead.
7. Running the test scene on every Cebu visit conflicted with later story progression. Gating it on the original prologue flag fixed re-entry in the user's latest test.

## Where work left off

The latest user feedback was positive: the flag-gated build appeared to resolve the Cebu re-entry issue. No new defect is currently awaiting a code change. The next sensible step is to continue the main story-hack work from the project handoff, while retaining the test builder and notes on this branch for future event experiments.

## Branch and worktree notes

- The new branch was created from `main` at `8428637`.
- The current working tree contains the event notes, ROM builder, this log, and the pre-existing untracked `Zoids Legacy ROM Hack — Project Handoff.md`.
- The handoff document was left unchanged. Keep it alongside this log as project context.
- The test ROM in `build/` is ignored by `.gitignore`; rebuild it from the clean ROM when needed:

```bash
python3 tools/build_test_cutscene_rom.py \
  --rom "Zoids Legacy (USA).gba" \
  --out build/ZoidsLegacy-CebuTown-Bit-prologue-only.gba
```

- Before merging anything back, review the branch diff and verify the intended source/document files. The baseline `main` remains at its original commit until an explicit merge or cherry-pick.
