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
executor = None
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
claim_list_button = types.KeyboardButton(text="Список заявок")
claim_list_button_archive = types.KeyboardButton(text="Архив заявок")
main_keyboard.add(claim_list_button, claim_list_button_archive)


def claim_detail_keyboard(claimid):
    detail_keyboard = types.InlineKeyboardMarkup()
    # claim_detail_button = types.InlineKeyboardButton(text="Вернуться к списку", callback_data=f"return_to_list")
    send_comment_button = types.InlineKeyboardButton(text="Комментарий ✉", callback_data=f"send_comment#{claimid}")
    detail_keyboard.add(send_comment_button)
    return detail_keyboard


def send_image_keyboard(claimid):
    detail_keyboard = types.InlineKeyboardMarkup()
    # claim_detail_button = types.InlineKeyboardButton(text="Вернуться к списку", callback_data=f"return_to_list")
    send_comment_button = types.InlineKeyboardButton(text="Комментарий", callback_data=f"send_comment#{claimid}")
    send_image_button = types.InlineKeyboardButton(text="Фотоотчет", callback_data=f"send_image#{claimid}")
    detail_keyboard.add(send_comment_button, send_image_button)
    return detail_keyboard


class Executor(BaseModel):
    id: int
    name: str = None
    profession: str = None
    phone: int = None
    url: str = None


class ExecutorList(BaseModel):
    each_executor: list[Executor]


class User(BaseModel):
    users_id: int
    name: str = 'Anonim'
    try_authorization: int = 0
    phone: int = None


class Claim(BaseModel):
    id: int
    company: str
    applicant: str
    created: datetime
    status: str
    text: str = None
    planned_date: Optional[datetime] = 'Не запланировано'


class ClaimList(BaseModel):
    each_claim: list[Claim]


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


def del_list_mes_id(chat_id):
    index_to_remove = []
    for i in list_mes_id:
        try:
            bot.delete_message(CHAT_ID, i)
        except:
            print(f"Can't delete {i}")
            index_to_remove.append(i)
    for i in index_to_remove:
        list_mes_id.remove(i)


def get_user_and_now():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    user_now = now + ' ' + executor.name
    return user_now


def set_in_executor_chat_id(id, chat_id):
    res = requests.patch(f'{BASE_PATH}/api/v1/company/executor/{id}/',
                         {'chat_id': chat_id}, headers=headers)
    print('res status', res.text)
    print('chat_id', chat_id)
    print('set_in_executor_chat_id', res)


def get_executor_list(chat_id):
    r = requests.get(f'{BASE_PATH}/api/v1/company/executor/', headers=headers)
    # print(r)

    # try:
    # executor_list = json.loads(r.text)
    executor_list = ExecutorList(each_executor=json.load(StringIO(r.text)))
    print('executor_list', executor_list)
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
                executor = Executor(id=i.id, name=i.name, profession=i.profession, url=i.url, phone=i.phone)
                set_in_executor_chat_id(executor.id, chat_id)
                # Executor.name = i.get_requisites
                # Executor.profession = i.specialization
                print(f'executors = {i}')
                return executor
    # except:
    #     print('error executor list')


def set_status_claim_in_work(claimid):
    body = {"status": 2}
    print('-' * 10)
    print(claimid)
    print(headers)
    print('-' * 10)
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
    number_claim = claim['id']
    created = claim['created'].split('.')[0].replace('T', ' ')
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
        print(type(comment), comment)
        comments = '<i>Комментарии:</i>\n'
        for i in comment:
            if len(i['message']):
                message = i['message']
                changed = i['changed'].split('.')[0].replace('T', ' ')
                executor = i['executor']
                print(f'{changed} - {message} - {executor}')
                comments += f'{changed} - {message} - {executor}\n'


    except Exception as e:
        print(f'error get comment - {e}')

    claim_detail = f'<i>Заявка №</i>:<b>{number_claim}</b>\n<i>Создана:</i> {created}\n' \
                   f'<i>Приоритет:</i> {emergency}\n<i>Заказчик:</i> {applicant}\n' \
                   f'<i>Телефон:</i> +{contact_phone}\n<i>Сообщение:</i> {text}\n<i>Текущий статус:</i> {status}\n' \
                   f'<i>Планируемая дата закрытия:</i>{planned_date}\n' + comments
    return claim_detail


def get_claim_list_in_json(message, id):
    # claimlist  = []
    response = requests.get(BASE_PATH + f'/api/v1/claim/?executor={id}&status=2&status=1', headers=headers)
    print('response', response.text)
    claim_list = ClaimList(each_claim=json.load(StringIO(response.text)))
    # claims = json.loads(r.text)
    # print('&&&&&&&&', claims)
    # for i in claims:
    #     claim_id = i.get('id')
    #     company = i.get('company')
    #     applicant = i.get('applicant')
    #     status = i.get('status')
    #     created = i.get('created')
    #     claimlist.append(ClaimList(claim_id, company, applicant, created, status))
    # print(f'claim_id = {claim_id} claims = {claims}')
    # return claimlist
    return claim_list


def get_claim_list_archive(message, id):
    response = requests.get(BASE_PATH + f'/api/v1/claim/?executor={id}&ordering=internal_id&status=3',
                            headers=headers)
    claim_archive_list = ClaimList(each_claim=json.load(StringIO(response.text)))
    # for i in claimarchive:
    # claim_id = i.get('id')
    # company = i.get('company')
    # applicant = i.get('applicant')
    # status = i.get('status')
    # created = i.get('created')
    # claim_archive_data = ClaimList(claim_id, company, applicant, created, status)
    # print('claim_archive_data', claim_archive_data)
    # claimarchivelist.append(claim_archive_data)
    # print( f'claimarchive:: {claimarchivelist}')
    return claim_archive_list


def get_claims(claims, chat_id):
    print('get_claims work')
    for i in claims.each_claim:
        # print('i', i)
        # applicant = i.applicant
        # status = i.status
        # claim_id = i.id
        claim_list_res = f'<i>Идентификатор:</i> <b>{i.id}</b>\n<i>Адрес</i>: <b>{i.applicant}</b> \n<i>Статус:</i> <b>{i.status}</b>  \n '
        keyboard = types.InlineKeyboardMarkup()
        claim_detail_button = types.InlineKeyboardButton(text="Подробнее ✏", callback_data=f"claim_detail#{i.id}")
        send_comment_button = types.InlineKeyboardButton(text="Комментарий ✉", callback_data=f"send_comment#{i.id}")
        if i.status == 'Принята':
            callback_button = types.InlineKeyboardButton(text="В работу 👷", callback_data=f"take_to_work#{i.id}")
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
            callback_button = types.InlineKeyboardButton(text="Завершить ✅", callback_data=f"claim_close#{i.id}")
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


def get_chat_id_json(chat_id):
    res = requests.get(f'{BASE_PATH}/api/v1/company/executor/?chat_id={chat_id}', headers=headers)
    res_json = json.loads(res.text)
    print('chat_id', chat_id)
    print('res_ison', res_json)
    executor_class = {}
    if res_json:
        print('get_chat_id_json res_json', res_json)
        executor = res_json[0]
        executor_class = Executor(id=executor['id'], name=executor['get_requisites'],
                                  profession=executor['specialization'], url=executor['url'], phone=executor['phone'])
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
    executor_json = get_chat_id_json(CHAT_ID)
    if executor_json:
        print(executor)
        User.phone = executor_json.phone
        set_in_executor_chat_id(executor_json.id, CHAT_ID)
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=False)
        button_line = types.KeyboardButton(text='Выйти на линию')
        keyboard.add(button_line)
        bot.register_next_step_handler(message, get_menu)
        print(f'user = {User}')
        mes_in_line = bot.send_message(CHAT_ID, text=f"Добрый день, нажмите кнопку выйти на линию.",
                                       reply_markup=keyboard)
        mes_id['mes_in_line'] = mes_in_line.message_id

    else:
        # if user_id not in users_id:
        print('no in user')
        users_id.add(user_id)
        User.users_id = user_id
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
def get_menu(message):
    print('get_menu сработал')
    global executor
    # bot.delete_message(message.chat.id, mes_send_phone.message_id)
    mes_out_in_line = message.message_id
    bot.delete_message(message.chat.id, mes_out_in_line)
    executor = get_executor_list(message.chat.id)
    # print(f'executor = {executor}')
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
    print(message.chat.id)
    chat_id = message.chat.id
    try:
        user_id = message.from_user.id
    except:
        print('error get user')
    if message.text == 'Список заявок':
        executor_json = get_chat_id_json(message.chat.id)
        del_list_mes_id(chat_id)
        claims = get_claim_list_in_json(message, executor_json.id)
        print('claims', claims)
        get_claims(claims, chat_id)
        try:
            bot.delete_message(chat_id, message.message_id)
            list_mes_id.remove(message.message_id)
            bot.delete_message(chat_id, mes_id['you_in_line'])
            list_mes_id.remove(mes_id['you_in_line'])
        except Exception as e:
            print("can't delete message claim_list", e)
        # del_list_mes_id()
        # get_claims(claim_id, claims)
    elif message.text == 'Архив заявок':
        executor_json = get_chat_id_json(chat_id)
        del_list_mes_id(chat_id)
        bot.delete_message(chat_id, message.message_id)
        claims = get_claim_list_archive(message, executor_json.id)
        get_claims(claims, chat_id)


    else:
        bot.send_message(chat_id, 'Не понял команду')


@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    chat_id = message.chat.id
    try:
        phone = message.contact.phone_number.replace('+', '')
        User.phone = phone
        executor = get_executor_list(CHAT_ID)
        print('exec', executor.id)
        set_in_executor_chat_id(executor.id, CHAT_ID)
        print('user.phone', User.phone)
    except Exception as e:
        print(e)
    mes_phone_info = message.message_id
    mes_id['mes_phone_info'] = mes_phone_info
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=False)
    button_line = types.KeyboardButton(text='Выйти на линию')
    keyboard.add(button_line)
    bot.register_next_step_handler(message, get_menu)
    print(f'user = {User}')
    mes_in_line = bot.send_message(chat_id, text=f"Добрый день, нажмите кнопку выйти на линию.", reply_markup=keyboard)
    mes_id['mes_in_line'] = mes_in_line.message_id
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

def send_comment(claim_id, executor, message):
    data = {'claim': claim_id, 'executor': str(executor), 'message': message}
    print('data', data)
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
    else:
        claimid = None
    detail_keyboard = claim_detail_keyboard(claimid)
    if call.data.split('#')[0] == "take_to_work":
        print('test message', call.message)
        try:
            [bot.delete_message(call.message.chat.id, i) for i in list_mes_id]
        except:
            pass
        try:
            print(call.message.message_id)
        except Exception as e:
            print('Except:', e)

        # taked_claim = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
        # text="Заявка принята", reply_markup=detail_keyboard)
        # list_mes_id.appendleft(taked_claim.message_id)
        set_status_claim_in_work(claimid)
        # bot.delete_message(CHAT_ID, list_mes_id.popleft())
        # comment_text = create_comment_text(claimid, taked_claim.text)
        # set_claim_detail(claimid, comment_text)


    elif call.data.split('#')[0] == "claim_close":
        key_det_image = send_image_keyboard(claimid)
        claim_close = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                            text="Заявка выполнена", reply_markup=key_det_image)
        set_status_claim_close(claimid)
        # comment_text = create_comment_text(claimid, claim_close.text)
        # set_claim_detail(claimid, comment_text)
        list_mes_id.appendleft(claim_close.message_id)
        # bot.delete_message(CHAT_ID, list_mes_id.popleft())
    elif call.data.split('#')[0] == "claim_detail":
        claim_detail = get_claim_detail(claimid)
        key_det = claim_detail_keyboard(claimid)
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
    elif call.data.split('#')[0] == "send_comment":
        def set_comment(message, claimid=claimid):
            # comment_text = create_comment_text(claimid, message.text)
            # set_claim_detail(claimid, comment_text)
            executor_class = get_chat_id_json(message.chat.id)
            print('executor_class', executor_class)
            send_comment(claimid, executor_class.id, message.text)
            bot.send_message(message.chat.id,
                             f' <i>Заявка №</i> <b>{claimid}</b> <i>Исполнитель</i> -<b>{executor_class.id}</b> <i>оставил комментарий</i> <b>{message.text}</b>',
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
                executor = get_chat_id_json(message.chat.id)
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
