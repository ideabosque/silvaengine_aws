#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
__author__ = 'bibow'

from datawald_model.models import SyncControl, TransactionModel

class Control(object):

    def __init__(self, logger, **setting):
        self.logger = logger
        self.setting = setting

    def get_task(self, table, id):
        task = {"ready": 0}
        if table == 'Transaction':
            entity = TransactionModel.get(id)
        
        task['id'] = id
        task['src_id'] = entity.src_id
        task['tgt_id'] = entity.tgt_id
        task['task_status'] = entity.tx_status
        task['task_note'] = entity.tx_note
        task['updated_at'] = entity.updated_at

        if task["task_status"] not in ["N", "P"]:
            task["ready"] = 1
        
        return task

    def get_cut_dt(self, frontend, task):
        ## 
        pass

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