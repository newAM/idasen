###############################################################################
# Copyright 2020 Alex M.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
###############################################################################

from typing import Optional
import datetime
import os
import sys
import toml

this_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(this_dir, ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from idasen.cli import get_parser, DEFAULT_CONFIG  # noqa: E402

# Sphinx extensions
extensions = [
    "sphinx.ext.linkcode",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",  # google style docstrings
]

templates_path = []
source_suffix = ".rst"

with open(os.path.join(repo_root, "pyproject.toml"), "r") as f:
    pyproject = toml.load(f)

# The master toctree document.
master_doc = "index"

# General information about the project.
project = pyproject["tool"]["poetry"]["name"]
year = datetime.datetime.now().year
author = pyproject["tool"]["poetry"]["authors"][0].split("<", 1)[0].rstrip()
copyright = f"{year}, {author}"
version = pyproject["tool"]["poetry"]["version"]
release = pyproject["tool"]["poetry"]["version"]
language = "en"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", ".tox"]
pygments_style = "sphinx"
todo_include_todos = True
nitpicky = True

# HTML Options
html_theme = "sphinx_rtd_theme"
htmlhelp_basename = pyproject["tool"]["poetry"]["name"]
html_theme_options = {"display_version": True}
html_context = {
    "display_github": True,
    "github_user": "newAM",
    "github_repo": project,
}

parser = get_parser(DEFAULT_CONFIG)
with open(os.path.join(this_dir, "cli.txt"), "w") as f:
    parser.print_help(f)


def linkcode_resolve(domain: str, info: dict) -> Optional[str]:
    if domain != "py":
        return None
    if not info["module"]:
        return None
    if info["module"] == "idasen":
        return f"https://github.com/newAM/idasen/blob/v{version}/idasen/__init__.py"
