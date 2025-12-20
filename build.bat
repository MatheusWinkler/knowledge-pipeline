@echo off
TITLE Building Knowledge Pipeline

:: --- CONFIGURATION ---
:: 1. Output location
SET OUTPUT_DIR=D:\knowledge_pipeline\dist
:: 2. Temp build location
SET WORK_DIR=D:\knowledge_pipeline\build
:: 3. Desired Name of the Executable (and initial folder)
SET EXE_NAME=Start_Knowledge_Pipeline
:: 4. Desired Final Folder Name
SET FINAL_FOLDER_NAME=knowledge_pipeline
:: 5. Path to your source config folder
SET CONFIG_SRC=config

:: Calculated Paths
SET INITIAL_BUILD_DIR=%OUTPUT_DIR%\%EXE_NAME%
SET TARGET_DIR=%OUTPUT_DIR%\%FINAL_FOLDER_NAME%
SET FINAL_CONFIG_DIR=%TARGET_DIR%\config

echo ========================================================
echo  CLEANING PREVIOUS BUILDS
echo ========================================================
if exist "%OUTPUT_DIR%" rmdir /s /q "%OUTPUT_DIR%"
if exist "%WORK_DIR%" rmdir /s /q "%WORK_DIR%"

echo.
echo ========================================================
echo  BUILDING: Main Pipeline
echo  (EXE Name: %EXE_NAME%.exe)
echo ========================================================
:: Build with the specific EXE name. This creates dist\Start_Knowledge_Pipeline
pyinstaller --noconfirm --onedir --console --clean ^
 --name "%EXE_NAME%" ^
 --hidden-import="whisper" ^
 --collect-all="whisper" ^
 --distpath "%OUTPUT_DIR%" ^
 --workpath "%WORK_DIR%" ^
 main.py

echo.
echo ========================================================
echo  RENAMING FOLDER
echo ========================================================
:: Rename 'dist\Start_Knowledge_Pipeline' to 'dist\knowledge_pipeline'
if exist "%INITIAL_BUILD_DIR%" (
    move "%INITIAL_BUILD_DIR%" "%TARGET_DIR%" >nul
    echo [OK] Renamed folder to: %FINAL_FOLDER_NAME%
) else (
    echo [ERROR] Build folder not found. PyInstaller failed.
    pause
    exit /b
)

echo.
echo ========================================================
echo  BUILDING: Configurator
echo ========================================================
pyinstaller --noconfirm --onefile --noconsole --clean ^
 --name "Setup_Knowledge_Pipeline" ^
 --distpath "%OUTPUT_DIR%" ^
 --workpath "%WORK_DIR%" ^
 "%CONFIG_SRC%\configure.py"

echo.
echo ========================================================
echo  STRUCTURING FOLDERS & ASSETS
echo ========================================================

:: --- 1. CONFIGURATION FOLDER ---
if not exist "%FINAL_CONFIG_DIR%" mkdir "%FINAL_CONFIG_DIR%"
echo [OK] Created 'config' subfolder

:: Move Setup EXE to config folder
if exist "%OUTPUT_DIR%\Setup_Knowledge_Pipeline.exe" (
    move "%OUTPUT_DIR%\Setup_Knowledge_Pipeline.exe" "%FINAL_CONFIG_DIR%\" >nul
    echo [OK] Setup tool moved to config folder
)

:: Copy Config Files
if exist "%CONFIG_SRC%\settings.yaml" copy "%CONFIG_SRC%\settings.yaml" "%FINAL_CONFIG_DIR%\" >nul
if exist "%CONFIG_SRC%\.env.example" copy "%CONFIG_SRC%\.env.example" "%FINAL_CONFIG_DIR%\" >nul
if exist "%CONFIG_SRC%\.env" copy "%CONFIG_SRC%\.env" "%FINAL_CONFIG_DIR%\" >nul
echo [OK] Config files copied

:: --- 2. ROOT DOCUMENTATION (LICENSE & README) ---
echo Copying documentation...

if exist "LICENSE" (
    copy "LICENSE" "%TARGET_DIR%\" >nul
    echo [OK] LICENSE copied
) else (
    echo [WARNING] LICENSE file not found in root.
)

if exist "Readme.md" (
    copy "Readme.md" "%TARGET_DIR%\" >nul
    echo [OK] Readme.md copied
) else (
    echo [WARNING] Readme.md file not found in root.
)

echo.
echo ========================================================
echo  BUILD COMPLETE
echo  Folder:      %TARGET_DIR%
echo  Executable:  %TARGET_DIR%\%EXE_NAME%.exe
echo  Config Tool: %FINAL_CONFIG_DIR%\Setup_Knowledge_Pipeline.exe
echo ========================================================
pause