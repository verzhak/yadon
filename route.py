#!/usr/bin/python3

############################################################################ 
# Класс маршрутизационного сервера
############################################################################ 

# Подключение модуля socket (содержит функционал использования сокетов)
# стандартной библиотеки
import socket

# Подключение модулей программы
from server import CListenServer
from gvar import *
import config

# Класс маршрутизационного сервера
class CRouteTable(CListenServer):

	# Конструктор
	def __init__(self):

		# Вызов конструктора базового класса
		CListenServer.__init__(self, config.route_port)

		self.reread()

	# Функция обновления таблицы маршрутизации на основе содержимого
	# списка route конфигурационного файла
	def reread(self):

		# Создание таблицы маршрутизации
		self.db.create_table(tname["route"],
			["ip char(15) not null", "route_port int not null",
			 "download_port int not null", "mysql_port int not null",
			 "user char(50) not null", "db char(50) not null",
			 "primary key (ip, route_port)"])

		# Усечение таблицы маршрутизации
		self.db.truncate(tname["route"])

		for x in config.route_table:

			# Попытка подключения к очередному соседнему узлу
			self.connect(x[0], x[1])

	# Функция подключения к соседнему узлу
	def connect(self, host, port):

		# Создание клиентского TCP-сокета
		cli_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		
		try:

			# Подключение к соседнему узлу
			cli_sock.connect((host, port))

			# Отправка соседнему узлу информации о данном узле
			send_str = str(config.route_port) + " " + str(config.upload_port) + \
								 " " + str(config.mysql_port) + " " + config.user + " " + \
								 config.db
			cli_sock.send(send_str.encode())

			# Получение от соседнего узла информации о нем
			buf = cli_sock.recv(1024).decode()

		except: return False

		# Закрытие сокета
		cli_sock.close()

		# Обработка информации,
		# поступившей от соседнего узла при подключении к нему
		return self.parse(host, buf)

	# Разрыв связи с соседним узлом
	# (удаление соседнего узла из таблицы маршрутизации)
	def disconnect(self, host, port):

		query = "where (ip = \"" + host + "\" and route_port = " + \
						str(port) + ")"
		self.db.delete(tname["route"], query)

	# Функция обработки информации,
	# поступившей от соседнего узла при подключении к нему
	def parse(self, host, buf, tindex = 0):

		param = buf.split(" ")
		
		if len(param) == 5:

			try: self.db.insert(tname["route"],
													index = tindex, value = [[host] + param])
			except: pass

			return True
		
		return False

	# Главная функция потока маршрутизационного сервера
	def run(self):

		try:

			# Пока узел подключен к сети повторять
			while self.is_run:

				# Ожидать подключения клиентского сокета
				try: (cli_sock, cli_addr) = self.sock.accept()
				except: continue

				# Если очередной соседний узел подключился
				# к маршрутизационному серверу, то проанализировать информацию
				# о соседнем узле и, если требуется, отправить соседнему узлу
				# информацию о данном узле
				if self.parse(str(cli_addr[0]), cli_sock.recv(1024).decode(), 1):

					send_str = str(config.route_port) + " " + str(config.upload_port) \
										 + " " + str(config.mysql_port) + " " + config.user + \
										 " " + config.db
					cli_sock.send(send_str.encode())

				# Закрыть сокет
				cli_sock.close()

		except: pass

