import shutil
import subprocess
import tempfile

from mu.exceptions import MuError
from mu.formats.html.reader import DocumentReader, beautiful_soup


class Reader(DocumentReader):
    def __init__(self, path: str) -> None:
        """
        Same as an HTML reader, but convert from markdown at runtime.
        """
        # Convert markdown to html with Pandoc
        try:
            html_content = subprocess.check_output(
                ["pandoc", "--from=markdown", "--to=html5", path]
            ).decode()
        except FileNotFoundError as e:
            if shutil.which("pandoc") is None:
                raise MuError("pandoc must be installed to read from Markdown.") from e

        # Load html
        html = beautiful_soup(html_content)

        # Trim all <p> tags surrounding videos
        # Note: as far as I know, we no longer need to do this
        # for video_html in html.find_all("video"):
        #     if video_html.parent and video_html.parent.name == "p":
        #         video_html.parent.replace_with_children()

        super().__init__(html)


class StringReader(Reader):
    """
    Same as reader, but read from raw string. Convenient for unit testing.
    """

    def __init__(self, content: str) -> None:
        with tempfile.NamedTemporaryFile("w") as of:
            of.write(content)
            of.flush()
            super().__init__(of.name)
