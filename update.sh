#!/bin/bash

# Automated checkout of the latest version of the branch you are on.
# Should only be used in dev. It's here for convenience.

# Reset, "fbhomerecognition.py" gets changed with non-changes
git reset --hard
# Get latest version of branch
git fetch
git pull
# Make executable, and restart the service
chmod +x fbhomerecognition.py
service fritzmotionhome restart