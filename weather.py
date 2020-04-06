# -*- coding:utf-8 -*-
import sys
import os
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
#libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
libdir = "/home/thomas/python/scripts/lib"
if os.path.exists(libdir):
    sys.path.append(libdir)

import math, cmath, numpy
import logging
from waveshare_epd import epd4in2
import time
from PIL import Image,ImageDraw,ImageFont
import traceback
import json, requests, datetime

logging.basicConfig(level=logging.DEBUG)
log = logging #je suis un peu un flémmard
#tokenJsonData = {"token": {"access_token":"aaaa", "refresh_token" : "bbbb", "update_time": ""}}
configData = {}
thermoData = {}
weatherData = {}

def openConfigFile():
    try:
        log.info("loading config file")
        with open("config.json", "r") as fTokenJsonData:
            global configData
            configData = json.load(fTokenJsonData)
            #log.debug("config file bellow:")
            #log.debug(configData)
    except:
        print("Error on reading config file: ", sys.exc_info()[0], "\n", sys.exc_info()[1], "\n", sys.exc_info()[2])
        logging.fatal("failed to open config file (config.json)")
        exit()

def writeConfig():
    with open("config.json", "w") as fJson:
        json.dump(configData, fJson, sort_keys=True, indent=4, default=str)

def updateToken():
    log.info("updating token")
    POSTdata = {"grant_type":"refresh_token", "refresh_token": configData["token"]["refresh_token"], "client_id":configData["token"]["client_id"], "client_secret":configData["token"]["client_secret"]}
    r = requests.post("https://api.netatmo.com/oauth2/token", data=POSTdata)
    
    #vérifie si la requête http est accepté par le serveur
    if r.status_code == requests.codes.ok:
        log.debug(r.text)
        data = json.loads(r.text)
        configData["token"]["refresh_token"] = data["refresh_token"]
        configData["token"]["access_token"] = data["access_token"]
        configData["token"]["update_time"] = datetime.datetime.now()
        writeConfig()
    else:
        log.error("error on updating token (HTTP " + str(r.status_code) + ")")

def checkAndUpdateToken():
    log.debug("checking token")
    print(json.dumps(configData, indent=4, sort_keys=True))
    if configData['token']["update_time"] == "":
        log.debug("no update time found for token, updating")
        updateToken()
    else:
        log.debug("checking time to see if updating token is needed")
        dt = datetime.datetime.strptime(configData["token"]["update_time"], "%Y-%m-%d %H:%M:%S.%f")
        timedelta = datetime.datetime.now() - dt

        #si la dernière maj des tokens remonte à plus de deux heures
        if timedelta.total_seconds() > 7200:
            updateToken()
        else:
            log.debug("no token update is needed")

def UpdateWeatherData():
    r = requests.get("https://api.netatmo.com/api/getstationsdata?device_id=[...]&get_favorites=false", headers={"Authorization": "Bearer " + configData["token"]["access_token"]})
    #print(r.text)
    #print("\n")
    global thermoData
    thermoData = json.loads(r.text)
    params = {"id":"6450758", "appid":"[...]", "units": "metric", "lang": "fr", "mode": "JSON"}
    r = requests.get("https://api.openweathermap.org/data/2.5/forecast", params=params)
    #print(r.text)
    global weatherData
    weatherData = json.loads(r.text)

def DrawScreen(img, drawing):
    #TOP PART
    #prout = Image.open("icon/sun.png", "r")
    #prout = prout.resize((40,40))
    #img.paste(prout)
    font = ImageFont.truetype(font="Calibri Regular.ttf", size=20)
    BIGfont = ImageFont.truetype(font="Calibri Regular.ttf", size=50)
    smallfont = ImageFont.truetype(font="Calibri Regular.ttf", size=10)
    
    #Intérieur NetAtmo
    drawing.rectangle((0,0, 180, 100), outline=0, width=1)
    drawing.text((0, 0), "Intérieur", fill=0, font=font)
    drawing.text((0, 20), str(thermoData["body"]["devices"][0]["dashboard_data"]["Temperature"]) + "°", fill=0, font=BIGfont)

    SecondColIntText = str(thermoData["body"]["devices"][0]["dashboard_data"]["Humidity"]) + "%\n" + str(thermoData["body"]["devices"][0]["dashboard_data"]["Noise"]) + "dB\n" + str(thermoData["body"]["devices"][0]["dashboard_data"]["CO2"]) + "ppm"
    SecondColSize = drawing.multiline_textsize(SecondColIntText, font=font)
    #log.debug(SecondColSize)
    drawing.text((180 - SecondColSize[0], 20), SecondColIntText, font=font)

    drawing.text((0, 75), str(thermoData["body"]["devices"][0]["dashboard_data"]["Pressure"]) + "mBar", font=font)

    #Extérieur NetAtmo
    drawing.rectangle((180,0, 300, 100), outline=0, width=1)
    drawing.text((180, 0), "Extérieur", fill=0, font=font)
    drawing.text((180, 20), str(thermoData["body"]["devices"][0]["modules"][0]["dashboard_data"]["Temperature"]) + "°", fill=0, font=BIGfont)
    drawing.text((180, 60), str(thermoData["body"]["devices"][0]["modules"][0]["dashboard_data"]["Humidity"]) + "%", fill=0, font=font)
    if str(thermoData["body"]["devices"][0]["modules"][0]["dashboard_data"]["temp_trend"] == "up"):
        trend_img = Image.open("icon/trend-up.png", "r")
    elif str(thermoData["body"]["devices"][0]["modules"][0]["dashboard_data"]["temp_trend"] == "down"):
        trend_img = Image.open("icon/trend-down.png", "r")
    else: #stable
        trend_img = Image.open("icon/trend-stable.png", "r")
    img.paste(trend_img, (280, 0))

    #MIDDLE PART
    drawing.text((0, 101), str(weatherData["city"]["name"]), fill=0, font=BIGfont)
    td = datetime.datetime.fromtimestamp(time.time()-weatherData["list"][0]["dt"])
    drawing.text((0, 120), str(td.hour) + ":" + str(td.minute) + " " + str(weatherData["list"][0]["weather"][0]["description"]), fill=0, font=font)


def Main():
    try:
        
        log.info("starting")
        openConfigFile()
        checkAndUpdateToken()
        UpdateWeatherData()

        epd = epd4in2.EPD()

        log.info("init and clear")
        epd.init()
        epd.Clear()

        # Drawing on the Horizontal image
        log.info("init initial image") 
        log.debug("X=" + str(epd.height) + " y=" + str(epd.width))
        HBlackimage = Image.new('1', (epd.height, epd.width), 255)  #black buffer
        drawblack = ImageDraw.Draw(HBlackimage)

        DrawScreen(HBlackimage, drawblack)

        HBlackimage = HBlackimage.rotate(180)

        epd.display(epd.getbuffer(HBlackimage))

    except IOError as e:
        logging.info(e)
        
    except KeyboardInterrupt:    
        logging.info("ctrl + c:")
        epd4in2.epdconfig.module_exit()
        exit()

if __name__ == "__main__":
    Main()