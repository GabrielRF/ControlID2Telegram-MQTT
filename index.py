import flask
import json
import os
import requests
import telebot
import paho.mqtt.client as mqtt
from flask import request

alerts = os.getenv('ALERTS', '1,2,3,4,5,6,7,8,9,10,11,12,13')
bot_token = os.getenv('BOT_TOKEN')
controlid_ip = os.getenv('CONTROLID_IP')
host_ip = os.getenv('HOST_IP')
dest = os.getenv('MESSAGE_DESTINATION')
password = os.getenv('CONTROLID_PASSWORD')
webhook_host = os.getenv('WEBHOOK_HOST', '0.0.0.0')
webhook_port = os.getenv('WEBHOOK_PORT', '5432')
MQTTSERVER = os.getenv('MQTTSERVER')
MQTTUSER = os.getenv('MQTTUSER')
MQTTPASS = os.getenv('MQTTPASS')
MQTTTOPIC = os.getenv('MQTTTOPIC')

app = flask.Flask(__name__)
bot = telebot.TeleBot(bot_token)

def set_monitor():
    url = "http://" + controlid_ip + "/login.fcgi"

    payload = '{\n\t\n\t\"login\":\"admin\",\n\t\"password\":\"'+str(password)+'\"\n\t\n}'
    headers = {
        'content-type': "application/json"
        }

    response = requests.request("POST", url, data=payload, headers=headers)
    session = json.loads(response.text)['session']

    url = "http://" + controlid_ip + "/set_configuration.fcgi?session=" + session
    payload = ("{\n\t\"monitor\":" +
               "{\n\t\"request_timeout\":\"500\"," +
               "\n\t\"hostname\":\"" + host_ip + "\"," +
               "\n\t\"port\":\"" + webhook_port + "\"," +
               "\n\t\"path\":\"api/notification\"\n}\n}")
    print(payload)
    headers = {
        'content-type': "application/json"
        }

    response = requests.request("POST", url, data=payload, headers=headers)
    print(str(response))

def login(controlid_ip, password):
    url = 'http://' + controlid_ip + '/login.fcgi'
    payload = '{\n\t\n\t\"login\":\"admin\",\n\t\"password\":\"'+password+'\"\n\t\n}'
    headers = {
        'content-type': "application/json"
    }

    response = requests.request("POST", url, data=payload, headers=headers)
    session = json.loads(response.text)['session']
    return session

def get_username(controlid_ip, session, userid):
    url = 'http://' + controlid_ip + '/load_objects.fcgi?session=' + session
    payload = ("{\n\t\"object\":\"users\"," +
           "\n\t\n\t\"where\":{" +
           "\n\t\t\"users\":{" +
           "\n\t\t\t\"id\":" + userid +
           "\n\t\t}\n\t}\n}")
    headers = {
        'content-type': 'application/json'
    }

    response = requests.request('POST', url, data=payload, headers=headers)
    response = json.loads(response.text)
    return str(response['users'][0]['name'])

def sendmsg(bot, dest, userid, username, event):
    for i in dest.split(','):
        message = ('{} <b>{}</b> ({})').format(event, username, str(userid))
        bot.send_message(i, message, parse_mode='HTML')

def get_event(eventnum):
    cases = {
        1: 'Equipamento inválido',
        2: 'Parâmetros de regra de identificação inválidos',
        3: str(u'\U000026D4') + 'Não identificado',
        4: 'Identificação pendente',
        5: 'Timeout na identificação',
        6: str(u'\U000026D4'), # 'Acesso negado',
        7: str(u'\U00002705'), # 'Acesso autorizado',
        8: 'Acesso pendente',
        9: 'Usuário não é administrador',
        10: 'Acesso não identificado',
        11: str('\U0001F518') + 'Acesso através de botoeira',
        12: str('\U0001F310') + 'Acesso através de interface web',
        13: 'Desistência de entrada',
        200: 'Equipamento ligado',
        
    }
    return cases.get(int(eventnum))

@app.route('/api/notification/dao', methods=['POST'])
def index():
    mqttclient.connect(MQTTSERVER)
    jsonData = request.get_json()
    userid = jsonData['object_changes'][0]['values']['user_id']
    eventnum = jsonData['object_changes'][0]['values']['event']

    if eventnum not in alerts:
        return('')
    session = login(controlid_ip, password)
    try:
        username = get_username(controlid_ip, session, userid)
    except:
        username = ''
    event = get_event(eventnum)
    sendmsg(bot, dest, userid, username, event)
    mqttclient.publish(f'{MQTTTOPIC}/name', f'{username} ({userid})')
    return('')

@app.route('/api/notification/operation_mode', methods=['POST'])
def op_mode():
    jsonData = request.get_json()
    mode = jsonData['operation_mode']['mode']
    mode_name = jsonData['operation_mode']['mode_name']
    print(str(mode) + '\t' + mode_name)
    event = get_event(200)
    sendmsg(bot, dest, '', '', event)
    return('')


@app.route('/api/notification/secbox', methods=['POST'])
def secbox():
    mqttclient.connect(MQTTSERVER)
    jsonData = request.get_json()
    id = jsonData['secbox']['id']
    open = jsonData['secbox']['open']
    print(str(id) + '\t' + str(open))
    if open:
        mqttclient.publish(f'{MQTTTOPIC}/state', 'True')
    else:
        mqttclient.publish(f'{MQTTTOPIC}/state', 'False')
    return('')

if __name__ == '__main__':
    # app.debug = True
    mqttclient = mqtt.Client(client_id='ControlID2Telegram')
    mqttclient.username_pw_set(MQTTUSER, password=MQTTPASS)
    set_monitor()
    app.run(host=webhook_host, port=webhook_port)


