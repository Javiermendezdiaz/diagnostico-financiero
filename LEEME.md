# Cómo trabajar con este proyecto

## Solo hay un fichero que ejecutar

**`EJECUTAR.bat`** — doble clic. Tarda unos diez minutos y hace todo:

1. Compara cada fichero con lo publicado en GitHub
2. Comprueba las 29 verificaciones de las cifras
3. Compila el informe individual y el de pareja
4. Exporta las páginas a PNG en la carpeta `PAGINAS` para poder revisarlas
5. Deja en `SUBIR-A-GITHUB` los ficheros que hay que subir

Al terminar deja **`RESULTADO.txt`**. Si pone VERDE, se puede subir.

> Los demás `.bat` de la carpeta (VERIFICAR, VERIFICAR2, FINAL, CIERRE, VER,
> MIRAR, SUBIR, COMPARAR) son versiones antiguas. **Se pueden borrar.**

---

## La regla de oro

**La carpeta local NO es una copia fiel de lo publicado en GitHub.**

Algunos ficheros van por detrás y contienen errores que ya estaban corregidos
arriba. El 10-sep-2026 aparecieron tres, ninguno introducido a propósito:

| Dónde | Qué pasaba |
|---|---|
| `report_couple.py` | Las barras de comparación se dibujaban al revés que el número impreso al lado |
| `report_couple.py` | Lo mismo otra vez, en la sección faceta por faceta |
| `legado_pages.py` | Se pasaba la rentabilidad como `5.5` en vez de `0.055` — un **550% anual**, que adelantaba muchísimo la fecha de libertad del cliente |

Por eso **nunca se sube un fichero sin compararlo antes**. `EJECUTAR.bat` lo hace
automáticamente y escribe el detalle en `COMPARACION.txt`.

---

## OneDrive

El repositorio vive dentro de OneDrive, que bloquea los ficheros temporales
mientras sincroniza. Eso hacía que las compilaciones fallaran de forma aleatoria
(`Permission denied: _proy.png`). Por eso `EJECUTAR.bat` compila en una carpeta
temporal fuera de OneDrive y luego trae los resultados de vuelta.

---

## Cómo subir a GitHub

1. Abrir `https://github.com/Javiermendezdiaz/diagnostico-financiero/upload/main`
2. Arrastrar los ficheros de la carpeta `SUBIR-A-GITHUB` — **solo esos**
3. Escribir un mensaje y pulsar *Commit changes*

Render redespliega solo en un par de minutos.

---

## Las redes de seguridad que existen

- **`test_numeros.py`** — 29 comprobaciones de las cifras. La **I9** es la que
  garantiza que el Número de Libertad sea el mismo por todas las rutas del
  informe (llegó a haber 248.000 € de diferencia entre dos páginas).
- **`probar_pareja.py`** — comprueba que las barras del informe de pareja usan la
  misma escala que los números impresos al lado.
- **`mirar_informe.py`** — compila un informe real y verifica la coherencia.
- **`comparar.py`** — compara con GitHub, fichero a fichero.
- **`ver_paginas.py`** — exporta páginas del PDF a PNG para revisar la maqueta.
- **`ci_check.py`** — inspección completa: HTML, sintaxis, cifras y 7 informes.
