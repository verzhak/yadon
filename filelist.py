#!/usr/bin/python3

############################################################################ 
# Класс, отвечающий за списки файлов и блоков файлов,
# доступных для скачивания удаленными узлами
############################################################################ 

# Подключение модулей стандартной библиотеки
#
# os - модуль, содержащий разнообразные системные функции
#
# hashlib - модуль, содержащий, кроме всего прочего, функционал,
#						позволяющий рассчитывать MD5-хэш блоков данных
#
import os, hashlib

# Подключение модулей программы
from gvar import *
import config, mysql

# Класс, отвечающий за списки файлов и блоков файлов,
# доступных для скачивания удаленными узлами
class CFileList():

	# Конструктор
	def __init__(self):

		# Подключение к локальному серверу MySQL
		self.__db = mysql.CMySQL(user = config.user, db = config.db)

		# Создание списка файлов, доступных для скачивания удаленными узлами
		self.__db.create_table(tname["filelist"],
			["hash char(32) not null", "size int not null", "path blob not null",
				"hash_path char(32) not null unique primary key", "check size > 0"])

		# Создание списка блоков файлов,
		# доступных для скачивания удаленными узлами
		self.__db.create_table(tname["partlist"],
			["hash char(32) not null", "hash_path char(32) not null",
				"pos_in_file int not null", "foreign key (hash_path) references " +
				tname["filelist"] +
				"(hash_path) on delete cascade on update cascade",
				"check pos_in_file >= 0"])

		# Создание хранимой процедуры удаления из списков файлов
		# и блоков файлов информации о целевом файле узла
		code = """declare s_hash_path char(32);
				select hash_path into s_hash_path from filelist where path = s_path;
				delete from partlist where hash_path = s_hash_path;
				delete from filelist where hash_path = s_hash_path;"""
		self.__db.create_procedure(pname["delete_from_filelist"],
															 code = code, param = [["s_path", "blob"]])

	# Деструктор (вызывается явно)
	def destroy(self):

		self.__db.destroy()

	# Функция обновления списков файлов и блоков файлов по информации
	# из списка filelist конфигурационного файла
	def refresh(self):

		# Для каждого элемента списка config.filelist повторять
		for x in config.filelist:

			# Если объект файловой системы по полному пути и имени x существует
			if os.path.exists(x):

				# Если объект файловой системы - каталог
				if os.path.isdir(x):
					
					# Для каждого файла из каталога и подкаталогов любой степени
					# вложенности в данном каталоге -
					# добавить файл в списки файлов и блоков файлов
					for item in os.walk(x):
						
						for file in item[2]:
							
							self.add(item[0] + "/" + file)

				# Если объект файловой системы - файл,
				# то добавить файл в списки файлов и блоков файлов
				else: self.add(x)

	# Функция добавления файла в список файлов, доступных для скачивания
	# удаленными узлами
	def add(self, path):

		# Подсчет MD5-хэша полного пути и имени файла
		#
		# (таковой хэш служит первичным ключом в таблице filelist
		# и первичным / внешним ключом в таблице partlist, поскольку,
		# в отличии от полного пути и имени файла, хэш имеет
		# строго определенный размер в байтах)
		path_hash = str(hashlib.md5(path.encode()).hexdigest())
		if self.__db.select("* from " + tname["filelist"] +
												" where hash_path = \"" + path_hash + "\"") != []:
			return False

		file_size = os.path.getsize(path)
		cur_size = 0
		part_hash = []

		# Инициализация объекта подсчета MD5-хэша файла
		file_hash_obj = hashlib.md5()

		# Открытие файла на бинарное чтение
		fl = open(path, "rb")

		while cur_size < file_size:

			# Чтение очередного блока файла
			part = fl.read(part_size)

			# Обновление объекта подсчета MD5-схэша файла в соответствии
			# с содержимым очередного блока файла
			file_hash_obj.update(part)

			# Подсчет MD5-хэша очередного блока файла
			part_hash.append(str(hashlib.md5(part).hexdigest()))

			cur_size += part_size

		# Закрытие файла
		fl.close()

		# Получение MD5-хэша файла
		file_hash = str(file_hash_obj.hexdigest()) 
		
		# Помещение записи о файле в список файлов,
		# доступных для скачивания удаленными узлами
		self.__db.insert(tname["filelist"],
										 value = [[file_hash, file_size, path, path_hash]])

		# Помещение записи о блоках файла в список блоков файлов,
		# доступных для скачивания удаленными узлами
		for x in range(0, len(part_hash)):

			self.__db.insert(tname["partlist"],
											 value = [[part_hash[x], path_hash, x * part_size]])

		return True

	# Удаление файла из списка файлов,
	# доступных для скачивания удаленными узлами
	def delete(self, path):

		self.__db.call_procedure(pname["delete_from_filelist"], [path])

