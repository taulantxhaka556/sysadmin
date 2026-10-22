"""Teacher group management and read-only course summaries from existing records."""
import json
from collections import defaultdict

from fastapi import Request, Form, HTTPException
from sqlalchemy.exc import IntegrityError
from main import app, DB, Group, User, Lesson, Work, select, user, csrf, token, page, go, h
from learning import LearningProgress, CourseProgress, initial, passed, completed
from course_catalog import MODULES


def snapshot(d, students):
    """Read progress in batches; legacy module-one state has the same precedence as learning."""
    ids=[s.id for s in students]
    states=defaultdict(dict); works=defaultdict(list)
    if ids:
        for row in d.scalars(select(CourseProgress).where(CourseProgress.user_id.in_(ids))):
            states[row.user_id][row.module_id]=initial()|json.loads(row.payload)
        for row in d.scalars(select(LearningProgress).where(LearningProgress.user_id.in_(ids))):
            states[row.user_id][1]=initial()|json.loads(row.payload)
        for row in d.scalars(select(Work).where(Work.user_id.in_(ids))):
            works[row.user_id].append(row)
    lesson_map={l.id:l for l in d.scalars(select(Lesson))}
    result={}
    for student in students:
        modules=[]
        for number,m in MODULES.items():
            state=initial()|states[student.id].get(number,{})
            modules.append(dict(id=number,done=passed(state),best=state['best'],
                lessons=sum(completed(state,l) for l in m['lessons']),total=len(m['lessons']),lab=state['lab']))
        reports=works[student.id]
        scores=[w.score for w in reports if w.status=='graded' and w.score is not None]
        tests=[m['best'] for m in modules if m['best'] is not None]
        count=sum(m['done'] for m in modules)
        result[student.id]=dict(student=student,modules=modules,done=count,percent=round(count/len(MODULES)*100),
            lessons=sum(m['lessons'] for m in modules),pending=sum(w.status=='pending' for w in reports),
            revision=sum(w.status=='revision' for w in reports),
            practice=sum(w.status=='graded' and lesson_map.get(w.lesson_id) is not None and lesson_map[w.lesson_id].kind=='practice' for w in reports),
            average=round(sum(scores)/len(scores),1) if scores else None,
            test_average=round(sum(tests)/len(tests),1) if tests else None,
            started=bool(reports) or any(m['lessons'] or m['lab'] or m['best'] is not None for m in modules)
                or any(s.get('attempts') or s.get('solved') or s.get('lab_attempts') for s in states[student.id].values()))
    return result,works,lesson_map


def metrics(rows):
    n=len(rows)
    values=[('Студентов',n),('Средний прогресс',str(round(sum(r['done'] for r in rows)/(n*len(MODULES))*100))+'%' if n else '—'),
            ('Ожидают проверки',sum(r['pending'] for r in rows)),('На доработке',sum(r['revision'] for r in rows))]
    return '<div class="admin-metrics">'+''.join(f'<div><span>{h(label)}</span><strong>{h(value)}</strong></div>' for label,value in values)+'</div>'


def group_card(group_id,name,rows):
    percent=round(sum(r['done'] for r in rows)/(len(rows)*len(MODULES))*100) if rows else 0
    pending=sum(r['pending'] for r in rows)
    return f'''<a class="group-card" href="/admin/groups/{group_id}"><span class="eyebrow">УЧЕБНАЯ ГРУППА</span><h2>{h(name)}</h2>
    <p>{len(rows)} студентов <span>· {pending} работ на проверке</span></p><div class="group-progress"><span>Средний прогресс по модулям</span><strong>{str(percent)+'%' if rows else '—'}</strong></div>
    <progress value="{percent}" max="100" aria-label="Прогресс группы {h(name)}">{percent}%</progress><span class="group-open">Открыть группу →</span></a>'''


def overview(r):
    with DB() as d:
        user(r,d,True)
        groups=d.scalars(select(Group).order_by(Group.name)).all()
        students=d.scalars(select(User).where(User.role=='student').order_by(User.name)).all()
        data,works,lessons=snapshot(d,students)
        body='<p class="page-intro">Создавайте группы и следите за обучением: от первого урока до итогового теста.</p>'+metrics(list(data.values()))
        body+='<div class="admin-actions"><a href="/journal">Журнал оценок</a><a href="/admin/exams">Пробные экзамены</a><a href="/admin/analytics">Аналитика работ</a></div>'
        body+='<section class="create-group"><div><h2>Новая группа</h2><p class="muted">После создания группа появится в форме регистрации студентов.</p></div><form method="post" action="/admin/group">'+token(r)+'<label for="group-name">Название группы</label><div class="group-create"><input id="group-name" name="name" placeholder="Например, ИС-24-1" minlength="2" maxlength="120" required><button>Создать группу</button></div></form></section>'
        body+='<div class="section-heading"><h2>Ваши группы</h2><span class="muted">'+str(len(groups))+'</span></div><div class="group-grid">'
        for group in groups:
            body+=group_card(group.id,group.name,[data[s.id] for s in students if s.group_id==group.id])
        unassigned=[data[s.id] for s in students if s.group_id is None]
        if unassigned:body+=group_card(0,'Без группы',unassigned)
        body+='</div>'
        if not groups and not students:body+='<section class="empty"><h2>Создайте первую группу</h2><p>Затем студенты смогут зарегистрироваться и выбрать её. Здесь появятся их результаты.</p></section>'
        body+='<details class="admin-materials"><summary>Редактирование учебных материалов</summary><div class="list">'
        for l in sorted(lessons.values(),key=lambda l:(l.kind!='theory',l.number)):
            body+=f'<a class="item" href="/admin/edit/{l.id}">{"Теория" if l.kind=="theory" else "Практика"} {l.number}. {h(l.title)}</a>'
        return page(r,'Группы и обучение',body+'</div></details>')


def error(r,message,status=400):
    response=page(r,'Не удалось сохранить',f'<section><p role="alert">{h(message)}</p><a class="button" href="/admin">Вернуться к группам</a></section>')
    response.status_code=status
    return response


def valid_name(d,name,exclude=None):
    name=' '.join(name.split())
    if not 2<=len(name)<=120:return None,'Название должно содержать от 2 до 120 символов.',400
    if any(g.id!=exclude and g.name.casefold()==name.casefold() for g in d.scalars(select(Group))):
        return None,'Группа с таким названием уже существует.',409
    return name,None,None


def create_group(r,name,t):
    with DB() as d:
        user(r,d,True);csrf(r,t)
        name,message,status=valid_name(d,name)
        if message:return error(r,message,status)
        group=Group(name=name);d.add(group)
        try:d.commit()
        except IntegrityError:
            d.rollback();return error(r,'Группа с таким названием уже существует.',409)
        return go(f'/admin/groups/{group.id}')


@app.get('/admin/groups/{id}')
def group_page(r:Request,id:int,q:str='',state:str=''):
    with DB() as d:
        user(r,d,True)
        group=d.get(Group,id) if id else None
        if id and not group:raise HTTPException(404,'Группа не найдена')
        name=group.name if group else 'Без группы'
        groups=d.scalars(select(Group).order_by(Group.name)).all()
        students=d.scalars(select(User).where(User.role=='student',User.group_id==(id or None)).order_by(User.name)).all()
        data,works,lessons=snapshot(d,students)
        body='<p><a href="/admin">← Все группы</a></p>'+metrics(list(data.values()))
        body+='<p class="muted">Прогресс — доля завершённых модулей из 14. Модуль завершён после практической модели и итогового теста от 70/100. Оценки преподавателя за отчёты учитываются отдельно.</p>'
        if group:
            body+=f'<div class="admin-actions"><a href="/journal?group_id={id}">Журнал этой группы</a><a href="/journal/export.csv?group_id={id}&stage=1">CSV журнала · этап 1</a></div><details class="group-settings"><summary>Название группы</summary><form method="post" action="/admin/groups/{id}/rename">'+token(r)+f'<label>Новое название<input name="name" value="{h(name)}" minlength="2" maxlength="120" required></label><button>Сохранить название</button></form></details>'
        if not students:
            body+='<section class="empty"><h2>Пока нет студентов</h2><p>Попросите студентов открыть страницу регистрации и выбрать группу «'+h(name)+'». Уже зарегистрированного студента можно перевести сюда со страницы его группы.</p><a href="/register">Открыть страницу регистрации</a></section>'
            return page(r,name,body)
        body+=f'<form class="filters admin-filters" method="get"><label>Поиск студента<input name="q" value="{h(q[:200])}" placeholder="Имя или email" maxlength="200"></label><label>Показать<select name="state">'
        for value,label in [('', 'Всех студентов'),('pending','Есть работы на проверке'),('revision','Есть работы на доработке'),('new','Ещё не начали'),('complete','Курс завершён')]:
            body+=f'<option value="{value}"'+(' selected' if value==state else '')+'>'+label+'</option>'
        body+=f'</select></label><button>Показать</button><a href="/admin/groups/{id}">Сбросить</a></form>'
        def matches(s):
            row=data[s.id]
            return q[:200].strip().casefold() in (s.name+' '+s.email).casefold() and (not state or
                (state=='pending' and row['pending']) or (state=='revision' and row['revision']) or
                (state=='new' and not row['started']) or (state=='complete' and row['done']==len(MODULES)))
        shown=[s for s in students if matches(s)]
        body+=f'<div class="section-heading"><h2>Студенты</h2><span role="status">{len(shown)} из {len(students)}</span></div>'
        if not shown:return page(r,name,body+'<section class="empty"><h2>Нет студентов по этому запросу</h2><p>Измените поиск или сбросьте фильтры.</p></section>')
        body+='<div class="table-wrap admin-table" tabindex="0" role="region" aria-label="Прогресс студентов"><table><thead><tr><th>Студент</th><th>Модули</th><th>Уроки</th><th>Практика проверена</th><th>Средний балл работ</th><th>Работы</th><th>Группа</th></tr></thead><tbody>'
        for s in shown:
            row=data[s.id]
            body+=f'<tr><th scope="row"><a href="/journal/student/{s.id}">{h(s.name)}</a><small class="student-email">{h(s.email)}</small></th><td><strong>{row["done"]} / 14</strong><progress value="{row["done"]}" max="14" aria-label="Модули: {h(s.name)}"></progress></td><td>{row["lessons"]} / 60</td><td>{row["practice"]} / 40</td><td>{str(row["average"])+"/100" if row["average"] is not None else "—"}</td><td>{row["pending"]} на проверке<br>{row["revision"]} на доработке</td><td>'
            body+=f'<details><summary>Перевести</summary><form method="post" action="/admin/students/{s.id}/group">'+token(r)+f'<label>Группа для {h(s.name)}<select name="group_id" required>'
            for g in groups:body+=f'<option value="{g.id}"'+(' selected' if s.group_id==g.id else '')+'>'+h(g.name)+'</option>'
            body+='</select></label><button>Перевести</button></form></details></td></tr>'
        body+='</tbody></table></div><h2 class="admin-section-title">Результаты по модулям</h2><p class="muted">✓ — модуль завершён; число — лучший результат итогового теста; «—» — тест ещё не завершён. Под результатом — пройденные уроки.</p><div class="table-wrap admin-table" tabindex="0" role="region" aria-label="Результаты по 14 модулям"><table><thead><tr><th>Студент</th>'
        body+=''.join(f'<th title="{h(m["title"])}">{n}. {h(m["title"])}</th>' for n,m in MODULES.items())+'</tr></thead><tbody>'
        for s in shown:
            body+=f'<tr><th scope="row"><a href="/journal/student/{s.id}">{h(s.name)}</a></th>'
            for m in data[s.id]['modules']:
                label=('✓ ' if m['done'] else '')+(str(m['best'])+'/100' if m['best'] is not None else '—')
                body+=f'<td class="module-result {"passed" if m["done"] else ""}">{label}<small>{m["lessons"]}/{m["total"]} уроков</small><small>Модель: {"выполнена" if m["lab"] else "не выполнена"}</small></td>'
            body+='</tr>'
        body+='</tbody></table></div><h2 class="admin-section-title">Ожидают проверки</h2><div class="list">'
        queue=[(s,w) for s in shown for w in works[s.id] if w.status=='pending']
        for s,w in sorted(queue,key=lambda pair:pair[1].id,reverse=True):
            lesson=lessons.get(w.lesson_id)
            body+=f'<a class="item" href="/admin/review/{w.id}"><span>{h(s.name)} · {h(lesson.title if lesson else "Работа")}</span><strong>Проверить →</strong></a>'
        if not queue:body+='<p class="muted">У выбранных студентов нет работ на проверке.</p>'
        return page(r,name,body+'</div>')


@app.post('/admin/groups/{id}/rename')
def rename_group(r:Request,id:int,name:str=Form(...),t:str=Form('',alias='token')):
    with DB() as d:
        user(r,d,True);csrf(r,t)
        group=d.get(Group,id)
        if not group:raise HTTPException(404)
        name,message,status=valid_name(d,name,id)
        if message:return error(r,message,status)
        group.name=name
        try:d.commit()
        except IntegrityError:
            d.rollback();return error(r,'Группа с таким названием уже существует.',409)
    return go(f'/admin/groups/{id}')


@app.post('/admin/students/{id}/group')
def move_student(r:Request,id:int,group_id:int=Form(...),t:str=Form('',alias='token')):
    with DB() as d:
        user(r,d,True);csrf(r,t)
        student=d.get(User,id);group=d.get(Group,group_id)
        if not student or student.role!='student' or not group:raise HTTPException(404)
        student.group_id=group.id;d.commit()
    return go(f'/admin/groups/{group_id}')
