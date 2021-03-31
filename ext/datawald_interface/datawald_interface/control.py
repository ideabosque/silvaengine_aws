#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
__author__ = 'bibow'

import os
from datawald_model.models import SyncControl, TransactionModel

class Control(object):

    def __init__(self, logger, **setting):
        self.logger = logger
        self.setting = setting

    def get_task(self, table, id):
        task = {"ready": 0}
        if table == 'Transaction':
            entity = TransactionModel.get(id)
        
        task['source'] = entity.source
        task['id'] = id
        task['src_id'] = entity.src_id
        task['tgt_id'] = entity.tgt_id
        task['task_status'] = entity.tx_status
        task['task_note'] = entity.tx_note
        task['updated_at'] = entity.updated_at

        if task["task_status"] != 'N':
            task["ready"] = 1
        
        return task

    def get_cut_date(self, frontend, task):
        cut_date = os.environ["DEFAULTCUTDATE"]
        offset = 0
        sync_statuses = ['Completed', 'Fail', 'Incompleted', 'Processing']
        sync_tasks = [
            sync_task for sync_task in SyncControl.frontend_index.query(
                task, 
                frontend, 
                SyncControl.sync_status.is_in(*sync_statuses)
            )
        ]

        if len(sync_tasks) > 0:
            last_sync_task = max(
                sync_tasks,
                key=lambda sync_task:(
                    sync_task.cut_date,
                    int(sync_task.offset)
                )
            )
            id = last_sync_task.id
            cut_date = last_sync_task.cut_date
            offset = int(last_sync_task.offset)
        self.flush_sync_control(id, frontend, task)
        return cut_date, offset

    def flush_sync_control(self, id, frontend, task):
        ## 
        pass

    def insert_sync_control(self, backoffice, frontend, task, table, sync_task):
        ## 
        pass

    def update_sync_control(self, id, entities):
        ## 
        pass

    def get_sync_task(self, id):
        ## 
        pass

    def del_sync_task(self, id):
        ## 
        pass

    def dispatch_sync_task(self, backoffice, frontend, table, id, entities):
        ## 
        pass