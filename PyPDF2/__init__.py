"""Minimal local PyPDF2 shim for unit tests.

The forensics tests patch ``PyPDF2.PdfReader`` and ``PyPDF2.PdfWriter``.
In this environment the dependency is not installed, so the patch target
must still be importable.
"""


class PdfReader:
    """Placeholder PdfReader implementation for tests that monkeypatch it."""

    def __init__(self, *_args, **_kwargs):
        self.pages = []


class PdfWriter:
    """Placeholder PdfWriter implementation for tests that monkeypatch it."""

    def __init__(self, *_args, **_kwargs):
        self.pages = []

    def add_page(self, page):
        self.pages.append(page)
