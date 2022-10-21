#! /home/www/telergram/gram/bin/python
# from pydantic.dataclasses import dataclass
import json
import time
from collections import deque
from io import StringIO
from typing import Optional

import requests
import telebot
from PIL import Image
from keyboa import keyboa_maker
from pydantic import BaseModel
from telebot import types

from smsc_api import *

list_mes_id = deque()
bot = telebot.TeleBot('1592543804:AAEUjCrnijrDmGSU0cFvIFKDYNbcfyP9JGM')
# bot = telebot.TeleBot('5261851830:AAF9v6oBcTddOORqAtMFMFKbVJaOy0JUU0Y')
now = datetime.now()
admin = None
executor = None
executor_list = None
claimlist = []
claimarchivelist = []
headers = {'Authorization': 'Token 	aa8951ceeeb9426593f593c1fba996935bc83d38'}  # prod
# headers = {'Authorization': 'Token a12995c2388c585b3cad611bf74440c1558d84aa'} #dev
BASE_PATH = 'https://backend.upravhouse.ru'  # prod
# BASE_PATH = 'http://127.0.0.1:8700' #dev
CHAT_ID = None
mes_id = {}

actions_with_id = [
    {"Принять заявку": "101"},
    {"list": "102"},
    {"Завершить заявку": "103"},
    {"Написать диспетчеру": "104"}
]

main_keyboard = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True, one_time_keyboard=False)
claim_list_button = types.KeyboardButton(text="Открытые заявки исполнителя")
claim_list_button_archive = types.KeyboardButton(text="Последние закрытые заявки исполнителя")
main_keyboard.add(claim_list_button, claim_list_button_archive)

admin_main_keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=False)
open_claim_list_button = types.KeyboardButton(text="Открытые заявки")
in_work_claim_list_button = types.KeyboardButton(text="Заявки на исполнении")
claim_list_button_archive = types.KeyboardButton(text="Последние закрытые заявки")
claim_list_button_executor = types.KeyboardButton(text="Список всех сотрудников")
send_message_all_executor = types.KeyboardButton(text="Написать всем сотрудникам")
admin_main_keyboard.add(open_claim_list_button, in_work_claim_list_button, claim_list_button_archive,
                        claim_list_button_executor,
                        send_message_all_executor)


def claim_detail_keyboard(claimid, status=None):
    detail_keyboard = types.InlineKeyboardMarkup()
    # claim_detail_button = types.InlineKeyboardButton(text="Вернуться к списку", callback_data=f"return_to_list")
    send_comment_button = types.InlineKeyboardButton(text="Комментарий", callback_data=f"send_comment#{claimid}")
    if status == 'Поступила':
        callback_button = types.InlineKeyboardButton(text="В работу", callback_data=f"take_to_work#{claimid}")
        detail_keyboard.add(callback_button, send_comment_button)
    elif status == 'В работе':
        callback_button = types.InlineKeyboardButton(text="Завершить", callback_data=f"claim_close#{claimid}")
        detail_keyboard.add(callback_button, send_comment_button)
    else:
        detail_keyboard.add(send_comment_button)
    return detail_keyboard


def send_image_keyboard(claimid):
    detail_keyboard = types.InlineKeyboardMarkup()
    # claim_detail_button = types.InlineKeyboardButton(text="Вернуться к списку", callback_data=f"return_to_list")
    send_comment_button = types.InlineKeyboardButton(text="Комментарий", callback_data=f"send_comment#{claimid}")
    send_image_button = types.InlineKeyboardButton(text="Фотоотчет", callback_data=f"send_image#{claimid}")
    detail_keyboard.add(send_comment_button, send_image_button)
    return detail_keyboard


class Admin(BaseModel):
    id: int
    name: str = None
    username: str = None
    email: str = None
    phone: int = None


class Executor(BaseModel):
    id: int
    get_requisites: str = None
    specialization: str = None
    phone: int = None
    chat_id: str = None


class AdminList(BaseModel):
    each_admin: list[Admin]


class ExecutorList(BaseModel):
    each_executor: list[Executor]


class User(BaseModel):
    users_id: int
    name: str = 'Anonim'
    try_authorization: int = 0
    phone: int = None


class Claim(BaseModel):
    id: int
    internal_id: int
    company: str
    applicant: str
    created: datetime
    status: str
    text: str = None
    emergency: bool
    planned_date: Optional[datetime] = 'Не запланировано'


class ClaimList(BaseModel):
    each_claim: list[Claim]

    def __len__(self):
        return len(self.each_claim)


# @dataclass
# class ClaimArchiveList:
#     claim_id: int
#     company: str
#     applicant: str
#     created: str
#     status: str
#     text: str = None


kb_actions = keyboa_maker(items=actions_with_id)
users_id = set()


def resize_img(path_img):
    img = Image.open(path_img)
    width, height = img.size
    width = int(width)
    height = int(height)
    resize = img.resize((width, height), Image.ANTIALIAS)
    resize.save(path_img)


def formatting_phone(datetime):
    datetime = datetime.split(' ')
    date = datetime[0]
    time = datetime[1]
    date = date.split('-')
    year = date[0]
    month = date[1]
    number = date[2]
    datetime = ''.join(f'{number}-{month}-{year} {time}')
    return datetime


def del_list_mes_id(chat_id):
    index_to_remove = []
    for i in list_mes_id:
        try:
            bot.delete_message(chat_id, i)
        except:
            print(f"Can't delete {i}")
            index_to_remove.append(i)
    for i in index_to_remove:
        list_mes_id.remove(i)


def get_user_and_now():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    user_now = now + ' ' + executor.name
    return user_now


def set_in_admin_chat_id(id, chat_id):
    res = requests.patch(f'{BASE_PATH}/api/v1/user/{id}/', {'chat_id': chat_id}, headers=headers)
    print('set_in_admin_chat_id', res.text)


def set_in_executor_chat_id(id, chat_id):
    res = requests.patch(f'{BASE_PATH}/api/v1/company/executor/{id}/',
                         {'chat_id': chat_id}, headers=headers)
    print('res status', res.text)
    print('chat_id', chat_id)
    print('set_in_executor_chat_id', res)


def get_admin_object(chat_id):
    try:
        res = requests.get(f'{BASE_PATH}/api/v1/user/?chat_id={chat_id}', headers=headers)
        res_json = json.loads(res.text)[0]
        admin_object = Admin(id=res_json['id'], name=res_json['get_full_name'], username=res_json['username'],
                             phone=res_json['phone'], email=res_json['email'])
        return admin_object
    except:
        return None


def get_admin_list(chat_id):
    r = requests.get(f'{BASE_PATH}/api/v1/user/', headers=headers)
    admin_list = AdminList(each_admin=json.load(StringIO(r.text)))
    for i in admin_list.each_admin:
        global admin
        if i.phone != None:
            if int(i.phone) == int(User.phone):
                admin = Admin(id=i.id, name=i.name, username=i.username,
                              phone=i.phone, email=i.email)
                return admin


def get_executor_list(chat_id):
    r = requests.get(f'{BASE_PATH}/api/v1/company/executor/', headers=headers)
    executor_list = ExecutorList(each_executor=json.load(StringIO(r.text)))
    for i in executor_list.each_executor:
        global executor
        if i.phone != None:
            if int(i.phone) == int(User.phone):
                # print('i', i)
                # executor_id = i.get('id')
                # name = i.get('get_requisites')
                # profession = i.get('specialization')
                # phone = i.get('phone')
                # url = i.get('url')
                # print(executor_id, name, profession, phone, url)
                executor = Executor(id=i.id, get_requisites=i.get_requisites, specialization=i.specialization
                                    , phone=i.phone)
                set_in_executor_chat_id(executor.id, chat_id)
                # Executor.name = i.get_requisites
                # Executor.profession = i.specialization
                print(f'executors = {i}')
                return executor
    # except:
    #     print('error executor list')


def set_status_claim_in_work(claimid):
    body = {"status": 2}
    try:
        r = requests.patch(f'{BASE_PATH}/api/v1/claim/{claimid}/', json=body, headers=headers)
        print(r.text)
    except Exception as e:
        print(e)


def set_status_claim_close(claimid):
    body = {"status": 3}
    try:
        r = requests.patch(f'{BASE_PATH}/api/v1/claim/{claimid}/', json=body, headers=headers)
    except Exception as e:
        print(e)
    print(r.text)


def get_claim_detail_json(claimid):
    try:
        r = requests.get(f'{BASE_PATH}/api/v1/claim/{claimid}/', headers=headers)
    except Exception as e:
        print(e)
    claim = json.loads(r.text)
    return claim


# def set_claim_detail(claimid, comment_text):
#     body = {"close_comment": comment_text}
#     try:
#         r = requests.patch(BASE_PATH + f'/api/v1/claim/{claimid}/', json=body, headers=headers)
#     except Exception as e:
#         print(e)
#     claim = json.loads(r.text)
#     return claim


def get_claim_detail(claimid):
    claim = get_claim_detail_json(claimid)
    number_claim = claim['internal_id']
    created = claim['created'].split('.')[0].replace('T', ' ')
    created = formatting_phone(created)
    print('created', created)

    if claim['emergency']:
        emergency = 'Аварийная'
    else:
        emergency = 'Обычная'
    applicant = claim['applicant']
    contact_phone = claim['contact_phone']
    text = claim['text']
    if claim['status'] == 1:
        status = 'Поступила'
    elif claim['status'] == 2:
        status = 'В работе'
    elif claim['status'] == 3:
        status = 'Закрыта'
    else:
        status = None
    try:
        planned_date = claim['planned_date'].split('T')[0]
    except:
        planned_date = 'Не установлена'
    try:
        response = requests.get(BASE_PATH + f'/api/v1/claim/claim-log/?claim={claimid}', headers=headers)
        comment = json.loads(response.text)
        print('comment', comment)
        comments = 'Комментарии:\n'
        for i in comment:
            if len(i['message']):
                message = i['message']
                message = message.replace('на:', ':\n')
                message = message.replace(';', '\n')
                changed = i['changed'].split('.')[0].replace('T', ' ')
                changed = formatting_phone(changed)
                executor = i['executor']
                pointer = i['pointer']
                if executor:
                    comments += f'{changed}\n{message} - {executor}\n'
                elif pointer:
                    comments += f'{changed}\n{message} - {pointer}\n'
    except Exception as e:
        print(f'error get comment - {e}')

    claim_detail = f'Заявка №: {number_claim}\nСоздана: {created}\n' \
                   f'Приоритет: {emergency}\nЗаказчик: {applicant}\n' \
                   f'Телефон: +{contact_phone}\nСообщение: {text}\nТекущий статус: {status}\n' \
                   f'Планируемая дата закрытия: {planned_date}\n' + comments
    return claim_detail, status


def get_claim_list_in_json(params):
    d = dict()
    response = requests.get(BASE_PATH + f'/api/v1/claim/', params=params, headers=headers)
    claim_list = ClaimList(each_claim=json.load(StringIO(response.text)))
    claim_list_sort_id = sorted(claim_list.each_claim, key=lambda x: x.id)
    claim_list_sort = []
    emergency_list = []
    for i in claim_list_sort_id:
        if i.emergency:
            emergency_list.append(i)
        else:
            claim_list_sort.append(i)
    emergency_list = sorted(emergency_list, key=lambda x: x.id, reverse=True)
    claim_list_sort += emergency_list
    d['claim_list'] = claim_list_sort_id
    d['claim_list_sort'] = claim_list_sort
    return d


# def get_claim_list_in_json(message, id):
#     # claimlist  = []
#     response = requests.get(BASE_PATH + f'/api/v1/claim/?executor={id}&status=2&status=1', headers=headers)
#     print('response', response.text)
#     claim_list = ClaimList(each_claim=json.load(StringIO(response.text)))
#     print('claim_list!', type(claim_list))
#     # claims = json.loads(r.text)
#     # print('&&&&&&&&', claims)
#     # for i in claims
#     #     claim_id = i.get('id')
#     #     company = i.get('company')
#     #     applicant = i.get('applicant')
#     #     status = i.get('status')
#     #     created = i.get('created')
#     #     claimlist.append(ClaimList(claim_id, company, applicant, created, status))
#     # print(f'claim_id = {claim_id} claims = {claims}')
#     # return claimlist
#     return claim_list


# def get_claim_list_archve_company(message, list_companies):
#     params = {'status': 3}
#     params['company'] = list_companies
#     response = requests.get(BASE_PATH + f'/api/v1/claim/', params=params, headers=headers)
#     claim_archive_list = ClaimList(each_claim=json.load(StringIO(response.text)))
#     return claim_archive_list


# def get_claim_list_archive(message, id):
#     response = requests.get(BASE_PATH + f'/api/v1/claim/?executor={id}&ordering=internal_id&status=3',
#                             headers=headers)
#     claim_archive_list = ClaimList(each_claim=json.load(StringIO(response.text)))
#     # for i in claimarchive:
#     # claim_id = i.get('id')
#     # company = i.get('company')
#     # applicant = i.get('applicant')
#     # status = i.get('status')
#     # created = i.get('created')
#     # claim_archive_data = ClaimList(claim_id, company, applicant, created, status)
#     # print('claim_archive_data', claim_archive_data)
#     # claimarchivelist.append(claim_archive_data)
#     # print( f'claimarchive:: {claimarchivelist}')
#     return claim_archive_list


def view_executor_in_companies(executors, chat_id):
    for i in executors.each_executor:
        executor_list_res = f'ФИО: {i.get_requisites}\nТелефон: {i.phone}\n' \
                            f'Специализация: {i.specialization}'
        if i.chat_id:
            print('i$', i)
            keyboard = types.InlineKeyboardMarkup()
            send_message_button = types.InlineKeyboardButton(text="Написать сообщение сотруднику",
                                                             callback_data=f'send_message_to_executor${i.chat_id}')
            keyboard.add(send_message_button)
            mes_list = bot.send_message(chat_id, executor_list_res, reply_markup=keyboard, parse_mode="HTML")
            list_mes_id.append(mes_list.message_id)
            mes_id['mes_list_received'] = mes_list
        else:
            keyboard2 = types.InlineKeyboardMarkup()
            send_message_button2 = types.InlineKeyboardButton(text="Как пригласить сотрудника?",
                                                              callback_data='executor_not_registered')
            keyboard2.add(send_message_button2)
            mes_list = bot.send_message(chat_id, executor_list_res)
            mes_list2 = bot.send_message(chat_id, 'Этот сотрудник не зарегистрирован в телеграм-боте',
                                         reply_markup=keyboard2, parse_mode="HTML")
            list_mes_id.append(mes_list.message_id)
            list_mes_id.append(mes_list2.message_id)


def get_claims(claims, chat_id):
    print('get_claims work')
    for i in claims:
        # applicant = i.applicant
        # status = i.status
        # claim_id = i.id
        claim_list_res = f'Идентификатор: {i.id}\nНомер заявки: {i.internal_id}\nКомпания: {i.company}\nАдрес: {i.applicant} \nСтатус: {i.status}  \n '
        keyboard = types.InlineKeyboardMarkup()
        claim_detail_button = types.InlineKeyboardButton(text="Подробнее", callback_data=f"claim_detail#{i.id}")
        send_comment_button = types.InlineKeyboardButton(text="Комментарий", callback_data=f"send_comment#{i.id}")
        if i.status == 'Принята':
            callback_button = types.InlineKeyboardButton(text="В работу", callback_data=f"take_to_work#{i.id}")
            keyboard.add(callback_button, claim_detail_button, send_comment_button)
            mes_list = bot.send_message(chat_id, claim_list_res, reply_markup=keyboard, parse_mode="HTML")
            list_mes_id.append(mes_list.message_id)
            mes_id['mes_list_received'] = mes_list
        elif i.status == 'Закрыта':
            keyboard.add(claim_detail_button)
            mes_list = bot.send_message(chat_id, claim_list_res, reply_markup=keyboard, parse_mode="HTML")
            list_mes_id.append(mes_list.message_id)
            mes_id['mes_list_close'] = mes_list
        else:
            callback_button = types.InlineKeyboardButton(text="Завершить", callback_data=f"claim_close#{i.id}")
            keyboard.add(callback_button, claim_detail_button, send_comment_button)
            mes_list = bot.send_message(chat_id, claim_list_res, reply_markup=keyboard, parse_mode="HTML")
            list_mes_id.append(mes_list.message_id)
            mes_id['mes_list_other'] = mes_list


def send_image_result(claimid, file_path):
    url = f'{BASE_PATH}/api/v1/image/{claimid}/'
    files = [
        ('claim_result_image', (
            'создание дома.png', open(file_path, 'rb'), 'image/png'))
    ]
    # headers = {
    #     'Authorization': 'Token a12995c2388c585b3cad611bf74440c1558d84aa',
    # }
    response = requests.request("PUT", url, headers=headers, files=files)
    print(files)
    print('response', response.text)
    return response


def get_chat_id_json_admin(chat_id, id=None):
    res = requests.get(f'{BASE_PATH}/api/v1/user/{id}/', headers=headers)
    res_json = json.loads(res.text)
    if res_json:
        list_companies = res_json['companies']
        return list_companies


def get_executor_in_companies(list_companies):
    global executor_list
    params = {}
    params['company'] = list_companies
    print(params)
    res = requests.get(f'{BASE_PATH}/api/v1/company/executor/', params=params, headers=headers)
    executor_list = ExecutorList(each_executor=json.load(StringIO(res.text)))
    print('executor_list!', executor_list)
    return executor_list


def get_company_in_admin(admin_id):
    res = requests.get(f'{BASE_PATH}/api/v1/user/{admin_id}/', headers=headers)
    res_json = json.loads(res.text)
    if res_json:
        companies = res_json['companies']
        return companies


def get_chat_id_json_executor(chat_id):
    res = requests.get(f'{BASE_PATH}/api/v1/company/executor/?chat_id={chat_id}', headers=headers)
    res_json = json.loads(res.text)
    print('chat_id', chat_id)
    print('res_ison', res_json)
    executor_class = {}
    if res_json:
        print('get_chat_id_json res_json', res_json)
        executor = res_json[0]
        executor_class = Executor(id=executor['id'], name=executor['get_requisites'],
                                  specialization=executor['specialization'], url=executor['url'],
                                  phone=executor['phone'], chat_id=executor['chat_id'])
    return executor_class


@bot.message_handler(commands=['start'])
def start_message(message):
    global CHAT_ID
    CHAT_ID = message.chat.id
    user_id = message.from_user.id
    print(user_id)
    print('CHAT_ID', CHAT_ID)
    mes_to_line = message.message_id
    mes_id['mes_to_line'] = mes_to_line
    executor_json = get_chat_id_json_executor(CHAT_ID)
    # admin_json = get_chat_id_json_admin(CHAT_ID)

    # if admin_json:
    #     print('Работает если admin_json')

    if executor_json:
        print(executor)
        User.phone = executor_json.phone
        set_in_executor_chat_id(executor_json.id, CHAT_ID)
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=False)
        button_line = types.KeyboardButton(text='Выйти на линию')
        keyboard.add(button_line)
        bot.register_next_step_handler(message, get_menu)
        print(f'user = {User}')
        mes_in_line = bot.send_message(CHAT_ID, text=f"Добрый день, нажмите кнопку выйти на линию!",
                                       reply_markup=keyboard)
        mes_id['mes_in_line'] = mes_in_line.message_id

    else:
        # if user_id not in users_id:
        print('no in user')
        users_id.add(user_id)
        User.users_id = user_id
        print(User)
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=False)
        button_phone = types.KeyboardButton(text="Отправить номер телефона", request_contact=True)
        # button_line = types.KeyboardButton(text='Выйти на линию')
        keyboard.add(button_phone)
        # hint_text = bot.send_message(CHAT_ID, 'Если Вы свернули меню, развернуть его Вы можете кликнув по кнопке в панели ввода текста')
        # hint = bot.send_photo(CHAT_ID, open('/home/sleamey/leverans/telegrambot/images/photo.png', 'rb'))
        mes_send_phone = bot.send_message(CHAT_ID, "Отправьте мне, пожалуйста, свой номер телефона нажав кнопку",
                                          reply_markup=keyboard)
        print(mes_send_phone)
        # mes_id['mes_send_phone'] = mes_send_phone.message_id
        list_mes_id.append(mes_send_phone.message_id)
        print(mes_id)


@bot.message_handler(commands=['list_claim'])
def get_admin_menu(message):
    print('get_admin_menu сработал')
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=False)
    button_phone = types.KeyboardButton(text="Начать работу", request_contact=True)
    # button_line = types.KeyboardButton(text='Выйти на линию')
    keyboard.add(button_phone)


@bot.message_handler(commands=['list_claim'])
def get_menu(message):
    global executor
    # bot.delete_message(message.chat.id, mes_send_phone.message_id)
    mes_out_in_line = message.message_id
    bot.delete_message(message.chat.id, mes_out_in_line)
    admin = get_admin_object(message.chat.id)
    executor = get_executor_list(message.chat.id)
    # print(f'executor = {executor}')
    try:
        if admin:
            you_in_line = bot.send_message(message.chat.id, "Вы авторизовались как администратор",
                                           reply_markup=main_keyboard)
    except Exception as e:
        print('error block admin 447')
    try:
        print(User.phone)
        if executor:
            print('+++', executor)
            if int(User.phone) == int(executor.phone):
                print('сработал try')
                now = str(datetime.now()).split('.')[0]
                you_in_line = bot.send_message(message.chat.id, f"Вы вышли на смену {now}", reply_markup=main_keyboard)
                mes_id['you_in_line'] = you_in_line.message_id
                try:
                    bot.delete_message(message.chat.id, mes_id['mes_in_line'])
                    list_mes_id.remove(mes_id['mes_in_line'])
                except:
                    print(f"get_menu can't delete {mes_id['mes_in_line']}")
                try:
                    bot.delete_message(message.chat.id, mes_id['mes_to_line'])
                except:
                    print(f"get_menu can't delete {mes_id['mes_to_line']}")

            else:
                bot.send_message(message.chat.id,
                                 text='Доступ запрещен, запросите у диспетчера ввод Ваших данных в систему')
    except Exception as e:
        print('get_menu error', e)


@bot.message_handler(content_types=['text'])
def send_text(message):
    chat_id = message.chat.id
    try:
        user_id = message.from_user.id
    except:
        print('error get user')
    if message.text == 'Открытые заявки':
        admin_object = get_admin_object(chat_id)
        print('admin', admin)
        list_companies = get_chat_id_json_admin(message.chat.id, id=admin_object.id)
        params = {'status': 1, 'company': list_companies}
        claims = get_claim_list_in_json(params)
        get_claims(claims['claim_list_sort'], chat_id)

    elif message.text == 'Заявки на исполнении':
        admin_object = get_admin_object(chat_id)
        list_companies = get_chat_id_json_admin(message.chat.id, id=admin_object.id)
        params = {'status': 2, 'company': list_companies}
        claims = get_claim_list_in_json(params)
        get_claims(claims['claim_list_sort'], chat_id)


    elif message.text == 'Список всех сотрудников':
        admin_object = get_admin_object(chat_id)
        companies_in_admin = get_company_in_admin(admin_object.id)
        executor_in_companies = get_executor_in_companies(companies_in_admin)
        view_executor_in_companies(executor_in_companies, chat_id)

    elif message.text == 'Написать всем сотрудникам':
        list_chat_id = []
        executor_in_companies = None
        print('написать всем сотрудникам')

        def send_message_executors(message, list_chat_id=list_chat_id):
            for i in list_chat_id:
                bot.send_message(i, f'Вам поступила рассылка от администратора: {message.text}')

        admin_object = get_admin_object(chat_id)
        companies_in_admin = get_company_in_admin(admin_object.id)
        executor_in_companies = get_executor_in_companies(companies_in_admin)
        print('!', executor_in_companies)
        for i in executor_in_companies.each_executor:
            if i.chat_id:
                list_chat_id.append(i.chat_id)
        create_mesage_to_all_executor = bot.send_message(message.chat.id, f"Напишите сообщение всем сотрудникам",
                                                         parse_mode='HTML')
        bot.register_next_step_handler(create_mesage_to_all_executor, send_message_executors)

    elif message.text == 'Открытые заявки исполнителя':
        executor_json = get_chat_id_json_executor(message.chat.id)
        del_list_mes_id(chat_id)
        params = {'executor': executor_json.id, 'status': 1}
        claims = get_claim_list_in_json(params)
        print('claims', claims)
        get_claims(claims['claim_list_sort'], chat_id)
        try:
            bot.delete_message(chat_id, message.message_id)
            list_mes_id.remove(message.message_id)
            bot.delete_message(chat_id, mes_id['you_in_line'])
            list_mes_id.remove(mes_id['you_in_line'])
        except Exception as e:
            print("can't delete message claim_list", e)
        # del_list_mes_id()
        # get_claims(claim_id, claims)
    elif message.text == 'Последние закрытые заявки исполнителя':
        executor_json = get_chat_id_json_executor(chat_id)
        params = {'executor': executor_json.id, 'status': 3}
        del_list_mes_id(chat_id)
        bot.delete_message(chat_id, message.message_id)
        claims_list = get_claim_list_in_json(params)
        claims = claims_list['claim_list']
        claims_resent = claims[-10:]
        get_claims(claims_resent, chat_id)
    elif message.text == 'Последние закрытые заявки':
        get_admin_object(chat_id)
        admin_object = get_admin_object(chat_id)
        list_companies = get_chat_id_json_admin(message.chat.id, id=admin_object.id)
        params = {'company': list_companies, 'status': 3}
        del_list_mes_id(chat_id)
        bot.delete_message(chat_id, message.message_id)
        claims = get_claim_list_in_json(params)
        print('!!!!!@', claims['claim_list'])
        claims_list = claims['claim_list']
        claims_recent = claims_list[-10:]
        get_claims(claims_recent, chat_id)
    else:
        bot.send_message(chat_id, 'Не понял команду')


@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    chat_id = message.chat.id
    try:
        phone = message.contact.phone_number.replace('+', '')
        User.phone = phone
        admin = get_admin_list(CHAT_ID)
        if admin:
            print('admin', admin)
            set_in_admin_chat_id(admin.id, CHAT_ID)
            # bot.register_next_step_handler(message, get_admin_menu)
            you_in_line = bot.send_message(message.chat.id, "Вы авторизовались как администратор",
                                           reply_markup=admin_main_keyboard)
            print('сработал admin 530')
        else:
            print('no admin')
            executor = get_executor_list(CHAT_ID)
            if executor:
                set_in_executor_chat_id(executor.id, CHAT_ID)
                keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=False)
                button_line = types.KeyboardButton(text='Выйти на линию')
                keyboard.add(button_line)
                bot.register_next_step_handler(message, get_menu)
                print(f'user = {User}')
                mes_in_line = bot.send_message(chat_id, text=f"Добрый день, нажмите кнопку выйти на линию.",
                                               reply_markup=keyboard)
                mes_phone_info = message.message_id
                mes_id['mes_phone_info'] = mes_phone_info
                mes_id['mes_in_line'] = mes_in_line.message_id
            else:
                bot.send_message(chat_id, text='К сожалению,'
                                               ' на Ваш номер телефона не зарегистрирована учетная записть,'
                                               ' обратитесь к администратору или в техническую поддержку.')
        print('user.phone', User.phone)
    except Exception as e:
        print('error contact handler', e)
    try:
        bot.delete_message(chat_id, mes_id['mes_phone_info'])
        list_mes_id.remove(mes_id['mes_phone_info'])
        bot.delete_message(chat_id, mes_id['mes_send_phone'])
        list_mes_id.remove(mes_id['mes_send_phone'])
    except:
        print("can't delete mes_phone or mes_send_phone")


# def create_comment_text(claimid, mes):
#     user_now = get_user_and_now()
#     print('user_now', user_now)
#     claim_detail = get_claim_detail_json(claimid)
#     print('claim_detail', claim_detail)
#     close_comment = claim_detail.get('close_comment')
#     comment_text = '\n'.join([close_comment, '-' * 10, user_now, mes])
#     return comment_text

def send_comment(claim_id, executor=None, pointer=None, message=None):
    if executor:
        data = {'claim': claim_id, 'executor': str(executor), 'message': message}
        print('data', data)
    elif pointer:
        data = {'claim': claim_id, 'pointer': str(pointer), 'message': message}
    url = f'{BASE_PATH}/api/v1/claim/claim-log/'
    print(url)
    try:
        response = requests.get(f'{BASE_PATH}/api/v1/claim/{claim_id}/', headers=headers)
        new_comment = json.loads(response.text)

        count_new_comment = int(new_comment['count_new_comment'] + 1)
        print('count_new_comment', count_new_comment)
    except Exception as e:
        print(f'error get_new_comment - {e}')
    try:
        requests.post(url, json=data, headers=headers)
    except Exception as e:
        print(f'error send_comment - {e}')
    try:
        res = requests.patch(f'{BASE_PATH}/api/v1/claim/{claim_id}/',
                             {'count_new_comment': count_new_comment}, headers=headers)
        print('res', res)
    except Exception as e:
        print(f'error set new comment - {e}')


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    print('call.data', call.data)
    if '#' in call.data:
        claimid = call.data.split('#')[1]
    elif '$' in call.data:
        executor_chat_id = call.data.split('$')[1]
        claimid = None
    else:
        claimid = None
        executor_chat_id = None
    # detail_keyboard = claim_detail_keyboard(claimid)
    if call.data.split('#')[0] == "take_to_work":
        try:
            print(call.message.message_id)
        except Exception as e:
            print('Except:', e)
        # taked_claim = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
        # text="Заявка принята", reply_markup=detail_keyboard)
        # list_mes_id.appendleft(taked_claim.message_id)
        keyboard_detail = claim_detail_keyboard(claimid)
        print('call.message.message_id', call.message.message_id)
        claim_to_work = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                            text="Заявка в работе", reply_markup=keyboard_detail)
        set_status_claim_in_work(claimid)
        # bot.delete_message(CHAT_ID, list_mes_id.popleft())
        # comment_text = create_comment_text(claimid, taked_claim.text)
        # set_claim_detail(claimid, comment_text)
        try:
            [bot.delete_message(call.message.chat.id, i) for i in list_mes_id]
            pass
        except:
            pass

    elif call.data.split('#')[0] == "claim_close":
        key_det_image = send_image_keyboard(claimid)
        print('call.message.message_id', call.message.message_id)
        claim_close = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                            text="Заявка выполнена", reply_markup=key_det_image)
        set_status_claim_close(claimid)
        # comment_text = create_comment_text(claimid, claim_close.text)
        # set_claim_detail(claimid, comment_text)
        list_mes_id.appendleft(claim_close.message_id)
        # bot.delete_message(CHAT_ID, list_mes_id.popleft())

    elif call.data.split('#')[0] == "claim_detail":
        res_claim_detail = get_claim_detail(claimid)
        claim_detail = res_claim_detail[0]
        status = res_claim_detail[1]
        print('claim_detail_status', claim_detail)
        key_det = claim_detail_keyboard(claimid, status=status)
        # callback_button = types.InlineKeyboardButton(text="В работу", callback_data=f"take_to_work#{i.id}")
        mes_claim_detail = bot.send_message(call.message.chat.id, claim_detail, reply_markup=key_det, parse_mode='HTML')
        mes_id['mes_claim_detail'] = mes_claim_detail.message_id
        index_to_remove = []
        for i in list(list_mes_id):
            try:
                bot.delete_message(call.message.chat.id, i)
                index_to_remove.append(i)
            except:
                print(f"can't delete {i}")
        for i in index_to_remove:
            list_mes_id.remove(i)
        list_mes_id.appendleft(mes_claim_detail.message_id)
        print('list_mes_id', list_mes_id)
    elif call.data.split('$')[0] == "send_message_to_executor":
        print('executor_chat_id', executor_chat_id)
        del_list_mes_id(call.message.chat.id)
        if executor_chat_id:
            create_mesage_to_executor = None
            def send_message_to_executor(message, executor_chat_id=executor_chat_id, message_to_executor=create_mesage_to_executor):
                del_list_mes_id(call.message.chat.id)
                executor = None
                bot.send_message(executor_chat_id,
                                 f'Вам поступило сообщение от администратора компании: {message.text}')
                for i in executor_list.each_executor:
                    if i.chat_id == executor_chat_id:
                        executor = i.get_requisites
                bot.send_message(call.message.chat.id, f'Вы написали сообщение сотруднику {executor} - {message.text}')

            create_mesage_to_executor = bot.send_message(call.message.chat.id, f"Напишите сотруднику сообщение",
                                                         parse_mode='HTML')
            list_mes_id.append(create_mesage_to_executor.message_id)
            bot.register_next_step_handler(create_mesage_to_executor, send_message_to_executor)



        else:
            bot.send_message(call.message.chat.id, 'К сожалению, сотрудник ещё не зарегистрирован в телеграм боте\n'
                                                   'Пожалуйста, посмотрите инструкцию или обратитесь к менеджеру')

    elif call.data == 'executor_not_registered':
        text = 'Сотрудник ещё не зарегистрирован в телеграм-боте, ' \
               'ознакомьтесь с инструкцией по регистрации и отправьте её сотруднику.'
        bot.send_message(call.message.chat.id, text)
        document = 'https://backend.upravhouse.ru/media/instruction.pdf'
        bot.send_document(call.message.chat.id, document)


    elif call.data.split('#')[0] == "send_comment":
        claimid = call.data.split('#')[1]
        print('claimid', claimid)

        def set_comment(message, claimid=claimid):
            print('call.data', call.data)
            # comment_text = create_comment_text(claimid, message.text)
            # set_claim_detail(claimid, comment_text)
            executor_class = get_chat_id_json_executor(message.chat.id)
            print('executor_class', executor_class)
            if executor:
                send_comment(claimid, executor=executor_class.id, message=message.text)
                bot.send_message(message.chat.id,
                                 f' Заявка № {claimid} Исполнитель -{executor_class.id} оставил комментарий {message.text}',
                                 parse_mode='HTML')
            else:
                admin_object = get_admin_object(call.message.chat.id)
                send_comment(claimid, pointer=admin_object.id, message=message.text)
                bot.send_message(message.chat.id,
                                 f' Заявка № {claimid} Администратор -{admin_object.name} оставил комментарий {message.text}',
                                 parse_mode='HTML')
            bot.delete_message(message.chat.id, create_comment.message_id)
            bot.delete_message(message.chat.id, message.message_id)
            bot.answer_callback_query(callback_query_id=call.id, show_alert=True,
                                      text="Чтобы свернуть или развернуть кнопки нажмите на значок в панели сообщений")

        create_comment = bot.send_message(call.message.chat.id, f"Напишите комментарий к заявке №{claimid}",
                                          parse_mode='HTML')
        bot.register_next_step_handler(create_comment, set_comment)
        # set_comment(create_comment, claimid)

    elif call.data.split('#')[0] == "send_image":
        print('send_image')

        @bot.message_handler(content_types=['photo'])
        def send_photo(message):
            try:
                # bot.send_photo(CHAT_ID, message.photo, caption=None)
                file_id = message.photo[-1].file_id
                file = bot.get_file(file_id)
                file_path = file.file_path
                downloaded_file = bot.download_file(file_path)
                src = '/home/www/telergram/upravdombot/' + file_path
                print(src)
                with open(src, 'wb') as new_file:
                    new_file.write(downloaded_file)
                resize_img(src)
                send_image_result(claimid, src)
                bot.reply_to(message, 'Фото добавлено')
                # bot.delete_message(CHAT_ID, send_image_text)
                message_result = 'Фото результата работы'
                executor = get_chat_id_json_executor(message.chat.id)
                send_comment(claimid, executor.id, message_result)
            except Exception as e:
                bot.reply_to(message, 'Отправка не удалась')

        send_image_text = bot.send_message(call.message.chat.id, f"Отправьте фотоотчет к заявке №{claimid}")
        bot.register_next_step_handler(send_image_text, send_photo)
    elif call.data == "return_to_list":
        index_to_remove = []
        try:
            for i in list_mes_id:
                try:
                    bot.delete_message(call.message.chat.id, i)
                    index_to_remove.append(i)
                except:
                    print(f"call.data can't delete - {i}")
                    print('calldata', list_mes_id)
            for i in index_to_remove:
                list_mes_id.remove(i)
        except:
            pass
        claims = get_claim_list_archive(call.data)
        get_claims(claims)


bot.polling(none_stop=True)
while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print('error', e)
        time.sleep(15)
