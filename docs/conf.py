import datetime as dt
import importlib
import os
import time

import sphinx_rtd_theme

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
    "sphinx_issues",
]

primary_domain = "py"
default_role = "py:obj"

intersphinx_mapping = {
    "python": ("https://python.readthedocs.io/en/latest/", None),
    "marshmallow": ("https://marshmallow.readthedocs.io/en/latest/", None),
    "webargs": ("https://webargs.readthedocs.io/en/latest/", None),
}

issues_github_path = "marshmallow-code/apispec"


# Use SOURCE_DATE_EPOCH for reproducible build output
# https://reproducible-builds.org/docs/source-date-epoch/
build_date = dt.datetime.utcfromtimestamp(
    int(os.environ.get("SOURCE_DATE_EPOCH", time.time()))
)

source_suffix = ".rst"
master_doc = "index"
project = "apispec"
copyright = f"2014-{build_date:%Y}, Steven Loria and contributors"

version = release = importlib.metadata.version("apispec")

exclude_patterns = ["_build"]

# THEME

html_theme = "sphinx_rtd_theme"
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
