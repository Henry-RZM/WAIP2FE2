#####################################################################################
# 
# Script zur Abfrage der Einsätze der socket.io Schnittstelle von Wachalarm IP
# und Übergabe an Alamos FE2 http post Schnittstelle
#
# https://github.com/Henry-RZM/WAIP2FE2/
#
#####################################################################################

### libarys laden ##################################################################################
import socketio # socket.io libary für Wachalarm IP
import json # json libary, für Wachhalarm IP & FE2 API
import requests # libary für http requests zu FE2 API
import logging  # file or console logging
import traceback # stack trace
import time # sleep
import pathlib # get folder path
import sys # für parameter aufruf
import getopt # für parameter aufruf

### Parameter ##################################################################################

# Wachalarm IP URL
waip_url = 'https://wachalarm.leitstelle-lausitz.de'

# Wachalarm IP namespace
waip_namespace = '/waip'

# default Alamos FE2 Rest API
fe2_url = "http://127.0.0.1:83/rest/external/http/alarm/v2" 

# default Alamos FE2 Passwort
fe2_pass = "waip2alamos-secret"

# default Wachalarm IP Bereich (alles LST Lausitz)
wache = "0"

# parameter bei script aufruf auslesen
argv = sys.argv
arg_help = "{0} -f <fe2url> -p <fe2passwort> -w <wache>".format(argv[0])
    
try:
    opts, args = getopt.getopt(argv[1:], "hf:w:", ["help", "fe2url=", "fe2pass=", "wache="])
except:
    print(arg_help)
    sys.exit(2)

for opt, arg in opts:
    if opt in ("-h", "--help"):
        print(arg_help)  # print the help message
        sys.exit(2)
    elif opt in ("-f", "--fe2url"):
        fe2_url = arg
    elif opt in ("-p", "--fe2pass"):
        fe2_pass = arg
    elif opt in ("-w", "--wache"):
        wache = arg

letzter_alarm = "0" # Variable initialisieren

### debugging ##################################################################################
print('\n *** Script zur Abfrage der Einsätze der socket.io Schnittstelle von Wachalarm IP und Übergabe an Alamos FE2 http post Schnittstelle *** \n')

# socket.io debug output
sio = socketio.Client(logger=True, engineio_logger=False)

logpath = str(pathlib.Path().resolve())
logpath += "\waip_2_fe2.log"
print('Logfile Path: ', logpath)

# logging to file
logging.basicConfig(filename=logpath, encoding='utf-8', level=logging.INFO, format="%(asctime)s:%(levelname)s:%(message)s")
# logging to console
#logging.basicConfig(encoding='utf-8', level=logging.INFO, format="%(asctime)s:%(levelname)s:%(message)s")
logging.info(f' WAIP2ALAMOS: ===> start script')

print('Alamos FE2 API: ', fe2_url)
logging.info(f' WAIP2ALAMOS: ===> Alamos FE2 API: {fe2_url} \n')
print('Wachalarm IP Bereich: ', wache)
logging.info(f' WAIP2ALAMOS: ===> Wachalarm IP Bereich: {wache} \n')

### main ##################################################################################
sio = socketio.Client()

# Trigger Event Connect
@sio.event(namespace='/waip')
def connect():
    logging.info(f' WAIP2ALAMOS: ===> connection established')
    # Wachen ID senden und "abonnieren"
    print('Abonniere Wache: ',wache)
    sio.emit('WAIP', wache, namespace='/waip')
    logging.info(f' WAIP2ALAMOS: ===> Abonniere Wache: {wache}')

# Trigger Event Disconnect
@sio.event(namespace='/waip')
def disconnect():
    logging.info(f' WAIP2ALAMOS: ===> disconnected from server')

# Trigger Event Version; Gibt die Runtime ID des Servers wieder
@sio.on('io.version', namespace='/waip')
def on_message(data):
    logging.info(f' WAIP2ALAMOS: ===> Server Version/Process Number: {data}')

# Trigger Event Neuer Alarm
@sio.on('io.new_waip', namespace='/waip')
def on_message(data):
    global letzter_alarm

    # Zeitunterschied zwischen Alarm und jetzt
    from datetime import datetime
    time_dif = datetime.today() - datetime.strptime(data["zeitstempel"], '%Y-%m-%d %H:%M:%S')
    
    print(f'Neuer Alarm: {data["id"]} {data["stichwort"]} - {data["ort"]}')
    logging.info(f' WAIP2ALAMOS: ===> Neuer Alarm! ID: {data["id"]}')
    logging.info(f' WAIP2ALAMOS: zeitstempel: {data["zeitstempel"]}')
    logging.info(f' WAIP2ALAMOS: Alarm Offset: {time_dif}')
    logging.info(f' WAIP2ALAMOS: einsatzart: {data["einsatzart"]}')
    logging.info(f' WAIP2ALAMOS: stichwort: {data["stichwort"]}')
    logging.info(f' WAIP2ALAMOS: ortsteil: {data["ortsteil"]}')
    logging.info(f' WAIP2ALAMOS: ort: {data["ort"]}')
    logging.info(f' WAIP2ALAMOS: em_alarmiert: {data["em_alarmiert"]}')
    logging.info(f' WAIP2ALAMOS: em_weitere: {data["em_weitere"]}')
    logging.info(f' WAIP2ALAMOS: ========================================= ')

    # Fahrzeuge in json einlesen
    if data["em_alarmiert"]:
        em_alarmiert =  json.loads(data["em_alarmiert"])
    if data["em_weitere"]:
        em_weitere =  json.loads(data["em_weitere"])

    #  String für Alamos FE2 bauen
    string_data = '{  "type": "ALARM",  "timestamp": "'
    string_data += '2000-01-01T00:00:00+01:00'
    string_data += '",  "sender": "Wachalarm IP",  "authorization": "'
    string_data += fe2_pass
    string_data += '",  "data": {    "externalId": "python-waip-fe2",    "keyword": "'
    string_data += data["stichwort"]
    string_data += '",    "keyword_description": "'
    string_data += data["einsatzart"]
    string_data += '",    "message": [      "'
    string_data += data["stichwort"]
    string_data += ' \\n'
    string_data += data["ortsteil"]
    string_data += ' '
    string_data += data["ort"]
    string_data += ' '
    
    if data["em_alarmiert"]:
        string_data += '\\n \\n EM Alarmiert: '
        for em in em_alarmiert:
            string_data += em["name"]
            string_data += '; '

    if data["em_weitere"]:
        string_data += '\\n \\n EM Alarmiert Weitere: '
        for em in em_weitere:
            string_data += em["name"]
            string_data += '; '

    string_data += '"    ],    "location": {      "city": "'
    string_data += data["ort"]
    string_data += '",      "city_abbr": "'
    string_data += data["ortsteil"]
    string_data += '"    }, '
    string_data += '"vehicles": ['

    if data["em_alarmiert"]:
        for em in em_alarmiert:
            string_data += '{        "id": "'
            string_data += em["name"]
            string_data += '" },'
    
    if data["em_weitere"]:
        for em in em_weitere:
            string_data += '{        "id": "'
            string_data += em["name"]
            string_data += '" },'

    string_data = string_data.removesuffix(",")

    string_data += ']'
    string_data += '} }'

    if (time_dif.seconds < 600 ): # Nur Alarme mit geringe differenz zwischen WA-IP Zeitstempel und lokaler zeit senden, Vermeidung doppelalarmierung
        if (letzter_alarm != data["id"]):  # prüfen ob die vorherrige Alarm-ID identisch ist mit der aktuellen, Vermeidung doppelalarmierung
            post_data = json.loads(string_data)
            logging.info(f' WAIP2ALAMOS: Trying to do FE2 POST request with this data: {post_data}')
            post = requests.post(fe2_url, json = post_data, timeout=300)
            logging.info(f' WAIP2ALAMOS: FE2 POST request return code: {post.text}')
            letzter_alarm = data["id"]
        else:
            logging.info(f' WAIP2ALAMOS: Alarm nicht gesendet, doppelalarm')
    else:
        logging.info(f' WAIP2ALAMOS: Alarm nicht gesendet, Zeitunterschied ist zu groß')


while (2 >= 1): # Endlosschleife falls Verbindung getrennt wird
    # socket.io Verbindung aufbauen
    print(f'Verbinde zu Server: {waip_url}')
    logging.info(f' WAIP2ALAMOS: ===> Verbinde zu Server: {waip_url}')

    try:
        sio.connect(waip_url, namespaces=[waip_namespace])
    except Exception as e:
        logging.error(traceback.format_exc())
        print('Verbindung zu Server getrennt und reconnect failed')
        logging.info(f' Verbindung zu Server getrennt und reconnect failed')
        time.sleep(1) # pause, reduziert anfragen gegen den server

    sio.wait() # Sript am laufen halten, damit die events empfangen werden können
