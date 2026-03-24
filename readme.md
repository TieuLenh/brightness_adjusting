# virtual env
cmd: python -m venv venv 
`-m: using mudule`

`To active`
cmd: venv\Scripts\activate.bat 
     venv\Scripts\Activate.ps1

`Install all necessary modules`
cmd: pip install PyInstaller screen_brightness_control pystray Pillow winshell 

`To build`
cmd: python -m PyInstaller --onefile --windowed --hidden-import=screen_brightness_control --hidden-import=pystray --hidden-import=winshell --hidden-import=win32com brightness_app.py