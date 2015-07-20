#!/usr/bin/python3

############################################################################ 
# Класс скачивающего потока
#
# (данный поток производит обход очереди блоков на скачивание
# и, если данная очередь не пуста, производит скачивание очередного блока)
############################################################################ 

# Подключение модулей стандартной библиотеки:
#
# sys, os - модули, содержащие разнообразный системный функционал
# 
# socket - модуль, содержащий функционал манипуляции сокетами
# 
# mmap - модуль, содержащий функционал для организации
#				 файлового ввода / вывода с помощью файловых отображений
#
# time - модуль, предоставляющий функцию sleep(), используемую для
#				 организации блокировки выполнения потока на некоторый промежуток
#				 времени
#
import sys, os, socket, mmap, time

# Подключение модулей программы
from server import CBaseServer
from gvar import *
import config, mysql

# Класс скачивающего потока
class CDownload(CBaseServer):

	# Конструктор
	def __init__(self):
		
		# Вызов конструктора родительского класса
		CBaseServer.__init__(self)
		
		# Создание таблицы - очереди скачивания блоков
		self.db.create_table(tname["downlist"],
				["id int not null unique primary key auto_increment",
				 "hash char(32) not null",
				 "ip char(15) not null",
				 "path blob not null",
				 "pos_in_file int not null",
				 "check pos_in_file >= 0"])

		# Создание таблицы, содержащей результаты поиска файлов
		# в списках файлов соседних узлов
		self.db.create_table(tname["search_result"],
				["id int not null unique primary key auto_increment",
				 "ip char(15) not null", "path blob not null",
				 "hash_path char(32) not null", "size int not null",
				 "check size > 0"])
		self.db.truncate(tname["search_result"])

		# Создание таблицы, содержащей список блоков, загрузка которых закончена
		# с момента последней очистки данной таблицы
		self.db.create_table(tname["finished"], ["path blob not null"])
		self.db.truncate(tname["finished"])

		# Создание процедуры помещения в таблицу finished информации об
		# очередном блоке, чья загрузка завершена
		code = """insert into finished select path from downlist where id = s_id;
				  delete from downlist where id = s_id;"""
		self.db.create_procedure(pname["put_in_finished_table"],
														 code = code, param = [["s_id", "int"]])

	# Функция поиска файла в списках файлов соседних узлов
	# по маске имени (параметр path_pattern) и указанному выражению
	# для размера файла (параметры size_op и size)
	def find_file(self, path_pattern, size_op, size):

		self.db.truncate(tname["search_result"])
		
		query = "path, hash_path, size from " + tname["filelist"] + \
				" where (path like \"" + path_pattern + "\" and size " + \
				size_op + " " + size + ")"

		# Для каждого узла из таблицы маршрутизации повторять
		for x in self.db.select("ip, mysql_port, user, db from " +
														tname["route"]):

			(ip, port, user, db) = x

			# Подключится к MySQL-серверу из таблицы маршрутизации
			try: cli_db = mysql.CMySQL(host = ip, port = port,
																 db = db, user = user)
			except: continue

			# Произвести выборку из таблицы файлов соседнего узла,
			# после чего повторять для каждой записи из результатов выборки
			for y in cli_db.select(query):

				self.db.insert(tname["search_result"],
											 field = ["ip", "path", "hash_path", "size"],
											 value = [[ip, y[0].split("/")[-1], y[1], y[2]]])

			cli_db.destroy()

	# Поставить файл удаленного узла на скачивание
	#
	# Параметры:
	#
	#		id - идентификатор записи о файле в таблице результатов поиска файлов
	#		path - абсолютный путь и имя файла данного узла, в который будет
	#					 произведено скачивание файла удаленного узла
	def download_file(self, id, path):
		
		# Получение информации о целевом файле и об удаленном узле, на котором
		# данный файл расположен, из таблицы результатов поиска
		res = self.db.select("ip, hash_path, size from " +
												 tname["search_result"] + " where id = " + str(id))
		if res == []:
			return False

		(host, remote_hash_path, size) = res[0]

		part = []
		
		# Получение информации об удаленном узле, на котором расположен
		# целевой файл, из таблицы маршрутизации
		res = self.db.select("ip, mysql_port, user, db from " + tname["route"]
												 + " where ip = \"" + host + "\"")
		if res == []:
			return False
		
		(host, port, user, db) = res[0]
		
		# Подключение к удаленному узлу, на котором расположен целевой файл
		try: cli_db = mysql.CMySQL(host = host, port = port,
															 db = db, user = user)
		except: return False

		# Формирование списка хэшей блоков целевого файла
		for z in cli_db.select("hash, pos_in_file from " +
													 tname["partlist"] + " where (hash_path = \"" +
													 remote_hash_path + "\")"):

			part.append((z[0], z[1]))

		cli_db.destroy()

		# Создание пустого файла по полному пути и с именем path на данном узле
		fl = open(path, "wb")
		fl.seek(size - 1)
		fl.write(b'1')
		fl.close()

		# Для каждого удаленного узла из таблицы маршрутизации повторять
		for x in self.db.select("ip, mysql_port, user, db from " +
														tname["route"]):

			(host, port, user, db) = x
			try: cli_db = mysql.CMySQL(host = host, port = port,
																 db = db, user = user)
			except: continue

			for y in part:

				# Если один из блоков целевого файла присутствует также и на
				# очередном узле, то запись о данном блоке (вместе с IP адресом
				# удаленного узла) помещается в таблицу скачивания
				if cli_db.select("* from " + tname["partlist"] +
												 " where (hash = \"" + y[0] + "\")") != []:
			
					self.db.insert(tname["downlist"],
												 field = ["hash", "ip", "path", "pos_in_file"],
												 value = [[y[0], host, path, y[1]]])

			cli_db.destroy()

		return True

	# Удаление скачиваемого файла из таблицы скачивания и из файловой системы 
	def delete_download(self, path):

		os.remove(path)
		self.db.delete(tname["downlist"], "where path = \"" + path + "\"")

	# Очистка списка блоков, скачивание которых завершено
	def finished_clear(self):

		self.db.delete(tname["finished"])

	# Главная функция скачивающего потока
	def run(self):

		try:

			# Пока узел подключен к сети повторять
			while self.is_run:

				# Получить очередные 20 записей о блоках, стоящих в очереди
				# на скачивание
				to_download = self.db.select(index = 1,
						query = "id, hash, " + tname["downlist"] +
						".ip, download_port, path, pos_in_file from " +	tname["downlist"]
						+ ", " + tname["route"] + " where " + tname["downlist"] +
						".ip = " + tname["route"] + ".ip", limit = 20)

				# Если блоки, стоящие в очереди на скачивание, отсутствуют,
				# то скачивающий поток блокируется на пять секунд
				if to_download == []:

					time.sleep(5)

				else:

					# Для очередного блока, стоящего в очереди на скачивание,
					# выполнить
					for x in to_download:

						(id, hash, host, port, path, pos_in_file) = x

						# Создать клиентский TCP-сокет
						cli_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
					
						# Подключится к удаленному узлу, на котором блок расположен
						try: cli_sock.connect((host, port))
						except:	break
						
						# Отправить удаленному узлу хэш целевого блока
						cli_sock.send(hash.encode())

						# Открыть результирующий файл на бинарное добавление
						try: fl = open(path, "r+b")
						except: break
						
						# Создать файловое отображение для области
						# результирующего файла, в которую необходимо произвести
						# сохранение скачиваемого блока
						try: map = mmap.mmap(fl.fileno(),
																 length = part_size,
																 offset = pos_in_file)
						except:	map = mmap.mmap(fl.fileno(),
																	length = os.path.getsize(path) % part_size,
																	offset = pos_in_file)
						
						# Получение и запись в файловое отображение содержимого
						# очередного блока
						part = cli_sock.recv(part_size)
						
						if len(part) != 0:

							while len(part) != 0:

								map.write(part)
								part = cli_sock.recv(part_size)

							map.flush()

							self.db.call_procedure(index = 1,
																 proc_name = pname["put_in_finished_table"],
																 param = [id])
						
						# Закрытие сокета, удаление файлового отображения,
						# закрытие файла
						cli_sock.close()
						map.close()
						fl.close()

		except: pass

