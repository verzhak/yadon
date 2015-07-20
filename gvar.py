#!/usr/bin/python3

############################################################################ 
# Глобальные, не являющиеся конфигурационными, переменные
############################################################################ 

# Список названий таблиц
#
#	(ключ : название)
#
tname = {
					"route" : "route", "filelist" : "filelist",
					"partlist" : "partlist", "search_result" : "search_result",
					"downlist" : "downlist", "finished" : "finished"
				}

# Список названий хранимых процедур
#
# (ключ : название)
#
pname = {
					"delete_from_filelist" : "delete_from_filelist",
					"put_in_finished_table" : "put_in_finished_table"
				}

# Размер блока файла
#
# (1 мегабайт)
#
part_size = 1 << 20

