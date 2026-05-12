#!/usr/bin/env python3
# web_remote.py
from flask import Flask, render_template, request, jsonify
import sys
import os
import signal
import subprocess
import glob
import re
import time

#from web_daemon import Daemon
#from log_class import Log
#from web_config_class import Configuration
#from web_send_class import Webrsend

app = Flask(__name__)

playlists = []
tracks = []
status = {}
cur_volume=20

#log = Log()
#Webr = Webrsend()

#config = Configuration()
pidfile = '/var/run/web_remote.pid'
web_port=5000

# MPD files
MpdLibDir = "/var/lib/mpd"
PlaylistsDirectory =  MpdLibDir + "/playlists"
MusicDirectory =  MpdLibDir + "/music"


def run_mpc_command(command):
    """Выполнить команду MPC и вернуть результат"""
    try:
        result = subprocess.run(['mpc'] + command, 
                               capture_output=True, 
                               text=True, 
                               timeout=10)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timeout", 1
    except FileNotFoundError:
        return "", "MPC not found. Please install mpc.", 1
    except Exception as e:
        return "", str(e), 1

def get_lsplaylist():
    """Получить список плейлистов"""
    global playlists
    output, error, code = run_mpc_command(['lsplaylist'])
    if code != 0:
        return [], error
    playlists = []
    lines = output.split('\n')
    for i, line in enumerate(lines):
        if line.strip():
            playlists.append({
                'number': i+1,
                'name': line.strip(),
                'type':'file'
            })
    return playlists, None


def get_playlist():
    """Получить список треков из плейлиста"""
    global tracks
    output, error, code = run_mpc_command(['playlist'])
    if code != 0:
        return [], error
    tracks = []
    lines = output.split('\n')
    for i, line in enumerate(lines):
        if line.strip():
            tracks.append({
                'number': i+1,
                'name': line.strip(),
                'type':'m3u'
            })
    return tracks, None

def get_current_status():
    """Получить текущий статус MPD"""
    global status
    output, error, code = run_mpc_command(['status'])
    if code != 0:
        return None, error
    status = {}
    lines = output.split('\n')
    for i, line in enumerate(lines):
        if i==0 and 'volume' not in line:
            status['title'] = line.strip()
        if i==1 :
            status['state'] = line.strip()
        if (i==2 or (i==0 and 'volume' in line) ) and ':' in line :
            for lin in line.split('   '):
                #print(lin)
                key1, value1 = lin.split(':', 1)
                status[key1.strip()] = value1.strip()
    if 'state' in status and 'title' in status:
        tstat=status['state']
        #print(tstat)
        if '#' in tstat and '/' in tstat:
            numpos=tstat[tstat.find('#')+1:tstat.find('/')]
            status['title']=numpos+' > '+status['title']+' < '
    return status, None

def get_volume():
    """Получить текущую громкость"""
    global status
    global cur_volume
    if status and 'volume' in status:
        volume = status['volume']
        # Извлекаем числовое значение из строки вроде "volume: 75%"
        match = re.search(r'(\d+)%', volume)
        if match:
            x_volume=int(match.group(1))
            if x_volume>0:
                cur_volume=x_volume
            return x_volume
    return 0


def get_all_items():
    """Объединяет файлы и M3U каналы в один список"""
    items = []
    
    # Список m3u файлов
    get_lsplaylist()
    for flist in playlists:
        items.append({
            'name': flist['name'],
            'type': 'file',
            'number': str(flist['number'])
        })
    # Добавляем каналы из текущего M3U (если он загружен)
    get_playlist()
    for track in tracks:
        #print(track['name'])
        items.append({
            'name': track['name'],
            'type': 'm3u',
            'number': str(track['number'])
        })
    
    items.append({
            'name': 'PLAY',
            'type': 'cntrl',
            'number': '1'
        })
    items.append({
            'name': 'PAUSE',
            'type': 'cntrl',
            'number': '2'
        })
    items.append({
            'name': 'STOP',
            'type': 'cntrl',
            'number': '3'
        })
    items.append({
            'name': 'NEXT',
            'type': 'cntrl',
            'number': '4'
        })
    items.append({
            'name': 'PREV',
            'type': 'cntrl',
            'number': '5'
        })
    items.append({
            'name': 'VOLUME UP',
            'type': 'cntrl',
            'number': '6'
        })
    items.append({
            'name': 'VOLUME DOWN',
            'type': 'cntrl',
            'number': '7'
        })
    items.append({
            'name': 'MUTE',
            'type': 'cntrl',
            'number': '8'
        })
    
    return items

def launch_item(item):
    """Запускает файл или M3U поток"""
    # Загрузка нового списка
    print(item)
    if item['type'] == 'file':
        output, error, code = run_mpc_command(['clear'])
        time.sleep(0.2) # Sleep for 0.5 seconds
        output, error, code = run_mpc_command(['update'])
        time.sleep(0.2) # Sleep for 0.5 seconds
        output, error, code = run_mpc_command(['load',item['name']])
        time.sleep(0.2) # Sleep for 0.5 seconds
        return True, f"Выбран список: {item['name']}"
    
    # Запуск M3U потока
    elif item['type'] == 'cntrl':
        action_number = 0
        try:
            action_number= int(item['number'])
        except ValueError:
            pass
        """Управление MPD через кнопки"""
        try:
            if action_number == 1:
                output, error, code = run_mpc_command(['play'])
            elif action_number == 2:
                output, error, code = run_mpc_command(['pause'])
            elif action_number == 3:
                output, error, code = run_mpc_command(['stop'])
            elif action_number == 4:
                output, error, code = run_mpc_command(['next'])
            elif action_number == 5:
                output, error, code = run_mpc_command(['prev'])
            elif action_number == 6:
                output, error, code = run_mpc_command(['volume', '+5'])
            elif action_number == 7:
                output, error, code = run_mpc_command(['volume', '-5'])
            elif action_number == 8:
                if get_volume() == 0:
                    output, error, code = run_mpc_command(['volume', str(cur_volume)])
                else:
                    output, error, code = run_mpc_command(['volume', '0'])
            else:
                return jsonify({'error': 'Unknown action'}), 400
            
            if code == 0:
                return True, f"Command executed successfully"
            else:
                return False, f"error: Command failed"
                
        except Exception as e:
            return False, f"error: {str(e)}"
        return True, f"station:{cur_station} volume:{cur_volume}"

    # Запуск M3U потока
    elif item['type'] == 'm3u':
        track_number = 0
        try:
            track_number= int(item['number'])
        except ValueError:
            pass
        """Воспроизвести конкретный трек по номеру"""
        try:
            output, error, code = run_mpc_command(['play', str(track_number)])
            if code == 0:
                return True, f"Playing track {track_number}"
            else:
                return False, f"Failed to play track № {track_number}."
        except Exception as e:
            return False, f"error {str(e)}."
        
        return False, f"Не удалось запустить № {track_number}."
    
    return False, "Неизвестный тип элемента"

@app.route('/')
def index():
    items = get_all_items()
    return render_template('index.html', items=items)


@app.route('/refresh-m3u', methods=['POST'])
def refresh_m3u():
    """Принудительно обновляет только M3U список"""
    
    try:
        # Получаем свежие каналы
        time.sleep(0.1) # Sleep for 1 seconds
        get_playlist()
        print(len(tracks))
        return jsonify({
            'success': True,
            'items': [{'name': ch['name'], 'type': 'm3u','number': str(ch['number'])} for ch in tracks],
            'count': len(tracks)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/launch', methods=['POST'])
def launch():
    data = request.get_json()
    #print(data)
    item_name = data.get('name')
    item_type = data.get('type')
    #item_number = data.get('number')
    
    if not item_name or not item_type:
        return jsonify({'success': False, 'error': 'Не указан элемент для запуска'}), 400
   
    success, message = launch_item(data)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'error': message}), 500

@app.route('/status')
def get_status():
    """Получить текущий статус MPD"""
    status, error = get_current_status()
    if error:
        return jsonify({'error': error}), 500
    volume = get_volume()
    return jsonify({
        'status': status,
        'volume': volume
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=web_port) # debug=True - второй раз запускает прогу!

    #if pwd.getpwuid(os.geteuid()).pw_uid > 0:
    #    print("This program must be run with sudo or root permissions!")
    #    usage()

