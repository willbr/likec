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

:gcc
    call :default > out.c && gcc -Wall -g out.c
    exit /b %ERRORLEVEL%

:run
    call :gcc && a.exe
    exit /b %ERRORLEVEL%

:parse
    python pf_parser.py almost.c
    exit /b %ERRORLEVEL%

:tokens
    python Tokenizer.py almost.c
    exit /b %ERRORLEVEL%

