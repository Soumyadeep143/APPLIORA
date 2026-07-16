@echo off
cd /d "C:\Users\dell\PRODUCT\APPLIORA\backend"
echo ---------------------------------------------- >> reminders.log
echo %DATE% %TIME% - running reminders scan >> reminders.log
"C:\Users\dell\AppData\Local\Programs\Python\Python311\python.exe" -m app.reminders >> reminders.log 2>&1
