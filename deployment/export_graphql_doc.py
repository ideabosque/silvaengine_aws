#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import sys


module_name = sys.argv[-1]

schema = getattr(__import__(module_name), "schema")

graphql_html = open(f"{module_name}.html", "w")
graphql_html.write(schema.graphql_schema_doc())
graphql_html.close