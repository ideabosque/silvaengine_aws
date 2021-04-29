#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import os, uuid, boto3, traceback
from datetime import datetime
from time import sleep
from silvaengine_utility import Utility
from datawald_model.models import SyncControlModel, SyncTaskEntityMap, TransactionModel


class Control(object):

    sqs = boto3.client("sqs")
    aws_lambda = boto3.client("lambda")

    def __init__(self, logger, **setting):
        self.logger = logger
        self.setting = setting

    def entity_model(self, table):
        _entity_model = {"transaction": TransactionModel}
        return _entity_model.get(table)

    # Add GraphQL Query.
    def get_task(self, table, source, id):
        entity_model = self.entity_model(table)
        assert entity_model is not None, f"The table ({table}) is not supported."

        entity = entity_model.get(source, id)

        return {
            "source": source,
            "id": id,
            "task_status": entity.tx_status,
            "task_note": entity.tx_note,
            "updated_at": entity.updated_at,
            "ready": 1 if entity.tx_status != "N" else 0,
        }

    # Add GraphQL Query.
    def get_cut_date(self, source, task):
        cut_date = os.environ["DEFAULTCUTDATE"]
        offset = 0
        sync_statuses = ["Completed", "Fail", "Incompleted", "Processing"]
        sync_tasks = [
            sync_task
            for sync_task in SyncControlModel.task_source_index.query(
                task,
                SyncControlModel.source == source,
                SyncControlModel.sync_status.is_in(*sync_statuses),
            )
        ]

        if len(sync_tasks) > 0:
            last_sync_task = max(
                sync_tasks,
                key=lambda sync_task: (sync_task.cut_date, int(sync_task.offset)),
            )
            id = last_sync_task.id
            cut_date = last_sync_task.cut_date
            offset = int(last_sync_task.offset)

            # Flsuh Sync Control Table by frontend and task.
            self.flush_sync_control(task, source, id)
        return cut_date, offset

    def flush_sync_control(self, task, source, id):
        for sync_task in SyncControlModel.task_source_index.query(
            task, SyncControlModel.source == source
        ):
            sync_task.delete(SyncControlModel.id != id)

    # Add GraphQL Mutation.
    def insert_sync_control(self, source, target, task, table, sync_task):
        id = str(uuid.uuid1().int >> 64)
        sync_control_model = SyncControlModel(
            task,
            id,
            **{
                "source": source,
                "target": target,
                "table": table,
                "sync_status": "Processing",
                "start_date": datetime.utcnow(),
                "cut_date": sync_task["cut_date"],
                "offset": sync_task.get("offset", 0),
                "sync_note": f"Process task ({task}) for source ({source}).",
                "entities": [
                    SyncTaskEntityMap(**entity) for entity in sync_task["entities"]
                ],
            },
        )
        sync_control_model.save()

        if len(sync_control_model.entities) > 0:
            queue_name = f"{source}_{target}_{table}_{id}"[:75] + ".fifo"
            Control.dispatch_sync_task(
                self.logger, task, target, queue_name, sync_control_model.entities
            )

        return sync_control_model

    # Add GraphQL Mutation.
    def update_sync_control(self, task, id, entities):
        sync_status = "Completed"
        if len(list(filter(lambda x: x["task_status"] == "F", entities))) > 0:
            sync_status = "Fail"
        if len(list(filter(lambda x: x["task_status"] == "?", entities))) > 0:
            sync_status = "Incompleted"

        sync_task = SyncControlModel.get(task, id)
        return sync_task.update(
            actions=[
                SyncControlModel.sync_status.set(sync_status),
                SyncControlModel.end_date.set(datetime.utcnow()),
                SyncControlModel.entities.set(
                    [SyncTaskEntityMap(**entity) for entity in entities]
                ),
            ]
        )

    # Add GraphQL Query.
    def get_sync_task(self, task, id):
        return SyncControlModel.get(task, id)

    # Add GraphQL Mutation.
    def del_sync_task(self, task, id):
        sync_task = SyncControlModel.get(task, id)
        sync_task.delete()

    @classmethod
    def dispatch_sync_task(cls, logger, task, target, queue_name, entities):
        max_task_agents = int(os.environ.get("MAXTASKAGENTS", "1"))
        function_name = os.environ["AGENTTASKARN"]

        try:
            task_queue = cls.sqs.create_queue(
                QueueName=queue_name,
                Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
            )

            for entity in entities:
                if entity.tx_status != "N":
                    continue

                task_queue.send_message(
                    MessageBody=Utility.json_dumps(
                        {"source": entity.source, "id": entity.id}
                    ),
                    MessageGroupId=id,
                )

            while max_task_agents:
                cls.aws_lambda.invoke(
                    FunctionName=function_name,
                    InvocationType="Event",
                    Payload=Utility.json_dumps(
                        {"endpoint_id": target, "queue_name": queue_name, "funct": task}
                    ),
                )
                max_task_agents -= 1
                sleep(1)
        except Exception:
            log = traceback.format_exc()
            logger.exception(log)
            raise
