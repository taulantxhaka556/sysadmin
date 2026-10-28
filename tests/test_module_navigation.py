from fastapi.testclient import TestClient
from test_platform import main, token
from test_course import MODULES, SOLUTIONS


def test_registered_student_completes_last_module_first_and_keeps_progress():
    with main.DB() as d:
        group=main.Group(name='Free module navigation')
        d.add(group);d.commit();gid=group.id
    c=TestClient(main.app)
    result=c.post('/register',data={'name':'Independent Student','email':'free-modules@example.test',
        'password':'Student12345','group_id':gid,'token':token(c,'/register')})
    assert result.status_code==200 and result.url.path=='/learn/1'

    # Visit out of order immediately after registration, without demo mode.
    for number in (14,7,2,13,1,12,3,11,4,10,5,9,6,8):
        assert c.get(f'/learn/{number}').status_code==200
        response=c.get(f'/api/learn/{number}')
        assert response.status_code==200,response.text
        data=response.json()
        assert len(data['catalog'])==14 and all(m['available'] for m in data['catalog'])
        assert not any(m['passed'] for m in data['catalog'])

    url='/api/learn/14'
    data=c.get(url).json();csrf=data['token']
    def post(**payload):
        return c.post(url,json=payload,headers={'X-CSRF-Token':csrf})
    assert post(action='start_exam').status_code==403
    for lesson in MODULES[14]['lessons']:
        for question in lesson['questions']:
            result=post(action='check',id=question['id'],answer=question['answer'])
            assert result.status_code==200 and result.json()['correct']
    assert post(action='lab',config=SOLUTIONS[14]).json()['correct']
    exam=post(action='start_exam').json()['state']['active_exam']
    result=post(action='finish_exam',id=exam['id'],answers={q['id']:q['answer'] for q in MODULES[14]['exam']})
    assert result.json()['score']==100 and result.json()['state']['passed']
    assert c.get('/api/learn/1').json()['state']['solved']=={}
    assert c.get('/api/learn/7').json()['state']['best'] is None

    # The result belongs to the account and module, and survives a new session.
    returning=TestClient(main.app)
    returning.post('/login',data={'email':'free-modules@example.test','password':'Student12345','token':token(returning)})
    data=returning.get(url).json()
    assert data['state']['passed'] and data['state']['best']==100
    assert [m['id'] for m in data['catalog'] if m['passed']]==[14]
    assert all(m['available'] for m in data['catalog'])
    guest=TestClient(main.app)
    assert guest.get(url).status_code==401
    assert not guest.get(url+'?demo=true').json()['state']['passed']
