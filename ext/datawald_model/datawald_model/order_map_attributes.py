#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
__author__ = 'bibow'

from pynamodb.attributes import (
    MapAttribute, ListAttribute, UnicodeAttribute, NumberAttribute, UnicodeSetAttribute, UTCDateTimeAttribute
)


class ItemMap(MapAttribute):
    price = NumberAttribute()
    qty = NumberAttribute()
    sku = UnicodeAttribute()


class AddressMap(MapAttribute):
    address = UnicodeAttribute()
    city = UnicodeAttribute()
    company = UnicodeAttribute()
    country = UnicodeAttribute()
    email = UnicodeAttribute()
    firstname = UnicodeAttribute()
    lastname = UnicodeAttribute()
    postcode = UnicodeAttribute()
    region = UnicodeAttribute()
    telephone = UnicodeAttribute()


class AddressesMap(MapAttribute):
    billto = AddressMap()
    shipto = AddressMap()


class DataMap(MapAttribute):
    addresses = AddressesMap()
    items = ListAttribute(of=ItemMap)

