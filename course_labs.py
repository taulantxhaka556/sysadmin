"""Bounded, deterministic teaching models. No commands or traffic leave the server."""
import ipaddress

def F(id,label,value,options=None):
    return dict(id=id,label=label,value=value,options=[dict(value=a,label=b) for a,b in options] if options else None)

YES=[('no','Нет'),('yes','Да')]
LABS={
2:dict(title='Кадр между зданиями',goal='Соедините здания на расстоянии 200 м оптикой, восстановите линк и передайте кадр A → B. В таблице B находится на порту 2.',nodes=['A / порт 1','Коммутатор','B / порт 2'],fields=[F('medium','Линия 200 м','copper',[('copper','Обычный медный Ethernet без промежуточного узла'),('fiber','Совместимая оптика с достаточной дальностью')]),F('link','Линк поднят','no',YES),F('destination','MAC назначения','unknown',[('b','MAC B (известен)'),('unknown','Неизвестный MAC'),('broadcast','FF:FF:FF:FF:FF:FF')])]),
3:dict(title='Лаборатория IPv4',goal='Для 192.168.10.77/26 определите сеть, broadcast и число обычных узлов. В песочнице можно менять IP и префикс; для сдачи верните исходные параметры.',nodes=['IPv4-адрес','AND с маской','Границы блока'],fields=[F('ip','IPv4 узла','192.168.10.77'),F('prefix','Длина префикса','26',[(str(i),'/'+str(i)) for i in range(24,31)]),F('network','Ваш адрес сети','192.168.10.0'),F('broadcast','Ваш broadcast','192.168.10.255'),F('hosts','Ваше число узлов','254')]),
4:dict(title='Два коммутатора — одна VLAN',goal='ПК A и B должны находиться во VLAN 10 на разных коммутаторах; trunk должен переносить VLAN 10 и 20.',nodes=['ПК A / S1','Trunk 802.1Q','S2 / ПК B'],fields=[F('a','VLAN access-порта A','10',[('10','10'),('20','20')]),F('b','VLAN access-порта B','20',[('10','10'),('20','20')]),F('mode','Межкоммутаторный порт','access',[('access','access'),('trunk','trunk')]),F('allowed','Allowed VLAN','20',[('10','10'),('20','20'),('10,20','10,20')])]),
5:dict(title='Восстановите OSPF и путь ответа',goal='R1/R2 должны образовать соседство в area 0, иметь маршрут к 192.168.20.0/24 через 10.0.0.2 и обратный путь. Выберите назначение и наблюдайте longest-prefix match.',nodes=['R1 / LAN10','10.0.0.0/30','R2 / LAN20'],fields=[F('destination','IP назначения','192.168.20.10'),F('area','Area на R2 (R1 = 0)','1',[('0','0'),('1','1')]),F('passive','Канал соседства passive','yes',YES),F('specific','Маршрут 192.168.20.0/24 присутствует','no',YES),F('reverse','Обратный маршрут в LAN10','no',YES)]),
6:dict(title='Клиент получил адрес, но сайт не работает',goal='LAN 192.168.10.0/24: шлюз .1, DNS и HTTP-сервер .2. Статические адреса .1–.20 исключены; выдача должна начинаться с .21. Имя lab.test указывает на .2.',nodes=['DHCP-клиент','DORA / DNS','lab.test'],fields=[F('pool','Первый выдаваемый адрес','192.168.10.1'),F('gateway','Шлюз в DHCP','192.168.10.254'),F('dns','DNS в DHCP','192.168.10.3'),F('record','A-запись lab.test','192.168.10.99')]),
7:dict(title='Два клиента, один внешний IP',goal='Клиенты .10:51000 и .11:51000 обращаются к одному HTTPS-серверу. Настройте PAT через 203.0.113.5 и уникальные внешние порты, проверьте ответный трафик.',nodes=['Два клиента','NAT/PAT','HTTPS-сервер'],fields=[F('mode','Режим','nat',[('nat','NAT 1:1 с одним внешним адресом'),('pat','PAT / overload')]),F('interfaces','Inside/outside назначены верно','no',YES),F('route','Внешний маршрут есть','no',YES),F('port1','Внешний порт потока A','40001'),F('port2','Внешний порт потока B','40001')]),
8:dict(title='Подключите Wi-Fi-клиента',goal='Подключите клиент к LabNet с совместимой WPA2-AES или WPA3-SAE и верными учебными данными. Затем сравните результат с неверным ключом. Реальные пароли здесь не вводятся.',nodes=['Клиент','Точка доступа','LAN'],fields=[F('ssid','SSID клиента','Other',[('Other','Other'),('LabNet','LabNet')]),F('security','Защита точки доступа','wpa3',[('wpa2','WPA2-AES'),('wpa3','WPA3-SAE')]),F('support','Клиент поддерживает','wpa2',[('wpa2','Только WPA2'),('both','WPA2 и WPA3')]),F('key','Учебный ключ клиента','wrong',[('wrong','Неверный'),('correct','Верный')])]),
9:dict(title='Запустите сервис на виртуальной инфраструктуре',goal='На хосте 16 ГБ: 4 ГБ зарезервированы, оставшиеся 12 ГБ доступны двум ВМ без overcommit. Включите HTTP, разрешите его и выберите независимую резервную копию.',nodes=['Физический хост','Две ВМ','Клиент HTTP'],fields=[F('ram1','RAM первой ВМ, ГБ','8'),F('ram2','RAM второй ВМ, ГБ','8'),F('service','HTTP-служба запущена','no',YES),F('firewall','HTTP разрешён','no',YES),F('backup','Восстановление','snapshot',[('snapshot','Только snapshot на том же хранилище'),('independent','Независимая проверенная копия')])]),
10:dict(title='Сайт по IP работает, по имени — нет',goal='Исследуйте лабораторный сбой с помощью терминала: сервер 192.168.10.2, имя lab.test. Выберите подтверждённую причину и исправьте её. Терминал — ограниченная учебная модель, без доступа к реальной сети.',nodes=['Клиент .10','DNS .2','HTTP .2'],terminal=True,fields=[F('diagnosis','Ваш диагноз','link',[('link','Физический обрыв'),('dns','Ошибочная DNS-запись'),('http','Остановлен HTTP')]),F('repair','Исправление','none',[('none','Не выполнено'),('dns','lab.test → 192.168.10.2'),('route','Изменить исправный шлюз')])]),
11:dict(title='Первое совпадение в ACL',goal='Разрешите HTTPS обычному клиенту и SSH администратору, запретите SSH обычному клиенту. Включите журналирование. Меняйте порядок правил и прослеживайте выбранный пакет.',nodes=['Источник','ACL сверху вниз','Сервер'],fields=[dict(id='rules',label='Порядок правил (сверху вниз)',value=['deny','https','admin'],kind='order',options=[dict(value='deny',label='deny ip any any'),dict(value='https',label='permit TCP 443 от клиентов'),dict(value='admin',label='permit TCP 22 от admin')]),F('packet','Проверяемый пакет','user-ssh',[('user-https','Клиент → TCP 443'),('admin-ssh','Admin → TCP 22'),('user-ssh','Клиент → TCP 22')]),F('logging','Журналирование решений','no',YES)]),
12:dict(title='Исправьте защищённое подключение',goal='Клиент открывает lab.test и использует VPN между 192.168.10.0/24 и 192.168.20.0/24. Исправьте проверку стороны, аутентификацию туннеля, selectors и MFA.',nodes=['Удалённый клиент','TLS / VPN','Разрешённая служба'],fields=[F('name','Имя в сертификате','other.test',[('other.test','other.test'),('lab.test','lab.test')]),F('trust','Срок и доверенная цепочка корректны','no',YES),F('auth','Аутентификация IPsec совпадает','no',YES),F('selectors','Защищаемая удалённая сеть','192.168.30.0/24',[('192.168.30.0/24','192.168.30.0/24'),('192.168.20.0/24','192.168.20.0/24')]),F('mfa','Проверки пользователя','two-passwords',[('two-passwords','Пароль + второй пароль'),('key','Пароль + аппаратный ключ')])]),
13:dict(title='Закройте лишний доступ к облаку',goal='Офис 192.168.10.0/24 подключается к облаку. У пользователя должна быть только роль чтения, хранилище закрыто, временная ссылка ограничена, IoT изолирован и аудит включён.',nodes=['LAN / IoT','Контроль доступа','Private storage'],fields=[F('subnet','Облачная сеть','192.168.10.0/24',[('192.168.10.0/24','192.168.10.0/24'),('10.20.0.0/16','10.20.0.0/16')]),F('public','Хранилище публичное','yes',YES),F('role','Роль пользователя','admin',[('admin','Администратор'),('read','Чтение только нужного ресурса')]),F('ttl','Срок ссылки','forever',[('forever','Без ограничения'),('15','15 минут')]),F('iot','IoT изолирован от рабочих станций','no',YES),F('audit','Аудит доступа','no',YES)]),
14:dict(title='Приёмка корпоративной сети',goal='VLAN10/20 — отделы, VLAN30 — серверная 192.168.30.0/24. Исправьте связность, DHCP/DNS, политику, VPN, мониторинг и восстановление. Все проверки должны пройти.',nodes=['VLAN10 / VLAN20','L3 + DHCP/DNS','VLAN30 / VPN'],fields=[F('trunk','Trunk переносит 10,20,30','no',YES),F('routing','Шлюзы .1 и обратные маршруты настроены','no',YES),F('dhcp','Статические адреса исключены из DHCP','no',YES),F('dns','A-запись приложения','192.168.30.99'),F('acl','Политика доступа','any',[('any','Разрешить всё'),('least','HTTPS клиентам, управление только admin')]),F('vpn','VPN и полезный трафик проверены','no',YES),F('monitor','Мониторинг службы включён','no',YES),F('restore','Восстановление выполнено за 120 мин при RTO 120','no',YES)])
}

def normalized(module, values):
    if not isinstance(values,dict): raise ValueError('Настройки должны быть объектом')
    fields=LABS[module]['fields'];result={}
    if set(values)-{f['id'] for f in fields}: raise ValueError('Неизвестный параметр')
    for field in fields:
        value=values.get(field['id'],field['value'])
        if field.get('kind')=='order':
            valid={o['value'] for o in field['options']}
            if not isinstance(value,list) or len(value)!=len(valid) or any(not isinstance(x,str) for x in value) or set(value)!=valid: raise ValueError('Нужны все правила без повторов')
        else:
            if not isinstance(value,str) or len(value)>120: raise ValueError('Слишком длинное или неверное значение')
            value=value.strip()
            if field['options'] and value not in {o['value'] for o in field['options']}: raise ValueError('Недопустимый вариант')
        result[field['id']]=value
    return result

def simulate(module, values):
    v=normalized(module,values);trace=[];rows=[];headers=[]
    def step(title,ok,detail):trace.append(dict(title=title,ok=bool(ok),detail=detail))
    if module==2:
        step('Среда 200 м',v['medium']=='fiber','Для заданной длины выберите совместимую оптику; обычный медный Ethernet здесь выходит за пределы типового канала.')
        step('Физический линк',v['link']=='yes','Без поднятого линка кадр не передаётся.')
        ports='2' if v['destination']=='b' else '2, 3, 4 (та же VLAN)'
        step('Пересылка MAC',v['destination']=='b',f'Источник A изучен на порту 1. Выходные порты для выбранного назначения: {ports}. Для задания нужен известный B.')
        headers=['MAC','Порт'];rows=[['A (изучен)','1'],['B','2']]
    elif module==3:
        try:
            interface=ipaddress.IPv4Interface(v['ip']+'/'+v['prefix']);net=interface.network
        except ValueError: raise ValueError('Введите корректный IPv4-адрес и префикс')
        hosts=net.num_addresses-2
        step('Параметры задания',v['ip']=='192.168.10.77' and v['prefix']=='26','Для сдачи используйте 192.168.10.77/26; остальные значения доступны для исследования.')
        step('Адрес сети',v['network']==str(net.network_address),f'IP AND mask = {net.network_address}.')
        step('Broadcast',v['broadcast']==str(net.broadcast_address),f'Все биты узла = 1 → {net.broadcast_address}.')
        step('Число узлов',v['hosts']==str(hosts),f'2^(32−{net.prefixlen})−2 = {hosts} для обычной подсети.')
        headers=['Параметр','Значение'];rows=[['Маска',str(net.netmask)],['Маска двоично','.'.join(f'{int(o):08b}' for o in str(net.netmask).split('.'))],['Первый узел',str(net.network_address+1)],['Последний узел',str(net.broadcast_address-1)]]
    elif module==4:
        step('Access-порты',v['a']==v['b']=='10',f'A находится во VLAN {v["a"]}, B — во VLAN {v["b"]}. Без L3 разные VLAN изолированы.')
        step('Межкоммутаторный линк',v['mode']=='trunk','Для нескольких VLAN нужен trunk с согласованными параметрами.')
        step('Allowed VLAN',v['allowed']=='10,20',f'Сейчас передаются VLAN {v["allowed"]}; в задании нужны 10 и 20.')
        headers=['Участок','Параметр'];rows=[['A → S1',v['a']],['S1 → S2',v['mode']+' / '+v['allowed']],['S2 → B',v['b']]]
    elif module==5:
        try:destination=ipaddress.IPv4Address(v['destination'])
        except ValueError:raise ValueError('Неверный IP назначения')
        neighbor=v['area']=='0' and v['passive']=='no'
        step('Соседство OSPF',neighbor,'R1 использует area 0. Для R2 нужны area 0 и активный интерфейс соседства. Прочие параметры в модели совпадают.')
        routes=[('0.0.0.0/0','192.0.2.1')]
        if neighbor and v['specific']=='yes':routes.append(('192.168.20.0/24','10.0.0.2'))
        selected=max((r for r in routes if destination in ipaddress.ip_network(r[0])),key=lambda r:ipaddress.ip_network(r[0]).prefixlen)
        step('Поиск маршрута',selected[0]=='192.168.20.0/24',f'Для {destination} выбран {selected[0]} через {selected[1]}. Для лаборатории нужен маршрут к LAN20.')
        step('Обратный путь',v['reverse']=='yes','R2 также должен иметь путь ответа к LAN10.')
        headers=['Префикс','Next hop'];rows=routes
    elif module==6:
        targets={'pool':'192.168.10.21','gateway':'192.168.10.1','dns':'192.168.10.2','record':'192.168.10.2'}
        for key,title in [('pool','DORA: выдача адреса'),('gateway','Параметр шлюза'),('dns','DNS клиента'),('record','Разрешение lab.test')]:
            step(title,v[key]==targets[key],f'Получено {v[key]}. По адресному плану требуется {targets[key]}.')
        headers=['Обмен','Результат'];rows=[['Discover','Поиск сервера'],['Offer',v['pool']],['Request','Выбор предложения'],['ACK','IP/маска/шлюз/DNS'],['DNS A lab.test',v['record']]]
    elif module==7:
        try:ports=[int(v['port1']),int(v['port2'])]
        except ValueError:raise ValueError('Порты должны быть целыми числами')
        step('Режим трансляции',v['mode']=='pat','Для двух потоков через один внешний IP в этой задаче нужен PAT.')
        step('Граница и маршрут',v['interfaces']=='yes' and v['route']=='yes','Правильные inside/outside и внешний маршрут — независимые предпосылки.')
        step('Демультиплексирование ответа',all(1024<=p<=65535 for p in ports) and ports[0]!=ports[1],'В этой модели выбирайте разные внешние порты 1024–65535 для двух потоков к одному серверу.')
        headers=['Inside local','Inside global','Назначение'];rows=[['192.168.10.10:51000','203.0.113.5:'+v['port1'],'198.51.100.10:443'],['192.168.10.11:51000','203.0.113.5:'+v['port2'],'198.51.100.10:443']]
    elif module==8:
        step('Обнаружение сети',v['ssid']=='LabNet','Точка доступа объявляет SSID LabNet.')
        step('Совместимость режима',v['security']=='wpa2' or v['support']=='both','WPA3-SAE требует поддержки WPA3 у клиента; WPA2-клиент не подключится к чистому WPA3.')
        step('Аутентификация',v['key']=='correct','Неверные учебные данные должны приводить к отказу, а не открытой сети.')
        headers=['Проверка','Значение'];rows=[['SSID',v['ssid']],['Режим',v['security']],['IP после успешного подключения','192.168.10.21/24' if all(x['ok'] for x in trace) else 'Не получен']]
    elif module==9:
        try:a,b=int(v['ram1']),int(v['ram2'])
        except ValueError:raise ValueError('RAM должна быть целым числом ГБ')
        step('Ресурсы хоста',1<=a<=12 and 1<=b<=12 and a+b<=12,f'ВМ запрашивают {a+b} ГБ; доступно 12 ГБ без overcommit.')
        step('Прикладной сервис',v['service']=='yes' and v['firewall']=='yes','Нужны работающая HTTP-служба и разрешённое подключение.')
        step('Восстановление',v['backup']=='independent','Snapshot на общем диске не переживёт отказ этого диска; нужна проверенная независимая копия.')
        headers=['Ресурс','ГБ'];rows=[['Всего','16'],['Резерв','4'],['ВМ1',str(a)],['ВМ2',str(b)],['Остаток',str(12-a-b)]]
    elif module==10:
        step('Наблюдения',True,'ping 192.168.10.2 успешен; HTTP слушает. До исправления DNS возвращает 192.168.10.99.')
        step('Диагноз',v['diagnosis']=='dns','Наблюдения подтверждают ошибочную A-запись, а не физический отказ или остановленный HTTP.')
        step('Повторный тест',v['repair']=='dns','После исправления lab.test должен возвращать 192.168.10.2 и открывать работающую службу.')
        headers=['Время','Событие'];rows=[['10:00','link up'],['10:01','HTTP listening :80'],['10:02','DNS A lab.test changed to .99'],['10:03','Пользователь: по имени сайт не открывается']]
    elif module==11:
        def decision(packet):
            for rule in v['rules']:
                if rule=='deny':return False,rule
                if rule=='https' and packet=='user-https':return True,rule
                if rule=='admin' and packet=='admin-ssh':return True,rule
            return False,'implicit deny'
        for packet,expected in [('user-https',True),('admin-ssh',True),('user-ssh',False)]:
            allowed,rule=decision(packet)
            step(packet,allowed==expected,f'Результат: {"permit" if allowed else "deny"}; первое совпадение: {rule}. Ожидается {"permit" if expected else "deny"}.')
        step('Аудит',v['logging']=='yes','Логи помогают подтвердить реальные применения правил.')
        allowed,selected=decision(v['packet']);headers=['Правило','Обработка выбранного пакета'];stopped=False
        for rule in v['rules']:
            rows.append([rule,'Не достигается' if stopped else ('ПЕРВОЕ СОВПАДЕНИЕ → '+('permit' if allowed else 'deny') if rule==selected else 'Нет совпадения')]);stopped=stopped or rule==selected
    elif module==12:
        step('Проверка TLS-стороны',v['name']=='lab.test' and v['trust']=='yes','Нужны ожидаемое имя lab.test, действительный срок и доверенная цепочка.')
        step('IKE/IPsec',v['auth']=='yes' and v['selectors']=='192.168.20.0/24','Должны совпадать аутентификация и защищаемые подсети. Прочие параметры в модели согласованы.')
        step('MFA',v['mfa']=='key','Пароль + аппаратный ключ — разные категории факторов; два пароля — одна категория.')
        headers=['Уровень','Проверка'];rows=[['TLS',v['name']],['VPN remote subnet',v['selectors']],['MFA',v['mfa']]]
    elif module==13:
        step('Адресный план',v['subnet']=='10.20.0.0/16','Облачная сеть не должна пересекаться с офисной 192.168.10.0/24 в этой архитектуре.')
        step('Хранилище и роль',v['public']=='no' and v['role']=='read','Публичность выключена, пользователю достаточно чтения нужного ресурса.')
        step('Срок ссылки',v['ttl']=='15','Временная ссылка ограничена 15 минутами вместо бессрочного доступа.')
        step('IoT и наблюдение',v['iot']=='yes' and v['audit']=='yes','IoT сегментирован, доступ к облачным данным журналируется.')
        headers=['Объект','Политика'];rows=[['Хранилище','Публичное' if v['public']=='yes' else 'Закрытое'],['Роль',v['role']],['Ссылка',v['ttl']],['IoT',v['iot']]]
    elif module==14:
        for key,title in [('trunk','L2 / VLAN'),('routing','L3 / маршруты'),('dhcp','DHCP / исключения')]:step(title,v[key]=='yes','Проверьте соответствующую предпосылку адресного плана и связности.')
        step('DNS / приложение',v['dns']=='192.168.30.2','Сервер находится в VLAN30 по адресу 192.168.30.2.')
        step('Политика',v['acl']=='least','Клиентам нужен HTTPS, управление доступно только admin.')
        for key,title in [('vpn','VPN / полезный трафик'),('monitor','Наблюдение службы'),('restore','Восстановление / RTO')]:step(title,v[key]=='yes','Настройка должна быть подтверждена соответствующим положительным и отрицательным тестом.')
        headers=['Сегмент','Сеть','Шлюз'];rows=[['VLAN10','192.168.10.0/24','192.168.10.1'],['VLAN20','192.168.20.0/24','192.168.20.1'],['VLAN30','192.168.30.0/24','192.168.30.1']]
    correct=all(x['ok'] for x in trace)
    return dict(correct=correct,trace=trace,table=dict(headers=headers,rows=rows),config=v,
                explanation='Все проверки учебной модели пройдены.' if correct else 'Исправьте выделенные шаги и повторите проверку. Красный шаг относится к условию задания, а не обязательно к любой возможной сети.')

def terminal(values,command):
    v=normalized(10,values)
    if not isinstance(command,str) or len(command)>120:raise ValueError('Неверная команда')
    command=' '.join(command.lower().split())
    commands={
      'help':'Команды модели: ipconfig; ping 192.168.10.2; ping lab.test; tracert 192.168.10.2; netstat -an; nslookup lab.test; set dns lab.test 192.168.10.2. Команды не выполняются в реальной ОС.',
      'ipconfig':'IPv4: 192.168.10.10/24\nGateway: 192.168.10.1\nDNS: 192.168.10.2',
      'ping 192.168.10.2':'Reply from 192.168.10.2: time=1 ms\n4 sent, 4 received, 0% loss',
      'tracert 192.168.10.2':'1  192.168.10.2  1 ms\nDestination reached (same LAN)',
      'netstat -an':'Учебный снимок сервера: TCP 0.0.0.0:80 LISTENING',
      'nslookup lab.test':'Server: 192.168.10.2\nName: lab.test\nAddress: '+('192.168.10.2' if v['repair']=='dns' else '192.168.10.99'),
      'ping lab.test':'Reply from 192.168.10.2: time=1 ms' if v['repair']=='dns' else 'Resolved lab.test to 192.168.10.99\nRequest timed out',
    }
    if command=='set dns lab.test 192.168.10.2':
        v['repair']='dns';return dict(output='Учебная A-запись исправлена. Повторите nslookup и ping lab.test.',config=v)
    return dict(output=commands.get(command,'Команда не поддерживается этой моделью. Введите help.'),config=v)
