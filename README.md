# 𝝁 🌊 course authoring for humans

Mu is for authors of online courses. It allows you to cross-compile courses from one format to another. For instance, you can write your courses in a human-friendly format, such as Markdown, and convert them to a format that can be imported in your learning management system ([LMS](https://en.wikipedia.org/wiki/Learning_management_system)).

Supported formats:

- [Markdown](https://daringfireball.net/projects/markdown/): with [Pandoc-flavoured](https://garrettgman.github.io/rmarkdown/authoring_pandoc_markdown.html) header attributes.
- HTML 5
- Open Learning XML ([OLX](https://docs.openedx.org/en/latest/educators/navigation/olx.html)) from [Open edX](https://openedx.org).

Check out the [course.md](https://github.com/overhangio/mu/blob/main/examples/course.md) file to see what an actual course in Markdown format looks like.

## Installation

    pip install mu-courses

Conversion from and to Markdown is handled with the help of [Pandoc](https://pandoc.org/). Thus, a recent version of Pandoc is required when working with Markdown documents. See the corresponding [installation instructions](https://pandoc.org/installing.html).

## Usage

    # Markdown -> OLX
    mu /path/to/course.md /path/to/olx/
    # OLX -> HTML
    mu /path/to/olx/course/ /path/to/course.html
    # HTML -> OLX
    mu /path/to/course.html /path/to/olx/course/
    ...

When writing Markdown files, the generated documents will include non-standard (but widely recognized) [header identifiers](https://garrettgman.github.io/rmarkdown/authoring_pandoc_markdown.html#header-identifiers) to store the course unit attributes.

## Examples

Example courses are provided in the [examples](./examples) directory.

## Supported unit types and formats

For each unit type, we indicate whether reading from (R) and writing to (W) the corresponding format are supported.

Unit type / Format | OLX | HTML/Markdown
---|---|---
Collection | ✅ | ✅
Video | ✅ | ✅
Free text question | ✅ | ✅
Multiple choice question | ✅ | ✅
Raw HTML | ✅ | ✅

### Notes and known limitations

#### OLX

##### Writer

* Multiple choice questions are always rendered as checkboxes, and not as single-choice questions.

## Contributing

### Setting up a development environment

Install development requirements:

    pip install -r requirements/dev.txt
    pip install -e .

Run tests:

    make test

Reformat your code with [black](https://black.readthedocs.io/en/stable/):

    make format

Re-generate course samples:

    make examples

Upgrade pinned requirements:

    make upgrade-requirements

Publish a new release:

    python setup sdist
    twine upload dist/mu-courses*.tar.gz

### How to add a new type of course unit?

Want to add a new type of content to your course? Here's a general approach:

1. Start by creating a new type of unit in the [mu/units.py](https://github.com/overhangio/mu/blob/main/mu/units.py) module.
2. Add such a unit to the [examples/course.md](https://github.com/overhangio/mu/blob/main/examples/course.md) sample file, using your desired syntax.
3. Implement the corresponding HTML reader in the [mu/formats/html/reader.py](https://github.com/overhangio/mu/blob/main/mu/formats/html/reader.py) module. You should draw your inspiration from the `Reader.on_section` method. You are strongly encouraged to add at least one unit test to [tests/test_html.py](https://github.com/overhangio/mu/blob/main/mu/tests/test_html).
4. Now, implement the HTML writer in the [mu/formats/html/writer.py](https://github.com/overhangio/mu/blob/main/mu/formats/html/reader.py) module. This should be as simple as creating a new `Writer.on_yournewunitname` method. Add a unit test. Verify that your writer is generating the right HTML output by running `make example-html`.
5. Implement the corresponding OLX reader and writer in [mu/formats/olx/writer.py](https://github.com/overhangio/mu/blob/main/mu/formats/olx/reader.py) and [mu/formats/olx/writer.py](https://github.com/overhangio/mu/blob/main/mu/formats/olx/reader.py). Check that the OLX course is correctly generated when you run `make example-olx`.

### How to add a new input/output format?

Would you like to use Mu with an LMS that is not currently supported, or with your own course format? You will need to implement two Python classes: a `Reader` and a `Writer`.

In Mu, converting from one format to another works as follows:

    Reader -----------> unit.Course object ---------> Writer ------------> final path
            generates                       sent to           writes to    or directory

- The new `Reader` class must implement the methods from [`mu.formats.base.reader.BaseReader`](https://github.com/overhangio/mu/blob/main/mu/formats/base/reader.py).
- The new `Writer` class must implement the methods from [`mu.formats.base.writer.BaseWriter`](https://github.com/overhangio/mu/blob/main/mu/formats/base/writer.py).

You should make sure to add unit tests to the `tests/` directory.

At the moment, all reader/writers must live in the mu package. In the future, we expect that it will be possible to auto-discover different reader and writer packages.

## Troubleshooting

This project was created by Matthew Brett (@matthew-brett) and funded by a grant from the [Chan Zuckerberg Initiative](https://chanzuckerberg.com/). The project is maintained by Régis Behmo from [Overhang.IO](https://overhang.io). Would you like to report an issue or request a feature? Then [open a new GitHub issue](https://github.com/overhangio/mu/issues).

## License

This work is licensed under the terms of the [GNU Affero General Public License (AGPL)](https://github.com/overhangio/mu/blob/master/LICENSE.txt).
