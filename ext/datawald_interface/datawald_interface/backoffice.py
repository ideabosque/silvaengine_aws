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
        self.order_status = setting.get("order_status", [])

        self.common_object_types_module =  __import__(
            self.setting.get("common_object_types_module", "datawald_model.common_object_types")
        )
        self.input_type_class = getattr(self.common_object_types_module, 'InputType')
        self.transaction_status_input_type_class = getattr(self.common_object_types_module, 'TransactionStatusInputType')
        
        self.order_object_types_module = __import__(
            self.setting.get("order_object_types_module", "datawald_model.order_object_types")
        )
        self.order_type_class = getattr(self.order_object_types_module, 'OrderType')
        self.order_input_type_class = getattr(self.order_object_types_module, 'OrderInputType')
        
        self.itemreceipt_object_types_module = __import__(
            self.setting.get("itemreceipt_object_types_module", "datawald_model.itemreceipt_object_types")
        )
        self.itemreceipt_type_class = getattr(self.itemreceipt_object_types_module, 'ItemReceiptType')
        self.itemreceipt_input_type_class = getattr(self.itemreceipt_object_types_module, 'ItemReceiptInputType')

    def _get_transaction(self, source, src_id, tx_type):
        count = TransactionModel.source_index.count(
            source, 
            TransactionModel.src_id==src_id,
            TransactionModel.type==tx_type
        )
        if count >= 0:
            results = TransactionModel.source_index.query(
                source, 
                TransactionModel.src_id==src_id,
                TransactionModel.type==tx_type
            )
            return results.next()
        else:
            return None

    def get_transaction(self, source, src_id, tx_type):
        transaction = self._get_transaction(source, src_id, tx_type)
        if tx_type == "order":
            item_type_class = getattr(self.order_object_types_module, 'OrderItemType')
            transaction_type_class = self.order_type_class
        elif tx_type == "itemreceipt":
            item_type_class = getattr(self.itemreceipt_object_types_module, 'ItemReceiptItemType')
            transaction_type_class = self.itemreceipt_type_class

        if transaction is not None:
            transaction.data.items = [
                item_type_class(**dict(
                        (
                            k, 
                            Decimal(str(v)) if isinstance(v, (float, int)) else v
                        ) for k, v in item.items()
                    )
                ) for item in transaction.data.items
            ]
            return transaction_type_class(**transaction.__dict__['attribute_values'])
        else:
            return {}

    def insert_order(self, order):
        order_map_attributes_module = __import__(
            self.setting.get("order_map_attributes_module", "datawald_model.order_map_attributes")
        )
        data_class = getattr(order_map_attributes_module, 'OrderDataMap')
        item_class = getattr(order_map_attributes_module, 'OrderItemMap')

        tx_status = 'N' if order.get('order_status', 'new').lower() in self.order_status else 'I'  # N or I

        id = str(uuid.uuid1())
        created_at = datetime.utcnow()

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
            created_at = _order.created_at
            if _order.tx_status == 'N':
                tx_status = 'P'
            elif tx_status == 'N' and _order.tx_status == 'F':
                tx_status = 'N'
            else:
                tx_status = _order.tx_status

        order['data']['items'] = [
            item_class(**dict(
                    (
                        k, 
                        float(item[k]) if isinstance(v, NumberAttribute) else item[k]
                    ) for k, v in item_class.__dict__["_attributes"].items()
                )
            ) for item in order['data']['items']
        ]
        order_model = TransactionModel(
            id,
            **{
                'source': order["source"],
                'src_id': order["src_id"],
                'type': 'order',
                'data': data_class(**order['data']),
                'history': [],
                'created_at': created_at,
                'updated_at': datetime.utcnow(),
                'tx_note': '{source} -> DataWald'.format(source=order["source"]),
                'tx_status': tx_status
            }
        )

        return order_model.save()

    def insert_item_receipt(self, item_receipt):
        item_receipt_map_attributes_module = __import__(
            self.setting.get("itemreceipt_map_attributes_module", "datawald_model.itemreceipt_map_attributes")
        )
        data_class = getattr(item_receipt_map_attributes_module, 'ItemReceiptDataMap')
        item_class = getattr(item_receipt_map_attributes_module, 'ItemReceiptItemMap')

        tx_status = 'N'

        id = str(uuid.uuid1())
        created_at = datetime.utcnow()
        history = []

        count = TransactionModel.source_index.count(
            item_receipt["source"], 
            TransactionModel.src_id==item_receipt["src_id"]
        )

        if count >= 1:
            results = TransactionModel.source_index.query(
                item_receipt["source"], 
                TransactionModel.src_id==item_receipt["src_id"]
            )
            _item_receipt = results.next()
            id = _item_receipt.id
            created_at = _item_receipt.created_at

            data = _item_receipt.data.__dict__["attribute_values"]
            changed_values = [{k: v} for k, v in item_receipt["data"].items() if data[k] != v]
            if len(changed_values) > 0:
                _item_receipt.data.itemreceipt_id = _item_receipt.tgt_id 
                history = _item_receipt.history + [_item_receipt.data]
            else:
                tx_status = 'I'
                return _item_receipt.update(
                    actions=[
                        TransactionModel.updated_at.set(datetime.utcnow()),
                        TransactionModel.tx_note.set(
                            "No update item recepit: {0}/{1}".format(item_receipt["source"], item_receipt["src_id"])
                        ),
                        TransactionModel.tx_status.set(tx_status)
                    ]
                )

        item_receipt["data"]["items"] = [
            item_class(**dict(
                    (
                        k, 
                        float(item[k]) if isinstance(v, NumberAttribute) else item[k]
                    ) for k, v in item_class.__dict__["_attributes"].items()
                )
            ) for item in item_receipt["data"]["items"]
        ]
        
        item_receipts_model = TransactionModel(
            id,
            **{
                'source': item_receipt["source"],
                'src_id': item_receipt['src_id'],
                'type': 'itemreceipt',
                'data': data_class(**item_receipt["data"]),
                'history': history,
                'created_at': created_at,
                'updated_at': datetime.utcnow(),
                'tx_note': '{source} -> DataWald'.format(source=item_receipt["source"]),
                'tx_status': tx_status
            }
        )

        return item_receipts_model.save()

    def update_transaction_status(self, id, transaction_status):
        transaction_model = TransactionModel.get(id)

        return transaction_model.update(
            actions=[
                TransactionModel.tgt_id.set(transaction_status['tgt_id']),
                TransactionModel.updated_at.set(datetime.utcnow()),
                TransactionModel.tx_note.set(transaction_status['tx_note']),
                TransactionModel.tx_status.set(transaction_status['tx_status'])
            ]
        )

    def backoffice_graphql(self, **params):
        outer = self

        class Query(ObjectType):
            order = Field(outer.order_type_class, input=outer.input_type_class(required=True))
            itemreceipt = Field(outer.itemreceipt_type_class, input=outer.input_type_class(required=True))

            def resolve_order(self, info, input):
                return outer.get_transaction(input.source, input.src_id, "order")

            def resolve_itemreceipt(self, info, input):
                return outer.get_transaction(input.source, input.src_id, "itemreceipt")

        ## Mutation ##

        class InsertOrder(Mutation):
            class Arguments:
                order_input = outer.order_input_type_class(required=True)
            
            order = Field(outer.order_type_class)
            @staticmethod
            def mutate(root, info, order_input=None):
                try:
                    self.insert_order(
                        {
                            "source": order_input.source,
                            "src_id": order_input.src_id,
                            "order_status": order_input.order_status,
                            "data": json.loads(order_input.data)
                        }
                    )
                    order = outer.get_transaction(order_input.source, order_input.src_id, "order")
                except Exception:
                    log = traceback.format_exc()
                    self.logger.exception(log)
                    raise

                return InsertOrder(order=order)

        class InsertItemReceipt(Mutation):
            class Arguments:
                itemreceipt_input = outer.itemreceipt_input_type_class(required=True)
            
            itemreceipt = Field(outer.itemreceipt_type_class)
            @staticmethod
            def mutate(root, info, itemreceipt_input=None):
                try:
                    self.insert_item_receipt(
                        {
                            "source": itemreceipt_input.source,
                            "src_id": itemreceipt_input.src_id,
                            "data": json.loads(itemreceipt_input.data)
                        }
                    )
                    itemreceipt = outer.get_transaction(itemreceipt_input.source, itemreceipt_input.src_id, "itemreceipt")
                except Exception:
                    log = traceback.format_exc()
                    self.logger.exception(log)
                    raise

                return InsertItemReceipt(itemreceipt=itemreceipt)

        class UpdateTransactionStatus(Mutation):
            class Arguments:
                transaction_status_input = outer.transaction_status_input_type_class(required=True)
            
            status = Boolean()
            @staticmethod
            def mutate(root, info, transaction_status_input=None):
                try:
                    self.update_transaction_status(
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

        schema = Schema(query=Query, mutation=Mutations, types=[outer.order_type_class, outer.itemreceipt_type_class])

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
        return Utility.json_dumps(response)

