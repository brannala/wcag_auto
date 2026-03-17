"""
Automated HTML accessibility fixes for Canvas course exports.

Each fix function takes a BeautifulSoup object and returns True if
the DOM was modified. Fixes are applied in a specific phase order
by the pipeline.
"""

import logging
import re
from bs4 import BeautifulSoup, NavigableString, Tag

logger = logging.getLogger(__name__)


# Phase 1: Structural template fixes (once per file)

def fix_language(soup: BeautifulSoup) -> bool:
    """Add lang="en" to <html> element if missing."""
    html_tag = soup.find('html')
    if html_tag and not html_tag.get('lang'):
        html_tag['lang'] = 'en'
        return True
    return False


def fix_title(soup: BeautifulSoup) -> bool:
    """Ensure <title> element exists and is non-empty."""
    head = soup.find('head')
    if not head:
        return False
    title_tag = soup.find('title')
    if title_tag and title_tag.string and title_tag.string.strip():
        return False  # title already present and non-empty
    # Try to generate title from h1
    h1 = soup.find('h1')
    if h1:
        title_text = h1.get_text(strip=True)
    else:
        title_text = 'Untitled Page'
    if title_tag:
        title_tag.string = title_text
    else:
        title_tag = soup.new_tag('title')
        title_tag.string = title_text
        head.append(title_tag)
    return True


def fix_main_landmark(soup: BeautifulSoup) -> bool:
    """Wrap <body> children in a <main> element if missing."""
    if soup.find('main'):
        return False
    body = soup.find('body')
    if not body:
        return False
    main_tag = soup.new_tag('main')
    children = list(body.children)
    if not children:
        return False
    for child in children:
        main_tag.append(child.extract())
    body.append(main_tag)
    return True


def fix_missing_h1(soup: BeautifulSoup) -> bool:
    """Add <h1> from <title> if page has no h1."""
    if soup.find('h1'):
        return False
    title_tag = soup.find('title')
    if not title_tag or not title_tag.string or not title_tag.string.strip():
        return False
    body = soup.find('body')
    if not body:
        return False
    h1 = soup.new_tag('h1')
    h1.string = title_tag.string.strip()
    # Insert at beginning of body (before main if present, else first child)
    main_tag = body.find('main')
    target = main_tag if main_tag else body
    if target.contents:
        target.contents[0].insert_before(h1)
    else:
        target.append(h1)
    return True


# Phase 2: List structure fixes

def fix_orphaned_list_items(soup: BeautifulSoup) -> bool:
    """Wrap <li> elements not inside <ul>/<ol> in a <ul>."""
    modified = False
    # Keep fixing until no orphans remain
    while True:
        orphan = None
        for li in soup.find_all('li'):
            if li.parent and li.parent.name not in ('ul', 'ol', 'menu'):
                orphan = li
                break
        if not orphan:
            break
        # Collect consecutive orphaned <li> siblings from this point
        group = [orphan]
        node = orphan.next_sibling
        while node is not None:
            if isinstance(node, NavigableString):
                if node.strip():
                    break  # non-whitespace text node ends the group
                node = node.next_sibling
                continue
            if isinstance(node, Tag) and node.name == 'li':
                group.append(node)
                node = node.next_sibling
            else:
                break
        # Wrap group in <ul>
        ul = soup.new_tag('ul')
        orphan.insert_before(ul)
        for item in group:
            ul.append(item.extract())
        modified = True
    return modified


# Phase 3: Content-level fixes

def fix_aria_hidden_focus(soup: BeautifulSoup) -> bool:
    """Add tabindex="-1" to focusable elements inside aria-hidden containers."""
    modified = False
    for container in soup.find_all(attrs={'aria-hidden': 'true'}):
        # Check if container itself is a focusable <a>
        if container.name == 'a' and container.get('href') is not None:
            if container.get('tabindex') != '-1':
                container['tabindex'] = '-1'
                modified = True
        # Check focusable descendants
        for a in container.find_all('a', href=True):
            if a.get('tabindex') != '-1':
                a['tabindex'] = '-1'
                modified = True
        for el in container.find_all(['button', 'input', 'select', 'textarea']):
            if el.get('tabindex') != '-1':
                el['tabindex'] = '-1'
                modified = True
    return modified


def fix_table_accessibility(soup: BeautifulSoup) -> bool:
    """Add scope attributes to <th> and <caption> to data tables."""
    modified = False
    for table in soup.find_all('table'):
        if table.get('role') == 'presentation':
            continue

        # Add scope="col" to <th> in <thead>
        thead = table.find('thead')
        if thead:
            for th in thead.find_all('th'):
                if not th.get('scope'):
                    th['scope'] = 'col'
                    modified = True
        else:
            # Check if first row is all <th> — promote to thead
            first_row = table.find('tr')
            if first_row:
                cells = first_row.find_all(['th', 'td'])
                th_cells = first_row.find_all('th')
                if cells and len(th_cells) == len(cells) and len(cells) > 1:
                    new_thead = soup.new_tag('thead')
                    first_row.extract()
                    new_thead.append(first_row)
                    # Insert thead at beginning of table (before tbody)
                    tbody = table.find('tbody')
                    if tbody:
                        tbody.insert_before(new_thead)
                    else:
                        table.insert(0, new_thead)
                    for th in th_cells:
                        if not th.get('scope'):
                            th['scope'] = 'col'
                    modified = True

        # Add <caption> if missing
        if not table.find('caption'):
            caption = soup.new_tag('caption')
            # Try to derive caption from preceding heading
            prev_heading = table.find_previous_sibling(re.compile(r'^h[1-6]$'))
            if prev_heading:
                caption.string = prev_heading.get_text(strip=True)
            else:
                caption.string = 'Data table'
            table.insert(0, caption)
            modified = True

    return modified


def fix_faux_headings(soup: BeautifulSoup) -> bool:
    """Convert <p><strong>text</strong></p> faux headings to proper heading tags.

    Only converts when <strong>/<b> is the sole meaningful child of <p>
    and the text looks like a heading (no colon, reasonable length).
    """
    modified = False
    # Collect candidates first to avoid modifying during iteration
    candidates = []
    for p in soup.find_all('p'):
        children = [c for c in p.children
                    if not (isinstance(c, NavigableString) and not c.strip())]
        if len(children) != 1:
            continue
        child = children[0]
        if not isinstance(child, Tag) or child.name not in ('strong', 'b'):
            continue
        text = child.get_text(strip=True)
        # Skip labeled paragraphs like "Time: 45 minutes"
        if ':' in text:
            continue
        # Skip very long text (not a heading)
        if len(text) > 100:
            continue
        # Skip very short text
        if len(text) < 3:
            continue
        candidates.append(p)

    for p in candidates:
        child = [c for c in p.children
                 if not (isinstance(c, NavigableString) and not c.strip())][0]
        text = child.get_text(strip=True)
        level = _determine_heading_level(soup, p)
        heading = soup.new_tag(f'h{level}')
        heading.string = text
        if p.get('id'):
            heading['id'] = p['id']
        p.replace_with(heading)
        modified = True

    return modified


def _determine_heading_level(soup: BeautifulSoup, element: Tag) -> int:
    """Determine appropriate heading level based on preceding headings."""
    prev_heading = element.find_previous(re.compile(r'^h[1-6]$'))
    if prev_heading:
        current_level = int(prev_heading.name[1])
        # Use same level as previous, or one level deeper
        # (faux headings are typically subsections)
        return min(current_level + 1, 6)
    return 2  # Default to h2


# Fix registry — ordered by phase

FIX_PHASES = [
    # Phase 1: Structural
    ('language', fix_language),
    ('title', fix_title),
    ('missing_h1', fix_missing_h1),
    ('main_landmark', fix_main_landmark),
    # Phase 2: List structure
    ('orphaned_lists', fix_orphaned_list_items),
    # Phase 3: Content-level
    ('aria_hidden_focus', fix_aria_hidden_focus),
    ('table_accessibility', fix_table_accessibility),
    ('faux_headings', fix_faux_headings),
]


def apply_all_fixes(soup: BeautifulSoup) -> list:
    """Apply all fixes in phase order. Returns list of fix names applied."""
    applied = []
    for name, fix_fn in FIX_PHASES:
        try:
            if fix_fn(soup):
                applied.append(name)
        except Exception as e:
            logger.warning(f"Fix '{name}' failed: {e}")
    return applied
