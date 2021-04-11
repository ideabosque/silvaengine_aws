#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import (
    ObjectType,
    InputObjectType,
    String,
    Decimal,
    DateTime,
    List,
    Field,
    DateTime,
)


class ItemReceiptItemType(ObjectType):
    internal_id = String()
    item_no = String()
    qty = Decimal()


class ShipToType(ObjectType):
    address = String()
    city = String()
    contact = String()
    country_code = String()
    name = String()
    shipping = String()
    state = String()
    zip = String()


class ItemReceiptDataType(ObjectType):
    tgt_id = String()
    updated_at = DateTime()
    internal_id = String()
    items = List(ItemReceiptItemType)
    key = String()
    order_date = String()
    ref_no = List(String)
    ship_to = Field(ShipToType)
    status = String()
    tran_ids = List(String)
    update_date = String()


class ItemReceiptType(ObjectType):
    id = String()
    source = String()
    src_id = String()
    tgt_id = String()
    type = String()
    data = Field(ItemReceiptDataType)
    history = List(ItemReceiptDataType)
    created_at = DateTime()
    updated_at = DateTime()
    tx_note = String()
    tx_status = String()
