#!/bin/bash

echo "Starting Company Search Backend..."
echo ""

echo "Activating virtual environment..."
source venv/bin/activate

echo ""
echo "Choose which component to start:"
echo "1. Temporal Worker"
echo "2. FastAPI Server"
echo "3. Exit"
echo ""

read -p "Enter your choice (1, 2, or 3): " choice

case $choice in
    1)
        echo "Starting Temporal Worker..."
        python worker.py
        ;;
    2)
        echo "Starting FastAPI Server..."
        python app.py
        ;;
    3)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid choice!"
        exit 1
        ;;
esac
