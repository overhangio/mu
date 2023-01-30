import subprocess

from lecture.formats.html.reader import DocumentReader, beautiful_soup


class Reader(DocumentReader):
    @classmethod
    def create(cls, path: str) -> "Reader":
        """
        Same as an HTML reader, but convert from markdown at runtime.
        """
        # Convert markdown to html with Pandoc
        # TODO check whether pandoc is installed
        html_content = subprocess.check_output(
            ["pandoc", "--from=markdown", "--to=html5", path]
        ).decode()

        # Load html
        html = beautiful_soup(html_content)

        # Trim all <p> tags surrounding videos
        # TODO test this
        for video_html in html.find_all("video"):
            if video_html.parent and video_html.parent.name == "p":
                video_html.parent.replace_with_children()

        return cls(html)
