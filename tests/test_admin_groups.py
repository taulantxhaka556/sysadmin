import json
import uuid
from fastapi.testclient import TestClient
from test_platform import main, teacher, token
from learning import LearningProgress, CourseProgress, initial
from course_catalog import MODULES


def setup_group():
    suffix=uuid.uuid4().hex[:8]
    with main.DB() as d:
        g=main.Group(name='Группа '+suffix);other=main.Group(name='Другая '+suffix)
        d.add_all([g,other]);d.flush()
        a=main.User(name='Анна '+suffix,email=suffix+'@test.test',pw=main.hashed('Student12345'),role='student',group_id=g.id)
        b=main.User(name='Борис '+suffix,email='b'+suffix+'@test.test',pw=main.hashed('Student12345'),role='student',group_id=other.id)
        d.add_all([a,b]);d.flush()
        solved={q['id']:100 for l in MODULES[1]['lessons'] for q in l['questions']}
        d.add(LearningProgress(user_id=a.id,payload=json.dumps(initial()|dict(solved=solved,lab=True,best=80))))
        d.add(CourseProgress(user_id=a.id,module_id=2,payload=json.dumps(initial()|dict(best=0))))
        lesson=d.scalar(main.select(main.Lesson).where(main.Lesson.kind=='practice'))
        d.add(main.Work(user_id=a.id,lesson_id=lesson.id,status='pending',answer='Ready'))
        d.commit()
        return g.id,other.id,a.id,b.id,a.name,b.name,a.email


def test_group_creation_validation_and_rename():
    c=teacher();name='Новая '+uuid.uuid4().hex[:8]
    response=c.post('/admin/group',data={'name':name,'token':token(c,'/admin')},follow_redirects=False)
    assert response.status_code==303
    assert response.headers['location'].startswith('/admin/groups/')
    path=response.headers['location'];gid=int(path.rsplit('/',1)[1])
    assert 'Пока нет студентов' in c.get(path).text
    assert name in c.get('/register').text
    assert c.post('/admin/group',data={'name':name.swapcase(),'token':token(c,'/admin')}).status_code==409
    assert c.post('/admin/group',data={'name':'x'*121,'token':token(c,'/admin')}).status_code==400
    assert c.post(path+'/rename',data={'name':name+' обновлена','token':token(c,path)},follow_redirects=False).status_code==303
    assert name+' обновлена' in c.get('/admin').text
    assert c.get('/admin/groups/99999999').status_code==404


def test_group_progress_filter_and_transfer_preserve_learning():
    gid,other,uid,bid,name,bname,email=setup_group();c=teacher();path=f'/admin/groups/{gid}'
    html=c.get(path).text
    assert name in html and bname not in html
    assert '1 / 14' in html and '80/100' in html and '0/100' in html
    assert f'/journal/student/{uid}' in html and 'Ожидают проверки' in html
    assert name not in c.get(path+'?q=несуществующий').text
    assert 'Нет студентов по этому запросу' in c.get(path+'?q=несуществующий').text
    response=c.post(f'/admin/students/{uid}/group',data={'group_id':other,'token':token(c,path)},follow_redirects=False)
    assert response.status_code==303
    assert name not in c.get(path).text
    assert name in c.get(f'/admin/groups/{other}').text
    with main.DB() as d:
        assert d.get(main.User,uid).group_id==other
        assert json.loads(d.get(LearningProgress,uid).payload)['best']==80
        assert d.scalar(main.select(main.Work).where(main.Work.user_id==uid)).status=='pending'


def test_group_admin_boundaries():
    gid,other,uid,bid,name,bname,email=setup_group();path=f'/admin/groups/{gid}'
    guest=TestClient(main.app);c=TestClient(main.app)
    assert guest.get(path).status_code==401
    c.post('/login',data={'email':email,'password':'Student12345','token':token(c)})
    assert c.get(path).status_code==403
    assert c.post('/admin/group',data={'name':'Denied','token':token(c,'/assignments')}).status_code==403
    assert c.post(path+'/rename',data={'name':'Denied','token':token(c,'/assignments')}).status_code==403
    assert c.post(f'/admin/students/{uid}/group',data={'group_id':other,'token':token(c,'/assignments')}).status_code==403
    admin=teacher()
    assert admin.post(path+'/rename',data={'name':'Denied'}).status_code==403
    assert admin.post(f'/admin/students/{uid}/group',data={'group_id':other}).status_code==403
    assert admin.post(f'/admin/students/{uid}/group',data={'group_id':99999999,'token':token(admin,path)}).status_code==404


def test_summary_distinguishes_zero_missing_scores_and_legacy_progress():
    from admin_dashboard import snapshot
    gid,other,uid,bid,name,bname,email=setup_group()
    with main.DB() as d:
        theory=d.scalar(main.select(main.Lesson).where(main.Lesson.kind=='theory'))
        practice=d.scalar(main.select(main.Lesson).where(main.Lesson.kind=='practice',main.Lesson.number==2))
        d.add(main.Work(user_id=uid,lesson_id=theory.id,status='graded',score=0))
        d.add(main.Work(user_id=uid,lesson_id=practice.id,status='revision',score=None))
        d.add(CourseProgress(user_id=uid,module_id=1,payload=json.dumps(initial())))
        d.commit()
        rows,_,_=snapshot(d,[d.get(main.User,uid),d.get(main.User,bid)])
        assert rows[uid]['done']==1
        assert rows[uid]['lessons']==len(MODULES[1]['lessons'])
        assert rows[uid]['pending']==1 and rows[uid]['revision']==1
        assert rows[uid]['average']==0 and rows[uid]['test_average']==40
        assert rows[bid]['average'] is None and not rows[bid]['started']
    c=teacher()
    assert name in c.get(f'/admin/groups/{gid}?state=revision').text
    assert name not in c.get(f'/admin/groups/{gid}?state=complete').text
