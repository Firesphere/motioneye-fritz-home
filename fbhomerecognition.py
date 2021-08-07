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

import dotenv
import pycurl
from fritzconnection import FritzConnection
from fritzconnection.lib.fritzhosts import FritzHosts

# Load env variables
env_path = os.path.join(os.getcwd(), '.env')
dotenv.load_dotenv(dotenv_path=env_path)
# create pid file
pid = str(os.getpid())
f = open(os.getenv('lockfile'), 'w')
f.write(pid)
f.close()

handler = None
logger = logging.getLogger("FRITZ!Box AmIHome Recognition")
logger.setLevel(logging.INFO)
if os.getenv('environment') == 'dev':
    handler = logging.StreamHandler(sys.stdout)
else:  # The else is to prevent errors trying to open the log file as the wrong user
    handler = logging.FileHandler('/var/log/fbhome.log')
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(name)s : %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

if os.getenv('maclist'):
    maclist = os.getenv('maclist').split(',')
elif os.path.exists('devices.json'):
    devices = open('devices.json', 'r')
    maclist = json.load(devices)
else:
    raise LookupError("No MAC addresses found to check against!")
motion = os.getenv('motion')
# FRITZ!Box settings are stored in .env
fritz = FritzConnection(address=os.getenv('fritzbox'), user=os.getenv('fbuser'), password=os.getenv('fbpass'))


def main():
    status = motion_statuscheck()
    while status is not "UNKNOWN":  # We loop forever
        try:
            home = check_hosts()
            status = startstop_motion(status, home)
            # Clear out the existing output, so we're not accidentally doubling up
            # Wait for 60 seconds before this runs again
        except BaseException:
            logger.exception('Error at Fritz!Box Home Recognition ', BaseException)
        time.sleep(60)
    # Only if the while loop breaks, will we enter the UNKNOWN state
    logger.error("Status is unknown. Restarting MotionEye and Home Detection")
    # Restart MotionEye, to make sure it's running and we're able to detect the status
    # next time around. And restart this daemon after that.
    try:
        subprocess.run('service motioneye start', shell=True)
        time.sleep(20)  # Give it some time to (re)start
        os.execv(__file__, sys.argv)
    except BaseException:
        logger.exception('Complete system restart failure. Exiting', BaseException)
        sys.exit(255)


# Check if the the registered  MAC addresses are connected
def check_hosts():
    home = False
    hosts = FritzHosts(fritz).get_hosts_info()
    # Read data from Fritz!Box with fritzconnection
    # check if given MAC addresses stored in .env are online
    # This could be a bit more readable though...
    for host in hosts:
        mac = host.get('mac')
        if mac in maclist:
            logger.info("Found {}".format(mac))
            home = True

    return home


# Map status from Motion to useful values
def motion_statuscheck():
    motion_status = "UNKNOWN"
    output = io.BytesIO()
    # Read status of motion detection from MotionEye(OS) if it's not set yet
    try:
        curl_motion(output)
        status = output.getvalue().decode()
        if status.find("PAUSE") != -1:
            motion_status = "PAUSE"
        elif status.find("ACTIVE") != -1:
            motion_status = "ACTIVE"
    except BaseException:
        logger.info("Motion returned an error", BaseException)
        # We got an error, so, force to be "Unknown"
        # This will break the loop above and attempt to restart the daemons
        motion_status = "UNKNOWN"

    output.truncate()

    return motion_status


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
    if not home and status is not "ACTIVE":  # Nobody is home, activate
        status = "ACTIVE"
        action = "start"
    elif home and status is "ACTIVE":  # Someone is home, deactivate
        status = "PAUSE"
        action = "stop"

    if action is not False:
        try:
            cmd = 'service motioneye ' + action
            subprocess.run(cmd, shell=True)
            logger.info("MotionEye status updated.")
            logger.info("Previous status: {}".format(old_status))
            logger.info("New status: {}".format(status))
        except BaseException:
            logger.exception('Failed action {} on MotionEye'.format(action), BaseException)
            # If execution of the action fails, revert to "UNKNOWN" to restart all processes
            # and start over again
            status = "UNKNOWN"

    return status


if __name__ == '__main__':
    main()
