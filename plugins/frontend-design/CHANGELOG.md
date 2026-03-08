## [1.1.0] - 2026-03-08

### Changed
- Light and dark themes are now both first-class citizens with complete token sets
- Color palette uses `prefers-color-scheme` media query and `data-theme` attribute for system/manual switching
- Tailwind config uses CSS variable references instead of hardcoded hex values for automatic theme support
- Updated anti-patterns table, implementation checklist, and rules to reflect dual-theme approach
- Removed "dark by default" language in favor of "respect system preference"

## [1.0.0] - 2026-03-08

### Added
- Initial release of opinionated frontend design skill
- Complete design token system (colors, typography, spacing, layout) derived from 5 curated reference sites
- Component patterns: sidebar nav, cards, lists/feeds, buttons, forms, tables, command palette
- Anti-pattern table contrasting "LLM-default" choices with correct alternatives
- Tailwind CSS configuration matching the design system
- Animation guidelines (minimal, purposeful motion)
- Implementation checklist for pre-ship verification
- Light theme override tokens for editorial/reading contexts
