import sys, time
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5.QtWidgets import QScrollBar, QSplitter, QTableWidgetItem, QTableWidget, QComboBox, QVBoxLayout, QGridLayout, \
    QDialog, QWidget, QPushButton, QApplication, QMainWindow, QAction, QMessageBox, QLabel, QTextEdit, QProgressBar, \
    QLineEdit, QHBoxLayout
from PyQt5.QtCore import QCoreApplication
import socket
from threading import Thread
from socketserver import ThreadingMixIn

conn = None


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.widget = QWidget()
        self.setCentralWidget(self.widget)

        self.h_lay = QHBoxLayout(self)
        self.widget.setLayout(self.h_lay)

        v_lay = QVBoxLayout()
        self.h_lay.addLayout(v_lay)

        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        v_lay.addWidget(self.chat)

        h_lay = QHBoxLayout()
        v_lay.addLayout(h_lay)

        self.chat_message = QLineEdit(self)
        h_lay.addWidget(self.chat_message)

        self.btnSend = QPushButton("Отправить")
        self.btnSend.clicked.connect(self.send)
        h_lay.addWidget(self.btnSend)

        self.setWindowTitle("Электронная приемная ВИТ ЭРА")

    def send(self):
        text = self.chat_message.text()
        self.chat.append("Вы: " + text)
        global conn
        conn.send(text.encode("utf-8"))
        self.chat_message.setText("")


class ServerThread(Thread):
    def __init__(self, window):
        Thread.__init__(self)
        self.window = window

    def run(self):
        TCP_IP = '0.0.0.0'
        TCP_PORT = 80
        BUFFER_SIZE = 20
        tcpServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcpServer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tcpServer.bind((TCP_IP, TCP_PORT))
        threads = []

        tcpServer.listen(4)
        while True:
            print("Multithreaded Python server : Waiting for connections from TCP clients...")
            global conn
            (conn, (ip, port)) = tcpServer.accept()
            print(conn, (ip, port))
            newthread = ClientThread(ip, port, window)
            newthread.start()
            threads.append(newthread)

        for t in threads:
            t.join()


class ClientThread(Thread):
    def __init__(self, ip, port, window):
        Thread.__init__(self)
        self.window = window
        self.ip = ip
        self.port = port
        window.chat.append("[+] Пользователь " + ip + ":" + str(port) + " присоединился")

    def run(self):
        while True:
            # (conn, (self.ip,self.port)) = serverThread.tcpServer.accept()
            global conn
            data = conn.recv(2048)
            window.chat.append(self.ip + ":" + str(self.port) + ": " + data.decode("utf-8"))
            print(data)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = Window()
    serverThread = ServerThread(window)
    serverThread.start()
    window.show()

    sys.exit(app.exec_())
