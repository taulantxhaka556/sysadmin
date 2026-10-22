from fastapi.testclient import TestClient
from test_platform import main
from course_catalog import MODULES


def test_every_topic_has_a_beginner_explanation_and_defined_terms():
    client=TestClient(main.app)
    sources=[]
    for number,m in MODULES.items():
        response=client.get(f'/api/learn/{number}?demo=true')
        assert response.status_code==200
        lessons=response.json()['lessons']
        assert [l['id'] for l in lessons]==[l['id'] for l in m['lessons']]
        for lesson in lessons:
            sources.append(lesson['source'])
            beginner=lesson['beginner']
            assert len(beginner['intro'])>60
            assert 3<=len(beginner['terms'])<=8
            assert beginner['analogy'] and beginner['boundary']
            for term in beginner['terms']:
                assert all(term.get(key) for key in ('term','definition','example'))
            assert all('answer' not in q for q in lesson['questions'])
    assert sorted(sources)==list(range(1,61))


def test_foundations_assets_available_without_changing_assessment_progress():
    client=TestClient(main.app)
    before=client.get('/api/learn/1?demo=true').json()['state']
    html=client.get('/learn/1/demo').text
    assert '/static/beginner.js' in html and '/static/beginner.css' in html
    assert client.get('/static/beginner.js').status_code==200
    after=client.get('/api/learn/1?demo=true').json()['state']
    assert before==after
