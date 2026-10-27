# -*- coding: utf-8 -*-
"""ITAP · Control de calidad VISUAL del PDF antes de que salga.

Revisa el PDF YA generado (lo que el cliente va a ver), no el codigo:
  1. Paginas vacias o casi vacias (un desbordamiento que deja 3 lineas solas en una hoja).
  2. Texto que se sale del papel (cortado en el borde).
  3. Plantilla rota: "None", "nan", "%s", "{nombre}"... impresos tal cual.
  4. Cifras incoherentes: el Numero de Libertad debe ser UNO en todo el libro.
  5. Promesa comercial: la web dice "mas de 50 paginas" en el completo y en pareja.

A prueba de fallos: NUNCA lanza excepcion ni bloquea la entrega. Devuelve una lista de
hallazgos [{severidad, regla, pagina, mensaje}] para avisar a Adapta con el detalle.
"""
import re

_CABECERA = ("ADAPTA", "FAMILY OFFICE", "DOCUMENTO CONFIDENCIAL", "NO ES ASESORAMIENTO")
_RE_PAG = re.compile(r"^\s*\d{1,3}\s*/\s*\d{1,3}\s*$")
_RE_PARTE = re.compile(r"^\s*PARTE\s+\d\s*·")
_RE_ROTO = re.compile(r"\bNone\b|\bnan\b|\bNaN\b|%\(?[a-z_]*\)?[sd]\b|\{[a-z_]{2,}\}|Traceback|\uFFFD|\x00")
_RE_NUM = [re.compile(r"N[ÚU]MERO DE LIBERTAD\s*\n\s*([\d\.]{5,}) ?€"),
           re.compile(r"N[úu]mero de Libertad (?:de (?:vuestro|tu) hogar )?es (?:de )?([\d\.]{5,}) ?€")]


def _contenido(texto):
    """Texto de la pagina sin cabecera, pie ni numero de pagina."""
    out = []
    for ln in (texto or "").splitlines():
        s = ln.strip()
        if not s or _RE_PAG.match(s) or _RE_PARTE.match(s):
            continue
        if any(s.upper().startswith(c) for c in _CABECERA):
            continue
        out.append(s)
    return " ".join(out)


def revisar(path, tier=None):
    hall = []
    try:
        import fitz  # PyMuPDF
    except Exception as e:
        return [{"severidad": "aviso", "regla": "qa_no_disponible", "pagina": None,
                 "mensaje": "No se pudo revisar el PDF (falta PyMuPDF: %s)." % e}]
    try:
        doc = fitz.open(path)
    except Exception as e:
        return [{"severidad": "critico", "regla": "pdf_ilegible", "pagina": None,
                 "mensaje": "El PDF no se puede abrir: %s" % e}]
    nums = {}
    try:
        n = len(doc)
        flags = fitz.TEXTFLAGS_DICT & ~fitz.TEXT_MEDIABOX_CLIP   # ver tambien el texto que se sale del papel
        for i, pg in enumerate(doc):
            p = i + 1
            try:
                txt = pg.get_text("text")
                cont = _contenido(txt)
                imgs = len(pg.get_images(full=False))
                try:
                    dib = len(pg.get_drawings())
                except Exception:
                    dib = 0
                # 1) vacias / casi vacias (las paginas-imagen y las de grafico no cuentan)
                if p not in (1, n) and imgs == 0 and dib < 25:
                    if len(cont) < 40:
                        hall.append({"severidad": "alto", "regla": "pagina_vacia", "pagina": p,
                                     "mensaje": "Página %d prácticamente en blanco." % p})
                    elif len(cont) < 220:
                        hall.append({"severidad": "aviso", "regla": "pagina_casi_vacia", "pagina": p,
                                     "mensaje": "Página %d casi vacía (%d caracteres): posible desbordamiento. Empieza: «%s…»"
                                                % (p, len(cont), cont[:70])})
                # 2) texto fuera del papel
                W, H = pg.rect.width, pg.rect.height
                fuera = []
                for b in pg.get_text("dict", flags=flags).get("blocks", []):
                    for l in b.get("lines", []):
                        for s in l.get("spans", []):
                            t = (s.get("text") or "").strip()
                            if not t:
                                continue
                            x0, y0, x1, y1 = s["bbox"]
                            if x1 > W + 1 or x0 < -1 or y1 > H + 1 or y0 < -1:
                                fuera.append(t[:40])
                if fuera:
                    hall.append({"severidad": "alto", "regla": "texto_cortado", "pagina": p,
                                 "mensaje": "Página %d: texto que se sale del papel: «%s»" % (p, " | ".join(fuera[:3]))})
                # 3) plantilla rota
                m = _RE_ROTO.search(cont)
                if m:
                    a = max(0, m.start() - 30)
                    hall.append({"severidad": "alto", "regla": "plantilla_rota", "pagina": p,
                                 "mensaje": "Página %d: aparece «%s» impreso tal cual (…%s…)." % (p, m.group(0), cont[a:m.end() + 30])})
                # 4) numero de libertad
                for rx in _RE_NUM:
                    for v in rx.findall(txt):
                        nums.setdefault(v, []).append(p)
            except Exception:
                continue
        if len(nums) > 1:
            det = "; ".join("%s € (págs. %s)" % (v, ", ".join(str(x) for x in sorted(set(ps))))
                            for v, ps in nums.items())
            hall.append({"severidad": "critico", "regla": "numero_incoherente", "pagina": None,
                         "mensaje": "El Número de Libertad no es el mismo en todo el libro: " + det})
        # 5) promesa comercial de la web
        try:
            if int(tier or 0) in (2, 3) and n <= 50:
                hall.append({"severidad": "aviso", "regla": "menos_de_50", "pagina": None,
                             "mensaje": "El libro tiene %d páginas y la web promete más de 50." % n})
        except Exception:
            pass
    finally:
        try:
            doc.close()
        except Exception:
            pass
    return hall


def resumen_html(hall):
    if not hall:
        return ""
    col = {"critico": "#B91C1C", "alto": "#C2410C", "aviso": "#6B7280"}
    li = "".join("<li><b style='color:%s'>%s</b> · %s</li>" % (col.get(h["severidad"], "#333"), h["severidad"].upper(), h["mensaje"])
                 for h in hall)
    return ("<div style='margin-top:14px;padding:12px 14px;border:1px solid #F3C4B5;background:#FFF7F3;border-radius:8px'>"
            "<b>Control de calidad visual</b> (el cliente ya lo tiene; revisa y, si hace falta, regenera y reenvía):<ul>%s</ul></div>" % li)


def resumen_log(hall):
    return "\n".join("  [%s] %s" % (h["severidad"], h["mensaje"]) for h in hall)


if __name__ == "__main__":
    import sys
    for f in sys.argv[1:]:
        r = revisar(f, tier=(sys.argv[0] and None))
        print("==", f, "->", len(r), "hallazgos")
        print(resumen_log(r) or "  OK")
