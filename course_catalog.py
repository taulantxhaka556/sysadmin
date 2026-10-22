"""One primary home for every original exam question and practical task."""
import json
from pathlib import Path
from module1_content import LESSONS as FIRST_LESSONS, EXAM as FIRST_EXAM
from course_lessons import TOPICS
from module1_content import q

# Short modules still have a meaningful final check across several decisions.
EXTRA_EXAM={
4:[(9,'vlan-final-2','На trunk разрешена только VLAN20. Почему ПК VLAN10 на разных коммутаторах не обмениваются кадрами?',['VLAN10 отсутствует в allowed list','У них слишком длинный MAC','DNS не создал VLAN'],0,'Trunk должен переносить VLAN10; access-порты обоих ПК также должны принадлежать VLAN10.'),
   (9,'vlan-final-3','STP заблокировал резервный линк в L2-кольце. Как оценить результат?',['Это обязательно отказ кабеля','Это нормальное устранение петли при сохранении резервного пути','Нужно выключить STP на всех портах'],1,'STP строит логическую топологию без петель; резервный путь может стать активным при отказе основного.')],
7:[(57,'pat-final-3','Два TCP-потока идут к одному серверу через один публичный IP. Что помогает вернуть ответы правильным клиентам?',['Таблица трансляций с разными внешними портами','Одинаковый MAC всех клиентов','Только имя домена'],0,'PAT хранит соответствия внутренних и внешних адресов/портов и использует их для обратной трансляции.')],
8:[(41,'wifi-final-3','Клиент поддерживает только WPA2, точка работает только в WPA3-SAE. Что проверить первым?',['Совместимость режима защиты','Размер HTTP-страницы','Номер VLAN на другом континенте'],0,'Чистый WPA3-SAE требует поддержки WPA3. Нужна согласованная безопасная конфигурация или обновление клиента.')],
14:[(42,'restore-final-3','Резервное копирование завершилось без ошибок. Что ещё нужно для доказательства готовности к аварии?',['Проверить восстановление данных и приложения в рамках RPO/RTO','Только удалить старый журнал','Переименовать архив'],0,'Успех задания копирования не доказывает восстановимость. Нужен тест восстановления с проверкой данных, службы и сроков.')]
}

PLAN = [
 ('Как устроена сеть',[1,3,5,6,21,22],[],'Проведите запрос от клиента к серверу и соберите первый путь.'),
 ('Канальный уровень и среда передачи',[17,19,20,23,24],[],'Разберите пересылку кадров и выберите линию связи для двух зданий.'),
 ('IPv4, IPv6 и подсети',[49,50,51],[3,5,13,14,15],'Рассчитайте подсеть, назначьте адреса и проверьте границы диапазона.'),
 ('VLAN и коммутация',[9],[6,7],'Разделите сегменты и восстановите передачу VLAN через trunk.'),
 ('Маршрутизация',[52,54,53,2],[1,2,8,16,17,18,19,20,28],'Выберите маршрут, восстановите OSPF и проверьте обратный путь.'),
 ('DHCP и DNS',[10,55,11,56],[9,10,29,30],'Выдайте правильные параметры клиенту и восстановите разрешение имени.'),
 ('NAT и PAT',[8,57],[11,12],'Проведите два потока через общий внешний адрес и разберите трансляции.'),
 ('Беспроводные сети',[4,41],[4,35],'Подключите клиента к защищённой сети и сравните успешный и неуспешный вход.'),
 ('Серверы и инфраструктура',[14,15,16,18],[],'Распределите ресурсы ВМ, включите службу и подготовьте восстановление.'),
 ('Диагностика и наблюдение',[26,59,29,30],[25,26,27,31,32],'Найдите причину сбоя по командам, пакетам и событиям.'),
 ('Политики и защита сети',[7,25,27,28,34,37,58,38,40],[21,22,33,34,38],'Проверьте матрицу доступов и устраните ошибку порядка правил.'),
 ('TLS, VPN и управление доступом',[35,36,31,32,33,39],[23,24],'Проверьте сторону соединения, параметры туннеля и права удалённого пользователя.'),
 ('Облако, IoT и новые угрозы',[12,13,45,46,47,44,43,48],[37],'Закройте облачное хранилище, разделите сети и сократите права.'),
 ('Восстановление и итоговая сеть',[42,60],[36,39,40],'Восстановите сервис и проверьте всю корпоративную сеть по цепочке.'),
]
SOURCE=json.loads((Path(__file__).parent/'content.json').read_text(encoding='utf-8'))
SOURCE_T={x['number']:x['title'] for x in SOURCE['theory']}
SOURCE_P={x['number']:x['title'] for x in SOURCE['practice']}
MODULES={}
for number,(title,theory,practice,goal) in enumerate(PLAN,1):
    lessons=FIRST_LESSONS if number==1 else [TOPICS[n] for n in theory]
    exam=FIRST_EXAM if number==1 else [TOPICS[n]['exam'] for n in theory]
    for source,id,prompt,options,answer,explanation in EXTRA_EXAM.get(number,[]):
        exam.append(q(id,'choice',prompt,options,[str(answer)],explanation,'')|{'source':source})
    MODULES[number]=dict(id=number,title=title,theory=theory,practice=practice,goal=goal,
                         lessons=lessons,exam=exam,exam_seconds=max(600,len(exam)*100))
assert sorted(n for m in MODULES.values() for n in m['theory'])==list(range(1,61))
assert sorted(n for m in MODULES.values() for n in m['practice'])==list(range(1,41))

# Supplement existing lessons without changing IDs, questions or saved progress.
from detailed_materials import MATERIALS
for m in MODULES.values():
    for lesson in m['lessons']:
        lesson['detail']=MATERIALS['theory:'+str(lesson['source'])]
        lesson['minutes']=max(lesson['minutes'],lesson['detail']['minutes'])
