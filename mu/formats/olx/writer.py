import hashlib
import logging
import os
import typing as t

from bs4 import BeautifulSoup, Tag

from mu import units
from mu.exceptions import MuError
from mu.formats.base.writer import BaseWriter
from mu.utils.youtube import get_video_id as get_youtube_video_id

logger = logging.getLogger(__name__)


class Writer(BaseWriter):
    def __init__(self) -> None:
        # List of (xml, parent_xml, path) tuples
        self.xml_paths: t.List[t.Tuple[Tag, str]] = []
        # unit -> xml dict
        self.unit_xml: t.Dict[units.Unit, Tag] = {}

    def write_to(self, path: str) -> None:
        for unit_xml, unit_path in self.xml_paths:
            # Write all xml files
            write_xml(unit_xml, os.path.join(path, unit_path), makedirs=True)

    def on_unit(self, unit: units.Unit) -> None:
        self.process_top_level_unit(unit)

    def on_course(self, unit: units.Course) -> None:
        # course.xml
        attributes = {
            "org": "organization",
            "course": "course",
            "url_name": get_url_name(unit),
        }
        for name in ["org", "course", "url_name"]:
            # TODO IMPORTANT should we also copy all the olx-* attributes? (I think we should)
            # TODO IMPORTANT should we also copy the attributes when we convert from olx?
            if olx_attr := unit.attributes.get(f"olx-{name}"):
                attributes[name] = olx_attr
            else:
                logger.warning(
                    "Top-level course does not have required attribute 'olx-%s'. Will default to '%s'.",
                    name,
                    attributes[name],
                )
        unit_xml = Tag(name="course", attrs=attributes)
        self.xml_paths.append((unit_xml, "course.xml"))
        self.unit_xml[unit] = unit_xml

        # course/<title>.xml
        self.process_top_level_unit(unit)

    def on_multiplechoicequestion(self, unit: units.MultipleChoiceQuestion) -> None:
        """
        https://edx.readthedocs.io/projects/edx-open-learning-xml/en/latest/problem-xml/checkbox.html

        Note that we generate checkbox problems by default, and not multiple choice problem, which support only a single answer:
        https://edx.readthedocs.io/projects/edx-open-learning-xml/en/latest/problem-xml/multiple_choice.html#multiple-choice-problem-olx-reference
        """
        problem_xml = self.process_unit(unit, "problem")
        response_xml = Tag(name="choiceresponse")
        question_xml = Tag(name="label")
        question_xml.string = unit.question
        response_xml.append(question_xml)
        responsegroup_xml = Tag(name="checkboxgroup")
        for index, (answer, is_correct) in enumerate(unit.answers):
            answer_xml = Tag(
                name="choice",
                attrs={"correct": str(is_correct).lower(), "name": str(index)},
            )
            answer_xml.string = answer
            responsegroup_xml.append(answer_xml)

        response_xml.append(responsegroup_xml)
        problem_xml.append(response_xml)

    def on_freetextquestion(self, unit: units.MultipleChoiceQuestion) -> None:
        """
        https://edx.readthedocs.io/projects/edx-open-learning-xml/en/latest/problem-xml/text_input.html
        """
        problem_xml = self.process_unit(unit, "problem")
        response_xml = Tag(name="stringresponse")
        response_xml.attrs["answer"] = unit.answers[0][0]
        question_xml = Tag(name="label")
        question_xml.string = unit.question
        response_xml.append(question_xml)
        for answer, _ in unit.answers[1:]:
            answer_xml = Tag(
                name="additional_answer",
                attrs={"answer": answer},
            )
            response_xml.append(answer_xml)
        problem_xml.append(response_xml)

    def on_rawhtml(self, unit: units.RawHtml) -> None:
        """
        https://edx.readthedocs.io/projects/edx-open-learning-xml/en/latest/components/html-components.html

        Note that the spec is incorrect. We should use "filename" and not "file_name".
        """
        html_xml = self.process_unit(unit, "html")

        # Create a <url_name>.html file with the html contents
        # Note the parser we use to prevent adding <html> tags
        # https://beautiful-soup-4.readthedocs.io/en/latest/#specifying-the-parser-to-use
        url_name = get_url_name(unit)
        self.xml_paths.append(
            (
                BeautifulSoup(unit.contents, "html.parser"),
                os.path.join("html", f"{url_name}.html"),
            )
        )

        # Point to the html file
        html_xml.attrs["filename"] = url_name

    def on_video(self, unit: units.Video) -> None:
        """
        https://edx.readthedocs.io/projects/edx-open-learning-xml/en/latest/components/video-components.html
        """
        video_xml = self.process_unit(unit, "video")
        # We need to define an empty youtube url; otherwise the default video with Anant is picked up.
        video_xml.attrs["youtube_id_1_0"] = ""
        for source in unit.sources:
            if youtube_video_id := get_youtube_video_id(source):
                video_xml.attrs["youtube_id_1_0"] = youtube_video_id
            else:
                video_xml.append(Tag(name="source", attrs={"src": source}))

    def process_top_level_unit(self, unit: units.Unit) -> None:
        """
        Process title units.
        """
        olx_types = ["course", "chapter", "sequential", "vertical"]
        unit_depth = unit.depth
        if unit_depth >= len(olx_types):
            # The title unit will not be created. Instead, we will use its title as the
            # unit display name.
            return
        if unit_depth >= len(olx_types) + 1:
            logger.warning(
                "Cannot render top-level unit '%s' of depth %d in olx.",
                unit.title,
                unit_depth,
            )
            return
        unit_type = olx_types[unit_depth]
        self.process_unit(unit, unit_type)

    def process_unit(self, unit: units.Unit, unit_type: str) -> Tag:
        """
        - If the unit has no url_name, generate one
        - Create the xml object that corresponds to <unit type>/<url_name>.xml
        - Append some xml reference to the parent xml
        - If children don't have a url_name, generate it
        """
        # Get/Generate url_name
        url_name = get_url_name(unit)

        # <unit_type>/<url_name>.xml
        display_name = unit.title
        if not display_name and unit.parent:
            # Borrow the title from the above unit
            display_name = unit.parent.title
        unit_xml = Tag(name=unit_type, attrs={"display_name": display_name})
        self.xml_paths.append(
            (
                unit_xml,
                os.path.join(unit_type, f"{url_name}.xml"),
            )
        )
        self.unit_xml[unit] = unit_xml

        # Find the nearest parent for which we have created an xml element
        parent = unit.parent
        while parent is not None:
            # Append <type url_name="..."> to that parent (if any)
            if parent_xml := self.unit_xml.get(parent):
                parent_xml.append(Tag(name=unit_type, attrs={"url_name": url_name}))
                break
            parent = parent.parent

        return unit_xml


def get_url_name(unit: units.Unit) -> str:
    if url_name := unit.attributes.get("olx-url_name"):
        return url_name
    url_name_hash = get_url_name_hash(unit)
    return hashlib.md5(url_name_hash.encode()).hexdigest()


def get_url_name_hash(unit: units.Unit) -> str:
    # Generate a repeatable hash based on the unit position in the tree
    # E.g: 3_11_0_5
    current_unit = unit
    unit_hash = ""
    while current_unit.parent is not None:
        if unit_hash:
            unit_hash = f"_{unit_hash}"
        nth_child = current_unit.parent.children.index(current_unit)
        unit_hash = f"{nth_child}{unit_hash}"
        current_unit = current_unit.parent
    return unit_hash


def write_xml(tag: Tag, path: str, makedirs: bool = False) -> None:
    directory = os.path.dirname(path)
    if makedirs:
        os.makedirs(directory, exist_ok=True)
    if not os.path.exists(directory):
        raise MuError(f"Destination directory does not exist: {directory}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(tag.prettify())
        f.write("\n")
