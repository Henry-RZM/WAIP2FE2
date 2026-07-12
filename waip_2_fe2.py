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
import threading # für Session-Keepalive

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
    opts, args = getopt.getopt(argv[1:], "hf:p:w:", ["help", "fe2url=", "fe2pass=", "wache="])
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

logpath = str(pathlib.Path().resolve())
logpath += r"\waip_2_fe2.log"
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
sio = socketio.Client(logger=False, engineio_logger=False)

# Zeitstempel des letzten Disconnects — für Reconnect-Dauer-Messung.
# None = noch nie verbunden gewesen (erster Connect → immer Konsole).
_disconnect_time = None

def _cprint(msg):
    """Gibt eine Meldung sowohl auf der Konsole als auch im Logfile aus."""
    print(msg)
    logging.info(f' WAIP2ALAMOS: {msg}')

# Trigger Event Connect
@sio.event(namespace='/waip')
def connect():
    global _disconnect_time
    if _disconnect_time is None:
        # Erster Connect → Konsole + Log
        _cprint(f'===> Verbunden mit Wache: {wache} (erster Connect)')
    else:
        elapsed = time.time() - _disconnect_time
        if elapsed >= 10:
            # Langsamer Reconnect → Konsole + Log
            _cprint(f'===> Verbunden mit Wache: {wache} (Reconnect nach {elapsed:.1f}s)')
        else:
            # Normaler ~15-Min-Reconnect unter 10 Sekunden → nur Log
            logging.info(f' WAIP2ALAMOS: ===> reconnected, Wache: {wache} ({elapsed:.1f}s)')
    sio.emit('WAIP', wache, namespace='/waip')

# Trigger Event Disconnect
@sio.event(namespace='/waip')
def disconnect():
    global _disconnect_time
    _disconnect_time = time.time()
    logging.info(f' WAIP2ALAMOS: ===> disconnected from server')

# Trigger Event Version; Gibt die Runtime ID des Servers wieder
@sio.on('io.version', namespace='/waip')
def on_message(data):
    logging.info(f' WAIP2ALAMOS: ===> Server Version/Process Number: {data}')

# Trigger Event Fehler vom Server (z.B. Session-Timeout → normaler Reconnect-Zyklus)
@sio.on('io.error', namespace='/waip')
def on_error(data):
    logging.warning(f' WAIP2ALAMOS: ===> Server io.error: {data}')

# Trigger Event Neuer Alarm
@sio.on('io.new_waip', namespace='/waip')
def on_alarm(data):
    # Rohdaten sofort loggen, damit ein Payload mit fehlenden/unerwarteten Feldern
    # nachvollziehbar bleibt, auch wenn die Verarbeitung weiter unten crasht.
    logging.info(f' WAIP2ALAMOS: ===> io.new_waip Rohdaten: {data}')

    try:
        _process_alarm(data)
    except Exception:
        logging.error(f' WAIP2ALAMOS: Fehler bei der Verarbeitung von io.new_waip: {data}')
        logging.error(traceback.format_exc())


def _process_alarm(data):
    global letzter_alarm

    from datetime import datetime

    # zeitstempel ist ein formatierter String (kein ts_alarm Unix-Timestamp,
    # die Wachalarm IP API liefert nach wie vor das alte Feld)
    alarm_time = datetime.strptime(data["zeitstempel"], "%Y-%m-%d %H:%M:%S")
    time_dif = datetime.today() - alarm_time

    # Feldname ist stichwort (kein einsatzstichwort, die API liefert nach wie vor das alte Feld)
    stichwort = data["stichwort"]

    print(f'Neuer Alarm: {data["id"]} {stichwort} - {data["ort"]}')
    logging.info(f' WAIP2ALAMOS: ===> Neuer Alarm! ID: {data["id"]}')
    logging.info(f' WAIP2ALAMOS: zeitstempel: {alarm_time}')
    logging.info(f' WAIP2ALAMOS: Alarm Offset: {time_dif}')
    logging.info(f' WAIP2ALAMOS: einsatzart: {data["einsatzart"]}')
    logging.info(f' WAIP2ALAMOS: stichwort: {stichwort}')
    logging.info(f' WAIP2ALAMOS: ortsteil: {data["ortsteil"]}')
    logging.info(f' WAIP2ALAMOS: ort: {data["ort"]}')
    logging.info(f' WAIP2ALAMOS: em_alarmiert: {data["em_alarmiert"]}')
    logging.info(f' WAIP2ALAMOS: em_weitere: {data["em_weitere"]}')
    logging.info(f' WAIP2ALAMOS: ========================================= ')

    # em_alarmiert/em_weitere sind jetzt Listen, nicht mehr JSON-Strings
    em_alarmiert = data["em_alarmiert"] if data["em_alarmiert"] else []
    em_weitere = data["em_weitere"] if data["em_weitere"] else []

    # Feldname in em-Einträgen: name -> name_einsatzmittel
    def em_name(em):
        return em.get("name_einsatzmittel") or em.get("name", "")

    # Fahrzeug-Liste für FE2 (em_alarmiert + em_weitere)
    vehicles = [{"id": em_name(em)} for em in em_alarmiert + em_weitere]

    # Meldetext
    message_parts = [f'{stichwort}\n{data["ortsteil"]} {data["ort"]}']
    if em_alarmiert:
        message_parts.append('EM Alarmiert: ' + '; '.join(em_name(em) for em in em_alarmiert))
    if em_weitere:
        message_parts.append('EM Alarmiert Weitere: ' + '; '.join(em_name(em) for em in em_weitere))

    post_data = {
        "type": "ALARM",
        "timestamp": "2000-01-01T00:00:00+01:00",
        "sender": "Wachalarm IP",
        "authorization": fe2_pass,
        "data": {
            "externalId": "python-waip-fe2",
            "keyword": stichwort,
            "keyword_description": data["einsatzart"],
            "message": [' \n '.join(message_parts)],
            "location": {
                "city": data["ort"],
                "city_abbr": data["ortsteil"],
            },
            "vehicles": vehicles,
        }
    }

    if (time_dif.total_seconds() < 600):
        if (letzter_alarm != data["id"]):
            logging.info(f' WAIP2ALAMOS: Trying to do FE2 POST request with this data: {post_data}')
            try:
                post = requests.post(fe2_url, json=post_data, timeout=300)
                logging.info(f' WAIP2ALAMOS: FE2 POST request return code: {post.text}')
            except requests.exceptions.RequestException as e:
                logging.error(f' WAIP2ALAMOS: FE2 POST request fehlgeschlagen: {e}')
            letzter_alarm = data["id"]
        else:
            logging.info(f' WAIP2ALAMOS: Alarm nicht gesendet, doppelalarm')
    else:
        logging.info(f' WAIP2ALAMOS: Alarm nicht gesendet, Zeitunterschied ist zu groß')


# HTTP-Session für Cookie-Übergabe beim Socket-Connect und Keepalive.
# Verlängert den Server-seitigen Disconnect von ~10 auf ~15 Minuten.
# Nach Disconnect reconnectet der While-Loop automatisch (<2 Sekunden).
http_session = requests.Session()
http_session.get(f'{waip_url}/waip/{wache}', timeout=10)
logging.info(f' WAIP2ALAMOS: ===> HTTP-Session initialisiert, Cookie: {bool(http_session.cookies)}')

def session_keepalive():
    while True:
        time.sleep(4 * 60)
        try:
            http_session.get(f'{waip_url}/waip/{wache}', timeout=10)
            logging.info(f' WAIP2ALAMOS: ===> Session keepalive OK')
        except Exception as e:
            logging.warning(f' WAIP2ALAMOS: Session keepalive fehlgeschlagen: {e}')

threading.Thread(target=session_keepalive, daemon=True).start()

while (2 >= 1): # Endlosschleife falls Verbindung getrennt wird
    logging.info(f' WAIP2ALAMOS: ===> Verbinde zu Server: {waip_url}')

    session_cookies = '; '.join(f'{k}={v}' for k, v in http_session.cookies.items())

    try:
        sio.connect(
            waip_url,
            namespaces=[waip_namespace],
            transports=['polling'],
            auth={'id': wache},
            wait_timeout=10,
            headers={'Cookie': session_cookies} if session_cookies else {},
        )
        sio.wait()
    except socketio.exceptions.ConnectionError as e:
        print(f'Verbindungsfehler: {e}')
        logging.error(f' WAIP2ALAMOS: Verbindungsfehler: {e}')
        logging.error(traceback.format_exc())
        time.sleep(5)
    except Exception as e:
        print(f'Unerwarteter Fehler: {type(e).__name__}: {e}')
        logging.error(traceback.format_exc())
        time.sleep(5)
    finally:
        try:
            sio.disconnect()
        except Exception:
            pass
