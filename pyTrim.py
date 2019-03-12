#!/usr/bin/env python3
# Script for controlling Pololi G2 rPi-HAT from ProSim v1 generic TCP-driver
# Script written by Mathias Nilsen <m(a)thias.no>
# Licence? Use if you want, but if you make it better or it is handy for your
# project, please tell me. :-)

# 

import socket
import sys
import threading
import time
import re
from dual_g2_hpmd_rpi import motors, MAX_SPEED

# This is the only thing you need to edit here.. 
SERVER = '10.0.10.120'
PORT = 8091

global cs
global flapspos
global trimpos
global trimspeed
global trimmotor
global cmd
global kill
global speedbrake

trimpos = "Not initialized"
trimmotor = "Not initialized"
trimspeed = "NA"
flapspos = "Not initialized"
cmd = "Not initialized"
speedbrake = "Not initialized"
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
	global speedbrake
	
	while True:
		try:
			# Initialize socket to SERVER
			cs = "\033[1;33;40mInitializing..."
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.settimeout(30) # 30
			try:
				cs = "\033[1;33;40mTrying to connect to %s:%s" % (SERVER, PORT)
				s.connect((SERVER, PORT))
				try:
					#s.send(b'filter G_PED_ELEV_TRIM')
					#s.send(b'filter N_TRIM_MOTOR_VALUE')
					#s.send(b'filter B_FLAP')
					#s.send(b'filter B_PITCH_CMD')
					#s.send(b'B_SPEED_BRAKE')
					cs = "\033[1;30;42mConnected to %s:%s" % (SERVER, PORT)
					line = b''
					while True:
						if trimmotor != "Not initialized":
							kill = 0
						msg, ancmsg, flags, addr = s.recvmsg(8148)
						d = msg.decode('utf-8').rstrip()
						#part = s.recv(1)
						#if part != b'\n':
							#line = line + part
						#elif part == b'\n':
							#d = line.decode('utf-8')
							#line = b''
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
						elif d.startswith("B_SPEED_BRAKE_DEPLOY = 1"):
							speedbrake = "DEPLOY"
						elif d.startswith("B_SPEED_BRAKE_RESTOW = 1"):
							speedbrake = "RESTOW"
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
			trimspeed = 113
		elif cmd is "Disengaged" and flapspos is not "0":
			trimspeed = 175
		elif cmd is "Engaged" and flapspos is "0":
			trimspeed = 90
		elif cmd is "Engaged" and flapspos is not "0":
			trimspeed = 135
		else:
			kill = 1
		time.sleep(.2)

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
		elif (trimspeed == 113 or trimspeed == 175 or trimspeed == 90 or trimspeed == 135):
			motors.motor1.setSpeed(0)
			motorspeed = 0
			motors.motor1.enable()
			motorstatus = "Enabled"
			if trimmotor is "Up":
				if trimspeed is not 480: # Give some boost if not max speed
					motors.motor1.setSpeed(480)
					motorspeed = 480
					if trimspeed == 175:
						time.sleep(.25)
					elif trimspeed == 135:
						time.sleep(.2)
					elif trimspeed == 113:
						time.sleep(.15)
					elif trimspeed == 90:
						time.sleep(.15)
					else:
						time.sleep(.15)
				while trimmotor is "Up":
					motorspeed = trimspeed
					motors.motor1.setSpeed(motorspeed)
					time.sleep(.01)
				motors.motor1.setSpeed(-480)
				if trimspeed == 175:
					time.sleep(.23)
				elif trimspeed == 90:
					time.sleep(.12)
				else:
					time.sleep(.15)
				motors.motor1.setSpeed(0)
			elif trimmotor is "Down":
				if trimspeed is not 480: # Give some boost if not max speed
					motors.motor1.setSpeed(-480)
					motorspeed = -480
					if trimspeed == 175:
						time.sleep(.25)
					elif trimspeed == 135:
						time.sleep(.2)
					elif trimspeed == 113:
						time.sleep(.15)
					elif trimspeed == 90:
						time.sleep(.15)
					else:
						time.sleep(.15)
				while trimmotor is "Down":
					motorspeed = trimspeed * -1
					motors.motor1.setSpeed(motorspeed)
					time.sleep(.01)
				motors.motor1.setSpeed(480)
				if trimspeed == 175:
					time.sleep(.22)
				elif trimspeed == 90:
					time.sleep(.12)
				else:
					time.sleep(.15)
				motors.motor1.setSpeed(0)
			else:
				motors.motor1.setSpeed(0)
				motorspeed = 0
			time.sleep(.1)
		else:
			motors.motor1.disable()
			motorstatus = "Disabled"
			time.sleep(.1)
			
def speedbrakecontrol():
	global speedbrake
	time.sleep(1)
	motors.motor2.enable()
	motors.motor2.setSpeed(0)
	speedbrake = "Brake"
	while True:
		if speedbrake == "DEPLOY":
			#motors.motor2.enable()
			motors.motor2.setSpeed(-300)
			time.sleep(.9)
			motors.motor2.setSpeed(0)
			#motors.motor2.disable()
			speedbrake = "Brake"
		elif speedbrake == "RESTOW":
			#motors.motor2.enable()
			motors.motor2.setSpeed(300)
			time.sleep(.9)
			motors.motor2.setSpeed(0)
			#motors.motor2.disable()
			speedbrake = "Brake"
		time.sleep(.2)

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
		print("Killswitch: \t\t" +str(kill), end="\r\n\n")
		print("Speedbrake: \t\t" +speedbrake)
		print("\033[0;37;40m", end="")
		time.sleep(.5)

threading.Thread(target=connection, args=(SERVER,PORT)).start()
threading.Thread(target=settrimspeed).start()
threading.Thread(target=motorcontrol).start()
threading.Thread(target=status).start()
threading.Thread(target=speedbrakecontrol).start()

