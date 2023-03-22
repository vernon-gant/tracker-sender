set project_path=C:\Users\aleks\PycharmProjects\tracker-sender

pyinstaller --onefile ^
            --distpath "%project_path%" ^
            --add-data ".env;.env" ^
            --paths "%project_path%\venv\Lib\site-packages" ^
            tracker.py

del /f /q "%project_path%\tracker.spec"
rmdir /s /q "%project_path%\build"

tracker.exe
del /f /q "%project_path%\tracker.exe"

