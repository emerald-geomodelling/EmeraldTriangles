"""
Minimal setup.py for Cython extension configuration.
All metadata and dependencies are in pyproject.toml.

This file is only needed because the _landxml extension requires
dynamic pkg-config configuration for libxml-2.0.
"""

import subprocess
import setuptools


def get_pkg_config(lib, flag):
    """Get pkg-config flags for a library."""
    try:
        output = subprocess.check_output(
            ["pkg-config", lib, flag]
        ).decode("utf-8")
        prefix = flag.split("-")[-1][0]  # 'I', 'L', or 'l'
        return [a.strip() for a in output.split(f"-{prefix}") if a.strip()]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


class NumpyExtension(setuptools.Extension):
    """Extension that defers numpy import until build time."""

    def __init__(self, *args, **kwargs):
        self._include_dirs = []
        super().__init__(*args, **kwargs)

    @property
    def include_dirs(self):
        import numpy
        return self._include_dirs + [numpy.get_include()]

    @include_dirs.setter
    def include_dirs(self, dirs):
        self._include_dirs = dirs


# Get libxml-2.0 configuration
include_dirs = get_pkg_config("libxml-2.0", "--cflags-only-I")
library_dirs = get_pkg_config("libxml-2.0", "--libs-only-L")
libraries = get_pkg_config("libxml-2.0", "--libs-only-l")

ext_modules = [
    NumpyExtension(
        "emeraldtriangles.io._landxml",
        sources=["emeraldtriangles/io/_landxml.pyx"],
        include_dirs=include_dirs,
        library_dirs=library_dirs,
        libraries=libraries,
    ),
]

setuptools.setup(ext_modules=ext_modules)
