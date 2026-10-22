'use strict';
const demo = document.body.dataset.demo === 'true';
const moduleId=Number(document.body.dataset.module);
let course={},catalog=[],practice=[],model=null,examCount=0,modelConfig={};
const endpoint = '/api/learn/'+moduleId + (demo ? '?demo=true' : '');
const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const storage = {get(k){try{return localStorage.getItem(k);}catch{return null;}},set(k,v){try{localStorage.setItem(k,v);}catch{}},remove(k){try{localStorage.removeItem(k);}catch{}}};
let lessons=[], state={}, token='', view='home', busy=false, clock=null, animation=null, lastReview=null;
let lab={devices:{},edges:[],selected:'client',wireStart:null,live:false};
const roleNames={client:'Клиент',switch:'Коммутатор',router:'Маршрутизатор',server:'Сервер'};
const roleIcons={client:'▱',switch:'▤',router:'⇄',server:'▥'};
const toast=msg=>{ $('#toast').textContent=msg; setTimeout(()=>{$('#toast').textContent='';},5000); };
const savedTheme=storage.get('network-theme');
if(savedTheme==='dark') document.documentElement.dataset.theme='dark';
$('#theme').onclick=()=>{const theme=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=theme;storage.set('network-theme',theme);};

async function api(payload){
  const response=await fetch(endpoint,payload?{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:JSON.stringify(payload)}:{});
  let data;try{data=await response.json();}catch{throw Error('Сервис временно недоступен. Попробуйте ещё раз.');}
  if(!response.ok) throw Error(typeof data.detail==='string'?data.detail:'Не удалось сохранить ответ. Обновите страницу и войдите снова.');
  if(data.state)state=data.state;
  if(data.token)token=data.token;
  return data;
}
async function act(payload, callback){
  if(busy)return;
  busy=true;
  try{const result=await api(payload);callback?.(result);updateNav();}
  catch(error){toast(error.message);}
  finally{busy=false;}
}
function updateNav(){
  $('#lesson-nav').innerHTML=lessons.map((l,i)=>`<button data-view="${l.id}" class="${view===l.id?'active ':''}${state.completed.includes(l.id)?'done':''}" ${!state.unlocked.includes(l.id)||state.active_exam?'disabled':''}><span class="step-num">${state.completed.includes(l.id)?'✓':i+1}</span><span>${esc(l.title)}</span></button>`).join('');
  const labButton=$('[data-view="lab"]'), examButton=$('[data-view="exam"]');
  labButton.disabled=state.completed.length<lessons.length||!!state.active_exam;examButton.disabled=!state.lab;
  labButton.classList.toggle('active',view==='lab');examButton.classList.toggle('active',view==='exam');
  $('[data-view="home"]').classList.toggle('active',view==='home');
  $('#lab-status').textContent=state.lab?'✓':'';$('#exam-status').textContent=state.passed?'✓':'';
  const steps=state.completed.length+Number(state.lab)+Number(state.passed);
  $('#sidebar-progress').innerHTML=`<span>Пройдено ${steps} из ${lessons.length+2} шагов</span><progress max="${lessons.length+2}" value="${steps}" aria-label="Прогресс модуля"></progress>`;
  $$('[data-view]', $('.sidebar')).forEach(b=>b.onclick=()=>navigate(b.dataset.view));
}
function nextView(){return lessons.find(l=>!state.completed.includes(l.id))?.id||(!state.lab?'lab':'exam');}
function navigate(id, focus=true){
  if(state.active_exam)id='exam';
  if(lessons.some(l=>l.id===id)&&!state.unlocked.includes(id))return;
  if(id==='lab'&&state.completed.length<lessons.length)return;
  if(id==='exam'&&!state.lab)return;
  view=id;clearInterval(clock);clearInterval(animation);clock=null;animation=null;
  if(id==='home')renderHome();else if(id==='lab')renderLab();else if(id==='exam')renderExam();else renderLesson(lessons.find(l=>l.id===id));
  updateNav();
  if(focus){$('#content').focus({preventScroll:true});$('#content').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});}
}
const heroArt=()=>`<div class="hero-art" aria-label="Схема: клиент, коммутатор, сервер"><div class="live-dot">● СВЯЗЬ НАЧИНАЕТСЯ С ЗАПРОСА</div><svg viewBox="0 0 400 150" role="img" aria-label="Путь данных между клиентом и сервером"><path class="signal" d="M65 77H335" stroke="#bce77d" stroke-width="2"/><g fill="#234361" stroke="#5e7d9a"><rect x="18" y="48" width="85" height="60" rx="12"/><rect x="159" y="48" width="85" height="60" rx="12"/><rect x="300" y="48" width="85" height="60" rx="12"/></g><g fill="#eaf1fb" font-size="12" text-anchor="middle"><text x="60" y="83">Клиент</text><text x="201" y="83">Switch</text><text x="342" y="83">Сервер</text></g><g fill="#b7cadd" font-size="10"><text x="25" y="132">Запрос →</text><text x="307" y="132">← Ответ</text></g></svg><small>Не просто читайте о сети. Управляйте ею.</small></div>`;
function renderHome(){
  $('#content').innerHTML=`<div class="eyebrow">МОДУЛЬ ${String(moduleId).padStart(2,'0')} / ИНТЕРАКТИВНЫЙ КУРС</div><div class="hero"><div><h1>${esc(course.title)}</h1><p>${esc(course.goal)}</p><div class="actions"><button class="primary" id="continue">${state.completed.length?'Продолжить обучение':'Начать первый урок'} <span>→</span></button><span class="muted" style="font-size:12px">≈ ${lessons.reduce((n,l)=>n+l.minutes,0)+15} минут с практикой</span></div></div>${heroArt()}</div><div class="stats"><div class="stat"><b>${state.completed.length} / ${lessons.length}</b><span>уроков пройдено</span></div><div class="stat"><b>${Object.keys(state.solved).length} / ${lessons.length*3}</b><span>проверок понимания решено</span></div><div class="stat"><b>${state.best??'—'}<small>${state.best!==null?' / 100':''}</small></b><span>лучший итоговый тест</span></div></div><div class="section-head"><h2>Ваш маршрут</h2><small>Каждый урок открывается после предыдущего</small></div><div class="course-grid">${lessons.map((l,i)=>`<button class="lesson-card" data-lesson="${l.id}" ${state.unlocked.includes(l.id)?'':'disabled'}><span class="number">${state.completed.includes(l.id)?'✓':String(i+1).padStart(2,'0')}</span><span><strong>${esc(l.title)}</strong><small>${l.minutes} мин с интерактивом · схема + 3 задания · Т${String(l.source).padStart(2,'0')}</small></span></button>`).join('')}</div><div class="callout"><b>Проверьте себя в лаборатории.</b><br>Изменяйте настройки, разбирайте результат и сдайте итоговый тест. Порог — 70/100 и выполненная практика.</div>${state.passed?'<div class="result-card pass"><span class="pill">МОДУЛЬ ПРОЙДЕН</span><h2>Основа заложена.</h2><p>Результат сохранён. Выберите следующий модуль в карте курса. Практические отчёты проверяет преподаватель отдельно.</p><button id="repeat-exam" class="secondary">Повторить итоговый тест</button></div>':''}`;
  $('#content').insertAdjacentHTML('beforeend',courseMap());
  const revision=lessons.filter(l=>(state.weak||[]).includes(l.source)||l.questions.some(q=>(state.wrong||[]).includes(q.id)));
  if(revision.length){const box=document.createElement('div');box.className='callout';box.innerHTML='<h3>Повторение ошибок</h3><p>Темы, которым стоит уделить внимание по последним ответам.</p>'+revision.map(l=>`<button class="quiet" data-revise="${l.id}">${esc(l.title)} →</button>`).join('');$('#content').appendChild(box);$$('[data-revise]').forEach(b=>b.onclick=()=>navigate(b.dataset.revise));}
  $('#continue').onclick=()=>navigate(nextView());$$('[data-lesson]').forEach(b=>b.onclick=()=>navigate(b.dataset.lesson));if($('#repeat-exam'))$('#repeat-exam').onclick=()=>navigate('exam');
}
function questionHTML(q,index,exam=false){
  const name=esc(q.id);let options='';
  if(q.kind==='text')options=`<label class="muted" for="answer-${name}">Ваш ответ</label><input id="answer-${name}" type="text" maxlength="120" autocomplete="off" >`;
  else if(q.kind==='order')options=`<p class="hint">Переместите шаги кнопками ↑ и ↓. Верхний шаг выполняется первым.</p><ol class="order-list">${q.options.map((o,i)=>`<li data-value="${i}"><span>${esc(o)}</span><button type="button" data-move="-1" aria-label="Поднять: ${esc(o)}">↑</button><button type="button" data-move="1" aria-label="Опустить: ${esc(o)}">↓</button></li>`).join('')}</ol>`;
  else options=(q.kind==='multi'?'<p class="hint">Выберите все верные варианты.</p>':'')+q.options.map((o,i)=>`<label class="option"><input type="${q.kind==='multi'?'checkbox':'radio'}" name="${name}" value="${i}"><span>${esc(o)}</span></label>`).join('');
  return `<div class="question" data-q="${name}"><fieldset><legend>${index+1}. ${esc(q.prompt)}</legend>${options}</fieldset>${exam?'':`<div class="actions"><button class="primary check">Проверить</button><button class="quiet hint-button">Подсказка · −5 баллов</button><span class="q-status">${state.solved[q.id]!==undefined?'✓ Решено · '+state.solved[q.id]+'/100':''}</span></div><div class="hint-text"></div>`}<div class="q-feedback" aria-live="polite"></div></div>`;
}
function answerOf(q,el){if(q.kind==='order')return $$('.order-list li',el).map(li=>li.dataset.value);if(q.kind==='text')return [$('input',el).value];return $$('input:checked',el).map(x=>x.value);}
function bindOrders(root,changed=()=>{}){
  $$('[data-move]',root).forEach(b=>b.onclick=()=>{const li=b.closest('li'),previous=li.previousElementSibling,next=li.nextElementSibling;if(b.dataset.move==='-1'&&previous)li.parentNode.insertBefore(li,previous);if(b.dataset.move==='1'&&next)li.parentNode.insertBefore(next,li);b.focus();changed();});
}
function renderLesson(l){
  if(!l){navigate('home');return;}
  const index=lessons.indexOf(l);
  $('#content').innerHTML=`<div class="lesson-head"><div class="eyebrow">МОДУЛЬ ${String(moduleId).padStart(2,'0')} / УРОК ${index+1} ИЗ ${lessons.length}</div><h1>${esc(l.title)}</h1><p>${esc(l.lead)}</p><div class="lesson-meta"><span class="pill">ВОПРОС Т${String(l.source).padStart(2,'0')}</span><span class="muted">${l.minutes} мин на урок · 3 проверки</span></div></div><div class="learn-layout"><div class="reading">${l.blocks.map((b,i)=>`<article><span class="chapter">${String(i+1).padStart(2,'0')} / РАЗБЕРЁМСЯ</span><h3>${esc(b[0])}</h3><p>${esc(b[1])}</p></article>`).join('')}</div><div class="visual-card"><span class="eyebrow">ПОПРОБУЙТЕ САМИ</span><h3 id="visual-title"></h3><small>Нажимайте на элементы и наблюдайте изменения.</small><div id="visual"></div></div></div>${detailedReading(l.detail)}<details class="exam-answer"><summary>Как ответить на экзамене · Т${String(l.source).padStart(2,'0')}</summary><p>${esc(l.summary)}</p></details><div class="callout"><b>Частая ошибка</b><br>${esc(l.pitfall)}</div><div class="quiz-card"><div class="quiz-top"><h2>Закрепим сразу</h2><span>3 задания</span></div><p class="muted">Ошибаться здесь полезно. Прочитайте объяснение и попробуйте снова. Для продолжения решите все три задания; подсказка снижает балл задания до 95.</p>${l.questions.map((q,i)=>questionHTML(q,i)).join('')}</div><div class="lesson-bottom"><button class="secondary" id="previous">← ${index?'Предыдущий урок':'Карта модуля'}</button><small id="next-note"></small><button class="primary" id="next">${index===lessons.length-1?'К практике':'Следующий урок'} →</button></div>`;
  renderVisual(l.visual);bindOrders($('#content'));
  l.questions.forEach(q=>{const el=$(`[data-q="${q.id}"]`);
    $('.check',el).onclick=()=>{const answer=answerOf(q,el);if(!answer.length||answer.every(a=>!a.trim())){toast('Сначала дайте ответ.');return;}const button=$('.check',el);button.disabled=true;act({action:'check',id:q.id,answer},data=>{const feedback=$('.q-feedback',el);feedback.className='q-feedback '+(data.correct?'good':'bad');feedback.textContent=(data.correct?'Верно. ':'Попробуйте ещё раз. ')+data.explanation;$('.q-status',el).textContent=state.solved[q.id]!==undefined?'✓ Решено · '+state.solved[q.id]+'/100':'';refreshNext();}).finally(()=>{button.disabled=false;});};
    $('.hint-button',el).onclick=()=>act({action:'hint',id:q.id},data=>{$('.hint-text',el).innerHTML=`<p class="q-feedback">${esc(data.hint)}</p>`;});
  });
  function refreshNext(){const done=state.completed.includes(l.id);$('#next').disabled=!done;$('#next-note').textContent=done?'Все проверки пройдены. Можно продолжать.':'Решите три задания, чтобы открыть следующий шаг.';}
  refreshNext();$('#previous').onclick=()=>navigate(index?lessons[index-1].id:'home');$('#next').onclick=()=>navigate(index===lessons.length-1?'lab':lessons[index+1].id);
}
function renderVisual(type){
  if(type==='course'){ $('#visual-title').textContent=model.title; renderModel($('#visual'),false);return;}
  if(type==='packet'){renderPacket();return;}
  const visuals={
    exchange:{title:'Запрос → обработка → ответ',names:['Клиент','Сервер','Клиент'],icons:['▱','▥','▱'],notes:['1. Браузер отправляет HTTP-запрос. Он просит страницу, а не управляет коммутатором.','2. Веб-сервер обрабатывает запрос. Здесь формируется содержимое ответа.','3. Браузер получает ответ и отображает страницу. Запрос и ответ — разные направления обмена.']},
    devices:{title:'Три роли на одной схеме',names:['Switch','Router','Access point'],icons:['▤','⇄','⌁'],notes:['Коммутатор соединяет локальные узлы и пересылает кадры по MAC-таблице.','Маршрутизатор связывает разные IP-сети и выбирает следующий узел для пакета.','Точка доступа подключает Wi-Fi-клиентов. Она не создаёт Интернет сама по себе.']},
    ports:{title:'Куда подключается кабель?',names:['Ethernet','Wi-Fi','TCP 443'],icons:['▦','⌁','⇥'],notes:['Физический интерфейс: кабель подключает узел к каналу Ethernet. Номер разъёма локален для устройства.','Беспроводной интерфейс: подключение к сети через радио. Отдельный кабель на клиенте не требуется.','Транспортный порт: приложение обращается к службе на узле. В этот «порт» нельзя вставить кабель.']},
    office:{title:'От требования к службе',names:['Документы','Печать','Гостевой Wi-Fi'],icons:['▱','▧','⌁'],notes:['Нужны файловая служба и права: сотрудник должен открыть разрешённый документ, а не просто получить ping-ответ.','Нужны доступный принтер и служба печати. Проверка результата — тестовая страница.','Гостям нужен разрешённый доступ, а не все ресурсы организации. Связность и права проверяют отдельно.']},
    forwarding:{title:'Проследите путь к другой сети',names:['Switch','Router','Сервер'],icons:['▤','⇄','▥'],notes:['В локальном сегменте коммутатор направляет кадр к шлюзу по MAC назначения.','Маршрутизатор выбирает маршрут по IP назначения. Старый кадр разобран, для следующего участка создан новый.','Пакет достигает сервера. Для получения ответа нужен обратный маршрут. IP назначения без NAT — адрес конечного узла.']}
  };
  const v=visuals[type];let step=0;
  $('#visual-title').textContent=v.title;
  const draw=()=>{ $('#visual').innerHTML=`<div class="scene"><div class="flow-row">${v.names.map((n,i)=>`${i?'<span class="arrow" aria-hidden="true">→</span>':''}<button class="node ${step===i?'active':''}" data-node="${i}" aria-pressed="${step===i}"><span class="icon" aria-hidden="true">${v.icons[i]}</span>${n}</button>`).join('')}</div><div class="scene-note" aria-live="polite">${v.notes[step]}</div></div><div class="actions sim-controls"><button class="secondary" id="visual-prev" ${step===0?'disabled':''}>← Назад</button><button class="primary" id="visual-next">${step===2?'Сначала ↺':'Далее →'}</button><span class="sim-step">${step+1} / 3</span></div>`;$$('[data-node]').forEach(b=>b.onclick=()=>{step=Number(b.dataset.node);draw();});$('#visual-prev').onclick=()=>{step--;draw();};$('#visual-next').onclick=()=>{step=(step+1)%3;draw();};};draw();
}
function renderPacket(){
  $('#visual-title').textContent='Откройте страницу и разберите упаковку';let step=0,detailed=false;
  const steps=[['Приложение формирует запрос страницы.','HTTP: GET /',6],['TCP добавляет порты и данные управления потоком.','[ TCP | HTTP ]',3],['IP добавляет адреса отправителя и получателя.','[ IP | TCP | HTTP ]',2],['Ethernet добавляет MAC-адреса и контроль кадра.','[ Ethernet | IP | TCP | HTTP | FCS ]',1],['По физической среде передаются сигналы.','Сигналы в среде →',0],['Получатель обрабатывает кадр и извлекает IP-пакет.','[ IP | TCP | HTTP ]',1],['IP передаёт полезную нагрузку TCP.','[ TCP | HTTP ]',2],['TCP собирает упорядоченные данные для приложения.','HTTP: GET /',3],['Веб-сервер получает запрос. Теперь он может сформировать ответ.','Приложение: запрос получен ✓',6]];
  const layers=['1 · Физический','2 · Канальный','3 · Сетевой','4 · Транспортный','5 · Сеансовый','6 · Представления','7 · Прикладной'];const colors=['#97a4b7','#72a989','#54a8bd','#658bdf','#8e7bce','#af79b7','#d7a05f'];
  const draw=()=>{$('#visual').innerHTML=`<div class="sim-controls"><button class="secondary" id="detail" aria-pressed="${detailed}">${detailed?'Упрощённо':'Подробно: 7 уровней OSI'}</button></div><div class="scene"><div class="stack">${(detailed?[6,5,4,3,2,1,0]:[6,3,2,1,0]).map(i=>`<div class="layer ${steps[step][2]===i?'active':''}" style="--layer:${colors[i]}"><span>${detailed?layers[i]:({6:'Приложение',3:'Транспорт',2:'IP',1:'Канал',0:'Среда'})[i]}</span><span>${steps[step][2]===i?'← сейчас':''}</span></div>`).join('')}</div><div class="pdu">${esc(steps[step][1])}</div></div><div class="scene-note" aria-live="polite">${steps[step][0]}</div><div class="sim-controls"><button class="secondary" id="packet-prev" ${step===0?'disabled':''}>←</button><button class="primary" id="packet-next">${step===8?'Сначала ↺':'Шаг →'}</button><button class="secondary" id="packet-play">${animation?'Пауза':'▶ Авто'}</button><span class="sim-step">${step+1} / 9</span></div><p class="hint" style="margin-top:14px">Учебная модель HTTP поверх TCP/Ethernet. TCP/IP объединяет функции верхних уровней OSI; TLS здесь опущен, чтобы показать инкапсуляцию.</p>`;$('#detail').onclick=()=>{detailed=!detailed;draw();};$('#packet-prev').onclick=()=>{step--;draw();};$('#packet-next').onclick=()=>{step=(step+1)%9;draw();};$('#packet-play').onclick=()=>{if(animation){clearInterval(animation);animation=null;}else animation=setInterval(()=>{step=(step+1)%9;if(step===8){clearInterval(animation);animation=null;}draw();},2200);draw();};};draw();
}
function renderLab(){
  if(moduleId!==1){renderCourseLab();return;}
  $('#content').innerHTML=`<div class="eyebrow">МОДУЛЬ ${String(moduleId).padStart(2,'0')} / ПРАКТИКА</div><h1>Соберите путь запроса.</h1><p class="muted">Рабочее место находится в сети офиса, сервер — в другой IP-сети. Выберите роли устройств и соедините их в непрерывный путь.</p><div class="practice-card"><h2>Офис → серверная</h2><p class="hint">Это модель ролей и соединений. IP-адреса, интерфейсы и маршруты уже настроены. Адресацию и реальные команды будем изучать после основ.</p><div class="lab-guide"><div><strong>01 · Разместите</strong><p>Перетащите устройство в слот или выберите его кнопкой и нажмите слот.</p></div><div><strong>02 · Соедините</strong><p>Выберите «Соединять» и нажмите два слота. Для удаления связи используйте её кнопку.</p></div><div><strong>03 · Проверьте</strong><p>Запустите проверку пути. Объяснение поможет исправить ошибку.</p></div></div><div id="palette" class="lab-palette"></div><div id="board" class="lab-board" aria-label="Конструктор топологии"></div><div id="connections" class="connections" aria-label="Добавленные связи"></div><div class="actions"><button class="primary" id="test-path">Проверить путь запроса →</button><button class="secondary" id="clear-lab">Очистить схему</button></div><div id="lab-feedback" class="q-feedback" aria-live="polite"></div></div><div class="lesson-bottom"><button class="secondary" id="back-to-lesson">← К последнему уроку</button><button class="primary" id="to-exam" ${state.lab?'':'disabled'}>К итоговому тесту →</button></div>`;
  drawLab();$('#back-to-lesson').onclick=()=>navigate(lessons[5].id);$('#to-exam').onclick=()=>navigate('exam');
  $('#clear-lab').onclick=()=>{lab={devices:{},edges:[],selected:'client',wireStart:null,live:false};drawLab();$('#lab-feedback').textContent='';};
  $('#test-path').onclick=()=>{const b=$('#test-path');b.disabled=true;act({action:'lab',devices:lab.devices,edges:lab.edges},data=>{lab.live=data.correct;drawLab();$('#lab-feedback').className='q-feedback '+(data.correct?'good':'bad');$('#lab-feedback').textContent=data.explanation;$('#to-exam').disabled=!state.lab;}).finally(()=>b.disabled=false);};
}
function drawLab(){
  $('#palette').innerHTML=Object.entries(roleNames).map(([role,name])=>`<button draggable="true" data-role="${role}" aria-pressed="${lab.selected===role}" class="${lab.selected===role?'selected':''}">${roleIcons[role]} ${name}</button>`).join('')+`<button data-role="wire" aria-pressed="${lab.selected==='wire'}" class="${lab.selected==='wire'?'selected':''}">⌁ Соединять</button>`;
  const slots=['a','b','c','d','e'], labels=['Рабочее место','Сеть офиса','Граница сетей','Сеть серверов','Служба приложения'];
  $('#board').innerHTML=`<svg viewBox="0 0 1000 215" preserveAspectRatio="none" aria-hidden="true">${lab.edges.map(edge=>{const [a,b]=edge.split('-');return `<line class="wire ${lab.live?'live':''}" x1="${slots.indexOf(a)*200+100}" x2="${slots.indexOf(b)*200+100}" y1="95" y2="95"/>`;}).join('')}</svg>`+slots.map((slot,i)=>`<div class="lab-slot"><button data-slot="${slot}" class="${lab.devices[slot]?'filled':''} ${lab.wireStart===slot?'selected':''}" aria-label="${slot.toUpperCase()}: ${labels[i]}, ${roleNames[lab.devices[slot]]||'пустой слот'}"><span class="device-icon">${roleIcons[lab.devices[slot]]||'+'}</span><span>${roleNames[lab.devices[slot]]||'Поставить'}</span></button><small>${slot.toUpperCase()} · ${labels[i]}</small></div>`).join('');
  $('#connections').innerHTML=lab.edges.length?lab.edges.map(edge=>`<button data-edge="${edge}" aria-label="Удалить связь ${edge}">${edge.toUpperCase().replace('-',' ↔ ')} ×</button>`).join(''):'<small>Связей пока нет. На мобильном они перечисляются здесь.</small>';
  $$('[data-role]').forEach(b=>{b.onclick=()=>{lab.selected=b.dataset.role;lab.wireStart=null;drawLab();};b.ondragstart=e=>{if(b.dataset.role==='wire'){e.preventDefault();return;}e.dataTransfer.setData('text/plain',b.dataset.role);};});
  $$('[data-slot]').forEach(b=>{b.onclick=()=>{const s=b.dataset.slot;lab.live=false;if(lab.selected!=='wire')lab.devices[s]=lab.selected;else if(!lab.wireStart)lab.wireStart=s;else{if(s!==lab.wireStart){const edge=[s,lab.wireStart].sort().join('-');if(!lab.edges.includes(edge))lab.edges.push(edge);}lab.wireStart=null;}drawLab();};b.ondragover=e=>e.preventDefault();b.ondrop=e=>{e.preventDefault();const role=e.dataTransfer.getData('text/plain');if(roleNames[role]){lab.devices[b.dataset.slot]=role;lab.live=false;drawLab();}};});
  $$('[data-edge]').forEach(b=>b.onclick=()=>{lab.edges=lab.edges.filter(x=>x!==b.dataset.edge);lab.live=false;drawLab();});
}
function renderExam(){
  if(state.active_exam){renderActiveExam();return;}
  if(lastReview){renderResults(lastReview);return;}
  $('#content').innerHTML=`<div class="eyebrow">МОДУЛЬ ${String(moduleId).padStart(2,'0')} / ИТОГОВАЯ ПРОВЕРКА</div><h1>Проверьте, что осталось в голове.</h1><div class="exam-card"><h2>${examCount} вопросов · ${Math.round(course.exam_seconds/60)} минут</h2><p>Вопросы охватывают темы модуля. Порядок случайный. Подсказок и проверки отдельных ответов нет — разбор получите после завершения.</p><div class="stats"><div class="stat"><b>${examCount}</b><span>вопросов</span></div><div class="stat"><b>${Math.round(course.exam_seconds/60)} мин</b><span>на попытку</span></div><div class="stat"><b>70%</b><span>порог прохождения</span></div></div><p class="hint">Для прохождения нужны минимум ${Math.ceil(examCount*0.7)} верных ответов из ${examCount}. После истечения времени попытка получает 0; сервер проверяет срок независимо от таймера. Можно повторить тест.</p><button class="primary" id="start-exam">Начать тест →</button></div>${state.history.length?`<div class="section-head"><h2>Последние попытки</h2></div>${state.history.slice().reverse().map(x=>`<p>${new Date(x.at*1000).toLocaleString('ru-RU')} · <b>${x.score}/100</b>${x.expired?' · время истекло':''}</p>`).join('')}`:''}`;
  $('#start-exam').onclick=()=>act({action:'start_exam'},()=>renderActiveExam());
}
function renderActiveExam(){
  const exam=state.active_exam,key='network-exam-'+exam.id;
  $('#content').innerHTML=`<div class="section-head"><div><div class="eyebrow">ИТОГОВЫЙ ТЕСТ / МОДУЛЬ ${String(moduleId).padStart(2,'0')}</div><h1>Ваш ход.</h1></div><div id="timer" class="timer" role="timer" aria-label="Оставшееся время"></div></div><p class="muted">Ответы сохраняются в этом браузере до отправки. Не закрывайте вкладку: время продолжает идти.</p><div class="exam-card">${exam.questions.map((q,i)=>questionHTML(q,i,true)).join('')}<p id="exam-error" role="alert"></p><button class="primary" id="submit-exam">Завершить и увидеть разбор</button></div>`;
  let saved={};try{saved=JSON.parse(storage.get(key)||'{}');}catch{}
  exam.questions.forEach(q=>{const el=$(`[data-q="${q.id}"]`),a=saved[q.id];if(!Array.isArray(a))return;if(q.kind==='order'){const list=$('.order-list',el);a.forEach(v=>{const li=$(`li[data-value="${v}"]`,list);if(li)list.appendChild(li);});}else if(q.kind==='text')$('input',el).value=a[0]||'';else $$('input',el).forEach(input=>input.checked=a.includes(input.value));});
  const answers=()=>Object.fromEntries(exam.questions.map(q=>[q.id,answerOf(q,$(`[data-q="${q.id}"]`))]));
  const save=()=>storage.set(key,JSON.stringify(answers()));bindOrders($('#content'),save);$$('input',$('#content')).forEach(x=>x.onchange=save);
  let sending=false;
  const finish=async(expired=false)=>{if(sending)return;const a=answers();if(!expired&&Object.values(a).some(v=>!v.length)){ $('#exam-error').textContent='Ответьте на все вопросы перед отправкой.';return; }sending=true;$('#submit-exam').disabled=true;
    try{const result=await api({action:'finish_exam',id:exam.id,answers:a});clearInterval(clock);clock=null;storage.remove(key);lastReview=result;renderResults(result);updateNav();}
    catch(error){$('#exam-error').textContent=error.message;$('#submit-exam').disabled=false;}
    finally{sending=false;}
  };
  $('#submit-exam').onclick=()=>finish();
  let automaticAttempted=false;
  const tick=()=>{const seconds=Math.max(0,Math.ceil(exam.deadline-Date.now()/1000));if($('#timer'))$('#timer').textContent=`${String(Math.floor(seconds/60)).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}`;if(!seconds&&!automaticAttempted){automaticAttempted=true;finish(true);}};
  clearInterval(clock);clock=setInterval(tick,1000);tick();updateNav();
}
function renderResults(result){
  const passed=result.score>=70;
  $('#content').innerHTML=`<div class="eyebrow">МОДУЛЬ ${String(moduleId).padStart(2,'0')} / РЕЗУЛЬТАТ</div><div class="result-card ${passed?'pass':''}"><span class="pill">${passed?'МОДУЛЬ ПРОЙДЕН':'ЕЩЁ ОДНА ПОПЫТКА — ЕЩЁ БОЛЬШЕ ПОНИМАНИЯ'}</span><div class="result-score">${result.score}<small> / 100</small></div><h2>${passed?'Вы справились с темами модуля.':'Разберём ошибки и закрепим.'}</h2><p class="muted">${result.expired?'Время истекло. Ответы этой попытки не засчитаны.':passed?'Практика выполнена, порог теста достигнут. Результат сохранён.':'Порог — 70/100. Повторите темы ниже и пройдите тест ещё раз.'}</p><div class="actions"><button class="primary" id="result-home">К карте модуля</button><button class="secondary" id="retry-exam">Повторить тест</button></div></div><h2>Разбор по темам</h2><div class="exam-card">${result.review.map(q=>{const l=lessons.find(l=>l.source===q.source);return `<div class="review-row"><span class="pill">${q.correct?'✓ Верно':'↺ Повторить'} · Т${String(q.source).padStart(2,'0')}</span><h3>${esc(q.prompt)}</h3><p>${esc(q.explanation)}</p><button class="quiet" data-review="${l.id}">Вернуться: ${esc(l.title)} →</button></div>`;}).join('')}</div>`;
  $('#result-home').onclick=()=>navigate('home');$('#retry-exam').onclick=()=>{lastReview=null;renderExam();};$$('[data-review]').forEach(b=>b.onclick=()=>navigate(b.dataset.review));
}
async function boot(){
  try{const data=await api();lessons=data.lessons;course=data.module;catalog=data.catalog;practice=data.practice;model=data.lab;examCount=data.exam_count;modelConfig=state.draft||{};setupCourse();if(moduleId===1&&state.draft)lab={...lab,devices:state.draft.devices,edges:state.draft.edges,live:state.lab};
    $('#mode-banner').innerHTML=demo?'<span><b>Деморежим.</b> Все 14 модулей доступны для просмотра. Внутри модуля уроки последовательны. Демо не попадает в журнал и удаляется после 14 дней бездействия.</span><button id="reset-demo">Начать заново</button><a href="/login">Войти и сохранять прогресс →</a>':'<span>Учебный режим · Прогресс сохраняется в аккаунте и доступен преподавателю.</span><a href="/assignments">Отчёты для преподавателя →</a>';
    if(demo)$('#reset-demo').onclick=()=>{if(confirm('Сбросить только прогресс этой демонстрации?'))act({action:'reset_demo'},()=>{lastReview=null;modelConfig={};lab={devices:{},edges:[],selected:'client',wireStart:null,live:false};navigate('home');});};
    navigate(state.active_exam?'exam':'home',false);
  }catch(error){$('#content').innerHTML=`<div class="error-box"><h2>Не удалось открыть модуль</h2><p>${esc(error.message)}</p><div class="actions"><button class="primary" id="retry-load">Повторить загрузку</button><a href="/login">Войти</a><a href="/learn/1/demo">Открыть демонстрацию</a></div></div>`;$('#retry-load').onclick=boot;}
}
boot();
