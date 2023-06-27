import requests
import time
import json

#Get Rooms Function
def get_rooms(hue_api_key, hue_bridge_ip):
    url = f"https://{hue_bridge_ip}/clip/v2/resource/room"
    
    headers = {
        'hue-application-key': hue_api_key
    }
    
    response = requests.get(url, headers=headers, verify=False)

    json_payload = response.json()
    
    return json_payload

#Get Scenes Function
def get_scenes(hue_api_key, hue_bridge_ip):
    url = f"https://{hue_bridge_ip}/clip/v2/resource/scene"
    
    headers = {
        'hue-application-key': hue_api_key
    }
    
    response = requests.get(url, headers=headers, verify=False)
    json_payload = response.json()
    
    return json_payload

#Get Devices Function
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
def filter_rooms(hue_rooms_json, hue_scenes_json):
    # Step 1: Filter scenes list to entries with metadata name 'circadian'
    hue_scenes_circadian_json = [scene for scene in hue_scenes_json['data'] if scene['metadata']['name'] == 'circadian']

    # Step 2: Filter rooms list by removing any rooms found in step 1 which already have a scene named circadian
    group_rids = {scene['group']['rid'] for scene in hue_scenes_circadian_json} #creates array of rid values which correspond to rooms with a scene named circadian
    filtered_rooms = [room for room in hue_rooms_json['data'] if room['id'] not in group_rids]

    return filtered_rooms

#Find light RIDs in a given room Function (because light RIDs are not stored in the room object for some reason)
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

#Create circadian scenes given a room, list of light RIDs, an API key, bridge IP, brightness value, and colortemp
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


#Variables
hue_api_key = 'APIKEY'
hue_bridge_ip = 'IP'
hue_rooms_json = get_rooms(hue_api_key, hue_bridge_ip)
hue_scenes_json = get_scenes(hue_api_key, hue_bridge_ip)
hue_devices_json = get_devices(hue_api_key, hue_bridge_ip)
filtered_rooms = filter_rooms(hue_rooms_json, hue_scenes_json)
brightness = 100
color_temp = 300
scenes_per_second = 5

# Calculate the delay between each request
delay = 1.0 / scenes_per_second

# Loop through each room in the filtered rooms
for room in filtered_rooms:
    # Get the light rids for the current room
    light_rids = convert_deviceRIDs_to_lightRIDs(room, hue_devices_json)
    # Create a scene for each light rid
    response = create_circadian_scene(room, light_rids, hue_api_key, hue_bridge_ip, brightness, color_temp)
    # Print the response
    print(response)
    # Wait for the delay period before the next request
    time.sleep(delay)
