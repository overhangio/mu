import os

from bs4 import BeautifulSoup
from bs4.element import Tag

from lecture import units
from lecture.formats.base.writer import Writer as BaseWriter
from lecture.utils import youtube


def dump(course: units.Course, path: str) -> None:
    writer = StyledWriter()
    writer.write(course)
    writer.write_to(path)


class Writer(BaseWriter):
    def __init__(self) -> None:
        self.document = beautiful_soup("<!DOCTYPE html>")

    def write_to(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.dumps())

    def dumps(self) -> str:
        # Convenience method
        contents: str = self.document.decode(pretty_print=True)
        return contents

    def append_to_body(self, tag: Tag) -> None:
        self.document.html.body.append(tag)

    def on_unit(self, unit: units.Unit) -> None:
        if title := unit.title:
            tag = Tag(
                name=f"h{unit.depth + 1}",
                attrs={f"data-{k}": v for k, v in unit.attributes.items()},
            )
            tag.string = title
            self.append_to_body(tag)

    def on_course(self, unit: units.Course) -> None:
        self.on_unit(unit)

    def on_multiplechoicequestion(self, unit: units.MultipleChoiceQuestion) -> None:
        self.on_unit(unit)

        # Write question
        answers_html = Tag(name="ul")
        question_html = Tag(name="li")
        question_html.string = unit.question
        answers_html.append(question_html)
        # Write answers
        for answer, is_correct in unit.answers:
            answer_html = Tag(name="li")
            answer_html.string = f"{'✅' if is_correct else '❌'} {answer}"
            answers_html.append(answer_html)
        self.append_to_body(answers_html)

    def on_video(self, unit: units.Video) -> None:
        """
        We parse the video sources. If one is youtube, we include a youtube iframe.
        Else, we include a <video> element.
        TODO
        """
        self.on_unit(unit)
        # TODO handle transcripts
        video_tag = Tag(name="video", attrs={"controls": None})
        youtube_video_tag = None
        for source in unit.sources:
            if youtube_embed_url := youtube.get_embed_url(source):
                youtube_video_tag = Tag(
                    name="iframe",
                    attrs={"src": youtube_embed_url},
                )
            else:
                video_extension = os.path.splitext(source)[1].lower()
                video_type = {
                    ".mp4": "mp4",
                    ".mov": "mp4",
                    ".ogg": "ogg",
                    ".webm": "webm",
                }.get(video_extension)
                if video_type:
                    video_tag.append(
                        Tag(
                            name="source",
                            attrs={"src": source, "type": f"video/{video_type}"},
                        )
                    )
        self.append_to_body(youtube_video_tag or video_tag)

    def on_rawhtml(self, unit: units.RawHtml) -> None:
        self.append_to_body(BeautifulSoup(unit.contents, "html.parser"))


class StyledWriter(Writer):
    """
    Add some basic CSS styling to the default writer.
    """

    def on_course(self, unit: units.Course) -> None:
        super().on_course(unit)
        css = Tag(name="style")
        css.string = """
body {
    max-width: 1024px;
    margin: auto;
    font-family: sans-serif;
}

video {
    width: 800px;
}

iframe {
    width: 800px;
    height: 450px;
}
"""
        self.document.html.head.append(css)


def beautiful_soup(contents: str) -> BeautifulSoup:
    return BeautifulSoup(contents, "html5lib")
