#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
__author__ = 'bibow'

from pynamodb.models import Model
from pynamodb.attributes import (
    MapAttribute, ListAttribute, UnicodeAttribute, NumberAttribute, UnicodeSetAttribute, UTCDateTimeAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, LocalSecondaryIndex, AllProjection


class SourceSrcIdIndex(GlobalSecondaryIndex):
    """
    This class represents a global secondary index
    """
    class Meta:
        # index_name is optional, but can be provided to override the default name
        index_name = 'source-src_id-index'
        read_capacity_units = 2
        write_capacity_units = 1
        # All attributes are projected
        projection = AllProjection()
    # This attribute is the hash key for the index
    # Note that this attribute must also exist
    # in the model
    source  = UnicodeAttribute(hash_key=True)
    src_id  = UnicodeAttribute(range_key=True)


class SourceSKUIndex(GlobalSecondaryIndex):
    """
    This class represents a global secondary index
    """
    class Meta:
        # index_name is optional, but can be provided to override the default name
        index_name = 'source-sku-index'
        read_capacity_units = 2
        write_capacity_units = 1
        # All attributes are projected
        projection = AllProjection()
    # This attribute is the hash key for the index
    # Note that this attribute must also exist
    # in the model
    source  = UnicodeAttribute(hash_key=True)
    sku  = UnicodeAttribute(range_key=True)


class SourceIdentityIndex(GlobalSecondaryIndex):
    """
    This class represents a global secondary index
    """
    class Meta:
        # index_name is optional, but can be provided to override the default name
        index_name = 'source-identity-index'
        read_capacity_units = 2
        write_capacity_units = 1
        # All attributes are projected
        projection = AllProjection()
    # This attribute is the hash key for the index
    # Note that this attribute must also exist
    # in the model
    source  = UnicodeAttribute(hash_key=True)
    identity  = UnicodeAttribute(range_key=True)


class BaseModel(Model):
    class Meta:
        region = 'us-west-2'
        billing_mode = 'PAY_PER_REQUEST'
    id = UnicodeAttribute(hash_key=True)
    source = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    tx_note = UnicodeAttribute()
    tx_status = UnicodeAttribute()


class TransactionModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = 'transaction'
    src_id = UnicodeAttribute()
    tgt_id = UnicodeAttribute(default='#####')
    type = UnicodeAttribute()
    data = MapAttribute()
    history = ListAttribute(of=MapAttribute)
    source_index = SourceSrcIdIndex()


class ProductModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = 'product'
    sku = UnicodeAttribute()
    tgt_id = UnicodeAttribute(default='#####')
    attribute_set = UnicodeAttribute()
    data = MapAttribute()
    raw_data = MapAttribute()
    old_data = ListAttribute()
    source_index = SourceSKUIndex()


class ProductExtModel(Model):
    class Meta(BaseModel.Meta):
        table_name = 'productext'
    sku = UnicodeAttribute()
    tgt_id = UnicodeAttribute(default='#####')
    type = UnicodeAttribute()
    data = ListAttribute()
    source_index = SourceSKUIndex()


class ProductImageGalleryModel(Model):
    class Meta(BaseModel.Meta):
        table_name = 'productimagegallery'
    sku = UnicodeAttribute()
    tgt_id = UnicodeAttribute(default='#####')
    data = MapAttribute()
    source_index = SourceSKUIndex()


class BusinessEntityModel(Model):
    class Meta(BaseModel.Meta):
        table_name = 'businessentity'
    identity = UnicodeAttribute()
    tgt_id = UnicodeAttribute(default='#####')
    type = UnicodeAttribute()
    data = MapAttribute()
    source_index = SourceIdentityIndex()