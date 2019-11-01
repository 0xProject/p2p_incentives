#!/usr/bin/env python

"""setuptools module for p2p_incentives package."""

import glob
import subprocess  # nosec
from shutil import rmtree
from os import environ, path

# from pathlib import Path
from sys import argv

# Added a comment below since mypy doesn't know there's a clean in distutils.command.clean
from distutils.command.clean import clean  # type: ignore

import distutils.command.build_py
from setuptools import find_packages, setup
from setuptools.command.test import test as TestCommand


class TestCommandExtension(TestCommand):
    """Run pytest tests."""

    def run_tests(self):
        """Invoke pytest."""

        # pylint: disable=C0415, R1722
        
        import pytest

        exit(pytest.main(["--doctest-modules"]))


class LintCommand(distutils.command.build_py.build_py):
    """Custom setuptools command class for running linters."""

    description = "Run linters"

    def run(self):
        """Run linter shell commands."""
        files = " ".join(glob.glob("./**/*.py", recursive=True))
        lint_commands = [
            # # formatter:
            ("black --line-length 88 --check --diff " + files).split(),
            # # style guide checker (formerly pep8):
            # ("pycodestyle " + files).split(),
            # # docstring style checker:
            # ("pydocstyle " + files).split(),
            # static type checker:
            ("mypy --ignore-missing-imports " + files).split(),
            # # security issue checker:
            # ("bandit -r " + files).split(),
            # general linter:
            ("pylint " + files).split(),
            # pylint takes relatively long to run, so it runs last, to enable
            # fast failures.
        ]

        # tell mypy where to find interface stubs for 3rd party libs
        environ["MYPYPATH"] = path.join(path.dirname(path.realpath(argv[0])), "stubs")

        for lint_command in lint_commands:
            print("Running lint command `", " ".join(lint_command).strip(), "`")
            subprocess.check_call(lint_command)  # nosec


class CleanCommandExtension(clean):
    """Custom command to do custom cleanup."""

    def run(self):
        """Run the regular clean, followed by our custom commands."""
        super().run()
        rmtree("dist", ignore_errors=True)
        rmtree(".mypy_cache", ignore_errors=True)
        rmtree(".tox", ignore_errors=True)
        rmtree(".pytest_cache", ignore_errors=True)


with open("README.md", "r") as file_handle:
    README_MD = file_handle.read()


setup(
    name="0x-p2p-incentives",
    version="2.0.0",
    description="Peer-to-peer incentives",
    long_description=README_MD,
    long_description_content_type="text/markdown",
    url=("https://github.com/0xProject/p2p_incentives/tree/development"),
    author="Weijie Wu",
    author_email="weijie@0x.org",
    cmdclass={
        "clean": CleanCommandExtension,
        "lint": LintCommand,
        "test": TestCommandExtension,
    },
    install_requires=["matplotlib", "mypy_extensions", "numpy"],
    extras_require={
        "dev": [
            # HACK(weijiewu): needed to pin version of pylint dependency due to bug described
            # at https://github.com/PyCQA/pylint/issues/3123
            # "astroid==2.2.5",
            "bandit",
            "black",
            "coverage",
            "coveralls",
            "deprecated",
            "mypy",
            "mypy_extensions",
            "pycodestyle",
            "pydocstyle",
            # HACK(weijiewu): Due to downgrade of astroid I have to downgrade pylint as well (
            # otherwise they don't work together).
            "pylint",
            "pytest",
            "sphinx",
            "sphinx-autodoc-typehints",
            "tox",
            "twine",
        ]
    },
    python_requires=">=3.6, <4",
    package_dir={"": "."},
    license="Apache 2.0",
    keywords=("ethereum cryptocurrency 0x decentralized blockchain dex exchange"),
    packages=find_packages("."),
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Office/Business :: Financial",
        "Topic :: Other/Nonlisted Topic",
        "Topic :: Security :: Cryptography",
        "Topic :: Software Development :: Libraries",
        "Topic :: Utilities",
    ],
    zip_safe=False,  # required per mypy
    command_options={
        "build_sphinx": {
            "source_dir": ("setup.py", "src"),
            "build_dir": ("setup.py", "build/docs"),
        }
    },
)
