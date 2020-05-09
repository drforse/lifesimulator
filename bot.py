# -*- coding: utf-8 -*-
import os
import telebot
import time
import random
import threading
from emoji import emojize
from telebot import types
from pymongo import MongoClient
import traceback

token = os.environ['TELEGRAM_TOKEN']
bot = telebot.TeleBot(token)


client=MongoClient(os.environ['database'])
db=client.lifesim
users=db.users
locs = db.locs
kvs = db.kvs

users.update_many({},{'$set':{'human.walking':False}})
kvs.update_many({},{'$set':{'humans':[]}})

#users.update_many({},{'$set':{'power':40,
#        'maxpower':100,
#        'sleep':100,
#        'maxsleep':100}})

streets = {
    'bitard_street':{
        'name':'Битард-стрит',
        'nearlocs':['meet_street'],
        'code':'bitard_street',
        'homes':['17', '18', '30'],
        'buildings':{},
        'humans':[]
    },
    
    'new_street':{
        'name':'Новая',
        'nearlocs':['meet_street'],
        'code':'new_street',
        'homes':['101', '228'],
        'buildings':{},
        'humans':[]
    },
    
    'meet_street':{
        'name': 'Встречная',
        'nearlocs':['new_street', 'bitard_street'],
        'code':'meet_street',
        'homes':[],
        'buildings':{},
        'humans':[]
    }


}

#locs.remove({})

for ids in streets:
    street = streets[ids]
    if locs.find_one({'code':street['code']}) == None:
        locs.insert_one(street)  

letters = [' ', 'а', 'б', 'в', 'г', 'д', 'е', 'ё', 'ж', 'з', 'и', 'й', 'к', 'л', 'м', 'н', 'о', 'п', 'р', 'с', 'т', 'у', 'ф', 
          'х', 'ц', 'ч', 'ш', 'щ', 'ь', 'ъ', 'ы', 'э', 'ю', 'я']

emjs = ['🚶', '🚶‍♀️']

h_colors = ['brown', 'gold', 'orange', 'black']
h_lenghts = ['short', 'medium', 'long']

@bot.message_handler(commands=['clear_all'])
def clearall(m):
    if m.from_user.id == 441399484:
        users.remove({})
        bot.send_message(m.chat.id, 'Очистил юзеров.')

@bot.message_handler(commands=['navigator'])
def navv(m):
    bot.send_message(m.chat.id, '📴Проблемы с соединением, навигатор временно не работает!')
    
@bot.message_handler(commands=['help'])
def navv(m):
    bot.send_message(m.chat.id, '📴Проблемы с соединением, сайт временно не работает!')

@bot.message_handler(func = lambda message: message.text != None and message.text[0] in emjs)
def doings(m):
    if m.from_user.id != m.chat.id:
        return
    user = getuser(m.from_user)
    if user['start_stats'] == True:
        return
    if user['human']['walking']:
        bot.send_message(m.chat.id, 'Вы сейчас в пути!')
        return
    
    if m.text == '🚶Передвижение' or m.text == '🚶‍♀️Передвижение':
        avalaible_locs = []
        h = user['human']
        street = streets[h['position']['street']]
        if h['position']['flat'] == None and h['position']['building'] == None:
            for ids in street['nearlocs']:
                avalaible_locs.append('street?'+ids)
                
            for ids in street['buildings']:
                avalaible_locs.append('building?'+ids)
            
            for ids in h['keys']:
                kv = kvs.find_one({'id':int(ids.split('#')[2])})
                if kv['home'] in street['homes'] and kv['street'] == street['code']:
                        avalaible_locs.append('home?'+str(kv['id']))
                    
        else:
            avalaible_locs.append('street?'+street['code'])
        
        if h['gender'] == 'male':
            em = '🚶'
        elif h['gender'] == 'female':
            em = '🚶‍♀️'
        kb = types.ReplyKeyboardMarkup()
            
        for ids in avalaible_locs:
            print(ids)
            kb.add(types.KeyboardButton(em+to_text(ids, 'place')))
            
        bot.send_message(m.chat.id, 'Куда хотите пойти?', reply_markup=kb)
        
    else:
        try:
            what = m.text[1:].split(' ')[0]
            which = m.text.split(what+' ')[1]
        except:
            bot.send_message(m.chat.id, 'Такого места в городе нет!')
            return
        
        if what == 'Улица':
            newstr = None
            for ids in streets:
                if streets[ids]['name'] == which:
                    newstr = streets[ids]
                
            if newstr == None:
                bot.send_message(m.chat.id, 'Чего-то вы придумываете... Улицы '+which+' в этом городе нет!')
                return
            
            h = user['human']
            curstr = h['position']['street']
            if newstr['code'] not in streets[curstr]['nearlocs'] and h['position']['flat'] == None and h['position']['building'] == None:
                bot.send_message(m.chat.id, 'Вы не можете попасть на эту улицу отсюда!')
                return
            if h['position']['flat'] != None:
                kv = kvs.find_one({'id':h['position']['flat']})
                if kv['street'] != newstr['code']:
                    bot.send_message(m.chat.id, 'Вы не можете попасть на эту улицу отсюда!')
                    return
            users.update_one({'id':user['id']},{'$set':{'human.walking':True}})
            if h['position']['flat'] != None:
                threading.Timer(random.randint(50, 70), endwalk, args = [user, newstr, 'flat']).start()
                bot.send_message(m.chat.id, 'Вы выходите из квартиры. Окажетесь на улице примерно через минуту.')
            else:
                threading.Timer(random.randint(50, 70), endwalk, args = [user, newstr]).start()
                bot.send_message(m.chat.id, 'Вы направились в сторону улицы '+newstr['name']+'. Дойдёте примерно через минуту.')
            
        elif what == 'Квартира':
            try:
                kv = kvs.find_one({'id':int(which)})
                if kv == None:
                    crash += 1
            except:
                bot.send_message(m.chat.id, 'От такой квартиры ключей у вас нет!')
                return
            
            h = user['human']
            curkv = h['position']['flat']
            curb = h['position']['building']
            if curkv != None or curb != None:
                bot.send_message(m.chat.id, 'Вы не можете попасть в эту квартиру отсюда!')
                return
            
            if kv['street'] != h['position']['street']:
                bot.send_message(m.chat.id, 'Вы не можете попасть в эту квартиру отсюда!')
                return

            users.update_one({'id':user['id']},{'$set':{'human.walking':True}})
            threading.Timer(random.randint(50, 70), endwalk_flat, args = [user, kv]).start()
            bot.send_message(m.chat.id, 'Вы начали подниматься в квартиру '+str(which)+'. Дойдёте примерно через минуту.')
            
            
            
            
def endwalk_flat(user, kv):
    users.update_one({'id':user['id']},{'$set':{'human.walking':False}})
    kvs.update_one({'id':kv['id']},{'$push':{'humans':user['id']}})
    users.update_one({'id':user['id']},{'$set':{'human.position.building':None}})
    users.update_one({'id':user['id']},{'$set':{'human.position.flat':kv['id']}})
    bot.send_message(user['id'], 'Вы зашли в квартиру '+str(kv['id'])+'!')
    kv = kvs.find_one({'id':kv['id']})
    for ids in kv['humans']:
        if int(ids) != user['id']:
            bot.send_message(ids, 'В квартиру заходит '+desc(user))
            
    text = 'В квартире вы видите следующих людей:\n\n'
    for ids in kv['humans']:
        if ids != user['id']:
            text += desc(users.find_one({'id':ids}), True)+'\n\n'
            
    if text != 'В квартире вы видите следующих людей:\n\n':
        bot.send_message(user['id'], text)
    

    
def desc(user, high=False):
    text = ''
    h = user['human']
    telosl = 0
    if h['gender'] == 'male':
        if not high:
            text += 'парень '
        else:
            text += 'Парень '
    elif h['gender'] == 'female':
        if not high:
            text += 'девушка '
        else:
            text += 'Девушка '
    if h['strenght'] <= 5:
        telosl -= 1
    elif h['strenght'] <= 10:
        telosl -= 3
    elif h['strenght'] <= 20:
        telosl -= 6
        
    if h['maxhunger'] <= 60:
        telosl -= 4
    elif h['maxhunger'] <= 85:
        telosl -= 2
    elif h['maxhunger'] <= 100:
        telosl -= 1
    elif h['maxhunger'] <= 120:
        telosl += 2
    elif h['maxhunger'] <= 150:
        telosl += 5
    elif h['maxhunger'] <= 200:
        telosl += 9
        
    
    if telosl <= -7:
        text += 'тощего телосложения, '
    elif telosl <= -3:
        text += 'стройного телосложения, '
    elif telosl <= 5:
        text += 'среднего телосложения, '
    elif telosl <= 10:
        text += 'полного телосложения, '
    elif telosl > 10:
        text += 'очень полного телосложения, '
      
    text += 'примерно '
    if h['body']['height'] <= 165:
        text += 'небольшого роста. '
    elif h['body']['height'] <= 180:
        text += 'среднего роста. '
    elif h['body']['height'] > 180:
        text += 'высокого роста. '
        
    if h['gender'] == 'male':
        gn = 'него'
    elif h['gender'] == 'female':
        gn = 'неё'
    if h['body']['hair_lenght'] == 'short':
        text += 'У '+gn+' короткие, '
    elif h['body']['hair_lenght'] == 'medium':
        text += 'У '+gn+' средней длины '
    elif h['body']['hair_lenght'] == 'long':
        text += 'У '+gn+' длинные, '
        
    if h['body']['hair_color'] == 'brown':
        text += 'русые волосы.'
    if h['body']['hair_color'] == 'gold':
        text += 'золотые волосы.'
    if h['body']['hair_color'] == 'orange':
        text += 'рыжие волосы.'
    if h['body']['hair_color'] == 'black':
        text += 'чёрные волосы.'
        
    gnd = ' Он'
    gnd2 = 'им'
    if h['gender'] == 'female':
        gnd = ' Она'
        gnd2 = 'ей'
    if h['sleep'] / h['maxsleep'] <= 0.4:
        text += gnd+' выглядит уставш'+gnd2+'.'
    return text       
    
    
def endwalk(user, newstr, start = 'street'):
    users.update_one({'id':user['id']},{'$set':{'human.walking':False}})
    locs.update_one({'code':user['human']['position']['street']},{'$pull':{'humans':user['id']}})
    users.update_one({'id':user['id']},{'$set':{'human.position.street':newstr['code']}})
    users.update_one({'id':user['id']},{'$set':{'human.position.building':None, 'human.position.flat':None}})
    if start == 'street':
        bot.send_message(user['id'], 'Гуляя по городским переулкам, вы дошли до улицы '+newstr['name']+'!')
    elif start == 'flat':
        bot.send_message(user['id'], 'Вы вышли на улицу '+newstr['name']+'!')
    locs.update_one({'code':newstr['code']},{'$push':{'humans':user['id']}})
    
    street = locs.find_one({'code':newstr['code']})
    for ids in street['humans']:
        if int(ids) != user['id']:
            bot.send_message(ids, 'На улице появляется '+desc(user))
            
    text = 'На улице вы видите следующих людей:\n\n'
    for ids in street['humans']:
        if ids != user['id']:
            text += desc(users.find_one({'id':ids}), True)+'\n\n'
            
    if text != 'На улице вы видите следующих людей:\n\n':
        bot.send_message(user['id'], text)
    
    
@bot.message_handler(content_types = ['text'])
def alltxts(m):
    if m.from_user.id == m.chat.id:
        user = getuser(m.from_user)
        if user['newbie']:
            users.update_one({'id':user['id']},{'$set':{'newbie':False}})
            bot.send_message(m.chat.id, 'Здравствуй, новый житель города "Телеград". Не знаю, зачем вы сюда пожаловали, но я в чужие '+
                             'дела не лезу, как говорится. Я - Пасюк, гид в этом городе. И моя роль - заселять сюда новоприезжих, вот и всё ('+
                             'по секрету - мне за это даже не платят, хотя я стою тут 24/7 и встречаю новых людей. Делаю я это по доброте душевной '+
                             'и просто потому, что могу). '+
                             'Так что заполните анкету и сообщите мне, когда будете готовы, и я покажу вам вашу новую квартиру.')
            
            kb = getstartkb(user)
            bot.send_message(m.chat.id, 'Нажмите на характеристику, чтобы изменить её. Внимание! Когда вы нажмёте "✅Готово", '+
                                 'некоторые характеристики больше нельзя будет изменить!', reply_markup = kb)
            return
        
        if user['human']['walking']:
            bot.send_message(m.chat.id, 'Вы сейчас в пути!')
            return
        
        if user['wait_for_stat'] != None and user['start_stats'] == True:
            what = user['wait_for_stat']
            allow = True
            er_text = ''
            if what == 'name':
                val = m.text.title()
                for ids in m.text:
                    if ids.lower() not in letters:
                        allow = False
                        er_text = 'Имя должно содержать не более 50 символов и не может содержать ничего, кроме букв русского алфавита и пробелов!'
            elif what == 'gender':
                if m.text.lower() == 'парень':
                    val = 'male'
                if m.text.lower() == 'девушка':
                    val = 'female'
                if m.text.lower() not in ['парень', 'девушка']:
                    allow = False
                    er_text = 'Ваш пол может быть либо `парень`, либо `девушка`!'
            elif what == 'age':
                try:
                    age = int(m.text)
                    val = age
                    if age < 18 or age > 25:
                        crash += '_'
                except:
                    allow = False
                    er_text = 'Начальный возраст может быть от 18 до 25!'
            elif what == 'body.hair_color':
                if m.text.lower() == 'русый':
                    val = 'brown'
                elif m.text.lower() == 'золотой':
                    val = 'gold'
                elif m.text.lower() == 'рыжий':
                    val = 'orange'
                elif m.text.lower() == 'чёрный':
                    val = 'black'
                if m.text.lower() not in ['русый', 'золотой', 'рыжий', 'чёрный']:
                    allow = False
                    er_text = 'Цвет волос может быть `русый`, `золотой`, `рыжий` или `чёрный`!'
            elif what == 'body.hair_lenght':
                if m.text.lower() == 'короткие':
                    val = 'short'
                if m.text.lower() == 'средние':
                    val = 'medium'
                if m.text.lower() == 'длинные':
                    val = 'long'
                if m.text.lower() not in ['короткие', 'средние', 'длинные']:
                    allow = False
                    er_text = 'Длина волос может быть: `короткие`, `средние`, `длинные`!'
                    
            elif what == 'body.height':
                try:
                    height = int(m.text)
                    val = height
                    if height < 140 or height > 200:
                        crash += '_'
                except:
                    allow = False
                    er_text = 'Рост может быть от 140 до 200 см!'
                    
            if allow:        
                users.update_one({'id':user['id']},{'$set':{'human.'+what:val, 'wait_for_stat':None}})    
                user = getuser(m.from_user)
            
            if allow == False:
                bot.send_message(m.chat.id, er_text, parse_mode = 'markdown')
                kb = getstartkb(user)
                bot.send_message(m.chat.id, 'Нажмите на характеристику, чтобы изменить её. Внимание! Когда вы нажмёте "✅Готово", '+
                                 'некоторые характеристики больше нельзя будет изменить!', reply_markup = kb)
            else:
                bot.send_message(m.chat.id, 'Успешно изменена выбранная характеристика на "'+str(val)+'"!')
                kb = getstartkb(user)
                bot.send_message(m.chat.id, 'Нажмите на характеристику, чтобы изменить её. Внимание! Когда вы нажмёте "✅Готово", '+
                                 'некоторые характеристики больше нельзя будет изменить!', reply_markup = kb)
        if user['human']['position']['street']:
            street = locs.find_one({'code': user['human']['position']['street']})
            for human in street['humans']:
           
                   
                bot.send_message(human, f"{user['human']['name']}: {m.text}")
        elif user['human']['position']['flat']:
            kv = kvs.find_one({'id': user['human']['position']['flat']})
            for human in kv['humans']:  
         
                   
                bot.send_message(human, f"{user['human']['name']}: {m.text}")

def getstartkb(user):
    h = user['human']
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(text = 'Имя: '+str(h['name']), callback_data = 'change?name'))
    kb.add(types.InlineKeyboardButton(text = 'Пол: '+to_text(h['gender'], 'gender').lower(), callback_data = 'change?gender'))
    kb.add(types.InlineKeyboardButton(text = 'Возраст: '+str(h['age']), callback_data = 'change?age'))
    kb.add(types.InlineKeyboardButton(text = 'Наличные: '+str(h['money']), callback_data = 'change?not'))
    kb.add(types.InlineKeyboardButton(text = 'Образование: '+to_text(h['education'], 'education').lower(), callback_data = 'change?not'))
    kb.add(types.InlineKeyboardButton(text = 'Цвет волос: '+to_text(h['body']['hair_color'], 'hair_color').lower(), callback_data = 'change?body.hair_color'))
    kb.add(types.InlineKeyboardButton(text = 'Длина волос: '+to_text(h['body']['hair_lenght'], 'hair_lenght').lower(), callback_data = 'change?body.hair_lenght'))
    kb.add(types.InlineKeyboardButton(text = 'Рост: '+str(h['body']['height'])+'см', callback_data = 'change?body.height'))
    
    kb.add(types.InlineKeyboardButton(text = '✅Готово', callback_data = 'change?ready'))
    
    return kb
        
    
@bot.callback_query_handler(func = lambda call: call.data.split('?')[0] == 'change')
def changestats(call):
    user = users.find_one({'id':call.from_user.id})
    if user == None:
        return
    if user['start_stats'] == False:
        return
    what = call.data.split('?')[1]
    if what == 'not':
        bot.answer_callback_query(call.id, 'Эту характеристику изменить нельзя!', show_alert = True)
        return
    users.update_one({'id':user['id']},{'$set':{'wait_for_stat':what}})
    text = 'не определено'
    if what == 'name':
        text = 'Теперь пришлите мне ваше имя.'
    elif what == 'gender':
        text = 'Теперь пришлите мне ваш пол (может быть `парень` или `девушка`).'
    elif what == 'age':
        text = 'Теперь пришлите мне ваш возраст (от 18 до 25).'
    elif what == 'body.hair_color':
        text = 'Теперь пришлите мне цвет ваших волос (может быть: `русый`, `золотой`, `рыжий`, `чёрный`).'
    elif what == 'body.hair_lenght':
        text = 'Теперь пришлите мне длину ваших волос (могут быть: `короткие`, `средние`, `длинные`).'
    elif what == 'body.height':
        text = 'Теперь пришлите мне ваш рост (от 150 до 190).'
        
    elif what == 'ready':
        h = user['human']
        if h['name'] == None:
            bot.answer_callback_query(call.id, 'Нельзя начать с пустым именем!', show_alert = True)
            return
        else:
            medit('Хорошо! Я вас зарегистрировал, '+h['name']+'. Ваша квартира будет находиться по адресу: улица '+
                  streets[h['street']]['name']+', дом '+h['home']+'. Надеюсь, сами доберётесь. Сейчас вы находитесь на улице Встречная! '+
                  'Чтобы найти какое-то место, вы всегда можете воспользоваться навигатором (/navigator) на своём устройстве. Успехов!', call.message.chat.id, call.message.message_id)
            
            users.update_one({'id':user['id']},{'$set':{'start_stats':False}})
            users.update_one({'id':user['id']},{'$set':{'wait_for_stat':False}})
                
            time.sleep(2)
            bot.send_message(call.message.chat.id, 'Чуть не забыл! По всем вопросам можете обращаться на сайт нашего города (/help). Я сам его программировал!')
            return
    medit(text, call.message.chat.id, call.message.message_id, parse_mode = 'markdown')

        
def to_text(x, param):
    ans = 'Не определено (напишите @Loshadkin)'
    if param == 'gender':
        if x == 'male':
            ans = 'Парень'
        elif x == 'female':
            ans = 'Девушка'
            
    elif param == 'education':
        if x == 'basic':
            ans = 'Общее среднее (11 классов)'
            
    elif param == 'hair_color':
        if x == 'brown':
            ans = 'Русые'
        elif x == 'gold':
            ans = 'Золотые'
        elif x == 'orange':
            ans = 'Рыжие'
        elif x == 'black':
            ans = 'Чёрные'
            
    elif param == 'hair_lenght':
        if x == 'short':
            ans = 'Короткие'
        elif x == 'medium':
            ans = 'Средние'
        elif x == 'long':
            ans = 'Длинные'
          
    elif param == 'place':
        place = x.split('?')[0]
        code = x.split('?')[1]
        if place == 'street':
            if code in ['bitard_street', 'meet_street', 'new_street']:
                ans = 'Улица '+streets[code]['name']
        if place == 'building':
            ans = 'Дом '+str(code)
        if place == 'home':
            ans = 'Квартира '+str(code)
    return ans
            
        
def human(user):
    allstrs = []
    for ids in streets:
        if len(streets[ids]['homes']) > 0:
            allstrs.append(streets[ids])
    street = random.choice(allstrs)
    home = random.choice(street['homes'])
    key = street['code']+'#'+home+'#'+str(user.id)
    return {
        'name':None,
        'gender':random.choice(['male', 'female']),
        'age':random.randint(18, 25),
        'money':random.randint(2000, 2500),
        'street':street['code'],
        'home':home,
        'keys':[key],
        'position':{
            'street':'meet_street',
            'flat':None,
            'building':None
        },
        'hunger':100,
        'maxhunger':100,
        'health':100,
        'maxhealth':100,
        'strenght':random.randint(3, 3),
        'intelligence':random.randint(3, 3),
        'power':40,
        'maxpower':100,
        'sleep':100,
        'maxsleep':100,
        'education':'basic',
        'walking':False,
        'body':{
            'hair_color':random.choice(h_colors),
            'hair_lenght':random.choice(h_lenghts),
            'height':random.randint(150, 190)
        }
        
    }    

def createuser(user):
    return {
        'id':user.id,
        'name':user.first_name,
        'username':user.username,
        'human':human(user),
        'newbie':True,
        'start_stats':True,
        'wait_for_stat':None
    }

def createkv(user, hom, street):
    return {
        'id':user.id,
        'name':user.first_name,
        'home':hom,
        'street':street,
        'humans':[]
    }

def getuser(u):
    user = users.find_one({'id':u.id})
    if user == None:
        users.insert_one(createuser(u))
        user = users.find_one({'id':u.id})
        hom = user['human']['home']
        street = user['human']['street']
        kvs.insert_one(createkv(u, hom, street))
    return user

def medit(message_text,chat_id, message_id,reply_markup=None,parse_mode=None):
    return bot.edit_message_text(chat_id=chat_id,message_id=message_id,text=message_text,reply_markup=reply_markup,
                                 parse_mode=parse_mode)   

print('7777')
bot.polling(none_stop=True,timeout=600)

