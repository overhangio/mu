import typing as t

from lecture import units
from lecture.exceptions import LectureError


class Reader:
    """
    TODO document me
    """

    def read(self) -> units.Course:
        for course in self.parse():
            if not isinstance(course, units.Course):
                # TODO better message
                raise LectureError(
                    f"Failed to parse course. Expected Course object, got {course.__class__}"
                )
            return course
        # TODO what if there are multiple courses found?
        raise LectureError("No course found")

    def parse(self) -> t.Iterable[units.Unit]:
        raise NotImplementedError

    def dispatch(
        self, name: str, *args: t.Any, **kwargs: t.Any
    ) -> t.Iterable[units.Unit]:
        # Parse element itself
        on_func: t.Optional[t.Callable[[t.Any], t.Iterable[units.Unit]]] = getattr(
            self, f"on_{name}", None
        )
        if on_func is not None:
            yield from on_func(*args, **kwargs)
