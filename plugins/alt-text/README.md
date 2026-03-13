# alt-text

Guidance for writing effective image alt-text grounded in accessibility standards and screen reader user research.

## What it does

AI-generated alt-text tends toward keyword soup, hedging language ("may be an image of..."), and inconsistent identity description. Generic prompting produces descriptions that sound like tag clouds rather than natural language.

This skill provides:

- **W3C-aligned classification framework** — categorizes images as decorative, functional, informative (simple), or informative (complex) to determine appropriate description depth
- **Image-type specific rules** — tailored guidance for people, charts, screenshots, memes, and functional images
- **Identity description decision tree** — structured approach for handling race, gender, disability, and age in image descriptions
- **Anti-pattern table** — common mistakes with concrete corrections
- **Quality self-assessment checklist** — verification list before finalizing alt-text

## Usage

Invoke `/alt-text` before writing alt-text for images. The skill loads
guidance into context so Claude produces descriptions that are accurate,
accessible, and screen-reader friendly.

## Installation

```bash
claude plugin marketplace add https://github.com/Jython1415/jshoes-claude-plugins
claude plugin install alt-text@jshoes-claude-plugins --scope user
```

## Requirements

- Claude Code CLI

## References

- [W3C WAI Image Tutorials](https://www.w3.org/WAI/tutorials/images/)
- [WCAG 2.1 Success Criterion 1.1.1](https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html)
- [WebAIM Alternative Text Guide](https://webaim.org/techniques/alttext/)
- [WebAIM Screen Reader User Survey #10](https://webaim.org/projects/screenreadersurvey10/)
- [Microsoft Research: "Person, Shoes, Tree" (CHI 2020)](https://www.microsoft.com/en-us/research/blog/alt-text-that-informs-meeting-the-needs-of-people-who-are-blind-or-low-vision/)
- [Amy Cesal: Writing Alt Text for Data Visualization](https://medium.com/nightingale/writing-alt-text-for-data-visualization-2a218ef43f81)
- [Computer Vision and Conflicting Values (ACM AIES 2021)](https://arxiv.org/html/2105.12754)
- [MIT Gender Shades Study](https://www.media.mit.edu/articles/study-finds-gender-and-skin-type-bias-commercial-artificial-intelligence-systems/)
- [American Foundation for the Blind: Alt-Text in the Age of AI](https://afb.org/blog/entry/alt-text-age-ai)
- [University of Colorado Boulder: Identity and Inclusion in Alt Text](https://www.colorado.edu/digital-accessibility/identity-and-inclusion-alt-text)

## Author

**Jython1415** — [github.com/Jython1415](https://github.com/Jython1415)
