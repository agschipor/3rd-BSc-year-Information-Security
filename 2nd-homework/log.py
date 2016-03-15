import time

def info(message):
	date = str(time.ctime())
	
	fd = open("log", "a")

	fd.write("[" + date + "] " + message + "\n")

	fd.close()
