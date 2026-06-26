@echo off
echo [%date% %time%] Debut sync replica...

set PG="C:\Program Files\PostgreSQL\17\bin"
set DB_NAME=napsterlegal_db
set DB_USER=napster_user
set PGPASSWORD=napster_pass_2024
set TEMP_DUMP=%TEMP%\napster_sync_temp.dump

%PG%\pg_dump.exe -U %DB_USER% -p 5432 -d %DB_NAME% -F c -f %TEMP_DUMP%
if errorlevel 1 goto error

%PG%\psql.exe -U postgres -p 5433 -c "DROP DATABASE IF EXISTS %DB_NAME%;"
%PG%\psql.exe -U postgres -p 5433 -c "CREATE DATABASE %DB_NAME% OWNER %DB_USER%;"
%PG%\pg_restore.exe -U %DB_USER% -p 5433 -d %DB_NAME% %TEMP_DUMP%
if errorlevel 1 goto error

echo [%date% %time%] Sync OK.
del %TEMP_DUMP%
goto end

:error
echo [%date% %time%] SYNC FAILED.

:end
