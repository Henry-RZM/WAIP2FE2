# WAIP2FE2
Script zur Abfrage der Einsätzt der socket.io Schnittstelle von Wachalarm IP und übergabe an Alamos FE2 http post Schnittstelle

## Infos
Wachalarm IP Git Repo
https://github.com/Robert-112/Wachalarm-IP-Web/wiki

Wachalarm IP Schnittstellen Doku
https://github.com/Robert-112/Wachalarm-IP-Web/wiki/Schnittstellen

Doku Schnittstelle von Alamos FE2
https://alamos-support.atlassian.net/wiki/spaces/documentation/pages/219480366/Externe+Schnittstelle

## Installation
Installation Python
* https://www.microsoft.com/store/productId/9NRWMJP3717K

Wachalarm IP Server verwendet eine ätere socket.io version, man muss uf Version 3 downgraden
* https://www.appsloveworld.com/django/100/284/python-socketio-open-packet-not-returned-by-the-server
* pip install python-engineio==3.14.2 python-socketio==4.6.0

libarys installieren
* python -m pip install logging
* python -m pip install requests
