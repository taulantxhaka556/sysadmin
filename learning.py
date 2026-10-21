"""Module-one learning flow, server grading and isolated signed-cookie demo."""
import copy
import json
import secrets
import time
from contextlib import contextmanager

from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import Column, Integer, Text, ForeignKey, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from main import B, DB, User, app, csrf, user, h, P
from module1_content import LESSONS, EXAM


class LearningProgress(B):
    __tablename__ = 'learning_module_one'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    payload = Column(Text, nullable=False, default='{}')


def initial():
    return dict(solved={}, attempts={}, hints=[], lab=False, lab_attempts=0,
                exam=None, history=[], best=None, wrong=[], draft=None)


@contextmanager
def progress(r, demo):
    if demo:
        state = initial() | copy.deepcopy(r.session.get('learn_demo', {}))
        yield state
        # State is intentionally compact: answers/explanations never enter the cookie.
        r.session['learn_demo'] = state
    else:
        with DB() as d:
            u = user(r, d)
            insert = pg_insert if d.bind.dialect.name == 'postgresql' else sqlite_insert
            d.execute(insert(LearningProgress).values(user_id=u.id, payload='{}').on_conflict_do_nothing())
            row = d.scalar(select(LearningProgress).where(LearningProgress.user_id == u.id).with_for_update())
            state = initial() | json.loads(row.payload)
            yield state
            row.payload = json.dumps(state, ensure_ascii=False)
            d.commit()


def completed(state, lesson):
    return all(q['id'] in state['solved'] for q in lesson['questions'])


def public_question(q):
    return {k: q[k] for k in ('id', 'kind', 'prompt', 'options')}


def public_state(state):
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


def find_question(state, id):
    for i, lesson in enumerate(LESSONS):
        for q in lesson['questions']:
            if q['id']==id:
                if i and not completed(state, LESSONS[i-1]):
                    raise HTTPException(403, 'Сначала завершите предыдущий урок')
                return q
    raise HTTPException(404, 'Задание не найдено')


@app.get('/learn/1', response_class=HTMLResponse)
def learning_page(r:Request):
    with DB() as d: user(r,d)
    return render(r, False)


@app.get('/learn/1/demo', response_class=HTMLResponse)
def demo_page(r:Request):
    return render(r, True)


def render(r, demo):
    template = (P/'static/learn.html').read_text(encoding='utf-8')
    return HTMLResponse(template.replace('{{DEMO}}', 'true' if demo else 'false'))


@app.get('/api/learn/1')
def learning_data(r:Request, demo:bool=False):
    with progress(r,demo) as state:
        lessons = [{k:v for k,v in l.items() if k!='questions'} | {'questions':[public_question(q) for q in l['questions']]} for l in LESSONS]
        return dict(lessons=lessons, state=public_state(state), token=r.session['csrf'])


@app.post('/api/learn/1')
async def learning_action(r:Request, demo:bool=False):
    csrf(r, r.headers.get('X-CSRF-Token',''))
    raw = await r.body()
    if len(raw)>12000: raise HTTPException(413)
    try: data=json.loads(raw)
    except (ValueError, UnicodeDecodeError): raise HTTPException(400, 'Некорректный запрос')
    if not isinstance(data,dict): raise HTTPException(400)
    action = data.get('action')
    with progress(r,demo) as state:
        feedback={}
        if state['exam'] and action in ('check','hint','lab'):
            raise HTTPException(409, 'Завершите активную попытку теста; подсказки во время теста недоступны')
        if action in ('check','hint'):
            question=find_question(state,data.get('id'))
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
        elif action=='lab':
            if not all(completed(state,l) for l in LESSONS): raise HTTPException(403, 'Завершите шесть уроков')
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
                state['exam']=dict(id=secrets.token_hex(8),deadline=int(time.time())+600,ids=ids)
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
        return dict(state=public_state(state), **feedback)


def teacher_summary(d, uid):
    row=d.get(LearningProgress,uid)
    if not row: return '<p>Интерактивный модуль 1: ещё не начат.</p>'
    state=initial()|json.loads(row.payload)
    done=sum(completed(state,l) for l in LESSONS)
    attempts=sum(state['attempts'].values())
    best=str(state['best'])+'/100' if state['best'] is not None else 'не сдан'
    return f'<section><h2>Интерактивный модуль 1</h2><p>Уроки: {done}/6 · Проверки: {len(state["solved"])}/18 · Попыток: {attempts} · Подсказок: {len(state["hints"])}.</p><p>Практика: {"выполнена" if state["lab"] else "не выполнена"} · Лучший итоговый тест: {h(best)}.</p><p>Тренировочный результат учитывается отдельно от выставленных преподавателем оценок.</p></section>'

