@echo off
REM Component Tests Runner Script for Windows
REM Usage: scripts\run_component_tests.bat [options]

echo ================================
echo   Component Tests Runner
echo ================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not running!
    echo Please start Docker Desktop and try again.
    exit /b 1
)

echo [OK] Docker is running

REM Check if virtual environment exists
if not exist "venv" (
    echo Virtual environment not found. Creating...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install --upgrade pip
    pip install -r requirements-test.txt
) else (
    call venv\Scripts\activate.bat
)

echo [OK] Virtual environment activated

REM Check if pytest is installed
python -c "import pytest" 2>nul
if errorlevel 1 (
    echo pytest not found. Installing dependencies...
    pip install -r requirements-test.txt
)

echo [OK] Dependencies installed
echo.

REM Default test path
set TEST_PATH=tests/component/
set EXTRA_ARGS=

REM Parse arguments (simplified for Windows)
:parse_args
if "%1"=="" goto run_tests
if "%1"=="--e2e" (
    set TEST_PATH=tests/component/test_end_to_end_flow.py
    shift
    goto parse_args
)
if "%1"=="--parallel" (
    set EXTRA_ARGS=%EXTRA_ARGS% -n auto
    shift
    goto parse_args
)
if "%1"=="--coverage" (
    set EXTRA_ARGS=%EXTRA_ARGS% --cov=services --cov-report=html --cov-report=term
    shift
    goto parse_args
)
if "%1"=="--verbose" (
    set EXTRA_ARGS=%EXTRA_ARGS% -vv
    shift
    goto parse_args
)
if "%1"=="--quick" (
    set EXTRA_ARGS=%EXTRA_ARGS% -x
    shift
    goto parse_args
)

:run_tests
echo Running tests: %TEST_PATH%
echo.

pytest %TEST_PATH% -v %EXTRA_ARGS%
if errorlevel 1 (
    echo.
    echo ================================
    echo   Some tests failed!
    echo ================================
    exit /b 1
) else (
    echo.
    echo ================================
    echo   All tests passed!
    echo ================================
)

