:: Define project_path variable
set project_path=C:\Users\aleks\PycharmProjects\tracker-sender
set deploy_path=C:\Users\aleks\tracker

:: Create requirements.txt file
call venv\Scripts\activate.bat && pip freeze > requirements.txt

:: Check if deploy directory exists
if exist "%deploy_path%" (
    :: Clear deploy directory
    rd /s /q "%deploy_path%"
    mkdir "%deploy_path%"
) else (
    mkdir "%deploy_path%"
)

:: Copy files to deploy directory
xcopy /s /y "%project_path%\requirements.txt" "%deploy_path%"
xcopy /s /y "%project_path%\.env" "%deploy_path%"
xcopy /s /y "%project_path%\tracker.py" "%deploy_path%"

:: Create virtual environment
cd /d "%deploy_path%"
python3.10 -m venv venv

::Activate virtual environment and install dependencies
call venv\Scripts\activate.bat && pip install -r requirements.txt

:: Build executable
pyinstaller --onefile ^
            --distpath "%deploy_path%" ^
            --add-data ".env;.env" ^
            --paths "%deploy_path%\venv\Lib\site-packages" ^
            tracker.py

:: Remove unnecessary files
del /f /q "%project_path%\requirements.txt"
