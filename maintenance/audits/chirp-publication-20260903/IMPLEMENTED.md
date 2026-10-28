# Chirp future publication fix — 2026-09-03

Installed on `https://fvtt.univare.icu`, world `taiyi`, Smartphone Chirp App 1.1.1. Browser verification used the authorized AssistantAgent session. The Foundry process was not restarted; existing clients must refresh.

## Observed defect and result

The live application loaded all posts into every view without checking `timestamp`, `publishTimestamp`, or `isHidden`. At Smartphone time `1904509738000` ms, 68 of the world's 113 posts were dated in the future. Expanding the original timeline to 1,000 entries rendered 100 cards, including 60 future cards.

After the fix, the cache still contains all 113 posts. The common view map contains 45 eligible posts. The expanded timeline renders 40 cards and **zero future cards**; replies and rechirps explain why card counts differ from post counts.

The raw posts SHA-256 before and after is `5de5989dc6f7e677d9932bee26a33232dc141a64407262a5e55d1abca273449f`. World time remained `1904509738` seconds. No posts, dates, accounts, game time, or world settings were edited for verification.

## Implementation

- `apps/chirp/chirp-publication.js`: shared eligibility projection using the clock selected in Smartphone. Both publication dates must be due; the boundary is inclusive. Undated/invalid posts and hidden unscheduled drafts remain hidden. Replies to unpublished ancestors stay hidden too.
- `apps/ChirpApp.js`: retain a complete cache, expose eligible posts to all existing view renderers, filter socket updates and setting reloads, and refresh on Smartphone/world time hooks plus a one-second fallback timer. Hiding/cleaning the app releases hooks and timers. Existing protection for unfinished compose/edit fields is preserved.
- `socket/gmHandlers.js`: native schedule calls now validate and align the publication date, and broadcast immediately. Manual publish clears the schedule and brings future dates forward to now. These handlers were tested in isolation; no real post was scheduled or published during this work.

This controls ordinary Chirp display, including GM timelines. It does not add a GM draft editor or change notification delivery. The original world setting still stores all posts. Existing notification badges and manual trend metadata are outside this patch.

## Verification

- Syntax checks for all three deployed JavaScript files passed.
- `node --experimental-vm-modules scripts/fvtt/chirp-publication-20260903/test.cjs` passed. Tests load the actual patched application, socket callback, GM handlers, and original view renderers with isolated Foundry/clock adapters.
- Covered both timelines, four profile tabs, search, detail, bookmarks, trend tabs, quote fallback, nested replies, invalid dates, native schedules, the exact release boundary, time rewind, future realtime updates/rescheduling, setting reloads, compose preservation, and watcher cleanup. Original source fixture data remained unchanged.
- Server version and source SHA-256 guards matched before installation. Original files were backed up and verified. The three deployed files were verified both on disk and through public HTTPS responses against `deployment.json`.
- Fresh live browser load confirmed the patched method, complete raw cache, active hooks, eligible map, zero future DOM cards, unchanged posts hash, and unchanged world time. `chirp-fixed.png` records the actual rendered timeline. The browser's unrelated initial module changelog and small-viewport warnings remain visible behind the phone.
- Automatic release and rewind were exercised with an isolated clock, not by changing the running campaign clock.

## Files and recovery

Local patch, reproducible builder, tests, and exact hashes: `scripts/fvtt/chirp-publication-20260903/`.

Fresh original module sources, before/after runtime evidence, screenshot, and test results: this directory.

Server backup: `C:\foundryvtt\Backups\taiyi-chirp-publication-20260903\original\`.

To roll back, restore `apps\ChirpApp.js` and `socket\gmHandlers.js` from that backup to `C:\foundryvtt\Data\modules\smartphone-chirp-app\`, then refresh clients. The new helper becomes unused after restoration. `module/package.json` is only for local syntax checks and was not deployed. A future upstream module update may overwrite this local patch; recheck behavior/version before reapplying.
