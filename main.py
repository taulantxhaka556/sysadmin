import os,json,secrets,hashlib,hmac,uuid,csv,io
from pathlib import Path
from html import escape as H
from fastapi import FastAPI,Request,Form,UploadFile,File,HTTPException
from fastapi.responses import HTMLResponse,RedirectResponse,FileResponse,Response
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import create_engine,Column,Integer,String,Text,ForeignKey,select
from sqlalchemy.orm import declarative_base,sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from settings import ROOT as P, DATABASE_URL as url, SESSION_SECRET as secret, ON_VERCEL
from storage import save_file, file_response
e=create_engine(url,pool_pre_ping=True,**({'connect_args':{'check_same_thread':False}} if url.startswith('sqlite') else {'poolclass':NullPool}));DB=sessionmaker(e);B=declarative_base()
class Group(B):
 __tablename__='groups';id=Column(Integer,primary_key=True);name=Column(String,unique=True)
class User(B):
 __tablename__='users';id=Column(Integer,primary_key=True);name=Column(String);email=Column(String,unique=True);pw=Column(String);role=Column(String,default='student');group_id=Column(Integer,ForeignKey('groups.id'))
class Lesson(B):
 __tablename__='lessons';id=Column(Integer,primary_key=True);kind=Column(String);number=Column(Integer);section=Column(Integer);title=Column(Text);material=Column(Text,default='')
class Work(B):
 __tablename__='works';id=Column(Integer,primary_key=True);user_id=Column(Integer,ForeignKey('users.id'));lesson_id=Column(Integer,ForeignKey('lessons.id'));status=Column(String);answer=Column(Text,default='');filename=Column(String);score=Column(Integer);comment=Column(Text,default='')
def hashed(p):
 s=secrets.token_bytes(16);return s.hex()+':'+hashlib.scrypt(p.encode(),salt=s,n=16384,r=8,p=1).hex()
def check(p,v):
 try:s,h=v.split(':');return hmac.compare_digest(hashlib.scrypt(p.encode(),salt=bytes.fromhex(s),n=16384,r=8,p=1).hex(),h)
 except Exception:return False
app=FastAPI()
def h(x):return H(str(x if x is not None else ''),quote=True)
def go(x):return RedirectResponse(x,303)
def user(r,d,admin=False):
 u=d.get(User,r.session.get('uid')) if r.session.get('uid') else None
 if not u:raise HTTPException(401,'Войдите в аккаунт')
 if admin and u.role!='admin':raise HTTPException(403)
 return u
def csrf(r,t):
 if not t or not hmac.compare_digest(t,r.session.get('csrf','')):raise HTTPException(403,'CSRF')
def token(r):return '<input type="hidden" name="token" value="'+h(r.session['csrf'])+'">'
def page(r,title,body):
 nav=('<a href="/dashboard">Учёба</a> <a href="/trainer">Тренажёр</a> <a href="/exam">Экзамен</a> <a href="/journal">Журнал</a> '+('<a href="/admin">Преподаватель</a> ' if r.session.get('role')=='admin' else '')+'<form class="inline" method="post" action="/logout">'+token(r)+'<button>Выйти</button></form>') if r.session.get('uid') else '<a href="/login">Вход</a> <a href="/register">Регистрация</a>'
 return HTMLResponse('<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+h(title)+'</title><link rel="stylesheet" href="/static/style.css"><header><b>🌐 Network Exam</b><nav>'+nav+'</nav></header><main><h1>'+h(title)+'</h1>'+body+'</main></html>')
from fastapi.staticfiles import StaticFiles
app.mount('/static',StaticFiles(directory=str(P/'static')),name='static')
@app.middleware('http')
async def add_token(r,call_next):
 if 'csrf' not in r.session:r.session['csrf']=secrets.token_urlsafe(24)
 response=await call_next(r)
 response.headers['Cache-Control']='private, no-store'
 response.headers['X-Content-Type-Options']='nosniff'
 response.headers['X-Frame-Options']='DENY'
 response.headers['Referrer-Policy']='same-origin'
 return response
app.add_middleware(SessionMiddleware,secret_key=secret or 'LOCAL_DEV_ONLY',same_site='lax',https_only=ON_VERCEL)
@app.get('/health')
def health():
 with DB() as d:
  try:d.execute(select(Lesson.id).limit(1))
  except Exception:raise HTTPException(503,'Database unavailable or not initialized')
 return {'status':'ok'}
@app.get('/')
def home(r:Request):return go('/dashboard' if r.session.get('uid') else '/login')
@app.get('/login')
def login_page(r:Request):return page(r,'Вход','<section><h2>Сеть начинается с простого запроса</h2><p>Попробуйте интерактивный модуль: схемы, короткие задания и конструктор сети.</p><a class="button" href="/learn/1/demo">Попробовать без регистрации →</a></section><form method="post">'+token(r)+'<label>Email<input type="email" name="email" required></label><label>Пароль<input type="password" name="password" required></label><button>Войти</button></form>')
@app.post('/login')
def login(r:Request,email:str=Form(...),password:str=Form(...),t:str=Form('',alias='token')):
 csrf(r,t)
 with DB() as d:
  u=d.scalar(select(User).where(User.email==email.strip().lower()))
  if not u or not check(password,u.pw):raise HTTPException(401,'Неверный email или пароль')
  r.session.clear();r.session.update({'uid':u.id,'role':u.role,'csrf':secrets.token_urlsafe(24)})
  return go('/admin' if u.role=='admin' else '/dashboard')
@app.post('/logout')
def logout(r:Request,t:str=Form('',alias='token')):
 csrf(r,t);r.session.clear();return go('/login')
@app.get('/register')
def register_page(r:Request):
 with DB() as d:
  opts=''.join(f'<option value="{g.id}">{h(g.name)}</option>' for g in d.scalars(select(Group).order_by(Group.name)))
  return page(r,'Регистрация','<p>Преподаватель сначала создаёт группы.</p><form method="post">'+token(r)+'<label>ФИО<input name="name" required></label><label>Email<input type="email" name="email" required></label><label>Пароль (8+ символов)<input type="password" name="password" minlength="8" required></label><label>Группа<select name="group_id" required>'+opts+'</select></label><button>Зарегистрироваться</button></form>')
@app.post('/register')
def register(r:Request,name:str=Form(...),email:str=Form(...),password:str=Form(...),group_id:int=Form(...),t:str=Form('',alias='token')):
 csrf(r,t)
 if not 8<=len(password)<=256 or not 2<=len(name.strip())<=120 or len(email)>254 or '@' not in email:raise HTTPException(400,'Проверьте имя, email и пароль (8–256 символов)')
 with DB() as d:
  if not d.get(Group,group_id) or d.scalar(select(User).where(User.email==email.strip().lower())):raise HTTPException(400,'Группа не существует или email занят')
  u=User(name=name.strip()[:120],email=email.strip().lower(),pw=hashed(password),group_id=group_id);d.add(u);d.commit();r.session.clear();r.session.update({'uid':u.id,'csrf':secrets.token_urlsafe(24)})
 return go('/dashboard')
@app.get('/dashboard')
def dashboard(r:Request):
 from journal import STAGES,stage_of,STATUS
 with DB() as d:
  u=user(r,d);ls=d.scalars(select(Lesson).order_by(Lesson.kind.desc(),Lesson.number)).all()
  works={w.lesson_id:w for w in d.scalars(select(Work).where(Work.user_id==u.id))}
  count=sum(w.status=='graded' for w in works.values())
  body=f'<p class="eyebrow">КУРС / КОМПЬЮТЕРНЫЕ СЕТИ</p><p>Здравствуйте, {h(u.name)}. Изучайте конспекты, выполняйте задания и отправляйте ответы преподавателю.</p><div class="summary"><b>{count} / {len(ls)}</b><span>работ проверено</span><progress max="{len(ls)}" value="{count}"></progress></div><p><a class="button" href="/journal">Мои оценки</a> <a href="/trainer">Практика IPv4</a> · <a href="/exam">Пробный экзамен</a></p>'
  body+='<section><p class="eyebrow">НОВЫЙ ФОРМАТ · МОДУЛЬ 01</p><h2>Как устроена сеть</h2><p>Шесть коротких уроков, интерактивные схемы, 18 проверок, конструктор и итоговый тест. Результат сохраняется в вашем аккаунте.</p><a class="button" href="/learn/1">Продолжить интерактивный курс →</a></section>'
  for n,title in STAGES.items():
   stage_lessons=[l for l in ls if stage_of(l)==n]
   done=sum(l.id in works and works[l.id].status=='graded' for l in stage_lessons)
   body+=f'<details class="stage" {"open" if n==1 else ""}><summary><span>Этап {n} · {h(title)}</span><small>{done}/{len(stage_lessons)} проверено</small></summary><div class="list">'
   for l in stage_lessons:
    w=works.get(l.id)
    status=(str(w.score)+'/100') if w and w.score is not None else STATUS.get(w.status,'Не начато') if w else 'Не начато'
    body+=f'<a class="item" href="/lesson/{l.id}"><span>{"Теория" if l.kind=="theory" else "Практика"} {l.number}. {h(l.title)}</span><small>{h(status)}</small></a>'
   body+='</div></details>'
  return page(r,'Подготовка к экзамену',body)
@app.get('/lesson/{id}')
def lesson(r:Request,id:int):
 with DB() as d:
  u=user(r,d);l=d.get(Lesson,id)
  if not l:raise HTTPException(404)
  w=d.scalar(select(Work).where(Work.user_id==u.id,Work.lesson_id==id));body=f'<p class="tag">{"Теория" if l.kind=="theory" else "Практика"} № {l.number}</p><section><h2>{h(l.title)}</h2><h3>Материал</h3><p class="pre">{h(l.material) if l.material else "Преподаватель пока не добавил учебный материал."}</p></section>'
  if u.role=='student' and (not w or w.status not in ('pending','graded')):
   body+=f'<form method="post" action="/lesson/{id}/submit" enctype="multipart/form-data">'+token(r)
   body+='<label>'+('Ответ на вопрос своими словами' if l.kind=='theory' else 'Отчёт: что настроено, как проверено, какой результат')+'<textarea name="answer" rows="6" minlength="20" maxlength="15000" required>'+h(w.answer if w else '')+'</textarea></label>'
   if l.kind=='practice':body+='<label>Файл работы (до 4 МБ)<input type="file" name="upload" accept=".pkt,.pka,.png,.jpg,.jpeg,.pdf,.txt,.zip,.pcap,.pcapng"></label>'
   body+='<button>Отправить на проверку</button></form>'
  if w:body+='<p>Статус: '+h(journal.STATUS.get(w.status,w.status))+'; оценка: '+h(w.score if w.score is not None else 'не выставлена')+'</p><p>'+h(w.comment)+'</p>'
  return page(r,'Задание',body)
@app.post('/lesson/{id}/submit')
async def submit(r:Request,id:int,t:str=Form('',alias='token'),answer:str=Form(''),upload:UploadFile|None=File(None)):
 csrf(r,t)
 with DB() as d:
  u=user(r,d)
  if u.role!='student':raise HTTPException(403)
  l=d.get(Lesson,id)
  if not l:raise HTTPException(404)
  w=d.scalar(select(Work).where(Work.user_id==u.id,Work.lesson_id==id))
  if not w:w=Work(user_id=u.id,lesson_id=id);d.add(w)
  if w.status in ('graded','pending'):raise HTTPException(409,'Работа уже отправлена. Для повторной сдачи преподаватель должен вернуть её на доработку.')
  if len(answer.strip())<20 or len(answer)>15000:raise HTTPException(400,'Ответ должен содержать от 20 до 15000 символов')
  w.status='pending';w.answer=answer;w.score=None
  if l.kind=='practice' and upload and upload.filename:
   w.filename=await save_file(upload)
  d.commit()
 return go('/lesson/'+str(id))
@app.get('/admin')
def admin(r:Request):
 with DB() as d:
  user(r,d,True);groups=d.scalars(select(Group)).all();students=d.scalars(select(User).where(User.role=='student')).all();works=d.scalars(select(Work)).all();ls={l.id:l for l in d.scalars(select(Lesson))};names={g.id:g.name for g in groups};body='<p><a href="/journal">Журнал оценок</a> · <a href="/admin/analytics">📊 Расширенная аналитика</a> · <a href="/admin/exams">📝 Проверка пробных экзаменов</a></p><h2>Группы</h2><form method="post" action="/admin/group">'+token(r)+'<input name="name" placeholder="ИС-24-1" required><button>Создать группу</button></form><p>'+', '.join(h(g.name) for g in groups)+'</p><h2>Студенты</h2><a href="/admin/report.csv">Экспорт CSV</a><div class="list">'
  for u in students:
   uw=[w for w in works if w.user_id==u.id];th=sum(1 for w in uw if ls[w.lesson_id].kind=='theory' and w.status in ('done','graded'));pr=sum(1 for w in uw if ls[w.lesson_id].kind=='practice' and w.status=='graded');body+=f'<div class="item">{h(u.name)} — {h(names.get(u.group_id))} — теория {th}/60, практика {pr}/40</div>'
  body+='</div><h2>Ожидают проверки</h2><div class="list">'
  for w in works:
   if w.status=='pending':
    u=next((x for x in students if x.id==w.user_id),None);body+=f'<a class="item" href="/admin/review/{w.id}">{h(u.name if u else "Студент")} — {"Теория" if ls[w.lesson_id].kind=="theory" else "Практика"} № {ls[w.lesson_id].number}</a>'
  body+='</div><h2>Редактировать учебные материалы</h2><div class="list">'
  for l in ls.values():body+=f'<a class="item" href="/admin/edit/{l.id}">{h(l.kind)} № {l.number}: {h(l.title)}</a>'
  return page(r,'Панель преподавателя',body+'</div>')
@app.post('/admin/group')
def group(r:Request,name:str=Form(...),t:str=Form('',alias='token')):
 csrf(r,t)
 with DB() as d:
  user(r,d,True)
  if len(name.strip())<2:raise HTTPException(400)
  if not d.scalar(select(Group).where(Group.name==name.strip())):d.add(Group(name=name.strip()[:120]));d.commit()
 return go('/admin')
@app.get('/admin/edit/{id}')
def edit(r:Request,id:int):
 with DB() as d:
  user(r,d,True);l=d.get(Lesson,id)
  if not l:raise HTTPException(404)
  return page(r,'Редактирование № '+str(l.number),'<p>'+h(l.title)+'</p><form method="post">'+token(r)+'<label>Учебный материал / инструкция<textarea rows="16" name="material">'+h(l.material)+'</textarea></label><button>Сохранить</button></form>')
@app.post('/admin/edit/{id}')
def save(r:Request,id:int,material:str=Form(''),t:str=Form('',alias='token')):
 csrf(r,t)
 with DB() as d:
  user(r,d,True);l=d.get(Lesson,id)
  if not l:raise HTTPException(404)
  l.material=material[:40000];d.commit()
 return go('/admin/edit/'+str(id))
@app.get('/admin/review/{id}')
def review_page(r:Request,id:int):
 with DB() as d:
  user(r,d,True);w=d.get(Work,id)
  if not w:raise HTTPException(404)
  l=d.get(Lesson,w.lesson_id);u=d.get(User,w.user_id);body=f'<p>{h(u.name)} — {h(l.title)}</p><section class="pre">{h(w.answer)}</section>'
  if w.filename:body+=f'<p><a href="/file/{id}">Скачать файл студента</a></p>'
  return page(r,'Проверка работы',body+'<form method="post">'+token(r)+f'<label>Оценка 0–100<input name="score" type="number" min="0" max="100" value="{w.score if w.score is not None else 0}" required></label><label>Комментарий<textarea name="comment" maxlength="5000">{h(w.comment)}</textarea></label><label>Решение<select name="decision"><option value="graded">Оценить</option><option value="revision">Вернуть на доработку</option></select></label><button>Сохранить</button></form>')
@app.post('/admin/review/{id}')
def review(r:Request,id:int,score:int=Form(...),comment:str=Form(''),t:str=Form('',alias='token'),decision:str=Form('graded')):
 csrf(r,t)
 if not 0<=score<=100:raise HTTPException(400)
 with DB() as d:
  user(r,d,True);w=d.get(Work,id)
  if not w:raise HTTPException(404)
  if decision not in ('graded','revision'):raise HTTPException(400)
  if decision=='revision' and not comment.strip():raise HTTPException(400,'Напишите, что нужно исправить')
  from journal import record_review
  record_review(d,w,r.session['uid'],score,comment,decision)
  d.commit()
 return go('/admin')
@app.get('/file/{id}')
async def download(r:Request,id:int):
 with DB() as d:
  u=user(r,d);w=d.get(Work,id)
  if not w or not w.filename or (u.role!='admin' and w.user_id!=u.id):raise HTTPException(404)
  return await file_response(w.filename)
@app.get('/admin/report.csv')
def report(r:Request):
 with DB() as d:
  user(r,d,True);groups={g.id:g.name for g in d.scalars(select(Group))};ls={l.id:l for l in d.scalars(select(Lesson))};works=d.scalars(select(Work)).all();out=io.StringIO();writer=csv.writer(out);writer.writerow(['ФИО','Email','Группа','Теория / 60','Практика / 40','Средняя оценка'])
  for u in d.scalars(select(User).where(User.role=='student')):
   uw=[w for w in works if w.user_id==u.id];theory=sum(1 for w in uw if ls[w.lesson_id].kind=='theory' and w.status in ('done','graded'));scores=[w.score for w in uw if ls[w.lesson_id].kind=='practice' and w.status=='graded' and w.score is not None];writer.writerow([u.name,u.email,groups.get(u.group_id,''),theory,len(scores),round(sum(scores)/len(scores),1) if scores else ''])
  return Response('\ufeff'+out.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="report.csv"'})

import upgrade  # noqa: E402 - register extended routes
import journal
import learning

def initialize_database():
 # Explicit bootstrap, not a write on every serverless cold start.
 with e.begin() as connection:
  if connection.dialect.name=='postgresql':connection.execute(text('SELECT pg_advisory_xact_lock(8042026)'))
  B.metadata.create_all(connection)
  with DB(bind=connection) as d:
   data=json.loads((P/'content.json').read_text(encoding='utf-8'))
   existing={(x.kind,x.number) for x in d.scalars(select(Lesson))}
   for kind in ('theory','practice'):
    for x in data[kind]:
     if (kind,x['number']) not in existing:d.add(Lesson(kind=kind,number=x['number'],section=x.get('section',0),title=x['title']))
   email=os.getenv('ADMIN_EMAIL','').strip().lower();password=os.getenv('ADMIN_PASSWORD','')
   if email and not d.scalar(select(User).where(User.email==email)):
    if len(password)<12 or password.startswith('replace-'):raise RuntimeError('Set ADMIN_PASSWORD with at least 12 characters')
    d.add(User(name='Преподаватель',email=email,pw=hashed(password),role='admin'))
   d.flush()
   upgrade.seed_materials(d)
   d.commit()

if not ON_VERCEL and os.getenv('AUTO_INIT_DB','1')=='1':initialize_database()

