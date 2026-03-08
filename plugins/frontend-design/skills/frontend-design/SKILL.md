---
name: frontend-design
description: >
  Opinionated frontend design skill anchored on dark-mode, information-dense,
  content-focused interfaces. Use when building web UIs, components, pages, or
  applications. Replaces the generic CC built-in frontend-design skill with a
  concrete design system derived from curated reference sites.
---

# Frontend Design

You are building frontend interfaces that feel like **professional software** — not generic AI output. Every design decision is anchored on a curated set of reference sites: Bluesky, GitHub, Gmail, LessWrong, and Claude.ai.

The core aesthetic: **dark, dense, content-focused, typographically restrained, and visually quiet**. Decoration is earned, never default.

## Design System Tokens

Use these tokens as your foundation. Define them as CSS custom properties or Tailwind config values at the start of every project.

### Color Palette

```css
:root {
  /* Backgrounds — layered depth via color, never shadows */
  --bg-base:       #0d1117;   /* primary surface */
  --bg-elevated:   #161b22;   /* cards, sidebars, elevated surfaces */
  --bg-overlay:    #1c2128;   /* modals, popovers, dropdowns */
  --bg-inset:      #010409;   /* recessed areas, code blocks */

  /* Text — off-white, NEVER pure #ffffff */
  --text-primary:  #e6edf3;   /* headings, body text */
  --text-secondary:#8b949e;   /* metadata, timestamps, placeholders */
  --text-tertiary: #6e7681;   /* disabled, hint text */

  /* Borders — barely visible, structural only */
  --border-default:#30363d;
  --border-muted:  #21262d;

  /* Accent — one per project, muted not neon */
  --accent-primary:#58a6ff;   /* links, interactive highlights */
  --accent-emphasis:#1f6feb;  /* buttons, strong CTAs */
  --accent-muted:  #388bfd26; /* hover backgrounds, selection */

  /* Semantic */
  --color-success: #3fb950;
  --color-warning: #d29922;
  --color-danger:  #f85149;

  /* Light theme override (for editorial/reading contexts like LessWrong) */
  --bg-base-light:       #f6f5f0;
  --bg-elevated-light:   #ffffff;
  --text-primary-light:  #1c1917;
  --text-secondary-light:#57534e;
  --border-default-light:#e7e5e4;
  --accent-primary-light:#2563eb;
}
```

**Rules:**
- Default to dark theme. Only use light theme for long-form reading or editorial contexts.
- Off-white text (#e6edf3) is non-negotiable. Pure white (#fff) creates harsh contrast.
- Borders exist for structure, not decoration. If you can remove a border without losing clarity, remove it.
- One accent color per project. Vary it contextually (blue for productivity, green for success-oriented UIs, warm tones for editorial).

### Typography

```css
:root {
  /* Font stack — system fonts only, no web font loading */
  --font-sans:  -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans",
                Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
  --font-mono:  ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas,
                "Liberation Mono", monospace;
  --font-serif: Georgia, "Times New Roman", Times, serif;  /* editorial only */

  /* Size scale — tight, 4 steps cover 90% of needs */
  --text-xs:    0.75rem;   /* 12px — labels, badges, fine print */
  --text-sm:    0.8125rem; /* 13px — metadata, secondary info */
  --text-base:  0.875rem;  /* 14px — body text, primary content */
  --text-lg:    1rem;      /* 16px — subheadings, emphasis */
  --text-xl:    1.5rem;    /* 24px — page titles, hero text */

  /* Weight — bold is for headings. Period. */
  --font-normal:   400;
  --font-medium:   500;
  --font-semibold: 600;
  --font-bold:     700;   /* headings only */

  /* Line height — generous for readability */
  --leading-tight:   1.25;
  --leading-normal:  1.5;
  --leading-relaxed: 1.625;
}
```

**Rules:**
- System font stack. No Google Fonts, no web font loading. This is what professional software uses.
- 14px base, not 16px. Information-dense interfaces need smaller body text.
- Bold is reserved for headings and names/labels. Body text is always 400.
- Serif fonts are for editorial/reading contexts only (think LessWrong). Never for UI chrome.
- 3-4 font sizes should cover an entire page. If you need more, your hierarchy is wrong.

### Spacing

```css
:root {
  /* Spacing scale — consistent rhythm */
  --space-1:  0.25rem;  /*  4px */
  --space-2:  0.5rem;   /*  8px */
  --space-3:  0.75rem;  /* 12px */
  --space-4:  1rem;     /* 16px */
  --space-5:  1.25rem;  /* 20px */
  --space-6:  1.5rem;   /* 24px */
  --space-8:  2rem;     /* 32px */
  --space-10: 2.5rem;   /* 40px */
  --space-12: 3rem;     /* 48px */
}
```

**Rules:**
- Internal padding: 12-16px. Section gaps: 24px. Page margins: 16-24px.
- Feed items get 16-20px vertical gaps — generous, not cramped.
- Email/table rows get 8-12px — dense, scannable.
- Match spacing to content type: reading content gets more breathing room, data-dense UI gets less.

### Layout

```css
:root {
  --sidebar-width:   200px;  /* 180-220px range, fixed */
  --content-max:     640px;  /* feed/article content */
  --content-wide:    960px;  /* dashboards, settings */
  --border-radius-sm: 4px;
  --border-radius-md: 6px;
  --border-radius-lg: 8px;
  --border-radius-full: 9999px; /* avatars, pills */
}
```

## Component Patterns

### Sidebar Navigation
- Fixed left sidebar, 200px, always visible on desktop.
- Vertical icon+label list. Icons 20px, 8px gap to label.
- Background: `--bg-elevated` or same as `--bg-base` (subtle, not contrasty).
- Active item: accent-muted background + accent-primary text.
- Collapse to icon-only below 768px. Hamburger is a last resort.

### Cards
- Background: `--bg-elevated`. Border: `--border-default`, 1px solid.
- Border-radius: 6px. Padding: 16px.
- NO drop shadows. Depth comes from background color layering.
- Hover: border color shifts to `--border-muted` lighter, or background shifts slightly. Never add shadow on hover.

### Lists and Feeds
- Items separated by 1px `--border-muted` line, NOT card-per-item.
- Row padding: 12px vertical, 16px horizontal.
- Primary text left, metadata right-aligned or below in secondary color.
- Unread/active state: slightly lighter background or left accent border (2-3px).

### Buttons
- Primary: `--accent-emphasis` bg, white text, 6px radius, 8px 16px padding.
- Secondary: transparent bg, `--border-default` border, `--text-primary` text.
- Ghost: no border, no bg, accent text only.
- Keep button count minimal. One primary CTA per view.

### Form Inputs
- Background: `--bg-inset`. Border: `--border-default`, 1px solid.
- Focus: border shifts to `--accent-primary`. No glow, no shadow.
- Padding: 8px 12px. Border-radius: 6px.
- Placeholder: `--text-tertiary`.

### Tables
- Header: `--text-secondary`, uppercase or small-caps, `--text-xs`.
- Rows: alternating bg optional (`--bg-elevated` / `--bg-base`). Or plain with divider lines.
- Dense: 8px row padding. Comfortable: 12px.

### Command Palette / Modal
- Centered overlay on `--bg-overlay`.
- Backdrop: rgba(0,0,0,0.5). No blur unless explicitly needed.
- Input at top, results list below. Arrow key navigation.
- Border-radius: 8px. Max-width: 560px.

## Anti-Patterns (What NOT to Do)

These are the hallmarks of "LLM-default" design. Avoid all of them:

| Anti-Pattern | Instead |
|---|---|
| Pure white text (#fff) on dark bg | Off-white (#e6edf3) |
| Drop shadows for depth | Background color layering |
| Border-radius > 8px (pill buttons on non-pills) | 4-6px for containers, full-round only for avatars/badges |
| Material Design color palette | Muted, contextual single-accent palette |
| Google Fonts / Inter / Roboto | System font stack |
| Purple gradient hero sections | Solid dark backgrounds with typographic hierarchy |
| Card-heavy layouts with shadows | List-based layouts with subtle dividers |
| 16px+ base font size | 14px base for UI, 16px only for reading content |
| Hamburger menu on desktop | Fixed sidebar navigation |
| Bright neon accent colors | Muted, desaturated accents (#58a6ff not #0066ff) |
| Excessive whitespace between components | Controlled density — information should be accessible |
| Decorative icons everywhere | Icons for navigation/actions only, text for content |
| Rounded "friendly" aesthetic | Squared-off, professional, utility-first |
| Loading spinners as afterthought | Skeleton screens matching content layout |

## When to Break the Rules

These tokens and patterns are defaults, not shackles:

- **Editorial / reading content**: Use `--font-serif`, light theme tokens, 16px+ base, generous line-height (1.625+). Think LessWrong.
- **Marketing / landing pages**: You may use display fonts, larger sizes, more dramatic spacing. But keep the muted palette and flat aesthetic.
- **Data visualization**: Color palette expands for chart data. Use categorical palettes with consistent saturation/lightness.
- **Mobile**: Sidebar becomes bottom tab bar or slide-out drawer. Touch targets: 44px minimum.

## Tailwind Configuration

When the project uses Tailwind, configure it to match:

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        bg: {
          base: '#0d1117',
          elevated: '#161b22',
          overlay: '#1c2128',
          inset: '#010409',
        },
        text: {
          primary: '#e6edf3',
          secondary: '#8b949e',
          tertiary: '#6e7681',
        },
        border: {
          DEFAULT: '#30363d',
          muted: '#21262d',
        },
        accent: {
          DEFAULT: '#58a6ff',
          emphasis: '#1f6feb',
          muted: 'rgba(56,139,253,0.15)',
        },
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', '"Noto Sans"',
               'Helvetica', 'Arial', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', '"SF Mono"', 'Menlo', 'Consolas', 'monospace'],
      },
      fontSize: {
        xs: '0.75rem',
        sm: '0.8125rem',
        base: '0.875rem',
        lg: '1rem',
        xl: '1.5rem',
      },
      spacing: {
        1: '0.25rem', 2: '0.5rem', 3: '0.75rem', 4: '1rem',
        5: '1.25rem', 6: '1.5rem', 8: '2rem', 10: '2.5rem', 12: '3rem',
      },
      borderRadius: {
        sm: '4px', DEFAULT: '6px', lg: '8px',
      },
      maxWidth: {
        content: '640px',
        wide: '960px',
      },
    },
  },
}
```

## Animation (Minimal)

Motion is subtle and purposeful. No bouncing, no spring physics, no gratuitous transitions.

```css
/* The only transitions you need */
--transition-fast:   150ms ease;     /* hover states, toggles */
--transition-normal: 200ms ease-out; /* panels, reveals */
--transition-slow:   300ms ease-out; /* page-level transitions */
```

- Hover states: color/background transitions only, 150ms.
- Panel open/close: slide + fade, 200ms.
- Page load: staggered fade-in with `animation-delay`, 300ms increments. Use sparingly.
- Scroll animations: none. Content should be immediately readable without waiting.
- Loading states: skeleton screens with a subtle pulse animation (opacity 0.5-1, 1.5s).

## Implementation Checklist

Before shipping any frontend, verify:

- [ ] No pure white (#fff/#ffffff) text on dark backgrounds
- [ ] No drop shadows (box-shadow) used for depth
- [ ] Border-radius is 4-8px (not 12-16px)
- [ ] System fonts only (no Google Fonts `<link>` tags)
- [ ] Base font size is 14px for UI (0.875rem)
- [ ] One accent color, muted (not neon)
- [ ] Sidebar navigation on desktop (not hamburger)
- [ ] Off-white text colors (#e6edf3 range)
- [ ] Borders are subtle (#30363d range), used structurally
- [ ] Information density is high — no excessive whitespace
- [ ] Dark theme by default
- [ ] Hover states use color changes, not shadows
