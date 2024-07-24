# web_interface.py
from flask import Flask, render_template, request, redirect, url_for, jsonify
import threading, subprocess, os, html, signal
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

logs = []
def ansi_to_html(text):
    ansi_to_css = {
        "\033[0;30m": "ansi30",
        "\033[0;31m": "ansi31",
        "\033[0;32m": "ansi32",
        "\033[0;33m": "ansi33",
        "\033[0;34m": "ansi34",
        "\033[0;35m": "ansi35",
        "\033[0;36m": "ansi36",
        "\033[0;37m": "ansi37",
        "\033[1;30m": "ansi90",
        "\033[1;31m": "ansi91",
        "\033[1;32m": "ansi92",
        "\033[1;33m": "ansi93",
        "\033[1;34m": "ansi94",
        "\033[1;35m": "ansi95",
        "\033[1;36m": "ansi96",
        "\033[1;37m": "ansi97",
        "\033[0m": "reset",
    }

    for ansi_code, css_class in ansi_to_css.items():
        if css_class == "reset":
            text = text.replace(ansi_code, "</span>")
        else:
            text = text.replace(ansi_code, f'<span class="{css_class}">')
            
    return text

@app.route('/')
def index():
    log_file_path = './logs.log'  
    if os.path.exists(log_file_path):
        with open(log_file_path, 'r', encoding='utf-8') as file:
            logs = file.read()
        logs = html.escape(logs)
        logs = logs.replace('ERROR', '<span class="log-error">ERROR</span>')
        logs = logs.replace('INFO', '<span class="log-info">INFO</span>')
        logs = logs.replace('WARNING', '<span class="log-warning">WARNING</span>')
    else:
        logs = "Log file not found."
    return render_template('index.html', logs=logs)

def read_output(pipe, output_type, process_done):
    try:
        while True:
            line = pipe.readline()
            if not line:
                break
            formatted_line = ansi_to_html(f'[{output_type}] {line.strip()}') + '<br>'
            socketio.emit('output', {'data': formatted_line})
    except Exception as e:
        print(f"Error reading output: {e}")
    finally:
        process_done[output_type] = True
        if all(process_done.values()):
            socketio.emit('output', {'data': '<br><strong>Process finished</strong><br>'})

@app.route('/execute', methods=['POST'])
def execute_command():
    command = request.json.get('command')
    if command:
        try:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            process_done = {'stdout': False, 'stderr': False}

            threading.Thread(target=read_output, args=(process.stdout, 'stdout', process_done)).start()
            threading.Thread(target=read_output, args=(process.stderr, 'stderr', process_done)).start()

            process.wait()
            return jsonify({'status': 'done'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'No command provided'}), 400

@app.route('/kill', methods=['POST'])
def kill_app():
    try:
        try:
            os.kill(os.getpid(), signal.SIGINT)
        except OSError as e:
            return jsonify({'status': e})
        
        return jsonify({'status': 'server shutting down'})
    except Exception as e:
        print(f"Error in /kill route: {e}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/logs')
def get_logs():
    log_file_path = './logs.log'
    if os.path.exists(log_file_path):
        with open(log_file_path, 'r', encoding='utf-8') as file:
            logs = file.read()
        logs = html.escape(logs)
        logs = logs.replace('ERROR', '<span class="log-error">ERROR</span>')
        logs = logs.replace('INFO', '<span class="log-info">INFO</span>')
        logs = logs.replace('WARNING', '<span class="log-warning">WARNING</span>')
    else:
        logs = "Log file not found."
    return logs

@app.route('/clear', methods=['POST'])
def clear_logs():
    global logs
    logs = []
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=2137)