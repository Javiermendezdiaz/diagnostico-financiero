#!/bin/bash
# Redirigir caché de Rust a zona escribible en Render
export CARGO_HOME=/tmp/.cargo
export NUMPY_EXPERIMENTAL_ARRAY_FUNCTION=1
pip install -r requirements.txt
