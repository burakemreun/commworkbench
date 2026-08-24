@echo off
pyinstaller CommWorkbench.spec
echo Build complete: dist\CommWorkbench.exe
echo Copy your configs\ folder next to the exe - it reads configs\ from its own directory.
