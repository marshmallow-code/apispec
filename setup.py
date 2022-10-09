import re
from setuptools import setup, find_packages

INSTALL_REQUIRES = "packaging>=21.3"

EXTRAS_REQUIRE = {
    "marshmallow": ["marshmallow>=3.18.0"],
    "yaml": ["PyYAML>=3.10"],
    "validation": ["prance[osv]>=0.11", "openapi_spec_validator<0.5"],
    "lint": [
        "flake8==5.0.4",
        "flake8-bugbear==22.9.23",
        "pre-commit~=2.4",
        "mypy==0.982",
        "types-PyYAML",
    ],
    "docs": [
        "marshmallow>=3.13.0",
        "pyyaml==6.0",
        "sphinx==5.2.3",
        "sphinx-issues==3.0.1",
        "sphinx-rtd-theme==1.0.0",
    ],
}
EXTRAS_REQUIRE["tests"] = (
    EXTRAS_REQUIRE["yaml"]
    + EXTRAS_REQUIRE["validation"]
    + ["marshmallow>=3.13.0", "pytest", "mock"]
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
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
    license="MIT",
    zip_safe=False,
    keywords="apispec swagger openapi specification oas documentation spec rest api",
    python_requires=">=3.7",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3 :: Only",
    ],
    test_suite="tests",
    project_urls={
        "Funding": "https://opencollective.com/marshmallow",
        "Issues": "https://github.com/marshmallow-code/apispec/issues",
        "Tidelift": "https://tidelift.com/subscription/pkg/pypi-apispec?utm_source=pypi-apispec&utm_medium=pypi",  # noqa: B950,E501
    },
)
