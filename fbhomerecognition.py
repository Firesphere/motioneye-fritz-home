#!/usr/bin/python3
# This script is launched at boot via systemd and runs on my server pi (Raspberry pi 3b+)
# where it switches MotionEyeOS motion detection on or off
# depending on if given devices are found in the Fritz!Box (WIFI)network.

# Be aware of that this is a beginners work. If you find anything that could be improved
# feel free to tell me.

import io
import logging
import os
import subprocess
import time
import sys
import json
import paho.mqtt.publish as publish

import dotenv
import pycurl
from fritzconnection import FritzConnection
from fritzconnection.lib.fritzhosts import FritzHosts

# Load env variables
env_path = os.path.join(os.getcwd(), '.env')
dotenv.load_dotenv(dotenv_path=env_path)

handler = None
logger = logging.getLogger("FRITZ!Box AmIHome Recognition")
logger.setLevel(logging.INFO)
if os.getenv('ENVIRONMENT') == 'dev':
    handler = logging.StreamHandler(sys.stdout)
else:  # The else is to prevent errors trying to open the log file as the wrong user
    handler = logging.FileHandler('/var/log/fbhome.log')
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(name)s : %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

if os.getenv('MACLIST'):
    maclist = os.getenv('MACLIST').split(',')
elif os.path.exists('devices.json'):
    devices = open('devices.json', 'r')
    maclist = json.load(devices)
else:
    raise LookupError("No MAC addresses found to check against!")
motion = os.getenv('MOTION')
# FRITZ!Box settings are stored in .env
fritz = FritzConnection(address=os.getenv('FRITZBOX', '192.168.178.1'), user=os.getenv('FBUSER'), password=os.getenv('FBPASS'))


def main():
    # Default to set everything to be paused
    publish_mqtt("PAUSE")
    # Assume motion is active, and someone is home.
    # This will cause a cut-out of maximum one minute if the system is rebooted
    # However, the reboot will be much faster without motion startup
    status = startstop_motion("ACTIVE", True)
    while True:  # We loop forever
        if status == "UNKNOWN":
            # Only if we get the UNKNOWN state
            logger.warning("Status is unknown. Restarting MotionEye and Home Detection")
            # Attempt to force MotionEye to start, better safe than sorry
            startstop_motion("PAUSE", False)

        try:
            home = check_hosts(status)
            status = startstop_motion(status, home)
            publish_mqtt(status)
            # Clear out the existing output, so we're not accidentally doubling up
            # Wait for 60 seconds before this runs again
        except BaseException as e:
            logger.exception('Error at Fritz!Box Home Recognition ', e)
        time.sleep(30)


# Check if the the registered  MAC addresses are connected
def check_hosts(status):
    home = False
    hosts = FritzHosts(fritz).get_active_hosts()
    # Read data from Fritz!Box with fritzconnection
    # check if given MAC addresses stored in .env are online
    # This could be a bit more readable though...
    for host in hosts:
        mac = host.get('mac')
        if mac in maclist:
            if status != "PAUSE":
                logger.info("Found {} - {}".format(mac, host.get('name')))
            home = True

    return home


def publish_mqtt(status):
    if os.getenv('MQTT') is not None:
        status_boolean = 1 if status == 'ACTIVE' else 0
        publish.single(os.getenv('MQTT_TOPIC'), status_boolean, hostname=os.getenv('MQTT'))


# Get the status from Motion and put it in to our output
def curl_motion(output):
    crl = pycurl.Curl()
    crl.setopt(pycurl.URL, motion + "/0/detection/status")
    crl.setopt(pycurl.WRITEFUNCTION, output.write)
    crl.perform()
    crl.reset()


# Check if we need to start or stop Motion, and exec
def startstop_motion(status, home):
    old_status = status
    action = False
    if not home and status != "ACTIVE":  # Nobody is home, activate
        status = "ACTIVE"
        action = "start"
    elif home and status == "ACTIVE":  # Someone is home, deactivate
        status = "PAUSE"
        action = "stop"

    if action is not False:
        try:
            cmd = 'service motioneye ' + action
            subprocess.run(cmd, shell=True)
            logger.info("MotionEye status updated. Previous status: {}; new status: {}".format(old_status, status))
        except BaseException as e:
            logger.exception('Failed action {} on MotionEye'.format(action), e)
            # If execution of the action fails, revert to "UNKNOWN" to restart all processes
            # and start over again
            status = "UNKNOWN"

    publish_mqtt(status)

    return status


if __name__ == '__main__':
    main()
