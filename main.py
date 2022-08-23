#!/usr/bin/env python3
import os
import sys

import dotenv
import logging
from subprocess import call

import paho.mqtt.client as mqtt

env_path = os.path.join(os.getcwd(), '.env')
dotenv.load_dotenv(dotenv_path=env_path)
logger = logging.getLogger("Reboot logger")
logger.setLevel(logging.INFO)
if os.getenv('ENVIRONMENT', 'prod') == 'dev':
    handler = logging.StreamHandler(sys.stdout)
    node_name = 'prelude'  # My debugging name
else:  # The else is to prevent errors trying to open the log file as the wrong user
    handler = logging.FileHandler('/var/log/mqtt_reboot.log')
    node_name = os.uname().nodename.lower()
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(name)s : %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# configuration:
mqtt_host = os.getenv('MQTT_HOST', '127.0.0.1')
mqtt_port = os.getenv('MQTT_PORT', 1883)
mqtt_user = os.getenv('MQTT_USER', "")
mqtt_pass = os.getenv('MQTT_PASS', "")
mqtt_topc = os.getenv('MQTT_TOPC', "")
report_topic = '{}/{}/{}'.format(mqtt_topc, node_name, 'available')
report_me_topic = '{}/{}/{}'.format(mqtt_topc, node_name, 'motioneye')
command_topic = '{}/{}/{}'.format(mqtt_topc, node_name, 'cmd')
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(mqtt_user, mqtt_pass)
mqtt_client.will_set(report_topic, "offline", 1, True)
mqtt_client.will_set(report_me_topic, "offline", 1, True)
mqtt_client.connect(mqtt_host, mqtt_port)  # Connect to the test MQTT broker


# "on connect" event
def connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("connected OK Returned code={}".format(rc))
        mqtt_client.publish(report_topic, "online", 1, True)  # Publish message to MQTT broker
        mqtt_client.subscribe(command_topic)  # Subscribe after re-connect
    else:
        logger.warning("Bad connection Returned code={}".format(rc))


# "on message" event
def read_message(client, userdata, message):
    topic = str(message.topic)
    payload = str(message.payload.decode("utf-8"))
    logger.info("Received payload {} on topic {}".format(payload, topic))
    if topic == command_topic:
        handle_command(payload)


# handle new MQTT command function
def handle_command(cmd):
    if cmd == "reboot":
        call(['reboot'], shell=False)  # reboot host
    elif cmd == "shutdown":
        call(['shutdown', '-h', 'now'], shell=False)  # shut down host
    elif cmd == "motioneye":
        call("service motioneye start", shell=True)  # Start motioneye
        mqtt_client.publish(report_me_topic, "online", 1, True)
    elif cmd == "test":
        mqtt_client.publish(report_topic, "Reply to test msg")  # Publish reply to an incoming msg with payload "test"


if __name__ == '__main__':
    mqtt_client.on_connect = connect  # run function on connect with broker
    mqtt_client.on_message = read_message  # Attach the messageFunction to subscription
    mqtt_client.loop_forever()
