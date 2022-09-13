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
import inspect
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
github_user = "newAM"
html_context = {
    "display_github": True,
    "github_user": github_user,
    "github_repo": project,
    # https://github.com/readthedocs/sphinx_rtd_theme/issues/465
    "github_version": "main",
    "conf_py_path": "/docs/",  # needs leading and trailing slashes
}

parser = get_parser(DEFAULT_CONFIG)
with open(os.path.join(this_dir, "cli.txt"), "w") as f:
    parser.print_help(f)


def linkcode_resolve(domain: str, info: dict) -> Optional[str]:
    # https://github.com/Lasagne/Lasagne/blob/5d3c63cb315c50b1cbd27a6bc8664b406f34dd99/docs/conf.py
    import idasen

    def find_source():
        # try to find the file and line number, based on code from numpy:
        # https://github.com/numpy/numpy/blob/master/doc/source/conf.py#L286
        obj = sys.modules[info["module"]]
        for part in info["fullname"].split("."):
            obj = getattr(obj, part)
        fn = inspect.getsourcefile(obj)
        fn = os.path.relpath(fn, start=os.path.dirname(idasen.__file__))
        source, lineno = inspect.getsourcelines(obj)
        return fn, lineno, lineno + len(source) - 1

    if domain != "py" or not info["module"]:
        return None

    try:
        filename = f"{project}/%s#L%d-L%d" % find_source()
    except Exception:
        filename = f"{project}/__init__.py"
    print(filename)
    return f"https://github.com/{github_user}/{project}/blob/main/{filename}"
