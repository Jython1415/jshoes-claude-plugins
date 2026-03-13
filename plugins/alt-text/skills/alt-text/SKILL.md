---
name: alt-text
description: >
  ONLY for writing or reviewing image alt-text. Provides a classification
  framework, description process, identity decision tree, and quality
  checklist grounded in accessibility standards and screen reader user
  research.
---

# Alt-Text

Write alt-text that gives screen reader users equivalent access to image
content. Every description must earn its words — omit what adds no
information, include what a sighted user would gain.

## Before you write

Determine the image's context. If context is already clear from the
conversation or task, proceed. If not, ask:

- Where will this image appear? (web page, social media, documentation, etc.)
- What role does the image play? (illustrative, informational, decorative, functional)

Context changes what matters. A headshot on a company page needs role and
setting. The same headshot on a diversity report needs observable identity.
The same headshot as a profile avatar may need nothing beyond the person's name.

## Classification (always do this first)

Every image falls into one of four categories. Classify before describing.

| Category | Signal | Action |
|----------|--------|--------|
| **Decorative** | Purely visual (borders, spacers, background patterns, aesthetic flourishes) | Empty alt-text (`alt=""`) — skip description entirely |
| **Functional** | Triggers an action (button, link, icon, control) | Describe the *action*, not the appearance: "Search", "Print this page", "Close dialog" |
| **Informative (simple)** | Conveys content (photos, illustrations, screenshots) | Describe content and purpose (see framework below) |
| **Informative (complex)** | Conveys data or relationships (charts, diagrams, flowcharts) | Brief alt-text summary + supplemental description (table, caption, or linked detail) |

When uncertain whether an image is decorative or informative: if removing
the image would lose information, it's informative.

## Description framework (for informative images)

Work through these steps in order. Stop when the description is sufficient.

### 1. Capture text in the image

Text in images is almost always essential. Reproduce it:
- Short text (under ~5 lines): transcribe verbatim
- Long text: summarize and note that full text should be available elsewhere
- Overlaid text on memes: always include — it's usually the point

### 2. Identify primary subjects

Describe what is most prominent or most relevant to context:

**People:** presence, number, primary activity or pose, observable
characteristics relevant to context (see identity section below)

**Objects:** primary subject, state, distinguishing attributes

**Places:** type of location, notable environmental features, time of day
or season if clearly conveyed

Use specific language: "golden retriever" not "dog", "cobalt blue" not "blue"
— unless specificity isn't relevant to purpose.

### 3. Describe activity or action

What is happening? Activity often conveys purpose even without surrounding
context. "A woman presenting financial data to a boardroom" is more useful
than a static inventory of people and objects.

### 4. Add distinguishing context

What makes *this* image different from similar ones? Setting, emotional tone
(if clearly conveyed through expression/body language), weather, relationships
between subjects, or medium type if non-obvious (illustration, screenshot,
diagram).

### 5. Apply length discipline

Target: 1-2 sentences. Most effective alt-text is 50-150 characters.

There is no hard character limit — purpose matters more than count. But
screen reader users find long descriptions fatiguing and often skip them.
Every word must earn its place.

For complex images that need more detail: write brief alt-text identifying
the content, then provide supplemental description elsewhere (data table,
caption, or linked long description).

## Image-type rules

### People and portraits

**Describe:** clothing, expression, pose, approximate age range, visible
accessories, activity

**Use caution with:** race, gender, disability, body size — see identity
decision tree below

**Avoid:** emotional interpretation ("happy", "angry") — describe the
expression instead ("smiling", "frowning"). Stereotypical associations.
Assumptions about relationships.

### Charts and data visualizations

Use this formula: **[Chart type] of [data type] where [main takeaway]**

Examples:
- "Bar chart of quarterly revenue where Q4 grew 40% over Q3"
- "Line chart of daily active users showing steady decline since March"

The actual data belongs in an accessible table, not compressed into alt-text.

### Screenshots and UI

- Identify as screenshot: "Screenshot of..." or "Dialog showing..."
- Focus on actionable content: buttons, form state, error messages
- Describe purpose, not pixels: "Login form with email and password fields"
  not "White input boxes on gray background"
- Mention state if meaningful: "Disabled submit button", "Error message:
  Invalid email format"

### Memes

1. Describe the image subject briefly
2. Transcribe all overlaid text exactly
3. Name the meme format if recognizable

Example: "Distracted boyfriend meme. Man labeled 'Me' looks at woman labeled
'New framework' while girlfriend labeled 'Current codebase' looks on
disapprovingly."

### Functional images (icons, buttons, links)

Describe the action, never the appearance:
- "Search" not "Magnifying glass icon"
- "Close" not "X button"
- "Visit homepage" not "Company logo"

If text already accompanies the image and conveys the same information,
use empty alt-text (`alt=""`).

## Identity decision tree

When an image contains people, use this tree to decide what identity
characteristics to include:

```
Is the person's identity known (public figure, named in context)?
├─ YES → Use their name. Include identity details only if relevant
│        to the image's purpose.
└─ NO  → Continue below.

Is identity central to the image's purpose?
(diversity content, civil rights imagery, identity-focused narrative)
├─ YES → Describe observable characteristics:
│        - Skin tone: descriptive terms ("dark skin", "light brown skin")
│          rather than racial categories
│        - Gender presentation: describe what you observe; use "person"
│          when unclear
│        - Assistive devices: "person using a wheelchair" (describe the
│          device, not the disability)
│        - Age: approximate range ("young adult", "elderly") not exact
└─ NO  → Use neutral terms ("person", "people", "group").
         Describe clothing, expression, and activity instead.
```

**Consistency check:** would you describe a white, non-disabled man the
same way? If not, reconsider what you're including.

**When uncertain:** describe observable features and actions rather than
identity categories. Omitting is safer than assuming — but deliberate
omission in contexts where identity matters can erase representation.

## Anti-patterns

| Don't | Why | Do instead |
|-------|-----|-----------|
| "Image of..." / "Photo of..." | Screen readers already announce "image" — creates "Image, Image of..." | Start directly with content |
| "May be..." / "Appears to be..." | Hedging confuses users who can't verify | State what you see; omit what you're unsure about |
| "Beautiful sunset" / "Delicious meal" | Opinion, not information | Describe what makes it so: "Sunset over calm ocean, pink and orange sky" |
| ALL CAPS words | Some screen readers spell out each letter | Standard sentence case |
| Keyword lists: "office, desk, computer, woman" | Reads as tag soup, not a description | Natural language: "Woman working at a desk in an open office" |
| Describing decorative images | Adds noise for screen reader users | Use `alt=""` |
| Cramming chart data into alt-text | Unnavigable wall of text | Brief summary + data table |
| Omitting alt attribute entirely | Screen reader reads the filename or URL | Always include `alt` — use `alt=""` for decorative |
| Repeating adjacent text | User hears the same information twice | Use `alt=""` if nearby text already covers it |

## Quality checklist

Before finalizing alt-text:

- [ ] **Accurate?** Everything described is actually visible in the image
- [ ] **Sufficient?** Someone who can't see the image understands why it's there
- [ ] **Concise?** Every word earns its place — no filler adjectives
- [ ] **No "Image of"?** Doesn't start with redundant type announcement
- [ ] **No hedging?** No "may be", "appears to", "seems like"
- [ ] **Purpose-focused?** Functional images describe actions, not visuals
- [ ] **Identity-appropriate?** People described per the decision tree above
- [ ] **Natural language?** Reads like speech, not keyword tags
- [ ] **Punctuated?** Ends with period (creates natural screen reader pause)
- [ ] **Right category?** Decorative images use `alt=""`, not verbose descriptions

## When to break the rules

- **Social media image descriptions**: can be longer and more expressive —
  users expect richer descriptions in alt-text on platforms like Mastodon
- **Art and photography**: aesthetic qualities may be the point — describing
  composition, color, mood is appropriate when the image IS the content
- **Technical documentation**: precision over brevity — exact UI element
  names, exact error text, exact code visible in screenshots
- **User request**: if the user asks for a specific style or level of detail,
  follow their guidance over these defaults
