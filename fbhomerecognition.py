#!/usr/bin/python3
# This script is launched at boot via cron and runs on my server pi (Raspberry pi 3b+)
# where it switches MotionEyeOS motion detection on another pi (Raspberry pi Zero W)
# depending on if given devices are found in the Fritz!Box (WIFI)network.

# Be aware of that this is a beginners work. If you find anything that could be improved
# feel free to tell me.
# I am from germany and therefore my english is not quite good. Sorry ;-)

import subprocess
import os
import time
import pycurl
import io
import logging
import dotenv
from fritzconnection import FritzConnection
from fritzconnection.lib.fritzwlan import FritzWLAN

# Load env variables
env_path = os.path.join(os.getcwd(), '.env')
dotenv.load_dotenv(dotenv_path=env_path)
# create pid file
pid = str(os.getpid())
f = open(os.getenv('lockfile'), 'w')  # Change path to fit your needs
f.write(pid)
f.close()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('/var/log/fbhome.log')
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(name)s : %(message)s')
file_handler.setFormatter(formatter)

# add file handler to logger
logger.addHandler(file_handler)

# Load the environment variables into application globals
maclist = os.getenv('maclist').split(',')
fritz_ip = os.getenv('fritzbox')
fritz_user = os.getenv('fbuser')
fritz_password = os.getenv('fbpass')
motion = os.getenv('motion')
fritz = FritzConnection(address=fritz_ip, port=None, user=fritz_user, password=fritz_password)


def main():
    # Method specific parts
    status = "UNKNOWN"
    output = io.BytesIO()
    while True:
        try:
            # Read data from Fritz!Box with fritzconnection
            # check if given MAC addresses stored in credentials.py are online
            home = False
            # Path depends on where you installed fritzconnection. IP needs to be set to Fritz!Box IP.
            # fbuser and fpbass are stored in credentials.py
            hosts = FritzWLAN(fritz).get_hosts_info()
            for host in hosts:
                if not home and host.get('mac') in maclist:
                    home = True
                    hosts.clear()
                    break

            status = startstop_motion(status, home)

            # Clear out the existing output, so we're not accidentally doubling up
            output.truncate()
            # Wait for 60 seconds before this runs again
            time.sleep(60)
        except BaseException:
            logger.exception('Error at Fritz!Box Home Recognition:', BaseException)
            break


def motion_statuscheck(motion_status, output):
    # Read status of motion detection from MotionEye(OS) if it's not set yet
    try:
        crl = pycurl.Curl()
        crl.setopt(pycurl.URL, motion + "/0/detection/status")
        crl.setopt(pycurl.WRITEFUNCTION, output.write)
        crl.perform()
        status = output.getvalue().decode()
        crl.reset()
        if status.find("PAUSE") != -1:
            return "PAUSE"
        elif status.find("ACTIVE") != -1:
            return "ACTIVE"
    except BaseException:
        logger.info("Motion returned an error", BaseException)
        motion_status = "PAUSE"
    return motion_status


# Check if we need to start or stop Motion, and exec
def startstop_motion(status, home):
    action = "start"
    if not home and status is not "ACTIVE":
        status = "ACTIVE"
    elif home and status is "ACTIVE":
        status = "PAUSE"
        action = "stop"

    cmd = 'service motioneye ' + action
    result = subprocess.call(cmd, shell=True)
    logger.info(result)

    return status


if __name__ == '__main__':
    main()
