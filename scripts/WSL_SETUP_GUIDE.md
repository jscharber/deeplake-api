# 🐧 WSL VSCode Development Setup Guide

## ✅ Current Status: WSL Extension Conflict Fixed!

Your WSL environment is properly set up with:
- ✅ Ubuntu 24.04.2 LTS
- ✅ Python 3.13.5 in virtual environment
- ✅ UV package manager working
- ✅ MyPy 1.7.1 configured
- ✅ All dependencies imported successfully
- ✅ Type checking: `Success: no issues found in 35 source files`

## 🔧 VSCode WSL-Specific Configuration Applied

### Settings Updated (`.vscode/settings.json`):
```json
{
    // WSL-friendly Python configuration
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    
    // Disable problematic MyPy extension, use built-in analysis
    "mypy-type-checker.enable": false,
    "python.analysis.typeCheckingMode": "strict",
    
    // WSL file handling
    "files.eol": "\n",
    "terminal.integrated.defaultProfile.linux": "bash"
}
```

### MyPy Extension Issue:
The `ms-python.mypy-type-checker` extension has compatibility issues with WSL symlinks. We've disabled it and enabled the Python extension's built-in type analysis instead, which provides similar functionality without the spawn errors.

## 🚀 To Apply Changes in VSCode:

### 1. **Ensure Remote-WSL Extension**
   ```bash
   # Install VSCode Remote-WSL extension if not already installed
   code --install-extension ms-vscode-remote.remote-wsl
   ```

### 2. **Open Project in WSL Mode**
   ```bash
   # From WSL terminal, open project
   cd /home/jscharber/eng/deeplake-api
   code .
   ```

### 3. **Select Correct Python Interpreter**
   - Press `Ctrl+Shift+P`
   - Type "Python: Select Interpreter"
   - Choose: `./venv/bin/python` or the workspace folder path

### 4. **Clear VSCode Cache & Reload**
   ```bash
   # Clear any cached configurations
   rm -rf .mypy_cache __pycache__ .vscode/.ropeproject
   ```
   - Press `Ctrl+Shift+P`
   - Type "Developer: Reload Window"
   - Wait for extensions to reload

### 5. **Verify Setup**
   ```bash
   # Run this script to verify everything works
   ./check_wsl_setup.sh
   ```

## 🐛 Common WSL + VSCode Issues & Solutions:

### Issue 1: "Unable to import 'structlog'" (Fixed ✅)
**Cause**: VSCode using Windows Python instead of WSL Python
**Solution**: Use absolute WSL paths in settings.json

### Issue 2: MyPy errors in IDE but not CLI
**Cause**: Different mypy versions/configs between Windows and WSL
**Solution**: Pinned mypy to 1.7.1 and configured WSL-specific paths

### Issue 3: Extensions not working in WSL
**Cause**: Extensions need to be installed in WSL, not just Windows
**Solution**: Install extensions in WSL context via the extension panel

### Issue 4: Terminal using wrong environment
**Cause**: VSCode opening Windows terminal instead of WSL
**Solution**: Set `"terminal.integrated.defaultProfile.linux": "bash"`

## 📁 File Structure Verification:
```
/home/jscharber/eng/deeplake-api/
├── .venv/bin/python    ✅ (Python 3.13.5)
├── .venv/bin/mypy      ✅ (MyPy 1.7.1)  
├── .vscode/settings.json ✅ (WSL-configured)
├── pyproject.toml      ✅ (MyPy config)
└── app/                ✅ (Source code)
```

## 🎯 Next Steps:

1. **Restart VSCode** completely (close and reopen)
2. **Open in WSL**: `code /home/jscharber/eng/deeplake-api` from WSL terminal
3. **Check status bar**: Should show "WSL: Ubuntu-24.04" in bottom left
4. **Test typing**: Open any Python file - should show no import errors

## 🔍 Debug Commands:

```bash
# Verify Python environment
which python3
python3 -c "import structlog; print('OK')"

# Verify MyPy
uv run mypy app/ | head -5

# Check VSCode extension host
code --list-extensions --show-versions | grep python
```

## 🏆 Success Indicators:

You'll know everything is working when:
- ✅ No red import underlines in Python files
- ✅ MyPy type checking shows no errors
- ✅ Auto-complete works for all imports
- ✅ Bottom left shows "WSL: Ubuntu-24.04"
- ✅ Terminal opens in `/home/jscharber/eng/deeplake-api`

Your environment is now optimally configured for WSL development! 🚀