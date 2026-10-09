"""Wybór konfiguracji eksperymentu przez zmienną CONFIG_MODULE (domyślnie v1.1: config)."""
import importlib
import os


def load():
    return importlib.import_module(os.environ.get("CONFIG_MODULE", "config"))
