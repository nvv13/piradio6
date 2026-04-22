#!/usr/bin/env python3


import configparser
import sys
import pwd
import os
import time
import signal
import socket
import errno
import re
import pdb
from evdev import *
from threading import Timer

# Radio project imports
from config_class import Configuration
from log_class import Log

log = Log()
udphost = 'localhost'   # IR Listener UDP host default localhost
udpport = 5100      # IR Listener UDP port number default 5100

config = Configuration()


    # Send button data to radio program
class Webrsend:
    udphost = config.remote_control_host
    udpport = config.remote_control_port
    log.message("UDP connect host " + udphost + " port " + str(udpport), log.DEBUG)
    
    def udpSend(self,button):
        global udpport
        data = ''
        log.message("Remote control daemon udpSend " + button, log.DEBUG)
        
        # The host to send to is either local host or the IP address of the remote server
        udphost = config.remote_listen_host
        try:
            clientsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            clientsocket.settimeout(5)
            button = button.encode('utf-8')
            clientsocket.sendto(button, (udphost, udpport))
            data = clientsocket.recv(100).strip()
            #data = data.decode('utf-8')
            clientsocket.close()

        except socket.error as e:
            err = e.args[0]
            if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                msg = "web remote udpSend no data: " + str(e)
                print(msg)
                log.message(msg, log.ERROR)
            else:
                # Errors such as timeout
                msg = "web remote udpSend: " + str(e)
                print(msg)
                log.message(msg , log.ERROR)

        if len(data) > 0:
            data = data.decode('utf-8')
            log.message("web daemon server sent: " + data, log.DEBUG)
            return data

### Main routine ###
if __name__ == "__main__":
	Webr=Webrsend()
	play_number = 3
	if play_number > 0:
        	print('PLAY_' + str(play_number))
        	reply = Webr.udpSend('PLAY_' + str(play_number))
        	print(reply)
