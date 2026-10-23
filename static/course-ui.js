'use strict';
function moduleUrl(id){return '/learn/'+id+(demo?'/demo':'');}
function setupCourse(){
  document.title=course.title+' · Network Exam';
  $('.module-home').innerHTML=`<span class="module-number">${String(moduleId).padStart(2,'0')}</span><span>${esc(course.title)}<small>Теория → практика → тест</small></span>`;
  $('.topbar b').textContent=course.title;
  if(moduleId===1&&!$('#basics-nav')){$('.finish-nav').insertAdjacentHTML('beforebegin','<button id="basics-nav" data-view="basics">Начать с азов · 5 тем</button>');}
  $('footer').innerHTML=`Network Exam · Модуль ${moduleId} / 14 <span>Понимание важнее запоминания.</span>`;
  $('#module-picker').innerHTML=catalog.map(m=>`<option value="${m.id}" ${m.id===moduleId?'selected':''} ${m.available?'':'disabled'}>${m.passed?'✓ ':''}${m.id}. ${esc(m.title)}${m.available?'':' · закрыт'}</option>`).join('');
  $('#module-picker').onchange=e=>location.assign(moduleUrl(e.target.value));
}
function courseMap(){
  return `<section class="editorial-course-route"><div class="editorial-route-heading"><h2>Ваш учебный маршрут</h2><small>${catalog.length} модулей · 60 тем · 40 практических работ</small></div><div class="editorial-module-grid">${catalog.map(m=>{
    const available=m.available||(m.id===moduleId+1&&state.passed);
    const current=m.id===moduleId;
    const nextLesson=current?(lessons.find(l=>!state.completed.includes(l.id))||lessons[0]):null;
    const name=`<span class="module-index">${m.passed||(current&&state.passed)?'✓':String(m.id).padStart(2,'0')}</span><h3>${esc(m.title)}</h3>`;
    return `<article class="editorial-module" ${available?'':'aria-disabled="true"'}>${available?`<a class="module-link" href="${moduleUrl(m.id)}">${name}</a>`:`<div class="module-link">${name}</div>`}<p>${esc(m.goal)}</p>${current&&nextLesson?`<p class="current-lesson">Текущий урок<br>${esc(nextLesson.title)}</p><button class="module-open" data-lesson="${esc(nextLesson.id)}" ${state.unlocked.includes(nextLesson.id)?'':'disabled'}>Открыть урок →</button>`:`<span class="module-state">${m.passed?'Пройден':available?'Доступен':'Сначала предыдущие модули'}</span>`}${editorialModuleArt(m.id)}</article>`;
  }).join('')}</div></section>`;
}
function practiceCards(){
  if(!practice.length)return '';
  const names={new:'Не начато',pending:'На проверке',revision:'На доработке',graded:'Проверено',done:'Выполнено'};
  return `<section class="practice-card"><h2>Практические работы для преподавателя</h2><p>После учебной модели выполните исходные задания и отправьте отчёт. Модель не заменяет настройку оборудования или Packet Tracer. Оценки за отчёты сохраняются в журнале.${demo?' Для отправки войдите в аккаунт.':''}</p><div class="course-grid">${practice.map(p=>`<a class="lesson-card" href="${p.url}" target="_blank" rel="noopener"><span class="number">П${String(p.number).padStart(2,'0')}</span><span><strong>${esc(p.title)}</strong><small>${esc(names[p.status]||p.status)}${p.score!==null?' · '+p.score+'/100':''} · Открыть задание ↗</small></span></a>`).join('')}</div></section>`;
}
function renderCourseLab(){
  $('#content').innerHTML=`<div class="eyebrow">МОДУЛЬ ${moduleId} / ПРАКТИКА</div><h1>${esc(model.title)}</h1><p>${esc(model.goal)}</p><div id="course-lab" class="practice-card"></div>${practiceCards()}<div class="lesson-bottom"><button id="back-last" class="secondary">← К последнему уроку</button><button id="to-exam" class="primary" ${state.lab?'':'disabled'}>К итоговому тесту →</button></div>`;
  renderModel($('#course-lab'),true);
  $('#back-last').onclick=()=>navigate(lessons.at(-1).id);$('#to-exam').onclick=()=>navigate('exam');
}
function renderModel(root,graded){
  const values=Object.fromEntries(model.fields.map(f=>[f.id,modelConfig[f.id]??f.value]));
  root.innerHTML=`<p class="hint">${esc(model.goal)}</p><div class="model-path">${model.nodes.map((n,i)=>`<span>${i?'→ ':''}${esc(n)}</span>`).join('')}</div><div class="model-fields">${model.fields.map(f=>{
    if(f.kind==='order')return `<fieldset data-field="${f.id}"><legend>${esc(f.label)}</legend><ol class="order-list">${values[f.id].map(v=>`<li data-value="${v}"><span>${esc(f.options.find(o=>o.value===v).label)}</span><button type="button" data-move="-1" aria-label="Поднять правило">↑</button><button type="button" data-move="1" aria-label="Опустить правило">↓</button></li>`).join('')}</ol></fieldset>`;
    return `<label>${esc(f.label)}${f.options?`<select data-field="${f.id}">${f.options.map(o=>`<option value="${esc(o.value)}" ${o.value===values[f.id]?'selected':''}>${esc(o.label)}</option>`).join('')}</select>`:`<input data-field="${f.id}" value="${esc(values[f.id])}" maxlength="120" autocomplete="off">`}</label>`;
  }).join('')}</div>${model.terminal?'<form class="model-terminal"><label>Учебный терминал<input name="command" aria-label="Команда терминала" value="help" maxlength="120" autocomplete="off"></label><button class="secondary">Выполнить команду</button><pre class="terminal-output" aria-live="polite">Введите help для списка команд.</pre></form>':''}<div class="actions"><button class="primary model-run">${graded?'Проверить и зачесть практику':'Запустить модель →'}</button><button class="secondary model-reset">Сбросить настройки</button></div><div class="model-output" aria-live="polite"><p class="muted">Измените параметры и запустите модель. Вы увидите путь проверки и таблицу состояния.</p></div><p class="hint">Ограниченная учебная модель: реальные команды, устройства и сетевой трафик не запускаются.</p>`;
  const read=()=>Object.fromEntries(model.fields.map(f=>{const el=$(`[data-field="${f.id}"]`,root);return [f.id,f.kind==='order'?$$('li',el).map(x=>x.dataset.value):el.value];}));
  const remember=()=>{modelConfig=read();$('.model-output',root).innerHTML='<p class="muted">Настройки изменены. Запустите проверку заново.</p>';};
  bindOrders(root,remember);$$('input[data-field],select[data-field]',root).forEach(el=>el.onchange=remember);
  $('.model-run',root).onclick=()=>{modelConfig=read();act({action:graded?'lab':'simulate',config:modelConfig},data=>{showModelResult(root,data);if(graded&&$('#to-exam'))$('#to-exam').disabled=!state.lab;});};
  $('.model-reset',root).onclick=()=>{modelConfig={};renderModel(root,graded);};
  if(model.terminal)$('form',root).onsubmit=e=>{e.preventDefault();modelConfig=read();const command=$('[name="command"]',root).value;act({action:'terminal',config:modelConfig,command},data=>{modelConfig=data.config;for(const f of model.fields)$(`[data-field="${f.id}"]`,root).value=data.config[f.id];$('.terminal-output',root).textContent='$ '+command+'\n'+data.output;});};
}
function showModelResult(root,data){
  $('.model-output',root).innerHTML=`<p class="q-feedback ${data.correct?'good':'bad'}">${esc(data.explanation)}</p><div class="actions"><button class="secondary trace-next">Разобрать по шагам →</button><span class="trace-position">Все шаги</span></div><ol class="model-trace">${data.trace.map(t=>`<li class="${t.ok?'ok':'fail'}"><strong>${t.ok?'✓':'↺'} ${esc(t.title)}</strong><p>${esc(t.detail)}</p></li>`).join('')}</ol><div class="model-table"><table><thead><tr>${data.table.headers.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${data.table.rows.map(row=>`<tr>${row.map(c=>`<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  let step=-1;$('.trace-next',root).onclick=()=>{const rows=$$('.model-trace li',root);step=(step+1)%(rows.length+1);rows.forEach((row,i)=>{row.hidden=step<rows.length&&i!==step;});$('.trace-position',root).textContent=step===rows.length?'Все шаги':('Шаг '+(step+1)+' из '+rows.length);};
}

function detailedReading(d){
  if(!d)return '';
  return `<section class="detailed-reading"><div class="eyebrow">ПОНИМАНИЕ В ДЕТАЛЯХ</div><h2>Разберём на практике</h2><div class="detail-columns">${d.sections.map(s=>`<article><h3>${esc(s.title)}</h3><p>${esc(s.text)}</p></article>`).join('')}</div><div class="worked-example"><span class="pill">ПРИМЕР</span><h3>${esc(d.example.title)}</h3><p>${esc(d.example.text)}</p>${d.example.code?`<pre><code>${esc(d.example.code)}</code></pre>`:""}</div><div class="independent-task"><h3>Теперь ваша очередь</h3><p>${esc(d.exercise.task)}</p><details><summary>Свериться с решением</summary><p>${esc(d.exercise.solution)}</p></details></div></section>`;
}
