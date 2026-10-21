"""Module-one learning flow, server grading and isolated signed-cookie demo."""
import copy
import json
import secrets
import time
from contextlib import contextmanager

from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import Column, Integer, String, Text, ForeignKey, select, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from main import B, DB, User, Lesson, Work, app, csrf, user, h, P
from module1_content import LESSONS, EXAM
from course_catalog import MODULES, SOURCE_P
from course_labs import LABS, simulate, terminal


class LearningProgress(B):
    __tablename__ = 'learning_module_one'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    payload = Column(Text, nullable=False, default='{}')


class CourseProgress(B):
    __tablename__ = 'learning_course'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    module_id = Column(Integer, primary_key=True)
    payload = Column(Text, nullable=False, default='{}')


class DemoProgress(B):
    __tablename__ = 'learning_demo'
    id = Column(String(64), primary_key=True)
    payload = Column(Text, nullable=False, default='{}')
    updated = Column(Integer, nullable=False)


def module(number):
    if number not in MODULES: raise HTTPException(404, 'Модуль не найден')
    return MODULES[number]


def account_states(d, uid):
    rows={row.module_id:initial()|json.loads(row.payload) for row in d.scalars(select(CourseProgress).where(CourseProgress.user_id==uid))}
    first=d.get(LearningProgress,uid)
    if first: rows[1]=initial()|json.loads(first.payload)
    return rows


def passed(state):
    return state.get('lab',False) and (state.get('best') or 0)>=70


def initial():
    return dict(solved={}, attempts={}, hints=[], lab=False, lab_attempts=0,
                exam=None, history=[], best=None, wrong=[], draft=None)


@contextmanager
def progress(r, demo, module_id=1):
    module(module_id)
    with DB() as d:
        if demo:
            key=r.session.get('course_demo')
            row=d.scalar(select(DemoProgress).where(DemoProgress.id==key).with_for_update()) if key else None
            if row is None:
                d.execute(delete(DemoProgress).where(DemoProgress.updated<int(time.time())-14*86400))
                key=secrets.token_urlsafe(24)
                row=DemoProgress(id=key,payload=json.dumps({'1':r.session.pop('learn_demo',{})}),updated=int(time.time()))
                d.add(row);r.session['course_demo']=key
            states=json.loads(row.payload)
            state=initial()|states.get(str(module_id),{})
            yield state
            states[str(module_id)]=state
            row.payload=json.dumps(states,ensure_ascii=False);row.updated=int(time.time())
        else:
            u = user(r, d)
            states=account_states(d,u.id)
            if u.role!='admin' and any(not passed(states.get(i,{})) for i in range(1,module_id)):
                raise HTTPException(403,'Сначала пройдите предыдущие модули: практика и итоговый тест от 70/100')
            model=LearningProgress if module_id==1 else CourseProgress
            values=dict(user_id=u.id,payload='{}')
            if module_id!=1: values['module_id']=module_id
            insert = pg_insert if d.bind.dialect.name == 'postgresql' else sqlite_insert
            d.execute(insert(model).values(**values).on_conflict_do_nothing())
            query=select(model).where(model.user_id==u.id)
            if module_id!=1: query=query.where(model.module_id==module_id)
            row=d.scalar(query.with_for_update())
            state = initial() | json.loads(row.payload)
            yield state
            row.payload = json.dumps(state, ensure_ascii=False)
        d.commit()


def catalog(r,demo):
    with DB() as d:
        if demo:
            row=d.get(DemoProgress,r.session.get('course_demo',''))
            states={int(k):v for k,v in json.loads(row.payload).items()} if row else {}
            preview=True
        else:
            u=user(r,d);states=account_states(d,u.id);preview=u.role=='admin'
        return [dict(id=i,title=m['title'],goal=m['goal'],theory=m['theory'],practice=m['practice'],passed=passed(states.get(i,{})),available=preview or all(passed(states.get(j,{})) for j in range(1,i))) for i,m in MODULES.items()]


def practical_tasks(r,demo,m):
    with DB() as d:
        uid=None if demo else user(r,d).id
        works={w.lesson_id:w for w in d.scalars(select(Work).where(Work.user_id==uid))} if uid else {}
        lessons={l.number:l for l in d.scalars(select(Lesson).where(Lesson.kind=='practice'))}
        result=[]
        for n in m['practice']:
            lesson=lessons.get(n);w=works.get(lesson.id) if lesson else None
            result.append(dict(number=n,title=SOURCE_P[n],url='/lesson/'+str(lesson.id) if lesson and not demo else '/login',status=w.status if w else 'new',score=w.score if w else None))
        return result


def completed(state, lesson):
    return all(q['id'] in state['solved'] for q in lesson['questions'])


def public_question(q):
    return {k: q[k] for k in ('id', 'kind', 'prompt', 'options')}


def public_state(state, module_id=1):
    LESSONS=module(module_id)["lessons"];EXAM=module(module_id)["exam"]
    done = [l['id'] for l in LESSONS if completed(state, l)]
    unlocked = [l['id'] for i, l in enumerate(LESSONS) if i == 0 or completed(state, LESSONS[i-1])]
    exam = state.get('exam')
    return dict(solved=state['solved'], attempts=state['attempts'], hints=state['hints'],
                completed=done, unlocked=unlocked, lab=state['lab'], lab_attempts=state['lab_attempts'],
                best=state['best'], history=state['history'], wrong=state['wrong'], draft=state['draft'],
                passed=state['lab'] and state['best'] is not None and state['best'] >= 70, weak=state.get('weak',[]),
                active_exam=({'id':exam['id'], 'deadline':exam['deadline'],
                              'questions':[public_question(next(q for q in EXAM if q['id']==id)) for id in exam['ids']]}
                             if exam else None))


def evaluate(q, answer):
    if not isinstance(answer, list) or len(answer)>12 or any(not isinstance(a,str) or len(a)>120 for a in answer):
        raise HTTPException(400, 'Некорректный формат ответа')
    normalized = [s.strip().casefold() for s in answer]
    expected = q['answer']
    return set(normalized)==set(expected) and len(normalized)==len(expected) if q['kind']=='multi' else normalized==expected


def find_question(state, id, module_id=1):
    LESSONS=module(module_id)["lessons"]
    for i, lesson in enumerate(LESSONS):
        for q in lesson['questions']:
            if q['id']==id:
                if i and not completed(state, LESSONS[i-1]):
                    raise HTTPException(403, 'Сначала завершите предыдущий урок')
                return q
    raise HTTPException(404, 'Задание не найдено')


@app.get('/learn/{module_id}', response_class=HTMLResponse)
def learning_page(r:Request, module_id:int):
    with DB() as d: user(r,d)
    return render(r, False, module_id)


@app.get('/learn/{module_id}/demo', response_class=HTMLResponse)
def demo_page(r:Request, module_id:int):
    return render(r, True, module_id)


def render(r, demo, module_id):
    module(module_id)
    template = (P/'static/learn.html').read_text(encoding='utf-8')
    return HTMLResponse(template.replace('{{DEMO}}', 'true' if demo else 'false').replace('{{MODULE}}',str(module_id)))


@app.get('/api/learn/{module_id}')
def learning_data(r:Request, module_id:int, demo:bool=False):
    m=module(module_id)
    with progress(r,demo,module_id) as state:
        lessons=[{k:v for k,v in l.items() if k not in ('questions','exam')} | {'questions':[public_question(q) for q in l['questions']]} for l in m['lessons']]
        result=dict(lessons=lessons,state=public_state(state,module_id),token=r.session['csrf'],
                    module={k:v for k,v in m.items() if k not in ('lessons','exam')},
                    lab=LABS.get(module_id),exam_count=len(m['exam']))
    result['catalog']=catalog(r,demo)
    result['practice']=practical_tasks(r,demo,m)
    return result


@app.post('/api/learn/{module_id}')
async def learning_action(r:Request, module_id:int, demo:bool=False):
    m=module(module_id);LESSONS=m["lessons"];EXAM=m["exam"]
    csrf(r, r.headers.get('X-CSRF-Token',''))
    raw = await r.body()
    if len(raw)>12000: raise HTTPException(413)
    try: data=json.loads(raw)
    except (ValueError, UnicodeDecodeError): raise HTTPException(400, 'Некорректный запрос')
    if not isinstance(data,dict): raise HTTPException(400)
    action = data.get('action')
    with progress(r,demo,module_id) as state:
        feedback={}
        if state['exam'] and action in ('check','hint','lab','simulate','terminal'):
            raise HTTPException(409, 'Завершите активную попытку теста; подсказки во время теста недоступны')
        if action in ('check','hint'):
            question=find_question(state,data.get('id'),module_id)
            id=question['id']
            if action=='hint':
                if id not in state['hints']: state['hints'].append(id)
                if id in state['solved']: state['solved'][id]=95
                feedback={'hint':question['hint']}
            else:
                correct=evaluate(question,data.get('answer'))
                state['attempts'][id]=min(state['attempts'].get(id,0)+1,999)
                if correct:
                    state['solved'][id]=95 if id in state['hints'] else 100
                    state['wrong']=[x for x in state['wrong'] if x!=id]
                elif id not in state['wrong']: state['wrong'].append(id)
                feedback=dict(correct=correct, explanation=question['explanation'])
        elif action in ('simulate','terminal') or (action=='lab' and module_id!=1):
            if module_id not in LABS: raise HTTPException(400,'В этом модуле используется конструктор')
            if action=='lab' and not all(completed(state,l) for l in LESSONS):
                raise HTTPException(403,'Завершите все уроки модуля')
            try:
                if action=='terminal':
                    if module_id!=10: raise ValueError('Терминал доступен в модуле диагностики')
                    feedback=terminal(data.get('config',{}),data.get('command'))
                else: feedback=simulate(module_id,data.get('config',{}))
            except ValueError as error: raise HTTPException(400,str(error))
            if action=='lab':
                state['lab_attempts']+=1;state['draft']=feedback['config']
                if feedback['correct']: state['lab']=True
        elif action=='lab':
            if not all(completed(state,l) for l in LESSONS): raise HTTPException(403, 'Завершите все уроки модуля')
            state['lab_attempts']+=1
            devices=data.get('devices',{})
            edges=data.get('edges',[])
            if not isinstance(devices,dict) or not isinstance(edges,list) or len(edges)>10 or any(not isinstance(x,str) for x in edges): raise HTTPException(400)
            if any(k not in 'abcde' or len(k)!=1 or v not in ('client','switch','router','server') for k,v in devices.items()): raise HTTPException(400)
            if any(x not in {a+'-'+b for a in 'abcde' for b in 'abcde' if a<b} for x in edges): raise HTTPException(400)
            state['draft']=dict(devices=devices,edges=edges)
            expected={'a':'client','b':'switch','c':'router','d':'switch','e':'server'}
            errors=[]
            for slot, role in expected.items():
                if devices.get(slot)!=role:
                    label={'a':'рабочее место','b':'локальная сеть офиса','c':'граница двух IP-сетей','d':'локальная сеть серверов','e':'служба приложения'}[slot]
                    errors.append('Проверьте роль устройства: '+label+'.')
            if set(edges)!={'a-b','b-c','c-d','d-e'} or len(edges)!=4:
                errors.append('Нужен непрерывный путь: рабочее место → сеть офиса → граница сетей → сеть серверов → служба. Лишние связи удалите.')
            correct=not errors
            if correct: state['lab']=True
            feedback=dict(correct=correct, explanation='Путь собран. В учебной модели интерфейсы, адреса и маршруты уже настроены. Запрос и ответ проходят через оба сегмента.' if correct else ' '.join(errors))
        elif action=='start_exam':
            if not state['lab']: raise HTTPException(403, 'Сначала выполните практику')
            if not state['exam']:
                ids=[q['id'] for q in EXAM]; secrets.SystemRandom().shuffle(ids)
                state['exam']=dict(id=secrets.token_hex(8),deadline=int(time.time())+m["exam_seconds"],ids=ids)
        elif action=='finish_exam':
            exam=state.get('exam')
            if not exam or data.get('id')!=exam['id']: raise HTTPException(409, 'Эта попытка уже завершена или не найдена')
            answers=data.get('answers',{})
            if not isinstance(answers,dict): raise HTTPException(400)
            expired=time.time()>exam['deadline']
            review=[]
            for id in exam['ids']:
                q=next(q for q in EXAM if q['id']==id)
                correct=evaluate(q,answers.get(id,[])) and not expired
                review.append(dict(id=id,source=q['source'],correct=correct,prompt=q['prompt'],explanation=q['explanation']))
            score=round(100*sum(q['correct'] for q in review)/len(review))
            state['best']=max(state['best'] or 0,score)
            state['history']=(state['history']+[dict(score=score,at=int(time.time()),expired=expired)])[-5:]
            state['exam']=None
            # Small source-id list supports revision after reload without large cookies.
            state['weak']=[q['source'] for q in review if not q['correct']]
            feedback=dict(score=score, expired=expired, review=review)
        elif action=='reset_demo' and demo:
            state.clear();state.update(initial())
        else: raise HTTPException(400, 'Неизвестное действие')
        return dict(state=public_state(state,module_id), **feedback)


def teacher_summary(d, uid):
    states=account_states(d,uid);rows=[]
    for i,m in MODULES.items():
        state=initial()|states.get(i,{})
        done=sum(completed(state,l) for l in m['lessons'])
        best=str(state['best'])+'/100' if state['best'] is not None else '—'
        rows.append(f'<tr><td>{i}. {h(m["title"])}</td><td>{done}/{len(m["lessons"])}</td><td>{len(state["solved"])}/{3*len(m["lessons"])}</td><td>{"✓" if state["lab"] else "—"}</td><td>{h(best)}</td></tr>')
    return '<section><h2>Интерактивный курс · 14 модулей</h2><p>Автоматические результаты отделены от оценок преподавателя за отчёты и этапы.</p><div style="overflow:auto"><table><thead><tr><th>Модуль</th><th>Уроки</th><th>Проверки</th><th>Модель</th><th>Тест</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div></section>'
