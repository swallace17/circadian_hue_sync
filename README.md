# circadian_hue_sync
Python scripts designed to be run in pyscript on Home Assistant for use with Circadian Lighting custom component.

create_scenes.py creates a scene named 'circadian' in every room on your Hue Bridge, and update_scenes.py keep those scenes updated with the brightness and ct values provided by Circadian Lighting. 

In Hue, these scenes can then be associated with a physical light switch (Hue, Friends of Hue, etc) and whenever the light turns on it will instantly turn on to the correct values determined by Circadian Lighting. (By default there are delays of a few seconds between the lights turning on to some random value, and Circadian Lighting taking over setting the lights to the calculated values)

## Installation 
### Prerequisites
- [Home Assistant Phillips Hue Integration](https://www.home-assistant.io/integrations/hue/) needs to be installed and configured 
- [Home Assistant Community Store (HACS)](https://hacs.xyz/) needs to be installed
- via HACS, both the [pyscript custom componenet](https://hacs-pyscript.readthedocs.io/en/latest/installation.html#option-1-hacs) and the [Circadian Lighting custom componenet](https://github.com/claytonjn/hass-circadian_lighting) need to be installed and configured. 

note: Pyscript needs to be configured to to use hass global variables for these scripts to function

### Installing the scripts
Place both scripts in a folder named 'pyscript' in your Home Assistant install's /config folder, per the hacs-pyscript documentation

## How does it work? 

High level overview - both scripts begin by pulling the IP address of your Hue gateway and its API key from the already configured Hue Integration. From there, the create scenes script will run anytime it detects a area_registry_updated event in the Home Assistant event bus. To run it manually for the first time, open Home Assistant, navigate to Settings-->Areas & Zones and click the "Create Area" button. Create a room named 'test', or whatever you want, and the create scenes script will fire off, creating circadian scenes in all your rooms. From here on out, whenever you create a new room/area in Home Assistant (or whenever one is created automatically by Hue integration, Homekit integrations, etc) a circadian scene will be created. 

With these scenes created, the update script is then triggered anytime Circadian Lighting's sensor updates. This indicates that updated colortemp and brightness values are available, and that the hue circadian scenes need to be updated. 

With these scenes being constantly updated, you can map them to your Hue-integrated physical light switches via the Hue App (or third-party Hue apps like iConnectHue) and retain full control of the devices within the Hue ecosystem (no need to wipe switch configurations in hue, pair them to home assistant, and lose all the rest of the hue functionality)
