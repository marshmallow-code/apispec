import datetime as dt
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join("..", "src")))
import apispec  # noqa: E402

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

version = release = apispec.__version__

exclude_patterns = ["_build"]

# THEME

# on_rtd is whether we are on readthedocs.org
on_rtd = os.environ.get("READTHEDOCS", None) == "True"

if not on_rtd:  # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme

    html_theme = "sphinx_rtd_theme"
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
