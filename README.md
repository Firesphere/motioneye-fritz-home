# Fritz!Box Motion control

Based on the MAC addresses registered at your Fritz!Box,
this library will start or stop Motion, on your MotionEye system.


#### Notes

- The powerup/shutdown is the entire Motion/MotionEye services, not just pausing Motion

## Requirements

Python3.

## Installation

git clone this repository to your folder of likings.

`sudo pip3 install -r requirements.txt`

Ensure the file `fbhomerecognition.py` is executable:

```shell
chmod +x fbhomerecognition.py
```

### Running

Run manually with `./fbhomerecognition.py`

### In your init

If you can, run it via `/etc/init.d` or some other automated start-up script.

`/path/to/fbhomerecognition.pi` in your start-up script

### Start-as-a-service

Or, add it to your start-up scripts.

See the `.service` file. Adjust the variables to what you need, and copy it to

`/etc/systemd/system/fritzmotionhome.service`

Then run the following:

```shell
sudo systemctl daemon-reload
sudo systemctl enable fritzmotionhome
sudo systemctl start fritzmotionhome
```

## Configuration

Copy `example.env` to `.env`, and adjust the settings as needed.

## MAC addresses

Either configured in your `.env`, or in a separate `devices.json` file
in json format:

```json
[
  "00:00:00:00:00",
  "11:11:11:11:11"
]
```

## Logging

Should work. Logs are in `/var/log/fbhome.log`

To get an output while working in the console, 
set the environment in your `.env` to "dev"

### Logrotate (Debian based systems)

Copy the file `fbhome` to `/etc/logrotate.d/fbhome`

Test with the following command:

`sudo logrotate -d /etc/logrotate.d/fbhome`

# LICENSE
WTFPL

## Did you read this entire readme? 

You rock!

# Pictured below is a cow, just for you.
```

               /( ,,,,, )\
              _\,;;;;;;;,/_
           .-"; ;;;;;;;;; ;"-.
           '.__/`_ / \ _`\__.'
              | (')| |(') |
              | .--' '--. |
              |/ o     o \|
              |           |
             / \ _..=.._ / \
            /:. '._____.'   \
           ;::'    / \      .;
           |     _|_ _|_   ::|
         .-|     '==o=='    '|-.
        /  |  . /       \    |  \
        |  | ::|         |   | .|
        |  (  ')         (.  )::|
        |: |   |;  U U  ;|:: | `|
        |' |   | \ U U / |'  |  |
        ##V|   |_/`"""`\_|   |V##
           ##V##         ##V##
```
