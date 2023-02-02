from mu import units


class BaseWriter:
    def write_to(self, path: str) -> None:
        raise NotImplementedError

    def write(self, unit: units.Unit) -> "BaseWriter":
        # Get the "on_<Name>" function that corresponds to the unit type.
        on_func = getattr(self, f"on_{unit.__class__.__name__.lower()}")
        on_func(unit)

        # Write children recursively: depth-first traversal
        for child in unit.children:
            self.write(child)

        return self

    def on_unit(self, unit: units.Unit) -> None:
        pass

    def on_course(self, unit: units.Course) -> None:
        pass

    def on_multiplechoicequestion(self, unit: units.MultipleChoiceQuestion) -> None:
        pass

    def on_video(self, unit: units.Video) -> None:
        pass

    def on_rawhtml(self, unit: units.RawHtml) -> None:
        pass
