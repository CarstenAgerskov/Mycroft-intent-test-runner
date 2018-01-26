# Intent test runner for Mycroft skills

This is the first cut at a test runner for testing a skill based on json files in the skills /tests/intent/ folder. 

I will publish this test runner it in this immature state, to get feedback on the approach I have taken, and if its usable at all.

In particular, the code depends on timing to correlate messages on the bus. Suggestions for a better way is most welcome.

The problem is, that I miss a strong way to corrrelate messages, for instance a GUID that the first producer creates and write to the message. All consumers copy that GUID from request to response. This would not only facilitate testing and debugging, but might even be an advantage if, in the future, several identical modules listens on the bus.



## Setting up
To start the test runner copy intent_test_runner.py to mycroft-core/mycroft/skills. This allows it to share Mycrofts setup.

Change to mycrofts virtualenv: workon mycroft, before executing



## Running 
The intent_test_runner.py is supposed to be executed after Mycroft is started, and has loaded the skill to be tested. It can work with only the bus and the skill container as well. 

Run it with: 
```python
python intent_test_runner.py /opt/mycroft/skills/your-skill
```

The json files containing test data in the skills /tests/intent/ 
folder is formatted as messages, and sent on the bus, in alphabetic order. 

Alphabetic ordering can be used for compensating (trans)actions, for instance first add to a list, then remove from a list, to leave the list unchanged.

The test runner will write some output on the console for each json test file.

Currently the output is not validated against the expected value, but only printed
For example:
```
Intent: 4175061547157869683:AddTaskToListIntent
Skill start: add_task_to_list_intent
Remove context: UndoContext
Remove context: ConfirmContext
Add context: ConfirmContext
Speak: I can't find a list called none, do you want to add the task to personal instead?
Skill end: add_task_to_list_intent
-------------------
Intent: 4175061547157869683:GetTokenIntent
Skill start: get_token_intent
Speak: My token is valid, it is not neccesary to get a new token
Remove context: ConfirmContext
Remove context: UndoContext
Skill end: get_token_intent
```

The test runner will stop after 30 seconds of inactivity on the bus. Or if the "skill end" above is found for all test cases.

## To do
If this approach is viable, I will go on and implement code to assert that Mycroft responds as expected, sets the right context, and so on.
I will try to make it compatible with the current json test files, but I would like to extend the options to more closely match that it is messages on the bus that are checked.
For instance: 
If I expect to receive this message 
```
{u'type': u'remove_context', u'data': {u'context': u'ConfirmContext'}, u'context': None}
```
I would like in my json file defining the test to be something like
```
{ “AssertEqual”: { “type”: “ remove_context”, “data” : {'context': 'ConfirmContext'}}
```


### Integration into Mycroft core
If this test runner it is found usable, it could be integrated 
into mycroft-core/mycroft/skills/container.py, and activated 
by a command line argument to the container.
 
