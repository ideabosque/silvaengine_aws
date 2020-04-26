#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
__author__ = 'bibow'

import uuid, json, traceback
from datetime import datetime, date
from decimal import Decimal
from datawald_model.models import TransactionModel
from pynamodb.attributes import (
    MapAttribute, ListAttribute, UnicodeAttribute, NumberAttribute, UnicodeSetAttribute, UTCDateTimeAttribute
)
from graphene import Field, ObjectType, Schema, Mutation, Boolean
from silvaengine_utility import Utility
from decimal import Decimal


class ModelEncoder(json.JSONEncoder):
    
    def default(self, obj):   # pylint: disable=E0202
        if isinstance(obj, Decimal):
            if obj % 1 > 0:
                return float(obj)
            else:
                return str(obj)
        if hasattr(obj, 'attribute_values'):
            return obj.attribute_values
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, (bytes, bytearray)):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)


class BackOffice(object):

    def __init__(self, logger, **setting):
        self.logger = logger
        self.setting = setting
        self.orderStatus = setting.get("order_status", [])

    def insertOrder(self, order):
        OrderMapAttributesModule = __import__(
            self.setting.get("order_map_attributes_module", "datawald_model.order_map_attributes")
        )
        Data = getattr(OrderMapAttributesModule, 'DataMap')
        Item = getattr(OrderMapAttributesModule, 'ItemMap')

        txStatus = 'N' if order.get('order_status', 'new').lower() in self.orderStatus else 'I'  # N or I

        id = str(uuid.uuid1())
        createdAt = datetime.utcnow()

        count = TransactionModel.source_index.count(
            order["source"], 
            TransactionModel.src_id==order["src_id"]
        )
        
        if count >= 1:
            results = TransactionModel.source_index.query(
                order["source"], 
                TransactionModel.src_id==order["src_id"]
            )
            _order = results.next()
            id = _order.id
            createdAt = _order.created_at
            if _order.tx_status == 'N':
                txStatus = 'P'
            elif txStatus == 'N' and _order.tx_status == 'F':
                txStatus = 'N'
            else:
                txStatus = _order.tx_status

        order['data']['items'] = [
            Item(**dict(
                    (
                        k, 
                        float(item[k]) if isinstance(v, NumberAttribute) else item[k]
                    ) for k, v in Item.__dict__["_attributes"].items()
                )
            ) for item in order['data']['items']
        ]
        orderModel = TransactionModel(
            id,
            **{
                'source': order["source"],
                'src_id': order["src_id"],
                'type': 'order',
                'data': Data(**order['data']),
                'history': [],
                'created_at': createdAt,
                'updated_at': datetime.utcnow(),
                'tx_note': '{source} -> DataWald'.format(source=order["source"]),
                'tx_status': txStatus
            }
        )

        return orderModel.save()

    def insertItemReceipt(self, itemReceipt):
        ItemReceiptMapAttributesModule = __import__(
            self.setting.get("itemreceipt_map_attributes_module", "datawald_model.itemreceipt_map_attributes")
        )
        Data = getattr(ItemReceiptMapAttributesModule, 'DataMap') 
        Item = getattr(ItemReceiptMapAttributesModule, 'ItemMap')

        txStatus = 'N'

        id = str(uuid.uuid1())
        createdAt = datetime.utcnow()
        history = []

        count = TransactionModel.source_index.count(
            itemReceipt["source"], 
            TransactionModel.src_id==itemReceipt["src_id"]
        )

        if count >= 1:
            results = TransactionModel.source_index.query(
                itemReceipt["source"], 
                TransactionModel.src_id==itemReceipt["src_id"]
            )
            _itemReceipt = results.next()
            id = _itemReceipt.id
            createdAt = _itemReceipt.created_at

            data = _itemReceipt.data.__dict__["attribute_values"]
            changedValues = [{k: v} for k, v in itemReceipt["data"].items() if data[k] != v]
            if len(changedValues) > 0:
                _itemReceipt.data.itemreceipt_id = _itemReceipt.tgt_id 
                history = _itemReceipt.history + [_itemReceipt.data]
            else:
                txStatus = 'I'
                return _itemReceipt.update(
                    actions=[
                        TransactionModel.updated_at.set(datetime.utcnow()),
                        TransactionModel.tx_note.set(
                            "No update item recepit: {0}/{1}".format(itemReceipt["source"], itemReceipt["src_id"])
                        ),
                        TransactionModel.tx_status.set(txStatus)
                    ]
                )

        itemReceipt["data"]["items"] = [
            Item(**dict(
                    (
                        k, 
                        float(item[k]) if isinstance(v, NumberAttribute) else item[k]
                    ) for k, v in Item.__dict__["_attributes"].items()
                )
            ) for item in itemReceipt["data"]["items"]
        ]
        
        itemReceiptsModel = TransactionModel(
            id,
            **{
                'source': itemReceipt["source"],
                'src_id': itemReceipt['src_id'],
                'type': 'itemreceipt',
                'data': Data(**itemReceipt["data"]),
                'history': history,
                'created_at': createdAt,
                'updated_at': datetime.utcnow(),
                'tx_note': '{source} -> DataWald'.format(source=itemReceipt["source"]),
                'tx_status': txStatus
            }
        )

        return itemReceiptsModel.save()

    def updateTransactionStatus(self, id, transactionStatus):
        transactionModel = TransactionModel.get(id)

        return transactionModel.update(
            actions=[
                TransactionModel.tgt_id.set(transactionStatus['tgt_id']),
                TransactionModel.updated_at.set(datetime.utcnow()),
                TransactionModel.tx_note.set(transactionStatus['tx_note']),
                TransactionModel.tx_status.set(transactionStatus['tx_status'])
            ]
        )

    def backofficeGraphql(self, **params):
        CommonObjectTypesModule =  __import__(
            self.setting.get("common_object_types_module", "datawald_model.common_object_types")
        )
        InputType = getattr(CommonObjectTypesModule, 'InputType')
        TransactionStatusInputType = getattr(CommonObjectTypesModule, 'TransactionStatusInputType')
        
        OrderObjectTypesModule = __import__(
            self.setting.get("order_object_types_module", "datawald_model.order_object_types")
        )
        OrderType = getattr(OrderObjectTypesModule, 'OrderType')
        OrderInputType = getattr(OrderObjectTypesModule, 'OrderInputType')
        
        ItemreceiptObjectTypesModule = __import__(
            self.setting.get("itemreceipt_object_types_module", "datawald_model.itemreceipt_object_types")
        )
        ItemReceiptType = getattr(ItemreceiptObjectTypesModule, 'ItemReceiptType')
        ItemReceiptInputType = getattr(ItemreceiptObjectTypesModule, 'ItemReceiptInputType')

        # outer = self
        def _getTransaction(source, src_id, txType):
            count = TransactionModel.source_index.count(
                source, 
                TransactionModel.src_id==src_id,
                TransactionModel.type==txType
            )
            if count >= 0:
                results = TransactionModel.source_index.query(
                    source, 
                    TransactionModel.src_id==src_id,
                    TransactionModel.type==txType
                )
                return results.next()
            else:
                return None

        def getTransaction(source, src_id, txType):
            transaction = _getTransaction(source, src_id, txType)
            if txType == "order":
                ItemType = getattr(OrderObjectTypesModule, 'OrderItemType')
                TransactionType = OrderType
            elif txType == "itemreceipt":
                ItemType = getattr(ItemreceiptObjectTypesModule, 'ItemReceiptItemType')
                TransactionType = ItemReceiptType

            if transaction is not None:
                transaction.data.items = [
                    ItemType(**dict(
                            (
                                k, 
                                Decimal(str(v)) if isinstance(v, (float, int)) else v
                            ) for k, v in item.items()
                        )
                    ) for item in transaction.data.items
                ]
                return TransactionType(**transaction.__dict__['attribute_values'])
            else:
                return {}

        class Query(ObjectType):
            order = Field(OrderType, input=InputType(required=True))
            itemreceipt = Field(ItemReceiptType, input=InputType(required=True))

            def resolve_order(self, info, input):
                return getTransaction(input.source, input.src_id, "order")

            def resolve_itemreceipt(self, info, input):
                return getTransaction(input.source, input.src_id, "itemreceipt")

        ## Mutation ##

        class InsertOrder(Mutation):
            class Arguments:
                order_input = OrderInputType(required=True)
            
            order = Field(OrderType)
            @staticmethod
            def mutate(root, info, order_input=None):
                try:
                    self.insertOrder(
                        {
                            "source": order_input.source,
                            "src_id": order_input.src_id,
                            "order_status": order_input.order_status,
                            "data": json.loads(order_input.data)
                        }
                    )
                    order = getTransaction(order_input.source, order_input.src_id, "order")
                except Exception:
                    log = traceback.format_exc()
                    self.logger.exception(log)
                    raise

                return InsertOrder(order=order)

        class InsertItemReceipt(Mutation):
            class Arguments:
                itemreceipt_input = ItemReceiptInputType(required=True)
            
            itemreceipt = Field(ItemReceiptType)
            @staticmethod
            def mutate(root, info, itemreceipt_input=None):
                try:
                    self.insertItemReceipt(
                        {
                            "source": itemreceipt_input.source,
                            "src_id": itemreceipt_input.src_id,
                            "data": json.loads(itemreceipt_input.data)
                        }
                    )
                    itemreceipt = getTransaction(itemreceipt_input.source, itemreceipt_input.src_id, "itemreceipt")
                except Exception:
                    log = traceback.format_exc()
                    self.logger.exception(log)
                    raise

                return InsertItemReceipt(itemreceipt=itemreceipt)

        class UpdateTransactionStatus(Mutation):
            class Arguments:
                transaction_status_input = TransactionStatusInputType(required=True)
            
            status = Boolean()
            @staticmethod
            def mutate(root, info, transaction_status_input=None):
                try:
                    self.updateTransactionStatus(
                        transaction_status_input.id,
                        {
                            "tgt_id": transaction_status_input.tgt_id,
                            "tx_note": transaction_status_input.tx_note,
                            "tx_status": transaction_status_input.tx_status
                        } 
                    )
                    status = True
                except Exception:
                    log = traceback.format_exc()
                    self.logger.exception(log)
                    raise

                return UpdateTransactionStatus(status=status)

        class Mutations(ObjectType):
            insert_order = InsertOrder.Field()
            insert_itemreceipt = InsertItemReceipt.Field()
            update_transaction_status = UpdateTransactionStatus.Field()

        ## Mutation ##

        schema = Schema(query=Query, mutation=Mutations, types=[OrderType, ItemReceiptType])

        variables = params.get("variables", {})
        query = params.get("query")
        if query is not None:
            result = schema.execute(query, variables=variables)
        mutation = params.get("mutation")
        if mutation is not None:
            result = schema.execute(mutation, variables=variables)

        response = {
            "data": dict(result.data) if result.data != None else None,
        }
        if (result.errors != None):
            response['errors'] = [str(error) for error in result.errors]
        return Utility.jsonDumps(response)

