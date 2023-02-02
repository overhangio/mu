import io
import os
import typing as t

from setuptools import find_packages, setup

HERE = os.path.abspath(os.path.dirname(__file__))


def load_readme() -> str:
    with io.open(os.path.join(HERE, "README.md"), "rt", encoding="utf8") as f:
        return f.read()


def load_requirements(filename: str) -> t.List[str]:
    with io.open(
        os.path.join(HERE, "requirements", filename), "rt", encoding="utf-8"
    ) as f:
        return [line.strip() for line in f if is_requirement(line)]


def is_requirement(line: str) -> bool:
    return not (line.strip() == "" or line.startswith("#"))


setup(
    name="mu-courses",
    version="0.0.1",
    url="https://github.com/overhangio/mu/",
    project_urls={
        "Code": "https://github.com/overhangio/mu",
        "Issue tracker": "https://github.com/overhangio/mu/issues",
    },
    license="AGPLv3",
    author="Overhang.IO",
    author_email="contact@overhang.io",
    description="Course authoring for humans",
    long_description=load_readme(),
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["tests*"]),
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=load_requirements("base.in"),
    entry_points={"console_scripts": ["mu=mu.main:main"]},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    test_suite="tests",
)
