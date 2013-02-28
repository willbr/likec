@echo off

if "%1"=="" (
    call :default
) else (
    call :%*
)
exit /b %ERRORLEVEL%

:default
    call :compile almost.c
    exit /b %ERRORLEVEL%

:c
:compile
    python -tt prefix_compiler.py %1
    exit /b %ERRORLEVEL%

:test
    python -tt -m unittest discover
    exit /b %ERRORLEVEL%

:g
:gcc
    call :compile %1 > out.c && gcc -Wall -g out.c
    exit /b %ERRORLEVEL%

:r
:run
    call :gcc %1 && a.exe %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%

:p
:parse
    python -tt prefix_parser.py %1
    exit /b %ERRORLEVEL%

:t
:tokens
    python -tt prefix_tokenizer.py %1
    exit /b %ERRORLEVEL%

