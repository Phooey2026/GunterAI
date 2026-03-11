from pvrecorder import PvRecorder

for i, device in enumerate(PvRecorder.get_available_devices()):
    print(f"Index {i}: {device}")
