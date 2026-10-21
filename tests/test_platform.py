import os
import re
import tempfile
import atexit
from pathlib import Path

TEST_DIR = tempfile.TemporaryDirectory(prefix='network-exam-test-')
os.environ['DATABASE_URL'] = 'sqlite:///' + str(Path(TEST_DIR.name)/'test.db')
os.environ['UPLOAD_DIR'] = str(Path(TEST_DIR.name)/'uploads')
os.environ['ADMIN_EMAIL'] = 'teacher@example.test'
os.environ['ADMIN_PASSWORD'] = 'Teacher-test-pass-123'
os.environ['SESSION_SECRET'] = 'test-only-session-secret-with-32-characters'
os.environ.pop('VERCEL', None)
os.environ.pop('BLOB_READ_WRITE_TOKEN', None)
os.environ.pop('BLOB_STORE_ID', None)

from fastapi.testclient import TestClient
import main
atexit.register(main.e.dispose)
from main import DB, User, Lesson, Work, select
from journal import StageGrade, GradeEvent


def token(client, path='/login'):
    result=client.get(path)
    assert result.status_code==200, result.text
    return re.search(r'name="token" value="([^"]+)"',result.text).group(1)


def teacher():
    c=TestClient(main.app)
    assert c.post('/login',data={'email':'teacher@example.test','password':'Teacher-test-pass-123','token':token(c)},follow_redirects=False).status_code==303
    return c


def student(email):
    c=TestClient(main.app)
    t=token(c,'/register')
    assert c.post('/register',data={'email':email,'password':'Student12345','name':'Тест Студент','group_id':1,'token':t},follow_redirects=False).status_code==303
    return c


def test_complete_learning_and_grading_flow():
    admin=teacher()
    assert admin.post('/admin/group',data={'name':'ИС-101','token':token(admin,'/admin')},follow_redirects=False).status_code==303
    s=student('student@example.test')
    other=student('other@example.test')
    with DB() as d:
        theory=d.scalar(select(Lesson).where(Lesson.kind=='theory',Lesson.number==1)).id
        practice=d.scalar(select(Lesson).where(Lesson.kind=='practice',Lesson.number==1)).id
        uid=d.scalar(select(User).where(User.email=='student@example.test')).id
    assert s.post(f'/lesson/{theory}/submit',data={'answer':'short','token':token(s,f'/lesson/{theory}')}).status_code==400
    answer='Маршрутизатор выбирает путь по наиболее длинному совпадающему префиксу.'
    assert s.post(f'/lesson/{theory}/submit',data={'answer':answer,'token':token(s,f'/lesson/{theory}')},follow_redirects=False).status_code==303
    assert s.post(f'/lesson/{theory}/submit',data={'answer':answer,'token':token(s,'/dashboard')}).status_code==409
    with DB() as d:w=d.scalar(select(Work).where(Work.user_id==uid,Work.lesson_id==theory));wid=w.id
    assert s.post(f'/admin/review/{wid}',data={'score':100,'token':token(s,'/dashboard')}).status_code==403
    assert admin.post(f'/admin/review/{wid}',data={'score':0,'decision':'revision','comment':'Добавьте пример.','token':token(admin,f'/admin/review/{wid}')},follow_redirects=False).status_code==303
    assert 'Добавьте пример.' in s.get(f'/lesson/{theory}').text
    assert s.post(f'/lesson/{theory}/submit',data={'answer':answer+' Например, /24 предпочтительнее /16.','token':token(s,f'/lesson/{theory}')},follow_redirects=False).status_code==303
    assert admin.post(f'/admin/review/{wid}',data={'score':90,'comment':'Верно','token':token(admin,f'/admin/review/{wid}')},follow_redirects=False).status_code==303
    assert admin.post(f'/journal/student/{uid}/stage/1',data={'score':85,'comment':'Этап пройден','token':token(admin,'/journal')},follow_redirects=False).status_code==303
    assert '85' in s.get('/journal').text
    assert other.get(f'/journal/student/{uid}').status_code==403
    assert s.get('/journal/export.csv').status_code==403
    assert admin.get('/journal/export.csv?stage=1').status_code==200
    assert admin.post(f'/journal/student/{uid}/stage/1',data={'score':101,'token':token(admin,'/journal')}).status_code==400
    assert admin.post(f'/journal/student/{uid}/stage/1',data={'score':100}).status_code==403
    assert s.post(f'/lesson/{practice}/submit',data={'answer':'Настроены адреса, маршруты и проверена связность.','token':token(s,f'/lesson/{practice}')},files={'upload':('lab.pkt',b'lab-content')},follow_redirects=False).status_code==303
    with DB() as d:pw=d.scalar(select(Work).where(Work.user_id==uid,Work.lesson_id==practice)).id
    assert s.get(f'/file/{pw}').content==b'lab-content'
    assert admin.get(f'/file/{pw}').status_code==200
    assert other.get(f'/file/{pw}').status_code==404
    assert TestClient(main.app).get(f'/file/{pw}').status_code==401
    assert s.get('/exam').status_code==200
    result=s.post('/exam',data={'token':token(s,'/exam')},follow_redirects=False)
    assert result.status_code==303
    assert other.get(result.headers['location']).status_code==404
    for route in ('/health','/dashboard','/trainer','/admin','/admin/analytics','/admin/exams','/journal'):
        assert admin.get(route).status_code==200,route
    main.initialize_database()
    with DB() as d:
        assert len(d.scalars(select(Lesson)).all())==100
        assert d.scalar(select(StageGrade).where(StageGrade.user_id==uid)).score==85
        assert len(d.scalars(select(GradeEvent).where(GradeEvent.user_id==uid)).all())==3


def test_vercel_configuration_rejects_sqlite():
    import subprocess, sys
    env=dict(os.environ,VERCEL='1')
    result=subprocess.run([sys.executable,'-c','import settings'],env=env,capture_output=True,text=True)
    assert result.returncode!=0
    assert 'persistent PostgreSQL' in result.stderr


def test_storage_private_backend(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from io import BytesIO
    from starlette.datastructures import UploadFile
    from vercel import blob
    import storage
    calls=[]
    async def put(path,data,**kwargs):
        calls.append((path,data,kwargs));return SimpleNamespace(pathname=path)
    async def get(path,**kwargs):
        assert kwargs['access']=='private'
        return SimpleNamespace(body=b'private-lab')
    monkeypatch.setenv('BLOB_READ_WRITE_TOKEN','test-token')
    monkeypatch.setattr(blob,'put_blob',put)
    monkeypatch.setattr(blob,'get_blob',get)
    ref=asyncio.run(storage.save_file(UploadFile(filename='test.pkt',file=BytesIO(b'private-lab'))))
    assert ref.startswith('blob:submissions/')
    assert calls[0][2]['access']=='private'
    response=asyncio.run(storage.file_response(ref))
    assert response.body==b'private-lab'
    assert response.headers['cache-control']=='private, no-store'


def test_all_lessons_have_materials():
    from curriculum import material
    with DB() as d:
        for lesson in d.scalars(select(Lesson)):
            assert len(material(lesson))>600


def test_upload_validation(monkeypatch):
    import asyncio
    from io import BytesIO
    from fastapi import HTTPException
    from starlette.datastructures import UploadFile
    import pytest
    import storage
    for filename, data, expected in [('bad.exe',b'x',400),('empty.pkt',b'',400),('large.pkt',b'x'*(storage.MAX_FILE_BYTES+1),413)]:
        with pytest.raises(HTTPException) as exc:
            asyncio.run(storage.save_file(UploadFile(filename=filename,file=BytesIO(data))))
        assert exc.value.status_code==expected
    monkeypatch.setenv('VERCEL','1')
    with pytest.raises(HTTPException) as exc:
        asyncio.run(storage.save_file(UploadFile(filename='lab.pkt',file=BytesIO(b'x'))))
    assert exc.value.status_code==503
