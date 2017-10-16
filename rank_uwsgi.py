import sys
import os

APP_PATH = '/home/rank/back'
sys.path.insert(0, APP_PATH)
os.chdir(APP_PATH)

from rank import app as application
