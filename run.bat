@echo off
chcp 65001 >nul
title Techtoon Accounting - C# Edition
color 0A

echo.
echo  ==================================================
echo            Techtoon Accounting System
echo            C# Edition - v1.0.0
echo  ==================================================
echo.
echo  Starting Techtoon Accounting...
echo  Please wait while the application loads...
echo.

cd /d "D:\PROG\Accounting Prog\Techtoon Accounting C+"
dotnet run --project Techtoon.UI --no-build

echo.
echo  Application closed.
pause