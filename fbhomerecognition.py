#!/usr/bin/python3
# This script is launched at boot via cron and runs on my server pi (Raspberry pi 3b+)
# where it switches MotionEyeOS motion detection on another pi (Raspberry pi Zero W)
# depending on if given devices are found in the Fritz!Box (WIFI)network.

# Be aware of that this is a beginners work. If you find anything that could be improved
# feel free to tell me.
# I am from germany and therefore my english is not quite good. Sorry ;-)

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
# Load the environment variables into globals
maclist = os.getenv('maclist').split(',')
fritz_ip = os.getenv('fritzbox')
fritz_user = os.getenv('fbuser')
fritz_password = os.getenv('fbpass')
motion = os.getenv('motion')
fritz = FritzConnection(address=fritz_ip, port=None, user=fritz_user, password=fritz_password)


def main():
    # Method specific parts
    crl = pycurl.Curl()
    # Only set status at first run
    status = "UNKNOWN"
    # Change IP to where your MotionEye(OS) is running. Port is standard port.
    # "1" is the number of the camera to check. For more information read MotionEye(OS) wiki
    while True:
        output = io.BytesIO()
        try:
            # Read data from Fritz!Box with fritzconnection
            # check if given MAC addresses stored in credentials.py are online
            home = False
            # Path depends on where you installed fritzconnection. IP needs to be set to Fritz!Box IP.
            # fbuser and fpbass are stored in credentials.py
            status = motion_statuscheck(crl, status, output)
            hosts = FritzWLAN(fritz).get_hosts_info()
            for host in hosts:
                if not home and host.get('mac') in maclist:
                    home = True
                    hosts.clear()
                    break

            status = startstop_motion(crl, status, home)

            # Reset the cURL to make sure we're not doubling up requests
            # Clear out the existing output, so we're not accidentally doubling up
            output.truncate()
            # Wait for 60 seconds before this runs again
            time.sleep(60)
        except BaseException:
            status = "UNKNOWN"
            logging.error('Error at Fritz!Box Home Recognition:', BaseException)
            break


def motion_statuscheck(crl, motion_status, output):
    # Read status of motion detection from MotionEye(OS) if it's not set yet
    if motion_status is "UNKNOWN":
        crl.setopt(pycurl.URL, motion + "/0/detection/status")
        crl.setopt(pycurl.WRITEFUNCTION, output.write)
        crl.perform()
        status = output.getvalue().decode()
        crl.reset()
        if status.find("PAUSE") != -1:
            return "PAUSE"
        elif status.find("ACTIVE") != -1:
            return "ACTIVE"
        else:
            return "UNKNOWN"
    return motion_status


# Check if we need to start or stop Motion, and exec
def startstop_motion(crl, status, home):
    action = "start"
    exec_crl = False
    if not home and status is not "ACTIVE":
        status = "ACTIVE"
        exec_crl = True
    elif home and status is "ACTIVE":
        action = "pause"
        status = "PAUSE"
        exec_crl = True

    if exec_crl:
        logging.info('Setting Motion status to ' + action)
        crl.setopt(pycurl.URL, motion + "/0/detection/" + action)
        crl.perform()
        crl.reset()

    return status


if __name__ == '__main__':
    main()
