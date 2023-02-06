import typing as t

U = t.TypeVar("U", bound="Unit")


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
