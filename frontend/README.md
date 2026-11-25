# Frontend (Angular)

Web interface for the Literature Review Cockpit.

## Stack

- **Angular:** `22.2.x` (`@angular/core ^22.2.0`, `@angular/cli ^22.2.5`)
- **UI Library:** Angular Material `22.2.7` (Material 3 `azure-blue` theme)
- **Testing:** Vitest `^5.0.0` (`ng test`)
- **Best Practices & Agent Guidance:** Follow the `angular-developer` skill (`.agents/skills/angular-developer/SKILL.md`) and [frontend/AGENTS.md](AGENTS.md).

## Commands

Run from `frontend/` (or use `make frontend` / `make dev` from the repo root):

```bash
npm start     # Start dev server at http://localhost:4200
npm run build # Production build into dist/frontend
npm test      # Run Vitest unit tests
```
