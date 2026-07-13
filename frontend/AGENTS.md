<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# Rules

- **context7**: before using any library API (Tiptap, TanStack Query, shadcn, Supabase JS), fetch current docs via the context7 MCP instead of relying on memorized knowledge — installed versions (Next 16, React 19, Tiptap 3) are newer than model training data. For Next.js, prefer the vendored docs above.
- **ponytail**: all frontend code follows the ponytail discipline — simplest working solution, native/stdlib before new dependencies, no speculative abstractions (Constitution Principle V, YAGNI). Run `/ponytail-review` on diffs before merge.
- **Styling**: Tailwind 4 + shadcn/ui (see `components.json`). Add components via the shadcn MCP; don't hand-roll what the registry provides. Dark mode is class-based (`.dark`).

## Design workflow

Every new or reworked screen goes through this pipeline, in order:

1. **`ui-ux-pro-max`** generates the visual foundation from `frontend/design-system/MASTER.md` (palette, typography, tokens, base components, global nav). Design choices (palette, typography, light/dark strategy, which shadcn primitives fit a given screen) are decided freely by the skill from its own analysis of the project — do not hardcode or second-guess a specific font/color/component list here.
2. **Playwright MCP** renders the result and captures screenshots at 360px and desktop width, so misalignment or overflow is caught before handoff.
3. **`impeccable`** audits and art-directs the render (`/impeccable audit` for WCAG AA contrast/hierarchy, `/impeccable polish` for finishing, `/impeccable animate` for micro-interactions within the FR-054 500ms budget). Use **Product** mode (not Brand) — every MVP screen is an authenticated tool, not marketing content. Its automatic hook findings on frontend edits must be handled, not ignored.

Optional: `npx impeccable detect` can gate CI alongside eslint once the design system stabilizes.
