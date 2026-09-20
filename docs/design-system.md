# Career Workspace design system

## Experience goal

The interface should feel calm, current, and familiar to people who use modern Google products. Material 3 informs the adaptive layout, tonal surfaces, clear state changes, and comfortable controls. Career Workspace adds a more continuous work-surface quality through layered regions, contextual overlays, and boundaries that become stronger only where interaction or comprehension needs them.

The product is a working surface. The first viewport prioritizes current applications and next actions instead of a marketing message.

### Boundaryless, with purposeful boundaries

- The page canvas, navigation, and primary workspace should read as one connected environment.
- Use whitespace, tone, and alignment before adding a border around every group.
- Use explicit boundaries for draggable stages, editable fields, destructive actions, modal layers, and dense rows.
- Allow the global assistant and application detail to float above the workspace with one clear elevation layer.
- Avoid stacking translucent panels or using blur where it makes text, focus, or performance worse.
- Preserve familiar button, input, table, and dialog behavior even when the surrounding composition is distinctive.

## Accessibility target

Target WCAG 2.2 AA for the product interface.

- Normal text contrast must be at least 4.5:1.
- Large text and meaningful component boundaries must be at least 3:1.
- Product text must not be smaller than 12 CSS pixels.
- Body copy defaults to 14 or 16 pixels with at least 1.45 line height.
- Primary interactive targets are at least 44 by 44 pixels. The WCAG minimum is 24 by 24 pixels, but the larger product default is easier to operate.
- Keyboard focus must remain visible with a two-layer focus treatment.
- Color cannot be the only way status is communicated.
- Layout must remain usable at 200 percent browser zoom and when text spacing is overridden.
- Motion must respect `prefers-reduced-motion`.

## Typography

Use Inter Variable for interface text with system sans-serif fallbacks.

| Token | Size | Line height | Weight | Use |
| --- | ---: | ---: | ---: | --- |
| `display` | 32px | 40px | 650 | Page-level empty states only |
| `headline` | 24px | 32px | 650 | Page title |
| `title` | 18px | 26px | 650 | Section and card title |
| `body-lg` | 16px | 24px | 450 | Important explanatory text |
| `body` | 14px | 21px | 450 | Default interface copy |
| `label` | 13px | 18px | 600 | Controls and metadata |
| `caption` | 12px | 17px | 500 | Supporting metadata |

Use sentence case. Avoid uppercase paragraphs and excessive letter spacing.

## Color

The palette uses deep forest for trust, blue for primary action, and warm amber for attention. Semantic tokens must be used instead of hard-coded component colors.

### Light theme

| Token | Value | Purpose |
| --- | --- | --- |
| `canvas` | `#F7F8F6` | Application background |
| `surface` | `#FFFFFF` | Primary container |
| `surface-subtle` | `#EEF2EF` | Secondary grouping |
| `text` | `#18201D` | Main text |
| `text-muted` | `#59645F` | Supporting text |
| `border` | `#D7DED9` | Dividers and inactive controls |
| `primary` | `#315BE8` | Primary actions and focus |
| `primary-strong` | `#2346BC` | Hover and pressed action |
| `primary-soft` | `#E9EEFF` | Selected navigation and information |
| `success` | `#1D6F4A` | Completed and ready states |
| `success-soft` | `#E2F3E9` | Success surface |
| `warning` | `#8A5A00` | Needs attention |
| `warning-soft` | `#FFF0C7` | Warning surface |
| `danger` | `#B3261E` | Error and destructive action |
| `danger-soft` | `#FCE8E6` | Error surface |

Dark-theme tokens are defined in code from the beginning, even if light is the initial default.

## Shape, spacing, and elevation

- Use a 4px base spacing unit.
- Common gaps are 8, 12, 16, 24, and 32 pixels.
- Inputs and buttons use a 10px radius.
- Cards and panels use a 16px radius.
- Full pills are limited to compact status badges and filters.
- Default containers use a border instead of a shadow.
- Elevated overlays use one soft shadow and a visible border.

## Components

Shared primitives live under `frontend/src/components/ui`. Product components compose them without duplicating focus, disabled, or error behavior.

Initial primitives:

- Button
- IconButton
- Input and Textarea
- Card
- Badge
- Dialog
- Tooltip
- Progress and Spinner
- EmptyState
- VisuallyHidden

Initial product components:

- ApplicationCard
- ApplicationTimeline
- CaptureConfirmation
- StatusBadge
- ResumeUpload
- AgentActivity
- PrivacySetting
- AppShell and SidebarNavigation

## Navigation and workflows

Desktop uses a collapsible navigation rail. Mobile uses a modal navigation sheet. The routes are Today, Applications, Capture Inbox, Career Profile, Assistant, and Privacy.

The first capture workflow is:

1. Detect a likely application event.
2. Show the extracted company, role, URL, status, and confidence.
3. Let the user correct the record and choose whether to include a screenshot.
4. Store only after confirmation.
5. Show a success acknowledgement and the new timeline item.

## Content rules

- Use direct labels such as “Save application” instead of “Proceed.”
- Explain permissions immediately before requesting them.
- Put the next useful action in the empty state.
- Pair errors with a recovery action.
- Do not expose model reasoning or private chain-of-thought. Show concise activity summaries and tool status only.
- Do not use invented application data in the live product. Development fixtures belong in tests.
