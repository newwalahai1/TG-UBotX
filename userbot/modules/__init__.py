# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.c (the "License");
# you may not use this file except in compliance with the License.
#
""" Init file which loads all of the modules """
from userbot import LOGS


def __list_all_modules():
    from os.path import dirname, isfile, relpath
    from glob import glob

    root_dir = dirname(__file__)
    mod_paths = glob(root_dir + "/**/*.py", recursive=True)
    all_modules = [
        '.'.join(relpath(f, root_dir).split('/'))[:-3]
        for f in mod_paths
        if isfile(f) and f.endswith(".py") and not f.endswith("__init__.py")
    ]
    return all_modules


ALL_MODULES = sorted(__list_all_modules())
LOGS.info("Modules to load: %s", str(ALL_MODULES))
__all__ = ALL_MODULES + ["ALL_MODULES"]
