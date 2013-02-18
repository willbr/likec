@echo off

if "%1"=="" (
    call :compile almost.c
) else (
    call :%1 %2
)
exit /b


:c
:compile
    python prefix_compiler.py %1
    exit /b %ERRORLEVEL%

:test
    python -m unittest discover
    exit /b %ERRORLEVEL%

:g
:gcc
    call :compile %1 > out.c && gcc -Wall -g out.c
    exit /b %ERRORLEVEL%

:r
:run
    call :gcc %1 && a.exe
    exit /b %ERRORLEVEL%

:p
:parse
    python prefix_parser.py %1
    exit /b %ERRORLEVEL%

:t
:tokens
    python prefix_tokenizer.py %1
    exit /b %ERRORLEVEL%

