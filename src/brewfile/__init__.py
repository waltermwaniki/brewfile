"""
Brewfile - Intelligent Homebrew Package Management

A command-line tool for managing Homebrew packages with JSON configuration
and machine-aware installations using brew bundle.
"""

__version__ = "0.1.0"
__author__ = "Walter Mwaniki"
__email__ = "walter.g.mwaniki@gmail.com"

# Import main CLI function for easy access
from .cli import main

__all__ = ["main", "__version__", "__author__", "__email__"]
