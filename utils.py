

@bot.message_handler(commands=['phone'])
def tophone(message):
    mes = bot.send_message(CHAT_ID, '+79630745397')
    print(mes.message_id)
    bot.delete_message(CHAT_ID, message.message_id)
    #bot.delete_message(CHAT_ID, mes.message_id)

print(list_mes_id)


@bot.callback_query_handler(func=lambda call: call.endswith('hone'))
def callback_inline(call):
    bot.send_message(('phone send'))


@bot.message_handler(commands = ['url'])
def url(message):
    markup = telebot.types.InlineKeyboardMarkup()
    btn_my_site = telebot.types.InlineKeyboardButton(text='Наш сайт', url='leverans.ru')
    markup.add(btn_my_site)
    bot.send_message(message.chat.id, "Нажми на кнопку и перейди на наш сайт.", reply_markup = markup)


@bot.inline_handler(lambda query: len(query.query) > 0)
def query_text(query):
    kb = types.InlineKeyboardMarkup()
    # Добавляем колбэк-кнопку с содержимым "test"
    kb.add(types.InlineKeyboardButton(text="Нажми меня", callback_data="test"))
    results = []
    single_msg = types.InlineQueryResultArticle(id="1", title="Press me", reply_markup=kb)
    results.append(single_msg)
    bot.answer_inline_query(query.id, results)
