# 𝝁 🌊 the course authoring tool for humans

Mu is a tool for writing online courses in a human-friendly format and converting them to formats that can be understood by common learning management systems ([LMS](https://en.wikipedia.org/wiki/Learning_management_system)). In particular, Mu can convert courses from Markdown to Open edX Learning XML ([OLX](https://edx.readthedocs.io/projects/edx-open-learning-xml/)).

⚠ This work is still in the alpha stage! Do not report issues just yet. ⚠

Supported formats:

- [Markdown](https://daringfireball.net/projects/markdown/): with [Pandoc-flavoured](https://garrettgman.github.io/rmarkdown/authoring_pandoc_markdown.html) header attributes.
- HTML 5
- Open Learning XML ([OLX](https://edx.readthedocs.io/projects/edx-open-learning-xml/) from [Open edX](https://openedx.org).

## Installation

    pip install git+https://github.com/overhangio/mu

## Requirements

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
Video | R+W | R+W
Free text question | R+W | R+W
Multiple choice question | R+W | R+W
Raw HTML | R+W | R+W
more to come! |  |

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

    make tests

Reformat your code with [black](https://black.readthedocs.io/en/stable/):

    make format

Re-generate course samples:

    make examples

Upgrade pinned requirements:

    make upgrade-requirements

### How can we add a new type of course unit?

Want to add a new type of content to your course? Here's a general approach:

1. Start by creating a new type of unit in the [mu/units.py](https://github.com/overhangio/mu/blob/main/mu/units.py) module.
2. Add such a unit to the [examples/course.md](https://github.com/overhangio/mu/blob/main/examples/course.md) sample file, using your desired syntax.
3. Implement the corresponding HTML reader in the [mu/formats/html/reader.py](https://github.com/overhangio/mu/blob/main/mu/formats/html/reader.py) module. You should draw your inspiration from the `Reader.on_section` method. You are strongly encouraged to add at least one unit test to [tests/test_html.py](https://github.com/overhangio/mu/blob/main/mu/tests/test_html).
4. Now, implement the HTML writer in the [mu/formats/html/writer.py](https://github.com/overhangio/mu/blob/main/mu/formats/html/reader.py) module. This should be as simple as creating a new `Writer.on_yournewunitname` method. Add a unit test. Verify that your writer is generating the right HTML output by running `make example-html`.
5. Implement the corresponding OLX reader and writer in [mu/formats/olx/writer.py](https://github.com/overhangio/mu/blob/main/mu/formats/olx/reader.py) and [mu/formats/olx/writer.py](https://github.com/overhangio/mu/blob/main/mu/formats/olx/reader.py). Check that the OLX course is correctly generated when you run `make example-olx`.

## License

This work is licensed under the terms of the [GNU Affero General Public License (AGPL)](https://github.com/overhangio/mu/blob/master/LICENSE.txt).

<!-- TODO:
- how to support a new format
- extensibility?
- supported unit types: do we really need R+W symbols?
- Contributing section
- Troubleshooting -->
