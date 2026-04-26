# Auto Push Service

This service automatically commits and pushes changes to the remote repository.

## Files
- auto_push.py: Main Python script for auto-commit and push
- auto_push.bat: Windows batch file to run the service
- auto_push.log: Log file for the service

## Usage

Run once (manual commit and push):
python auto_push.py --once

Run continuous service (auto-commit and push every 60 seconds):
python auto_push.py
python auto_push.py --interval 30  # Check every 30 seconds

Windows batch file:
auto_push.bat
