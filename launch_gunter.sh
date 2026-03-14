#!/bin/bash
# 1. Start Ollama in the background
ollama serve &

# 2. Wait 5 seconds for the engine to warm up
sleep 5

# 3. Launch Gunter using the Virtual Environment
/home/pi/PyCharmMiscProject/PythonAIAgent/.venv/bin/python /home/pi/PyCharmMiscProject/PythonAIAgent/Mechanic.py

# 4. (Optional) Kill Ollama when Gunter closes to free up RAM
pkill ollama
