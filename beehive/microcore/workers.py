#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import os
import sys

sys.path.append("/opt")

EFS_MOUNT_POINT = os.environ.get("EFSMOUNTPOINT")
PYTHON_PACKAGES_PATH = os.environ.get("PYTHONPACKAGESPATH")
if EFS_MOUNT_POINT is not None and PYTHON_PACKAGES_PATH is not None:
    sys.path.append(f"{EFS_MOUNT_POINT}/{PYTHON_PACKAGES_PATH}")

import logging

from silvaengine_base import Worker

logger = logging.getLogger()
logger.setLevel(eval(os.environ["LOGGINGLEVEL"]))

handler = Worker.get_handler(logger)  # input values for args and/or kwargs
