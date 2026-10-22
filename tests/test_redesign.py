from fastapi.testclient import TestClient
from test_platform import main, teacher
from detailed_materials import MATERIALS
from course_catalog import MODULES
from detailed_materials import material_html
from html import escape


def test_configuration_examples_are_visible_and_escaped():
    for key,material in MATERIALS.items():
        if material['example'].get('code'):
            kind,number=key.split(':')
            assert '<pre><code>'+escape(material['example']['code'])+'</code></pre>' in material_html(kind,int(number))


def test_all_existing_lessons_have_detailed_material_without_overwriting_teacher_text():
    c=teacher()
    with main.DB() as d:
        lessons=d.scalars(main.select(main.Lesson)).all()
        assert len(lessons)==100
        original={l.id:l.material for l in lessons}
        ids=[l.id for l in lessons]
    for id in ids:
        response=c.get(f'/lesson/{id}')
        assert response.status_code==200
        assert 'Подробный разбор' in response.text
        assert 'Попробуйте самостоятельно' in response.text
        assert 'Показать разбор решения' in response.text
        assert 'action="/logout"' in response.text
    with main.DB() as d:
        assert {l.id:l.material for l in d.scalars(main.select(main.Lesson))}==original


def test_interactive_modules_keep_ids_and_include_explanations():
    c=TestClient(main.app)
    sources=[]
    for number,module in MODULES.items():
        result=c.get(f'/api/learn/{number}?demo=true')
        assert result.status_code==200
        data=result.json()
        assert [l['id'] for l in data['lessons']]==[l['id'] for l in module['lessons']]
        for lesson in data['lessons']:
            sources.append(lesson['source'])
            assert lesson['detail']==MATERIALS['theory:'+str(lesson['source'])]
            assert lesson['detail']['sections'] and lesson['detail']['exercise']['solution']
            assert len(lesson['questions'])==3
            assert all('answer' not in q for q in lesson['questions'])
        html=c.get(f'/learn/{number}/demo').text
        assert '/static/course-theme.css' in html
    assert sorted(sources)==list(range(1,61))
