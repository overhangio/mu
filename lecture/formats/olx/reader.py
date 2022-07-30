import io
import logging
import os
import re
import typing as t

from bs4 import BeautifulSoup

from lecture import units
from lecture.exceptions import LectureError
from lecture.formats.base.reader import Reader as BaseReader
from lecture.utils import youtube

logger = logging.getLogger(__file__)


def load(root_directory: str) -> units.Course:
    """
    TODO error management
    """
    reader = FilesystemReader(root_directory)
    course = reader.read()
    if not isinstance(course, units.Course):
        # TODO this error management should happen in the BaseReader class
        raise LectureError("Failed to parse course object in XML file")
    return course


class Reader(BaseReader):
    def __init__(self, unit_xml: BeautifulSoup) -> None:
        # TODO error management
        # if not (course_xml := getattr(document, "course")):
        # raise LectureError("Missing top-level course attribute in XML file")
        self.unit_xml = unit_xml

    def get_child_reader(self, child_xml: BeautifulSoup) -> "Reader":
        return Reader(child_xml)

    def parse(self) -> t.Iterable[units.Unit]:
        # We skip name-less children, such as 'NavigableString'
        if not getattr(self.unit_xml, "name", None):
            return

        # Dispatch call to on_* functions
        for unit in self.dispatch(self.unit_xml.name, self.unit_xml):
            # Parse children
            for child_xml in self.unit_xml.children:
                reader = self.get_child_reader(child_xml)
                for child in reader.parse():
                    unit.add_child(child)
            yield unit

    def on_course(self, unit_xml: BeautifulSoup) -> t.Iterable[units.Unit]:
        yield units.Course(
            get_unit_attributes(unit_xml), title=unit_xml.attrs.get("display_name", "")
        )

    def on_chapter(self, unit_xml: BeautifulSoup) -> t.Iterable[units.Unit]:
        yield units.Unit(
            get_unit_attributes(unit_xml), title=unit_xml.attrs.get("display_name", "")
        )

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

    def on_sequential(self, unit_xml: BeautifulSoup) -> t.Iterable[units.Unit]:
        yield units.Unit(
            get_unit_attributes(unit_xml), title=unit_xml.attrs.get("display_name", "")
        )

    def on_vertical(self, unit_xml: BeautifulSoup) -> t.Iterable[units.Unit]:
        yield units.Unit(
            get_unit_attributes(unit_xml), title=unit_xml.attrs.get("display_name", "")
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


class StringReader(Reader):
    def __init__(self, contents: str) -> None:
        super().__init__(beautiful_soup(contents))


class FilesystemReader(Reader):
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
                raise LectureError(
                    "Badly formatted course.xml file: missing <course> element"
                )
            unit_xml = unit_xml.course

        # Load xml from file pointed by url_name
        if url_name := getattr(unit_xml, "attrs", {}).get("url_name"):
            url_name_path = os.path.join(
                self.root_directory, unit_xml.name, f"{url_name}.xml"
            )
            if not os.path.exists(url_name_path):
                # TODO should we really just ignore this file?
                logger.warning(
                    "Failed to load unit. File does not exist: %s", url_name_path
                )
            else:
                new_unit_xml = getattr(load_xml(url_name_path), unit_xml.name)
                # TODO error management
                # What to do when the loaded element has no child with the selected name?
                if new_unit_xml is not None:
                    new_unit_xml.attrs["url_name"] = url_name
                    # Copy attributes from source element
                    new_unit_xml.attrs.update(unit_xml.attrs)
                    # Replace source element
                    unit_xml = new_unit_xml

        super().__init__(unit_xml)

    def get_child_reader(self, child_xml: BeautifulSoup) -> "FilesystemReader":
        return FilesystemReader(self.root_directory, child_xml)


def load_xml(path: str) -> BeautifulSoup:
    if not os.path.isfile(path):
        raise LectureError(f"Missing XML file: '{path}'")
    with open(path, encoding="utf-8") as f:
        return beautiful_soup(f)


def beautiful_soup(src: t.Union[str, io.TextIOBase]) -> BeautifulSoup:
    return BeautifulSoup(src, "xml")
