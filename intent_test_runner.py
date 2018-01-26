import argparse
import sys
from websocket import create_connection, WebSocketTimeoutException
from os.path import dirname, exists, isdir

from mycroft.configuration import Configuration
from mycroft.util.log import LOG
from mycroft.messagebus.message import Message
import os
import json

TEST_PATH = "/tests/intent/"

class SkillTestContainer(object):
    def __init__(self, args):
        params = self.__build_params(args)

        if params.config:
            Configuration.get([params.config])

        if exists(params.lib) and isdir(params.lib):
            sys.path.append(params.lib)

        sys.path.append(params.dir)
        self.dir = params.dir

        self.test_suite = None

        self.__init_client(params)

    @staticmethod
    def __build_params(args):
        parser = argparse.ArgumentParser()
        parser.add_argument("--config", default="./mycroft.conf")
        parser.add_argument("dir", nargs='?', default=dirname(__file__))
        parser.add_argument("--lib", default="./lib")
        parser.add_argument("--host", default=None)
        parser.add_argument("--port", default=None)
        parser.add_argument("--use-ssl", action='store_true', default=False)
        return parser.parse_args(args)


    def __init_client(self, params):
        config = Configuration.get().get("websocket")

        if not params.host:
            params.host = config.get('host')
        if not params.port:
            params.port = config.get('port')

        uri = 'ws://' + params.host + ':' + str(params.port) + '/core'
        self.ws = create_connection(uri)


    def read_test_suite(self, home_dir):
        test_suite = []
        map(lambda x: test_suite.append(json.load(open(home_dir + TEST_PATH + x))),
            sorted(filter(lambda f: f.endswith(".json"), os.listdir(home_dir + TEST_PATH))))
        return test_suite

    def run_test_suite(self):
        try:
            self.test_runner()
        except Exception as e:
            LOG.error("Error: {0}".format(e))
            self.stop()

    def test_runner(self):
        test_suite = self.read_test_suite(self.dir)
        for test_case in test_suite:
            m = Message("recognizer_loop:utterance", {"lang": "en-us", "utterances": [test_case['utterance']]})
            self.ws.send(m.serialize())
            try:
                while True:
                    self.ws.settimeout(30)
                    result = json.loads(self.ws.recv())
                    if self.analyse_message(result, test_case):
                        break
            except WebSocketTimeoutException:
                pass

    def analyse_message(self, result, test_case):
        if str(result['type']).endswith(str(test_case['intent_type'])):
            print "Intent: " + str(result['type'])
        if str(result['type']) == "mycroft.skill.handler.start":
            print "Skill start: " + result['data']['handler']
        if str(result['type']) == "mycroft.skill.handler.complete":
            print "Skill end: " + result['data']['handler']
            print "-------------------"
            return True
        if str(result['type']) == "remove_context":
            print "Remove context: " + result['data']['context']
        if str(result['type']) == "add_context":
            print "Add context: " + result['data']['context']
        if str(result['type']) == "speak":
            print "Speak: " + result['data']['utterance']
        return False
def main():
    container = SkillTestContainer(sys.argv[1:])
    try:
        container.run_test_suite()
    except KeyboardInterrupt:
        pass
    finally:
        sys.exit()

if __name__ == "__main__":
    main()
