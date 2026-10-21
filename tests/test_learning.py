import json
import time
from fastapi.testclient import TestClient
from test_platform import main, teacher
from module1_content import LESSONS, EXAM
from learning import LearningProgress


def test_complete_demo_with_hints_unlocks_lab_and_exam():
    c=TestClient(main.app)
    assert c.get('/learn/1').status_code==401
    assert c.get('/learn/1/demo').status_code==200
    data=c.get('/api/learn/1?demo=true').json()
    token=data['token']
    def post(**data):return c.post('/api/learn/1?demo=true',json=data,headers={'X-CSRF-Token':token})
    assert all('answer' not in q and 'explanation' not in q for l in data['lessons'] for q in l['questions'])
    assert post(action='check',id='devices-1',answer=['1']).status_code==403
    assert post(action='start_exam').status_code==403
    assert c.post('/api/learn/1?demo=true',json={'action':'hint','id':'client-1'}).status_code==403
    assert post(action='check',id='client-1',answer=['1']).json()['correct'] is False
    assert 'hint' in post(action='hint',id='client-1').json()
    for lesson in LESSONS:
        for question in lesson['questions']:
            result=post(action='check',id=question['id'],answer=question['answer'])
            assert result.status_code==200,result.text
            assert result.json()['correct']
    assert result.json()['state']['solved']['client-1']==95
    assert len(result.json()['state']['completed'])==6
    assert post(action='lab',devices={},edges=[]).json()['correct'] is False
    configuration={'a':'client','b':'switch','c':'router','d':'switch','e':'server'}
    result=post(action='lab',devices=configuration,edges=['a-b','b-c','c-d','d-e'])
    assert result.json()['correct']
    exam=post(action='start_exam').json()['state']['active_exam']
    assert post(action='hint',id='client-1').status_code==409
    assert post(action='finish_exam',id='wrong-id',answers={}).status_code==409
    result=post(action='finish_exam',id=exam['id'],answers={q['id']:q['answer'] for q in EXAM})
    assert result.json()['score']==100
    assert result.json()['state']['passed']
    assert post(action='finish_exam',id=exam['id'],answers={}).status_code==409
    assert c.get('/api/learn/1?demo=true').json()['state']['best']==100
    assert len(c.cookies.get('session'))<3800
    other=TestClient(main.app)
    assert other.get('/api/learn/1?demo=true').json()['state']['completed']==[]
    assert post(action='reset_demo').json()['state']['solved']=={}


def test_account_progress_is_persistent_and_expiry_is_server_checked(monkeypatch):
    c=teacher()
    data=c.get('/api/learn/1').json()
    def post(**data):return c.post('/api/learn/1',json=data,headers={'X-CSRF-Token':token})
    token=data['token']
    for lesson in LESSONS:
        for q in lesson['questions']:
            assert post(action='check',id=q['id'],answer=q['answer']).json()['correct']
    assert post(action='lab',devices={'a':'client','b':'switch','c':'router','d':'switch','e':'server'},edges=['a-b','b-c','c-d','d-e']).json()['correct']
    exam=post(action='start_exam').json()['state']['active_exam']
    monkeypatch.setattr('learning.time.time',lambda:exam['deadline']+2)
    result=post(action='finish_exam',id=exam['id'],answers={q['id']:q['answer'] for q in EXAM})
    assert result.json()['score']==0 and result.json()['expired']
    fresh=teacher()
    state=fresh.get('/api/learn/1').json()['state']
    assert len(state['completed'])==6 and state['lab'] and state['best']==0
    assert not state['passed']
    # A separate demo never inherits account results.
    assert fresh.get('/api/learn/1?demo=true').json()['state']['best'] is None
    assert post(action='reset_demo').status_code==400


def test_module_content_matches_exam_and_invalid_answers_rejected():
    assert {l['source'] for l in LESSONS}=={1,3,5,6,21,22}
    assert {q['source'] for q in EXAM}=={1,3,5,6,21,22}
    assert len({q['id'] for l in LESSONS for q in l['questions']})==18
    c=TestClient(main.app)
    token=c.get('/api/learn/1?demo=true').json()['token']
    for answer in (None, '0', [None], ['x'*121]):
        assert c.post('/api/learn/1?demo=true',headers={'X-CSRF-Token':token},json={'action':'check','id':'client-1','answer':answer}).status_code==400
    assert c.get('/api/learn/1').status_code==401
