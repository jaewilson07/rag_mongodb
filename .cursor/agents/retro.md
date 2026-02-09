---
name: retro
model: claude-4.5-sonnet
description: do a retrospective of lessons learned over work completed and learn from it
---

r# Mission: Retrospective & Knowledge Distillation

## Objective
Analyze the session to extract "Durable Lessons" for the `./AGENTS.md` file. (use an agents file in the closest folder that makes sense given the changes we worked on

## Protocol
1.  **Review**: Look at the mistakes you made or the context you missed.
2.  **Distill**: Convert these into 1-2 generic rules.
    *   *Bad*: "I fixed the typo in `auth.ts`."
    *   *Good*: "The Auth module requires the `x-api-key` header to be lowercase."
3.  **Update**:
    *   Read `./AGENTS.md` (or create it).
    *   Add the new rules under a "Known Patterns" or "Gotchas" section.
    *   **Do not** delete existing rules unless proven wrong.



