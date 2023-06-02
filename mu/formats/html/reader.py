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
        Parse the html content.

        The dispatch method is called recursively by the child `on_header` method.
        """
        yield from self.iter_units(self.unit_html)

    def iter_units(self, unit_html: BeautifulSoup) -> t.Iterable[units.Unit]:
        yield from super().dispatch(unit_html.name, unit_html)

    def on_header(self, unit_html: BeautifulSoup) -> t.Iterable[units.Unit]:
        """
        Parse `<h1>, ...<h6>` DOM elements.

        This method yields a single Collection for the current header. Headers from
        level n+1 will be added as children, provided they are direct children.

        This method is a little difficult to read. The problem with html headers is
        that they break the concept of parent -> child inclusion. So children in the
        sense of a course are actually siblings in the html world, and we need to figure
        out which ones are direct children of the current unit.
        """
        header_level = get_header_level(unit_html.name)
        assert header_level is not None

        # Create collection unit
        UnitClass = units.Course if header_level == 1 else units.Collection
        unit: units.Collection = UnitClass(
            attributes=get_data_attributes(unit_html),
            title=unit_html.string.strip(),
        )

        # Find children units.
        siblings_are_children = True
        for child_html in unit_html.find_next_siblings():
            if not getattr(child_html, "name"):
                # Ignore raw strings
                continue
            if child_header_level := get_header_level(child_html.name):
                # Header found: all other siblings are actually children of another unit
                if child_header_level < header_level:
                    # Child is actually a parent header: stop searching for children
                    # Parent header will be parsed in the parent call.
                    break
                elif child_header_level == header_level:
                    # Child is a header with the same level:
                    # Stop parsing and yield from a different parser.
                    break
                elif child_header_level == header_level + 1:
                    # Direct child -> will be appended to children
                    for child in self.iter_units(child_html):
                        unit.add_child(child)
                    # Other siblings are no longer children of this unit
                    siblings_are_children = False
                else:
                    # Child is a grand-child, so we ignore it
                    continue
            else:
                if siblings_are_children:
                    # Found a non-header unit: append to children
                    # (and concatenate RawHtml units in the process)
                    for child in self.iter_units(child_html):
                        if (
                            unit.children
                            and isinstance(unit.children[-1], units.RawHtml)
                            and isinstance(child, units.RawHtml)
                        ):
                            # Concatenate all RawHtml children
                            unit.children[-1].concatenate(child)
                        else:
                            # Append child
                            unit.add_child(child)

        # Yield current unit
        yield unit

    on_h1 = on_header
    on_h2 = on_header
    on_h3 = on_header
    on_h4 = on_header
    on_h5 = on_header
    on_h6 = on_header

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
        elif unit_type == "survey":
            # Survey questionaire
            yield from process_survey(unit_html)
        else:
            logger.warning("Unit type is unsupported by HTML reader: %s", unit_type)

    def _on_html(self, unit_html: BeautifulSoup) -> t.Iterable[units.Unit]:
        """
        All data-* attributes are copied to the RawHtml unit.
        """
        yield units.RawHtml(
            contents=str(unit_html),
            attributes=get_data_attributes(unit_html),
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


def get_data_attributes(unit_html: BeautifulSoup) -> t.Dict[str, str]:
    """
    Return all attributes that start with "data-"
    """
    return {
        key[5:]: value
        for key, value in unit_html.attrs.items()
        if key.startswith("data-")
    }


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


def process_survey(unit_html: BeautifulSoup) -> t.Iterable[units.Unit]:
    title, questions, answers = get_questions_answers(unit_html)
    feedback = unit_html.find("code").string.strip() if unit_html.find("code") else ""
    yield units.Survey(
        title=title,
        questions=questions,
        answers=answers,
        feedback=feedback,
        attributes={
            attr.replace("data-", "", 1): val
            for attr, val in unit_html.find(re.compile("^h[1-6]$")).attrs.items()
        },
    )


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


def get_questions_answers(
    unit_html: BeautifulSoup,
) -> t.Tuple[str, t.List[str], t.List[str]]:
    title = ""
    if title_html := find_title(unit_html):
        title = title_html.string

    answers = []

    ul_html = unit_html.find("ul")
    if ul_html is None:
        raise MuError(f"Missing <ul> element in multiple choice question: {unit_html}")
    for li_html in ul_html.find_all("li"):
        answer = li_html.string.strip()
        answers.append(answer.strip())

    questions = []
    for q in unit_html.findAll("p"):
        if "code" not in [c.name for c in q.children]:
            questions.append(q.string.strip())
    if len(questions) < 1:
        raise MuError(f"Missing <p> element in survey: {unit_html}")
    return title, questions, answers


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
