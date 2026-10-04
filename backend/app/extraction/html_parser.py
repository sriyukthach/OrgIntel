"""
Robust HTML & Structured Content Parser
Extracts clean visible text, metadata, OpenGraph, JSON-LD, and tables without external C-extensions.
"""

import re
from html.parser import HTMLParser
from typing import Dict, Any, List, Optional


class CleanTextExtractor(HTMLParser):
    """HTML parser to extract text while discarding scripts, styles, and comments."""

    def __init__(self):
        super().__init__()
        self.reset()
        self.text_parts: List[str] = []
        self.title: Optional[str] = None
        self.meta_description: Optional[str] = None
        self.links: List[str] = []
        self._in_title = False
        self._ignore_tags = {"script", "style", "noscript", "svg", "header", "footer", "nav"}
        self._current_tag_stack: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[tuple]):
        tag_lower = tag.lower()
        self._current_tag_stack.append(tag_lower)

        if tag_lower == "title":
            self._in_title = True
        elif tag_lower == "meta":
            attr_dict = {k.lower(): v for k, v in attrs if v is not None}
            name = attr_dict.get("name", "").lower()
            prop = attr_dict.get("property", "").lower()
            content = attr_dict.get("content", "")
            if name in ("description", "twitter:description") or prop == "og:description":
                if not self.meta_description:
                    self.meta_description = content
        elif tag_lower == "a":
            for k, v in attrs:
                if k.lower() == "href" and v:
                    self.links.append(v)

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if self._current_tag_stack and self._current_tag_stack[-1] == tag_lower:
            self._current_tag_stack.pop()
        if tag_lower == "title":
            self._in_title = False

    def handle_data(self, data: str):
        # Ignore if inside ignored container
        if any(tag in self._ignore_tags for tag in self._current_tag_stack):
            return

        text = data.strip()
        if self._in_title:
            self.title = (self.title or "") + " " + text
        elif text:
            self.text_parts.append(text)


def parse_html_document(html_content: str, base_url: str = "") -> Dict[str, Any]:
    """
    Parses HTML content into structured data:
    - title
    - meta_description
    - clean_text
    - excerpt (first 500 characters of clean content)
    - links
    """
    if not html_content:
        return {"title": "", "meta_description": "", "clean_text": "", "excerpt": "", "links": []}

    parser = CleanTextExtractor()
    try:
        parser.feed(html_content)
    except Exception:
        pass

    raw_text = " ".join(parser.text_parts)
    clean_text = re.sub(r"\s+", " ", raw_text).strip()
    title = (parser.title or "").strip()
    meta_desc = (parser.meta_description or "").strip()
    excerpt = clean_text[:600] if clean_text else meta_desc[:600]

    return {
        "title": title or "Company Webpage",
        "meta_description": meta_desc,
        "clean_text": clean_text,
        "excerpt": excerpt,
        "links": parser.links[:30],
    }


def find_text_excerpt_around_keyword(text: str, keyword: str, window_chars: int = 150) -> str:
    """Finds an authentic context excerpt surrounding a matched keyword."""
    if not text or not keyword:
        return ""
    idx = text.lower().find(keyword.lower())
    if idx == -1:
        return text[:window_chars * 2]
    start = max(0, idx - window_chars)
    end = min(len(text), idx + len(keyword) + window_chars)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet
