import json,random,ipaddress,datetime,csv,io
from sqlalchemy import Column,Integer,String,Text,ForeignKey,select
from fastapi import Request,Form,HTTPException
from fastapi.responses import Response
from main import B,e,DB,Lesson,User,Group,Work,app,user,csrf,token,page,go,h
class Attempt(B):
 __tablename__='auto_attempts';id=Column(Integer,primary_key=True);user_id=Column(Integer,ForeignKey('users.id'));question=Column(Text);answer=Column(Text);expected=Column(Text);score=Column(Integer);created=Column(String)
class Exam(B):
 __tablename__='mock_exams';id=Column(Integer,primary_key=True);user_id=Column(Integer,ForeignKey('users.id'));payload=Column(Text);score=Column(Integer,nullable=True);created=Column(String)
def seed_materials(d):
 from curriculum import material
 for lesson in d.scalars(select(Lesson)):
  if not lesson.material:
   lesson.material=material(lesson)

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
KEYS=['network','broadcast','first','last','hosts','mask']
def task():
 n=ipaddress.ip_network('192.168.%s.0/%s'%(random.choice([10,20,30,40,50]),random.choice([25,26,27,28])));k=random.choice(KEYS);return n,k
def expected(n,k):return {'network':str(n.network_address),'broadcast':str(n.broadcast_address),'first':str(n.network_address+1),'last':str(n.broadcast_address-1),'hosts':str(n.num_addresses-2),'mask':str(n.netmask)}[k]
@app.get('/trainer')
def trainer(r:Request):
 with DB() as d:user(r,d)
 n,k=task();r.session['trainer']=[str(n),k];labels=dict(network='адрес сети',broadcast='broadcast',first='первый адрес узла',last='последний адрес узла',hosts='число доступных адресов узлов',mask='маску подсети')
 return page(r,'Тренажёр IPv4','<p>Автоматическая проверка подсетей.</p><form method="post" action="/trainer/check">'+token(r)+f'<p>Подсеть <b>{n}</b>: определите {labels[k]}.</p><input type="hidden" name="network" value="{n}"><input type="hidden" name="kind" value="{k}"><label>Ответ<input name="answer" required></label><button>Проверить</button></form>')
@app.post('/trainer/check')
def check_task(r:Request,network:str=Form(...),kind:str=Form(...),answer:str=Form(...),t:str=Form('',alias='token')):
 csrf(r,t)
 if r.session.get('trainer') != [network,kind]:raise HTTPException(400,'Задание изменилось. Откройте тренажёр заново.')
 r.session.pop('trainer',None)
 try:n=ipaddress.ip_network(network,strict=True)
 except ValueError:raise HTTPException(400)
 if kind not in KEYS or not isinstance(n,ipaddress.IPv4Network) or not n.is_private or n.prefixlen not in (25,26,27,28):raise HTTPException(400)
 correct=expected(n,kind);score=100 if answer.strip()==correct else 0
 with DB() as d:
  u=user(r,d);d.add(Attempt(user_id=u.id,question=network+' '+kind,answer=answer[:100],expected=correct,score=score,created=now()));d.commit()
 return page(r,'Проверка',f'<section><h2>{"Верно" if score else "Неверно"}</h2><p>Ваш ответ: {h(answer)}</p><p>Правильный ответ: <b>{h(correct)}</b></p><p>В этой подсети {n.num_addresses} адресов. Первый адрес обозначает сеть, последний — broadcast.</p><a href="/trainer">Следующая задача</a></section>')
@app.post('/exam')
def new_exam(r:Request,t:str=Form('',alias='token')):
 csrf(r,t)
 with DB() as d:
  u=user(r,d);ls=d.scalars(select(Lesson).where(Lesson.kind=='theory')).all();questions=[{'id':l.id,'title':l.title} for l in random.sample(ls,min(10,len(ls)))];ex=Exam(user_id=u.id,payload=json.dumps({'questions':questions,'answers':{}},ensure_ascii=False),created=now());d.add(ex);d.commit();return go('/exam/'+str(ex.id))
@app.get('/exam/{id}')
def exam_view(r:Request,id:int):
 with DB() as d:
  u=user(r,d);ex=d.get(Exam,id)
  if not ex or (ex.user_id!=u.id and u.role!='admin'):raise HTTPException(404)
  p=json.loads(ex.payload);body='<p>10 случайных теоретических вопросов. Свободные ответы проверяет преподаватель.</p><form method="post">'+token(r)
  for i,q in enumerate(p['questions'],1):body+=f'<label>{i}. {h(q["title"])}<textarea name="q_{q["id"]}" rows="4" {"readonly" if p.get("submitted") else "required"}>{h(p["answers"].get(str(q["id"]),""))}</textarea></label>'
  if not p.get('submitted'):body+='<button>Сдать экзамен</button>'
  else:body+='<p>Экзамен сдан. Оценка: '+(str(ex.score) if ex.score is not None else 'ожидает проверки')+'</p>'
  return page(r,'Пробный экзамен',body+'</form>')
@app.post('/exam/{id}')
async def exam_submit(r:Request,id:int):
 form=await r.form();csrf(r,str(form.get('token','')))
 with DB() as d:
  u=user(r,d);ex=d.get(Exam,id)
  if not ex or ex.user_id!=u.id:raise HTTPException(403)
  p=json.loads(ex.payload)
  if p.get('submitted'):raise HTTPException(409)
  ans={str(q['id']):str(form.get('q_'+str(q['id']),''))[:5000] for q in p['questions']}
  if any(len(x.strip())<10 for x in ans.values()):raise HTTPException(400,'Заполните все ответы')
  p.update(answers=ans,submitted=True);ex.payload=json.dumps(p,ensure_ascii=False);d.commit()
 return go('/exam/'+str(id))
@app.get('/admin/exams')
def exams_admin(r:Request):
 with DB() as d:
  user(r,d,True);names={u.id:u.name for u in d.scalars(select(User))};exams=d.scalars(select(Exam).order_by(Exam.id.desc())).all();body='<div class="list">'
  for x in exams:
   p=json.loads(x.payload)
   if p.get('submitted'):body+=f'<a class="item" href="/admin/exams/{x.id}">{h(names.get(x.user_id))} — {h(x.created[:10])} — {"ожидает проверки" if x.score is None else str(x.score)+"/100"}</a>'
  return page(r,'Проверка экзаменов',body+'</div>')
@app.get('/admin/exams/{id}')
def exam_grade_page(r:Request,id:int):
 with DB() as d:
  user(r,d,True);ex=d.get(Exam,id)
  if not ex:raise HTTPException(404)
  p=json.loads(ex.payload)
  if not p.get('submitted'):raise HTTPException(400)
  body='<form method="post">'+token(r)
  for q in p['questions']:body+=f'<section><b>{h(q["title"])}</b><p class="pre">{h(p["answers"].get(str(q["id"]),""))}</p></section>'
  return page(r,'Оценка экзамена',body+'<label>Итоговая оценка 0–100<input type="number" name="score" min="0" max="100" required></label><button>Сохранить оценку</button></form>')
@app.post('/admin/exams/{id}')
def exam_grade(r:Request,id:int,score:int=Form(...),t:str=Form('',alias='token')):
 csrf(r,t)
 if not 0<=score<=100:raise HTTPException(400)
 with DB() as d:
  user(r,d,True);ex=d.get(Exam,id)
  if not ex or not json.loads(ex.payload).get('submitted'):raise HTTPException(404)
  ex.score=score;d.commit()
 return go('/admin/exams')
def stats(d):
 users=d.scalars(select(User).where(User.role=='student')).all();groups={g.id:g.name for g in d.scalars(select(Group))};works=d.scalars(select(Work)).all();ls={l.id:l for l in d.scalars(select(Lesson))};aa=d.scalars(select(Attempt)).all();exams=d.scalars(select(Exam)).all();rows=[]
 for u in users:
  w=[x for x in works if x.user_id==u.id];a=[x for x in aa if x.user_id==u.id];xx=[x for x in exams if x.user_id==u.id];scores=[x.score for x in w if x.score is not None];rows.append([u.name,u.email,groups.get(u.group_id,''),sum(x.status in ('done','graded') and ls[x.lesson_id].kind=='theory' for x in w),sum(x.status=='graded' and ls[x.lesson_id].kind=='practice' for x in w),sum(x.status=='pending' for x in w),len(a),round(sum(x.score for x in a)/len(a),1) if a else '',round(sum(scores)/len(scores),1) if scores else '',len(xx),round(sum(x.score for x in xx if x.score is not None)/len([x for x in xx if x.score is not None]),1) if any(x.score is not None for x in xx) else ''])
 return rows
HEAD=['ФИО','Email','Группа','Теория изучено','Практика оценено','Практика ожидает','Попытки тренажёра','Точность тренажёра %','Средняя практика','Экзамены начаты','Средняя оценка экзаменов']
@app.get('/admin/analytics')
def analytics(r:Request):
 with DB() as d:
  user(r,d,True);rows=stats(d);body=f'<p>Студентов: <b>{len(rows)}</b> · Отправлено практических работ: <b>{sum(x[4]+x[5] for x in rows)}</b> · Попыток тренажёра: <b>{sum(x[6] for x in rows)}</b></p><p><a href="/admin/analytics.csv">Скачать CSV</a> · <a href="/admin/exams">Проверить экзамены</a></p><div style="overflow-x:auto"><table><tr>'+''.join('<th>'+h(x)+'</th>' for x in HEAD)+'</tr>'
  for row in rows:body+='<tr>'+''.join('<td>'+h(x)+'</td>' for x in row)+'</tr>'
  return page(r,'Расширенная аналитика',body+'</table></div>')
@app.get('/admin/analytics.csv')
def analytics_csv(r:Request):
 with DB() as d:
  user(r,d,True);output=io.StringIO();writer=csv.writer(output);writer.writerow(HEAD);writer.writerows(stats(d));return Response('\ufeff'+output.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="analytics.csv"'})
