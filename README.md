# circadian_hue_sync
Python script designed to by run in pyscript on Home Assistant for use with Circadian Lighting Integration.

Script will automatically create a scene named 'circadian' in every room on your Hue Bridge. From there, it will keep this scene sync'd with the values provided by Circadian Lightings Sensor and Switch. 

In Hue, this scene can then be associated with a physical light switch (Hue, Friends of Hue, etc) and whenever the light turns on it will instantly turn on to the correct values determined by Circadian Lighting. (By default there are delays of a few seconds between the lights turning on to some random value, and Circadian Lighting taking over and doing things correctly). 
