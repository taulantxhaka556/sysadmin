'use strict';
function moduleUrl(id){return '/learn/'+id+(demo?'/demo':'');}
function setupCourse(){
  document.title=course.title+' · Network Exam';
  $('.module-home').innerHTML=`<span class="module-number">${String(moduleId).padStart(2,'0')}</span><span>${esc(course.title)}<small>Теория → практика → тест</small></span>`;
  $('.topbar b').textContent=course.title;
  $('footer').innerHTML=`Network Exam · Модуль ${moduleId} / 14 <span>Понимание важнее запоминания.</span>`;
  $('#module-picker').innerHTML=catalog.map(m=>`<option value="${m.id}" ${m.id===moduleId?'selected':''} ${m.available?'':'disabled'}>${m.passed?'✓ ':''}${m.id}. ${esc(m.title)}${m.available?'':' · закрыт'}</option>`).join('');
  $('#module-picker').onchange=e=>location.assign(moduleUrl(e.target.value));
}
function courseMap(){
  return `<div class="section-head"><h2>Весь курс · 14 модулей</h2><small>60 тем и 40 практических работ</small></div><p class="muted">В учебном аккаунте следующий модуль открывается после практической модели и теста от 70/100. Отчёты по исходным практическим работам сдаются отдельно и оцениваются преподавателем в журнале.</p><div class="course-grid">${catalog.map(m=>{const available=m.available||(m.id===moduleId+1&&state.passed);return `<${available?'a':'div'} ${available?'href="'+moduleUrl(m.id)+'"':''} class="lesson-card ${m.id===moduleId?'current-module':''}" ${available?'':'aria-disabled="true"'}><span class="number">${m.passed||(m.id===moduleId&&state.passed)?'✓':String(m.id).padStart(2,'0')}</span><span><strong>${esc(m.title)}</strong><small>${m.theory.length} тем · ${m.practice.length} отчётов${available?'':' · сначала предыдущие модули'}</small></span></${available?'a':'div'}>`;}).join('')}</div>`;
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
