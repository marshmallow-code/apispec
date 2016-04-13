# -*- coding: utf-8 -*-
import re
from setuptools import setup, find_packages


REQUIRES = [
    'PyYAML>=3.10'
]


def find_version(fname):
    """Attempts to find the version number in the file names fname.
    Raises RuntimeError if not found.
    """
    version = ''
    with open(fname, 'r') as fp:
        reg = re.compile(r'__version__ = [\'"]([^\'"]*)[\'"]')
        for line in fp:
            m = reg.match(line)
            if m:
                version = m.group(1)
                break
    if not version:
        raise RuntimeError('Cannot find version information')
    return version

__version__ = find_version('apispec/__init__.py')


def read(fname):
    with open(fname) as fp:
        content = fp.read()
    return content

setup(
    name='apispec',
    version=__version__,
    description='A pluggable API specification generator. Currently supports the '
                'OpenAPI specification (f.k.a. Swagger 2.0).',
    long_description=read('README.rst'),
    author='Steven Loria, Josh Carp',
    author_email='sloria1@gmail.com',
    url='https://github.com/marshmallow-code/apispec',
    packages=find_packages(exclude=("test*", )),
    package_dir={'apispec': 'apispec'},
    include_package_data=True,
    install_requires=REQUIRES,
    license=read("LICENSE"),
    zip_safe=False,
    keywords='apispec swagger openapi specification documentation spec rest api',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
)
