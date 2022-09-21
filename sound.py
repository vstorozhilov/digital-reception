import json
import time

from PyQt5 import *
import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtMultimedia import QSound
import datetime
import schedule

# class SheduleWorker(QObject):
#
#     date_changed = pyqtSignal()
#
#     def time_tracker(self):
#         schedule.every().day.at("10:13").do(self.date_changed.emit)
#         while True:
#             schedule.run_pending()
#             time.sleep(60)
#
# class Handler(QObject):
#
#     run = pyqtSignal()
#
#     def date_changed(self):
#         print(datetime.datetime.now())
#
# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     sw = SheduleWorker()
#     h = Handler()
#     thread = QThread()
#     sw.moveToThread(thread)
#     sw.date_changed.connect(h.date_changed)
#     h.run.connect(sw.time_tracker)
#     thread.start()
#     h.run.emit()
#     app.exec_()

import re
import os

with open('app.log', 'r+')  as f:
    while True:
        line = f.readline()
        if line == "":
            break
        if re.search("- ERROR -", line, re.MULTILINE):
            exit()
    f.truncate(0)

    #time.sleep(100)

