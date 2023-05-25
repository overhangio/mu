import logging
import os

from bs4 import BeautifulSoup
from bs4.element import Tag

from mu import units
from mu.formats.base.writer import BaseWriter
from mu.utils import youtube

from .common import TYPE_ATTR

logger = logging.getLogger(__name__)


class UnstyledWriter(BaseWriter):
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

    def get_header(self, unit: units.Unit) -> Tag:
        tag = Tag(
            name=f"h{unit.depth + 1}",
            attrs={f"data-{k}": v for k, v in unit.attributes.items()},
        )
        if title := unit.title:
            tag.string = title
        return tag

    def on_collection(self, unit: units.Collection) -> None:
        self.append_to_body(self.get_header(unit))

    def on_course(self, unit: units.Course) -> None:
        self.append_to_body(self.get_header(unit))

    def on_multiplechoicequestion(self, unit: units.MultipleChoiceQuestion) -> None:
        section_html = Tag(name="section", attrs={TYPE_ATTR: "mcq"})

        # Write title
        section_html.append(self.get_header(unit))

        # Write question
        question_html = Tag(name="p")
        question_html.string = unit.question
        section_html.append(question_html)
        answers_html = Tag(name="ul")

        # Write answers
        for answer, is_correct in unit.answers:
            answer_html = Tag(name="li")
            answer_html.string = f"{'✅' if is_correct else '❌'} {answer}"
            answers_html.append(answer_html)
        section_html.append(answers_html)

        self.append_to_body(section_html)

    def on_freetextquestion(self, unit: units.FreeTextQuestion) -> None:
        section_html = Tag(name="section", attrs={TYPE_ATTR: "ftq"})

        # Write title
        section_html.append(self.get_header(unit))

        # Write question
        question_html = Tag(name="p")
        question_html.string = unit.question
        section_html.append(question_html)
        answers_html = Tag(name="ul")

        # Write answers
        for answer, _ in unit.answers:
            answer_html = Tag(name="li")
            answer_html.string = answer
            answers_html.append(answer_html)
        section_html.append(answers_html)

        self.append_to_body(section_html)

    def on_survey(self, unit: units.Survey) -> None:
        section_html = Tag(name="section", attrs={TYPE_ATTR: "survey"})

        # Write title
        section_html.append(self.get_header(unit))

        # Write questions
        for question in unit.questions:
            question_html = Tag(name="p")
            question_html.string = question
            section_html.append(question_html)

        answers_html = Tag(name="ul")

        # Write answers
        for answer in unit.answers:
            answer_html = Tag(name="li")
            answer_html.string = answer
            answers_html.append(answer_html)
        section_html.append(answers_html)

        # Write Feedback
        feedback_html = Tag(name="code")
        feedback_html.string = unit.feedback
        section_html.append(feedback_html)

        self.append_to_body(section_html)

    def on_poll(self, unit: units.Poll) -> None:
        section_html = Tag(name="section", attrs={TYPE_ATTR: "poll"})

        # Write title
        section_html.append(self.get_header(unit))

        # Write question
        question_html = Tag(name="p")
        question_html.string = unit.question
        section_html.append(question_html)

        answers_html = Tag(name="ul")

        # Write answers
        for answer in unit.answers:
            answer_html = Tag(name="li")
            answer_html.string = answer
            answers_html.append(answer_html)
        section_html.append(answers_html)

        # Write Feedback
        feedback_html = Tag(name="code")
        feedback_html.string = unit.feedback
        section_html.append(feedback_html)

        self.append_to_body(section_html)

    def on_video(self, unit: units.Video) -> None:
        """
        We parse the video sources. If one is youtube, we include a youtube iframe.
        Else, we include a <video> element.
        """
        section_html = Tag(name="section", attrs={TYPE_ATTR: "video"})

        # Write title
        section_html.append(self.get_header(unit))

        # TODO handle transcripts
        video_tag = get_video_tag(unit.sources)
        section_html.append(video_tag)
        self.append_to_body(section_html)

    def on_rawhtml(self, unit: units.RawHtml) -> None:
        self.append_to_body(BeautifulSoup(unit.contents, "html.parser"))


class Writer(UnstyledWriter):
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


def get_video_tag(sources: list[str]) -> BeautifulSoup:
    """
    Return either a <video> or <iframe> element based on the video sources.
    """
    video_tag = Tag(name="video", attrs={"controls": None})
    for source in sources:
        if youtube_embed_url := youtube.get_embed_url(source):
            # Video url points to youtube. In such a case, we don't return a <video> but an iframe.
            return Tag(
                name="iframe",
                attrs={"src": youtube_embed_url},
            )
        # Video is standard html5
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
        else:
            logger.warning("Unsupported video extension: %s", video_extension)
    return video_tag


def beautiful_soup(contents: str) -> BeautifulSoup:
    return BeautifulSoup(contents, "html5lib")
