#!/bin/bash
# 1. Start Ollama in the background
ollama serve &

# 2. Wait 5 seconds for the engine to warm up
sleep 5

# 3. Set Bluetooth as default
# cd /home/shogun/PyCharmMiscProject/PythonAIAgent
# source .venv/bin/activate
# pactl set-default-sink bluez_output.08_EB_ED_48_58_F0.1

# 4. Launch Gunter using the Virtual Environment
/home/shogun/PyCharmMiscProject/PythonAIAgent/.venv/bin/python /home/shogun/PyCharmMiscProject/PythonAIAgent/Mechanic.py

# 5. (Optional) Kill Ollama when Gunter closes to free up RAM
pkill ollama
