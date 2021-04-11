import json


class Sample(object):
    def __init__(self, logger, **setting):
        self.logger = logger
        self.setting = setting

    def get_setting(self, **params):
        return json.dumps(params)
