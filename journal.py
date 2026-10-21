"""Teacher gradebook and student progress, sharing the existing lesson records."""
import csv
import io
from datetime import datetime, timezone

from fastapi import Request, Form, HTTPException
from fastapi.responses import Response
from sqlalchemy import Column, Integer, String, Text, ForeignKey, UniqueConstraint, select
from main import B, DB, Lesson, Work, User, Group, app, user, csrf, token, page, go, h

STAGES = {
    1: 'Основы сетей и протоколы', 2: 'VLAN и сетевые службы',
    3: 'Серверы и инфраструктура', 4: 'Среды передачи и оборудование',
    5: 'Администрирование и диагностика', 6: 'Защищённые соединения',
    7: 'Защита сети и восстановление', 8: 'Облачная безопасность',
    9: 'Адресация и маршрутизация', 10: 'Сервисы и итоговый проект',
}
PRACTICE_STAGE = {1:1,2:9,3:1,4:1,5:3,6:2,7:2,8:9,9:2,10:2,11:10,12:10,
    13:9,14:9,15:9,16:9,17:9,18:9,19:9,20:9,21:7,22:7,23:6,24:6,
    25:5,26:5,27:5,28:9,29:10,30:10,31:5,32:5,33:7,34:7,35:7,36:7,
    37:8,38:7,39:10,40:10}
STATUS = {'pending':'На проверке','graded':'Оценено','revision':'На доработке','done':'Изучено (без оценки)'}


class StageGrade(B):
    __tablename__ = 'stage_grades'
    __table_args__ = (UniqueConstraint('user_id', 'stage', name='uq_student_stage'),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    stage = Column(Integer, nullable=False)
    score = Column(Integer, nullable=False)
    comment = Column(Text, default='')
    teacher_id = Column(Integer, ForeignKey('users.id'))
    updated = Column(String)


class GradeEvent(B):
    __tablename__ = 'grade_events'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    teacher_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    target = Column(String, nullable=False)
    previous_score = Column(Integer)
    score = Column(Integer)
    comment = Column(Text)
    decision = Column(String)
    created = Column(String)


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def stage_of(lesson):
    return lesson.section if lesson.kind == 'theory' else PRACTICE_STAGE[lesson.number]


def record_review(d, work, teacher_id, score, comment, decision):
    d.add(GradeEvent(user_id=work.user_id, teacher_id=teacher_id, target=f'lesson:{work.lesson_id}',
        previous_score=work.score, score=score if decision=='graded' else None,
        comment=comment[:5000], decision=decision, created=now()))
    work.score = score if decision=='graded' else None
    work.comment = comment[:5000]
    work.status = decision


def csv_safe(value):
    value = str(value if value is not None else '')
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) else value


@app.get('/journal')
def journal(r: Request, group_id: int = 0, stage: int = 1):
    if stage not in STAGES:
        raise HTTPException(400)
    with DB() as d:
        u = user(r, d)
        if u.role != 'admin':
            return student_journal(r, d, u, False)
        groups = d.scalars(select(Group).order_by(Group.name)).all()
        students = d.scalars(select(User).where(User.role=='student').order_by(User.name)).all()
        students = [s for s in students if not group_id or s.group_id == group_id]
        lessons = [l for l in d.scalars(select(Lesson).order_by(Lesson.kind.desc(),Lesson.number)) if stage_of(l)==stage]
        works = {(w.user_id,w.lesson_id):w for w in d.scalars(select(Work))}
        grades = {(g.user_id,g.stage):g for g in d.scalars(select(StageGrade))}
        body = '<p>Оценки 0–100. Нажмите на работу для проверки, на имя — для итоговой оценки этапа.</p><form method="get" class="filters"><label>Группа<select name="group_id"><option value="0">Все группы</option>'
        body += ''.join(f'<option value="{g.id}" {"selected" if g.id==group_id else ""}>{h(g.name)}</option>' for g in groups)
        body += '</select></label><label>Этап<select name="stage">'
        body += ''.join(f'<option value="{n}" {"selected" if n==stage else ""}>{n}. {h(title)}</option>' for n,title in STAGES.items())
        body += f'</select></label><button>Показать</button></form><p><a href="/journal/export.csv?group_id={group_id}&stage={stage}">Скачать журнал CSV</a></p><div class="table-wrap"><table><thead><tr><th>Студент</th>'
        body += ''.join(f'<th title="{h(l.title)}">{"Т" if l.kind=="theory" else "П"}{l.number}</th>' for l in lessons)
        body += '<th>Итог этапа</th></tr></thead><tbody>'
        for s in students:
            body += f'<tr><th><a href="/journal/student/{s.id}#stage-{stage}">{h(s.name)}</a></th>'
            for l in lessons:
                w = works.get((s.id,l.id))
                value = str(w.score) if w and w.score is not None else STATUS.get(w.status,'—') if w else '—'
                body += f'<td><a href="/admin/review/{w.id}">{h(value)}</a></td>' if w else '<td>—</td>'
            g = grades.get((s.id,stage))
            body += f'<td>{g.score if g else "—"}</td></tr>'
        if not students:
            body += f'<tr><td colspan="{len(lessons)+2}">В этой группе пока нет студентов.</td></tr>'
        return page(r,'Журнал преподавателя',body+'</tbody></table></div><p>Т — теория, П — практика. «—» — работа ещё не сдана или итог не выставлен.</p>')


def student_journal(r, d, student, teacher):
    works = {w.lesson_id:w for w in d.scalars(select(Work).where(Work.user_id==student.id))}
    grades = {g.stage:g for g in d.scalars(select(StageGrade).where(StageGrade.user_id==student.id))}
    lessons = d.scalars(select(Lesson).order_by(Lesson.kind.desc(),Lesson.number)).all()
    body = '<p>'+h(student.name)+' · Итоговые оценки выставляет преподаватель.</p>'
    for n,title in STAGES.items():
        ls = [l for l in lessons if stage_of(l)==n]
        graded = [works[l.id].score for l in ls if l.id in works and works[l.id].score is not None]
        g = grades.get(n)
        body += f'<section id="stage-{n}"><h2>{n}. {h(title)}</h2><p>Проверено: {len(graded)}/{len(ls)} · Средний балл работ: {round(sum(graded)/len(graded),1) if graded else "—"} · Итог: <b>{g.score if g else "не выставлен"}</b></p>'
        if g and g.comment:body += '<p>'+h(g.comment)+'</p>'
        body += '<div class="list">'
        for l in ls:
            w=works.get(l.id)
            link=f'/admin/review/{w.id}' if teacher and w else f'/lesson/{l.id}'
            body += f'<a class="item" href="{link}"><span>{"Т" if l.kind=="theory" else "П"}{l.number}. {h(l.title)}</span><small>{str(w.score)+"/100" if w and w.score is not None else STATUS.get(w.status,"Не начато") if w else "Не начато"}</small></a>'
            if w and w.comment:body += '<p class="feedback">'+h(w.comment)+'</p>'
        body += '</div>'
        if teacher:
            body += f'<form method="post" action="/journal/student/{student.id}/stage/{n}">'+token(r)+f'<label>Итоговая оценка этапа (0–100)<input name="score" type="number" min="0" max="100" value="{g.score if g else ""}" required></label><label>Комментарий<textarea name="comment" maxlength="5000">{h(g.comment if g else "")}</textarea></label><button>Сохранить оценку этапа</button></form>'
        body += '</section>'
    events = d.scalars(select(GradeEvent).where(GradeEvent.user_id==student.id).order_by(GradeEvent.id.desc()).limit(100)).all()
    body += '<details><summary>История последних 100 изменений оценок (UTC)</summary>'
    for event in events:
        body += f'<p>{h(event.created)} · {h(event.target)} · {h(event.previous_score)} → {h(event.score)} · {h(STATUS.get(event.decision,event.decision))} · {h(event.comment)}</p>'
    return page(r,'Журнал — '+student.name,body+'</details>')


@app.get('/journal/student/{id}')
def journal_student(r:Request,id:int):
    with DB() as d:
        u=user(r,d)
        if u.role!='admin' and u.id!=id:raise HTTPException(403)
        s=d.get(User,id)
        if not s or s.role!='student':raise HTTPException(404)
        return student_journal(r,d,s,u.role=='admin')


@app.post('/journal/student/{id}/stage/{stage}')
def grade_stage(r:Request,id:int,stage:int,score:int=Form(...),comment:str=Form(''),t:str=Form('',alias='token')):
    csrf(r,t)
    if stage not in STAGES or not 0<=score<=100:raise HTTPException(400)
    with DB() as d:
        teacher=user(r,d,True)
        student=d.get(User,id)
        if not student or student.role!='student':raise HTTPException(404)
        g=d.scalar(select(StageGrade).where(StageGrade.user_id==id,StageGrade.stage==stage))
        d.add(GradeEvent(user_id=id,teacher_id=teacher.id,target=f'stage:{stage}',previous_score=g.score if g else None,score=score,comment=comment[:5000],decision='graded',created=now()))
        if not g:
            g=StageGrade(user_id=id,stage=stage);d.add(g)
        g.score=score;g.comment=comment[:5000];g.teacher_id=teacher.id;g.updated=now()
        d.commit()
    return go(f'/journal/student/{id}#stage-{stage}')


@app.get('/journal/export.csv')
def export(r:Request,group_id:int=0,stage:int=1):
    if stage not in STAGES:raise HTTPException(400)
    with DB() as d:
        user(r,d,True)
        students=d.scalars(select(User).where(User.role=='student').order_by(User.name)).all()
        lessons=[l for l in d.scalars(select(Lesson).order_by(Lesson.kind.desc(),Lesson.number)) if stage_of(l)==stage]
        works={(w.user_id,w.lesson_id):w for w in d.scalars(select(Work))}
        grades={(g.user_id,g.stage):g for g in d.scalars(select(StageGrade))}
        out=io.StringIO();writer=csv.writer(out)
        writer.writerow(['Студент']+[('Т' if l.kind=='theory' else 'П')+str(l.number) for l in lessons]+['Итог этапа'])
        for s in students:
            if group_id and s.group_id!=group_id:continue
            row=[s.name]+[works[(s.id,l.id)].score if (s.id,l.id) in works else '' for l in lessons]+[grades[(s.id,stage)].score if (s.id,stage) in grades else '']
            writer.writerow([csv_safe(x) for x in row])
        return Response('\ufeff'+out.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="journal-stage-{stage}.csv"'})


@app.get('/exam')
def exam_start(r:Request):
    from upgrade import Exam
    with DB() as d:
        u=user(r,d)
        exams=d.scalars(select(Exam).where(Exam.user_id==u.id).order_by(Exam.id.desc())).all()
        body='<p>10 случайных вопросов. Ответы проверяет преподаватель.</p><form method="post">'+token(r)+'<button>Начать новый экзамен</button></form><h2>Мои попытки</h2><div class="list">'
        for ex in exams:
            body+=f'<a class="item" href="/exam/{ex.id}">Экзамен №{ex.id} · {h(ex.created[:10])}<span>{str(ex.score)+"/100" if ex.score is not None else "Без оценки"}</span></a>'
        return page(r,'Пробный экзамен',body+'</div>')
