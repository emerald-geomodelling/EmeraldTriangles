#!/usr/bin/env python

import setuptools
import subprocess
from setuptools import setup

include_dirs = [a for a in (a.strip() for a in subprocess.check_output(
    ["pkg-config", "libxml-2.0", "--cflags-only-I"]).decode("utf-8").split("-I")) if a]
library_dirs = [a for a in (a.strip() for a in subprocess.check_output(
    ["pkg-config", "libxml-2.0", "--libs-only-L"]).decode("utf-8").split("-L")) if a]
libraries = [a for a in (a.strip() for a in subprocess.check_output(
    ["pkg-config", "libxml-2.0", "--libs-only-l"]).decode("utf-8").split("-l")) if a]

class Extension(setuptools.Extension):
    def __init__(self, *args, **kwargs):
        self.__include_dirs = []
        super().__init__(*args, **kwargs)

    @property
    def include_dirs(self):
        import numpy
        return self.__include_dirs + [numpy.get_include()]

    @include_dirs.setter
    def include_dirs(self, dirs):
        self.__include_dirs = dirs
    
setuptools.setup(
    name='emeraldtriangles',
    version='0.1.1',
    description='Triangle mesh transforms',
    long_description='Iteratively add points to an existing mesh, calculate mesh bounding polygons etc.',
    long_description_content_type="text/markdown",
    author='Egil Moeller, Craig W. Christensen, et al.',
    author_email='em@emrld.no',
    url='https://github.com/EMeraldGeo/EmeraldTriangles',
    packages=setuptools.find_packages(),
    install_requires=[
        "numpy==1.24.4",
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
            include_dirs = include_dirs,
            library_dirs = library_dirs,
            libraries = libraries,
        ),
    ]
)
