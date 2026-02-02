#!/usr/bin/env python3
"""
Canvas Accessibility Remediation Pipeline

Two-stage accessibility remediation for Canvas LMS course content:
  Stage 1: Automated scanning with pa11y and veraPDF
  Stage 2: Claude-assisted remediation for issues requiring judgment

Usage:
    python pipeline.py export --course-id COURSE_ID --token TOKEN --url URL
    python pipeline.py scan --input course_export.imscc
    python pipeline.py remediate --input extracted/ --reports reports/
    python pipeline.py full --course-id COURSE_ID --token TOKEN --url URL
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

try:
    import requests
except ImportError:
    print("Installing requests...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Installing beautifulsoup4...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4", "lxml", "-q"])
    from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the remediation pipeline."""
    canvas_url: str = ""
    canvas_token: str = ""
    course_id: str = ""
    work_dir: Path = field(default_factory=lambda: Path("./a11y_work"))
    output_dir: Path = field(default_factory=lambda: Path("./a11y_output"))
    wcag_standard: str = "WCAG2AA"
    pa11y_runners: list = field(default_factory=lambda: ["axe", "htmlcs"])
    verapdf_profile: str = "ua1"  # PDF/UA-1
    skip_pdf_scan: bool = False
    skip_html_scan: bool = False
    generate_claude_input: bool = True
    
    @classmethod
    def from_file(cls, config_path: Path) -> 'PipelineConfig':
        """Load configuration from JSON file."""
        with open(config_path) as f:
            data = json.load(f)
        return cls(**data)
    
    def to_file(self, config_path: Path):
        """Save configuration to JSON file."""
        with open(config_path, 'w') as f:
            json.dump(self.__dict__, f, indent=2, default=str)


class CanvasExporter:
    """Export course content from Canvas LMS via API."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {config.canvas_token}'
        })
    
    def api_url(self, endpoint: str) -> str:
        """Construct full API URL."""
        base = self.config.canvas_url.rstrip('/')
        return f"{base}/api/v1/{endpoint.lstrip('/')}"
    
    def export_course(self, output_path: Path) -> Path:
        """
        Export course as Common Cartridge.
        
        Returns path to downloaded IMSCC file.
        """
        course_id = self.config.course_id
        logger.info(f"Starting export for course {course_id}")
        
        # Request export
        export_url = self.api_url(f"courses/{course_id}/content_exports")
        resp = self.session.post(export_url, data={'export_type': 'common_cartridge'})
        resp.raise_for_status()
        export_data = resp.json()
        
        export_id = export_data['id']
        progress_url = export_data.get('progress_url')
        
        logger.info(f"Export started, ID: {export_id}")
        
        # Poll for completion
        status_url = self.api_url(f"courses/{course_id}/content_exports/{export_id}")
        max_attempts = 120  # 10 minutes with 5-second intervals
        
        for attempt in range(max_attempts):
            resp = self.session.get(status_url)
            resp.raise_for_status()
            status_data = resp.json()
            
            state = status_data.get('workflow_state')
            logger.debug(f"Export state: {state}")
            
            if state == 'exported':
                download_url = status_data.get('attachment', {}).get('url')
                if download_url:
                    break
            elif state == 'failed':
                raise RuntimeError(f"Export failed: {status_data}")
            
            time.sleep(5)
        else:
            raise TimeoutError("Export timed out after 10 minutes")
        
        # Download export
        logger.info("Downloading export...")
        output_file = output_path / f"course_{course_id}_export.imscc"
        
        with self.session.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(output_file, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        logger.info(f"Export saved to {output_file}")
        return output_file


class ContentExtractor:
    """Extract and organize content from IMSCC export."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
    
    def extract(self, imscc_path: Path, output_dir: Path) -> dict:
        """
        Extract IMSCC file and organize content.
        
        Returns manifest of extracted content.
        """
        logger.info(f"Extracting {imscc_path}")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(imscc_path, 'r') as zf:
            zf.extractall(output_dir)
        
        # Build content manifest
        manifest = {
            'html_files': [],
            'pdf_files': [],
            'image_files': [],
            'other_files': [],
            'structure': {}
        }
        
        for root, dirs, files in os.walk(output_dir):
            root_path = Path(root)
            for filename in files:
                file_path = root_path / filename
                rel_path = file_path.relative_to(output_dir)
                ext = file_path.suffix.lower()
                
                if ext in ['.html', '.htm']:
                    manifest['html_files'].append(str(rel_path))
                elif ext == '.pdf':
                    manifest['pdf_files'].append(str(rel_path))
                elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg']:
                    manifest['image_files'].append(str(rel_path))
                else:
                    manifest['other_files'].append(str(rel_path))
        
        # Parse imsmanifest.xml if present
        manifest_xml = output_dir / 'imsmanifest.xml'
        if manifest_xml.exists():
            manifest['structure'] = self._parse_manifest(manifest_xml)
        
        # Save manifest
        manifest_path = output_dir / 'content_manifest.json'
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Extracted: {len(manifest['html_files'])} HTML, "
                   f"{len(manifest['pdf_files'])} PDF, "
                   f"{len(manifest['image_files'])} images")
        
        return manifest
    
    def _parse_manifest(self, manifest_path: Path) -> dict:
        """Parse imsmanifest.xml for course structure."""
        try:
            with open(manifest_path) as f:
                soup = BeautifulSoup(f.read(), 'lxml-xml')
            
            structure = {
                'title': '',
                'items': []
            }
            
            # Get course title
            title_elem = soup.find('title')
            if title_elem:
                structure['title'] = title_elem.get_text()
            
            # Get items
            for item in soup.find_all('item'):
                item_data = {
                    'identifier': item.get('identifier', ''),
                    'title': '',
                    'href': item.get('identifierref', '')
                }
                title_elem = item.find('title')
                if title_elem:
                    item_data['title'] = title_elem.get_text()
                structure['items'].append(item_data)
            
            return structure
        except Exception as e:
            logger.warning(f"Could not parse manifest: {e}")
            return {}


class AccessibilityScanner:
    """Run automated accessibility scans."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
    
    def check_dependencies(self) -> dict:
        """Check which scanning tools are available."""
        deps = {
            'pa11y': False,
            'verapdf': False,
            'node': False
        }
        
        # Check Node.js
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True)
            deps['node'] = result.returncode == 0
        except FileNotFoundError:
            pass
        
        # Check pa11y (via npx or global)
        try:
            result = subprocess.run(['npx', 'pa11y', '--version'], capture_output=True, text=True)
            deps['pa11y'] = result.returncode == 0
        except FileNotFoundError:
            pass
        
        # Check veraPDF
        for cmd in ['verapdf', './verapdf/verapdf']:
            try:
                result = subprocess.run([cmd, '--version'], capture_output=True, text=True)
                if result.returncode == 0:
                    deps['verapdf'] = cmd
                    break
            except FileNotFoundError:
                pass
        
        return deps
    
    def scan_html(self, content_dir: Path, manifest: dict, output_dir: Path) -> dict:
        """
        Scan HTML files with pa11y.
        
        Returns aggregated report.
        """
        if self.config.skip_html_scan:
            logger.info("Skipping HTML scan (disabled)")
            return {'skipped': True}
        
        logger.info("Starting HTML accessibility scan...")
        
        report = {
            'scanner': 'pa11y',
            'standard': self.config.wcag_standard,
            'runners': self.config.pa11y_runners,
            'files_scanned': 0,
            'files_with_issues': 0,
            'total_issues': 0,
            'issues_by_type': {},
            'file_reports': []
        }
        
        html_files = manifest.get('html_files', [])
        
        for html_file in html_files:
            file_path = content_dir / html_file
            if not file_path.exists():
                continue
            
            file_report = self._scan_single_html(file_path)
            file_report['file'] = html_file
            report['file_reports'].append(file_report)
            report['files_scanned'] += 1
            
            if file_report.get('issues'):
                report['files_with_issues'] += 1
                report['total_issues'] += len(file_report['issues'])
                
                for issue in file_report['issues']:
                    issue_type = issue.get('code', 'unknown')
                    report['issues_by_type'][issue_type] = \
                        report['issues_by_type'].get(issue_type, 0) + 1
        
        # Save report
        report_path = output_dir / 'pa11y_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"HTML scan complete: {report['total_issues']} issues "
                   f"in {report['files_with_issues']}/{report['files_scanned']} files")
        
        return report
    
    def _scan_single_html(self, file_path: Path) -> dict:
        """Scan a single HTML file with pa11y."""
        try:
            runners = ','.join(self.config.pa11y_runners)
            cmd = [
                'npx', 'pa11y',
                str(file_path),
                '-s', self.config.wcag_standard,
                '-r', 'json',
                '-e', runners,
                '--include-notices',
                '--include-warnings'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.stdout:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {'error': 'Invalid JSON output', 'raw': result.stdout[:500]}
            
            return {'issues': [], 'error': result.stderr if result.returncode != 0 else None}
            
        except subprocess.TimeoutExpired:
            return {'error': 'Scan timed out'}
        except FileNotFoundError:
            return {'error': 'pa11y not found - run npm install in project root'}
        except Exception as e:
            return {'error': str(e)}
    
    def scan_pdfs(self, content_dir: Path, manifest: dict, output_dir: Path) -> dict:
        """
        Scan PDF files with veraPDF.
        
        Returns aggregated report.
        """
        if self.config.skip_pdf_scan:
            logger.info("Skipping PDF scan (disabled)")
            return {'skipped': True}
        
        logger.info("Starting PDF accessibility scan...")
        
        report = {
            'scanner': 'veraPDF',
            'profile': self.config.verapdf_profile,
            'files_scanned': 0,
            'files_with_issues': 0,
            'total_issues': 0,
            'file_reports': []
        }
        
        pdf_files = manifest.get('pdf_files', [])
        deps = self.check_dependencies()
        verapdf_cmd = deps.get('verapdf')
        
        if not verapdf_cmd:
            logger.warning("veraPDF not found - skipping PDF scan")
            report['error'] = 'veraPDF not installed'
            return report
        
        for pdf_file in pdf_files:
            file_path = content_dir / pdf_file
            if not file_path.exists():
                continue
            
            file_report = self._scan_single_pdf(file_path, verapdf_cmd)
            file_report['file'] = pdf_file
            report['file_reports'].append(file_report)
            report['files_scanned'] += 1
            
            if file_report.get('issues'):
                report['files_with_issues'] += 1
                report['total_issues'] += len(file_report['issues'])
        
        # Save report
        report_path = output_dir / 'verapdf_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"PDF scan complete: {report['total_issues']} issues "
                   f"in {report['files_with_issues']}/{report['files_scanned']} files")
        
        return report
    
    def _scan_single_pdf(self, file_path: Path, verapdf_cmd: str) -> dict:
        """Scan a single PDF file with veraPDF."""
        try:
            cmd = [
                verapdf_cmd,
                '-f', self.config.verapdf_profile,
                '--format', 'json',
                str(file_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    # Extract issues from veraPDF JSON structure
                    issues = []
                    report = data.get('report', data)
                    jobs = report.get('jobs', [])
                    
                    for job in jobs:
                        validation = job.get('validationResult', {})
                        details = validation.get('details', {})
                        rules = details.get('rules', [])
                        
                        for rule in rules:
                            if rule.get('status') == 'failed':
                                issues.append({
                                    'rule': rule.get('clause', ''),
                                    'description': rule.get('description', ''),
                                    'test': rule.get('test', ''),
                                    'failures': rule.get('failedChecks', 0)
                                })
                    
                    return {
                        'compliant': validation.get('compliant', False),
                        'issues': issues
                    }
                except json.JSONDecodeError:
                    return {'error': 'Invalid JSON output'}
            
            return {'issues': [], 'error': result.stderr if result.returncode != 0 else None}
            
        except subprocess.TimeoutExpired:
            return {'error': 'Scan timed out'}
        except Exception as e:
            return {'error': str(e)}


class ClaudeRemediationGenerator:
    """Generate input files for Claude-assisted remediation."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
    
    def generate_remediation_input(
        self,
        content_dir: Path,
        manifest: dict,
        html_report: dict,
        pdf_report: dict,
        output_dir: Path
    ) -> Path:
        """
        Generate consolidated input for Claude remediation.
        
        Creates a JSON file containing:
        - Issues to remediate
        - Relevant content context
        - Remediation instructions
        """
        logger.info("Generating Claude remediation input...")
        
        remediation_tasks = {
            'course_info': {
                'content_dir': str(content_dir),
                'title': manifest.get('structure', {}).get('title', 'Unknown Course')
            },
            'html_tasks': [],
            'pdf_tasks': [],
            'summary': {
                'total_html_issues': 0,
                'total_pdf_issues': 0,
                'auto_fixable': 0,
                'needs_judgment': 0
            }
        }
        
        # Process HTML issues
        for file_report in html_report.get('file_reports', []):
            if not file_report.get('issues'):
                continue
            
            file_path = content_dir / file_report['file']
            content = self._read_file_safely(file_path)
            
            task = {
                'file': file_report['file'],
                'content_preview': content[:5000] if content else None,
                'issues': [],
                'images': []
            }
            
            for issue in file_report.get('issues', []):
                categorized = self._categorize_html_issue(issue)
                task['issues'].append(categorized)
                remediation_tasks['summary']['total_html_issues'] += 1
                
                if categorized['auto_fixable']:
                    remediation_tasks['summary']['auto_fixable'] += 1
                else:
                    remediation_tasks['summary']['needs_judgment'] += 1
            
            # Extract image references for alt text generation
            if content:
                task['images'] = self._extract_images(content, content_dir, file_report['file'])
            
            remediation_tasks['html_tasks'].append(task)
        
        # Process PDF issues
        for file_report in pdf_report.get('file_reports', []):
            if not file_report.get('issues'):
                continue
            
            task = {
                'file': file_report['file'],
                'compliant': file_report.get('compliant', False),
                'issues': file_report['issues']
            }
            
            remediation_tasks['pdf_tasks'].append(task)
            remediation_tasks['summary']['total_pdf_issues'] += len(file_report['issues'])
        
        # Save remediation input
        output_file = output_dir / 'claude_remediation_input.json'
        with open(output_file, 'w') as f:
            json.dump(remediation_tasks, f, indent=2)
        
        logger.info(f"Remediation input saved to {output_file}")
        logger.info(f"Summary: {remediation_tasks['summary']}")
        
        return output_file
    
    def _read_file_safely(self, file_path: Path) -> Optional[str]:
        """Read file content with fallback encoding."""
        if not file_path.exists():
            return None
        
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                with open(file_path, encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        return None
    
    def _categorize_html_issue(self, issue: dict) -> dict:
        """Categorize HTML issue and determine if auto-fixable."""
        code = issue.get('code', '')
        issue_type = issue.get('type', 'error')
        message = issue.get('message', '')
        context = issue.get('context', '')
        selector = issue.get('selector', '')
        
        # Determine category and auto-fixability
        category = 'other'
        auto_fixable = False
        remediation_hint = ''
        
        if 'alt' in code.lower() or 'image' in message.lower():
            category = 'images'
            auto_fixable = False  # Needs Claude judgment for alt text
            remediation_hint = 'Generate descriptive alt text based on image content and context'
        
        elif 'link' in code.lower() or 'anchor' in message.lower():
            category = 'links'
            auto_fixable = 'empty' in message.lower()
            remediation_hint = 'Make link text descriptive of destination'
        
        elif 'heading' in code.lower() or 'h1' in message.lower() or 'h2' in message.lower():
            category = 'headings'
            auto_fixable = False
            remediation_hint = 'Ensure proper heading hierarchy (h1 > h2 > h3)'
        
        elif 'lang' in code.lower() or 'language' in message.lower():
            category = 'language'
            auto_fixable = True
            remediation_hint = 'Add lang attribute to html element'
        
        elif 'contrast' in code.lower() or 'color' in message.lower():
            category = 'contrast'
            auto_fixable = False
            remediation_hint = 'Adjust colors to meet 4.5:1 contrast ratio'
        
        elif 'table' in code.lower():
            category = 'tables'
            auto_fixable = False
            remediation_hint = 'Add proper table headers and scope attributes'
        
        elif 'label' in code.lower() or 'form' in message.lower():
            category = 'forms'
            auto_fixable = False
            remediation_hint = 'Associate labels with form controls'
        
        return {
            'code': code,
            'type': issue_type,
            'message': message,
            'context': context,
            'selector': selector,
            'category': category,
            'auto_fixable': auto_fixable,
            'remediation_hint': remediation_hint
        }
    
    def _extract_images(self, content: str, content_dir: Path, html_file: str) -> list:
        """Extract image information for alt text generation."""
        images = []
        soup = BeautifulSoup(content, 'html.parser')
        
        for img in soup.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt')
            
            # Resolve relative path
            if src and not src.startswith(('http://', 'https://', 'data:')):
                html_dir = Path(html_file).parent
                img_path = content_dir / html_dir / src
                if not img_path.exists():
                    img_path = content_dir / src
                
                images.append({
                    'src': src,
                    'current_alt': alt,
                    'needs_alt': alt is None or alt == '' or alt == src,
                    'path': str(img_path) if img_path.exists() else None,
                    'context': self._get_image_context(img)
                })
        
        return images
    
    def _get_image_context(self, img_tag) -> str:
        """Get surrounding context for an image."""
        context_parts = []
        
        # Get parent element text
        parent = img_tag.parent
        if parent:
            siblings_text = parent.get_text(strip=True)[:200]
            if siblings_text:
                context_parts.append(f"Surrounding text: {siblings_text}")
        
        # Check for figure/figcaption
        figure = img_tag.find_parent('figure')
        if figure:
            caption = figure.find('figcaption')
            if caption:
                context_parts.append(f"Caption: {caption.get_text(strip=True)}")
        
        # Check for title attribute
        title = img_tag.get('title')
        if title:
            context_parts.append(f"Title: {title}")
        
        return ' | '.join(context_parts) if context_parts else ''


class HTMLRemediator:
    """Apply remediation fixes to HTML content."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
    
    def apply_auto_fixes(self, content_dir: Path, remediation_input: dict, output_dir: Path) -> dict:
        """
        Apply automatic fixes that don't require judgment.
        
        Returns report of applied fixes.
        """
        logger.info("Applying automatic HTML fixes...")
        
        fixes_applied = {
            'files_modified': 0,
            'fixes': []
        }
        
        for task in remediation_input.get('html_tasks', []):
            file_path = content_dir / task['file']
            output_path = output_dir / task['file']
            
            if not file_path.exists():
                continue
            
            content = self._read_file(file_path)
            if not content:
                continue
            
            modified = False
            soup = BeautifulSoup(content, 'html.parser')
            
            for issue in task.get('issues', []):
                if not issue.get('auto_fixable'):
                    continue
                
                if issue['category'] == 'language':
                    if self._fix_language(soup):
                        modified = True
                        fixes_applied['fixes'].append({
                            'file': task['file'],
                            'fix': 'Added lang="en" to html element'
                        })
            
            if modified:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(str(soup))
                fixes_applied['files_modified'] += 1
        
        return fixes_applied
    
    def _read_file(self, file_path: Path) -> Optional[str]:
        """Read file with encoding detection."""
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                with open(file_path, encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        return None
    
    def _fix_language(self, soup: BeautifulSoup) -> bool:
        """Add lang attribute to html element if missing."""
        html_tag = soup.find('html')
        if html_tag and not html_tag.get('lang'):
            html_tag['lang'] = 'en'
            return True
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Canvas Accessibility Remediation Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline with Canvas export
  python pipeline.py full --course-id 12345 --token YOUR_TOKEN --url https://canvas.university.edu

  # Export only
  python pipeline.py export --course-id 12345 --token YOUR_TOKEN --url https://canvas.university.edu

  # Scan existing export
  python pipeline.py scan --input course_export.imscc

  # Generate remediation tasks from scan results
  python pipeline.py remediate --input extracted/ --reports reports/

  # Use config file
  python pipeline.py full --config config.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export course from Canvas')
    export_parser.add_argument('--course-id', required=True, help='Canvas course ID')
    export_parser.add_argument('--token', required=True, help='Canvas API token')
    export_parser.add_argument('--url', required=True, help='Canvas instance URL')
    export_parser.add_argument('--output', default='./exports', help='Output directory')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan exported content')
    scan_parser.add_argument('--input', required=True, help='IMSCC file or extracted directory')
    scan_parser.add_argument('--output', default='./reports', help='Reports output directory')
    scan_parser.add_argument('--skip-pdf', action='store_true', help='Skip PDF scanning')
    scan_parser.add_argument('--skip-html', action='store_true', help='Skip HTML scanning')
    
    # Remediate command
    remediate_parser = subparsers.add_parser('remediate', help='Generate remediation tasks')
    remediate_parser.add_argument('--input', required=True, help='Extracted content directory')
    remediate_parser.add_argument('--reports', required=True, help='Reports directory')
    remediate_parser.add_argument('--output', default='./remediation', help='Output directory')
    
    # Full pipeline command
    full_parser = subparsers.add_parser('full', help='Run full pipeline')
    full_parser.add_argument('--course-id', help='Canvas course ID')
    full_parser.add_argument('--token', help='Canvas API token')
    full_parser.add_argument('--url', help='Canvas instance URL')
    full_parser.add_argument('--config', help='Config file path')
    full_parser.add_argument('--output', default='./a11y_output', help='Output directory')
    
    # Install dependencies command
    install_parser = subparsers.add_parser('install-deps', help='Install scanning dependencies')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Handle install-deps
    if args.command == 'install-deps':
        install_dependencies()
        sys.exit(0)
    
    # Build config
    config = PipelineConfig()
    
    if hasattr(args, 'config') and args.config:
        config = PipelineConfig.from_file(Path(args.config))
    
    if hasattr(args, 'course_id') and args.course_id:
        config.course_id = args.course_id
    if hasattr(args, 'token') and args.token:
        config.canvas_token = args.token
    if hasattr(args, 'url') and args.url:
        config.canvas_url = args.url
    if hasattr(args, 'output'):
        config.output_dir = Path(args.output)
    if hasattr(args, 'skip_pdf') and args.skip_pdf:
        config.skip_pdf_scan = True
    if hasattr(args, 'skip_html') and args.skip_html:
        config.skip_html_scan = True
    
    config.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Execute command
    try:
        if args.command == 'export':
            run_export(config)
        elif args.command == 'scan':
            run_scan(config, Path(args.input))
        elif args.command == 'remediate':
            run_remediate(config, Path(args.input), Path(args.reports))
        elif args.command == 'full':
            run_full_pipeline(config)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise


def install_dependencies():
    """Install required scanning tools."""
    logger.info("Installing dependencies...")
    
    # Check Node.js
    try:
        subprocess.run(['node', '--version'], capture_output=True, check=True)
        logger.info("Node.js: OK")
    except (FileNotFoundError, subprocess.CalledProcessError):
        logger.error("Node.js not found. Please install from https://nodejs.org/")
        sys.exit(1)
    
    # Install pa11y locally
    logger.info("Installing pa11y...")
    subprocess.run(['npm', 'install'], check=True)
    
    logger.info("Dependencies installed successfully!")
    logger.info("\nNote: veraPDF must be installed separately.")
    logger.info("Download from: https://verapdf.org/software/")


def run_export(config: PipelineConfig):
    """Run export stage."""
    exporter = CanvasExporter(config)
    export_path = exporter.export_course(config.output_dir)
    logger.info(f"Export complete: {export_path}")
    return export_path


def run_scan(config: PipelineConfig, input_path: Path):
    """Run scanning stage."""
    extractor = ContentExtractor(config)
    scanner = AccessibilityScanner(config)
    
    # Extract if IMSCC file
    if input_path.suffix.lower() in ['.imscc', '.zip']:
        extract_dir = config.output_dir / 'extracted'
        manifest = extractor.extract(input_path, extract_dir)
        content_dir = extract_dir
    else:
        content_dir = input_path
        manifest_file = content_dir / 'content_manifest.json'
        if manifest_file.exists():
            with open(manifest_file) as f:
                manifest = json.load(f)
        else:
            manifest = extractor.extract(input_path, content_dir)
    
    reports_dir = config.output_dir / 'reports'
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    # Run scans
    html_report = scanner.scan_html(content_dir, manifest, reports_dir)
    pdf_report = scanner.scan_pdfs(content_dir, manifest, reports_dir)
    
    return content_dir, manifest, html_report, pdf_report


def run_remediate(config: PipelineConfig, content_dir: Path, reports_dir: Path):
    """Run remediation stage."""
    generator = ClaudeRemediationGenerator(config)
    remediator = HTMLRemediator(config)
    
    # Load manifest
    manifest_file = content_dir / 'content_manifest.json'
    if manifest_file.exists():
        with open(manifest_file) as f:
            manifest = json.load(f)
    else:
        manifest = {'html_files': [], 'pdf_files': []}
    
    # Load reports
    html_report = {}
    pdf_report = {}
    
    html_report_file = reports_dir / 'pa11y_report.json'
    if html_report_file.exists():
        with open(html_report_file) as f:
            html_report = json.load(f)
    
    pdf_report_file = reports_dir / 'verapdf_report.json'
    if pdf_report_file.exists():
        with open(pdf_report_file) as f:
            pdf_report = json.load(f)
    
    remediation_dir = config.output_dir / 'remediation'
    remediation_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate remediation input for Claude
    remediation_input_file = generator.generate_remediation_input(
        content_dir, manifest, html_report, pdf_report, remediation_dir
    )
    
    # Apply automatic fixes
    auto_fixed_dir = config.output_dir / 'auto_fixed'
    auto_fixed_dir.mkdir(parents=True, exist_ok=True)
    
    with open(remediation_input_file) as f:
        remediation_input = json.load(f)
    
    fixes_report = remediator.apply_auto_fixes(content_dir, remediation_input, auto_fixed_dir)
    
    logger.info(f"Auto-fixes applied: {fixes_report['files_modified']} files modified")
    logger.info(f"Claude remediation input: {remediation_input_file}")
    
    return remediation_input_file


def run_full_pipeline(config: PipelineConfig):
    """Run complete pipeline."""
    logger.info("Starting full accessibility remediation pipeline...")
    
    # Check dependencies
    scanner = AccessibilityScanner(config)
    deps = scanner.check_dependencies()
    logger.info(f"Dependencies: {deps}")
    
    if not deps.get('pa11y'):
        logger.warning("pa11y not found - HTML scanning will be limited")
    
    # Export
    if config.canvas_url and config.canvas_token and config.course_id:
        export_path = run_export(config)
    else:
        logger.error("Canvas credentials required for full pipeline")
        sys.exit(1)
    
    # Scan
    content_dir, manifest, html_report, pdf_report = run_scan(config, export_path)
    
    # Generate remediation
    reports_dir = config.output_dir / 'reports'
    remediation_input_file = run_remediate(config, content_dir, reports_dir)
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("PIPELINE COMPLETE")
    logger.info("="*60)
    logger.info(f"Output directory: {config.output_dir}")
    logger.info(f"Extracted content: {config.output_dir / 'extracted'}")
    logger.info(f"Scan reports: {config.output_dir / 'reports'}")
    logger.info(f"Auto-fixed files: {config.output_dir / 'auto_fixed'}")
    logger.info(f"Claude remediation input: {remediation_input_file}")
    logger.info("\nNext steps:")
    logger.info("1. Review claude_remediation_input.json")
    logger.info("2. Use Claude with the accessibility skill to process remaining issues")
    logger.info("3. Apply Claude's fixes to the content")
    logger.info("4. Re-scan to verify remediation")


if __name__ == '__main__':
    main()
