#!/usr/bin/python3

############################################################################ 
# Класс отдающего сервера
############################################################################ 

# Подключение модулей программы
from server import CListenServer
from gvar import *
import config

# Класс отдающего сервера
class CUpload(CListenServer):

	# Конструктор
	def __init__(self):
		
		# Вызов конструктора базового класса
		CListenServer.__init__(self, config.upload_port)

	# Главная функция потока отдающего сервера
	def run(self):

		try:

			# Пока узел подключен к сети повторять
			while self.is_run:

				# Ожидать подключения клиента
				try: (cli_sock, cli_addr) = self.sock.accept()
				except: continue

				# Подключение клиента произошло -
				# считать из сокета хэш необходимого клиенту блока файла
				part_hash = cli_sock.recv(33).decode().rstrip()

				# Получить из таблицы блоков файлов, доступных для скачивания
				# удаленными узлами файлообменной сети, информацию о целевом
				# блоке
				res = self.db.select(
						index = 1,
						query = "path, pos_in_file from " +	tname["filelist"] + ", " +
								tname["partlist"] + " where (" + tname["partlist"] +
								".hash = \"" + part_hash + "\" and " +	tname["filelist"] +
								".hash_path = " + tname["partlist"] +	".hash_path)")

				# Если запись о блоке найдена в списке блоков
				if res != []:

					# Считать целевой блок из файла, в котором блок хранится,
					# и отправить блок удаленному узлу
					(path, pos_in_file) = res[0]
					fl = open(path, "rb")
					fl.seek(pos_in_file)
					cli_sock.send(fl.read(part_size))
			
				# Закрыть сокет
				cli_sock.close()

		except: pass

