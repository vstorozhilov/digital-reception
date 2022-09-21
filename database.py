import sys
import select
import psycopg2
import psycopg2.extensions
import datetime
import threading
import logging
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.Qt import QApplication


class NotifyHandler(QThread):
    notified = pyqtSignal(str, str)  # channel, message

    def __init__(self):
        super().__init__()
        self.conn = None
        self.running = False

    def run(self):
        while self.running:
            # if select.select([self.conn], [], [], 1) != ([], [], []):
            self.conn.poll() # we suggest that psycopg is a thread safe:-)
            while self.conn.notifies:
                notify = self.conn.notifies.pop(0)
                self.notified.emit(notify.channel, notify.payload)
            QThread.msleep(100)


class Database(QObject):
    # Формат данных: идентификатор, звание, ФИО, Цель, Дата, Время, Статус, Примечание
    # Формат статуса встречи: 0 - активна, 1 - Завершена, 2 - отменена
    notified = pyqtSignal(str, str)

    def __init__(self, logger=None):
        super().__init__()
        self.conn = None
        self.cur = None

        if logger is None:
            self.logger = logging.getLogger("database")
            self.logger.setLevel(logging.INFO)
            file_handler = logging.FileHandler("app.log", "a", "utf-8")
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        else:
            self.logger = logger

        self.thread = QThread()
        self.notifier = NotifyHandler()
        self.notifier.notified.connect(self.notify_handler)

    def connect(self, host, port, database, user, password):
        # Connect to your postgres DB
        self.logger.info(f"Подключение к postgresql://{user}@{host}:{port}/{database}")
        try:
            self.conn = psycopg2.connect(
                user=user,
                password=password,
                host=host,
                port=port,
                dbname=database
            )
            self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            self.cur = self.conn.cursor()
            return 0

        except Exception as e:
            self.logger.error(str(e))
            self.conn = None
            self.cur = None
            return 1

    def disconnect(self):
        self.logger.info("Отключение")

        self.cur.close()
        self.conn.close()

    @property
    def is_connected(self):
        return self.conn is not None and self.cur is not None

    def get_event_by_nid(self, nid):
        self.logger.info(f"Запрос события {nid}")
        try:
            self.cur.execute("SELECT * FROM events WHERE nid=%s;", (nid,))
        except Exception as e:
            self.logger.error(str(e))
            return None

        records = self.fetch_data()

        return records

    def get_events_by_date(self, date):
        self.logger.info(f"Запрос событий по дате {date}")
        try:
            self.cur.execute("SELECT * FROM events WHERE date=%s ORDER BY meettime ASC ;", (date, ))
        except Exception as e:
            self.logger.error(str(e))
            return None

        records = self.fetch_data()

        return records

    def get_active_visitors(self):
        self.logger.info("Запрос активных пользователей")
        try:
            self.cur.execute("SELECT * FROM visitors WHERE status < 2 ORDER BY nid ASC ;")
        except Exception as e:
            self.logger.error(str(e))
            return None

        records = self.fetch_data()
        return records

    def get_statistic_by_days(self):
        self.logger.info(f"Запрос статистики по дням")
        try:
            self.cur.execute("SELECT date, count(*) as count FROM events GROUP BY date;")
        except Exception as e:
            self.logger.error(str(e))
            return None

        records = self.fetch_data()
        data = {record["date"]: record["count"] for record in records}

        return data

    def add_event(self, date, meettime, description, responsible):
        self.cur.execute("select nextval('events_nid_seq');")
        try:
            nid = self.fetch_data()[0]['nextval']
        except Exception as e:
            self.logger.error(str(e))
            return None
        self.logger.info(f"Добавление события: {nid} {date} {meettime} {description} {responsible}")

        try:
            self.cur.execute(
                """
                INSERT INTO public.events(
                    nid, date, meettime, description, responsible
                ) VALUES (
                    %s, %s, %s, %s, %s
                );
                """,
                (nid, date, meettime, description, responsible)
            )
            self.conn.commit()
            return nid

        except Exception as e:
            self.logger.error(str(e))
            return None

    def add_visitor(self, fio, status):
        self.cur.execute("select nextval('visitors_nid_seq');")
        try:
            nid = self.fetch_data()[0]['nextval']
        except Exception as e:
            self.logger.error(str(e))
            return None
        self.logger.info(f"Добавление посетителя: {fio} {status}")

        try:
            # insert sql entity to database
            # commit current changes
            self.cur.execute(
                """
                INSERT INTO public.visitors(
                    fio, status, nid
                ) VALUES (
                    %s, %s, %s
                );
                """,
                (fio, status, nid)
            )
            self.conn.commit()
            return nid

        except Exception as e:
            self.logger.error(str(e))
            return None

    def update_event(self, date, meettime, description, nid, responsible):
        # формат status: 0 - OK, 1 - ERROR
        self.logger.info(f"Обновление события: {nid} {date} {meettime} {description} {responsible}")

        try:
            self.cur.execute(
                """
                UPDATE public.events
                SET nid=%s, date=%s, meettime=%s, description=%s, responsible=%s
                WHERE nid=%s;
                """,
                (nid, date, meettime, description, responsible, nid)
            )
            self.conn.commit()
            return 0
        except Exception as e:
            self.logger.error(str(e))

            return 1

    def update_visitor(self, fio, status, nid):
        # формат status: 0 - OK, 1 - ERROR
        self.logger.info(f"Обновление посетителя: {fio} {status} {nid}")

        try:
            self.cur.execute(
                """
                UPDATE public.visitors
                SET nid=%s, fio=%s, status=%s
                WHERE nid=%s;
                """,
                (nid, fio, status, nid)
            )
            self.conn.commit()
        except Exception as e:
            self.logger.error(str(e))

            return 1
        else:
            return 0

    def delete_event(self, nid):
        # формат status: 0 - OK, 1 - ERROR
        self.logger.info(f"Удаление  события: {nid}")

        try:
            self.cur.execute(
                """
                DELETE FROM public.events
                WHERE nid=%s;
                """,
                (nid, )
            )
            self.conn.commit()
        except Exception as e:
            self.logger.error(str(e))
            return 1

        else:
            return 0

    def delete_visitor(self, nid):
        # формат status: 0 - OK, 1 - ERROR
        self.logger.info(f"Удаление  посетителя: {nid}")

        try:
            self.cur.execute(
                """
                DELETE FROM public.visitors
                WHERE nid=%s;
                """,
                (nid, )
            )
            self.conn.commit()
        except Exception as e:
            self.logger.error(str(e))

            return 1
        else:
            return 0

    def listen(self, channel):
        self.logger.info(f"Слушаю канал {channel}")
        return self.cur.execute(f"LISTEN {channel};")

    def unlisten(self, channel):
        self.logger.info(f"Перестаю слушать канал {channel}")
        return self.cur.execute(f"UNLISTEN {channel};")

    def start_listen(self):
        self.logger.info("Начинаю слушать каналы")
        self.notifier.conn = self.conn
        self.notifier.running = True
        self.notifier.start()
        self.logger.info("Слушаю каналы ...")

    def stop_listen(self):
        self.logger.info("Перестаю слушать каналы")
        self.notifier.running = False
        self.notifier.wait()
        self.logger.info("Прослушивание остановлено")

    def notify_handler(self, channel, message):
        self.logger.info(f"Принято уведомление из канала {channel}: {message}")
        self.notified.emit(channel, message)

    def fetch_data(self):
        self.logger.info("Сбор данных из запроса")
        data = []
        try:
            if self.cur.description is None:
                self.logger.info("Найдено 0 записей")
                return []
            columns = [desc[0] for desc in self.cur.description]

            for result in self.cur.fetchall():
                row = {}
                for key, value in zip(columns, result):
                    if type(value) == datetime.date:
                        row[key] = value.strftime('%d.%m.%Y')
                    elif type(value) == datetime.time:
                        row[key] = value.strftime('%H:%M')
                    else:
                        row[key] = value
                data.append(row)
        except Exception as e:
            self.logger.error(f"Ошибка при получении данных:\n {str(e)}")
            return None
        else:
            self.logger.info(f"Найдено {len(data)} записей")
            return data

    def get_own_ip(self):
        self.logger.info("Запрос клиентского ip-адреса")
        try:
            self.cur.execute("SELECT inet_client_addr();")
        except Exception as e:
            self.logger.error(str(e))
            return None

        records = self.fetch_data()

        return records

