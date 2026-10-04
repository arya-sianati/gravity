# Copy-Paste This Into Antigravity First

You are taking over implementation of a new hackathon project named **Gravity**.

This is a fresh project. Do not import assumptions, architecture, code, or product ideas from unrelated repositories or prior projects.

Before writing or modifying code, read these files completely in this order:

1. `README.md`
2. `GRAVITY_AGENT_INSTRUCTIONS.md`
3. `GRAVITY_MASTER_SPEC.md`
4. `GRAVITY_PRODUCT_DECISIONS.md`
5. `GRAVITY_TECHNICAL_ARCHITECTURE.md`
6. `GRAVITY_DATA_MODEL.md`
7. `GRAVITY_UI_UX_SPEC.md`
8. `GRAVITY_API_REALTIME_SPEC.md`
9. `GRAVITY_BUILD_PHASES.md`
10. `GRAVITY_DEPLOYMENT.md`
11. `GRAVITY_TEST_DEMO_PLAN.md`
12. `IMPLEMENTATION_STATUS.md`

Then do the following:

1. Audit the specifications for internal contradictions, missing implementation-critical decisions, security/privacy concerns, or unrealistic assumptions.
2. Do **not** redesign the product merely because you prefer a different stack or product direction.
3. Verify current stable compatible versions of Python, Django, Django REST Framework, Django Channels, PostgreSQL/PostGIS, Redis, Node, Vite, React, Tailwind, and MapLibre before installing dependencies.
4. Produce a short implementation audit containing:
   - confirmed architecture,
   - any contradictions found,
   - any required corrections,
   - dependency/version choices,
   - exact Phase 00/01 plan.
5. If there is no blocking contradiction, initialize the repository and begin the phases in `GRAVITY_BUILD_PHASES.md`.
6. Treat P0 as mandatory. Never work on P2 while P0 is incomplete.
7. Keep `IMPLEMENTATION_STATUS.md` updated after every completed phase.
8. Run tests/build checks after each phase.
9. Preserve the product's key requirements:
   - live activity map,
   - dynamic heatmap,
   - overlapping activity types without territory conquest,
   - platform-defined configurable Activity Types,
   - Django Admin configuration,
   - self-reporting allowed,
   - QR join,
   - activity-specific metrics and leaderboards,
   - personal Gravity XP,
   - Gravity Events,
   - seasons,
   - privacy controls,
   - Pulse,
   - friends/challenges after core functionality.
10. If you find a specification issue, document the proposed change before implementing it.

Start by giving me the audit. Do not write application code until the audit is complete.
