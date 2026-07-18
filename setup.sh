#!/bin/bash

echo "Starting model setup..."
echo "1/2: Pulling base model qwen3:14b (this may take a while if you haven't downloaded it before)..."
ollama pull qwen3:14b

echo "2/2: Creating custom model 'language-teacher' from Modelfile..."
ollama create language-teacher -f Modelfile

echo "Setup complete! You can now run the Language Conversation Coach."
