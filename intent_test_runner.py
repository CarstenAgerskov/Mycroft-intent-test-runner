import argparse
import sys
from websocket import create_connection, WebSocketTimeoutException
from os.path import dirname, exists, isdir
from mycroft.configuration import Configuration
from mycroft.util.log import LOG
from mycroft.messagebus.message import Message
import os
import json
import time
import re

TEST_PATH = "/test/intent/"
OKGREEN = '\033[92m'
FAIL = '\033[91m'
ENDC = '\033[0m'

class SkillTestContainer(object):
    def __init__(self, args):
        params = self.__build_params(args)

        if params.config:
            Configuration.get([params.config])

        if exists(params.lib) and isdir(params.lib):
            sys.path.append(params.lib)

        sys.path.append(params.dir)
        self.dir = params.dir
        self.verbose = int(params.verbose)
        self.all_skills = params.all_skills

        self.test_suite = None
        self.succeeded = True

        self.__init_client(params)

    @staticmethod
    def __build_params(args):
        parser = argparse.ArgumentParser()
        parser.add_argument("--all-skills", action='store_true', default=False)
        parser.add_argument("--config", default="./mycroft.conf")
        parser.add_argument("dir", nargs='?', default=dirname(__file__))
        parser.add_argument("--lib", default="./lib")
        parser.add_argument("--host", default=None)
        parser.add_argument("--port", default=None)
        parser.add_argument("--use-ssl", action='store_true', default=False)
        parser.add_argument("--verbose", default=0)
        return parser.parse_args(args)


    def __init_client(self, params):
        config = Configuration.get().get("websocket")

        if not params.host:
            params.host = config.get('host')
        if not params.port:
            params.port = config.get('port')

        uri = 'ws://' + params.host + ':' + str(params.port) + '/core'
        try:
            self.ws = create_connection(uri)
            self.ws.settimeout(10)
        except Exception as e:
            print format(e)
            print "Did you forget to start Mycroft?"
            exit(1)

    def read_test_suite(self, home_dir):
        test_suite = []
        map(lambda x: test_suite.append(json.load(open(home_dir + TEST_PATH + x))),
            sorted(filter(lambda f: f.endswith(".json"), os.listdir(home_dir + TEST_PATH))))
        return test_suite


    def run_test_suite(self):
        try:
            if self.all_skills:
                for d in filter(lambda x: re.findall("/opt/mycroft/skills/.*?/test/intent",x), [x[0] for x in os.walk("/opt/mycroft/skills")]):
                    _dir = re.findall("/opt/mycroft/skills/.*?/",d)[0]
                    print "Running test for: " + _dir
                    self.test_runner(_dir)
                return self.succeeded
            else:
                self.test_runner(self.dir)
                return self.succeeded
        except Exception as e:
            LOG.error("Error: {0}".format(e))
            self.stop()


    def test_runner(self, dir):
        if self.verbose > 0:
            print "Testing skill: " + dir
        test_suite = self.read_test_suite(dir)
        for test_case in test_suite:
            op = self.test_case_to_op(test_case)
            _m = Message("recognizer_loop:utterance", {"lang": "en-us", "utterances": [test_case['utterance']]})
            self.ws.send(_m.serialize())
            if self.verbose > 0:
                print "Test case: " + str(test_case)
                print "Utterance: " + str(test_case['utterance'])

            timeout = time.time() + 30
            while True:
                try:
                    result = json.loads(self.ws.recv())
                    if self.verbose > 1:
                        print result

                    for _x in op:
                        self.op_evaluate(_x, result)

                    if not filter(lambda x: x[-1] != 'succeeded', op):
                        break
                    if time.time() > timeout:
                        break
                except WebSocketTimeoutException:
                    pass

            if not filter(lambda x: x[-1] != 'succeeded', op):
                print OKGREEN + "Succeeded: " + test_case['intent_type'] + ENDC
            else:
                print FAIL + "Failed: " + test_case['intent_type'] + ENDC
                self.succeeded = False
                break

            if self.verbose > 0:
                print "Test status: " + str(op)


    def test_case_to_op(self, test_case):
        op= []

        _x = ['and']
        if test_case.get('utterance', None):
            _x.append(['endsWith', 'type', str(test_case['intent_type'])])

        if test_case.get('intent', None):
            for item in test_case['intent'].items():
                _x.append(['equal', ['data', str(item[0])], str(item[1])])

        if _x != ['and']:
            op.append(_x)

        if test_case.get('assert', None):
            for _x in eval(test_case['assert']):
                op.append(_x)

        return op


    def get_field_value(self, op, msg):
        if isinstance(op, list):
            value = msg.get(op[0], None)
            if len(op) > 1 and value:
                for field in op[1:]:
                    value = value.get(field, None)
                    if not value:
                        break
        else:
            value =  msg.get(op, None)

        return value

    def op_evaluate(self, op, msg):
        if op[0] == 'equal':
            if self.get_field_value(op[1], msg) != op[2]:
                return False

        if op[0] == 'notEqual':
            if self.get_field_value(op[1], msg) == op[2]:
                return False

        if op[0] == 'endsWith':
            if not self.get_field_value(op[1], msg).endswith(op[2]):
                return False

        if op[0] == 'match':
            if not re.match(op[2], self.get_field_value(op[1], msg)):
                return False

        if op[0] == 'and':
            for i in op[1:]:
                if not self.op_evaluate(i,msg):
                    return False

        if op[0] == 'or':
            for i in op[1:]:
                if self.op_evaluate(i,msg):
                    op.append('succeeded')
                    return True
            return False

        op.append('succeeded')
        return True


def main():
    container = SkillTestContainer(sys.argv[1:])
    if not container.run_test_suite():
        exit(1)

if __name__ == "__main__":
    main()
