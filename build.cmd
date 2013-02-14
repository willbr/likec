@echo off

if "%1"=="" (
    call :compile almost.c
) else (
    call :%1 %2
)
exit /b


:c
:compile
    python compile.py %1
    exit /b %ERRORLEVEL%

:test
    python test_tokenizer.py
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
    python pf_parser.py %1
    exit /b %ERRORLEVEL%

:t
:tokens
    python Tokenizer.py %1
    exit /b %ERRORLEVEL%

