#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
__author__ = 'bibow'

import json
from decimal import Decimal
from datetime import datetime, date


class JSONEncoder(json.JSONEncoder):
    
    def default(self, o):   # pylint: disable=E0202
        if isinstance(o, Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return str(o)
        elif hasattr(o, 'attribute_values'):
            return o.attribute_values
        elif isinstance(o, (datetime, date)):
            return o.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(o, (bytes, bytearray)):
            return str(o)
        else:
            return super(JSONEncoder, self).default(o)


class JSONDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, o):
        if '_type' not in o:
            return o
        type = o['_type']
        if type in ['bytes', 'bytearray']:
            return str(o['value'])
        return o


class Struct(object):

    def __init__(self, d):
        for a, b in d.items():
            if isinstance(b, (list, tuple)):
               setattr(self, a, [Struct(x) if isinstance(x, dict) else x for x in b])
            else:
               setattr(self, a, Struct(b) if isinstance(b, dict) else b)

              
class Utility(object):

    @classmethod
    def json_dumps(cls, data):
        return json.dumps(data, indent=4, cls=JSONEncoder, ensure_ascii=False)

    @classmethod
    def json_loads(cls, data):
        return json.loads(data, cls=JSONDecoder, parse_float=Decimal)