import time
import machine
import aht21
import mpu6050
import json
import network
import robust
import ssl

time.sleep(5)

# Load Configuration
config_file = open("config.json")
config = json.load(config_file)

print("Config File Loaded")


# AHT21 Setup
aht21_config = config["aht21"]
i2c_aht21 = machine.SoftI2C(scl=machine.Pin(int(aht21_config['scl'])),sda=(int(aht21_config['sda'])))
aht_sensor = aht21.AHT21(i2c_aht21)

print("AHT21 Sensor Config Loaded")


# MPU6050 Setup
mpu6050_config = config["mpu6050"]
i2c_mpu6050 = machine.SoftI2C(scl=machine.Pin(int(mpu6050_config['scl'])), sda=machine.Pin(int(mpu6050_config['sda'])))
mpu6050_sensor = mpu6050.MPU6050(i2c_mpu6050)
mpu6050_threshold = mpu6050_config["threshold"]

print("MPU6050 Sensor Config Loaded")


# W5500 Setup
w5500_config = config["w5500"]
spi_w5500 = machine.SPI(0,2_000_000, mosi=machine.Pin(w5500_config["mosi"]), miso=machine.Pin(w5500_config["miso"]), sck=machine.Pin(w5500_config["sck"]))
nic = network.WIZNET5K(spi_w5500,machine.Pin(w5500_config["cs"]),machine.Pin(w5500_config["rst"]))
nic.active(False)
nic.active(True)
nic.ifconfig("dhcp")
while not nic.isconnected():
    time.sleep(1)
    print(nic.regs())
print(nic.ifconfig())

print("W5500 Config Loaded")


# MQTT Setup
mqtt_config = config["mqtt"]
mqtt_server = mqtt_config["server"]
mqtt_clientid = mqtt_config["clientid"]
mqtt_keepalive = mqtt_config["keepalive"]
mqtt_user = mqtt_config["user"]
mqtt_password = mqtt_config["password"]
mqtt_port = mqtt_config["port"]
mqtt_topic = mqtt_config["topic"]
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.verify_mode = ssl.CERT_NONE

print("MQTT Config Loaded")

mqtt_client = robust.MQTTClient(mqtt_clientid, mqtt_server, keepalive=mqtt_keepalive, user=mqtt_user, password=mqtt_password, port=mqtt_port, ssl=context)
mqtt_client.connect()
print("Connected to MQTT")


# AHT21 Read
def aht21_read(sensor_object):    
    aht_sensor_read = sensor_object.read()
    aht_humidity = str(round(float(aht_sensor_read[0]),2))
    aht_temperature = str(round(float(aht_sensor_read[1]),2))
    return(aht_temperature, aht_humidity)


# MPU6050 Read
def mpu6050_read(sensor_object):
    sensor_object.wake()
    acceleration = sensor_object.read_accel_data()
    x_axis = round(acceleration[0],2)
    y_axis = round(acceleration[1], 2)
    z_axis = round(acceleration[2], 2)    
    acceleration_return = (x_axis, y_axis, z_axis)
    return(acceleration_return)


# MPU6050 Detect Movement Above Threshold
def mpu6050_detect_movement(sensor_object, mpu6050_data):
    motion_detected = False 
    current_read = mpu6050_read(sensor_object)
    
    # Read current Gyro Information
    x_axis = round(current_read[0],2)
    y_axis = round(current_read[1], 2)
    z_axis = round(current_read[2], 2)
    
    # Create useable Gyro Stats
    try:
        x_axis_delta = round((abs(abs(x_axis) - abs(mpu6050_data[0])) / abs(mpu6050_data[0])) * 100, 2)
    except ZeroDivisionError:
        x_axis_delta = 0
    if x_axis_delta == 100:
        x_axis_delta = 0
    try:
        y_axis_delta = round((abs(abs(y_axis) - abs(mpu6050_data[1])) / abs(mpu6050_data[1])) * 100, 2)
    except ZeroDivisionError:
        y_axis_delta = 0
    if y_axis_delta == 100:
        y_axis_delta = 0
    try:
        z_axis_delta = round((abs(abs(z_axis) - abs(mpu6050_data[2])) / abs(mpu6050_data[2])) * 100, 2)
    except ZeroDivisionError:
        z_axis_delta = 0
    if z_axis_delta == 100:
        z_axis_delta = 0
    
    # Determine if motion occured on any axis
    if (x_axis_delta > mpu6050_threshold) or (y_axis_delta > mpu6050_threshold) or (z_axis_delta > mpu6050_threshold):
        motion_detected = True
    else:
        motion_detected = False
    # Format Gyro Data Return
    mpu6050_data = (x_axis, y_axis, z_axis)
    return(x_axis, y_axis, z_axis, motion_detected)


#Primary Loop Logic
def main_loop(mpu6050_startup, mqtt_client, mqtt_topic, sleep_time):
    mpu6050_data = mpu6050_startup
    while True:
        # Read Temp and Humidity
        aht21_reading = aht21_read(aht_sensor)
        temperature = aht21_reading[0]
        humidity = aht21_reading[1]
        # Detect Motion
        motion_detected = mpu6050_detect_movement(mpu6050_sensor, mpu6050_data)
        mpu6050_data = motion_detected
        #Format MQTT Data
        mqtt_data = {
            "temperature ": temperature,
            "humidity" : humidity,
            "motion" : motion_detected[3],
            }        
        mqtt_data = str(mqtt_data)
        # Print to Environment Data to Console
        print("Temperature: " + temperature)
        print("Humidity: " + humidity)
        print("Motion Detected: " + str(motion_detected[3]))
        
        #Send MQTT
        mqtt_client.connect
        mqtt_client.publish(mqtt_topic, mqtt_data)
        mqtt_client.disconnect
        #Print MQTT Send to Console
        print("MQTT Published")
        
        #Sleep Timer
        time.sleep(sleep_time)

#Primary Loop Startup
mpu6050_startup = mpu6050_read(mpu6050_sensor)
sleep_time = config["sleep_time"]
main_loop(mpu6050_startup, mqtt_client, mqtt_topic, sleep_time)