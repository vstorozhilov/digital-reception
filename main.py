import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtMultimedia import QSound
from database import Database
import logging
import json
import psutil
import schedule
import time
import re

DB_HOST = None
DB_PORT = None
DB_USER = None
DB_NAME = None
database = None
ETHERNET_ADDR = None

class AcceptCompleteButton(QPushButton):

    def __init__(self, name, parentListItem):
        super(AcceptCompleteButton, self).__init__(name)
        self.parentListItem = parentListItem
        if name=='Завершить приём':
            self.setStyleSheet(
                               "color : green;"
                               # "border :2px solid green;"
                               "padding: 7px 7px 7px 7px;"
                               "font-size: 18px; font-weight: bold;"
                               )
            self.clicked.connect(self.complete_click)
        else:
            self.clicked.connect(self.accept_click)

    def accept_click(self):
        self.parentListItem.event_visitors_window.logger.info("Нажата кнопка \"принять посетителя\"")
        parentListWidget = self.parentListItem.listWidget()
        widget = parentListWidget.itemWidget(self.parentListItem)
        data = self.parentListItem.event_visitors_window.data
        data['fio'] = widget.layout().itemAt(0).widget().text()
        data['status'] = self.parentListItem.event_visitors_window.visitor_status_map['Завершить приём']
        data['nid'] = self.parentListItem.data(Qt.UserRole)
        if self.parentListItem.event_visitors_window.update_visitor_to_database():
            self.parentListItem.event_visitors_window.show_database_error_window(2)
        data.clear()

    def complete_click(self):
        self.parentListItem.event_visitors_window.logger.info("Нажата кнопка \"завершить визит\"")
        data = self.parentListItem.event_visitors_window.data
        parentListWidget = self.parentListItem.listWidget()
        widget = parentListWidget.itemWidget(self.parentListItem)
        data['fio'] = widget.layout().itemAt(0).widget().text()
        data['status'] = self.parentListItem.event_visitors_window.visitor_status_map['_']
        data['nid'] = self.parentListItem.data(Qt.UserRole)
        if self.parentListItem.event_visitors_window.update_visitor_to_database():
            self.parentListItem.event_visitors_window.show_database_error_window(2)
        data.clear()

    def remove_click(self):
        self.parentListItem.event_visitors_window.logger.info("Нажата кнопка \"удалить визит\"")
        data = self.parentListItem.event_visitors_window.data
        parentListWidget = self.parentListItem.listWidget()
        widget = parentListWidget.itemWidget(self.parentListItem)
        data['fio'] = widget.layout().itemAt(0).widget().text()
        data['status'] = self.parentListItem.event_visitors_window.visitor_status_map['Удалён']
        data['nid'] = self.parentListItem.data(Qt.UserRole)
        if self.parentListItem.event_visitors_window.update_visitor_to_database():
            self.parentListItem.event_visitors_window.show_database_error_window(2)
        data.clear()


class AddVisitWindow(QDialog):

    def __init__(self, row=None):
        super(AddVisitWindow, self).__init__(None)
        l1 = QLabel("Фамилия И.О.")
        l1.setFont(QFont("Roboto", 14))
        text_edit_1 = QTextEdit()
        text_edit_1.setMinimumHeight(40)
        text_edit_1.setMinimumWidth(200)
        text_edit_1.setFont(QFont("Roboto", 12))
        vbox = QVBoxLayout()
        vbox.addWidget(l1)
        vbox.addWidget(text_edit_1)
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        vbox.addWidget(buttonBox)
        self.setLayout(vbox)
        self.setWindowIcon(QIcon("logo.ico"))
        self.setWindowTitle('Добавить посещение')


class AddMeetingWindow(QDialog):

    def __init__(self, row=None):
        super(AddMeetingWindow, self).__init__(None)
        l1 = QLabel("Время мероприятия")
        l1.setFont(QFont("Roboto", 14))
        l2 = QLabel("Описание")
        l2.setFont(QFont("Roboto", 14))
        l3 = QLabel("Ответственный")
        l3.setFont(QFont("Roboto", 14))

        date_time_field = QTimeEdit()
        date_time_field.setFont(QFont("Roboto", 12))
        date_time_field.setMinimumHeight(40)
        date_time_field.setMinimumWidth(200)
        text_edit_1 = QTextEdit()
        text_edit_1.setMinimumHeight(40)
        text_edit_1.setMinimumWidth(200)
        text_edit_1.setFont(QFont("Roboto", 12))
        text_edit_2 = QTextEdit()
        text_edit_2.setMinimumHeight(40)
        text_edit_2.setMinimumWidth(200)
        text_edit_2.setFont(QFont("Roboto", 12))

        fbox = QFormLayout()

        fbox.addRow(l1, date_time_field)
        fbox.addRow(l2, text_edit_1)
        fbox.addRow(l3, text_edit_2)
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        fbox.addWidget(buttonBox)
        self.setWindowTitle("Добавить мероприятие")
        self.setLayout(fbox)
        self.setWindowIcon(QIcon("logo.ico"))

class MainWindow(QWidget):

    def __init__(self, date: str, logger):
        super(MainWindow, self).__init__(None)
        self.date = date
        self.data = {}
        self.logger = logger
        database.notified.connect(self.database_changed)
        hbox_events = QHBoxLayout()
        add_event_button = QPushButton("Добавить мероприятие")
        edit_event_button = QPushButton("Редактировать мероприятие")
        return_button = QPushButton("К календарю")
        update_events_button = QPushButton("Обновить")
        update_events_button.clicked.connect(self.update_event_table)
        return_button.clicked.connect(self.return_button_clicked)
        add_event_button.clicked.connect(self.add_event_button_clicked)
        edit_event_button.clicked.connect(self.edit_event_wrapper)
        hbox_events.addWidget(return_button)
        hbox_events.addWidget(edit_event_button)
        hbox_events.addWidget(update_events_button)
        hbox_events.addStretch()
        hbox_events.addWidget(add_event_button)
        self.table = QTableWidget(0, 4)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.cellClicked.connect(self.delete_event)
        self.table.cellDoubleClicked.connect(self.edit_event)

        self.table.setHorizontalHeaderLabels(["Время",
                                         "Описание",
                                         "Ответственный",
                                         "Удалить"])

        vbox_events = QVBoxLayout()
        vbox_events.addLayout(hbox_events)

        vbox_events.addWidget(self.table)
        vbox_main = QVBoxLayout()
        vbox_main.addLayout(vbox_events)
        if (QDate.currentDate().toString("dd.MM.yyyy") == date):
            self.mute = False
            self.visitor_status_map = {
                "Принять" : 0,
                "Завершить приём" : 1,
                "_" : 2,
                "Удалён" : 3
            }
            hbox_visitors = QHBoxLayout()
            update_visitors_button = QPushButton("Обновить")
            add_button = QPushButton("Добавить посещение")
            edit_button = QPushButton("Редактировать посещение")
            self.mute_button = QPushButton()
            self.mute_button.clicked.connect(self.mute_button_clicked)
            add_button.clicked.connect(self.add_visitor_button_clicked)
            edit_button.clicked.connect(self.edit_visitor_button_clicked)
            update_visitors_button.clicked.connect(self.update_visitors_button_clicked)
            hbox_visitors.addWidget(edit_button)
            hbox_visitors.addWidget(update_visitors_button)
            hbox_visitors.addWidget(self.mute_button)
            self.mute_button.setIcon(QIcon('mute.ico'))
            hbox_visitors.addStretch()
            hbox_visitors.addWidget(add_button)
            self.list_visitors = QListWidget()
            self.list_visitors.setSelectionMode(QAbstractItemView.ExtendedSelection)
            self.list_visitors.itemDoubleClicked.connect(self.edit_visitor_button_clicked)
            self.list_visitors.setStyleSheet("QListWidget::item:selected{ background-color: #97cdfb }")
            vbox_visitors = QVBoxLayout()
            vbox_visitors.addLayout(hbox_visitors)
            vbox_visitors.addWidget(self.list_visitors)
            vbox_main.addLayout(vbox_visitors)

        self.setLayout(vbox_main)

    def mute_button_clicked(self):
        if self.mute == False:
            self.mute = True
            self.mute_button.setIcon(QIcon('mute_1.ico'))
        else:
            self.mute = False
            self.mute_button.setIcon(QIcon('mute.ico'))

    def draw_calendar(self):
        calendar = self.window().tabs.widget(0)
        calendar.data = database.get_statistic_by_days()
        if calendar.data is not None:
            calendar.updateCells()

    def show_database_error_window(self, frame_fraction: int):
        error_window = QMessageBox(text="Ошибка базы данных")
        error_window.setWindowTitle("Ошибка")
        geometry = self.window().geometry()
        error_window.setGeometry(int(geometry.x() + (2 * geometry.width()) / 4),
                                 int(geometry.y() + (frame_fraction * geometry.height()) / 4),
                                 int(geometry.width() / 4),
                                 int(geometry.height() / 4))
        error_window.exec_()


    def show_event_changes(self, row=None):
        data = self.data

        table = self.table

        if row is not None:
            current_row = row
        else:
            current_row = table.rowCount()
            table.insertRow(current_row)

        datetime_item = QTableWidgetItem()
        datetime_item.setText(self.date + ' ' + data['time'])
        table.setItem(current_row, 0, datetime_item)
        desc_item = QTableWidgetItem()
        desc_item.setText(data['description'])
        table.setItem(current_row, 1, desc_item)
        desc_item = QTableWidgetItem()
        desc_item.setText(data['responsible'])
        table.setItem(current_row, 2, desc_item)
        delete_button_item = QTableWidgetItem()
        delete_button_item.setText("x")
        delete_button_item.setBackground(QColor(255, 0, 0))
        delete_button_item.setTextAlignment(Qt.AlignCenter)
        delete_button_item.setForeground(QColor(255, 255, 255))
        delete_button_item.setFont(QFont("Roboto", 12))
        delete_button_item.setData(Qt.UserRole, data['nid'])
        table.setItem(current_row, 3, delete_button_item)

    def edit_event_wrapper(self):
        self.logger.info("Нажата кнопка: \"редактировать событие\"")
        if (len(self.table.selectedRanges())) == 1:
            row = self.table.currentRow()
            #self.table.setCurrentItem(None)
            self.edit_event(row, None)
        else:
            global error_window
            self.logger.info('Ошибка: не выбрано мероприятие для редактирования')
            error_window = QMessageBox(text="Выберете одно мероприятие")
            error_window.setWindowTitle("Ошибка")
            geometry = self.window().geometry()
            error_window.setGeometry(int(geometry.x() + geometry.width() / 4),
                                         int(geometry.y() + geometry.height() / 4),
                                         int(geometry.width() / 4),
                                         int(geometry.height() / 4))

            error_window.exec_()

    def edit_event(self, row, __):
        global new_window
        """update_event (Database class)"""
        self.logger.info("Начато редактирование события")
        new_window = AddMeetingWindow(row=row)
        new_window.main_window = self
        new_window.layout().itemAt(0, 1).widget().setTime(QTime.fromString(self.table.item(row, 0).text().split(' ')[1], "HH:mm"))
        new_window.layout().itemAt(1, 1).widget().setText(self.table.item(row, 1).text())
        new_window.layout().itemAt(2, 1).widget().setText(self.table.item(row, 2).text())
        geometry = self.window().geometry()
        new_window.setGeometry(int(geometry.x() +  geometry.width() / 4),
                               int(geometry.y() +  geometry.height() / 4),
                               int(geometry.width() / 4),
                               int(geometry.height() / 4))
        new_window.exec_()
        if new_window.result():
            data = self.data
            data['time'] = new_window.layout().itemAt(0, 1).widget().time().toString("HH:mm")
            data['description'] = new_window.layout().itemAt(1, 1).widget().toPlainText()
            data['responsible'] = new_window.layout().itemAt(2, 1).widget().toPlainText()
            data['nid'] = self.table.item(row, 3).data(Qt.UserRole)
            if self.update_event_to_database() != 0:
                self.show_database_error_window(1)
            data.clear()
        self.table.selectionModel().clearSelection()

    def delete_event(self, row, column):
        self.logger.info("Нажата кнопка: \"удалить событие\"")
        if column == 3:
            data = self.data
            data['nid'] = self.table.item(row, 3).data(Qt.UserRole)
            if self.delete_event_from_database() != 0:
                self.show_database_error_window(1)
            data.clear()

    def update_event_table(self):
        self.logger.info("Обновление таблицы событий")
        self.table.setRowCount(0)
        date = self.date
        # TODO: correct events selection by day
        new_data = database.get_events_by_date(date)
        if new_data is None:
            self.show_database_error_window(1)
            return

        data = self.data

        for event in new_data:
            data['nid'] = event['nid']
            data['time'] = event['meettime']
            data['description'] = event['description']
            data['responsible'] = event['responsible']
            self.show_event_changes()

        data.clear()
        self.draw_calendar()

    def update_visitors_button_clicked(self, nid=None):
        self.logger.info("Обновление списка посетителей")
        new_data = database.get_active_visitors()

        if new_data is None:
            self.show_database_error_window(2)
            return
        current_row = 0
        data = self.data
        self.list_visitors.clear()

        for visitor in new_data:
            data['fio'] = new_data[current_row]['fio']
            data['status'] = new_data[current_row]['status']
            data['nid'] = new_data[current_row]['nid']
            wid = QListWidgetItem()
            wid.event_visitors_window = self
            wid.setData(Qt.UserRole, data['nid'])
            widget = self.create_list_visitors_widget(wid)
            wid.setSizeHint(widget.minimumSizeHint())
            self.list_visitors.addItem(wid)
            self.list_visitors.setItemWidget(wid, widget)
            if nid == data['nid']:
                wid.setSelected(True)
            self.show_visitors_changes(widget)
            current_row += 1

        data.clear()

    def database_changed(self, channel, message):
        table, action, nid, ip_with_mask = message.split(";")
        ip = ip_with_mask.split('/')[0]
        if table=='events':
            self.update_event_table()
        elif table=='visitors' and self.date == QDate.currentDate().toString("dd.MM.yyyy"):
            if ip != ETHERNET_ADDR and self.mute == False:
                QSound.play('sound1.wav')
                self.update_visitors_button_clicked(int(nid))
            else:
                self.update_visitors_button_clicked()

    def return_button_clicked(self):
        self.table.setRowCount(0)
        self.window().to_calendar()

    def add_event_button_clicked(self):
        self.logger.info("Нажата кнопка: \"добавить событие\"")
        global add_event_window
        add_event_window = AddMeetingWindow()
        add_event_window.main_window = self
        geometry = self.window().geometry()
        add_event_window.setGeometry(int(geometry.x() +  geometry.width() / 4),
                               int(geometry.y() +  geometry.height() / 4),
                               int(geometry.width() / 4),
                               int(geometry.height() / 4))
        add_event_window.exec_()
        if add_event_window.result():
            data = self.data
            data['time'] = add_event_window.layout().itemAt(0, 1).widget().time().toString("HH:mm")
            data['description'] = add_event_window.layout().itemAt(1, 1).widget().toPlainText()
            data['responsible'] = add_event_window.layout().itemAt(2, 1).widget().toPlainText()
            data['nid'] = database.add_event(self.date,
                                               data['time'],
                                               data['description'],
                                               data['responsible'],
                                               )
            if data['nid'] is None:
                self.show_database_error_window(1)
            data.clear()

    def create_list_visitors_widget(self, listWid):
        widget = QWidget()
        hbox = QHBoxLayout()
        label = QLabel()
        if self.data['status'] == 1:
            label.setStyleSheet('color: green;'
                                "font-size: 18px; font-weight: bold;")
        hbox.addWidget(label)
        status = list(self.visitor_status_map.keys())[list(self.visitor_status_map.values()).index(self.data['status'])]
        accept = AcceptCompleteButton(status, listWid)
        hbox.addWidget(accept)
        remove_button = QPushButton('X')
        remove_button.setStyleSheet('color: white; background-color: red;'
                                    "padding: 5px 5px 5px 5px;"
                                    "font-size: 18px; font-weight: bold;"
                                    "border :2px solid red;")
        remove_button.clicked.connect(accept.remove_click)
        remove_button.setFixedWidth(50)
        hbox.addWidget(remove_button)
        widget.setLayout(hbox)
        return widget

    def add_visitor_button_clicked(self):
        self.logger.info("Нажата кнопка: \"добавить посещение\"")
        global add_visit_window
        add_visit_window = AddVisitWindow()
        geometry = self.window().geometry()
        add_visit_window.setGeometry(int(geometry.x() +  2 * (geometry.width() / 4)),
                               int(geometry.y() +  3 * (geometry.height() / 4)),
                               200,
                               150)
        add_visit_window.exec_()
        if add_visit_window.result():
            data = self.data
            data['fio'] = add_visit_window.layout().itemAt(1).widget().toPlainText()
            data['status'] = self.visitor_status_map['Принять']
            data['nid'] = self.add_visitor_to_database()
            if data['nid'] is None:
                self.show_database_error_window(2)
            data.clear()

    def edit_visitor_button_clicked(self):
        geometry = self.window().geometry()
        self.logger.info("Начато редактирование посещения")
        selected_items = self.list_visitors.selectedItems()
        if len(selected_items) != 1:
            self.logger.info('Ошибка: не выбрано посещение для редактирования')
            error_window = QMessageBox(text="Выберете одно посещение")
            error_window.setWindowTitle("Ошибка")
            error_window.setGeometry(int(geometry.x() + 2 * (geometry.width() / 4)),
                                     int(geometry.y() +  2 * (geometry.height() / 3)),
                                       100,
                                       50)
            error_window.exec_()
            return
        editing_visitor_window = AddVisitWindow()
        widget = self.list_visitors.itemWidget(selected_items[0])
        editing_visitor_window.layout().itemAt(1).widget().setText(widget.layout().itemAt(0).widget().text())
        editing_visitor_window.setGeometry(int(geometry.x() +  2 * (geometry.width() / 4)),
                               int(geometry.y() +  2 * (geometry.height() / 3)),
                               200,
                               150)
        editing_visitor_window.exec_()
        if editing_visitor_window.result():
            data = self.data
            data['fio'] = editing_visitor_window.layout().itemAt(1).widget().toPlainText()
            data['status'] = self.visitor_status_map[widget.layout().itemAt(1).widget().text()]
            data['nid'] = self.list_visitors.currentItem().data(Qt.UserRole)
            if self.update_visitor_to_database() != 0:
                self.show_database_error_window(2)
            data.clear()
        self.list_visitors.selectionModel().clearSelection()

    def show_visitors_changes(self, ListItemWidget: QListWidgetItem):
        ListItemWidget.layout().itemAt(0).widget().setText(self.data['fio'])

    def add_visitor_to_database(self):
        data = self.data
        return database.add_visitor(data['fio'], data['status'])

    def update_visitor_to_database(self):
        data = self.data
        return database.update_visitor(data['fio'],
                                      data['status'],
                                      data['nid'])

    def delete_visitor_from_database(self):
        data = self.data
        return database.delete_visitor(data['nid'])

    def add_event_to_database(self):
        data = self.data
        return database.add_event(
            self.date,
            data['time'],
            data['description'],
            data['responsible']
        )

    def update_event_to_database(self):
        data = self.data
        return database.update_event(
            self.date,
            data['time'],
            data['description'],
            data['nid'],
            data['responsible']
        )

    def delete_event_from_database(self):
        nid = self.data['nid']
        return database.delete_event(nid)


class MyCalendar(QCalendarWidget):

    def __init__(self, parent=None):
        QCalendarWidget.__init__(self, parent)
        self.data = {}
        self.setGridVisible(True)
        self.setHorizontalHeaderFormat(QCalendarWidget.ShortDayNames)
        self.setVerticalHeaderFormat(QCalendarWidget.ISOWeekNumbers)
        self.setNavigationBarVisible(True)
        self.setDateEditEnabled(True)

    def paintCell(self, painter, rect, date):

        QCalendarWidget.paintCell(self, painter, rect, date)

        if date.toString("dd.MM.yyyy") in self.data:
            painter.setPen(QPen(Qt.gray))
            font = painter.font()
            font.setPixelSize(10)
            font.setItalic(True)
            painter.setFont(font)

            painter.drawText(rect.topLeft() + QPoint(5, 10), str(self.data[date.toString("dd.MM.yyyy")]))

            painter.setBrush(QColor(0, 220, 0, 50))
            if date < date.currentDate():
                painter.setBrush(QColor(0, 0, 0, 20))

            painter.setPen(QColor(0, 0, 0, 0))
            painter.drawRect(rect)

            painter.save()
            #print('cells are updated')

        if date == date.currentDate():
            painter.setBrush(QColor(0, 200, 200, 50))
            painter.setPen(QColor(0, 0, 0, 0))
            painter.drawRect(rect)


class ScheduleWorker(QThread):

    date_changed = pyqtSignal()
    is_running = False

    def __init__(self, logger):
        super().__init__()
        self.application_lock = logger.handlers[0].lock
        
    def run(self):
        schedule.every().day.at("00:00").do(self.date_changed.emit)
        schedule.every().day.at("00:00").do(self.log_cleaner)
        while self.is_running:
            schedule.run_pending()
            for _ in range(600):
                if not self.is_running:
                    break
                QThread.msleep(100)

    def log_cleaner(self):
        self.application_lock.acquire()
        with open('app.log', 'r+', encoding='utf-8') as f:
            while True:
                line = f.readline()
                if line == "":
                    break
                if re.search("- ERROR -", line, re.MULTILINE):
                    self.application_lock.release()
                    return
            f.truncate(0)
        self.application_lock.release()


class TabWindow(QMainWindow):

    thread = QThread()

    def __init__(self, logger):
        super(TabWindow, self).__init__()
        self.logger = logger
        self.sw = ScheduleWorker(logger)
        calendar = MyCalendar()

        # configure date change tracker into separate thread
        self.sw.is_running = True
        self.sw.date_changed.connect(calendar.updateCells)
        self.sw.start()

        self.setStyleSheet('font-size: 20px;')
        calendar.data = database.get_statistic_by_days()
        if calendar.data is not None:
            calendar.updateCells()
        self.setGeometry(500, 500, 1040, 500)
        self.tabs = QTabWidget()
        self.tabs.tabBar().hide()
        self.setCentralWidget(self.tabs)
        self.tabs.addTab(calendar, "Календарь")
        self.tabs.widget(0).clicked.connect(self.to_events)
        self.setWindowTitle("КАЛЕНДАРЬ")
        self.setWindowIcon(QIcon("logo.ico"))

    def closeEvent(self, event):
        self.logger.info('Нажата кнопка \"Закрыть окно приложения\"')
        self.sw.is_running = False
        self.sw.wait()
        self.sw.log_cleaner()
        event.accept()

    def to_calendar(self):
        self.logger.info("Нажата кнопка: \"Возврат к календарю\"")
        self.setWindowTitle("КАЛЕНДАРЬ")
        database.notified.disconnect(self.tabs.widget(1).database_changed)
        self.tabs.removeTab(1)
        self.tabs.setCurrentWidget(self.tabs.widget(0))
        x = self.geometry().x()
        y = self.geometry().y()
        self.setGeometry(x, y, self.calendar_width, self.calendar_height)

    def to_events(self, date):
        string_date = self.tabs.widget(0).selectedDate().toString("dd.MM.yyyy")
        self.logger.info(f"Выбрана дата: {string_date}")
        self.setWindowTitle(string_date)
        self.tabs.addTab(MainWindow(string_date, self.logger), "Встречи")
        self.calendar_width = self.geometry().width()
        self.calendar_height = self.geometry().height()
        self.tabs.setCurrentWidget(self.tabs.widget(1))
        x = self.geometry().x()
        y = self.geometry().y()
        if (QDate.currentDate().toString("dd.MM.yyyy") == string_date):
            self.setGeometry(x, y, 800, 900)
            self.tabs.widget(1).update_event_table()
            self.tabs.widget(1).update_visitors_button_clicked()
        else:
            self.setGeometry(x, y, 800, 500)
            self.tabs.widget(1).update_event_table()

class DBConnectWindow(QDialog):

    def __init__(self, logger):
        super(DBConnectWindow, self).__init__(parent=None)
        self.logger = logger
        l1 = QLabel("Пароль")
        l1.setFont(QFont("Roboto", 14))
        pwd_edit = QLineEdit()
        pwd_edit.setEchoMode(QLineEdit.Password)
        pwd_edit.setMinimumHeight(40)
        pwd_edit.setMinimumWidth(200)
        pwd_edit.setFont(QFont("Roboto", 12))
        pwd_edit.setFixedSize(230, 30)
        fbox = QFormLayout()
        fbox.addRow(l1, pwd_edit)
        ok_button = QPushButton('OK')
        ok_button.clicked.connect(self.ok_button_clicked)
        cancel_button = QPushButton('Отмена')
        cancel_button.clicked.connect(self.reject)
        fbox.addRow(ok_button, cancel_button)
        self.setWindowTitle("Подключение к БД")
        self.setLayout(fbox)

    def ok_button_clicked(self):
        password = self.layout().itemAt(0, 1).widget().text()
        if database.connect(DB_HOST, DB_PORT, DB_NAME, DB_USER, password):
            if self.layout().rowCount() == 2:
                message = QLabel('Неправильный пароль или\nдругая ошибка\nподключения')
                message.setStyleSheet("color: red;")
                message.setFont(QFont("Roboto", 9))
                self.layout().insertRow(1, None, message)
                self.logger.error('Введён неправильный пароль или произошла другая ошибка подключения к БД')
        else:
            self.accept()

    def closeEvent(self, event):
        self.logger.info('Нажата кнопка \"Закрыть окно ввода пароля для подключения к БД\"')
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    logger_database = logging.getLogger("database")
    logger_database.setLevel(logging.INFO)
    file_handler = logging.FileHandler("app.log", "a", "utf-8")
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger_database.addHandler(file_handler)

    logger_app = logging.getLogger("application")
    logger_app.setLevel(logging.INFO)
    file_handler = logging.FileHandler("app.log", "a", "utf-8")
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger_app.addHandler(file_handler)

    with open('credentials.json', 'r') as f:
        db_credentials = json.load(f)

    DB_HOST = db_credentials['host']
    DB_PORT = db_credentials['port']
    DB_USER = db_credentials['db_user']
    DB_NAME = db_credentials['db_name']
    database = Database(logger_database)
    db_connect_window = DBConnectWindow(logger_app)
    db_connect_window.setWindowIcon(QIcon("logo.ico"))
    logger_app.info('Запрос пароля на подкдючение к базе данных')
    db_connect_window.exec_()
    if db_connect_window.result():
        try:
            ETHERNET_ADDR = database.get_own_ip()[0]['inet_client_addr']
        except Exception as e:
            logger_app.error("Ошибка базы данных.")
            QMessageBox.critical(None, "Ошибка базы данных", "Ошибка запроса IP-адреса.")
            database.disconnect()
            exit(0)
        database.start_listen()
        database.listen('cats')
        WM = TabWindow(logger_app)
        WM.show()
        app.exec_()
        database.stop_listen()
        database.unlisten('cats')
        database.disconnect()
        WM.sw.log_cleaner()




