import re
from setuptools import setup, find_packages

EXTRAS_REQUIRE = {
    "yaml": ["PyYAML>=3.10"],
    "validation": ["prance[osv]>=0.11"],
    "lint": ["flake8==3.9.2", "flake8-bugbear==21.4.3", "pre-commit~=2.4"],
    "docs": [
        "marshmallow>=3.0.0",
        "pyyaml==5.4.1",
        "sphinx==4.0.2",
        "sphinx-issues==1.2.0",
        "sphinx-rtd-theme==0.5.2",
    ],
}
EXTRAS_REQUIRE["tests"] = (
    EXTRAS_REQUIRE["yaml"]
    + EXTRAS_REQUIRE["validation"]
    + ["marshmallow>=3.10.0", "pytest", "mock"]
)
EXTRAS_REQUIRE["dev"] = EXTRAS_REQUIRE["tests"] + EXTRAS_REQUIRE["lint"] + ["tox"]


def find_version(fname):
    """Attempts to find the version number in the file names fname.
    Raises RuntimeError if not found.
    """
    version = ""
    with open(fname) as fp:
        reg = re.compile(r'__version__ = [\'"]([^\'"]*)[\'"]')
        for line in fp:
            m = reg.match(line)
            if m:
                version = m.group(1)
                break
    if not version:
        raise RuntimeError("Cannot find version information.")
    return version


def read(fname):
    with open(fname) as fp:
        content = fp.read()
    return content


setup(
    name="apispec",
    version=find_version("src/apispec/__init__.py"),
    description="A pluggable API specification generator. Currently supports the "
    "OpenAPI Specification (f.k.a. the Swagger specification).",
    long_description=read("README.rst"),
    author="Steven Loria",
    author_email="sloria1@gmail.com",
    url="https://github.com/marshmallow-code/apispec",
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    extras_require=EXTRAS_REQUIRE,
    license="MIT",
    zip_safe=False,
    keywords="apispec swagger openapi specification oas documentation spec rest api",
    python_requires=">=3.6",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3 :: Only",
    ],
    test_suite="tests",
    project_urls={
        "Funding": "https://opencollective.com/marshmallow",
        "Issues": "https://github.com/marshmallow-code/apispec/issues",
        "Tidelift": "https://tidelift.com/subscription/pkg/pypi-apispec?utm_source=pypi-apispec&utm_medium=pypi",  # noqa: B950,E501
    },
)
