import subprocess
import tempfile

from lecture import units
from lecture.formats.html.writer import StyledWriter


def dump(course: units.Course, path: str) -> None:
    writer = StyledWriter()
    writer.write(course)

    # Write html to temporary file
    with tempfile.NamedTemporaryFile("w") as of:
        writer.write_to(of.name)
        of.flush()
        # Convert file with pandoc
        subprocess.check_call(
            ["pandoc", "--from=html", "--to=markdown", of.name, f"--output={path}"]
        )
