#Create Circadian Scenes
##This script is designed to be run as a Home Assistant Service via the pyscript hacs integration. It will be run automatically by pyscript upon install, and is designed to be run again automatically via a Home Assistant Automation whenever a new room is created. 
import requests
import json

#Get hue_api_key and hue_bridge_ip
@pyscript_executor
def get_hue_gateway_and_key():
    with open('/config/.storage/core.config_entries', 'r') as entriesJson:
        response = json.load(entriesJson)

    hue_gateway = None
    key = None

    for entry in response["data"]["entries"]:
        if "Hue Bridge" in entry["title"]:
            if "data" in entry and "host" in entry["data"] and "api_key" in entry["data"]:
                hue_gateway = entry["data"]["host"]
                key = entry["data"]["api_key"]
                break
            else:
                raise KeyError("Data field with host and api_key is not found in the entry for Philips hue")

    if hue_gateway is None or key is None:
        raise ValueError("Philips hue entry not found or missing necessary data")

    return hue_gateway, key

#Get colortemp from Circadian Lighting sensor    
def get_colortemp():
    entity_id = 'sensor.circadian_values'
    state = hass.states.get(entity_id)

    if state is None:
        raise ValueError(f'Entity {entity_id} not found')

    colortemp_kelvin = state.attributes.get('colortemp')
    if colortemp_kelvin is None:
        raise ValueError(f'colortemp attribute not found for entity {entity_id}')

    # Convert Kelvin to Mireds (Phillips Hue uses Mireds), round it and convert to integer
    colortemp= int(round(1000000 / colortemp_kelvin))

    return colortemp


#Get brightness from Circadian Lighting sensor
def get_brightness():
    entity_id = 'switch.circadian_lighting_circadian_lighting'
    state = hass.states.get(entity_id)

    if state is None:
        raise ValueError(f'Entity {entity_id} not found')

    brightness = state.attributes.get('brightness')
    if brightness is None:
        raise ValueError(f'brightness attribute not found for entity {entity_id}')

    return brightness

#Get Rooms Function
@pyscript_executor
def get_rooms(hue_api_key, hue_bridge_ip):
    url = f"https://{hue_bridge_ip}/clip/v2/resource/room"
    
    headers = {
        'hue-application-key': hue_api_key
    }
    
    response = requests.get(url, headers=headers, verify=False)

    json_payload = response.json()
    
    return json_payload

#Get Scenes Function
@pyscript_executor
def get_scenes(hue_api_key, hue_bridge_ip):
    url = f"https://{hue_bridge_ip}/clip/v2/resource/scene"
    
    headers = {
        'hue-application-key': hue_api_key
    }
    
    response = requests.get(url, headers=headers, verify=False)
    json_payload = response.json()
    
    return json_payload

#Get Devices Function
@pyscript_executor
def get_devices(hue_api_key, hue_bridge_ip):
    url = f"https://{hue_bridge_ip}/clip/v2/resource/device"
    
    headers = {
        'hue-application-key': hue_api_key
    }
    
    response = requests.get(url, headers=headers, verify=False)
    json_payload = response.json()
    
    return json_payload

#Filter Rooms Function 
    #(filter for rooms without a scene named 'circadian')
@pyscript_executor
def filter_rooms(hue_rooms_json, hue_scenes_json):
    # Step 1: Filter scenes list to entries with metadata name 'circadian'
    hue_scenes_circadian_json = [scene for scene in hue_scenes_json['data'] if scene['metadata']['name'] == 'circadian']

    # Step 2: Filter rooms list by removing any rooms found in step 1 which already have a scene named circadian
    group_rids = {scene['group']['rid'] for scene in hue_scenes_circadian_json} #creates array of rid values which correspond to rooms with a scene named circadian
    filtered_rooms = [room for room in hue_rooms_json['data'] if room['id'] not in group_rids]

    return filtered_rooms

#Find light RIDs in a given room Function (because light RIDs are not stored in the room object for some reason)
@pyscript_executor
def convert_deviceRIDs_to_lightRIDs(room, hue_devices_json):
    # List to store the light rids
    light_rids = []

    # For each child device in the room
    for child in room['children']:
        # If the child is a device
        if child['rtype'] == 'device':
            # For each device in hue_devices_json
            for device in hue_devices_json['data']:
                # If the device id matches the child rid
                if device['id'] == child['rid']:
                    # For each service in the device
                    for service in device['services']:
                        # If the service is a light
                        if service['rtype'] == 'light':
                            # Add the light rid to the list
                            light_rids.append(service['rid'])

    # Return the list of light rids
    return light_rids

#Create circadian Scenes Function
    #given a room, list of light RIDs, an API key, bridge IP, brightness value, and colortemp
@pyscript_executor
def create_circadian_scene(room, light_rids, hue_api_key, hue_bridge_ip, brightness, color_temp):
    # Base URL for the API
    url = f"https://{hue_bridge_ip}/clip/v2/resource/scene"
    
    # Base action dictionary that will be used for each light
    base_action = {
        "action": {
            "on": {
                "on": True
            },
            "dimming": {
                "brightness": brightness
            },
            "color_temperature": {
                "mirek": color_temp
            }
        }
    }
    
    # Create an action for each light rid
    actions = []
    for rid in light_rids:
        # Copy the base action
        action = base_action.copy()
        # Set the target rid
        action["target"] = {
            "rid": rid,
            "rtype": "light"
        }
        # Add the action to the list
        actions.append(action)
    
    # Create the payload
    payload = json.dumps({
        "type": "scene",
        "actions": actions,
        "metadata": {
            "name": "circadian"
        },
        "group": {
            "rid": room['id'], # The room RID
            "rtype": "room"
        },
        "palette": {
            "color": [],
            "dimming": [],
            "color_temperature": [],
            "effects": []
        },
        "speed": 0.5,
        "auto_dynamic": False
    })
    
    # Headers for the request
    headers = {
        'hue-application-key': hue_api_key,
        'Content-Type': 'application/json'
    }
    
    # Send the request
    response = requests.post(url, headers=headers, data=payload, verify=False)

    # Return the response
    return response.text


@event_trigger('area_registry_updated')
def start(**kwargs):
    #Initiate variables & pull needed json bundles from Hue Bridge
    hue_bridge_ip, hue_api_key = get_hue_gateway_and_key()
    colortemp = get_colortemp()
    brightness = get_brightness()
    hue_rooms_json = get_rooms(hue_api_key, hue_bridge_ip)
    hue_scenes_json = get_scenes(hue_api_key, hue_bridge_ip)
    hue_devices_json = get_devices(hue_api_key, hue_bridge_ip)
    filtered_rooms = filter_rooms(hue_rooms_json, hue_scenes_json)
    scenes_per_second = 5
    delay = 1.0 / scenes_per_second
    
    #Create Hue Scenes if they do not already exist
    for room in filtered_rooms:
        light_rids = convert_deviceRIDs_to_lightRIDs(room, hue_devices_json)
        response = create_circadian_scene(room, light_rids, hue_api_key, hue_bridge_ip, brightness, colortemp)
        log.info(response)
        task.sleep(delay)