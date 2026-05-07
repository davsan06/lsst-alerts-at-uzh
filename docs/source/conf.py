# Configuration file for the Sphinx documentation builder.

# -- Project information

project = 'LSST Image processing at UZH'
copyright = '2026, UZH GW Cosmo group'
author = 'David Sanchez Cid (UZH GW Cosmo group)'

# Documentation drafted in collaboration with Anthropic's Claude (Opus 4.7)
# during interactive debugging sessions on the UZH Science Cluster, and
# verified against the running v29.2.1 LSST Science Pipelines installation.

release = '0.1'
version = '0.1.0'

# -- General configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

# -- Options for HTML output

html_theme = 'sphinx_rtd_theme'

# -- Options for EPUB output
epub_show_urls = 'footnote'