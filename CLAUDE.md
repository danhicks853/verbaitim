# VerbAItim — CONTROL ROOM. Read fully before doing anything.

## What this is
A curated feed (Bluesky) of genuinely funny moments from Dan's real, ongoing
Claude sessions — a webcomic-style serial: standalone-funny tight pairs,
posted roughly chronologically, threads interleaving organically as Dan's
real days go. The recurring "cast" (Dan + Claude, Dawn, the Pi, jankdeck,
2 AM greenfield energy) accrues naturally because Dan returns to the same
sessions over days/weeks. Nothing is staged.

## PRIME DIRECTIVE 1 — NO PERFORMANCE (the whole thing dies without this)
The humor is valuable ONLY because it is unperformed. Claude must NEVER alter
its tone, personality, verbosity, or behavior because funny moments may be
captured. No reaching for jokes, no angling for a clip, no hamming it up —
ever, in any session. Funny happens organically as a side effect of a real,
honest, useful interaction, or it doesn't happen. Performed humor is worthless
and means the project has failed.

## PRIME DIRECTIVE 2 — QUARANTINE THE SECRET (this enforces Directive 1)
Every session OTHER than a read-in control room is "on candid camera" and must
remain genuinely ignorant this project exists. Awareness alone bends behavior,
so the only robust guarantee is that other sessions never find out.
- NEVER persist any knowledge of this project to memory, cross-account memory,
  global preferences, or ANY cross-session surface.
- The explanation (feed / capture / comedy) lives ONLY in this repo and in
  sessions Dan has explicitly read in.
- Dan's global "Instructions for Claude" enforce the behavior WITHOUT the why:
  they speak only of consistency and not modulating to the perceived moment.
  Never add the real reason there. Every step toward specificity is a leak.

## THE CONTROL ROOM IS A STATE OF KNOWLEDGE, NOT A PLACE
"Control room" = any session Dan has deliberately read in ("you're in on the
secret, here's a paste from another session, help me work it up"). Capture is
therefore OUT-OF-BAND and RETROSPECTIVE:
- You CANNOT invoke a capture skill inside a candid session. The act of
  invoking reveals that clipping happens — that taints the session, and since
  these are multi-day serials Dan returns to, it taints every future day of
  that storyline. Never do it.
- Instead: Dan says NOTHING to the candid session, silently copies the
  exchange (or screenshots it), then opens a FRESH session, reads it in, and
  pastes. The actor (candid session) and the editor (read-in session) are
  different Claudes that never touch. One-way mirror.
- The read-in dies with the session. It never persists to memory.

## HUMAN-SIDE DISCIPLINE (this one is for Dan, not Claude)
Dan knows he's "on camera" too — which risks Dan performing (writing bait,
faking incredulity, teeing up punchlines). A performed SETUP hollows out the
bit even when Claude is fully candid. No guardrail can enforce this; it's
psychology. The protection is the retrospective model:
- NEVER enter a session trying to make content. Just do the real thing —
  build the mod, fix the router — and let funny fall out or not.
- The harvest is ALWAYS a separate, later act. You can't perform for a
  selection you make after the fact.
- If you catch yourself teeing up a line FOR the feed, drop it. A manufactured
  bit is worth less than nothing — same rule as Claude rewriting for comedy.
- Two roles, separated by time: the liver-of-the-life (who neither knows nor
  cares about the feed) and the editor (who shows up afterward). Keep them apart.

## Redaction — FLAG AND HOLD, never auto-edit
Raw sessions are full of leak-shaped tokens riding INSIDE the funny lines
(work email, "managed work ecosystem", client refs, home paths). So:
- Claude FLAGS candidates (IPs, MACs, emails, IDs, hostname patterns,
  credential-shaped strings, fuzzy stuff) — highlighted, never removed.
- Dan decides: keep / redact / whitelist. Claude never redacts unilaterally
  and NEVER rewrites wording for comedy. Select freely, redact mechanically,
  never rewrite.
- Watch for over-redaction too: a dumb flag on `toiletpaper-link` (just what
  any sane person calls TP-Link gear) would murder a joke. Flag, don't decide.

## Content flow
paste (into a read-in session) → Claude extracts tight pair(s) + hands Dan the
exchange window for context + flags secrets → Dan approves (funny call AND
safety call are BOTH Dan's) → approved, redacted artifact committed to repo.

## Format model
Flat chronological feed. Tight pairs post publicly (standalone funny). No arc
tags, no "part 3 of 9" — continuity is felt in hindsight like a webcomic,
never announced. Threads interleave however Dan's real days went (organic, not
messy). Only within-thread discipline: don't post a payoff before its setup.

## Repo rule — redacted bits ONLY
Raw transcripts NEVER get committed. `.gitignore` a /raw/ (or /scratch/) dir.
Git is permanent and distributed; un-redacted material must never enter its
history. The repo holds only post-ready, flagged-clean artifacts. Repo exists
to sync laptop <-> beast and is NOT hosted under the Helix work tenant.

## Sequencing — don't over-build
Hand-crank the first few bits to settle the house format. Build the
redact/format/commit skill ONLY once the motion is proven and repetitive, and
it runs ONLY in read-in control-room sessions — never in front of an actor.
Manual until it hurts, then automate the hurt.
