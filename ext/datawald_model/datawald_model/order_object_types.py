#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
__author__ = 'bibow'

from graphene import ObjectType, InputObjectType, String, Decimal, DateTime, List, Field


class OrderItemType(ObjectType):
    price = Decimal()
    qty = Decimal()
    sku = String()


class AddressType(ObjectType):
    address = String()
    city = String()
    company = String()
    country = String()
    email = String()
    firstname = String()
    lastname = String()
    postcode = String()
    region = String()
    telephone = String()


class AddressesType(ObjectType):
    billto = Field(AddressType)
    shipto = Field(AddressType)


class OrderDataType(ObjectType):
    addresses = Field(AddressesType)
    items = List(OrderItemType)


class OrderType(ObjectType):
    id = String()
    source = String()
    src_id = String()
    tgt_id = String()
    type = String()
    data = Field(OrderDataType)
    history = List(OrderDataType)
    created_at = DateTime()
    updated_at = DateTime()
    tx_note = String()
    tx_status = String()




class OrderInputType(InputObjectType):
    source = String(required=True)
    src_id = String(required=True)
    order_status = String()
    data = String()