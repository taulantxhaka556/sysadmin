# Groups and learning oversight

**Goal:** Let teachers create groups, inspect their students' learning and reach work requiring review.
**Architecture:** Server-rendered FastAPI pages backed by existing Group/User/Work and learning progress tables. No schema migration. A dedicated admin_dashboard module owns group pages and summary calculations.
**Tech stack:** Existing Python, SQLAlchemy, HTML/CSS.
**Design:** /admin shows group cards and creation; /admin/groups/{id} shows summaries, searchable roster, 14-module matrix and review queue. Links open existing individual journals. Teachers may rename groups and move a student to another existing group without changing progress. No destructive actions. Empty groups explain registration. Completion means lab + best test >=70; theory means all checks in a lesson solved. No inferred last-activity dates. All teacher endpoints enforce role and CSRF for mutations.

- [x] Tests: create/duplicate/rename groups; empty states; mixed module progress including legacy first-module table; pending/revision/zero scores; group isolation, membership transfer, auth/CSRF.
- [x] Implement admin_dashboard.py and replace existing /admin, /admin/group handler bodies. Add group routes after learning is imported.
- [x] Add responsive admin CSS and navigation, preserve material editor and journal access.
- [ ] Run full tests, review diff and publish to existing sysadmin main with expected SHA; await Vercel status.

Review focus: no demo progress in reports; no averaging missing grades as zero; group metrics unaffected by roster filters; transfer preserves work and progress; case-insensitive duplicate group names and bounded input.

Validation: 20 tests passed, Python compile checks passed; independent review found no blockers. Browser visual verification was not performed.
