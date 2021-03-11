#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
__author__ = 'bibow'

import sys, os
sys.path.append('/opt')

from silvaengine_base import Resources
import logging
logger = logging.getLogger()
logger.setLevel(eval(os.environ["LOGGINGLEVEL"]))

handler = Resources.get_handler(logger) # input values for args and/or kwargs