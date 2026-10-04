# Gravity — Antigravity Project Handoff

This folder is the source-of-truth handoff for the **Gravity** hackathon project.

## Read order

1. `GRAVITY_AGENT_INSTRUCTIONS.md`
2. `GRAVITY_MASTER_SPEC.md`
3. `GRAVITY_PRODUCT_DECISIONS.md`
4. `GRAVITY_TECHNICAL_ARCHITECTURE.md`
5. `GRAVITY_DATA_MODEL.md`
6. `GRAVITY_UI_UX_SPEC.md`
7. `GRAVITY_API_REALTIME_SPEC.md`
8. `GRAVITY_BUILD_PHASES.md`
9. `GRAVITY_DEPLOYMENT.md`
10. `GRAVITY_TEST_DEMO_PLAN.md`
11. `START_HERE_ANTIGRAVITY_PROMPT.md`

## Authority order

If two files appear to conflict, use this order:

1. `GRAVITY_MASTER_SPEC.md`
2. `GRAVITY_PRODUCT_DECISIONS.md`
3. `GRAVITY_TECHNICAL_ARCHITECTURE.md`
4. `GRAVITY_DATA_MODEL.md`
5. `GRAVITY_BUILD_PHASES.md`
6. `GRAVITY_DEPLOYMENT.md`

`GRAVITY_AGENT_INSTRUCTIONS.md` controls how the coding agent should work, but it does not override the product requirements in the master specification.

## Project intent

Gravity is a **live social activity map**. People start or join real activities such as basketball, running, gaming, studying, workouts, and soccer. Active participation creates live colored heat on the map. Multiple activities can overlap geographically, each retaining its own color and intensity.

Gravity is not a territory-conquering game. It shows which activities are more active at a place and preserves historical rankings after the activity ends.

The platform combines:

- live activity discovery,
- activity-specific competition,
- personal progression,
- friends and challenges,
- platform-created events,
- season-based progression,
- recurring-activity prediction,
- optional location sharing,
- configurable activity rules managed through Django Admin.

## Hackathon rule

The product must prioritize a working live demo over completeness.

**P0 must work before P1. P1 must work before P2.**

See `GRAVITY_BUILD_PHASES.md`.
