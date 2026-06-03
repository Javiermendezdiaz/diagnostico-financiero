REM Script VBS para iniciar servidor Diagnóstico Financiero
REM Uso: Doble-click en este archivo

Set objShell = CreateObject("WScript.Shell")
strPath = objShell.CurrentDirectory

REM Mostrar información
objShell.Popup "Iniciando Diagnóstico Financiero..." & vbCrLf & vbCrLf & "Carpeta: " & strPath, 3, "Diagnóstico Financiero"

REM Cambiar a carpeta del proyecto
objShell.CurrentDirectory = strPath

REM Ejecutar servidor en nueva ventana de CMD
REM El /K mantiene la ventana abierta después de ejecutar
objShell.Run "cmd /K python app_standalone.py", 1, False

REM Mostrar mensaje de confirmación
objShell.Popup "Servidor iniciado en http://localhost:8000" & vbCrLf & vbCrLf & "La ventana del servidor se abrirá en unos segundos...", 5, "Éxito"
