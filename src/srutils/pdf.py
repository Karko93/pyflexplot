"""Work with PDF files."""
# Standard library
import dataclasses as dc
import os
from typing import List

# Third-party
from PyPDF2 import PdfFileReader
from PyPDF2 import PdfFileWriter
from PyPDF2.pdf import PageObject
from PyPDF2.utils import PdfReadError


@dc.dataclass
class MultiPagePDF:
    """A multi-page PDF file composed of multiple individual PDF files."""

    pages: List[PageObject]

    def write(self, path: str) -> None:
        """Write the file to disk."""
        writer = PdfFileWriter()
        for page in self.pages:
            writer.addPage(page)
        dir_path = os.path.dirname(path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(path, "wb") as fo:
            writer.write(fo)

    @staticmethod
    def _read_pages(paths: List[str]) -> List[PageObject]:
        """Read pages from disk."""
        pages: List[PageObject] = []
        for path_i in paths:
            try:
                file = PdfFileReader(path_i)
            except (ValueError, TypeError, PdfReadError) as e:
                # Occur sporadically; likely a file system issue
                raise PdfReadError(path_i) from e
            page = file.getPage(0)
            pages.append(page)
        return pages

    @classmethod
    def from_files(cls, paths: List[str]) -> "MultiPagePDF":
        pages = cls._read_pages(paths)
        return cls(pages)