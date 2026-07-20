# Issue tracker: Local Markdown

Issues live as markdown files in `.scratch/`.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`
- The map is `.scratch/<effort>/map.md`
- Child tickets: `.scratch/<effort>/issues/NN-<slug>.md`, numbered from `01`
- `Status:` line: `claimed` / `resolved`
- `Type:` line: `research` / `prototype` / `grilling` / `task`
- `Blocked by: NN, NN` line near the top
- Frontier: open, unblocked, unclaimed files in `issues/`
- Claim: set `Status: claimed` and save
- Resolve: append answer under `## Answer`, set `Status: resolved`, update map Decisions-so-far
