#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
__author__ = 'bibow'

import sys, os
sys.path.append('/opt')

from silvaengine_utility import Tasks
import logging
logger = logging.getLogger()
logger.setLevel(eval(os.environ["LOGGINGLEVEL"]))

handler = Tasks.getHandler(logger) # input values for args and/or kwargs