#!/usr/bin/env python

import setuptools
import subprocess
from setuptools import setup, Extension

include_dirs = [a for a in (a.strip() for a in subprocess.check_output(
    ["pkg-config", "libxml-2.0", "--cflags-only-I"]).decode("utf-8").split("-I")) if a]
library_dirs = [a for a in (a.strip() for a in subprocess.check_output(
    ["pkg-config", "libxml-2.0", "--libs-only-L"]).decode("utf-8").split("-L")) if a]
libraries = [a for a in (a.strip() for a in subprocess.check_output(
    ["pkg-config", "libxml-2.0", "--libs-only-l"]).decode("utf-8").split("-l")) if a]

class get_numpy_include(object):
    def __str__(self):
        return self.__fspath__()
    def __fspath__(self):
        import numpy
        return numpy.get_include()
    def __getattr__(self, item):
        return getattr(str(self),item)
    def __add__(self, other):
        return str(self)+other

setuptools.setup(
    name='emeraldtriangles',
    version='0.0.20',
    description='Triangle mesh transforms',
    long_description='Iteratively add points to an existing mesh, calculate mesh bounding polygons etc.',
    long_description_content_type="text/markdown",
    author='Egil Moeller',
    author_email='em@emerld.no',
    url='https://github.com/EMeraldGeo/EmeraldTriangles',
    packages=setuptools.find_packages(),
    install_requires=[
        "numpy",
        "pandas",
        "scipy",
        "triangle",

        # Maybe make these optional?
        "pandasio",
        "lxml",
        "matplotlib",
        "shapely",
        "geoalchemy2",
        "pyproj",
        "pyvista",
        "scikit-gstat",
        "bokeh",
        'rasterio',
    ],
    setup_requires=[
        'setuptools>=18.0',
        'numpy',
        'cython',
    ],
    package_data={'emeraldtriangles': ['*/*.pyx', '*/*.pxd']},
    ext_modules=[
        Extension(
            'emeraldtriangles.io._landxml',
            sources=['emeraldtriangles/io/_landxml.pyx'],
            include_dirs = include_dirs + [get_numpy_include()],
            library_dirs = library_dirs,
            libraries = libraries,
        ),
    ]
)
