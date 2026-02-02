# WCAG 2.1 AA Quick Reference for Canvas Course Content

This document provides a concise reference for the WCAG 2.1 Level AA success criteria most relevant to Canvas LMS course content.

## Perceivable

### 1.1.1 Non-text Content (Level A)
All non-text content has a text alternative.

| Content Type | Required Action |
|-------------|----------------|
| Informational images | Provide alt text describing the content |
| Decorative images | Use `alt=""` (empty alt) |
| Complex images (charts, diagrams) | Brief alt + longer description nearby |
| Images of text | Alt text contains the same text |
| Functional images (buttons, links) | Alt describes the function |
| Image maps | Alt for `<img>` + alt for each `<area>` |
| CAPTCHA | Text alternative identifying the CAPTCHA type |

**Canvas-specific:**
- Images in Rich Content Editor need alt text via the image properties dialog
- Embedded images from Canvas files should have alt text set before upload

### 1.2.1-1.2.5 Time-based Media (Level A/AA)
Audio and video content needs alternatives.

| Media Type | Requirements |
|-----------|--------------|
| Pre-recorded audio only | Transcript |
| Pre-recorded video only | Audio description OR text alternative |
| Pre-recorded video with audio | Captions AND audio description |
| Live video with audio | Captions |

**Canvas-specific:**
- Canvas Studio provides captioning features
- YouTube videos should have accurate captions (not auto-generated)
- Kaltura captions can be edited for accuracy

### 1.3.1 Info and Relationships (Level A)
Structure and relationships conveyed through presentation can be programmatically determined.

**Headings:**
- Use heading tags (h1-h6) for headings, not just bold/large text
- Follow logical hierarchy (h1 > h2 > h3)
- One h1 per page (typically the page title)

**Lists:**
- Use proper list markup (`<ul>`, `<ol>`, `<li>`)
- Don't fake lists with dashes or asterisks

**Tables:**
- Data tables need `<th>` elements with `scope` attribute
- Complex tables need `headers` attribute
- Include `<caption>` for table identification
- Layout tables need `role="presentation"`

### 1.3.2 Meaningful Sequence (Level A)
Reading order is logical when linearized.

- Content order in HTML should match visual order
- Use CSS for visual positioning, not HTML order changes
- Tables should not be used for layout

### 1.4.1 Use of Color (Level A)
Color is not the only visual means of conveying information.

- Don't rely solely on color to indicate required fields
- Links should be distinguishable from text by more than color (underline)
- Charts should use patterns in addition to colors

### 1.4.3 Contrast (Minimum) (Level AA)
Text has a contrast ratio of at least 4.5:1 (3:1 for large text).

| Text Type | Minimum Ratio |
|-----------|---------------|
| Normal text (< 18pt or < 14pt bold) | 4.5:1 |
| Large text (≥ 18pt or ≥ 14pt bold) | 3:1 |
| Incidental text (decorative, logos) | No requirement |

**Testing tools:**
- WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/
- Browser DevTools color picker

### 1.4.4 Resize Text (Level AA)
Text can be resized to 200% without loss of content or functionality.

- Use relative units (em, rem, %) not fixed pixels for text
- Ensure content reflows, doesn't require horizontal scrolling

### 1.4.5 Images of Text (Level AA)
If text can be presented as text, don't use images.

- Avoid screenshots of text
- Use HTML/CSS for styled text when possible
- Exception: logos and essential images of text

### 1.4.10 Reflow (Level AA)
Content reflows without horizontal scrolling at 320 CSS pixels width.

- Use responsive design
- Avoid fixed-width layouts

### 1.4.11 Non-text Contrast (Level AA)
UI components and graphics have 3:1 contrast ratio.

- Form field borders visible against background
- Icon buttons distinguishable
- Chart elements distinguishable

## Operable

### 2.1.1 Keyboard (Level A)
All functionality is available via keyboard.

- All interactive elements can be reached with Tab
- All actions can be triggered with Enter or Space
- Custom widgets need keyboard support

### 2.1.2 No Keyboard Trap (Level A)
Keyboard focus can be moved away from any element.

- Modal dialogs need proper focus management
- Escape key should close overlays

### 2.4.1 Bypass Blocks (Level A)
Mechanism to bypass repeated content.

- Skip links to main content
- Proper heading structure for navigation

### 2.4.2 Page Titled (Level A)
Pages have descriptive titles.

- Canvas page titles should describe content
- Follow consistent naming convention

### 2.4.3 Focus Order (Level A)
Focus order is logical and meaningful.

- Tab order follows visual layout
- Modal dialogs trap focus appropriately

### 2.4.4 Link Purpose (In Context) (Level A)
Link purpose can be determined from link text or context.

**Good link text:**
```html
<a href="syllabus.pdf">Course Syllabus (PDF)</a>
<a href="module2.html">Module 2: Research Methods</a>
```

**Bad link text:**
```html
<a href="syllabus.pdf">Click here</a>
<a href="module2.html">Read more</a>
```

### 2.4.6 Headings and Labels (Level AA)
Headings and labels describe topic or purpose.

- Headings should be descriptive, not generic
- Form labels should clearly identify the expected input

### 2.4.7 Focus Visible (Level AA)
Keyboard focus indicator is visible.

- Don't remove focus outlines with CSS
- Custom focus styles should be clearly visible

## Understandable

### 3.1.1 Language of Page (Level A)
Page language is programmatically identified.

```html
<html lang="en">
```

### 3.1.2 Language of Parts (Level AA)
Language changes within content are identified.

```html
<p>The French phrase <span lang="fr">c'est la vie</span> means "that's life."</p>
```

### 3.2.1 On Focus (Level A)
Focus does not trigger unexpected context changes.

- Don't auto-submit forms on focus
- Don't open new windows on focus

### 3.2.2 On Input (Level A)
Input does not trigger unexpected context changes.

- Don't auto-submit forms on input change
- Warn before opening new windows

### 3.3.1 Error Identification (Level A)
Input errors are identified and described.

- Error messages describe the problem
- Indicate which field has the error

### 3.3.2 Labels or Instructions (Level A)
Labels or instructions are provided for user input.

- All form fields have associated labels
- Required fields are indicated
- Format hints are provided (e.g., "MM/DD/YYYY")

## Robust

### 4.1.1 Parsing (Level A)
HTML is well-formed.

- Valid HTML structure
- Properly nested elements
- Unique IDs

### 4.1.2 Name, Role, Value (Level A)
Custom widgets have accessible names and roles.

- ARIA labels for custom components
- Role attributes for non-standard elements
- State changes are communicated

## Common Canvas Issues and Fixes

| Issue | Fix |
|-------|-----|
| Images without alt text | Add alt via image properties in RCE |
| Generic link text | Replace with descriptive text |
| Missing heading structure | Use Format dropdown to apply headings |
| Tables without headers | Edit table properties, mark header row |
| Unlabeled form fields | Add labels via HTML editor |
| Low contrast text | Adjust colors in HTML or avoid dark themes |
| Inaccessible PDFs | Recreate as tagged PDF or provide HTML alternative |
| Auto-play media | Remove autoplay, provide controls |
| Missing page language | Add lang attribute to html element |
