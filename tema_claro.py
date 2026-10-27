# -*- coding: utf-8 -*-
"""TEMA CLARO para las paginas-imagen del libro.

Por que existe: el libro mezclaba paginas oscuras (azul marino y dorado) con paginas
crema de estilo editorial y se leia como dos documentos grapados. Este modulo pasa una
pagina oscura (SVG de matplotlib o PNG) a la paleta crema del libro sin redibujarla:

  · fondos y paneles oscuros  -> cremas (los paneles un punto mas oscuros, para que se distingan)
  · textos claros              -> tinta
  · grises medios              -> se invierten
  · colores con caracter (oro, rojo, verde) -> se conservan, algo mas oscuros para contrastar

Failsafe: si algo falla, devuelve la ruta original y la pagina sale como antes.
"""
import base64
import colorsys
import io
import os
import re

CREMA_CLARA = (0xFB, 0xF8, 0xF1)   # fondo
CREMA_OSCURA = (0xEC, 0xE4, 0xD2)  # paneles
TINTA = (0x14, 0x16, 0x1D)


def _lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def color(r, g, b):
    """Un color (0-255) del tema oscuro a su equivalente en el tema claro."""
    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    if l < 0.26:                                   # fondos, paneles, pistas de barras
        return _lerp(CREMA_CLARA, CREMA_OSCURA, min(1.0, l / 0.26))
    if l > 0.78 and s < 0.65:                      # textos claros -> tinta
        nl = 0.09 + (1.0 - l) * 0.9
        rr, gg, bb = colorsys.hls_to_rgb(h, nl, min(s, 0.18))
        return (int(rr * 255), int(gg * 255), int(bb * 255))
    if s < 0.22:                                   # grises medios: se invierten
        rr, gg, bb = colorsys.hls_to_rgb(h, 1.0 - l, s)
        return (int(rr * 255), int(gg * 255), int(bb * 255))
    nl = l * 0.74 if l > 0.5 else l                # oro/rojo/verde: algo mas oscuros sobre crema
    rr, gg, bb = colorsys.hls_to_rgb(h, nl, s)
    return (int(rr * 255), int(gg * 255), int(bb * 255))


def _hex(m):
    v = m.group(1)
    r, g, b = int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
    return "#%02x%02x%02x" % color(r, g, b)


def _png(img):
    """Mismo mapeo, vectorizado y POR FRANJAS (memoria acotada: el servidor tiene 512 MB)."""
    import numpy as np
    from PIL import Image
    im = img.convert("RGBA")
    arr = np.asarray(im)
    out_all = np.empty_like(arr)
    c1 = np.array(CREMA_CLARA, dtype=np.float32) / 255.0
    c2 = np.array(CREMA_OSCURA, dtype=np.float32) / 255.0
    tinta = np.array(TINTA, dtype=np.float32) / 255.0
    for y0 in range(0, arr.shape[0], 200):
        a = arr[y0:y0 + 200].astype(np.float32) / 255.0
        rgb, alpha = a[..., :3], a[..., 3:]
        mx, mn = rgb.max(-1), rgb.min(-1)
        l = (mx + mn) / 2.0
        d = mx - mn
        s = np.where(d < 1e-6, 0.0, np.where(l < 0.5, d / np.maximum(mx + mn, 1e-6), d / np.maximum(2.0 - mx - mn, 1e-6)))
        out = rgb.copy()
        osc = l < 0.26
        t = np.clip(l / 0.26, 0, 1)[..., None]
        out = np.where(osc[..., None], c1 + (c2 - c1) * t, out)
        cla = (l > 0.78) & (s < 0.65) & ~osc
        out = np.where(cla[..., None], tinta, out)
        gris = (s < 0.22) & ~osc & ~cla
        out = np.where(gris[..., None], 1.0 - rgb, out)
        out_all[y0:y0 + 200] = (np.concatenate([np.clip(out, 0, 1), alpha], -1) * 255).astype("uint8")
    return Image.fromarray(out_all, "RGBA")


def claro(path):
    """Devuelve la ruta de la version clara de una pagina-imagen (SVG o PNG). Failsafe."""
    try:
        base, ext = os.path.splitext(path)
        dest = base + "_claro" + ext
        ext = ext.lower()
        if ext == ".svg":
            txt = open(path, encoding="utf-8").read()

            def _img(m):
                try:
                    from PIL import Image
                    raw = base64.b64decode(m.group(2))
                    im = _png(Image.open(io.BytesIO(raw)))
                    buf = io.BytesIO(); im.save(buf, "PNG")
                    return m.group(1) + base64.b64encode(buf.getvalue()).decode("ascii")
                except Exception:
                    return m.group(0)
            txt = re.sub(r'(data:image/png;base64,)([A-Za-z0-9+/=\s]+)', _img, txt)
            txt = re.sub(r'#([0-9a-fA-F]{6})\b', _hex, txt)
            open(dest, "w", encoding="utf-8").write(txt)
            return dest
        if ext in (".png", ".jpg", ".jpeg"):
            from PIL import Image
            _png(Image.open(path)).convert("RGB").save(dest)
            return dest
    except Exception as e:
        import sys
        sys.stderr.write("[tema_claro] se deja oscura %s: %s\n" % (path, e))
    return path
