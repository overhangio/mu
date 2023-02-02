import typing as t

from mu import units
from mu.exceptions import MuError

T = t.TypeVar("T")


class BaseReader:
    """
    TODO document me

    Child classes should also implement a constructor that takes a single path as
    argument.
    """

    def __init__(self, path: str) -> None:
        raise NotImplementedError

    def read(self) -> units.Course:
        """
        Read the course content from the path.

        For now, only a single course is returned. In theory nothing would prevent us
        from iterating over multiple courses here. Maybe we'll do that in the future.
        """
        for course in self.parse():
            if not isinstance(course, units.Course):
                # TODO better message
                raise MuError(
                    f"Failed to parse course. Expected Course object, got {course.__class__}"
                )
            return course
        # TODO what if there are multiple courses found?
        raise MuError("No course found")

    def parse(self) -> t.Iterable[units.Unit]:
        """
        This is where the bulk of the parsing should happen.

        Parse the content of the file(s) and yield Unit objects.
        """
        raise NotImplementedError

    def dispatch(
        self, name: str, *args: t.Any, **kwargs: t.Any
    ) -> t.Iterable[units.Unit]:
        """
        Convenient utility method, which will call the `on_<name>` method from the
        reader with `*args, **kwargs`.

        If no corresponding method is found, don't do anything.
        """
        # Parse element itself
        on_func: t.Optional[t.Callable[[t.Any], t.Iterable[units.Unit]]] = getattr(
            self, f"on_{name}", None
        )
        if on_func is not None:
            yield from on_func(*args, **kwargs)
