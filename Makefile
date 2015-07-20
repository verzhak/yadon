
############################################################################
# Вспомогательный файл сборки
############################################################################ 

# Цель - очистка каталога с исходным кодом от файлов *.pyc -
# 			 результатов компиляции модулей языка Python в промежуточный
# 			 бинарный код
clean:

	rm -f *.pyc

# Qt4-цель - компиляция XML-ресурсов программы в код языка Python
# 					 с помощью средств, предоставляемых Qt4/PyQt4
qt:

	rm -f ui_window.py resource_rc.py
	pyuic4 qt/window.ui -o ui_window.py
	pyrcc4 -py3 qt/resource/resource.qrc -o resource_rc.py

