import serial
import time
import binascii
import datetime

s = None

password = bytearray(b'\x30\x30\x30\x30\x30\x30\x30\x30')         #default password:  00000000
password = bytearray(b'\x30\x30\x30\x31\x41\x42\x43\x44')         #default password level 1 0001ABDC
password = "ABCD0002"         #default password level 2 ABCD0002
#password = bytearray(b'\x46\x45\x44\x43\x30\x30\x30\x33')         #default password level 3 FEDC0003

def open():
	global s

	s = serial.Serial()
	s.port = "/dev/ttyUSB0"
	s.baudrate = 9600
	s.bytesize = serial.SEVENBITS           #number of bits per bytes
	s.parity = serial.PARITY_EVEN           #set parity check: EVEN
	s.stopbits = serial.STOPBITS_ONE        #number of stop bits
	s.timeout = 0.5                         #non-block read
	s.xonxoff = False                       #disable software flow control
	s.rtscts = False                        #disable hardware (RTS/CTS)
	try:
		s.open()
		print ('{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now()) + '   ###   :' + 'Begining communication')
	except Exception as e:
		print ("Error attemping to open serial port: " + str(e))
		exit()


def printLine(message, dir):
	if type(message) != "str":
		message = str(message)
	m2 = ""
	for m in message:
		c = binascii.hexlify(m)
		if c == "01":
			m2 += '<SOH>'
		elif c == "02":
			m2 += '<STX>'
		elif c == "03":
			m2 += '<ETX>'
		elif c == "0a":
			m2 += '<LF>'
		elif c == "0d":
			m2 += '<CR>'
		elif c == "06":
			m2 += '<ACK>'
		elif c == "15":
			m2 += '<NAK>'
		else:
			m2 += m

	print(dir + " " + m2)

	if dir == "RX":
		print ""


def getLine():
	message = []
	while True:
		c = s.read()
		if not c: break
		message.append(c)
	message = b''.join(message)
	printLine(message, 'RX')
	return message


def sendLine(message):
	s.write(message)
	printLine(message, 'TX')


def getId():
	message = bytearray(b'\x2F\x3F\x21\x0D\x0A')    #Sends command: /?!<CR><LF> to begin communication
	sendLine(message)
	return getLine()


def HangUp():
	message = bytearray(b'\x01\x42\x30\x03\x71')    #Sends command: /?!<CR><LF> to begin communication
	sendLine(message)
	return getLine()


def modeSwitchRequest():
	message = bytearray(b'\x06\x30\x35\x31\x0D\x0A')
	sendLine(message)
	time.sleep(0.2)     #Waits to send the whole message before changing port setup.
	s.baudrate = 9600
	return getLine()


def decryptA1700(seed, password):
	crypted = bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00')
	password = bytearray(password, 'ascii')

	for i in range (0, 8):
		crypted[i]= password[i] ^ seed[i]
	last = crypted[7]
	for i in range (0, 8):
		crypted[i] = (crypted[i] + last) & 0xFF
		last = crypted[i]

	crypted = (binascii.hexlify(crypted)).swapcase()
	return crypted


def getCRC(message):
	crc=0
	for b in message:
		crc = crc ^ b
	return crc
	
def convertReading(reading):
	#	Flip pairs of bytes in the reversed string
	tmp=""
	for i in range (0, 16, 2):
		tmp += reading[::-1][i+1]
		tmp += reading[::-1][i]

	return int(tmp)
	

open()

identidad = getId()

if identidad:
	seed = modeSwitchRequest()
	
	seed = bytearray.fromhex(seed[5:21])

	pw = decryptA1700(seed, password)

	#	Send hashed password
	message = bytearray(b'\x50\x32\x02\x28')
	message.extend(pw)
	message.extend(b'\x29\x03')

	send = bytearray(b'\x01')
	send.extend(message)
	send.append(getCRC(message))

	sendLine(send)
	response = getLine()

	for i in range (0, len(response)):
		if response[i] != b'\x06':
			print("Invalid response")
			HangUp()
			break

	#	Request reading
	message = bytearray(b'\x01\x52\x31\x02\x35\x30\x37\x30\x30\x31\x28\x34\x30\x29\x03\x64')
	sendLine(message)
	response = getLine()
	
	if response[0] == '\x02' and response[1] == '\x28':
		mImport = convertReading(response[2:18])
		mExport = convertReading(response[18:34])
		
		print "Import:", mImport
		print "Export:", mExport
		
HangUp()

s.close()
