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

import dotenv
import pycurl
from fritzconnection import FritzConnection
from fritzconnection.lib.fritzwlan import FritzWLAN

# Load env variables
env_path = os.path.join(os.getcwd(), '.env')
dotenv.load_dotenv(dotenv_path=env_path)
# create pid file
pid = str(os.getpid())
f = open(os.getenv('lockfile'), 'w')
f.write(pid)
f.close()

logger = logging.getLogger("FRITZ!Box AmIHome Recognition")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('/var/log/fbhome.log')
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(name)s : %(message)s')
file_handler.setFormatter(formatter)

# add file handler to logger
logger.addHandler(file_handler)

# Load the environment variables into application globals
maclist = os.getenv('maclist').split(',')
motion = os.getenv('motion')
# Path depends on where you installed fritzconnection. IP needs to be set to Fritz!Box IP.
# FRITZ!Box settings are stored in .env
fritz = FritzConnection(address=os.getenv('fritzbox'), user=os.getenv('fbuser'), password=os.getenv('fbpass'))


def main():
    # Method specific parts
    status = "UNKNOWN"
    status = motion_statuscheck(status)
    while status is not "UNKNOWN":  # We loop forever
        try:
            home = check_hosts()
            status = startstop_motion(status, home)
            # Clear out the existing output, so we're not accidentally doubling up
            # Wait for 60 seconds before this runs again
        except BaseException:
            logger.exception('Error at Fritz!Box Home Recognition ', BaseException)
        time.sleep(60)
    if status is "UNKNOWN":
        logger.error("Status is unknown. Restarting MotionEye and Home Detection")
        # Restart MotionEye, to make sure it's running and we're able to detect the status
        # next time around
        try:
            subprocess.run('service motioneye start', shell=True)
            os.execv(__file__, sys.argv)
            time.sleep(10)  # Give it some time to (re)start
        except BaseException:
            logger.exception('Complete system restart failure. Exiting', BaseException)
            exit(255)


# Check if the the registered WLAN MAC addresses are connected
# @todo See if they are connected via a repeater like Kodi
def check_hosts():
    home = False
    hosts = FritzWLAN(fritz).get_hosts_info()
    # Read data from Fritz!Box with fritzconnection
    # check if given MAC addresses stored in .env are online
    for host in hosts:
        if not home and host.get('mac') in maclist:
            home = host.get('mac')
            break
    return home


# Check the status of motion detection
def motion_statuscheck(motion_status):
    output = io.BytesIO()
    # Read status of motion detection from MotionEye(OS) if it's not set yet
    try:
        crl = pycurl.Curl()
        crl.setopt(pycurl.URL, motion + "/0/detection/status")
        crl.setopt(pycurl.WRITEFUNCTION, output.write)
        crl.perform()
        status = output.getvalue().decode()
        crl.reset()
        if status.find("PAUSE") != -1:
            motion_status = "PAUSE"
        elif status.find("ACTIVE") != -1:
            motion_status = "ACTIVE"
    except BaseException:
        logger.info("Motion returned an error", BaseException)
        # We got an error, so, force to be "Unknown"
        # This will break the loop and attempt to restart the daemon
        motion_status = "UNKNOWN"

    return motion_status


# Check if we need to start or stop Motion, and exec
def startstop_motion(status, home):
    logmsg = ("current status: " + status)
    action = False
    if home is False and status is not "ACTIVE":  # Nobody is home, activate
        status = "ACTIVE"
        action = "start"
    elif home is not False and status is "ACTIVE":  # Someone is home, deactivate
        status = "PAUSE"
        action = "stop"

    if action is not False:
        logger.info(home + " has registered on the Wifi")
        cmd = 'service motioneye ' + action
        subprocess.run(cmd, shell=True)
        logger.info(logmsg + " new status: " + status)

    return status


if __name__ == '__main__':
    main()
