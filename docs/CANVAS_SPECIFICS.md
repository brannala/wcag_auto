# Canvas-Specific Accessibility Considerations

This document covers accessibility considerations unique to Canvas LMS content.

## Canvas Rich Content Editor (RCE)

### Image Handling

Canvas provides an image properties dialog in the RCE that allows setting alt text:

1. Click on an image in the editor
2. Click the image options icon
3. Enter alt text in the "Alt Text" field
4. For decorative images, check "Decorative Image"

**Note:** When content is exported, images may reference Canvas file URLs that include authentication tokens. These become inaccessible when the export is used outside Canvas.

### Table Handling

Canvas RCE's table dialog supports:
- Header row designation
- Caption (title)
- Basic cell merging

It does NOT directly support:
- `scope` attributes on headers
- `headers` attribute for complex tables
- Row headers (first column as headers)

For complex tables, you'll need to use the HTML editor or fix exported HTML.

### Heading Handling

Canvas provides a Format dropdown for headings:
- Heading 2-4 available (H1 is reserved for page title)
- Paragraph for body text

**Canvas Limitation:** The page title becomes H1 automatically, so content should start with H2.

## Canvas Page Structure

### Modules

Each module page in Canvas has:
- Module title (rendered as heading)
- Module items (links to content)

When exported, module structure becomes:
- `course_settings/module_meta.xml` - Module metadata
- Individual content files in various directories

### Wiki Pages

Canvas wiki pages export to:
- `wiki_content/[page-url].html`
- Referenced images in `web_resources/`

**Issue:** Exported HTML may have:
- Canvas-specific CSS classes
- Inline styles for alignment
- Empty divs for spacing

### Assignments

Assignment descriptions export to:
- `[assignment-id]/description.html`
- Or embedded in assignment XML

### Quizzes

Classic Quizzes export as QTI (Question & Test Interoperability):
- Questions in XML format
- Images referenced separately

**Accessibility scanning limitation:** QTI XML needs different parsing than HTML.

### Discussions

Discussion prompts export as HTML but:
- Student responses are NOT included
- Only the original prompt is accessible

## Canvas-Specific Issues

### Issue: Canvas Equation Editor

Equations created with the equation editor:
- Render as images
- May lack proper alt text
- MathML version may not be present

**Remediation:**
```html
<!-- Before -->
<img src="equation.png" alt="LaTeX: x = \frac{-b \pm \sqrt{b^2-4ac}}{2a}">

<!-- After -->
<img src="equation.png" alt="x equals negative b plus or minus the square root of b squared minus 4ac, all divided by 2a">
```

### Issue: Canvas Media Embeds

Embedded media (video, audio) in Canvas:
- May use iframe embeds from external sources
- Canvas Studio videos have separate caption handling
- YouTube embeds rely on YouTube captions

**Remediation approach:**
1. Check if video has captions (YouTube API or manual check)
2. If no captions, flag for manual caption creation
3. Provide transcript as alternative

### Issue: LTI Tool Embeds

External LTI tools embedded in Canvas:
- Content is inside iframe
- Cannot be scanned or remediated
- Accessibility depends on external tool

**Best practice:** Flag LTI embeds for manual review of the external tool's accessibility.

### Issue: Canvas Styles

Canvas applies default styles that may affect accessibility:

```css
/* Canvas default link styling */
.user_content a {
    color: #0374B5;  /* May have contrast issues on some backgrounds */
}
```

**Remediation:** Use inline styles or custom CSS for better contrast.

### Issue: Announcements

Announcements export similarly to wiki pages but:
- Include posting dates
- May have notification-specific formatting

## Re-importing Fixed Content

After fixing accessibility issues in exported content:

### Option 1: Course Copy with Selective Import

1. Create a new blank course
2. Import the fixed IMSCC
3. Copy specific fixed items back to original course

### Option 2: Full Course Replace

1. Keep original course as backup
2. Import fixed IMSCC to new course shell
3. Move enrollments to new course

### Option 3: Manual Updates

For small numbers of fixes:
1. Open each Canvas page in RCE
2. Apply fixes manually
3. Document changes

**Recommendation:** For courses with many fixes, Option 2 is most efficient.

## Canvas API for Accessibility

### Useful Endpoints

```bash
# Get all pages
GET /api/v1/courses/:course_id/pages

# Get page content
GET /api/v1/courses/:course_id/pages/:url

# Update page content
PUT /api/v1/courses/:course_id/pages/:url
body: { "wiki_page": { "body": "<html>...</html>" } }

# Get all files
GET /api/v1/courses/:course_id/files

# Get file metadata (for alt text on images)
GET /api/v1/files/:file_id
```

### Programmatic Fixes

For institutions with API access, you can:
1. Export content via API
2. Run accessibility checks
3. Apply fixes
4. Update content via API

**Caution:** API updates bypass Canvas's content validation. Ensure your HTML is valid before pushing.

## Canvas Ally Integration

If your institution uses Ally:

1. Ally scans content automatically
2. Generates alternative formats
3. Provides instructor feedback

**Relationship with this pipeline:**
- This pipeline provides more detailed issue reports
- Ally handles some remediation automatically
- Use both for comprehensive coverage

## Testing Accessibility in Canvas

### Screen Reader Testing

Test your Canvas course with:
- NVDA (Windows, free)
- JAWS (Windows, commercial)
- VoiceOver (Mac, built-in)

### Keyboard Navigation Testing

1. Use Tab to navigate through page
2. Verify all interactive elements are reachable
3. Check focus indicators are visible
4. Ensure no keyboard traps

### Canvas-Specific Test Points

- [ ] Module navigation is keyboard accessible
- [ ] Syllabus renders properly
- [ ] Grade display is accessible
- [ ] Discussion posts are navigable
- [ ] Quiz questions are readable
- [ ] Assignment submission is accessible
