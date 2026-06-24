@echo off
title AskHR System Launcher
echo ==================================================
echo       Starting AskHR Enterprise AI System...
echo ==================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_all.ps1"
exit
