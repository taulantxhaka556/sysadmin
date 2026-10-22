"""Shared server-rendered shell. All interpolated values are escaped."""
from html import escape as h

ICONS = {
    'home':'<path d="m3 10 9-7 9 7v10H3Z"/><path d="M9 20v-7h6v7"/>',
    'book':'<path d="M12 5c-3-2-7-2-10-1v15c3-1 7-1 10 1 3-2 7-2 10-1V4c-3-1-7-1-10 1Z"/><path d="M12 5v15"/>',
    'lab':'<path d="M8 3h8M10 3v7L4 20h16l-6-10V3M7 15h10"/>',
    'exam':'<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 3h6v4H9zM9 12h6M9 16h4"/>',
    'admin':'<path d="M12 3 3 7v6c0 4 9 8 9 8s9-4 9-8V7Z"/><path d="m8 12 3 3 5-6"/>',
    'arrow':'<path d="M4 12h16m-6-6 6 6-6 6"/>',
    'logout':'<path d="M9 4H4v16h5m5-13 5 5-5 5m-6-5h11"/>',
    'menu':'<path d="M4 6h16M4 12h16M4 18h16"/>',
    'network':'<circle cx="5" cy="5" r="2.5"/><circle cx="19" cy="7" r="2.5"/><circle cx="8" cy="19" r="2.5"/><path d="m7 5 9 2M6 8l2 8m3 2 6-9"/>',
}


def icon(name):
    return '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+ICONS.get(name,ICONS['book'])+'</svg>'


def shell(title, body, path, csrf_token, person=None):
    brand='<a class="brand" href="/">'+icon('network')+'<span>Network<span class="brand-light">Exam</span></span></a>'
    signed=person is not None
    links=[('/dashboard','Продолжить курс','home'),('/assignments','Материалы и отчёты','book'),('/journal','Журнал оценок','book'),('/trainer','Тренажёр IPv4','lab'),('/exam','Пробный экзамен','exam')]
    if signed and person.role=='admin':
        links += [('/admin','Преподавателю','admin'),('/admin/analytics','Аналитика','lab'),('/admin/exams','Проверка экзаменов','exam')]
    def active(url):
        if url=='/assignments': return path.startswith(('/assignments','/modules','/lesson'))
        return path==url or (url=='/exam' and path.startswith('/exam/'))
    nav=''.join(f'<a href="{url}"'+(' aria-current="page"' if active(url) else '')+'>'+icon(i)+h(label)+'</a>' for url,label,i in links)
    if signed:
        sidebar=f'''<aside class="sidebar" id="navigation">{brand}<p class="nav-caption">Компьютерные сети</p><nav aria-label="Главная навигация">{nav}</nav>
        <div class="sidebar-bottom"><div class="course-note"><span class="signal-dot"></span>Учебная лаборатория<p>От первого пакета<br>до корпоративной сети.</p></div>
        <div class="account"><span class="avatar">{h(person.name[:1].upper())}</span><div><strong>{h(person.name)}</strong><small>{'Преподаватель' if person.role=='admin' else 'Студент'}</small></div></div>
        <form class="inline" action="/logout" method="post">{csrf_token}<button class="logout" data-logout>{icon('logout')}Выйти</button></form></div></aside>'''
        frame=f'''{sidebar}<div class="workspace"><header class="topbar"><button class="menu-toggle secondary" aria-expanded="false" aria-controls="navigation" aria-label="Открыть меню">{icon('menu')}</button><span>Network Exam<span class="topbar-description"> / Подготовка к экзамену</span></span><a href="/assignments">Учебный маршрут {icon('arrow')}</a></header><main id="main"><div class="page-heading"><h1>{h(title)}</h1></div>{body}<footer class="footer"><span>Network Exam · Учитесь понимать сети</span><a href="/assignments">К программе курса</a></footer></main></div>'''
    else:
        frame=f'''<header class="public-header">{brand}<nav aria-label="Навигация"><a href="/login">Вход</a><a href="/register">Регистрация</a></nav></header><main id="main" class="auth-layout"><div class="auth-story"><p class="auth-topic">Компьютерные сети и администрирование</p><h2>Понимать сеть.<br>Управлять связью.</h2><p>Пройдите путь от основ передачи данных до настройки и защиты корпоративной сети.</p><div class="auth-facts"><div><strong>14</strong><span>учебных модулей</span></div><div><strong>60</strong><span>теоретических тем</span></div><div><strong>40</strong><span>практических работ</span></div></div><div class="network-map" aria-hidden="true"><span>Клиент</span><i></i><span>Коммутатор</span><i></i><span>Сервер</span></div></div><div class="auth-form"><h1>{h(title)}</h1>{body}</div></main>'''
    return f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#f2f5f5"><title>{h(title)} · Network Exam</title><link rel="stylesheet" href="/static/style.css"><script src="/static/app.js" defer></script></head><body data-user="{person.id if signed else 'guest'}"><a class="skip-link" href="#main">К содержимому</a>{frame}</body></html>'''
