import json
from fastapi.testclient import TestClient
from test_platform import main, teacher
from course_catalog import MODULES
from course_labs import simulate, terminal
from learning import CourseProgress, LearningProgress, initial

SOLUTIONS={
2:dict(medium='fiber',link='yes',destination='b'),
3:dict(network='192.168.10.64',broadcast='192.168.10.127',hosts='62'),
4:dict(b='10',mode='trunk',allowed='10,20'),
5:dict(area='0',passive='no',specific='yes',reverse='yes'),
6:dict(pool='192.168.10.21',gateway='192.168.10.1',dns='192.168.10.2',record='192.168.10.2'),
7:dict(mode='pat',interfaces='yes',route='yes',port2='40002'),
8:dict(ssid='LabNet',support='both',key='correct'),
9:dict(ram1='6',ram2='6',service='yes',firewall='yes',backup='independent'),
10:dict(diagnosis='dns',repair='dns'),
11:dict(rules=['https','admin','deny'],logging='yes'),
12:dict(name='lab.test',trust='yes',auth='yes',selectors='192.168.20.0/24',mfa='key'),
13:dict(subnet='10.20.0.0/16',public='no',role='read',ttl='15',iot='yes',audit='yes'),
14:dict(trunk='yes',routing='yes',dhcp='yes',dns='192.168.30.2',acl='least',vpn='yes',monitor='yes',restore='yes')}

def test_every_module_complete_and_isolated():
    c=TestClient(main.app)
    for number,m in MODULES.items():
        if number==1:continue
        url=f'/api/learn/{number}?demo=true'
        response=c.get(url);assert response.status_code==200,response.text
        data=response.json();token=data['token']
        assert len(data['catalog'])==14
        assert len(data['practice'])==len(m['practice'])
        assert all('exam' not in l for l in data['lessons'])
        assert all('answer' not in q for l in data['lessons'] for q in l['questions'])
        def post(**payload):return c.post(url,json=payload,headers={'X-CSRF-Token':token})
        assert post(action='lab',config=SOLUTIONS[number]).status_code==403
        assert post(action='start_exam').status_code==403
        assert not post(action='simulate',config={}).json()['correct']
        for lesson in m['lessons']:
            for q in lesson['questions']:
                result=post(action='check',id=q['id'],answer=q['answer'])
                assert result.status_code==200,result.text
                assert result.json()['correct'],q
        assert not post(action='lab',config={}).json()['correct']
        assert post(action='lab',config=SOLUTIONS[number]).json()['correct']
        exam=post(action='start_exam').json()['state']['active_exam']
        assert post(action='simulate',config={}).status_code==409
        result=post(action='finish_exam',id=exam['id'],answers={q['id']:q['answer'] for q in m['exam']})
        assert result.json()['score']==100 and result.json()['state']['passed']
    assert c.get('/api/learn/2?demo=true').json()['state']['best']==100
    assert c.get('/api/learn/1?demo=true').json()['state']['best'] is None
    assert len(c.cookies.get('session'))<1000

def test_models_compute_and_reject_bad_inputs():
    result=simulate(3,dict(ip='10.0.0.129',prefix='25',network='10.0.0.128',broadcast='10.0.0.255',hosts='126'))
    assert all(t['ok'] for t in result['trace'][1:])
    assert not result['correct'] # exploration is not the assigned subnet
    assert '192.168.10.99' in terminal({},'nslookup lab.test')['output']
    fixed=terminal({},'set dns lab.test 192.168.10.2')
    assert '192.168.10.2' in terminal(fixed['config'],'nslookup lab.test')['output']
    assert 'не поддерживается' in terminal({},'rm -rf /')['output']
    for n,config in SOLUTIONS.items():assert simulate(n,config)['correct'],n
    c=TestClient(main.app);token=c.get('/api/learn/11?demo=true').json()['token']
    for config in ({'rules':['deny','deny','https']},{'unknown':'x'},{'logging':[]},{'logging':'x'*121}):
        assert c.post('/api/learn/11?demo=true',json={'action':'simulate','config':config},headers={'X-CSRF-Token':token}).status_code==400
    assert c.get('/api/learn/99?demo=true').status_code==404

def test_existing_student_can_access_every_module_and_teacher_preview():
    with main.DB() as d:
        u=main.User(name='Course gate',email='gate@example.test',pw=main.hashed('Student12345'),role='student');d.add(u);d.commit();uid=u.id
    from test_platform import token
    c=TestClient(main.app)
    c.post('/login',data={'email':'gate@example.test','password':'Student12345','token':token(c)},follow_redirects=False)
    data=c.get('/api/learn/14').json()
    assert all(m['available'] for m in data['catalog'])
    assert not any(m['passed'] for m in data['catalog'])
    with main.DB() as d:
        d.add(LearningProgress(user_id=uid,payload=json.dumps(initial()|dict(lab=True,best=70))));d.commit()
    assert c.get('/api/learn/2').status_code==200
    assert c.get('/api/learn/3').status_code==200
    admin=teacher();data=admin.get('/api/learn/14').json()
    assert len(data['lessons'])==2
    assert len(data['practice'])==3
    assert all(p['url'].startswith('/lesson/') for p in data['practice'])
    first=MODULES[14]['lessons'][0]['questions'][0]
    saved=admin.post('/api/learn/14',json={'action':'check','id':first['id'],'answer':first['answer']},headers={'X-CSRF-Token':data['token']})
    assert saved.json()['correct']
    assert first['id'] in teacher().get('/api/learn/14').json()['state']['solved']
    from learning import teacher_summary
    with main.DB() as d:
        admin_id=d.scalar(main.select(main.User.id).where(main.User.role=='admin'))
        assert '14. Восстановление' in teacher_summary(d,admin_id)

def test_all_original_sources_covered_once():
    assert sorted(l['source'] for m in MODULES.values() for l in m['lessons'])==list(range(1,61))
    assert sorted(n for m in MODULES.values() for n in m['practice'])==list(range(1,41))
    assert sum(len(l['questions']) for m in MODULES.values() for l in m['lessons'])==180
    assert all(len(m['exam'])>=3 for m in MODULES.values())
