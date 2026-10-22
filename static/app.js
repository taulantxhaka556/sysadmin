/* Progressive enhancement: navigation, exercises and drafts work locally. */
document.documentElement.classList.add('js');
const menu = document.querySelector('.menu-toggle');
const navigation = document.querySelector('#navigation');
menu?.addEventListener('click', () => {
  const open = menu.getAttribute('aria-expanded') !== 'true';
  menu.setAttribute('aria-expanded', String(open));
  menu.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
  navigation.classList.toggle('is-open', open);
  if (open) navigation.querySelector('a')?.focus();
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && menu?.getAttribute('aria-expanded') === 'true') {
    navigation.classList.remove('is-open'); menu.setAttribute('aria-expanded', 'false');
    menu.setAttribute('aria-label', 'Открыть меню'); menu.focus();
  }
});
document.querySelectorAll('.quiz').forEach(form => {
  form.addEventListener('submit', event => {
    event.preventDefault();
    const choice = form.querySelector('input:checked');
    if (!choice) return;
    const correct = choice.value === form.dataset.answer;
    const feedback = form.querySelector('.quiz-feedback');
    feedback.textContent = correct ? 'Верно. Откройте объяснение, чтобы закрепить ответ.' : 'Пока не совсем. Посмотрите разбор и попробуйте ещё раз.';
    feedback.className = `quiz-feedback ${correct ? 'success' : 'retry'}`;
    form.parentElement.querySelector('.quiz-solution').open = true;
  });
});
const user = document.body.dataset.user;
const prefix = `network-exam:${user}:`;
document.querySelectorAll('[data-draft], form textarea[name^="q_"]:not([readonly])').forEach(field => {
  const key = prefix + location.pathname + ':' + (field.dataset.draft || field.name);
  const message = field.closest('section')?.querySelector('.draft-status');
  try { const saved = sessionStorage.getItem(key); if (saved !== null) field.value = saved; }
  catch { if (message) message.textContent = 'Хранилище браузера недоступно. Скопируйте заметки перед закрытием страницы.'; }
  field.addEventListener('input', () => {
    try { sessionStorage.setItem(key, field.value); if (message) message.textContent = 'Черновик сохранён в этой вкладке. Преподаватель его не видит.'; }
    catch { if (message) message.textContent = 'Не удалось сохранить заметки. Скопируйте их перед закрытием страницы.'; }
  });
});
document.querySelector('[data-logout]')?.closest('form').addEventListener('submit', () => {
  try { Object.keys(sessionStorage).filter(key => key.startsWith(prefix)).forEach(key => sessionStorage.removeItem(key)); } catch { /* Storage may be disabled. */ }
});
const packet = document.querySelector('[data-packet]');
if (packet) {
  let step = 0;
  const nodes = [...document.querySelectorAll('.packet-node')];
  const wires = [...document.querySelectorAll('.packet-wire')];
  const descriptions = [
    'Клиент определяет: адрес сервера находится вне его подсети, поэтому нужен шлюз.',
    'Коммутатор передаёт Ethernet-кадр к порту шлюза, ориентируясь на MAC-адрес назначения.',
    'Маршрутизатор выбирает маршрут к 192.168.20.0/24 и формирует новый кадр для следующего участка.',
    'Сервер получает пакет. Для ответа тоже нужен обратный маршрут к сети клиента.'
  ];
  packet.addEventListener('click', () => {
    step = (step + 1) % nodes.length;
    nodes.forEach((node, index) => node.classList.toggle('is-active', index === step));
    wires.forEach((wire, index) => wire.classList.toggle('passed', index < step));
    document.querySelector('.packet-caption').textContent = descriptions[step];
    packet.textContent = step === nodes.length - 1 ? 'Начать сначала' : 'Следующий узел';
  });
}
if ('IntersectionObserver' in window) {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      document.querySelectorAll('.lesson-outline a[href^="#"]').forEach(link => {
        const current = link.getAttribute('href') === `#${entry.target.id}`;
        link.classList.toggle('is-current', current);
        if (current) link.setAttribute('aria-current', 'location'); else link.removeAttribute('aria-current');
      });
    });
  }, {rootMargin: '-5% 0px -65% 0px'});
  document.querySelectorAll('.lesson-block[id]').forEach(block => observer.observe(block));
}
