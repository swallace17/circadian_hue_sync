#Update Circadian Scenes
##This script is designed to be run as a Home Assistant Service via the pyscript hacs integration. It should be triggered via Home Assistant Automation whenever the value of the Circadian Lighting Sensor updates. 
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

#Generate json of all scenes named Circadian
@pyscript_executor
def get_circadian_scenes(hue_api_key, hue_bridge_ip):
    url = f"https://{hue_bridge_ip}/clip/v2/resource/scene"
    headers = {'hue-application-key': hue_api_key}
    response = requests.get(url, headers=headers, verify=False)

    # Raises an HTTPError if the response status was unsuccessful
    response.raise_for_status()

    json_obj = response.json()
    new_data = [entry for entry in json_obj["data"] if entry["metadata"]["name"] == "circadian"]
    json_obj["data"] = new_data

    return json_obj

#Generate list of light RIDs associated with a given a Hue Scene ID
def extract_lightRIDs_from_scene(scene_id, hue_scenes_json):
    # List to store the light rids
    light_rids = []

    # Find the scene in the scenes json
    for scene in hue_scenes_json['data']:
        if scene['id'] == scene_id:
            # For each action in the scene
            for action in scene['actions']:
                # If the target is a light
                if action['target']['rtype'] == 'light':
                    # Add the light rid to the list
                    light_rids.append(action['target']['rid'])

    # Return the list of light rids
    return light_rids

#Update circadian scenes
@pyscript_executor
def sync_circadian_scenes(scene_id, light_rids, hue_api_key, hue_bridge_ip, brightness, color_temp):
    # Base URL for the API
    url = f"https://{hue_bridge_ip}/clip/v2/resource/scene/{scene_id}"

    # Base action dictionary that will be used for each light
    base_action = {
        "action": {
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
    })

    # Headers for the request
    headers = {
        'hue-application-key': hue_api_key,
        'Content-Type': 'application/json'
    }

    # Send the request
    response = requests.put(url, headers=headers, data=payload, verify=False)

    # Return the response
    return response.text


@state_trigger('sensor.circadian_values')
def start(**kwargs):
    # Initiate variables & pull needed json bundles from Hue Bridge
    hue_bridge_ip, hue_api_key = get_hue_gateway_and_key()
    colortemp = get_colortemp()
    brightness = get_brightness()
    circadian_scenes_json = get_circadian_scenes(hue_api_key, hue_bridge_ip)
    scenes_per_second = 5
    delay = 1.0 / scenes_per_second

    # Iterate through each scene in circadian_scenes_json
    for scene in circadian_scenes_json['data']:
        scene_id = scene['id']
        # Extract the light rids for the current scene
        light_rids = extract_lightRIDs_from_scene(scene_id, circadian_scenes_json)
        # Sync the circadian scene with the updated light rids
        response = sync_circadian_scenes(scene_id, light_rids, hue_api_key, hue_bridge_ip, brightness, colortemp)
        log.info(response)
        task.sleep(delay)