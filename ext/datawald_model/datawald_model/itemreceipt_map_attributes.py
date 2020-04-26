#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
__author__ = 'bibow'

from pynamodb.attributes import (
    MapAttribute, ListAttribute, UnicodeAttribute, NumberAttribute, UnicodeSetAttribute, UTCDateTimeAttribute
)


class ItemMap(MapAttribute):
    internal_id = UnicodeAttribute()
    item_no = UnicodeAttribute()
    qty = NumberAttribute()


class ShipToMap(MapAttribute):
    address = UnicodeAttribute()
    city = UnicodeAttribute()
    contact = UnicodeAttribute()
    country_code = UnicodeAttribute()
    name = UnicodeAttribute()
    shipping = UnicodeAttribute()
    state = UnicodeAttribute()
    zip = UnicodeAttribute()


class DataMap(MapAttribute):
    itemreceipt_id = UnicodeAttribute(default='#####')
    internal_id = UnicodeAttribute()
    items = ListAttribute(of=ItemMap)
    key = UnicodeAttribute()
    order_date = UTCDateTimeAttribute()
    ref_no = ListAttribute()
    ship_to = ShipToMap() 
    status = UnicodeAttribute()
    tran_ids = ListAttribute()
    update_date = UTCDateTimeAttribute()


    