#!/bin/bash
git init
git config user.email "javier@mendezconsultoria.com"
git config user.name "Javier Mendez"
git branch -M main
git add -A
git commit -m "Deploy corrected single-port FastAPI architecture"
git remote add origin https://github.com/Javiermendezdiaz/diagnostico-financiero.git
echo "Ready to push"
