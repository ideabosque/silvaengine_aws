#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'bibow'

import sys
sys.path.append('/opt')

import json, os, boto3, traceback
from botocore.exceptions import ClientError
from decimal import Decimal


class LambdaBase(object):

    awsLambda = boto3.client('lambda')
    dynamodb = boto3.resource('dynamodb')

    @classmethod
    def getHandler(cls, *args, **kwargs):
        def handler(event, context):
            return cls(*args, **kwargs).handle(event, context)
        return handler

    def handle(self, event, context):
        raise NotImplementedError

    @classmethod
    def invoke(cls, functionName, payload, invocationType="Event"):
        response = cls.awsLambda.invoke(
            FunctionName=functionName,
            InvocationType=invocationType,
            Payload=json.dumps(payload),
        )
        if "FunctionError" in response.keys():
            log = json.loads(response['Payload'].read())
            raise Exception(log)
        if invocationType == "RequestResponse":
            return json.loads(response['Payload'].read())

    @classmethod
    def getItem(cls, table, **key):
        try:
            tableName = "se-{table}".format(table=table)
            response = cls.dynamodb.Table(tableName).get_item(
                Key=key
            )
        except ClientError:
            raise
        else:
            item = response.get("Item", None)
            if item is None:
                log = "Cannot find the item with the key({0})".format(key)
                raise Exception(log)
            return item

    @classmethod
    def getFunction(cls, endpointId, funct, apiKey="#####", method=None):
        # If a task calls this function, the special_connection should be TRUE.
        if endpointId != "0":
            endpoint = cls.getItem(
                "endpoints", **{
                    "endpoint_id": endpointId
                }
            )
            endpointId = endpointId if endpoint.get("special_connection") else "1"
            
        connection = cls.getItem("connections", **{
            "endpoint_id": endpointId,
            "api_key": apiKey            
        })
        functs = list(filter(lambda x: x["function"]==funct, connection["functions"]))

        assert len(functs) == 1, \
            "Cannot find the function({funct}) with endpoint_id({endpoint_id}) and api_key({api_key}).".format(
                funct=funct, 
                endpoint_id=endpointId, 
                api_key=apiKey
            )

        function = cls.getItem("functions", **{
            "aws_lambda_arn": functs[0]["aws_lambda_arn"],
            "function": functs[0]["function"]
        })

        ## Merge the setting in connection and function
        ## (the setting in the funct of a connection will override the setting in the function).
        setting = dict(function["config"].get("setting", {}), **functs[0].get("setting", {}))
        
        if method is not None:
            assert method in function["config"]["methods"], \
                "The function({funct}) doesn't support the method({method}).".format(
                    funct=funct, 
                    method=method
                )

        return (setting, function)


class Resources(LambdaBase):

    def __init__(self, logger): # implementation-specific args and/or kwargs
        # implementation
        self.logger = logger

    def handle(self, event, context):
        # TODO implement
        try:
            area = event['pathParameters']['area']
            method = event["httpMethod"]
            endpointId = event['pathParameters']['endpoint_id']
            funct = event['pathParameters']['proxy']
            params = dict(
                {"endpoint_id": endpointId, "area": area},
                **(event['queryStringParameters'] if event['queryStringParameters'] is not None else {})
            )
            body = event['body']
            apiKey = event['requestContext']['identity']['apiKey']
            self.logger.info([endpointId, funct, apiKey, method])

            (setting, function) = LambdaBase.getFunction(endpointId, funct, apiKey=apiKey, method=method)
            
            assert (function is not None and setting is not None) and area == function.get("area"), \
                "Cannot locate the function!!.  Please check the path and parameters."
            
            payload = {
                "MODULENAME": function["config"]["moduleName"],
                "CLASSNAME": function["config"]["className"],
                "funct": function["function"],
                "setting": json.dumps(setting),
                "params": json.dumps(params),
                "body": body
            }
            res = LambdaBase.invoke(
                function["aws_lambda_arn"],
                payload,
                invocationType=function["config"]["functType"]
            )
            return {
                "statusCode": 200,
                "headers": {
                    'Access-Control-Allow-Headers': 'Access-Control-Allow-Origin',
                    'Access-Control-Allow-Origin': '*'
                },
                "body": res
            }

        except Exception:
            log = traceback.format_exc()
            self.logger.exception(log)
            return {
                "statusCode": 500,
                'headers': {
                    'Access-Control-Allow-Headers': 'Access-Control-Allow-Origin',
                    'Access-Control-Allow-Origin': '*'
                },
                "body": (
                    json.dumps({"error": "{0}".format(log)}, indent=4)
                )
            }


class Tasks(LambdaBase):

    sqs = boto3.client('sqs')
    sns = boto3.client("sns")

    def __init__(self, logger): # implementation-specific args and/or kwargs
        # implementation
        self.logger = logger

    @classmethod
    def getQueueAttributes(cls, queueUrl=None):
        response = cls.sqs.get_queue_attributes(
            QueueUrl=queueUrl,
            AttributeNames=['All']
        )
        attributes = response["Attributes"]
        totalMessages = int(attributes["ApproximateNumberOfMessages"]) + \
            int(attributes["ApproximateNumberOfMessagesNotVisible"]) + \
            int(attributes["ApproximateNumberOfMessagesDelayed"])
        attributes["TotalMessages"] = totalMessages
        return attributes

    @classmethod
    def fetchQueueMessages(cls, queueName):
        messages = []
        totalMessages = 0
        queueUrl = None

        response = cls.sqs.list_queues(QueueNamePrefix=queueName)
        if "QueueUrls" in response.keys():
            queueUrl = response["QueueUrls"][0]

        if queueUrl is not None:
            totalMessages = cls.getQueueAttributes(queueUrl=queueUrl)["TotalMessages"]
            if totalMessages != 0:
                response = cls.sqs.receive_message(
                    QueueUrl=queueUrl,
                    MaxNumberOfMessages=int(os.environ["SQSMAXMSG"]),
                    VisibilityTimeout=600
                )
                for message in response['Messages']:
                    messages.append(json.loads(message['Body']))
                    cls.sqs.delete_message(
                        QueueUrl=queueUrl,
                        ReceiptHandle=message['ReceiptHandle']
                    )
                    totalMessages = totalMessages - 1
            if totalMessages == 0:
                cls.sqs.delete_queue(QueueUrl=queueUrl)

        return (queueUrl, messages, totalMessages)

    @classmethod
    def dispatch(cls, endpointId, funct, params=None):
        (setting, function) = cls.getFunction(endpointId, funct)
        assert function is not None and setting is not None, \
            "Cannot locate the function!!.  Please check the path and parameters."

        payload = {
            "MODULENAME": function["config"]["moduleName"],
            "CLASSNAME": function["config"]["className"],
            "funct": function["function"],
            "setting": json.dumps(setting),
            "params": json.dumps(params),
        }
        
        cls.invoke(
            function["aws_lambda_arn"],
            payload,
            invocationType=function["config"]["functType"]
        )


    def handle(self, event, context):
        # TODO implement

        try:
            queueName = event.get('queue_name')
            endpointId = event.get('endpoint_id')

            if queueName is not None:
                try:
                    (queueUrl, messages, totalMessages) = Tasks.fetchQueueMessages(queueName)
                    
                    if len(messages) > 0:
                        funct = event.get('funct')
                        Tasks.dispatch(endpointId, funct, params={"data": messages})
                        self.logger.info("endpoint: {endpoint_id}, funct: {funct}".format(
                                endpoint_id=endpointId, 
                                funct=funct
                            )
                        )

                except Exception:
                    log = traceback.format_exc()
                    self.logger.exception(log)
                    # sleep(15)
                    Tasks.invoke(
                        context.invoked_function_arn,
                        event
                    )
                    return

                self.logger.info({"queueUrl": queueUrl, "processedMessages": len(messages), "totalMessages": totalMessages})
                if queueUrl is not None:
                    if totalMessages == 0:
                        # sleep(15)
                        funct = "updateSyncTask"
                        Tasks.dispatch(endpointId, funct, params={"id": queueName})
                        self.logger.info("endpoint: {endpoint_id}, funct: {funct}".format(
                                endpoint_id=endpointId, 
                                funct=funct
                            )
                        )
                    else:
                        # sleep(5)
                        Tasks.invoke(
                            context.invoked_function_arn,
                            event
                        )
            else:
                funct = event.get('funct')
                params = event.get('params')
                Tasks.dispatch(endpointId, funct, params=params)
                self.logger.info("endpoint: {endpoint_id}, funct: {funct}".format(
                        endpoint_id=endpointId, 
                        funct=funct
                    )
                )

        except Exception:
            log = traceback.format_exc()
            self.logger.exception(log)
            Tasks.sns.publish(
                TopicArn=os.environ["SNSTOPICARN"],
                Subject=context.invoked_function_arn,
                MessageStructure="json",
                Message= json.dumps({"default": log})
            )


class Worker(LambdaBase):

    lastRequestId = None
    
    @classmethod
    def setLastRequestId(cls, awsRequestId):
        if cls.lastRequestId == awsRequestId:
            return # abort
        else:
            cls.lastRequestId = awsRequestId

    def __init__(self, logger): # implementation-specific args and/or kwargs
        # implementation
        self.logger = logger

    def handle(self, event, context):
        # TODO implement
        Worker.setLastRequestId(context.aws_request_id)

        Class = getattr(
            __import__(event.get("MODULENAME")),
            event.get("CLASSNAME")
        )

        funct = getattr(
            Class(self.logger, **json.loads(event.get("setting"))),
            event.get("funct")
        )

        params = json.loads(event.get("params"), parse_float=Decimal)
        body = json.loads(event.get("body"), parse_float=Decimal) \
            if event.get("body") is not None else {}
        if params is None and body is None:
            return funct()
        else:
            params = {
                k: v for k, v in dict(
                    ({} if params is None else params),
                    **body
                ).items() if v is not None and v != ""
            }
            return funct(**params)
