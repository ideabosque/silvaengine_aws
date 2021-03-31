#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
__author__ = 'bibow'

from pynamodb.models import Model
from pynamodb.attributes import (
    MapAttribute, ListAttribute, UnicodeAttribute, NumberAttribute, UnicodeSetAttribute, UTCDateTimeAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, LocalSecondaryIndex, AllProjection


class BaseLocalSecondaryIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """
    class Meta:
        billing_mode = 'PAY_PER_REQUEST'
        # All attributes are projected
        projection = AllProjection()


class BaseGlobalSecondaryIndex(GlobalSecondaryIndex):
    """
    This class represents a global secondary index
    """
    class Meta:
        # index_name is optional, but can be provided to override the default name
        billing_mode = 'PAY_PER_REQUEST'
        # All attributes are projected
        projection = AllProjection()


class SourceSrcIdIndex(BaseLocalSecondaryIndex):
    """
    This class represents a global secondary index
    """
    class Meta(BaseLocalSecondaryIndex.Meta):
        # index_name is optional, but can be provided to override the default name
        index_name = 'source-src_id-index'
    # This attribute is the hash key for the index
    # Note that this attribute must also exist
    # in the model
    source = UnicodeAttribute(hash_key=True)
    src_id = UnicodeAttribute(range_key=True)


class SourceSKUIndex(BaseLocalSecondaryIndex):
    class Meta(BaseLocalSecondaryIndex.Meta):
        # index_name is optional, but can be provided to override the default name
        index_name = 'source-sku-index'
    # This attribute is the hash key for the index
    # Note that this attribute must also exist
    # in the model
    source = UnicodeAttribute(hash_key=True)
    sku = UnicodeAttribute(range_key=True)


class SourceIdentityIndex(BaseLocalSecondaryIndex):
    class Meta(BaseLocalSecondaryIndex.Meta):
        # index_name is optional, but can be provided to override the default name
        index_name = 'source-identity-index'
    # This attribute is the hash key for the index
    # Note that this attribute must also exist
    # in the model
    source = UnicodeAttribute(hash_key=True)
    identity = UnicodeAttribute(range_key=True)


class TaskFrontendIndex(BaseLocalSecondaryIndex):
    class Meta(BaseLocalSecondaryIndex.Meta):
        # index_name is optional, but can be provided to override the default name
        index_name = 'task-frontend-index'
    # This attribute is the hash key for the index
    # Note that this attribute must also exist
    # in the model
    task = UnicodeAttribute(hash_key=True)
    frontend  = UnicodeAttribute(range_key=True)


class TaskBackOfficeIndex(BaseLocalSecondaryIndex):
    class Meta(BaseLocalSecondaryIndex.Meta):
        # index_name is optional, but can be provided to override the default name
        index_name = 'task-backoffice-index'
    # This attribute is the hash key for the index
    # Note that this attribute must also exist
    # in the model
    task = UnicodeAttribute(hash_key=True)
    backoffice = UnicodeAttribute(range_key=True)


class BaseModel(Model):
    class Meta:
        billing_mode = 'PAY_PER_REQUEST'
    

class EntityBaseModel(BaseModel):
    class Meta(BaseModel.Meta):
        pass
    source = UnicodeAttribute(hash_key=True)
    id = UnicodeAttribute(range_key=True)
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    tx_note = UnicodeAttribute()
    tx_status = UnicodeAttribute()


class TransactionModel(EntityBaseModel):
    class Meta(EntityBaseModel.Meta):
        table_name = 'dw-transaction'
    src_id = UnicodeAttribute()
    tgt_id = UnicodeAttribute(default='#####')
    type = UnicodeAttribute()
    data = MapAttribute()
    history = ListAttribute(of=MapAttribute)
    source_index = SourceSrcIdIndex()


class ProductModel(EntityBaseModel):
    class Meta(EntityBaseModel.Meta):
        table_name = 'product'
    sku = UnicodeAttribute()
    tgt_id = UnicodeAttribute(default='#####')
    attribute_set = UnicodeAttribute()
    data = MapAttribute()
    raw_data = MapAttribute()
    old_data = ListAttribute()
    source_index = SourceSKUIndex()


class ProductExtModel(EntityBaseModel):
    class Meta(EntityBaseModel.Meta):
        table_name = 'productext'
    sku = UnicodeAttribute()
    tgt_id = UnicodeAttribute(default='#####')
    type = UnicodeAttribute()
    data = ListAttribute()
    source_index = SourceSKUIndex()


class ProductImageGalleryModel(EntityBaseModel):
    class Meta(EntityBaseModel.Meta):
        table_name = 'productimagegallery'
    sku = UnicodeAttribute()
    tgt_id = UnicodeAttribute(default='#####')
    data = MapAttribute()
    source_index = SourceSKUIndex()


class BusinessEntityModel(EntityBaseModel):
    class Meta(EntityBaseModel.Meta):
        table_name = 'businessentity'
    identity = UnicodeAttribute()
    tgt_id = UnicodeAttribute(default='#####')
    type = UnicodeAttribute()
    data = MapAttribute()
    source_index = SourceIdentityIndex()


class SyncControlEntityMap(MapAttribute):
    id = UnicodeAttribute()
    src_id = UnicodeAttribute()
    tgt_id = UnicodeAttribute()
    task_note = UnicodeAttribute()
    task_status = UnicodeAttribute()
    updated_at = UnicodeAttribute()


class SyncControl(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = 'synccontrol'
    task = UnicodeAttribute(hash_key=True)
    id = UnicodeAttribute(range_key=True)
    frontend = UnicodeAttribute()
    backoffice = UnicodeAttribute()
    cut_date = UTCDateTimeAttribute()
    start_date = UTCDateTimeAttribute()
    end_date = UTCDateTimeAttribute()
    offset = NumberAttribute()
    store_code = UnicodeAttribute()
    table = UnicodeAttribute()
    task = UnicodeAttribute()
    sync_note = UnicodeAttribute()
    sync_status = UnicodeAttribute()
    entities = ListAttribute(of=SyncControlEntityMap)
    frontend_index = TaskFrontendIndex()
    backoffice_index = TaskBackOfficeIndex()