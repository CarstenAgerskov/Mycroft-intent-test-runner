# Intent test runner for Mycroft skills

This is a work in progress test runner for Mycroft skills. It is able to test if an intent is called,
and verify the parameters from the utterance is passed correctly

## Setting up
To start the test runner, copy intent_test_runner.py to mycroft-core/mycroft/skills. This allows it to share Mycrofts setup.


If you don't copy the intent_test_runner.py to mycroft-core/mycroft/skills you can use the command line flag --config to point to
mycroft.conf, something like ```--config ~/mycroft-core/mycroft/configuration/mycroft.conf``` when executing.

Change to mycrofts virtualenv: workon mycroft, before executing

## Running 
The intent_test_runner.py is supposed to be executed after Mycroft is started, and has loaded the skill to be tested.

Run it with: 
```python
python intent_test_runner.py /opt/mycroft/skills/your-skill
```
or more formalised:
```
Usage:
    python intent_test_runner.py [{skill_path | --all-skills}] [--config config_file] [--host host] [--port port] [--verbose level]

Options:
--all-skills
    Run the intent test runner on all skills in /opt/mycroft/skills whit a test/intent folder
--config
    Path to config_file mycroft.conf containing host and port configuration
--host
    Host for web socket to use, override mycroft.conf
--port
    Port for web socket to use, override mycroft.conf
--verbose
    Verbose level, 1 or 2
```

The json files containing test data is in the skills /test/intent/
folder. They are formatted as messages, and sent on the bus, in alphabetic order of the file name.

Alphabetic ordering can be used for compensating (trans)actions, for instance first add to a list, then remove from a list, to leave the list unchanged.

The test runner will write some output on the console for each json test file. Without verbose it looks like this:

```
Succeeded: AddTaskToListIntent
Succeeded: FindTaskOnListIntent
Succeeded: CompleteTaskOnListIntent
Succeeded: ReadListIntent
Failed: UndoIntent
Failed: GetTokenIntent
```

An intent succeedes if all test are passed for the intent. And in that case the test runner immedeately continues to the next test.
If all tests have not succeeded 30 seconds after the utterence, the test is failed.
Because of this, a failed test will take at least 30 seconds to complete.

If you want to try the test runner on some existing skills, read the section on skill status at the end of the document.

## Internal representation
The test runner transforms the json files in test/intent/ into an "internal test format". The example below:
```
{
  "utterance": "add some to my none list",
  "intent_type": "AddTaskToListIntent",
  "intent": {
    "taskName": "some",
    "listName": "none",
    "AddTaskToListKeyword": "add"
  }
}
```

is transformed into

```
[['and',
    ['endsWith', 'type', 'AddTaskToListIntent'],
    ['equal', ['data', 'listName'], 'none'],
    ['equal', ['data', 'taskName'], 'some'],
    ['equal', ['data', 'AddTaskToListKeyword'], 'add']]]
```

The above is then used to test this message on the bus:
```
{u'type': u'4175061547157869683:AddTaskToListIntent', u'data': {u'listName': u'none', u'AddTaskToListKeyword': u'add', u'target': None, u'intent_type': u'4175061547157869683:AddTaskToListIntent', u'confidence': 0.2, u'__tags__': [{u'end_token': 0, u'start_token': 0, u'from_context': False, u'entities': [{u'confidence': 1.0, u'data': [[u'add', u'AddTaskToListKeyword']], u'key': u'add', u'match': u'add'}], u'key': u'add', u'match': u'add'}, {u'end_token': 1, u'start_token': 1, u'from_context': False, u'entities': [{u'confidence': 0.5, u'data': [[u'some', u'taskName']], u'key': u'some', u'match': u'some'}], u'key': u'some', u'match': u'some'}, {u'end_token': 4, u'start_token': 4, u'from_context': False, u'entities': [{u'confidence': 0.5, u'data': [[u'none', u'listName']], u'key': u'none', u'match': u'none'}], u'key': u'none', u'match': u'none'}], u'taskName': u'some', u'utterance': u'add some to my none list'}, u'context': {u'target': None}}
```

The internal test format can be used in the json test file as well. The example below adds tests for removeal of two contexts:
```
{
  "utterance": "add some to my none list",
  "intent_type": "AddTaskToListIntent",
  "intent": {
    "taskName": "some",
    "listName": "none",
    "AddTaskToListKeyword": "add"
  },
  "assert": "[['and', ['equal', 'type', 'speak'], ['match', ['data', 'utterance'], 'I can\\'t find a list called none.*']], ['and', ['equal', 'type', 'remove_context'], ['equal', ['data', 'context'], 'UndoContext']], ['and', ['equal', 'type', 'remove_context'], ['equal', ['data', 'context'], 'ConfirmContext']]]"
}

```

After transformation to internal test format we get:
```
[
    ['and',
        ['endsWith', 'type', 'AddTaskToListIntent'],
        ['equal', ['data', 'listName'], 'none'],
        ['equal', ['data', 'taskName'], 'some'],
        ['equal', ['data', 'AddTaskToListKeyword'], 'add']
    ],
    ['and',
        ['equal', 'type', 'speak'],
        ['match', ['data', 'utterance'], "I can't find a list called none.*"]
    ],
    ['and',
        ['equal', 'type', 'remove_context'],
        ['equal', ['data', 'context'], 'UndoContext']
    ],
    ['and',
        ['equal', 'type', 'remove_context'],
        ['equal', ['data', 'context'], 'ConfirmContext']
    ]
]
```

The above contains 4 different tests, because 4 different messages on the bus are to be tested.
Also note the 'match' operation used to verofy the utterance, it is a regular expression evaluation.

The internal test format above is actually quite powerfull, the code already supports that operations can be nested to any depth, for instance:
```
[['and',
    ['endsWith', 'type', 'AddTaskToListIntent'],
    ['or',
        ['equal', ['data', 'listName'], 'none'],
        ['equal', ['data', 'taskName'], 'some']
    ],
    ['equal', ['data', 'AddTaskToListKeyword'], 'add']
]]
```
and besides "and" also "or" and "not" are supported.

## Troubleshoot a failed test
Using verbose level 1 the intent test runner diaplays:
* The Utterance is displayed
* The test
* The result of the parts of the test

For instance:
```
Test case: {u'intent': {u'AddTaskToListKeyword': u'get token'}, u'intent_type': u'GetTokenIntent', u'utterance': u'get a token'}
Utterance: get a token
Failed: GetTokenIntent
Test status: ['and', ['endsWith', 'type', 'GetTokenIntent', 'succeeded'], ['equal', ['data', 'AddTaskToListKeyword'], 'get token']]

```
If we look at the "Test status", we can see that the type=GetTokenIntent succeeded. The intent test runner added (at least one) 'succeeded' to the end of the comparesion.
However, data.AddTaskToListKeyword='get token' was not marked succeeded. Probably because AddTaskToListKeyword is wrong, is
should be GetTokenKeyword.

When using verbose level 2 all messages on the bus are logged. It is possible to find the message that the test case for GetTokenIntent is working on:
```
{u'type': u'4175061547157869683:GetTokenIntent', u'data': {u'confidence': 1.0, u'target': None, u'intent_type': u'4175061547157869683:GetTokenIntent', u'GetTokenKeyword': u'get token', u'__tags__': [{u'end_token': 1, u'start_token': 0, u'from_context': False, u'entities': [{u'confidence': 1.0, u'data': [[u'get token', u'GetTokenKeyword']], u'key': u'get token', u'match': u'get token'}], u'key': u'get token', u'match': u'get token'}], u'utterance': u'get a token'}, u'context': {u'target': None}}
```
and it is indeed using the key named GetTokenKeyword for the keyword.

## To do
* Find out how best to report test results. Logs, exit codes, dashboard?
* Find a way to make the skill aware that the skill runner is initiating the request, to avoid execution code with side effects in the skill
* Add support for "expected_dialog"
* Could messages be lost using this implementation?
* Syntax check of json files
* More resiliance and better reporting of internal errors in the test runner itself
* How to retreive a list of intents for a skill
* How to handle unreachable intents, like in a context

### Integration into Mycroft core
If this test runner it is found usable, it could be added to mycroft-core

## Skill status
I am testing this using "the cows lists", in a state where authentication with RTM did take place.
But I think it will work without as well.
In the current version, unfortunately I put the tests in tests/intent. They must be moved to test/intent before testing.

I tried using skill-weather as well. The first test succeedes if sample1.intent.json contains:
```
{ "utterance": "what's the weather like in seattle",
    "intent_type": "CurrentWeatherIntent",
    "intent": { "Weather": "weather",
                "Location": "Seattle" }
}
```