#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
__author__ = 'bibow'

import uuid, json, traceback
from datetime import datetime, date
from decimal import Decimal
from datawald_model.common_object_types import InputType, TransactionStatusInputType, TransactionInputType
from datawald_model.models import BaseModel, TransactionModel
from pynamodb.attributes import (
    MapAttribute, ListAttribute, UnicodeAttribute, NumberAttribute, UnicodeSetAttribute, UTCDateTimeAttribute
)
from graphene import Field, ObjectType, Schema, Mutation, Boolean
from silvaengine_utility import Utility


class BackOffice(object):

    def __init__(self, logger, **setting):
        self.logger = logger
        self.setting = setting
        if 'region_name' in setting.keys() and \
            'aws_access_key_id' in setting.keys() and \
                'aws_secret_access_key' in setting.keys():
            BaseModel.Meta.region = setting.get('region_name')
            BaseModel.Meta.aws_access_key_id = setting.get(
                'aws_access_key_id')
            BaseModel.Meta.aws_secret_access_key = setting.get(
                'aws_secret_access_key')

        self.order_status = setting.get("order_status", [])

        self.order_object_types_module = __import__(
            self.setting.get("order_object_types_module", "datawald_model.order_object_types")
        )
        self.order_type_class = getattr(self.order_object_types_module, 'OrderType')
        
        self.itemreceipt_object_types_module = __import__(
            self.setting.get("itemreceipt_object_types_module", "datawald_model.itemreceipt_object_types")
        )
        self.itemreceipt_type_class = getattr(self.itemreceipt_object_types_module, 'ItemReceiptType')

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

    def get_transaction(self, source, src_id, tx_type=None):
        transaction = self._get_transaction(source, src_id, tx_type)
        if tx_type == "order":
            transaction_type_class = self.order_type_class
        elif tx_type == "itemreceipt":
            transaction_type_class = self.itemreceipt_type_class

        if transaction is None:
            return None

        return transaction_type_class(**Utility.json_loads(
                Utility.json_dumps(transaction.__dict__['attribute_values'])
            )
        )

    def insert_transaction(self, transaction, tx_type=None):
        tx_status = 'N'

        _id = str(uuid.uuid1())
        created_at = datetime.utcnow()
        history = []

        count = TransactionModel.source_index.count(
            transaction["source"], 
            TransactionModel.src_id==transaction["src_id"]
        )

        if count >= 1:
            results = TransactionModel.source_index.query(
                transaction["source"], 
                TransactionModel.src_id==transaction["src_id"]
            )
            _transaction = results.next()
            _id = _transaction.id
            created_at = _transaction.created_at

            data = _transaction.data.__dict__["attribute_values"]
            changed_values = [{k: v} for k, v in transaction["data"].items() if data[k] != v]
            if len(changed_values) > 0:
                _transaction.data.tgt_id = _transaction.tgt_id
                _transaction.data.updated_at = _transaction.updated_at.strftime("%Y-%m-%dT%H:%M:%S")
                history = _transaction.history + [_transaction.data]
            else:
                tx_status = 'I'
                return _transaction.update(
                    actions=[
                        TransactionModel.updated_at.set(datetime.utcnow()),
                        TransactionModel.tx_note.set(
                            "No update {tx_type}: {source}/{src_id}".format(
                                tx_type=tx_type,
                                source=transaction["source"], 
                                src_id=transaction["src_id"]
                            )
                        ),
                        TransactionModel.tx_status.set(tx_status)
                    ]
                )
        
        transaction_model = TransactionModel(
            _id,
            **{
                'source': transaction["source"],
                'src_id': transaction['src_id'],
                'type': tx_type,
                'data': transaction["data"],
                'history': history,
                'created_at': created_at,
                'updated_at': datetime.utcnow(),
                'tx_note': '{source} -> DataWald'.format(source=transaction["source"]),
                'tx_status': tx_status
            }
        )

        return transaction_model.save()

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
            order = Field(self.order_type_class, input=InputType(required=True))
            itemreceipt = Field(self.itemreceipt_type_class, input=InputType(required=True))

            def resolve_order(self, info, input):
                return outer.get_transaction(input.source, input.src_id, tx_type="order")

            def resolve_itemreceipt(self, info, input):
                return outer.get_transaction(input.source, input.src_id, tx_type="itemreceipt")

        ## Mutation ##

        class InsertOrder(Mutation):
            class Arguments:
                order_input = TransactionInputType(required=True)
            
            order = Field(self.order_type_class)
            @staticmethod
            def mutate(root, info, order_input=None):
                try:
                    self.insert_transaction(
                        {
                            "source": order_input.source,
                            "src_id": order_input.src_id,
                            "data": json.loads(order_input.data)
                        },
                        tx_type='order'
                    )
                    order = self.get_transaction(order_input.source, order_input.src_id, "order")
                except Exception:
                    log = traceback.format_exc()
                    self.logger.exception(log)
                    raise

                return InsertOrder(order=order)

        class InsertItemReceipt(Mutation):
            class Arguments:
                itemreceipt_input = TransactionInputType(required=True)
            
            itemreceipt = Field(self.itemreceipt_type_class)
            @staticmethod
            def mutate(root, info, itemreceipt_input=None):
                try:
                    self.insert_transaction(
                        {
                            "source": itemreceipt_input.source,
                            "src_id": itemreceipt_input.src_id,
                            "data": json.loads(itemreceipt_input.data)
                        },
                        tx_type='itemreceipt'
                    )
                    itemreceipt = self.get_transaction(itemreceipt_input.source, itemreceipt_input.src_id, "itemreceipt")
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

        schema = Schema(query=Query, mutation=Mutations, types=[self.order_type_class, self.itemreceipt_type_class])

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

