#!/usr/bin/python3

############################################################################ 
# Главный класс графического интерфейса управления узлом
############################################################################ 

# Подключение модуля sys стандартной библиотеки,
# содержащего различный системный функционал
import sys

# Подключение модулей библиотеки Qt4 / PyQt4
#
# Qt и QtCore - модули, содержащие разнообразный общий функционал
#								библиотеки Qt4 / PyQt4
#
# QtSql - модуль, содержащий функционал взаимодействия с различными СУБД,
#					использующими в своей работе язык SQL
#
# QtGui - модуль, содержащий функционал управления графическим интерфейсом
#
from PyQt4 import QtGui, QtSql, QtCore, Qt

# Подключение модуля описания графического интерфейса,
# полученного путем компиляции XML-описания графического интерфейса
# в код языка Python
from ui_window import Ui_Dialog

# Подключение модулей программы
import route, upload, download, filelist, config
from gvar import *

############################################################################ 

# Вспомогательный класс, обеспечивающий корректный вывод данных различных
# выборок в таблицы графического интерфейса
class CMyModel(QtSql.QSqlTableModel):

	# Конструктор
	def __init__(self):

		# Получение информации времени выполнения о классе QByteArray
		self.__QByteArray_type = type(QtCore.QByteArray())

		# Вызов конструктора базового класса
		QtSql.QSqlTableModel.__init__(self)

	# Метод data() вызывается при любом обновлении поля таблицы
	def data(self, index, role):

		# Обновление связано с определением выравнивания содержимого поля
		if role == QtCore.Qt.TextAlignmentRole:

			# Выравнивание - по центру поля
			return QtCore.Qt.AlignCenter

		# Обновление связано с новыми данными поля
		elif role == QtCore.Qt.DisplayRole:

			data = QtSql.QSqlTableModel.data(self, index, role)

			# В случае, если тип данных суть есть QByteArray, то данные
			# суть есть строка, которую необходимо декодировать из QByteArray
			# в Unicode (UTF-8)
			if self.__QByteArray_type == type(data):

				return data.data().decode()

			return data

		# В случае прочих обновлений - вызвать метод родительского класса
		return QtSql.QSqlTableModel.data(self, index, role)

############################################################################ 

# Главный класс графического интерфейса управления узлом
# (главный класс окна программы)
class CMainDialog(QtGui.QDialog):

	# Конструктор
	def __init__(self):

		# Вызов конструктора базового класса
		QtGui.QDialog.__init__(self)

		# Подключение описания интерфейса
		self.__ui = Ui_Dialog()
		self.__ui.setupUi(self)

		# Подключение драйвера MySQL
		self.__db = QtSql.QSqlDatabase("QMYSQL")

		# Создание пяти моделей представления результатов выборки
		self.__model = {"host_list" : CMyModel(),
						"file_list" : CMyModel(), 
						"sea_res" : CMyModel(),
						"down_list" : CMyModel(),
						"down_finish" : CMyModel()}

		# Создание пяти таблиц графического интерфейса,
		# каждая из которых связывается со своей
		# моделью представления результатов выборки
		self.__ui.host_list.setModel(self.__model["host_list"])
		self.__ui.file_list.setModel(self.__model["file_list"])
		self.__ui.sea_res.setModel(self.__model["sea_res"])
		self.__ui.down_list.setModel(self.__model["down_list"])
		self.__ui.down_finish.setModel(self.__model["down_finish"])

		self.__server = {}
		self.__filelist = None

		# Считывание параметров подключения из конфигурационного файла
		self.first_config_host = config.host
		self.first_config_mysql_port = str(config.mysql_port)
		self.first_config_route_port = str(config.route_port)
		self.first_config_upload_port = str(config.upload_port)
		self.first_config_db = config.db
		self.first_config_user = config.user

		# Обновление интерфейса
		self.conf_reset_click()

	# Обновление таблиц графического интерфейса
	def refresh_view(self):

		# Для каждой из моделей представления результатов выборки -
		# соответствующая выборка выполняется заново
		for x in self.__model:

			self.__query[x].exec_()
			self.__model[x].setQuery(self.__query[x])

		self.__ui.sea_res.setColumnHidden(0, True)
		self.__ui.sea_res.setColumnWidth(1, 500)

	# Очистка таблиц графического интерфейса
	def clean_view(self):

		for x in self.__model:

			self.__query[x].clear()
			self.__model[x].setQuery(self.__query[x])

	# Деструктор
	def main_window_close(self):

		# Останов каждого из потоков программы
		for x in self.__server.values():

			x.kill()

		# Уничтожение описателя списка файлов
		if self.__filelist != None: self.__filelist.destroy()

		# Отключение от СУБД
		self.__db.close()

	# Подключение узла к файлообменной сети
	def start_click(self):

		# Получение параметров подключения
		config.host = self.__ui.conf_host.text()
		config.mysql_port = int(self.__ui.conf_mysql.text())
		config.route_port = int(self.__ui.conf_route.text())
		config.upload_port = int(self.__ui.conf_upload.text())
		config.db = self.__ui.conf_db.text()
		config.user = self.__ui.conf_user.text()

		# Обновление списка файлов, доступных для скачивания
		# удаленными узлами файлообменной сети
		self.__filelist = filelist.CFileList()
		self.__filelist.refresh()

		# Запуск двух серверов и скачивающего потока
		try:
		
			self.__server = {"route" : route.CRouteTable(),
							 "upload" : upload.CUpload(),
							 "download" : download.CDownload()}

			for x in self.__server.values():

				x.start()

		except:

			QtGui.QMessageBox().critical(self, "Ошибка!",
																	 "Невозможно запустить один из потоков")
			return

		# Настройка параметров подключения к локальному серверу MySQL
		self.__db.setHostName("localhost")
		self.__db.setUserName(config.user)
		self.__db.setDatabaseName(config.db)

		# Подключение к локальному серверу MySQL
		if not self.__db.open():

			QtGui.QMessageBox().critical(self, "Ошибка!",
													"Невозможно подключится к локальной базе данных")
			return

		# Создание пяти описателей выборок по одной для каждой из пяти моделей
		# представления результатов выборки
		self.__query = {
			
			"host_list"		:
				QtSql.QSqlQuery("""select distinct ip as \"IP\",
													 route_port as \"Route порт\" from """ +
												tname["route"] + " order by ip, route_port",
												db = self.__db),

			"file_list"		:
				QtSql.QSqlQuery("select distinct path as \"Путь и имя файла\" from "
												+ tname["filelist"] + " order by path",
												db = self.__db),

			"sea_res"		:
				QtSql.QSqlQuery("""select id as \"Номер\", path as \"Имя файла\",
													 size / 1048576 as \"Размер файла (мегабайты)\"
													 from """ + tname["search_result"] +
												" group by path order by path, size",
												db = self.__db),

			"down_list"		:
				QtSql.QSqlQuery("""select path as \"Путь и имя файла\",
													 count(*) as \"Доступно частей\" from """
												+ tname["downlist"] +
												" group by path order by path", db = self.__db),

			"down_finish"	:
				QtSql.QSqlQuery("select distinct path \"Путь и имя файла\" from " +
												tname["finished"] + """ where not exists
												(select * from downlist
																			where downlist.path = finished.path)
												order by path""", db = self.__db)
										}

		# Обновление таблиц графического интерфейса
		self.refresh_view()

		self.__ui.conf_host_all.setEnabled(False)
		self.__ui.conf_reset.setEnabled(False)
		self.__ui.start.setEnabled(False)
		self.__ui.conf_host.setEnabled(False)
		self.__ui.conf_mysql.setEnabled(False)
		self.__ui.conf_route.setEnabled(False)
		self.__ui.conf_upload.setEnabled(False)
		self.__ui.conf_db.setEnabled(False)
		self.__ui.conf_user.setEnabled(False)

		self.__ui.stop.setEnabled(True)
		self.__ui.host_list.setEnabled(True)
		self.__ui.host_ip.setEnabled(True)
		self.__ui.host_port.setEnabled(True)
		self.__ui.host_connect.setEnabled(True)
		self.__ui.host_disconnect.setEnabled(True)
		self.__ui.file_list.setEnabled(True)
		self.__ui.file_add.setEnabled(True)
		self.__ui.file_del.setEnabled(True)
		self.__ui.sea_mask.setEnabled(True)
		self.__ui.sea_size_op.setEnabled(True)
		self.__ui.sea_size.setEnabled(True)
		self.__ui.sea_run.setEnabled(True)
		self.__ui.sea_res.setEnabled(True)
		self.__ui.sea_down.setEnabled(True)
		self.__ui.down_list.setEnabled(True)
		self.__ui.down_del.setEnabled(True)
		self.__ui.down_finish.setEnabled(True)
		self.__ui.down_finish_clear.setEnabled(True)

	# Отключение узла от файлообменной сети
	def stop_click(self):

		# Каждый из потоков останавливается
		for x in self.__server.values():

			x.kill()

		# Описатель списка файлов, доступных для скачивания удаленными узлами,
		# уничтожается
		self.__filelist.destroy()

		self.__ui.conf_host_all.setEnabled(True)
		self.__ui.conf_reset.setEnabled(True)
		self.__ui.start.setEnabled(True)
		self.__ui.conf_host.setEnabled(True)
		self.__ui.conf_mysql.setEnabled(True)
		self.__ui.conf_route.setEnabled(True)
		self.__ui.conf_upload.setEnabled(True)
		self.__ui.conf_db.setEnabled(True)
		self.__ui.conf_user.setEnabled(True)

		self.__ui.stop.setEnabled(False)
		self.__ui.host_list.setEnabled(False)
		self.__ui.host_ip.setEnabled(False)
		self.__ui.host_port.setEnabled(False)
		self.__ui.host_connect.setEnabled(False)
		self.__ui.host_disconnect.setEnabled(False)
		self.__ui.file_list.setEnabled(False)
		self.__ui.file_add.setEnabled(False)
		self.__ui.file_del.setEnabled(False)
		self.__ui.sea_mask.setEnabled(False)
		self.__ui.sea_size_op.setEnabled(False)
		self.__ui.sea_size.setEnabled(False)
		self.__ui.sea_run.setEnabled(False)
		self.__ui.sea_res.setEnabled(False)
		self.__ui.sea_down.setEnabled(False)
		self.__ui.down_list.setEnabled(False)
		self.__ui.down_del.setEnabled(False)
		self.__ui.down_finish.setEnabled(False)
		self.__ui.down_finish_clear.setEnabled(False)

		# Очистка таблиц пользовательского интерфейса
		self.clean_view()

	# Обработчик щелчка по кнопке <<Все>>
	def conf_host_all_click(self):

		self.__ui.conf_host.setText("0.0.0.0")

	# Сброс параметров подключения в значения из конфигурационного файла
	def conf_reset_click(self):

		self.__ui.conf_host.setText(self.first_config_host)
		self.__ui.conf_mysql.setText(self.first_config_mysql_port)
		self.__ui.conf_route.setText(self.first_config_route_port)
		self.__ui.conf_upload.setText(self.first_config_upload_port)
		self.__ui.conf_db.setText(self.first_config_db)
		self.__ui.conf_user.setText(self.first_config_user)

	# Подключение к удаленному узлу
	def host_connect_click(self):

		if not self.__server["route"].connect(self.__ui.host_ip.text(),
																					int(self.__ui.host_port.text())):

			QtGui.QMessageBox().critical(self, "Ошибка!",
																	 "Невозможно подключится к узлу")

		else: self.refresh_view()

	# Удаление записи об удаленном узле из таблицы маршрутизации
	def host_disconnect_click(self):

		dis_row = []
		for x in self.__ui.host_list.selectedIndexes():

			row = x.row()

			if row not in dis_row:

				dis_row.append(row)

				self.__server["route"].disconnect(
						self.__model["host_list"].record(row).value("IP"),
						str(self.__model["host_list"].record(row).value("Route порт")))
		
		self.refresh_view()

	# Добавление файла в список файлов,
	# доступных для скачивания удаленными узлами
	def file_add_click(self):

		fname = QtGui.QFileDialog.getOpenFileName(self)

		if fname != "":
		
			try:

				if not self.__filelist.add(fname):
			
					QtGui.QMessageBox().critical(self, "Ошибка!",
																			 "Невозможно добавить файл " + fname +
																			 " - данный файл уже расшарен")

			except: QtGui.QMessageBox().critical(self, "Ошибка!",
																			 "Невозможно добавить файл  " + fname)

		self.refresh_view()

	# Удаление файла из списка файлов,
	# доступных для скачивания удаленными узлами
	def file_del_click(self):

		for x in self.__ui.file_list.selectedIndexes():

			self.__filelist.delete(
					self.__model["file_list"].record(x.row()).value(
																				"Путь и имя файла").data().decode())

		self.refresh_view()

	# Запуск операции поиска
	def sea_run_click(self):

		try:

			self.__server["download"].find_file(self.__ui.sea_mask.text(),
						 self.__ui.sea_size_op.currentText(), self.__ui.sea_size.text())

		except: QtGui.QMessageBox().critical(self, "Ошибка",
																				 "Некорректный поисковый запрос")

		self.refresh_view()

	# Постановка файла на скачивание
	def sea_down_click(self):

		for x in self.__ui.sea_res.selectedIndexes():

			row = x.row()
			id = self.__model["sea_res"].record(row).value("Номер")
			dest = QtGui.QFileDialog.getSaveFileName(self,
								directory = self.__model["sea_res"].record(row).value(
																								"Имя файла").data().decode())
			
			if not self.__server["download"].download_file(id, dest):
				
				QtGui.QMessageBox().critical(self, "Ошибка",
														 "Не удалось начать скачивание выбранного файла")

		self.refresh_view()

	# Удаление файла из очереди на скачивание
	def down_del_click(self):

		for x in self.__ui.down_list.selectedIndexes():

			self.__server["download"].delete_download(
					self.__model["down_list"].record(x.row()).value(
																				"Путь и имя файла").data().decode())

		self.refresh_view()

	# Очистка списка скачанных файлов
	def down_finish_clear_click(self):

		self.__server["download"].finished_clear()
		self.refresh_view()

	# По нажатию клавиши R таблицы графического интерфейса обновляются
	def keyPressEvent(self, ev):

		if ev.key() == QtCore.Qt.Key_R:

			self.refresh_view()

############################################################################ 
# Главная функция программы

# Создание объекта - описателя Qt4 приложения
app = QtGui.QApplication(sys.argv)

# Создание объекта - описателя окна программы
main_window = CMainDialog()

# Отображение окна программы
main_window.show()

# Запуск графической части приложения
sys.exit(app.exec_())

############################################################################ 

