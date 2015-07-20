#!/usr/bin/python3

############################################################################ 
# Класс, предоставляющий программе функционал доступа к MySQL-серверам
############################################################################ 

# Подключение модулей библиотеки Qt4 / PyQt4
#
#	QtCore - модуль, содержащий разнообразный общий функционал библиотеки
#					 Qt4 / PyQt4
#
# QtSql - модуль, содержащий функционал взаимодействия с различными СУБД,
#					использующими в своей работе язык SQL
#
from PyQt4 import QtCore, QtSql

# Класс, предоставляющий программе функционал доступа к MySQL-серверам
class CMySQL():

	# Конструктор
	def __init__(self, user, db, host = "localhost", port = None):

		self.__QByteArray_type = type(QtCore.QByteArray())

		self.__db = []
		# Создаются два подключения:
		#			один для главного потока программы,
		#			другой для возможно существующего дочернего потока программы
		for x in range(0, 2):
		
			# Загрузка драйвера для целевой СУБД
			next_db = QtSql.QSqlDatabase("QMYSQL")
		
			# Установка параметров подключения к целевому серверу БД
			next_db.setHostName(host)

			if port != None:
				
				next_db.setPort(port)

			next_db.setUserName(user)
			next_db.setDatabaseName(db)

			# Подключение к целевому серверу БД
			if not next_db.open():
				
				raise Exception("Ошибка при открытии базы данных")
			
			self.__db.append(next_db)

		# Инициализация объектов класса QSqlQuery,
		# с помощью которых будут выполнятся различные запросы к БД
		self.__query = [QtSql.QSqlQuery(db = self.__db[0]),
						QtSql.QSqlQuery(db = self.__db[1])]

	# Деструктор (вызывается явно)
	def destroy(self):

		self.__db[0].close()
		self.__db[1].close()

	# Создание таблицы
	def create_table(self, table_name, definition, index = 0):

		self.__query[index].exec_("create table if not exists " + table_name +
													" (" + ", ".join(definition) + ") engine = InnoDB")

	# Создание процедуры
	def create_procedure(self, proc_name, code, param = [], index = 0):

		query = "drop procedure " + proc_name
		self.__query[index].exec_(query)

		query = "create procedure " + proc_name +   " (" + \
						", ".join(map(" ".join, param)) + \
						") sql security invoker begin " + code + " end;"
		self.__query[index].exec_(query)

	# Усечение таблицы
	def truncate(self, table_name, index = 0):

		try: self.__query[index].exec_("truncate table " + table_name)
		except: pass

	# Выполнения выборки из таблицы с возвращением списка результатов выборки
	def select(self, query, limit = 0, index = 0):

		try: self.__query[index].clear()
		except: pass

		ret = []

		if limit > 0: query += " limit " + str(limit)
		
		try:

			self.__query[index].exec_("select " + query)

			# Формирование списка результатов выборки
			while self.__query[index].next():
			
				ins = []
			
				for x in range(0, self.__query[index].record().count()):
				
					next_val = self.__query[index].value(x)

					# В случае, если очередное поле в результатах выборки суть есть
					# строка в кодировке UTF-8 и поэтому представляется в виде
					# массива байт, то значение такового поля явно декодируется
					# в UTF-8-строку
					if type(next_val) == self.__QByteArray_type:

						next_val = next_val.data().decode()
				
					ins.append(next_val)
			
				ret.append(ins)

		except: pass

		return ret

	# Запись данных в таблицу
	def insert(self, table_name, value, field = [], index = 0):

		# Добавление кавычек к строковым значениям,
		# переданным в параметре value (тип параметра - список)
		y_range = range(0, len(value[0]))
		for x in range(0, len(value)):

			for y in y_range:

				try: value[x][y] = "\"" + value[x][y] + "\""
				except: pass

		if field == []: field_str = ""
		else: field_str = " (" + ", ".join(field) + ") "

		query = "insert into " + table_name + field_str + " values " + "(" + \
						"), (".join(map(lambda x: ", ".join(map(str, x)), value)) + ")"
		self.__query[index].exec_(query)

	# Удаление записи из таблицы
	def delete(self, table_name, query = "", index = 0):

		self.__query[index].exec_("delete from " + table_name + " " + query)

	# Вызов процедуры
	def call_procedure(self, proc_name, param = [], index = 0):

		for x in range(0, len(param)):

			try:
				
				if param[x][0] != "@":
					
					param[x] = "\"" + param[x] + "\""

			except: pass

		self.__query[index].exec_("call " + proc_name + "(" +
															", ".join(map(str, param)) + ")")

