---
name: Quiet Reference
colors:
  surface: '#f2fbff'
  surface-dim: '#d0dce1'
  surface-bright: '#f2fbff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eaf6fb'
  surface-container: '#e4f0f5'
  surface-container-high: '#deeaef'
  surface-container-highest: '#d8e4ea'
  on-surface: '#121d21'
  on-surface-variant: '#404849'
  inverse-surface: '#273236'
  inverse-on-surface: '#e7f3f8'
  outline: '#707979'
  outline-variant: '#bfc8c8'
  surface-tint: '#2c676a'
  primary: '#003739'
  on-primary: '#ffffff'
  primary-container: '#0b4f52'
  on-primary-container: '#86bfc2'
  inverse-primary: '#97d1d4'
  secondary: '#815500'
  on-secondary: '#ffffff'
  secondary-container: '#fdba55'
  on-secondary-container: '#724a00'
  tertiary: '#5e1705'
  on-tertiary: '#ffffff'
  tertiary-container: '#7d2d19'
  on-tertiary-container: '#ff9c82'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#b2edf0'
  primary-fixed-dim: '#97d1d4'
  on-primary-fixed: '#002021'
  on-primary-fixed-variant: '#0b4f52'
  secondary-fixed: '#ffddb2'
  secondary-fixed-dim: '#fdba55'
  on-secondary-fixed: '#291800'
  on-secondary-fixed-variant: '#624000'
  tertiary-fixed: '#ffdad2'
  tertiary-fixed-dim: '#ffb4a2'
  on-tertiary-fixed: '#3c0800'
  on-tertiary-fixed-variant: '#7c2d18'
  background: '#f2fbff'
  on-background: '#121d21'
  surface-variant: '#d8e4ea'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  data-mono:
    fontFamily: IBM Plex Mono
    fontSize: 13px
    fontWeight: '450'
    lineHeight: '1.5'
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.2'
    letterSpacing: 0.02em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  container-max: 800px
  gutter: 20px
---

## Brand & Style
The design system is centered on the concept of a "Quiet Reference"—a digital librarian for complex financial data. The personality is calm, trustworthy, and precise, intentionally distancing itself from the high-energy, urgent patterns common in fintech or trading applications. 

The aesthetic follows a **Modern Professional** style with a focus on editorial clarity. It utilizes generous whitespace, restrained color application, and a clear hierarchy to minimize cognitive load. The UI should evoke the feeling of a high-quality physical report or a well-indexed archive. Avoid all decorative imagery, "gamification" elements, or marketing-heavy graphics. Every element on screen must serve a functional purpose in aiding the user’s understanding of mutual fund data.

## Colors
The palette is grounded in "Teal" for authority and "Amber" for utility, creating a professional and scholarly atmosphere.

- **Primary (#0B4F52):** Used for navigation, active states, and primary actions. It represents the "Assistant's" voice.
- **Accent (#A9720C):** Strictly reserved for citations, source links, and footnotes. This distinguishes "External Truth" from the assistant's UI.
- **Error/Refusal (#B5573F):** A muted terracotta used for system errors or when the assistant cannot answer a query. Avoid bright reds to maintain the calm tone.
- **Neutral (Text-Ink #1F2A2E / Text-Muted #5B6B6E):** The foundation for all content. Maintain high legibility by using Ink for body text and Muted for metadata.
- **Surface & Background:** The background is a very soft grey-green (#F7F8F7) to reduce screen glare, while cards and containers use pure white (#FFFFFF) to create subtle separation.

## Typography
The typography system prioritizes legibility for long-form reading and data scanning.

- **Primary (Inter):** Used for the majority of the interface. Headings should have a slight negative letter spacing to feel tight and professional.
- **Secondary (IBM Plex Mono):** Utilized for "hard" data points, timestamps, and citation URLs. This font choice signals technical accuracy and raw data retrieval.
- **Line Height:** Maintain a generous 1.5–1.6 for body text to ensure users can comfortably read complex financial explanations without fatigue.

## Layout & Spacing
The layout follows a **Fixed Center Grid** model for the core assistant interface, mimicking a research paper or a document view. 

- **Max Width:** Content should be capped at 800px to maintain optimal line lengths for reading.
- **Rhythm:** Use a 4px base unit. Component padding should generally be 16px (md) or 24px (lg) to give elements room to breathe.
- **Responsive:** On mobile, margins reduce to 16px and the layout becomes a single column. On desktop, sidebars may be used for "Recent Searches" or "Glossary" terms, but the primary chat/data area remains centered.

## Elevation & Depth
This design system uses **Low-contrast Outlines** and **Tonal Layers** rather than heavy shadows.

- **Surfaces:** Use 1px solid borders (#E1E6E5) to define containers.
- **Depth:** Instead of shadows, use subtle color shifts. A "Surface" card (#FFFFFF) sits on the "Background" (#F7F8F7).
- **Active State:** For interactive elements, use a tiny, crisp shadow (2px blur, 5% opacity) only upon hover to indicate interactivity without breaking the flat, calm aesthetic.

## Shapes
The shape language is soft but structured. 

- **Cards and Containers:** Use a 12px radius (rounded-lg) to soften the professional tone and make the assistant feel approachable.
- **Chips/Labels:** Use "Pill" shapes (full radius) for status indicators or fund categories.
- **Inputs:** Maintain the 8px base radius (standard) to keep them feeling like distinct utility tools.

## Components
- **Message Bubbles:** Do not use traditional chat bubbles. Use card-like containers with 1px borders. The Assistant’s response should have a subtle #E4F0EF (Primary-Light) top-border to distinguish it.
- **Citations:** Small inline badges or footer links using #A9720C and IBM Plex Mono. When clicked, they should open a "Source View" with a light amber background (#F6ECD9).
- **Buttons:** Primary buttons use #0B4F52 with white text. Secondary buttons are outlined with #E1E6E5. Avoid gradients.
- **Input Field:** A wide, clean text area with an 8px radius. Use a 1px border that thickens slightly (or changes to teal) on focus.
- **Chips:** Used for "Suggested Questions." These are pill-shaped, using #E1E6E5 borders and #1F2A2E text.
- **Data Tables:** High density but clean. Use IBM Plex Mono for numerical values. Row separators should be faint #E1E6E5.