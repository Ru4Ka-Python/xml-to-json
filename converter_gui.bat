@echo off
chcp 65001 > nul
color 0F
cls

echo ========================================================
echo   ULTIMATE XML CONVERTER (AI DATASET EDITION)
echo ========================================================

python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python не найден.
    pause
    exit /b
)

echo.
echo [System] Проверка библиотек...
pip install lxml orjson xmltodict tqdm --disable-pip-version-check > nul

echo.
echo [System] Запуск конвертера...
echo --------------------------------------------------------
python converter.py
echo.
pause