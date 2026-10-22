"""Reviewed supplementary explanations; no writes to existing teacher materials."""
import json
from pathlib import Path
from html import escape as h

MATERIALS=json.loads((Path(__file__).parent/'detailed_materials.json').read_text(encoding='utf-8'))

def material_html(kind,number):
    lesson=MATERIALS.get(f'{kind}:{number}')
    if not lesson:return ''
    body='<section class="detailed-reading"><p class="eyebrow">ПОНЯТЬ → РАЗОБРАТЬ → ПРИМЕНИТЬ</p><h2>Подробный разбор</h2>'
    for section in lesson['sections']:
        body+=f'<h3>{h(section["title"])}</h3><p class="pre">{h(section["text"])}</p>'
    example=lesson['example']; exercise=lesson['exercise']
    body+=f'<div class="feedback"><h3>{h(example["title"])}</h3><p class="pre">{h(example["text"])}</p></div><h3>Попробуйте самостоятельно</h3><p class="pre">{h(exercise["task"])}</p><details><summary>Показать разбор решения</summary><p class="pre">{h(exercise["solution"])}</p></details>'
    if example.get('code'):
        body+='<h3>Команды и конфигурация</h3><pre><code>'+h(example['code'])+'</code></pre>'
    return body+'</section>'
