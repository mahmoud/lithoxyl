# -*- coding: utf-8 -*-
#
# Lithoxyl documentation build configuration file, created by
# sphinx-quickstart on Sun Apr 12 16:44:20 2015.
#
# This file is execfile()d with the current directory set to its
# containing dir.

import os
import sys
import sphinx

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
PROJECT_PATH = os.path.abspath(CUR_PATH + '/../')
PACKAGE_PATH = os.path.abspath(CUR_PATH + '/../lithoxyl/')
sys.path.insert(0, PROJECT_PATH)
sys.path.insert(0, PACKAGE_PATH)

# -- General configuration ------------------------------------------------

needs_sphinx = '1.2'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.coverage',
    'sphinx.ext.viewcode',
]

# Read the Docs is version 1.2 as of writing
if sphinx.version_info[:2] < (1, 3):
    extensions.append('sphinxcontrib.napoleon')
else:
    extensions.append('sphinx.ext.napoleon')


templates_path = ['_templates']
source_suffix = '.rst'

master_doc = 'index'

# General information about the project.
project = u'Lithoxyl'
copyright = u'2015, Mahmoud Hashemi'
author = u'Mahmoud Hashemi'

# |version| and |release|
# The short X.Y version.
version = '20.0'
# The full version, including alpha/beta/rc tags.
release = '20.0.0'

if os.name != 'nt':
    today_fmt = '%B %e, %Y'

# Added to the end of all rst files before rendering
rst_epilog = ""

exclude_patterns = ['_build']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

intersphinx_mapping = {'python': ('https://docs.python.org/2.7', None)}

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
if not on_rtd: # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

#html_theme_options = {}
#html_theme_path = []
#html_title = None
#html_short_title = None
#html_logo = None
#html_favicon = None
html_static_path = ['_static']

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# The name of a javascript file (relative to the configuration directory) that
# implements a search results scorer. If empty, the default will be used.
#html_search_scorer = 'scorer.js'

# Output file base name for HTML help builder.
htmlhelp_basename = 'Lithoxyldoc'

# -- Options for LaTeX output ---------------------------------------------

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  (master_doc, 'Lithoxyl.tex', u'Lithoxyl Documentation',
   u'Mahmoud Hashemi', 'manual'),
]


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'lithoxyl', u'Lithoxyl Documentation',
     [author], 1)
]

# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  (master_doc, 'Lithoxyl', u'Lithoxyl Documentation',
   author, 'Lithoxyl', 'One line description of project.',
   'Miscellaneous'),
]
