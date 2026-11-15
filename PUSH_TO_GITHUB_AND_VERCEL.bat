@echo off
title Push CalcWorker Changes to GitHub and Live Vercel
color 0a
cls
echo =====================================================================
echo       PUSH CALCWORKER CHANGES TO GITHUB & LIVE DEPLOY VERCEL
echo =====================================================================
echo.
cd /d "%~dp0"

echo [1] Checking status...
git status
echo.
set /p commit_msg="Enter commit message (ya bas Enter dabayein): "
if "%commit_msg%"=="" set commit_msg=Update CalcWorker via Claude AI

echo.
echo [2] Adding files and committing...
git add .
git commit -m "%commit_msg%"

echo.
echo [3] Pushing to GitHub (main branch)...
git push origin main

echo.
echo =====================================================================
echo SUCCESS! CODE GITHUB PE PUSH HO GAYA!
echo Vercel ab 10-15 seconds mein https://calcworker.com ko auto-deploy kar dega!
echo =====================================================================
pause
