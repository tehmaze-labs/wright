#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name='wright',
    version='0.1.6',
    description='Leight weight (C) project configurator',
    long_description="""
⚒ Wright
========

Yet Another Build Tool
----------------------

There are plenty of awesome configurators out there, but they are all way too
complicated for most of my project needs. Wright uses a simple modular stage
based configuration scheme and uses Jinja2 to generate code snippets, Makefiles,
etc.


Example Usage
-------------

Inspect the test directory at https://github.com/tehmaze-labs/wright/tree/master/test


Bugs/Features
-------------
You can issue a ticket in GitHub: https://github.com/tehmaze-labs/wright/issues
""",
    author='Wijnand Modderman-Lenstra',
    author_email='maze@pyth0n.org',
    url='https://github.com/tehmaze-labs/wright',
    license='MIT',
    keywords='configure autotools c build scons',
    packages=[
        'wright',
        'wright.stage',
    ],
    entry_points={
        'console_scripts': [
            'wright=wright.main:main',
        ],
    },
    install_requires=[
        'Jinja2',
    ],
)
