import io
import logging
import os
import re
import typing as t

from bs4 import BeautifulSoup

from mu import units
from mu.exceptions import MuError
from mu.formats.base.reader import BaseReader
from mu.utils import youtube

logger = logging.getLogger(__name__)


class InlineReader(BaseReader):
    # pylint: disable=super-init-not-called
    def __init__(self, unit_xml: BeautifulSoup) -> None:
        self.unit_xml = unit_xml

    def get_child_reader(self, child_xml: BeautifulSoup) -> "InlineReader":
        return InlineReader(child_xml)

    def parse(self) -> t.Iterable[units.Unit]:
        # We skip name-less children, such as 'NavigableString'
        if not getattr(self.unit_xml, "name", None):
            return

        # Dispatch call to on_* functions
        yield from self.dispatch(self.unit_xml.name, self.unit_xml)

    def parse_children(self) -> t.Iterable[units.Unit]:
        # Parse children
        for child_xml in self.unit_xml.children:
            reader = self.get_child_reader(child_xml)
            yield from reader.parse()

    def _on_collection(
        self, unit_xml: BeautifulSoup, collection: t.Optional[units.Collection] = None
    ) -> t.Iterable[units.Unit]:
        """
        Dispatch function for course, chapter, sequential and vertical units.
        """
        if collection is None:
            collection = units.Collection(
                get_unit_attributes(unit_xml),
                title=unit_xml.attrs.get("display_name", ""),
            )
        for child in self.parse_children():
            collection.add_child(child)
        yield collection

    def on_course(self, unit_xml: BeautifulSoup) -> t.Iterable[units.Unit]:
        course = units.Course(
            get_unit_attributes(unit_xml), title=unit_xml.attrs.get("display_name", "")
        )
        yield from self._on_collection(unit_xml, course)

    on_chapter = _on_collection
    on_sequential = _on_collection
    on_vertical = _on_collection

    def on_problem(self, unit_xml: BeautifulSoup) -> t.Iterable[units.Unit]:
        """
        https://edx.readthedocs.io/projects/edx-open-learning-xml/en/latest/problem-xml/checkbox.html
        https://edx.readthedocs.io/projects/edx-open-learning-xml/en/latest/problem-xml/text_input.html
        """
        # Parse question
        question_xml = unit_xml.find("label")
        question = question_xml.string if question_xml else ""

        if response_xml := unit_xml.find("choiceresponse"):
            # Multiple choice question
            yield units.MultipleChoiceQuestion(
                title=unit_xml.attrs.get("display_name", ""),
                question=question,
                answers=[
                    (
                        answer_xml.string,
                        answer_xml.attrs.get("correct", "").lower() == "true",
                    )
                    for answer_xml in response_xml.find_all("choice")
                ],
            )
        elif response_xml := unit_xml.find("stringresponse"):
            # Free text question
            ftq_answers = []
            ftq_answers.append(response_xml.attrs["answer"])
            for answer_xml in response_xml.find_all("additional_answer"):
                ftq_answers.append(answer_xml.attrs["answer"])
            yield units.FreeTextQuestion(
                title=unit_xml.attrs.get("display_name", ""),
                question=question,
                answers=ftq_answers,
            )

    def on_html(self, unit_xml: BeautifulSoup) -> t.Iterable[units.Unit]:
        """
        https://edx.readthedocs.io/projects/edx-open-learning-xml/en/latest/components/html-components.html
        """
        contents = "\n".join([str(c) for c in unit_xml.contents])
        yield units.RawHtml(
            title=unit_xml.attrs.get("display_name", ""), contents=contents
        )

    def on_video(self, unit_xml: BeautifulSoup) -> t.Iterable[units.Unit]:
        """
        https://edx.readthedocs.io/projects/edx-open-learning-xml/en/latest/components/video-components.html
        """
        sources: t.List[str] = []
        if youtube_id := unit_xml.attrs.get("youtube_id_1_0"):
            sources.append(youtube.get_watch_url(youtube_id))
        elif youtube_id := unit_xml.attrs.get("youtube"):
            # Format: 1.00:<id>,2.5:<id>,...
            # We only look for the single speed video
            # Some videos only include a 'youtube' attribute, but no 'youtube_id_1_0'.
            if youtube_id_match := re.match(r"1(\.00)?:(?P<id>.+)", youtube_id):
                sources.append(youtube.get_watch_url(youtube_id_match.group("id")))
        for source_xml in unit_xml.find_all("source"):
            if source := source_xml.attrs.get("src"):
                sources.append(source)
        yield units.Video(
            get_unit_attributes(unit_xml),
            title=unit_xml.attrs.get("display_name", ""),
            sources=sources,
        )


class StringReader(InlineReader):
    """
    Reader for xml-formatted strings.

    Convenient for unit testing.
    """

    def __init__(self, contents: str) -> None:
        super().__init__(beautiful_soup(contents).find())


class Reader(InlineReader):
    """
    This reader can load xml files indicated by the `url_name` property. In such
    cases, the "url_name" will be stored among the unit attributes.
    """

    def __init__(
        self, root_directory: str, unit_xml: t.Optional[BeautifulSoup] = None
    ) -> None:
        self.root_directory = root_directory
        if unit_xml is None:
            # Load course.xml from file
            unit_xml = load_xml(os.path.join(self.root_directory, "course.xml"))
            if not hasattr(unit_xml, "course"):
                raise MuError(
                    "Badly formatted course.xml file: missing <course> element"
                )
            unit_xml = unit_xml.course

        # Load xml from file pointed by url_name
        if url_name := getattr(unit_xml, "attrs", {}).get("url_name"):
            url_name_path = os.path.join(
                self.root_directory, unit_xml.name, f"{url_name}.xml"
            )
            if not os.path.exists(url_name_path):
                logger.warning(
                    "Failed to load unit. File does not exist: %s", url_name_path
                )
            else:
                new_unit_xml = getattr(load_xml(url_name_path), unit_xml.name)
                if new_unit_xml is None:
                    raise MuError(
                        f"Element with name '{unit_xml.name}' could not be found in {url_name_path}"
                    )
                new_unit_xml.attrs["url_name"] = url_name
                # Copy attributes from source element
                new_unit_xml.attrs.update(unit_xml.attrs)
                # Replace source element
                unit_xml = new_unit_xml

        super().__init__(unit_xml)

    def get_child_reader(self, child_xml: BeautifulSoup) -> "Reader":
        return Reader(self.root_directory, child_xml)


def get_unit_attributes(unit_xml: BeautifulSoup) -> t.Dict[str, t.Any]:
    """
    Call this function in your custom `on_*` methods to get a dict of OLX key/value
    attributes to be added to the created unit.
    """
    attributes = {}
    for k, v in unit_xml.attrs.items():
        attributes[f"olx-{k}"] = v
    attributes["olx-type"] = unit_xml.name
    return attributes


def load_xml(path: str) -> BeautifulSoup:
    if not os.path.isfile(path):
        raise MuError(f"Missing XML file: '{path}'")
    with open(path, encoding="utf-8") as f:
        return beautiful_soup(f)


def beautiful_soup(src: t.Union[str, io.TextIOBase]) -> BeautifulSoup:
    return BeautifulSoup(src, "xml")
