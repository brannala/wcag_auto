# Canvas Accessibility Remediation Pipeline

A two-stage accessibility remediation system for Canvas LMS course content:

1. **Stage 1 (Automated)**: Scan exported course content with pa11y and veraPDF, generate detailed issue reports
2. **Stage 2 (Claude-Assisted)**: Apply intelligent remediation for issues requiring human judgment (alt text, link text, heading structure, etc.)

## Features

- **HTML Scanning**: pa11y with axe-core and HTML CodeSniffer runners
- **PDF Validation**: veraPDF for PDF/UA compliance checking
- **Intelligent Remediation**: Claude-assisted fixes for judgment-requiring issues
- **Batch Processing**: Handle entire courses at once
- **Detailed Reports**: JSON reports for integration with other tools

## Requirements

### System Requirements
- Python 3.8+
- Node.js 16+ (for pa11y)
- Java 8+ (for veraPDF, optional)

### Python Dependencies
```
requests
beautifulsoup4
lxml
```

### Optional Tools
- **pa11y**: HTML accessibility scanning
- **veraPDF**: PDF/UA validation

## Installation

```bash
# Clone or download the pipeline
cd wcag_auto

# Install Python dependencies
pip install -r requirements.txt

# Install pa11y (requires Node.js)
npm install

# Verify scanning tools are available
python scripts/pipeline.py install-deps
```

### Installing veraPDF (Optional)

Download from https://verapdf.org/software/ and install following their instructions.

For Linux:
```bash
wget https://software.verapdf.org/releases/verapdf-installer.zip
unzip verapdf-installer.zip
cd verapdf-installer
./verapdf-install
```

## Usage

### Step 1: Export Your Course from Canvas

Export your course manually through the Canvas web interface:

1. Open your course in Canvas
2. Go to **Settings** > **Export Course Content**
3. Select **Course** (full export)
4. Click **Create Export**
5. When the export completes, download the `.imscc` file

### Step 2: Scan for Accessibility Issues

```bash
python scripts/pipeline.py scan \
    --input path/to/course_export.imscc \
    --output ./a11y_output
```

This:
- Extracts the IMSCC file
- Runs pa11y on all HTML files
- Runs veraPDF on all PDF files (skip with `--skip-pdf`)
- Generates JSON reports

To scan only HTML or only PDFs:
```bash
# HTML only
python scripts/pipeline.py scan --input course_export.imscc --output ./a11y_output --skip-pdf

# PDF only
python scripts/pipeline.py scan --input course_export.imscc --output ./a11y_output --skip-html
```

You can also scan a previously extracted directory instead of an IMSCC file:
```bash
python scripts/pipeline.py scan --input ./a11y_output/extracted --output ./a11y_output
```

### Step 3: Generate Remediation Tasks

```bash
python scripts/pipeline.py remediate \
    --input ./a11y_output/extracted \
    --reports ./a11y_output/reports \
    --output ./a11y_output
```

This:
- Analyzes scan results
- Applies automatic fixes where possible (language attributes, etc.)
- Generates `claude_remediation_input.json` for Claude-assisted remediation

### Step 4: Claude-Assisted Remediation

After running the pipeline, you'll have a `claude_remediation_input.json` file. Use this with Claude:

#### Generate Prompts for Claude Review

```bash
python scripts/claude_remediate.py \
    --input ./a11y_output/remediation/claude_remediation_input.json \
    --generate-prompts ./prompts
```

Then review the generated prompts in `./prompts/` and work through them with Claude.

#### Run Automated Remediation (Heuristic Fixes)

```bash
python scripts/claude_remediate.py \
    --input ./a11y_output/remediation/claude_remediation_input.json \
    --output ./remediated
```

This applies fixes that can be determined from context (alt text from filenames, link text from URLs, decorative image detection, etc.) and flags the rest for manual review.

Use `--dry-run` to preview what would be changed without modifying files:
```bash
python scripts/claude_remediate.py \
    --input ./a11y_output/remediation/claude_remediation_input.json \
    --output ./remediated \
    --dry-run
```

## Configuration

You can use a config file instead of command-line arguments:

```json
{
    "work_dir": "./a11y_work",
    "output_dir": "./a11y_output",
    "wcag_standard": "WCAG2AA",
    "pa11y_runners": ["axe", "htmlcs"],
    "verapdf_profile": "ua1",
    "skip_pdf_scan": false,
    "skip_html_scan": false,
    "generate_claude_input": true
}
```

Then pass it to any command:
```bash
python scripts/pipeline.py scan --input course_export.imscc --config config.json
```

See `config/config.sample.json` for a full template.

## Output Structure

```
a11y_output/
├── extracted/
│   ├── imsmanifest.xml               # Course structure
│   ├── wiki_content/                 # HTML pages
│   ├── web_resources/                # Uploaded files
│   └── content_manifest.json         # Extracted file listing
├── reports/
│   ├── pa11y_report.json             # HTML accessibility issues
│   └── verapdf_report.json           # PDF accessibility issues
├── auto_fixed/
│   └── [modified HTML files]         # Files with auto-fixes applied
└── remediation/
    ├── claude_remediation_input.json  # Input for Claude
    └── prompts/                       # Generated prompts (optional)
```

## Report Format

### pa11y Report

```json
{
    "scanner": "pa11y",
    "standard": "WCAG2AA",
    "files_scanned": 15,
    "files_with_issues": 8,
    "total_issues": 42,
    "issues_by_type": {
        "WCAG2AA.Principle1.Guideline1_1.1_1_1.H37": 12,
        "WCAG2AA.Principle2.Guideline2_4.2_4_4.H77": 8
    },
    "file_reports": [
        {
            "file": "wiki_content/syllabus.html",
            "issues": [
                {
                    "code": "WCAG2AA.Principle1.Guideline1_1.1_1_1.H37",
                    "type": "error",
                    "message": "Img element missing an alt attribute...",
                    "context": "<img src=\"diagram.png\">",
                    "selector": "html > body > div > img"
                }
            ]
        }
    ]
}
```

### Claude Remediation Input

```json
{
    "course_info": {
        "content_dir": "./extracted",
        "title": "Introduction to Biology"
    },
    "html_tasks": [
        {
            "file": "wiki_content/syllabus.html",
            "content_preview": "<!DOCTYPE html>...",
            "issues": [
                {
                    "code": "WCAG2AA.Principle1.Guideline1_1.1_1_1.H37",
                    "category": "images",
                    "auto_fixable": false,
                    "remediation_hint": "Generate descriptive alt text..."
                }
            ],
            "images": [
                {
                    "src": "images/diagram.png",
                    "current_alt": null,
                    "needs_alt": true,
                    "context": "Surrounding text: This diagram shows..."
                }
            ]
        }
    ],
    "summary": {
        "total_html_issues": 42,
        "auto_fixable": 5,
        "needs_judgment": 37
    }
}
```

## Applying Fixes Back to Canvas

After remediating the exported content, you need to get the fixes back into Canvas. Options:

### Option 1: Manual Updates (Small Number of Fixes)
1. Open each Canvas page in the Rich Content Editor
2. Apply fixes manually based on the remediation output
3. This is practical for courses with fewer than ~20 issues

### Option 2: Course Re-import (Many Fixes)
1. Re-package fixed content as IMSCC (not yet automated)
2. Import to a new Canvas course shell
3. Move enrollments to the new course

See `docs/CANVAS_SPECIFICS.md` for details on Canvas re-import considerations.

## Limitations

### What This Pipeline Can Do
- Detect most machine-testable WCAG 2.1 AA issues
- Auto-fix simple issues (missing lang attribute, etc.)
- Generate intelligent alt text suggestions from context
- Suggest better link text based on URLs and context
- Flag heading structure issues
- Identify inaccessible PDFs

### What Requires Human Judgment
- Alt text accuracy (heuristics can suggest, human should verify)
- Heading hierarchy (depends on content semantics)
- Color contrast fixes (design decisions)
- Complex table structure
- Video captions and audio descriptions

### What This Pipeline Cannot Do
- Fix video accessibility (captions, transcripts)
- Fix audio accessibility (transcripts)
- Guarantee 100% WCAG compliance
- Make design decisions about colors/layout
- Automatically re-import fixed content into Canvas

### Not Yet Implemented
- `--apply-fixes` in `claude_remediate.py` (applying fix JSON back to files)
- PDF remediation (PDFs are flagged for review only)
- Re-packaging fixed content as IMSCC for Canvas import

## Troubleshooting

### pa11y not found

```bash
# Ensure Node.js is installed
node --version

# Install from project root
npm install

# Verify
npx pa11y --version
```

### veraPDF not found

veraPDF is optional. To skip PDF scanning:
```bash
python scripts/pipeline.py scan --input course.imscc --skip-pdf
```

### Memory issues with large courses

For courses with many files, process in batches:
```bash
# Scan HTML only first
python scripts/pipeline.py scan --input course.imscc --skip-pdf

# Then scan PDFs
python scripts/pipeline.py scan --input ./extracted --skip-html
```

## Best Practices

See the documentation in `docs/`:

- **WCAG_QUICK_REFERENCE.md**: WCAG 2.1 AA checklist for Canvas content
- **REMEDIATION_PATTERNS.md**: Common fix patterns with before/after examples
- **CANVAS_SPECIFICS.md**: Canvas-specific considerations

## License

MIT License - See LICENSE file for details.

## Acknowledgments

- [pa11y](https://pa11y.org/) - Accessibility testing tools
- [axe-core](https://github.com/dequelabs/axe-core) - Accessibility testing engine
- [veraPDF](https://verapdf.org/) - PDF/A and PDF/UA validation
- [Canvas LMS](https://www.instructure.com/canvas) - Learning Management System
