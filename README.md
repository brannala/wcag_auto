# Canvas Accessibility Remediation Pipeline

A two-stage accessibility remediation system for Canvas LMS course content:

1. **Stage 1 (Automated)**: Export courses from Canvas, scan with pa11y and veraPDF, generate detailed issue reports
2. **Stage 2 (Claude-Assisted)**: Apply intelligent remediation for issues requiring human judgment (alt text, link text, heading structure, etc.)

## Features

- **Canvas API Integration**: Export courses directly via REST API
- **HTML Scanning**: pa11y with axe-core and HTML CodeSniffer runners
- **PDF Validation**: veraPDF for PDF/UA compliance checking
- **Intelligent Remediation**: Claude-assisted fixes for judgment-requiring issues
- **Batch Processing**: Handle entire courses at once
- **Detailed Reports**: JSON reports for integration with other tools
- **Best Practices Documentation**: WCAG 2.1 AA reference and remediation patterns

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

### Quick Start

```bash
# Clone or download the pipeline
cd canvas-a11y-pipeline

# Install Python dependencies
pip install -r requirements.txt

# Install pa11y (requires Node.js)
npm install -g pa11y

# Verify installation
python scripts/pipeline.py install-deps
```

### Installing veraPDF (Optional)

Download from https://verapdf.org/software/ and install following their instructions.

For Linux:
```bash
# Download installer
wget https://software.verapdf.org/releases/verapdf-installer.zip
unzip verapdf-installer.zip
cd verapdf-installer
./verapdf-install
```

## Usage

### Full Pipeline

Run the complete pipeline with a single command:

```bash
python scripts/pipeline.py full \
    --course-id 12345 \
    --token YOUR_CANVAS_API_TOKEN \
    --url https://canvas.youruniversity.edu \
    --output ./my_course_a11y
```

### Step-by-Step

#### Step 1: Export Course from Canvas

```bash
python scripts/pipeline.py export \
    --course-id 12345 \
    --token YOUR_CANVAS_API_TOKEN \
    --url https://canvas.youruniversity.edu \
    --output ./exports
```

This creates an IMSCC (IMS Common Cartridge) file containing all course content.

#### Step 2: Scan for Accessibility Issues

```bash
python scripts/pipeline.py scan \
    --input ./exports/course_12345_export.imscc \
    --output ./reports
```

This:
- Extracts the IMSCC file
- Runs pa11y on all HTML files
- Runs veraPDF on all PDF files
- Generates JSON reports

#### Step 3: Generate Remediation Tasks

```bash
python scripts/pipeline.py remediate \
    --input ./reports/extracted \
    --reports ./reports \
    --output ./remediation
```

This:
- Analyzes scan results
- Applies automatic fixes (language attributes, etc.)
- Generates input for Claude-assisted remediation

### Claude-Assisted Remediation

After running the pipeline, you'll have a `claude_remediation_input.json` file. Use this with Claude:

#### Option A: Generate Prompts for Claude

```bash
python scripts/claude_remediate.py \
    --input ./remediation/claude_remediation_input.json \
    --generate-prompts ./prompts
```

Then review the generated prompts in `./prompts/` and work through them with Claude.

#### Option B: Run Automated Remediation

```bash
python scripts/claude_remediate.py \
    --input ./remediation/claude_remediation_input.json \
    --output ./fixed
```

This applies fixes that can be determined from context (alt text from filenames, link text from URLs, etc.) and flags others for manual review.

## Configuration

### Using a Config File

Create a `config.json`:

```json
{
    "canvas_url": "https://canvas.youruniversity.edu",
    "canvas_token": "YOUR_TOKEN",
    "course_id": "12345",
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

Then run:
```bash
python scripts/pipeline.py full --config config.json
```

### Getting a Canvas API Token

1. Log into Canvas
2. Go to Account > Settings
3. Scroll to "Approved Integrations"
4. Click "+ New Access Token"
5. Set an expiration date and generate

## Output Structure

```
a11y_output/
├── exports/
│   └── course_12345_export.imscc     # Original export
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
    ├── claude_remediation_input.json # Input for Claude
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

## Using with Claude

### As a Claude Skill

Copy the `skills/SKILL.md` file to your Claude skills directory. When working with Canvas accessibility:

1. Run Stage 1 of the pipeline to generate reports
2. Share the `claude_remediation_input.json` with Claude
3. Ask Claude to remediate issues following the skill guidelines
4. Apply Claude's fixes to your content

### Example Claude Interaction

```
User: I've run the accessibility scan on my Canvas course. Here's the 
remediation input: [paste claude_remediation_input.json]

Please help me fix the accessibility issues, starting with the images 
that need alt text.

Claude: I'll analyze the images and generate appropriate alt text based 
on the context provided. Looking at the first image...
```

## Best Practices

See the documentation in `docs/`:

- **WCAG_QUICK_REFERENCE.md**: WCAG 2.1 AA checklist for Canvas content
- **REMEDIATION_PATTERNS.md**: Common fix patterns with examples

## Limitations

### What This Pipeline Can Do

- ✅ Detect most machine-testable WCAG 2.1 AA issues
- ✅ Auto-fix simple issues (missing lang attribute, etc.)
- ✅ Generate intelligent alt text suggestions from context
- ✅ Suggest better link text based on URLs and context
- ✅ Flag heading structure issues
- ✅ Identify inaccessible PDFs

### What Requires Human Judgment

- ⚠️ Alt text accuracy (Claude can suggest, human should verify)
- ⚠️ Heading hierarchy (depends on content semantics)
- ⚠️ Color contrast fixes (design decisions)
- ⚠️ Complex table structure
- ⚠️ Video captions and audio descriptions

### What This Pipeline Cannot Do

- ❌ Fix video accessibility (captions, transcripts)
- ❌ Fix audio accessibility (transcripts)
- ❌ Guarantee 100% WCAG compliance
- ❌ Make design decisions about colors/layout
- ❌ Access Canvas directly to apply fixes (export/import required)

## Troubleshooting

### pa11y not found

```bash
# Ensure Node.js is installed
node --version

# Install pa11y globally
npm install -g pa11y

# Verify
pa11y --version
```

### veraPDF not found

veraPDF is optional. To skip PDF scanning:
```bash
python scripts/pipeline.py scan --input course.imscc --skip-pdf
```

### Canvas API errors

- Verify your token hasn't expired
- Check the course ID is correct
- Ensure you have permission to export the course

### Memory issues with large courses

For courses with many files, process in batches:
```bash
# Scan HTML only first
python scripts/pipeline.py scan --input course.imscc --skip-pdf

# Then scan PDFs
python scripts/pipeline.py scan --input ./extracted --skip-html
```

## Contributing

Contributions welcome! Areas where help is needed:

- Additional auto-fix patterns
- Better alt text generation heuristics
- Support for more file types
- Integration with other LMS platforms

## License

MIT License - See LICENSE file for details.

## Acknowledgments

- [pa11y](https://pa11y.org/) - Accessibility testing tools
- [axe-core](https://github.com/dequelabs/axe-core) - Accessibility testing engine
- [veraPDF](https://verapdf.org/) - PDF/A and PDF/UA validation
- [Canvas LMS](https://www.instructure.com/canvas) - Learning Management System
