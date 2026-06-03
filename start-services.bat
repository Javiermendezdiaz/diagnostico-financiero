@echo off
start /d "C:\Users\javie\OneDrive\Escritorio\diagnostico financiero" cmd /k "npm run db:seed"
timeout /t 8
start /d "C:\Users\javie\OneDrive\Escritorio\diagnostico financiero" cmd /k "npm run dev:backend"
timeout /t 3
start /d "C:\Users\javie\OneDrive\Escritorio\diagnostico financiero" cmd /k "npm run dev:frontend"
