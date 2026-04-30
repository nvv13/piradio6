#!/usr/bin/env python3
# app.py
from flask import Flask, render_template, request, jsonify
import sys
import os
import signal
import subprocess
import glob
import re

#from web_daemon import Daemon
#from log_class import Log
#from web_config_class import Configuration
#from web_send_class import Webrsend

app = Flask(__name__)

#log = Log()
#Webr = Webrsend()

#config = Configuration()
pidfile = '/var/run/web_remote.pid'

# MPD files
MpdLibDir = "/var/lib/mpd"
PlaylistsDirectory =  MpdLibDir + "/playlists"
PlaylistsFile='Radio.m3u'
MusicDirectory =  MpdLibDir + "/music"
# Путь к директории с файлами (измените на свой)
FILES_DIRECTORY = PlaylistsDirectory

# Radio files
RadioLibDir = "/var/lib/radiod"
CurrentStationFile = RadioLibDir + "/current_station"  # номер тек станции в списке
SourceNameFile = RadioLibDir + "/source_name"  # имя списка 
VolumeFile = RadioLibDir + "/volume"


# Get the Value from a namefile
def getFileValue(namefile):
    Value = ''
    if os.path.isfile(namefile):
        try:
            f = open(namefile,'r')
            Value = f.readline().rstrip('\n').rstrip('\r')
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
    global PlaylistsFile    
    channels = []
    #m3u_file=PlaylistsDirectory+'/'+getFileValue(SourceNameFile)+'.m3u'
    m3u_file=PlaylistsDirectory+'/'+PlaylistsFile
    print(m3u_file)
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
                # Используем имя файла как название
                nameFile=os.path.basename(line)
                #if nameFile.rfind(".")>0:
                #    nameFile=nameFile[:nameFile.rfind(".")]
                channel_name = ('000'+str(indP))[-3:]+' '+nameFile
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
    items.append({
            'name': 'VOLUMEUP',
            'type': 'cntrl',
            'path': 'KEY_VOLUMEUP'
        })
    items.append({
            'name': 'VOLUMEDOWN',
            'type': 'cntrl',
            'path': 'KEY_VOLUMEDOWN'
        })
    items.append({
            'name': 'MUTE',
            'type': 'cntrl',
            'path': 'KEY_MUTE'
        })
    items.append({
            'name': 'CHANNELUP',
            'type': 'cntrl',
            'path': 'KEY_CHANNELUP'
        })
    items.append({
            'name': 'CHANNELDOWN',
            'type': 'cntrl',
            'path': 'KEY_CHANNELDOWN'
        })
    items.append({
            'name': 'MENU',
            'type': 'cntrl',
            'path': 'KEY_MENU'
        })
    items.append({
            'name': 'UP',
            'type': 'cntrl',
            'path': 'KEY_UP'
        })
    items.append({
            'name': 'DOWN',
            'type': 'cntrl',
            'path': 'KEY_DOWN'
        })
    items.append({
            'name': 'LEFT',
            'type': 'cntrl',
            'path': 'KEY_LEFT'
        })
    items.append({
            'name': 'RIGHT',
            'type': 'cntrl',
            'path': 'KEY_RIGHT'
        })
    items.append({
            'name': 'OK',
            'type': 'cntrl',
            'path': 'KEY_OK'
        })
    items.append({
            'name': 'INFO',
            'type': 'cntrl',
            'path': 'KEY_INFO'
        })
    items.append({
            'name': 'EXIT',
            'type': 'cntrl',
            'path': 'KEY_EXIT'
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
    cur_station='40' #getFileValue(CurrentStationFile)
    items.append({
            'name': cur_station,
            'type': 'cur_station',
            'position': cur_station
        })
    
    # Добавляем значение громкости
    cur_volume='40' #getFileValue(VolumeFile)
    items.append({
            'name': cur_volume,
            'type': 'cur_volume',
            'volume': cur_volume
        })
    
    return items

def launch_item(item):
    """Запускает файл или M3U поток"""
    global PlaylistsFile    
    # Запуск обычного файла
    if item['type'] == 'file':
        file_path = item['path']
        
        if not os.path.exists(file_path):
            return False, "Файл не найден"
        PlaylistsFile=item['name']
        print('PLAYLIST:' + PlaylistsFile[0:-4])
        #reply = Webr.udpSend('PLAYLIST:' + PlaylistsFile[0:-4])
        #print(reply)
        return True, f"Выбран список: {PlaylistsFile}"
    
    # Запуск M3U потока
    elif item['type'] == 'cntrl':
        cur_station='4' #getFileValue(CurrentStationFile)
        cur_volume='50' #getFileValue(VolumeFile)
        return True, f"station:{cur_station} volume:{cur_volume}"

    # Запуск M3U потока
    elif item['type'] == 'm3u':
        channel_name = item['name']
        play_number = 0
        try:
            play_number= int(channel_name[:3])
        except ValueError:
            pass
        
        stream_url = item['url']
        
        try:
            #subprocess.Popen(['vlc', stream_url])
            print('PLAY_' + str(play_number))
            #if play_number>0:
            #	reply = Webr.udpSend('PLAY_' + str(play_number))
            #	print(reply)
            return True, f"Запущен канал: {channel_name} в VLC"
        except FileNotFoundError:
            pass
        
        return False, f"Не удалось запустить канал {channel_name}. Установите VLC или mpv."
    
    return False, "Неизвестный тип элемента"

@app.route('/')
def index():
    items = get_all_items()
    return render_template('index.html', items=items)

@app.route('/undefined')
def index2():
    items = get_all_items()
    return render_template('index.html', items=items)


@app.route('/refresh-m3u', methods=['POST'])
def refresh_m3u():
    """Принудительно обновляет только M3U список"""
    
    try:
        # Получаем свежие каналы
        channels = get_m3u_channels()
        
        return jsonify({
            'success': True,
            'items': [{'name': ch['name'], 'type': 'm3u'} for ch in channels],
            'count': len(channels)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) # debug=True - второй раз запускает прогу!

    #if pwd.getpwuid(os.geteuid()).pw_uid > 0:
    #    print("This program must be run with sudo or root permissions!")
    #    usage()

