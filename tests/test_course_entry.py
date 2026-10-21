import json
from fastapi.testclient import TestClient
from test_platform import main, token
from learning import LearningProgress, initial


def test_registration_opens_real_course_and_demo_redirects():
    with main.DB() as d:
        group=main.Group(name='Course entry');d.add(group);d.commit();gid=group.id
    c=TestClient(main.app)
    result=c.post('/register',data={'name':'Course Student','email':'entry@example.test','password':'Student12345','group_id':gid,'token':token(c,'/register')})
    assert result.status_code==200 and result.url.path=='/learn/1'
    assert 'data-demo="false"' in result.text
    assert 'Этап 1 ·' not in result.text
    assert 'name="token"' in result.text and '/logout' in result.text
    for route in ('/dashboard','/login','/learn/1/demo','/learn/14/demo'):
        result=c.get(route)
        assert result.url.path=='/learn/1' and 'data-demo="false"' in result.text
    with main.DB() as d:
        uid=d.scalar(main.select(main.User.id).where(main.User.email=='entry@example.test'))
        d.add(LearningProgress(user_id=uid,payload=json.dumps(initial()|dict(lab=True,best=100))));d.commit()
    assert c.get('/dashboard').url.path=='/learn/2'
    assert c.get('/assignments').status_code==200
    guest=TestClient(main.app)
    assert 'data-demo="true"' in guest.get('/learn/1/demo').text
    assert guest.get('/learn').status_code==401
