import io
import logging
import re
import typing as t

from bs4 import BeautifulSoup

from mu import units
from mu.exceptions import MuError
from mu.formats.base.reader import BaseReader
from mu.utils import youtube

from .common import TYPE_ATTR

logger = logging.getLogger(__name__)


class HtmlReader(BaseReader):
    # pylint: disable=super-init-not-called
    def __init__(self, unit_html: BeautifulSoup) -> None:
        self.unit_html = unit_html

    def parse(self) -> t.Iterable[units.Unit]:
        """
        In this method we only detect the headers. Parsing the actual content of each
        unit is done in the `on_header` method.

        This method is called recursively.
        """
        header_level = None
        if getattr(self.unit_html, "name"):
            header_level = get_header_level(self.unit_html.name)

        # Parse html
        for unit in self.dispatch(self.unit_html.name, self.unit_html):
            # Find the next header from which we start parsing again
            for next_html in self.unit_html.find_next_siblings():
                if next_header_level := get_header_level(next_html.name):
                    if header_level is None:
                        # Current unit did not have a header
                        break
                    if next_header_level == header_level + 1:
                        # Next level, create a child reader, parse
                        child_reader = HtmlReader(next_html)
                        for child in child_reader.parse():
                            unit.add_child(child)
                    elif next_header_level <= header_level:
                        # We found a header with the same level or a parent unit. All
                        # subsequent items belong to it. We stop parsing.
                        break
            # Unit is yielded after we have added its children
            yield unit

    def on_section(self, unit_html: BeautifulSoup) -> t.Iterable[units.Unit]:
        """
        Parse `<section>` DOM elements.

        The parsing function that is called depends on the value of the
        "data-mu-type" attribute.
        """
        unit_type = unit_html.attrs.get(TYPE_ATTR)
        if unit_type == "mcq":
            # Multiple choice question
            yield from process_mcq(unit_html)
        elif unit_type == "video":
            yield from process_video(unit_html)
        elif unit_type == "ftq":
            # Free text question
            yield from process_ftq(unit_html)
        else:
            logger.warning("Unit type is unsupported by HTML reader: %s", unit_type)

    def on_header(self, unit_html: BeautifulSoup) -> t.Iterable[units.Unit]:
        """
        Parse `<h1>, ...<h6>` DOM elements.
        """
        # Create unit
        UnitClass = units.Course if unit_html.name == "h1" else units.Unit
        attributes = {
            k[5:]: v for k, v in unit_html.attrs.items() if k.startswith("data-")
        }
        unit: units.Unit = UnitClass(attributes, title=self.unit_html.string.strip())

        # Find children
        children = []
        for child_html in unit_html.find_next_siblings():
            if not getattr(child_html, "name"):
                # Skip raw string
                continue
            elif get_header_level(child_html.name) is not None:
                # Child is a header: stop processing
                break
            for child in self.dispatch(child_html.name, child_html):
                children.append(child)

        for child in children:
            if (
                isinstance(child, units.RawHtml)
                and unit.children
                and isinstance(unit.children[-1], units.RawHtml)
            ):
                # Concatenate all RawHtml children
                unit.children[-1].concatenate(child)
            else:
                # Append child
                unit.add_child(child)

        yield unit

    on_h1 = on_header
    on_h2 = on_header
    on_h3 = on_header
    on_h4 = on_header
    on_h5 = on_header
    on_h6 = on_header

    def _on_html(self, unit_html: BeautifulSoup) -> t.Iterable[units.Unit]:
        """
        All data-* attributes are copied to the RawHtml unit.
        """
        yield units.RawHtml(
            contents=str(unit_html),
            attributes={
                key: value
                for key, value in unit_html.attrs.items()
                if key.startswith("data-")
            },
        )

    # Add here all html elements that should be converted to RawHtml
    on_div = _on_html
    on_p = _on_html
    on_pre = _on_html
    on_video = _on_html


class DocumentReader(HtmlReader):
    """
    Same as Reader, but build reader from top-level h1 header.
    """

    def __init__(self, document: BeautifulSoup) -> None:
        if h1 := document.find(name="h1"):
            super().__init__(h1)
        else:
            raise MuError("Could not find any h1 element in the HTML document")


class StringReader(DocumentReader):
    """
    Same as DocumentReader, but for html-formatted strings.

    Convenient for unit testing.
    """

    def __init__(self, contents: str) -> None:
        super().__init__(beautiful_soup(contents))


class Reader(StringReader):
    """
    Same as StringReader, but with a constructor that takes a file object as argument.
    """

    def __init__(self, path: str) -> None:
        with open(path, encoding="utf8") as f:
            super().__init__(f.read())


def get_header_level(h: str) -> t.Optional[int]:
    """
    Parse the header level: "hX" -> X

    Return None in case of no match.
    """
    match = re.match(r"h([1-9])", h)
    if not match:
        return None
    return int(match.group(1))


def process_mcq(unit_html: BeautifulSoup) -> t.Iterable[units.Unit]:
    """
    <ul> tags may contain multiple choice questions. In such cases, the first <li>
    is the question and each subsequent <li> element starts with either ✅ or ❌.
    """
    title, question, answers = get_question_answers(unit_html)
    right = "✅"
    wrong = "❌"
    evaluated_answers = []
    for answer in answers:
        is_correct = False
        if answer.startswith(right):
            is_correct = True
        elif answer.startswith(wrong):
            is_correct = False
        else:
            # Not a multiple choice question
            raise MuError(
                f"Incorrectly formatted answer in multiple choice question: "
                f"should start with either {right} or {wrong}"
            )
        evaluated_answers.append((answer[1:].strip(), is_correct))

    # Generate MCQ
    yield units.MultipleChoiceQuestion(
        title=title,
        question=question,
        answers=evaluated_answers,
    )


def process_ftq(unit_html: BeautifulSoup) -> t.Iterable[units.Unit]:
    title, question, answers = get_question_answers(unit_html)
    yield units.FreeTextQuestion(title=title, question=question, answers=answers)


def process_video(unit_html: BeautifulSoup) -> t.Iterable[units.Unit]:
    """
    https://developer.mozilla.org/en-US/docs/Web/HTML/Element/video
    """
    title = ""
    if title_html := find_title(unit_html):
        title = title_html.string

    video_html = unit_html.find("video")
    iframe_html = unit_html.find("iframe")
    if video_html is None and iframe_html is None:
        raise MuError(
            f"Missing <video> or <iframe> element in unit labelled as video: {unit_html}"
        )

    if video_html:
        sources: t.List[str] = []
        if src := video_html.attrs.get("src"):
            sources.append(src)
        for source_html in video_html.find_all("source"):
            if source := source_html.attrs.get("src"):
                if source not in sources:
                    sources.append(source)
        yield units.Video(title=title, sources=sources)
    else:
        src = iframe_html.attrs.get("src")
        if youtube_video_id := youtube.get_embed_video_id(src):
            yield units.Video(
                title=title, sources=[youtube.get_watch_url(youtube_video_id)]
            )


def get_question_answers(unit_html: BeautifulSoup) -> t.Tuple[str, str, t.List[str]]:
    title = ""
    if title_html := find_title(unit_html):
        title = title_html.string

    question: t.Optional[str] = None
    answers = []
    question_html = unit_html.find("p")
    if question_html is None:
        raise MuError(f"Missing <p> element in multiple choice question: {unit_html}")
    question = question_html.string.strip()
    if question is None:
        raise MuError(
            f"Missing question string in multiple choice question: {unit_html}"
        )
    ul_html = unit_html.find("ul")
    if ul_html is None:
        raise MuError(f"Missing <ul> element in multiple choice question: {unit_html}")
    for li_html in ul_html.find_all("li"):
        answer = li_html.string.strip()
        answers.append(answer.strip())

    return title, question, answers


def find_title(unit_html: BeautifulSoup) -> t.Optional[BeautifulSoup]:
    return unit_html.find(
        [
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        ]
    )


def beautiful_soup(src: t.Union[str, io.TextIOBase]) -> BeautifulSoup:
    return BeautifulSoup(src, "html5lib")
