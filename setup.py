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


setuptools.setup(
    name='emeraldtriangles',
    version='0.0.5',
    description='Triangle mesh transforms',
    long_description='Iteratively add points to an existing mesh, calculate mesh bounding polygons etc.',
    long_description_content_type="text/markdown",
    author='Egil Moeller',
    author_email='em@emeraldgeo.no',
    url='https://github.com/EMeraldGeo/EmeraldTriangles',
    packages=setuptools.find_packages(),
    install_requires=[
        "numpy",
        "pandas",
        "scipy",
        "triangle",
        "lxml"
    ],
    setup_requires=[
        'setuptools>=18.0',
        'cython',
    ],
    ext_modules=[
        Extension(
            'emeraldtriangles.io.landxml2',
            sources=['emeraldtriangles/io/landxml2.pyx'],
            include_dirs = include_dirs,
            library_dirs = library_dirs,
            libraries = libraries,
        ),
    ]
)
