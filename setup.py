# -*- coding: utf-8 -*-
# @Time    : 2019/10/11 22:57
# @Author  : floatsliang
# @File    : setup.py
from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()
setup(
    name='sqlorm4es',
    version=__import__('sqlorm4es').__version__,
    description='A simple, expressive elasticsearch orm',
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=['test']),
    url='https://github.com/floatliang/sqlorm4es',
    author='floatsliang',
    author_email='utavianus@qq.com',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='sql orm elasticsearch',
    install_requires=[
        'elasticsearch >= 6.3.1',
        'python-dateutil >= 2.5.0',
        'six >= 1.10.0'
    ],
    zip_safe=False,
    platforms=['any'],
)
