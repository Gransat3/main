# TEAM: GRANSAT 3
# HIGH SCHOOL: IES GRANADILLA DE ABONA
# DATE: MAYO 2023
# MEMBERS:
# Carlos Buján
# Mateo Reyes
# Pablo Delgado
# María Angélica Rodríguez
# Carlos Cano
# Pablo Delgado

#Import libraries
from datetime import datetime, timedelta
import csv
from csv import writer
from pathlib import Path
from picamera import PiCamera
import os
import math
import adafruit_mpu6050
import time
import board
import adafruit_bmp3xx
import RPi.GPIO as GPIO
import serial
import sys, sx126x, threading, select, termios, tty
import pynmea2

# Delete old datas
os.system('rm data.csv')
os.system('rm -r \img')
os.system('mkdir img')

# Configure mode of GPIO
GPIO.setmode(GPIO.BCM)

# Configure BUZZER pin 24 as  exit
buzzer = 24
GPIO.setup(buzzer, GPIO.OUT)

# Configure LED pin 23 as output
led_pin = 23
GPIO.setup(led_pin, GPIO.OUT)
GPIO.output(led_pin,GPIO.HIGH) #Turn on Led

# BMP 390
i2c = board.I2C()
bmp = adafruit_bmp3xx.BMP3XX_I2C(i2c, 0x76)
bmp.sea_level_pressure = 1013.25

# Record the start and current time
start_time = datetime.now()
now_time = datetime.now()
cont = 0

# Establish the set up for the camera
contfoto = 0
nom_foto = ("NoFoto")

# MPU 6050
mpu = adafruit_mpu6050.MPU6050(i2c,0x68)

# Camera Pi
camera = PiCamera()
width = 2592
height = 1944
camera.resolution = (width, height)

# Comunication
old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())
node = sx126x.sx126x(serial_num = "/dev/ttyS0",freq=868,addr=0,power=22,rssi=True,air_speed=2400,relay=False)

# Function of comunication
def send_deal(Message):
    radioCnst = "0,868,"
    Message = str(radioCnst+Message)
    result=Message.split(",")
    
    offset_frequence = int(result[1])-(850 if int(result[1])>850 else 410)
    #         receiving node              receiving node                   receiving node           own high 8bit           own low 8bit                 own 
    #         high 8bit address           low 8bit address                    frequency                address                 address                  frequency             message payload
    data = bytes([int(result[0])>>8]) + bytes([int(result[0])&0xff]) + bytes([offset_frequence]) + bytes([node.addr>>8]) + bytes([node.addr&0xff]) + bytes([node.offset_freq]) + result[2].encode()
    node.send(data)

# Function to write to CSV
def create_csv_file():
    with open('data.csv', 'w', newline='') as f:   
        data_writer = writer(f)
        data_writer.writerow(['Fecha', 'Hora', 'Presión', 'Temperatura', 'Altitud','Posición en X','Posición en Y','Aceleración en X','Foto', 'Validación', 'Latitud', 'Longitud','xacc','yacc','zacc','xgyro','ygyro','zgyro'])

# Function to add a row to the data.csv
def add_csv_data(data):
    """Add a row of data to the data_file CSV"""
    with open('data.csv', 'a') as f:
        writer = csv.writer(f)
        writer.writerow(data)

# Function to collect data 
def get_sense_data():
    sense_data = []

    Pressure = "{:6.1f}".format(bmp.pressure)
    Temperature = "{:5.2f}".format(bmp.temperature)
    Altitude = round(bmp.altitude,2)

    # Date and Time
    now_time = datetime.now()
    fechayhora = str(now_time)
    Date = fechayhora [0:10]
    Hour = fechayhora [11:19]

    xacc, yacc, zacc = mpu.acceleration
    xgyro, ygyro, zgyro = mpu.gyro
    xacc = round(xacc,6)
    yacc = round(yacc,6)
    zacc = round(zacc,6)
    xgyro = round(xgyro,6)
    ygyro = round(ygyro,6)
    zgyro = round(zgyro,6)
    posx = math.atan(xacc/math.sqrt(pow(yacc,2) + pow(zacc,2)))*(180.0/3.14)
    posy = math.atan(yacc/math.sqrt(pow(xacc,2) + pow(zacc,2)))*(180.0/3.14) 
    
    # Image validation
    if posx < -20 or posx > 20 or posy < -20 or posy > 20:
        pos = ("invalida")
    else:
        pos = ("valida")
    
    #GPS 
    gps = False
    while (gps == False):
    port = "/dev/ttyS0"
    ser = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=0.5)
    dataout = pynmea2.NMEAStreamReader()
    newdata=ser.readline().decode('unicode_escape')
    newdata = str(newdata)

    if newdata[0:6] == "$GNRMC":
        newmsg=pynmea2.parse(newdata)
        lat=newmsg.latitude
        lng=newmsg.longitude
        gps = "Latitude=" + str(lat) + " Longitude=" + str(lng)
        print(gps)
        gps = True
    else:
        lat = 0
        lng = 0
    
    sense_data.append(Date)
    sense_data.append(Hour)
    sense_data.append(Pressure)
    sense_data.append(Temperature)
    sense_data.append(Altitude)
    sense_data.append(posx)
    sense_data.append(posy)
    sense_data.append(nom_foto)
    sense_data.append(pos)
    sense_data.append(lat)
    sense_data.append(lng)
    sense_data.append(xacc)
    sense_data.append(yacc)
    sense_data.append(zacc)
    sense_data.append(xgyro)
    sense_data.append(ygyro)
    sense_data.append(zgyro)

    send_deal(" GRANSAT Nombre: {} --- Pressure: {} Bar --- Temperature: {} Grados --- Altitude: {} Metros --- Latitud: {} --- Longitude: {}".format(
            nom_foto,
            Pressure,
            Temperature,
            Altitude,lat,lng))
    return sense_data

create_csv_file ()
while (now_time < start_time + timedelta(minutes=180)):
    try:
        data = get_sense_data()
        print (data)
        add_csv_data(data)
        cont += 1
        if (cont % 5) == 0:
            contfoto += 1
            camera.capture('./img/image%s.jpg' % contfoto)
            nom_foto = ("image%s.jpg" % contfoto)
            GPIO.output(buzzer,GPIO.HIGH)# Turn on buzzer
        else:
            nom_foto = ("NoFoto")
            time.sleep(1)
            GPIO.output(buzzer,GPIO.LOW)
    except:
        GPIO.output(buzzer, GPIO.LOW)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            
# Turn off led
GPIO.output(led_pin,GPIO.LOW)        

# Finish the program
print("exiting the program")
print(os._exit(0))
