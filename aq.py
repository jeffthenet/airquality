#!/usr/bin/env python
#
# Air quality monitoring
# Science project based on RaspberryPi, GrovePi and Grove sensors and actuators
#
#


'''
## License

The MIT License (MIT)

Copyright (c) 2017 Emma Gailleur

'''



import grovepi
import os
import time
from ISStreamer.Streamer import Streamer
import atexit
import datetime


# Connect the CO2 sensor to the RPISER port on the GrovePi
import grove_co2_lib

# ---------------------------------

def isFloat(string):
    try:
        float(string)
        return True
    except ValueError:
        return False
# ---------------------------------

# TO DO CONVERT IN OBJECT ORIENTED, CLASS SENSOR...

# --------- User Settings ---------
# The DHT_SENSOR_TYPE below may need to be changed depending on which DHT sensor you have:
#  0 - DHT11 - blue one - comes with the GrovePi+ Starter Kit
#  1 - DHT22 - white one, aka DHT Pro or AM2302
#  2 - DHT21 - black one, aka AM2301
#DHT_SENSOR_TYPE = 1
# Connect the DHT sensor to one of the digital pins (i.e. 2, 3, 4, 7, or 8)
#DHT_SENSOR_PIN = 4

#------------ Temp and humidity sensor
dht_sensor_port = 4		# Connect the DHt sensor to digital port 4
dht_sensor_type = 1             # change this depending on your sensor type - see header comment

# Initial State settings
BUCKET_NAME_AQ = "Air Quality Monitoring"
#BUCKET_KEY_AQ = "aq170216"
#BUCKET_KEY_AQ = "aq170216"
BUCKET_KEY_AQ = "kitchen-ids-170219"

# intial state access key for jgailleur@hotmail.com
ACCESS_KEY = "0Vcs79QnlzNa7tO7Bn1sJ0LHgzyuTJaj"

# Set the time between sensor reads
SECONDS_BETWEEN_READS = 15
INIT_SECONDS_WAIT = 30 # number of seconds to wait for sensors to warm up



#---------- AIR QUALITY SENSOR -----------------
# NOTE: # Wait 2 minutes for the sensor to heat-up
# Connect the Grove Air Quality Sensor to analog port A0
# SIG,NC,VCC,GND
air_sensor = 0 # air quality sensor
grovepi.pinMode(air_sensor,"INPUT")

#---------- CO2 SENSOR -----------------
# connect to the CO2 sensor
co2= grove_co2_lib.CO2()

#---------- HCHO SENSOR -----------------
# The sensitivity can be adjusted by the onboard potentiometer
# Connect the Grove HCHO Sensor to analog port A0
# SIG,NC,VCC,GND
hcho_sensor = 1
grovepi.pinMode(hcho_sensor,"INPUT")

#-------------- DUST SENSOR
# Vcc of the grove interface is normally 5v
grove_vcc = 5

# for dust sensor ???
atexit.register(grovepi.dust_sensor_dis)
grovepi.dust_sensor_en()
dustsensor_sampletime_ms = SECONDS_BETWEEN_READS

# gas sensor
# There are 5 gas sensors
# MQ2 - Combustible Gas, Smoke
# MQ3 - Alcohol Vapor
# MQ5 - LPG, Natural Gas, Town Gas
# MQ9 - Carbon Monoxide, Coal Gas, Liquefied Gas
# 02 - Oxygen
# The sensitivity can be adjusted by the onboard potentiometer
# http://www.seeedstudio.com/wiki/Grove_-_Gas_Sensor

# gas sensor MQ2, analog port
gas_sensor_MQ = 2
grovepi.pinMode(gas_sensor_MQ,"INPUT")

# leds
led_green = 6 # green on digital 6
led_red = 5 # red on digital 5
grovepi.pinMode(led_green,"OUTPUT")
grovepi.pinMode(led_red,"OUTPUT")

# open the streamer
streamer_aq = Streamer(bucket_name=BUCKET_NAME_AQ, bucket_key=BUCKET_KEY_AQ, access_key=ACCESS_KEY)

# First few seconds
init_few_seconds = 0

# infinite loop
while True:
    
    try:
        #green light on, red off
        grovepi.digitalWrite(led_green,1)
        grovepi.digitalWrite(led_red,0)

        # data acquisition
        now = datetime.datetime.utcnow()
        print ("---------------------")
        print("Now (utc): "+str(now))
        print ("---------------------")


        # Get air quality sensorS value
        air_quality_sensor_value = grovepi.analogRead(air_sensor)

        # get CO2
        [co2_ppm, co2_temp]= co2.read()

        # Get hcho sensor value
        hcho_sensor_value = grovepi.analogRead(hcho_sensor)
        # Calculate voltage
        hcho_voltage = (float)(hcho_sensor_value * grove_vcc / 1024)

        # Get gas sensor value
        gas_sensor_value_MQ = grovepi.analogRead(gas_sensor_MQ)
        # Calculate gas density - large value means more dense gas
        gas_MQ_density = round((float)(gas_sensor_value_MQ / 1024), 0)

        gas_MQ_density = gas_sensor_value_MQ


        # reading dust sensor
        [new_val,lowpulseoccupancy] = grovepi.dustSensorRead()
        # calculate concentration: http://www.howmuchsnow.com/arduino/airquality/grovedust/
        dust_concentration = 0
        if (new_val):
            ratio = (lowpulseoccupancy /(dustsensor_sampletime_ms*10.0)) # Integer percentage 0 to 100
            dust_concentration = round(1.1*pow(ratio,3)-3.8*pow(ratio,2)+520*ratio+0.62, 0) # using spec sheet curve

        # get temperature and humidity
        temp = 0
        hum = 0
        [temp,hum] = grovepi.dht(dht_sensor_port,dht_sensor_type)
        #adjustement for this not quality sensor
#        temp = temp-1

        # stream data after initialization
        if (init_few_seconds >= INIT_SECONDS_WAIT):            
            # stream data points

            # ----- Gases ----
            streamer_aq.log("Air quality gas (1 to 900), lower better",air_quality_sensor_value)
            streamer_aq.log("Carbon dioxide (CO2) PPM around 400",co2_ppm)
            streamer_aq.log("Methanal(HCHO) PPM, lower better",hcho_sensor_value)
            streamer_aq.log("Combustibles gas & smoke, lower better",gas_MQ_density)


            # ---------- PARTICULE ------------
            # stream dust particule information
            if (dust_concentration !=0):
                streamer_aq.log("Dust particule, >PM1 concentration, lower better", dust_concentration)

            # -------- temperature and humidity
            streamer_aq.log("Air temperature (Celcius)", temp)
            streamer_aq.log("Air humidity (%)", hum)
                
            streamer_aq.flush()
            
        else:
            print ("---------------------")
            print ("Warming up sensors...")
            init_few_seconds = init_few_seconds + SECONDS_BETWEEN_READS
            print ("init_few_seconds="+str(init_few_seconds))
            

        # always display on screen
        # Display on screen        
        if air_quality_sensor_value > 700:
            air_quality_type = "High pollution"
        elif air_quality_sensor_value > 300:
            air_quality_type = "Low pollution"
        else: 
            air_quality_type = "Fresh air"
        #endif
            
        print("Air quality: "+air_quality_type+" (%d)" %(air_quality_sensor_value))

        print("CO2 Conc: %d ppm\t Temp: %d C" %(co2_ppm,co2_temp))

        print("HCHO Value: " +str(hcho_sensor_value) + " voltage =" + str(hcho_voltage))

        print("Combustible gases & smoke, lower better %d" %(gas_MQ_density))

        if new_val:
            print("Dust particule ratio: " + str(ratio))
            print("Dust particule concentration: %d" %(dust_concentration))
        else:
            print("Dust particule: no reading")

        print("Air temperature (Celcius): " + str(temp))
        print("Air humidity(%%): " +str (hum))

        # wait until next acquisition
        grovepi.digitalWrite(led_green,0)
        for i in range (1, SECONDS_BETWEEN_READS):
            grovepi.digitalWrite(led_red,1)
            time.sleep(.5)
            grovepi.digitalWrite(led_red,0)
            time.sleep(.5)
#            time.sleep(SECONDS_BETWEEN_READS)

    # endtry

    except KeyboardInterrupt:	# Turn LED off before stopping
        grovepi.digitalWrite(led_green,0)
        grovepi.digitalWrite(led_red,0)
        break

    except IOError:
        print ("Error")


# end while


