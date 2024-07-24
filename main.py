# main.py
import threading
import subprocess
import sys

def start_flask():
    subprocess.run([sys.executable, 'web_interface.py'])

threading.Thread(target=start_flask).start()
