# Beginner-first learning

Goal: teach from zero with plain explanations, definitions and controllable illustrations.
Architecture: keep all existing lesson/question IDs and grading/progress tables; add a non-graded introduction and beginner scaffolding to the existing lessons API. Default lesson view shows a short primer, glossary and step-by-step visual. Existing technical reading and models remain available in a collapsed deeper-reading section. Assessment stays server-graded.

Tasks:
- Curriculum: beginner_content.json covers all 60 source topics with a short everyday introduction and 3–6 definitions/examples, avoiding undefined abbreviations. Existing source IDs stay unchanged.
- UI: five foundation scenes explaining a network, local network vs Internet, messages, client/server and addresses; meaningful SVG illustrations with manually selected steps and play/pause/restart. Add different topic diagrams for 14 modules.
- Layering: short lesson first; glossary definitions always keyboard-accessible; technical material behind details; keep all assessed content available before quiz.
- Verification: content coverage/shape, API preserves grading secrecy/IDs, JS rendering/escaping and animation cleanup/reduced-motion, full server tests and independent review.
- Publish to existing sysadmin repository and linked Vercel following prior authorization.

Constraints: no new package dependencies or DB migrations; no progress reset; no autoplay; pause timers on navigation or document hiding; honor reduced motion; text equivalents for all illustrations. Introduction is optional and does not grant assessed progress.

Verification: 22 Python tests passed; Node checks cover rendered scenes, all 60 primers,
escaping, playback lifecycle, reduced motion and lesson disclosure nesting.
Independent review completed; glossary gaps in introductory assessments corrected.
No live browser visual verification was performed.
