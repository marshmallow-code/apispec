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

html_theme = "furo"
html_theme_options = {
    "source_repository": "https://github.com/marshmallow-code/apispec",
    "source_branch": "dev",
    "source_directory": "docs/",
    "light_css_variables": {
        "font-stack": "Charter, Iowan Old Style, Palatino Linotype, Palatino, Georgia, serif;",
    },
    "top_of_page_buttons": ["view", "edit"],
}
pygments_dark_style = "lightbulb"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_copy_source = False
html_show_sourcelink = False
