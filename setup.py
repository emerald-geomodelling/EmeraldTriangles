#!/usr/bin/env python

import setuptools

setuptools.setup(
    name='emeraldtriangles',
    version='0.0.2',
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
        "triangle"
    ]
)
