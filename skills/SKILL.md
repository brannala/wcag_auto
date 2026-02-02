---
name: canvas-accessibility-remediation
description: "Two-stage accessibility remediation for Canvas LMS course content. Stage 1: Automated scanning with pa11y and veraPDF. Stage 2: Claude-assisted remediation for issues requiring human judgment."
version: 1.0.0
license: MIT
---

# Canvas Accessibility Remediation Skill

## Overview

This skill enables Claude to remediate accessibility issues in Canvas LMS course content that automated tools cannot fix on their own. It works as Stage 2 of a two-stage pipeline:

1. **Stage 1 (Automated)**: Export Canvas course → Scan with pa11y/veraPDF → Generate issue reports
2. **Stage 2 (Claude-Assisted)**: Read reports + content → Apply remediation decisions → Generate accessible output

## When to Use This Skill

Use this skill when you have:
- A Canvas course export (IMSCC/Common Cartridge format)
- JSON reports from pa11y (HTML issues) and/or veraPDF (PDF issues)
- The extracted course content files

## Quick Reference

| Issue Type | Claude's Role | Output |
|------------|---------------|--------|
| Missing alt text | Generate descriptive alt text from image content | Modified HTML with alt attributes |
| Empty/vague links | Rewrite link text based on destination context | Modified HTML with descriptive links |
| Heading hierarchy | Restructure headings based on content semantics | Modified HTML with proper h1-h6 |
| Missing document title | Generate title from content analysis | Modified HTML with title element |
| Missing lang attribute | Detect language and add attribute | Modified HTML with lang="xx" |
| Table accessibility | Add scope, headers, captions | Modified HTML with accessible tables |
| Color contrast | Suggest color alternatives meeting 4.5:1 ratio | CSS recommendations or inline styles |
| PDF structure issues | Generate remediation instructions or convert to HTML | Accessible HTML or tagged PDF guidance |

## Remediation Decision Framework

### Alt Text Generation

When generating alt text for images:

1. **Decorative images**: If the image is purely decorative (borders, spacers, backgrounds), use `alt=""`
2. **Informational images**: Describe the content and function, not appearance
3. **Complex images** (charts, diagrams): Provide brief alt + longer description in surrounding text
4. **Images of text**: Reproduce the text exactly in alt attribute
5. **Linked images**: Describe the link destination, not the image

**Good examples:**
```html
<!-- Informational -->
<img src="graph.png" alt="Bar chart showing enrollment increased 40% from 2020 to 2024">

<!-- Functional (linked) -->
<a href="syllabus.pdf"><img src="pdf-icon.png" alt="Download course syllabus (PDF)"></a>

<!-- Decorative -->
<img src="decorative-border.png" alt="">
```

**Bad examples:**
```html
<!-- Too vague -->
<img src="chart.png" alt="chart">

<!-- Describes appearance, not meaning -->
<img src="warning.png" alt="Yellow triangle with exclamation mark">

<!-- Filename as alt -->
<img src="IMG_2847.jpg" alt="IMG_2847.jpg">
```

### Link Text Remediation

When fixing link text:

1. **Never use**: "click here", "read more", "link", "here", or URLs as link text
2. **Do use**: Descriptive text indicating destination or purpose
3. **For documents**: Include format and size when relevant
4. **For external links**: Indicate when link opens new window/tab

**Good examples:**
```html
<a href="syllabus.pdf">Course Syllabus (PDF, 245KB)</a>
<a href="https://example.edu">University Homepage (opens in new tab)</a>
<a href="#section3">Jump to Grading Policy</a>
```

**Bad examples:**
```html
<a href="syllabus.pdf">Click here</a>
<a href="https://example.edu">https://example.edu</a>
<a href="#section3">here</a>
```

### Heading Structure

When fixing heading hierarchy:

1. **Single h1**: Each page should have exactly one h1 (usually the page title)
2. **No skipping**: Don't jump from h1 to h3; use h2 first
3. **Semantic meaning**: Headings should reflect content structure, not visual styling
4. **Nesting**: Subsections use the next heading level down

**Correct structure:**
```
h1: Course Introduction
  h2: Learning Objectives
  h2: Required Materials
    h3: Textbooks
    h3: Software
  h2: Grading Policy
```

**Incorrect structure:**
```
h1: Course Introduction
h3: Learning Objectives     ← Skipped h2
h2: Required Materials
h4: Textbooks               ← Skipped h3
h1: Grading Policy          ← Multiple h1s
```

### Table Accessibility

When fixing tables:

1. **Add caption**: Describes table purpose
2. **Header cells**: Use `<th>` with appropriate `scope` attribute
3. **Complex tables**: Use `headers` attribute to associate data cells with headers
4. **Layout tables**: Convert to CSS layout or mark with `role="presentation"`

**Accessible data table:**
```html
<table>
  <caption>Fall 2024 Assignment Due Dates</caption>
  <thead>
    <tr>
      <th scope="col">Assignment</th>
      <th scope="col">Due Date</th>
      <th scope="col">Points</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th scope="row">Essay 1</th>
      <td>September 15</td>
      <td>100</td>
    </tr>
  </tbody>
</table>
```

### Color Contrast

WCAG 2.1 AA requirements:
- **Normal text**: 4.5:1 contrast ratio minimum
- **Large text** (18pt+ or 14pt+ bold): 3:1 contrast ratio minimum
- **UI components**: 3:1 contrast ratio minimum

When contrast fails:
1. Darken text color or lighten background (or vice versa)
2. Increase font size/weight if appropriate
3. Add visual indicators beyond color (icons, patterns, underlines)

### Document Language

1. **Primary language**: Set `lang` attribute on `<html>` element
2. **Language changes**: Mark sections in different languages with `lang` attribute
3. **Use BCP 47 codes**: en, es, fr, zh, ja, etc.

```html
<html lang="en">
  <body>
    <p>Welcome to the course.</p>
    <p lang="es">Bienvenidos al curso.</p>
  </body>
</html>
```

## Working with Course Content

### IMSCC Structure

Canvas exports create an IMSCC (IMS Common Cartridge) file with this structure:

```
course_export.imscc (ZIP archive)
├── imsmanifest.xml          # Course structure and metadata
├── course_settings/
│   └── course_settings.xml  # Canvas-specific settings
├── wiki_content/            # HTML pages
│   ├── page-title.html
│   └── ...
├── assignment_groups/       # Assignment HTML descriptions
├── web_resources/          # Uploaded files
│   ├── files/
│   │   ├── document.pdf
│   │   ├── image.png
│   │   └── ...
│   └── ...
└── ...
```

### Processing HTML Content

1. Parse HTML with a lenient parser (html5lib or BeautifulSoup)
2. Apply fixes based on pa11y report
3. Preserve Canvas-specific markup and classes
4. Write back with consistent formatting

### Processing PDFs

For PDFs with accessibility issues:

1. **If convertible**: Extract content and generate accessible HTML alternative
2. **If must remain PDF**: Document required manual fixes
3. **For scanned PDFs**: Run OCR first, then tag structure

## Integration with Pipeline

This skill expects input in the following format:

```json
{
  "course_id": "12345",
  "content_path": "/path/to/extracted/course",
  "html_report": "/path/to/pa11y-report.json",
  "pdf_report": "/path/to/verapdf-report.json",
  "output_path": "/path/to/remediated/output"
}
```

## Limitations

Claude-assisted remediation cannot:
- Fix issues in binary formats (video, audio) - these need external tools
- Guarantee 100% WCAG compliance - manual review still recommended
- Access external resources during remediation
- Fix issues requiring user intent clarification without asking

## Best Practices Document

For detailed remediation guidance, consult:
- `docs/WCAG_QUICK_REFERENCE.md` - WCAG 2.1 AA checklist
- `docs/REMEDIATION_PATTERNS.md` - Common fix patterns
- `docs/CANVAS_SPECIFICS.md` - Canvas-specific considerations
