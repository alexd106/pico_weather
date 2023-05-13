"""
Raspberry pi Pico W weather station
Circuitpython 8.05
version: 0.3
Author: AD
2023-05-08

Collect sensor data and send to MQTT broker on raspberry pi using MiniMQTT
"""
import board
import os
import socketpool
import wifi
import alarm
import time
import gc
import adafruit_veml7700
from math import pi
from digitalio import DigitalInOut, Direction, Pull
from analogio import AnalogIn
import adafruit_ntp
from busio import I2C
from json import dumps
import rtc
from adafruit_bme280 import basic as adafruit_bme280
import adafruit_max1704x
from microcontroller import reset
import adafruit_minimqtt.adafruit_minimqtt as MQTT

gc.collect()

# Initialise constants and variables
windCount = 0
rainCount = 0
RADIUS = 9.0
BUCKET_SIZE = 0.2794
# WIND_INT = 5 # interval to calculate mean wind speed
RECORD_INT = 60 # interval to calculate mean and max wind speed
REPORTING_INT = 510 # reporting interval
MY_TZ_OFFSET = 0 # GMT

bme280_addr = 0x77
veml_addr = 0x10
max_addr = 0x36

def take_nap(nap_duration):
  time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + nap_duration)
  #print("Sleeping for: {0}".format(time_alarm.monotonic_time - time.monotonic()))
  alarm.exit_and_deep_sleep_until_alarms(time_alarm)

def connect_wifi():
    try:
        print("Connecting to WiFi")
        wifi.radio.connect(os.getenv('WIFI_SSID'), os.getenv('WIFI_PASSWORD'))
        print("Connected to WiFi")
    except Exception as e:
        print("Cannot connect to wifi\n", e)
        take_nap(300)

def push_mqtt(payload):
    try:
        mqtt_client.connect()
        mqtt_client.loop()
        mqtt_client.publish(mqtt_root_topic+mqtt_topic, dumps(payload))
    except Exception as e:
        print("MQTT failed\n", e)
        take_nap(300)

# create I2C bus
try:
    i2c = I2C(scl=board.GP17, sda=board.GP16, frequency=200_000)
    tsl_b280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, bme280_addr)  # address = 0x77
    tsl_veml = adafruit_veml7700.VEML7700(i2c, veml_addr)   # address = 0x10
except Exception as e:
    print("I2C exception occured!\n", e)
    take_nap(300)

# create I2C2 bus - battery monitor
try:
    i2c2 = I2C(scl=board.GP19, sda=board.GP18, frequency=200_000)
    maxBat = adafruit_max1704x.MAX17048(i2c2, max_addr)  # address = 0x36
except Exception as e:
    print("I2C exception occured!\n", e)
    take_nap(300)

# add rain gauge
rainInput = DigitalInOut(board.GP3)
rainInput.direction = Direction.INPUT
rainInput.switch_to_input(pull=Pull.UP)
rainFlag = 0

# add Anenometer
windInput = DigitalInOut(board.GP4)
windInput.direction = Direction.INPUT
windInput.switch_to_input(pull=Pull.UP)
windFlag = 0

# add wind vane
windDir = AnalogIn(board.GP26)

# MQTT topics
mqtt_root_topic = "pico_sensor/"
mqtt_topic = "pico_data"

# define callback methods
def connect(mqtt_client, userdata, flags, rc):
    print("Connected to MQTT broker on topic    %s" % mqtt_root_topic+mqtt_topic)
    print("Flags: {0}\n RC: {1}".format(flags, rc))

def disconnect(mqtt_client, userdata, rc):
    print("Disconnected from MQTT Broker!")

def publish(mqtt_client, userdata, topic, pid):
    print("Published to {0} with PID {1}".format(mqtt_root_topic+mqtt_topic, pid))

# read BME280 sensor
def read_bme():
    try:
        temp = round(tsl_b280.temperature, 2)
        humid = round(tsl_b280.humidity ,2)
        press = round(tsl_b280.pressure,2)
        time.sleep(1)
        return(temp, humid, press)
        gc.collect()
    except Exception as e:
        print("Failed to read BME280 sensor\n", e)
        take_nap(300)

# read VEML7700 light sensor
def read_light():
    try:
        amb_light = tsl_veml.light
        lux = round(tsl_veml.lux, 2)
        return(amb_light, lux)
    except Exception as e:
        print("Failed to read VEML7700 sensor\n", e)
        nap_time(300)

# read max17048 battery monitor
def read_batt():
    try:
        bat_volt = round(maxBat.cell_voltage, 2)
        bat_perc = int(maxBat.cell_percent)
        return(bat_volt, bat_perc)
    except Exception as e:
        print("Failed to read battery\n", e)
        nap_time(300)

# Calculate Wind Direction and return as a a string
def calculate_wind_direction():
    s = "N/A"
    deg = 999.9
    reading = windDir.value / 64 # Read A0, convert to 10-bit (0-1023)

    if 250 <= reading <= 284:
        s = "ESE"
        deg = 112.5
    elif 285 <= reading <= 304:
        s = "ENE"
        deg = 67.5
    elif 305 <= reading <= 324:
        s = "E"
        deg = 90.0
    elif 325 <= reading <= 374:
        s = "SSE"
        deg = 157.5
    elif 375 <= reading <= 450:
        s = "SE"
        deg = 135.5
    elif 451 <= reading <= 509:
        s = "SSW"
        deg = 202.5
    elif 510 <= reading <= 549:
        s = "S"
        deg = 180.0
    elif 550 <= reading <= 649:
        s = "NNE"
        deg = 22.5
    elif 650 <= reading <= 724:
        s = "NE"
        deg = 45.0
    elif 725 <= reading <= 797:
        s = "WSW"
        deg = 247.5
    elif 798 <= reading <= 824:
        s = "SW"
        deg = 225.0
    elif 825 <= reading <= 874:
        s = "NNW"
        deg = 337.5
    elif 875 <= reading <= 909:
        s = "N"
        deg = 0.0
    elif 910 <= reading <= 934:
        s = "WNW"
        deg = 292.5
    elif 935 <= reading <= 974:
        s = "NW"
        deg = 315.0
    elif 975 <= reading <= 1023:
        s = "W"
        deg = 270.0
    else:
        s = "N/A"
        deg = 999.9
    
    return(s, deg)

# rain gauge
def get_rain():
    global rainInput, rainFlag
    if(rainInput.value == 0 and rainFlag == 1): # Compare to our flag to look for a LOW transit
        global rainCount # Ensure we write to the global count variable
        rainCount += 1 # Since the sensor has transited low, increase the count by 1
    rainFlag = rainInput.value # Set our flag to match our input

# anemometer
def get_wind():
    global windInput, windFlag
    if(windInput.value ==  0 and windFlag == 1): # Compare to our flag to look for a LOW transit
        global windCount # Ensure we write to the global count variable
        windCount += 1 # Since the sensor has transited low, increase the count by 1
    windFlag = windInput.value # Set our flag to match our input

# return windspeed mph
def calculate_speed(windcount, time_sec, radius_cm):
    circumference_cm = (2 * pi) * radius_cm
    rotations = windcount / 2.0
    dist_km = (circumference_cm * rotations) / 100000.0
    km_per_sec = dist_km / time_sec
    km_per_hour = (km_per_sec * 3600) * 1.18
    miles_per_hour = km_per_hour * 0.6213711922
    return (miles_per_hour)

# convert barometric pressure to atmospheric
def baro_atmos(value, temp):
    h = 100
    atmosP = value * (1 - (0.0065 * h / (temp + 0.0065 * h + 273.15))) ** -5.257
    return(atmosP)

connect_wifi()
pool = socketpool.SocketPool(wifi.radio)

# synchronise rtc with ntp
try:
    ntp = adafruit_ntp.NTP(pool, tz_offset = MY_TZ_OFFSET)
    rtc.RTC().datetime = ntp.datetime
except Exception as e:
    print("Could not retreive RTC, falling back to system time\n", e)
    rtc.RTC().datetime = rtc.RTC().datetime # fallback

# set up a MQTT Client
mqtt_client = MQTT.MQTT(
    broker = os.getenv('BROKER_IP'),
    port = os.getenv('BROKER_PORT'),
    username = os.getenv('BROKER_USR'),
    password = os.getenv('BROKER_PASSWD'),
    socket_pool = pool)

# connect callback handlers to mqtt_client
mqtt_client.on_connect = connect
mqtt_client.on_disconnect = disconnect
mqtt_client.on_publish = publish
gc.collect()

start_time = time.time()
while time.time() - start_time <= RECORD_INT:
    get_rain()
    get_wind()
    # wind_start_time = time.time()
    # while time.time() - wind_start_time <= WIND_INT:
    #     pass

gc.collect()
bmeDat = read_bme()
dewpnt = round(((bmeDat[1] / 100) ** 0.125) * (112 + 0.9 * bmeDat[0]) + (0.1 * bmeDat[0]) - 112, 2)
atmosPr = baro_atmos(bmeDat[2], bmeDat[0])
gc.collect()
lightDat = read_light()
batDat = read_batt()
now = time.localtime()
rainfall = round(rainCount * BUCKET_SIZE, 2)
windHeading = calculate_wind_direction()
# print(windHeading)
measuredWind = round(calculate_speed(windCount, RECORD_INT, RADIUS), 2)
timestamp = "{0:04d}-{1:02d}-{2:02d} {3:02d}:{4:02d}:{5:02d}".format(now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min, now.tm_sec)
freemem = gc.mem_free()

payload = {'DATETIME': timestamp,
           'TEMP': bmeDat[0],
           'DEWPNT': dewpnt,
           'HUMID': bmeDat[1],
           'PRESS': atmosPr,
           'LIGHT': lightDat[0],
           'LUX': lightDat[1],
           'FREEMEM': freemem,
           'WINDDIR': windHeading[0],
           'WINDDEG': windHeading[1],
           'RAIN': rainfall,
           'WINDSPEED': measuredWind,
           'BATVOLT': batDat[0],
           'BATPERC': batDat[1]
           }
# print(payload)
push_mqtt(payload)

rainCount = 0
windCount = 0
del(bmeDat, lightDat, now, timestamp, freemem, payload, windHeading)
gc.collect()
take_nap(REPORTING_INT)

