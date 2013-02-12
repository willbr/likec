@echo off

if "%1"=="" (
    goto :default
) else (
    goto :%1
)
echo err: Unknown task
exit /b


:default
    python compile.py almost.c
    exit /b %ERRORLEVEL%

:test
    python test_tokenizer.py
    exit /b %ERRORLEVEL%

:g
:gcc
    call :default > out.c && gcc -Wall -g out.c
    exit /b %ERRORLEVEL%

:r
:run
    call :gcc && a.exe
    exit /b %ERRORLEVEL%

:p
:parse
    python pf_parser.py almost.c
    exit /b %ERRORLEVEL%

:t
:tokens
    python Tokenizer.py almost.c
    exit /b %ERRORLEVEL%

