#!/bin/bash
# setup_venv_macos.sh — GunterAI macOS Python environment setup
# Run from: /Users/minimac/PyCharmMiscProject/PythonAIAgent
#
# Usage:
#   chmod +x setup_venv_macos.sh
#   ./setup_venv_macos.sh

set -e

PROJECT_DIR="/Users/minimac/PyCharmMiscProject/PythonAIAgent"
VENV_DIR="$PROJECT_DIR/gunter_venv"

echo "=== GunterAI macOS venv setup ==="
echo "Project: $PROJECT_DIR"
echo "Venv:    $VENV_DIR"
echo ""

# Confirm Python 3.11+ is available (3.13 preferred to match Shogun)
PYTHON=$(which python3)
echo "Python:  $($PYTHON --version)"
echo ""

# Create fresh venv
if [ -d "$VENV_DIR" ]; then
    echo "Removing old venv at $VENV_DIR..."
    rm -rf "$VENV_DIR"
fi

echo "Creating venv..."
$PYTHON -m venv "$VENV_DIR"

# Activate
source "$VENV_DIR/bin/activate"
echo "Venv activated: $VIRTUAL_ENV"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

echo ""
echo "=== Installing GunterAI dependencies ==="

# Core AI / RAG stack
pip install anthropic
pip install langchain
pip install langchain-chroma
pip install langchain-ollama
pip install chromadb
pip install faster-whisper

# Audio
pip install pyaudio
pip install pvporcupine
pip install pvrecorder

# Utility
pip install python-dotenv
pip install requests
pip install Pillow

echo ""
echo "=== Installation complete ==="
echo ""
echo "To activate the venv in future sessions:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "To run GunterAI:"
echo "  cd $PROJECT_DIR"
echo "  source gunter_venv/bin/activate"
echo "  python mechanic_macos.py"
echo ""
echo "Optional: install CPU temp tools for sidebar display:"
echo "  brew install osx-cpu-temp"
echo "   — or —"
echo "  brew install smctemp"
echo ""
echo "Make sure Ollama is running if using local mode:"
echo "  ollama serve"
echo "  ollama pull mxbai-embed-large   # required for RAG embeddings"
echo "  ollama pull llama3.2:3b         # or your preferred local model"
