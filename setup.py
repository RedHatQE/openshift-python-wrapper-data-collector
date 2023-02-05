#! /usr/bin/python
# -*- coding: utf-8 -*-

from setuptools import find_packages, setup

setup(
    name="openshift-python-wrapper-data-collector",
    license="apache-2.0",
    keywords=["Openshift"],
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pytest",
        "pytest-testconfig",
        "PyYAML",
        "openshift-python-wrapper",
    ],
    python_requires=">=3.8",
)
