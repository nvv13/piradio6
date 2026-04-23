#!/usr/bin/env python3
# app.py
from flask import Flask, render_template, request, jsonify
import sys
import os
import signal
import subprocess
import glob
import re

from web_daemon import Daemon
from log_class import Log
from web_config_class import Configuration
from web_send_class import Webrsend

app = Flask(__name__)

log = Log()
Webr = Webrsend()

config = Configuration()
pidfile = '/var/run/web_remote.pid'
# Путь к директории с файлами (измените на свой)
FILES_DIRECTORY = "/home/orangepi/musik"

# MPD files
MpdLibDir = "/var/lib/mpd"
PlaylistsDirectory =  MpdLibDir + "/playlists"
MusicDirectory =  MpdLibDir + "/music"

# Radio files
RadioLibDir = "/var/lib/radiod"
CurrentStationFile = RadioLibDir + "/current_station"  # номер тек станции в списке
SourceNameFile = RadioLibDir + "/source_name"  # имя списка 
VolumeFile = RadioLibDir + "/volume"

# Signal SIGTERM handler
def signalHandler(signal,frame):
    global log
    pid = os.getpid()
    log.message("Remote control stopped, PID " + str(pid), log.INFO)
    sys.exit(0)

# Get the Value from a namefile
def getFileValue(namefile):
    Value = ''
    if os.path.isfile(namefile):
        try:
            f = open(namefile,'r')
            Value = f.readline()
            f.close()
        except Exception as e:
            print(str(e))
            pass
    return Value


def get_available_files():
    """Получает список файлов из директории"""
    try:
        files = glob.glob(os.path.join(FILES_DIRECTORY, "*"))
        file_names = [os.path.basename(f) for f in files if os.path.isfile(f)]
        return sorted(file_names)
    except Exception as e:
        print(f"Ошибка при чтении директории: {e}")
        return []

def get_m3u_channels():
    """Получает список каналов из M3U файла"""
    channels = []
    m3u_file=PlaylistsDirectory+'/'+getFileValue(SourceNameFile)+'.m3u'
    if not os.path.exists(m3u_file):
        print(f"M3U файл не найден: "+m3u_file)
        return channels
    
    try:
        with open(m3u_file, 'r', encoding='utf-8', errors='ignore') as file:
            lines = file.readlines()
        
        indP=1
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Стандартный M3U формат: #EXTINF:длительность,название канала
            if line.startswith('#EXTINF:'):
                # Извлекаем название канала
                # Формат: #EXTINF:0,Channel Name
                match = re.search(r'#EXTINF:[^,]*,?(.*)$', line)
                if match:
                    channel_name = ('000'+str(indP))[-3:]+' '+match.group(1).strip()
                    indP=indP+1
                    # Следующая строка - URL или путь к файлу
                    if i + 1 < len(lines):
                        channel_url = lines[i + 1].strip()
                        if channel_url and not channel_url.startswith('#'):
                            channels.append({
                                'name': channel_name,
                                'url': channel_url,
                                'type': 'm3u'
                            })
                i += 2
            # Пропускаем комментарии и пустые строки
            elif line.startswith('#') or not line:
                i += 1
            # Если встретили URL без метаданных
            elif line and not line.startswith('#'):
                # Используем имя файла как название канала
                channel_name = os.path.basename(line).split('.')[0]
                channels.append({
                    'name': channel_name,
                    'url': line,
                    'type': 'm3u'
                })
                i += 1
            else:
                i += 1
        
        return channels
    
    except Exception as e:
        print(f"Ошибка при чтении M3U файла: {e}")
        return []

def get_all_items():
    """Объединяет файлы и M3U каналы в один список"""
    items = []
    
    # Добавляем файлы из директории
    files = get_available_files()
    for file in files:
        items.append({
            'name': file,
            'type': 'file',
            'path': os.path.join(FILES_DIRECTORY, file)
        })
    
    # Добавляем каналы из M3U
    channels = get_m3u_channels()
    for channel in channels:
        items.append({
            'name': channel['name'],
            'type': 'm3u',
            'url': channel['url']
        })

    # Добавляем номер текущего канала 
    cur_station=getFileValue(CurrentStationFile)
    items.append({
            'name': cur_station,
            'type': 'cur_station',
            'position': cur_station
        })
    
    # Добавляем значение громкости
    cur_volume=getFileValue(VolumeFile)
    items.append({
            'name': cur_volume,
            'type': 'cur_volume',
            'volume': cur_volume
        })
    
    return items

def launch_item(item):
    """Запускает файл или M3U поток"""
    
    # Запуск обычного файла
    if item['type'] == 'file':
        file_path = item['path']
        
        if not os.path.exists(file_path):
            return False, "Файл не найден"
        
        # Запускаем в зависимости от расширения
        if item['name'].endswith('.py'):
            subprocess.Popen(['python3', file_path])
        elif item['name'].endswith('.sh'):
            subprocess.Popen(['bash', file_path])
        elif item['name'].endswith('.mp3') or item['name'].endswith('.wav'):
            # Аудио файлы
            subprocess.Popen(['xdg-open', file_path])
        elif item['name'].endswith('.mp4') or item['name'].endswith('.avi'):
            # Видео файлы
            subprocess.Popen(['xdg-open', file_path])
        else:
            subprocess.Popen(['xdg-open', file_path])
        
        return True, f"Запущен файл: {item['name']}"
    
    # Запуск M3U потока
    elif item['type'] == 'm3u':
        channel_name = item['name']
        play_number = 0
        try:
            play_number= int(channel_name[:3])
        except ValueError:
            pass
        
        stream_url = item['url']
        
        # Варианты запуска потокового видео/аудио
        # Вариант 1: Использовать VLC (рекомендуется)
        try:
            #subprocess.Popen(['vlc', stream_url])
            print('PLAY_' + str(play_number))
            if play_number>0:
            	reply = Webr.udpSend('PLAY_' + str(play_number))
            	print(reply)
            return True, f"Запущен канал: {channel_name} в VLC"
        except FileNotFoundError:
            pass
        
        # Вариант 2: Использовать mpv
        try:
            subprocess.Popen(['mpv', stream_url])
            return True, f"Запущен канал: {channel_name} в mpv"
        except FileNotFoundError:
            pass
        
        # Вариант 3: Использовать xdg-open (откроет в браузере, если это HLS)
        try:
            if stream_url.endswith('.m3u8') or 'm3u8' in stream_url:
                subprocess.Popen(['xdg-open', stream_url])
                return True, f"Открыт поток: {channel_name} в браузере"
        except:
            pass
        
        return False, f"Не удалось запустить канал {channel_name}. Установите VLC или mpv."
    
    return False, "Неизвестный тип элемента"

@app.route('/')
def index():
    items = get_all_items()
    return render_template('index.html', items=items)

@app.route('/launch', methods=['POST'])
def launch():
    data = request.get_json()
    item_name = data.get('name')
    item_type = data.get('type')
    
    if not item_name or not item_type:
        return jsonify({'success': False, 'error': 'Не указан элемент для запуска'}), 400
    
    # Находим элемент в списке
    items = get_all_items()
    selected_item = None
    
    for item in items:
        if item['name'] == item_name and item['type'] == item_type:
            selected_item = item
            break
    
    if not selected_item:
        return jsonify({'success': False, 'error': 'Элемент не найден'}), 404
    
    success, message = launch_item(selected_item)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'error': message}), 500

# Daemon class
class RemoteDaemon(Daemon):

    def run(self):
        global portHttp

        log.init('radio')
        progcall = str(sys.argv)
        log.message(progcall, log.DEBUG)
        log.message('web Remote control running pid ' + str(os.getpid()), log.INFO)
        signal.signal(signal.SIGHUP,signalHandler)

        portHttp=config.getRemoteWebPort()
        app.run(debug=False, host='0.0.0.0', port=portHttp) # debug=True - второй раз запускает прогу!
        log.message("web listen portHttp " + str(portHttp), log.DEBUG)

    # Status enquiry
    def status(self):
        # Get the pid from the pidfile
        try:
            pf = open(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if not pid:
            message = "web Remote control status: not running"
            log.message(message, log.INFO)
            print(message)
        else:
            message = "web Remote control running pid " + str(pid)
            log.message(message, log.INFO)
            print(message)
        return

            


# Print usage
def usage():
    print("Usage: sudo %s start|stop|status|restart|nodaemon")
    sys.exit(2)


if __name__ == '__main__':

    #if pwd.getpwuid(os.geteuid()).pw_uid > 0:
    #    print("This program must be run with sudo or root permissions!")
    #    usage()

    daemon = RemoteDaemon(pidfile)
    if len(sys.argv) >= 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'nodaemon' == sys.argv[1]:
            daemon.nodaemon()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        elif 'status' == sys.argv[1]:
            daemon.status()
        else:
            print("Unknown command: " + sys.argv[1])
            usage()
        sys.exit(0)
    else:
        usage()
