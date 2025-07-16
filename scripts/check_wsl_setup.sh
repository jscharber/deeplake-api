#!/bin/bash

echo "=== WSL Python Development Environment Check ==="
echo ""

echo "1. WSL Distribution:"
cat /etc/os-release | grep PRETTY_NAME
echo ""

echo "2. Current working directory:"
pwd
echo ""

echo "3. Python interpreter:"
which python3
echo "Python version: $(python3 --version)"
echo ""

echo "4. Virtual environment:"
echo "VIRTUAL_ENV: $VIRTUAL_ENV"
if [ -f ".venv/bin/python" ]; then
    echo "✅ Virtual environment found: .venv/bin/python"
    echo "Venv Python version: $(.venv/bin/python --version)"
else
    echo "❌ Virtual environment not found"
fi
echo ""

echo "5. UV package manager:"
if command -v uv &> /dev/null; then
    echo "✅ UV found: $(which uv)"
    echo "UV version: $(uv --version)"
else
    echo "❌ UV not found"
fi
echo ""

echo "6. MyPy setup:"
if [ -f ".venv/bin/mypy" ]; then
    echo "✅ MyPy found in venv"
    echo "MyPy version: $(.venv/bin/mypy --version)"
    echo "MyPy config test:"
    uv run mypy --version
else
    echo "❌ MyPy not found in venv"
fi
echo ""

echo "7. Import test:"
if .venv/bin/python -c "import structlog; print('✅ structlog import successful')" 2>/dev/null; then
    echo "✅ structlog import successful"
else
    echo "❌ structlog import failed"
fi

if .venv/bin/python -c "import fastapi; print('✅ fastapi import successful')" 2>/dev/null; then
    echo "✅ fastapi import successful"  
else
    echo "❌ fastapi import failed"
fi
echo ""

echo "8. Type checking test:"
echo "Running mypy on a simple file..."
if uv run mypy app/main.py --no-error-summary | grep -q "Success"; then
    echo "✅ MyPy working correctly"
else
    echo "❌ MyPy issues found"
fi
echo ""

echo "=== VSCode WSL Setup Tips ==="
echo "1. Make sure you're using VSCode with the Remote-WSL extension"
echo "2. Open the project in WSL: code /home/jscharber/eng/deeplake-api"
echo "3. Select the Python interpreter: /home/jscharber/eng/deeplake-api/.venv/bin/python"
echo "4. Reload VSCode window after changing settings"
echo ""
echo "=== Environment Check Complete ==="