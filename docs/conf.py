import importlib

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

source_suffix = ".rst"
master_doc = "index"
project = "apispec"
copyright = "Steven Loria, Jérôme Lafréchoux, and contributors"

version = release = importlib.metadata.version("apispec")

exclude_patterns = ["_build"]

# THEME

html_theme = "sphinx_rtd_theme"
