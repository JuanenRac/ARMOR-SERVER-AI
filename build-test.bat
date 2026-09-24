@echo off
REM ARMOR-SERVER-AI non-mutating build-test launcher. GPL-3.0-or-later.
call "%~dp0..\ARMOR-COMMON\scripts\armor-project.bat" build-test "%~dp0."
exit /b %ERRORLEVEL%
