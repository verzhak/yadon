#!/usr/bin/python3

# Разнообразный отладочный мусор

import route, upload, download, filelist, sys, time, signal

filelist = filelist.CFileList()
filelist.refresh()

s_route = route.CRouteTable()
s_up = upload.CUpload()
s_down = download.CDownload()

s_route.start()
s_up.start()
s_down.start()

def term(signum, frame):

	print("END")
	print("IN1")
	s_route.kill()
	print("IN2")
	s_up.kill()
	print("IN3")
	s_down.kill()
	print("IN4")
	filelist.destroy()
	print("FINISH END")
	exit(0)

signal.signal(signal.SIGTERM, term)

print("BEGIN")

#s_down.find_file("%арик%", ">", "0")
#s_down.download_file(1, "/home/amv/trash/1.avi")

#s_down.find_file("%.jpg", "<", "10000000")
#s_down.download_file(1, "/home/amv/trash/1.jpg")

while True:
	sys.stdin.read(1)

