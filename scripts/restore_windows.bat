@echo off
setlocal enabledelayedexpansion

echo ============================================
echo  NapsterLegal — Windows DB Restore (Option B)
echo ============================================
echo.

:: ── CONFIG ──────────────────────────────────────────────────────────────────
set PG="C:\Program Files\PostgreSQL\17\bin"
set BACKUPS=%~dp0..\backups
set DB_NAME=napsterlegal_db
set DB_USER=napster_user
set DB_PASS=napster_pass_2024
set ANALYTICS_DB=napsterlegal_analytics

:: ── PGPASSWORD pour eviter les prompts ──────────────────────────────────────
set PGPASSWORD=%DB_PASS%

echo [1/6] Verification des fichiers backup...
if not exist "%BACKUPS%\napsterlegal_primary.dump" (
    echo ERREUR: napsterlegal_primary.dump introuvable dans backups\
    pause & exit /b 1
)
if not exist "%BACKUPS%\napsterlegal_analytics.sql" (
    echo ERREUR: napsterlegal_analytics.sql introuvable dans backups\
    pause & exit /b 1
)
echo OK — fichiers trouves.
echo.

echo [2/6] Creation de l'utilisateur napster_user...
%PG%\psql.exe -U postgres -p 5432 -c "CREATE USER %DB_USER% WITH PASSWORD '%DB_PASS%';" 2>nul
%PG%\psql.exe -U postgres -p 5433 -c "CREATE USER %DB_USER% WITH PASSWORD '%DB_PASS%';" 2>nul
echo OK.
echo.

echo [3/6] Creation des bases PRIMARY (5432) et REPLICA (5433)...
%PG%\psql.exe -U postgres -p 5432 -c "DROP DATABASE IF EXISTS %DB_NAME%;"
%PG%\psql.exe -U postgres -p 5432 -c "CREATE DATABASE %DB_NAME% OWNER %DB_USER%;"
%PG%\psql.exe -U postgres -p 5433 -c "DROP DATABASE IF EXISTS %DB_NAME%;"
%PG%\psql.exe -U postgres -p 5433 -c "CREATE DATABASE %DB_NAME% OWNER %DB_USER%;"
echo OK.
echo.

echo [4/6] Restauration PRIMARY (port 5432)...
%PG%\pg_restore.exe -U %DB_USER% -p 5432 -d %DB_NAME% -v "%BACKUPS%\napsterlegal_primary.dump"
if errorlevel 1 (
    echo ATTENTION: pg_restore a retourne des warnings — verifiez les logs.
) else (
    echo OK.
)
echo.

echo [5/6] Restauration REPLICA (port 5433) — meme dump...
%PG%\pg_restore.exe -U %DB_USER% -p 5433 -d %DB_NAME% -v "%BACKUPS%\napsterlegal_primary.dump"
if errorlevel 1 (
    echo ATTENTION: pg_restore a retourne des warnings — verifiez les logs.
) else (
    echo OK.
)
echo.

echo [6/6] Restauration MariaDB analytics (port 3306)...
mysql -u root -p%ANALYTICS_DB% -e "CREATE DATABASE IF NOT EXISTS %ANALYTICS_DB% CHARACTER SET utf8mb4;"
mysql -u root -p "%BACKUPS%\napsterlegal_analytics.sql" %ANALYTICS_DB%
if errorlevel 1 (
    echo ERREUR: restauration MariaDB echouee.
    pause & exit /b 1
) else (
    echo OK.
)
echo.

echo ============================================
echo  Verification finale...
echo ============================================
%PG%\psql.exe -U %DB_USER% -p 5432 -d %DB_NAME% -c "SELECT pg_is_in_recovery();" 
%PG%\psql.exe -U %DB_USER% -p 5433 -d %DB_NAME% -c "SELECT pg_is_in_recovery();"
echo.
echo DONE — Les 3 bases sont restaurees.
echo   PRIMARY   → localhost:5432/%DB_NAME%
echo   REPLICA   → localhost:5433/%DB_NAME%
echo   ANALYTICS → localhost:3306/%ANALYTICS_DB%
echo.
pause
