#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
__author__ = 'bibow'

from graphene import ObjectType, InputObjectType, String, Decimal, DateTime, List, Field


class InputType(InputObjectType):
    source = String(required=True)
    src_id = String(required=True)


class TransactionStatusInputType(InputObjectType):
    id = String(required=True)
    tgt_id = String(required=True)
    tx_note = String(required=True)
    tx_status = String(required=True)