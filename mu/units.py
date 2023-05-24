import typing as t
import logging
import json

U = t.TypeVar("U", bound="Unit")

logger = logging.getLogger(__name__)


class Unit:
    """
    A generic course unit.

    All units have an optional title and key/value attributes.

    Courses follow a tree structure. Units which are not containers are terminal leaves.
    Every unit (except the top-level one) has a parent which is an instance of a
    Collection.
    """

    def __init__(
        self, attributes: t.Optional[t.Dict[str, str]] = None, title: str = ""
    ):
        self.attributes = attributes or {}
        self.parent: t.Optional["Collection"] = None
        self.title = title

    @property
    def depth(self) -> int:
        if self.parent is None:
            return 0
        return self.parent.depth + 1


class Collection(Unit):
    """
    A special type of Unit which can include children units.
    """

    def __init__(
        self, attributes: t.Optional[t.Dict[str, str]] = None, title: str = ""
    ):
        super().__init__(attributes=attributes, title=title)
        self.children: t.List[Unit] = []

    def add_child(self, unit: U) -> U:
        unit.parent = self
        self.children.append(unit)
        return unit


class Course(Collection):
    """
    Top-level element of a course.

    For now there is nothing special about this unit, but we may add extra properties in
    the future.
    """


class MultipleChoiceQuestion(Unit):
    def __init__(
        self,
        attributes: t.Optional[t.Dict[str, str]] = None,
        title: str = "",
        question: str = "",
        answers: t.Optional[t.List[t.Tuple[str, bool]]] = None,
    ):
        super().__init__(attributes=attributes, title=title)
        self.question = question
        answers = answers or []
        self.answers = [(answer.strip(), is_correct) for answer, is_correct in answers]


class FreeTextQuestion(MultipleChoiceQuestion):
    """
    A question for which the student is presented with a free text field to answer.

    Multiple answers are usually accepted.
    """

    def __init__(
        self,
        attributes: t.Optional[t.Dict[str, str]] = None,
        title: str = "",
        question: str = "",
        answers: t.Optional[t.List[str]] = None,
    ):
        answers = answers or []
        super().__init__(
            attributes=attributes,
            title=title,
            question=question,
            answers=[(answer, True) for answer in answers],
        )


class Poll(Unit):
    def __init__(
        self,
        attributes: t.Optional[t.Dict[str, str]] = None,
        title: str = "",
        question: str = "",
        answers: t.Optional[t.List[str]] = None,
        feedback: str = "",
    ):
        """
        Voting type question with 1 question and multiple answers.
        """
        attrs = {
            "feedback": "",
            "private_results": "false",
            "max_submissions": "1",
            "feedback": feedback,
        }
        accepted_attrs = ("url_name", "private_results", "max_submissions")
        ignored_attrs = ("id", "mu-type")
        if attributes:
            for attribute, value in attributes.items():
                attr_name = attribute.replace("data-", "", 1)
                if attr_name in accepted_attrs:
                    attrs[attr_name] = value
                elif attr_name not in ignored_attrs:
                    logger.warning(
                        f" {attr_name} attribute is unsupported by {self.__class__.__name__}."
                    )

        attrs["question"] = question
        answers = answers or []
        attrs["xblock-family"] = "xblock.v1"
        attrs["answers"] = (
            json.dumps(
                [
                    [
                        a.lower().replace(" ", "_"),
                        {"img": "", "img_alt": "", "label": a},
                    ]
                    for a in answers
                ],
                indent=4,
            )
            if answers
            else ""
        )

        super().__init__(attributes=attrs, title=title)


class Survey(Unit):
    def __init__(
        self,
        attributes: t.Dict[str, str] | None = None,
        title: str = "",
        answers: t.Optional[t.List[str]] = None,
        questions: t.Optional[t.List[str]] = None,
        feedback: str = "",
    ):
        """
        Multiple  questions with multiple choices common for all the questions.
        """
        attrs = {
            "feedback": "",
            "private_results": "false",
            "max_submissions": "1",
            "feedback": feedback,
        }
        accepted_attrs = ("url_name", "private_results", "max_submissions")
        ignored_attrs = ("id", "mu-type")
        if attributes:
            for attribute, value in attributes.items():
                attr_name = attribute.replace("data-", "", 1)
                if attr_name in accepted_attrs:
                    attrs[attr_name] = value
                elif attr_name not in ignored_attrs:
                    logger.warning(
                        f" {attr_name} attribute is unsupported by {self.__class__.__name__}."
                    )

        attrs["questions"] = (
            json.dumps(
                [
                    [
                        q.lower().replace(" ", "_"),
                        {"img": "", "img_alt": "", "label": q},
                    ]
                    for q in questions
                ],
                indent=4,
            )
            if questions
            else ""
        )

        answers = answers or []
        attrs["xblock-family"] = "xblock.v1"
        attrs["answers"] = (
            json.dumps([[a.lower().replace(" ", "_"), a] for a in answers], indent=4)
            or ""
        )
        super().__init__(attributes=attrs, title=title)


class RawHtml(Unit):
    def __init__(
        self,
        attributes: t.Optional[t.Dict[str, str]] = None,
        title: str = "",
        contents: str = "",
    ):
        super().__init__(attributes=attributes, title=title)
        self.contents = contents.strip()

    def concatenate(self, unit: "RawHtml") -> "RawHtml":
        self.contents += "\n" + unit.contents
        return self


class Video(Unit):
    def __init__(
        self,
        attributes: t.Optional[t.Dict[str, str]] = None,
        title: str = "",
        sources: t.Optional[t.List[str]] = None,
    ):
        """
        Sources are urls to the video. They can be completely arbitrary, such as youtube
        links or mp4 files.
        """
        super().__init__(attributes=attributes, title=title)
        self.sources = sources or []
