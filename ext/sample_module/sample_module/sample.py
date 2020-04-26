import json


class Sample(object):

    def __init__(self, logger, **setting):
        self.logger = logger
        self.setting = setting
    
    def getSetting(self, **params):
        return json.dumps(params)
