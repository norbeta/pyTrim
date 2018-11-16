#! /usr/bin/python3
# Script for controlling G2 rPi-HAT from ProSim v1 generic TCP-driver
# Script written by Mathias Nilsen <m@thias.no>

# For communicatiotn with ProSim, use Generic TCP driver. For JRK connections,
# use COM-ports. 
#
# Remember to set up gates for "Trim motor up" and "Trim motor down". 

import socket
import sys
import threading
import time
import re
from dual_g2_hpmd_rpi import motors, MAX_SPEED

SERVER = '192.168.0.122'
PORT = 8091

global cs
global flapspos
global trimpos
global trimspeed
global trimmotor
global cmd
global kill

trimpos = "Not initialized"
trimmotor = "Not initialized"
trimspeed = "NA"
flapspos = "Not initialized"
cmd = "Not initialized"
connerrors = 0
kill = 1

def connection(SERVER, PORT):
	global cs
	global trimpos
	global flapspos
	global trimmotor
	global cmd
	global connerrors
	global kill
	
	while True:
		try:
			# Initialize socket to SERVE
			cs = "\033[1;33;40mInitializing..."
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.settimeout(30) # 30
			try:
				cs = "\033[1;33;40mTrying to connect to %s:%s" % (SERVER, PORT)
				s.connect((SERVER, PORT))
				try:
					cs = "\033[1;30;42mConnected to %s:%s" % (SERVER, PORT)
					line = b''
					while True:
						if trimmotor != "Not initialized":
							kill = 0
						part = s.recv(1)
						if part != b'\n':
							line = line + part
						elif part == b'\n':
							d = line.decode('utf-8')
							line = b''
							if d.startswith("G_PED_ELEV_TRIM"):
								spl = d.split("= ", 1)
								trimpos = spl[1]
							elif d.startswith("N_TRIM_MOTOR_VALUE"):
								spl = re.split(" = |\r", d)
								if spl[1] == "1":
									trimmotor = "Up"
								elif spl[1] == "-1":
									trimmotor = "Down"
								else:
									trimmotor = "Brake"
							elif d.startswith("B_FLAP_"):
								spl = re.split(' = |_', d)
								if "1" in spl[3]:
									flapspos = spl[2]
							elif d.startswith("B_PITCH_CMD"):
								spl = re.split(" = |\r", d)
								if spl[1] == "1":
									cmd = "Engaged"
								else:
									cmd = "Disengaged"


				except socket.timeout:
					kill = 1
					cs = "\033[1;37;41mNothing received in a while. Reconnecting. "

			except socket.error as msg:
				kill = 1
				cs = "\033[1;37;41mCould not connect to ProSIM on %s:%s -> %s. Retrying.." % (SERVER, PORT, msg)
				time.sleep(.5)
			
		finally:
			connerrors += 1
			s.close()

def settrimspeed():
	global trimspeed
	while True:
		if flapspos == "Not initialized":
			trimspeed = "NA"
		elif cmd is "Disengaged" and flapspos is "0":
			trimspeed = 300
		elif cmd is "Disengaged" and flapspos is not "0":
			trimspeed = 480
		elif cmd is "Engaged" and flapspos is "0":
			trimspeed = 240
		elif cmd is "Engaged" and flapspos is not "0":
			trimspeed = 400
		else:
			kill = 1
		time.sleep(.1)

def motorcontrol():
	global motorstatus
	global motorspeed
	motorstatus = "Disabled"
	motorspeed = 0
	while True:
		if kill == 1:
			motors.motor1.disable()
			motorstatus = "Disabled"
			time.sleep(1)
		elif (trimspeed == 300 or trimspeed == 480 or trimspeed == 240 or trimspeed == 400):
			motors.motor1.setSpeed(0)
			motorspeed = 0
			motors.motor1.enable()
			motorstatus = "Enabled"
			if trimmotor is "Up":
				if trimspeed is not 480:
						motors.motor1.setSpeed(480)
						motorspeed = 480
						time.sleep(.2)
				while trimmotor is "Up":
					motorspeed = trimspeed
					motors.motor1.setSpeed(motorspeed)
					time.sleep(.01)
			elif trimmotor is "Down":
				if trimspeed is not 480:
					motors.motor1.setSpeed(-480)
					motorspeed = -480
					time.sleep(.2)
				while trimmotor is "Down":
					motorspeed = trimspeed * -1
					motors.motor1.setSpeed(motorspeed)
					time.sleep(.01)
			else:
				motors.motor1.setSpeed(0)
				motorspeed = 0
			time.sleep(.01)
		else:
			motors.motor1.disable()
			motorstatus = "Disabled"
			time.sleep(.01)
			
def status():
	while True:
		print(chr(27) + "[2J")
		print("\033[0;0H", end="")
		print(" - pyTrim - ")
		print("Connection status: " +cs)
		print("\033[0;37;40m", end="")
		print("Connection errors: " +str(connerrors), end="\r\n\n\n")
		print("Trim position: \t\t" +str(trimpos))
		print("Trim motor (from sim): \t" +trimmotor)
		print("Trim speed: \t\t" +str(trimspeed), end="\r\n\n")
		print("Flaps position: \t" +str(flapspos))
		print("Autopilot: \t\t" +cmd, end="\r\n\n\n")
		print("Actual motorstatus: \t" +motorstatus)
		print("Actual motorspeed: \t" +str(motorspeed))
		print("Killswitch: \t\t" +str(kill))
		print("\033[0;37;40m", end="")
		time.sleep(.1)

threading.Thread(target=connection, args=(SERVER,PORT)).start()
threading.Thread(target=settrimspeed).start()
threading.Thread(target=motorcontrol).start()
threading.Thread(target=status).start()


