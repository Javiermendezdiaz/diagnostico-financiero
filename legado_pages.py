# -*- coding: utf-8 -*-
"""Puente datos->diseño: alimenta las páginas-joya Legado con datos reales del motor."""
import os, legado_design as LD
SIM_URL=os.environ.get("ITAP_SIM_URL","https://javiermendezdiaz.github.io/diagnostico-financiero/simulador.html")

def _num(d,k):
    v=d.get(k); 
    try: return float(v) if v not in (None,"") else None
    except: return None

def _compact(n):
    try: n=float(n)
    except: return ("—","")
    if n>=1e6: return (("%.2f"%(n/1e6)).replace(".",","),"M")
    if n>=1e3: return (str(int(round(n/1e3))),"k")
    return (str(int(round(n))),"")

def stress(datos,p):
    ing=_num(datos,"ingreso_mensual") or 0; gas=_num(datos,"gasto_mensual") or 0
    col=_num(datos,"colchon_liquido") or 0; cuota=_num(datos,"cuota_deuda") or 0
    aho=_num(datos,"ahorro_mensual") or 0
    meses=(col/gas) if gas else 6.0
    dti=(100*cuota/ing) if ing else 0.0
    tasa=(100*aho/ing) if ing else 0.0
    c1=(p.get("C1",{}) or {}).get("score",0)/100.0
    s_col=max(0,min(1,(6-meses)/6)); s_dti=max(0,min(1,dti/45.0))
    s_aho=max(0,min(1,(20-tasa)/20.0)); s_c1=max(0,min(1,c1))
    idx=round(100*(0.30*s_col+0.20*s_dti+0.20*s_aho+0.30*s_c1))
    def col_(s): return "#3FB984" if s<0.34 else ("#E3B341" if s<0.67 else "#D9534F")
    drivers=[("Colchón de seguridad (%.1f meses)"%meses, max(.08,s_col), col_(s_col)),
             ("Carga de deuda (DTI %d%%)"%round(dti), max(.08,s_dti), col_(s_dti)),
             ("Tasa de ahorro (%s%%)"%(("%.1f"%tasa) if 0<tasa<10 else ("%d"%round(tasa))), max(.08,s_aho), col_(s_aho))]
    et="zona sana" if idx<40 else ("zona a vigilar" if idx<70 else "zona de alerta")
    return idx,et,drivers


def _asesor_health(perfil_in):
    t=((perfil_in or {}).get("asesor","") or "").lower()
    if any(k in t for k in ["confianza","family","patrimonial","estratég","estrateg","plan"]): return 80
    if any(k in t for k in ["gestor","papeleo","solo hace","banco","comercial"]): return 38
    if any(k in t for k in ["nadie","solo yo","por mi cuenta","ninguno","no teng"]): return 20
    return 50

def _tributacion_health(perfil_in):
    """Salud fiscal 0-100 a partir de las dos preguntas de fiscalidad (IRPF/productos + vivienda).
    Devuelve None si no se respondió ninguna (compatibilidad con sesiones antiguas)."""
    _m=[("lo controlo",80),("la conozco",80),("lo básico",45),("algo sé",45),
        ("voy a ciegas",20),("ni idea",20),("nunca me lo he planteado",12)]
    vals=[]
    for k in ("fiscalidad_nivel","fiscalidad_vivienda"):
        v=((perfil_in or {}).get(k,"") or "").lower()
        if (not v) or ("no aplica" in v) or ("no tengo vivienda" in v):
            continue
        for key,h in _m:
            if key in v:
                vals.append(h); break
    return round(sum(vals)/len(vals)) if vals else None

def sistema_items(extras, datos, p):
    perfil_in=(extras or {}).get("perfil_in") or {}
    def H(code):
        sc=(p.get(code,{}) or {}).get("score",None)
        return None if sc is None else max(0,min(100,round(100-sc)))
    def st(h):
        if h is None: return "Lo vemos juntos"
        return "Sólido" if h>=67 else ("En marcha" if h>=50 else ("A vigilar" if h>=34 else "Punto débil"))
    A=_asesor_health(perfil_in)
    T=_tributacion_health(perfil_in)
    rows=[("S","Saneamiento",H("C10")),("I","Ingresos",H("C7")),("S","Seguros",H("C5")),
          ("T","Tributación",T),("E","Excedentes",H("C9")),("M","Mantenimiento",H("C2")),
          ("A","Acompañamiento",A)]
    items=[(l,n,h,st(h)) for (l,n,h) in rows]
    nums=[(i,h) for i,(l,n,h,_) in enumerate(items) if h is not None]
    weakest=min(nums,key=lambda x:x[1])[0] if nums else 0
    return items,weakest


def _fac(p,code,key):
    return float(((p.get(code,{}) or {}).get("facetas",{}) or {}).get(key,0) or 0)

def _years_to(target,p0,monthly,r=0.07):
    w=p0
    for y in range(0,81):
        if w>=target: return y
        w=w*(1+r)+monthly*12
    return 81

def joyas_0001(seq, tmp, cli, datos, extras, p):
    """Páginas 0,001%: Blood Money, Escudo, Coste del Ego (Presente) + Arrepentimiento (Futuro)."""
    br=(extras or {}).get("brecha") or {}
    ing=_num(datos,"ingreso_mensual") or 0; gas=_num(datos,"gasto_mensual") or 0
    horas=_num(datos,"horas_semana"); col=_num(datos,"colchon_liquido") or 0
    invl=_num(datos,"inversiones_liquidas") or 0; pat=_num(datos,"patrimonio") or 0
    aho=_num(datos,"ahorro_mensual") or 0
    # BLOOD MONEY (solo si trabaja por horas)
    if horas and horas>0 and ing>0:
        eur=ing/(horas*4.33)
        items=[("Tu sueño (insomnio)",max(.05,_fac(p,"C1","insomnio")/100)),
               ("Tu cuerpo (somatización)",max(.05,_fac(p,"C1","somatizacion")/100)),
               ("Tu cabeza (rumiación)",max(.05,_fac(p,"C1","rumiacion")/100))]
        msg="Tu trabajo te paga %d €/hora en dinero. La factura la pagan tu sueño, tu cuerpo y tu cabeza — y luego gastas parte de ese dinero en recuperarlos."%round(eur)
        try: seq.append(LD.blood_money(tmp+"bm.svg",eur,items,msg))
        except Exception: pass
    # ESCUDO (siempre)
    try:
        realizable=((col+invl)/gas) if gas else 6
        c8=(100-(p.get("C8",{}) or {}).get("score",50))/100.0
        c5=(100-(p.get("C5",{}) or {}).get("score",50))/100.0
        s_desp=max(0,min(1,realizable/9.0))
        s_cisne=max(0,min(1,((col+0.7*invl)/gas/9.0) if gas else 0))*0.6+c8*0.4
        s_inval=c5*0.6+max(0,min(1,(pat/(gas*60)) if gas else 0))*0.4
        esc=[("Cisne negro",(("Inflación al 10%% y bolsas -30%%: tu vida resiste %d meses con lo líquido."%round((col+0.7*invl)/gas)) if gas else "—"),max(0,min(1,s_cisne))),
             ("Despido temprano","Tu ingreso principal cae a 0 mañana: aguantas %d meses con lo disponible."%round(realizable),s_desp),
             ("Invalidez","Un accidente te impide trabajar: %s."%("tu protección y patrimonio te dan margen" if s_inval>=0.5 else "hoy quedarías muy expuesto"),max(0,min(1,s_inval)))]
        seq.append(LD.escudo(tmp+"esc.svg",esc))
    except Exception: pass
    # COSTE DEL EGO (si declaró gasto de estatus)
    ge=_num(datos,"gasto_estatus")
    num=br.get("numero_ideal")
    if ge and ge>0 and num:
        try:
            y0=_years_to(num,pat,aho); y1=_years_to(num,pat,aho+ge)
            anos=max(0.0,y0-y1)
            n=min(30,max(5,_num(datos,"edad") and (65-_num(datos,"edad")) or 25))
            cap=ge*12*(((1.07**n)-1)/0.07)
            if anos>=0.5:
                seq.append(LD.coste_ego(tmp+"ego.svg",ge,anos,cap,n))
        except Exception: pass

def joya_arrepentimiento(seq, tmp, datos):
    eh=_num(datos,"edad_hijo_menor")
    if eh is not None and 0<=eh<18:
        try:
            findes=int(round((18-eh)*52))
            seq.append(LD.arrepentimiento(tmp+"arr.svg",findes,int(eh)))
        except Exception: pass


def _eu(n):
    try: return "{:,.0f} €".format(float(n)).replace(",",".")
    except: return "—"

def acelerador(seq, tmp, datos, extras, p):
    br=(extras or {}).get("brecha") or {}; num=br.get("numero_ideal")
    ing=_num(datos,"ingreso_mensual") or 0; gas=_num(datos,"gasto_mensual") or 0
    aho=_num(datos,"ahorro_mensual") or 0; pat=_num(datos,"patrimonio") or 0
    if not num or ing<=0: return
    try: seq.append(LD.acelerador_tabla(tmp+"acetab.svg",ing,gas,pat,num))
    except Exception: pass
    inv=((extras or {}).get("perfil_in") or {}).get("invierte","") or ""
    r0=1.5 if ("nada" in inv.lower() or inv=="") else (5.5 if "importante" in inv.lower() else 4.0)
    nuevo=aho+0.10*ing+0.10*gas
    y0=_years_to(num,pat,aho,r0); y10=_years_to(num,pat,nuevo,10.0)
    _inalc=(y0>=80)
    if _inalc and y10>=80: return   # ni con plan llega: no mostramos un payoff enganoso
    delta=max(0,y0-y10)
    if (not _inalc) and delta<0.5: return
    cil=[("Ingresos",_eu(ing),_eu(ing*1.1),"+10%"),
         ("Gastos",_eu(gas),_eu(gas*0.9),"−10%"),
         ("Rentabilidad","~%d%%"%round(r0),"~10%","S&P 500"),
         ("Patrimonio",_eu(pat),"+10%/año","compuesto")]
    # cilindro enemigo (psicología)
    c6=(p.get("C6",{}) or {}).get("score",0); c4=(p.get("C4",{}) or {}).get("score",0)
    c7=(p.get("C7",{}) or {}).get("score",0); comp=_fac(p,"C1","comparacion")
    if c6>=55 or c4>=55 or comp>=55:
        en=("Gastos","tu tendencia a la comparación y al estatus te empuja a gastar más en cuanto ganas más (la inflación del estilo de vida anula la fórmula)")
    elif "nada" in inv.lower() or inv=="":
        en=("Rentabilidad","tu capital está dormido; pasar de 'parado' a 'invertido con un plan' es tu mayor salto pendiente")
    elif c7>=55:
        en=("Ingresos","dependes demasiado de una sola fuente; subirla un 10% es frágil hasta que la diversifiques")
    else:
        en=("Gastos","mantener el gasto plano cuando suben los ingresos es donde casi todos fallan")
    try: seq.append(LD.acelerador_10x10(tmp+"ace.svg",cil,delta,en[0],en[1],y_plan=y10,inalcanzable=_inalc))
    except Exception: pass


def barrera(seq, tmp, datos, extras, p):
    p0=_num(datos,"patrimonio") or 0; aho=_num(datos,"ahorro_mensual") or 0
    if p0<=0 and aho<=0: return
    c6=(p.get("C6",{}) or {}).get("score",0); comp=_fac(p,"C1","comparacion")
    gas=_num(datos,"gasto_mensual") or 0; col=_num(datos,"colchon_liquido") or 0
    meses=(col/gas) if gas else 6
    if c6>=55 or comp>=55:
        cap="Tu mayor peligro: gastar este capital en estatus —un coche, un capricho— antes de cruzar los 100k. El día que lo tocas, reinicias el contador hacia tu libertad."
    elif meses<3:
        cap="Con tu colchón aún corto, la tentación de echar mano de este dinero ante un imprevisto es real. Para eso está tu fondo de emergencia; este reactor es sagrado y no se toca."
    else:
        cap="Tu mayor peligro: abandonar en el «Valle de las Sombras» de los primeros años, cuando el esfuerzo es alto y el interés aún parece invisible. Tu única métrica esos trimestres es la velocidad hacia los 100k."
    try: seq.append(LD.barrera_100k(tmp+"100k.svg",p0,aho,7,cap))
    except Exception: pass

def hero_open(cli, datos, extras, p, tmp="/tmp/_leg_", depth="completo", arq_meta=None):
    """Secuencia oscura de apertura, gateada por tier. esencial=T1 (reducido), completo=T2 (todo)."""
    completo = (depth != "esencial")
    seq=[]; nombre=cli.get("nombre") or "Cliente"
    ref=("AFO-%s"%(str(abs(hash(cli.get('email') or nombre))%9999)).zfill(4))
    seq.append(LD.cover(tmp+"00.svg",nombre,cli.get("fecha",""),ref=ref))
    br=(extras or {}).get("brecha") or {}
    if completo:
        seq.append(LD.divider(tmp+"01.svg","Sección I — Pasado",["Arqueología del","Comportamiento"],
            "Las decisiones y creencias que construyeron, en silencio, tus cimientos de hoy.",
            tint="#0E1622", accent="#8FA1BC"))
        if arq_meta:
            _pars=[arq_meta.get("desc",""),
                   "Esta forma de mirar el dinero no nació contigo: se aprendió, en lo que viste y oíste de pequeño sobre el dinero. No es un defecto. Es un guion — y todo guion se puede leer.",
                   "Hoy se nota así: %s Y su reverso: %s" % (arq_meta.get("luz",""), arq_meta.get("sombra",""))]
            seq.append(LD.guion_dinero(tmp+"01r.svg", arq_meta.get("nombre","Tu arquetipo"),
                arq_meta.get("lema",""), _pars,
                "Un guion se puede reescribir. Empieza por verlo.", accent="#8FA1BC"))
    ci=br.get("coste_ideal_mes"); ing=br.get("ingreso_mes"); gap=br.get("brecha_mes")
    if ci:
        if gap and gap>0:
            dn,du=_compact(gap*12)
            seq.append(LD.efecto_espejo(tmp+"02.svg","El espejo",
                "La vida que describí como ideal cuesta %s al mes."%LD_fmt(ci),
                "%s%s/año"%(dn,du),
                "Hoy tu modelo genera %s/mes; tu vida ideal pide %s/mes. Esa distancia anual es, exactamente, lo que vamos a cerrar. No es un fracaso: es el mapa."%(LD_fmt(ing or 0),LD_fmt(ci)),
                "Cerremos la brecha.", accent="#8FA1BC"))
        else:
            seq.append(LD.efecto_espejo(tmp+"02.svg","El espejo",
                "La vida que describí como ideal cuesta %s al mes."%LD_fmt(ci),
                "Ya llegas","Hoy tu flujo ya cubre tu vida ideal. El reto deja de ser cuánto ganas y pasa a ser a qué velocidad conviertes ese margen en capital que trabaje por ti.",
                "Ahora, protégelo.", accent="#8FA1BC"))
    if completo:
        seq.append(LD.divider(tmp+"03.svg","Sección II — Presente",["Radiografía","del Capital"],
            "Dónde estás hoy, medido no en cuánto tienes, sino en cuánta paz y cuánta libertad te da.",
            tint=LD.GLOW, accent=LD.BLUE))
    idx,et,drv=stress(datos,p)
    seq.append(LD.termometro(tmp+"04.svg","El termómetro de tu estrés financiero",idx,et,drv,accent=LD.BLUE))
    if completo:
        rp=_num(datos,"renta_pasiva") or 0; ingm=_num(datos,"ingreso_mensual") or 0
        pp=(rp/ingm) if ingm else 0.0
        seq.append(LD.matriz_tiempo(tmp+"04b.svg",pp,max(0,ingm-rp),rp,accent=LD.BLUE))
    try:
        _it,_wk=sistema_items(extras,datos,p)
        seq.append(LD.sistema_scorecard(tmp+"04c.svg",_it,_wk,accent=LD.BLUE))
    except Exception:
        pass
    if completo:
        joyas_0001(seq,tmp,cli,datos,extras,p)
        seq.append(LD.divider(tmp+"05.svg","Sección III — Futuro",["Visión","y Libertad"],
            "Hacia dónde vas, y el número exacto que convierte tu trabajo en una elección.",
            tint="#13202A", accent=LD.GOLD))
        barrera(seq,tmp,datos,extras,p)
    num=br.get("numero_ideal")
    if num:
        dn,du=_compact(num)
        bullets=[]
        if ci: bullets.append("Es el capital que, al 4%% prudente, paga tus %s/mes sin depender de una nómina."%LD_fmt(ci))
        _pension=_num(datos,"pension_estimada") or 0
        if ci and _pension>0:
            if _pension<ci:
                _num_aj=max(0,(ci-_pension))*12*25
                bullets.append("Al jubilarte no partes de cero: tu pensión estimada (%s/mes) cubre una parte. Contando con ella, el capital que necesitas baja a %s."%(LD_fmt(_pension),LD_fmt(_num_aj)))
            else:
                bullets.append("Tu pensión estimada (%s/mes) cubriría tu coste de vida: ese número, para el retiro, es casi cero. La cifra grande es para liberarte ANTES de jubilarte."%LD_fmt(_pension))
        bullets.append("Tu primera misión no es llegar: es asegurar el mes y dormir tranquilo.")
        seq.append(LD.bignum(tmp+"06.svg","Tu número de libertad",dn,du,"euros que compran tu tiempo",
            "El objetivo de seguridad",
            "Es la cifra que, generando renta, te permite vivir de tu patrimonio y no de tu tiempo.",
            bullets, accent=LD.GOLD))
    if completo:
        acelerador(seq,tmp,datos,extras,p)
        # Plan de 100 dias: TRES movimientos imperativos y claros (no diagnosticos)
        _dt=(extras or {}).get("deuda_tipo")
        _gas100=_num(datos,"gasto_mensual") or 0; _ing100=_num(datos,"ingreso_mensual") or 0
        _aho100=_num(datos,"ahorro_mensual") or 0; _col100=_num(datos,"colchon_liquido") or 0
        _meses100=(_col100/_gas100) if _gas100 else 99
        _tasa100=(100*_aho100/_ing100) if _ing100 else 0
        _inv100=((extras or {}).get("perfil_in") or {}).get("invierte","") or ""
        if _dt and "freno" in str(_dt[0]).lower():
            m1=("Ataca tu deuda más cara","Cada euro de interés que matas es la rentabilidad más segura que existe. Es tu primer movimiento, antes que ahorrar o invertir.")
        elif _meses100<3:
            m1=("Blinda tu colchón de 3 meses","Tu suelo: tres meses de gastos en una cuenta remunerada. Hecho esto, cualquier imprevisto deja de ser una amenaza.")
        elif _tasa100<10:
            m1=("Abre una rendija de excedente","Automatiza un ahorro fijo el día de cobro, aunque empiece pequeño. Lo que importa no es la cifra: es arrancar el hábito.")
        else:
            m1=("Da destino a tu excedente","Que cada euro que sobra tenga un sitio antes del día 5 del mes. Lo que no se dirige, se evapora sin que lo notes.")
        m2=("Automatiza tu ahorro","Que salga solo el día de cobro, antes de gastar. El sistema vence a la fuerza de voluntad: lo que no ves, no lo gastas.")
        if ("nada" in _inv100.lower()) or _inv100=="":
            m3=("Pon tu patrimonio a trabajar","Pasar de «parado» a «invertido con un plan» es tu mayor salto pendiente. Empieza, mide y ajusta el rumbo.")
        else:
            m3=("Reequilibra y consolida","Revisa tu fortuna neta, ajusta lo que se haya desviado y consolida el hábito. A partir de aquí, el plan es tuyo.")
        seq.append(LD.mapa_100(tmp+"07.svg",[
            ("Día 1–30",m1[0],m1[1]),
            ("Día 31–60",m2[0],m2[1]),
            ("Día 61–100",m3[0],m3[1])], accent=LD.GOLD))
        if arq_meta:
            _man="%s Y, esta vez, lo ejecutas: actúas sobre tu plan en lugar de aplazarlo." % (arq_meta.get('luz','') or '')
            seq.append(LD.el_salto(tmp+"07b.svg", arq_meta.get('nombre','Tu arquetipo'),
                arq_meta.get('sombra','') or 'Tu punto ciego te cuesta dinero y tranquilidad sin que lo veas.',
                _man, "No tienes que ser otro. Solo el mismo, sin la fuga.", accent=LD.GOLD))
        joya_arrepentimiento(seq,tmp,datos)
    try:
        seq.append(LD.qr_golden(tmp+"08.svg",SIM_URL,"Tu Simulador de Libertad",
            "Tu libro te da el diagnóstico. Este código abre tu simulador: mueve tus variables y mira, en vivo, cómo cada decisión adelanta o retrasa tu libertad. No se vende; se gana terminando tu libro.", accent=LD.GOLD))
    except Exception:
        pass
    if not completo:
        seq.append(LD.anzuelo(tmp+"anz.svg",[
            "Tu Pasado: la arqueología de tus creencias del dinero.",
            "Blood Money: lo que tu trabajo le cuesta a tu salud.",
            "Tu Escudo ante el cisne negro, el despido y la invalidez.",
            "El Coste de tu Ego y la Barrera de los 100.000 €.",
            "El Acelerador 10×10: cómo adelantar años tu libertad.",
            "Tus 12 capas psicofinancieras, una a una.",
            "Tu Constitución Financiera completa."], SIM_URL.rsplit("/",1)[0]))
    return seq

def hero_close(extras, tmp="/tmp/_leg_", depth="completo"):
    cmp=(extras or {}).get("compromiso") or {}
    reglas=[r for r in (cmp.get("reglas") or []) if r]
    n=3 if depth=="esencial" else 5
    reglas=reglas[:n]
    if len(reglas)<3: return None
    sub=("Tu versión completa, en El Libro Financiero." if depth=="esencial" else "Firmado por ti, para ti. — Adapta Family Office")
    return LD.constitucion(tmp+"99.svg",reglas,sub,accent=LD.GOLD)

def LD_fmt(n):
    try: return "{:,.0f} €".format(float(n)).replace(",",".")
    except: return "—"

# ============ Libro de Pareja (T3) ============
_FRIC = {
 "C6": ("Las apariencias y el estatus","Ciertas cosas (coche, marca, salir) importan y merecen pagarse","No entiendo gastar en aparentar; prefiero ese dinero ahorrado","una compra de imagen"),
 "C10":("Financiar o esperar","No me asusta financiar para tenerlo ya","La deuda me angustia; prefiero esperar y pagar con lo que tengo","decidir si financiar una compra grande"),
 "C3": ("El colchón y la seguridad","Necesito un colchón grande para dormir tranquilo","Con menos reserva me apaño; prefiero que el dinero trabaje","cuánto dejar parado por si acaso"),
 "C4": ("El día a día y los caprichos","Disfruto del ahora; los pequeños gastos mejoran la vida","Vigilo los gastos pequeños; suman más de lo que parece","los gastos pequeños del día a día"),
 "C2": ("Las metas a largo plazo","Vivo más el presente; el largo plazo me cuesta","Pienso mucho en el futuro y quiero planificarlo","hablar de objetivos a 10-20 años"),
 "C1": ("El peso emocional del dinero","El dinero me genera ansiedad y me cuesta hablarlo","Llevo el dinero con calma; no me quita el sueño","sentarse a revisar las cuentas"),
}
def friccion_zonas(pA,pB):
    c=[]
    for code,(tit,hi,lo,trig) in _FRIC.items():
        sa=(pA.get(code,{}) or {}).get("score",0); sb=(pB.get(code,{}) or {}).get("score",0)
        gap=abs(sa-sb)
        if gap<12: continue
        if sa>=sb: a_st,b_st=hi,lo
        else: a_st,b_st=lo,hi
        c.append((gap,tit,a_st,b_st,trig))
    c.sort(reverse=True)
    return [(t,a,b,tr) for (g,t,a,b,tr) in c[:3]]


def _carga_pct(perfil, propio=True):
    t=((perfil or {}).get("carga_familiar","") or "").lower()
    if "yo, bastante" in t or "yo bastante" in t: v=70
    elif "yo, algo" in t or "yo algo" in t: v=60
    elif "50" in t: v=50
    elif "pareja, algo" in t: v=40
    elif "pareja, bastante" in t: v=30
    else: v=None
    return v if propio else (100-v if v is not None else None)

def pareja_hero(nA,nB,cliA,dA,dB,pA,pB,hogar_num,fecha,tmp="/tmp/_lp_",perfilA=None,perfilB=None):
    seq=[]
    ref=("AFO-%s"%(str(abs(hash((cliA.get('email') or nA)+nB))%9999)).zfill(4))
    seq.append(LD.cover_pareja(tmp+"00.svg",nA,nB,fecha,ref=ref))
    seq.append(LD.divider(tmp+"01.svg","El Libro de Pareja",["La diferencia","callada"],
        "El dinero rara vez rompe por cuánto hay. Rompe por cómo lo vive cada uno — y no se habla. Aquí lo ponemos sobre la mesa.",
        tint=LD.GLOW, accent=LD.BLUE))
    zonas=friccion_zonas(pA,pB)
    if zonas:
        try: seq.append(LD.mapa_friccion(tmp+"02.svg",nA,nB,zonas))
        except Exception: pass
    # número de libertad conjunto
    if hogar_num and hogar_num>0:
        dn,du=_compact(hogar_num)
        seq.append(LD.bignum(tmp+"03.svg","Vuestro número de libertad","%s"%dn,du,"euros que os liberan a los dos",
            "Una sola meta",
            "Es el capital conjunto que sostiene la vida de los dos sin depender de ningún sueldo. Vuestro destino compartido, en una cifra.",
            ["Acordad este número juntos: media conversación, medio compromiso.",
             "Revisadlo cada seis meses, como un equipo que mira el mismo mapa."], accent=LD.GOLD))
    # esfuerzo vital (si tenemos gastos comunes + modelo de aportación)
    try:
        salA=_num(dA,"ingreso_mensual") or 0; salB=_num(dB,"ingreso_mensual") or 0
        _gc=[x for x in (_num(dA,"gastos_comunes"),_num(dB,"gastos_comunes")) if x]
        common=(sum(_gc)/len(_gc)) if _gc else None
        modelo=((perfilA or {}).get("aportacion_modelo") or (perfilB or {}).get("aportacion_modelo") or "")
        ml=modelo.lower()
        if common and salA>0 and salB>0 and "cuenta única" not in ml and "bolsa común" not in ml:
            if "proporcional" in ml:
                payA=common*salA/(salA+salB); payB=common-payA; etq="Proporcional"
            else:
                payA=payB=common/2.0; etq=("Mitad y mitad" if ("mitad" in ml or "50" in ml) else "Sin sistema claro")
            pctA=100*payA/salA; pctB=100*payB/salB
            capA=max(0,salA-payA); capB=max(0,salB-payB)
            _mas=nA if capA>=capB else nB; _menos=nB if _mas==nA else nA
            _capmax=max(capA,capB); _capmin=min(capA,capB)
            _ratio=(_capmax/_capmin) if _capmin>0 else 0
            _rtxt=((("%.1f"%_ratio).replace(".",",")+"×") if _ratio>=1.15 else "")
            if "proporcional" in ml:
                micro="Vuestro modelo proporcional iguala el %% de esfuerzo. Pero mirad la cifra de abajo: aun así, tras lo común a %s le quedan %s para ahorrar lo suyo y a %s %s. Quien más gana sigue pudiendo construir más patrimonio propio: conviene que el ahorro también se piense en equipo."%(_menos,_eu(_capmin),_mas,_eu(_capmax))
            else:
                hi=nA if pctA>=pctB else nB; lo=nB if hi==nA else nA
                micro="A %s le cuesta el %d%% de su sueldo y a %s el %d%%. Pero la grieta real está en la cifra de abajo: tras lo común, a %s le quedan %s para ahorrar lo suyo y a %s %s%s. Con el mismo hogar, el patrimonio personal de uno crece mucho más rápido. Esa es la dependencia que se construye en silencio."%(hi,round(max(pctA,pctB)),lo,round(min(pctA,pctB)),_menos,_eu(_capmin),_mas,_eu(_capmax),(" ("+_rtxt+" más)" if _rtxt else ""))
            # cruzar la capacidad de ahorro con el peso del hogar (lo hablado)
            _cA=_carga_pct(perfilA,True); _cB=_carga_pct(perfilB,False)
            _vals=[x for x in (_cA,_cB) if x is not None]
            if _vals:
                _hA=round(sum(_vals)/len(_vals)); _hB=100-_hA
                _mas_hogar=nA if _hA>_hB else nB; _h_de=lambda n:(_hA if n==nA else _hB)
                if abs(_hA-_hB)<=10:
                    micro+=" Y el hogar lo sostenéis casi a partes iguales: la única palanca que reequilibra es el ahorro."
                elif _mas_hogar==_menos:
                    micro+=" Y la grieta es doble: %s, que puede ahorrar menos, sostiene además el %d%% de la casa. Aporta más por el hogar y construye menos para sí; eso hay que reconocerlo y compensarlo en equipo."%(_menos,_h_de(_menos))
                else:
                    micro+=" Aun así, %s sostiene más hogar (%d%%), lo que en parte reequilibra: cada uno aporta una moneda distinta, y reconocerlo es el trabajo."%(_mas_hogar,_h_de(_mas_hogar))
            seq.append(LD.esfuerzo_vital(tmp+"02c.svg",nA,nB,pctA,pctB,etq,micro,capA=capA,capB=capB))
    except Exception:
        pass
    # balanza de las dos monedas (si tenemos carga familiar)
    try:
        salA=_num(dA,"ingreso_mensual") or 0; salB=_num(dB,"ingreso_mensual") or 0
        cargaA=_carga_pct(perfilA,True); cargaB=_carga_pct(perfilB,False)
        vals=[x for x in (cargaA,cargaB) if x is not None]
        if (salA+salB)>0 and vals:
            econA=round(100*salA/(salA+salB)); econB=100-econA
            hogarA=round(sum(vals)/len(vals)); hogarB=100-hogarA
            # veredicto honesto
            menos_dinero = nA if econA<econB else nB
            mas_hogar = nA if hogarA>hogarB else nB
            if menos_dinero==mas_hogar:
                verd="%s aporta menos dinero pero sostiene más hogar. Vuestro equipo está más equilibrado de lo que dicen las cuentas — pero solo si los dos lo reconocéis. El peligro: que uno mida en euros y el otro en horas, y ninguno vea la del otro."%menos_dinero
            elif hogarA==hogarB:
                verd="Repartís el hogar casi a partes iguales. La conversación pendiente es solo el dinero — y eso se negocia con números sobre la mesa."
            else:
                mas_ambas = nA if (econA>econB and hogarA>hogarB) else (nB if (econB>econA and hogarB>hogarA) else None)
                if mas_ambas:
                    verd="%s carga hoy con más dinero Y más hogar. Eso no es sostenible: es la antesala del agotamiento. Reequilibrad antes de que se convierta en reproche."%mas_ambas
                else:
                    verd="Cada uno sostiene una moneda distinta del hogar. Reconocer ambas, en voz alta, es la mitad del trabajo."
            seq.append(LD.balanza_aportacion(tmp+"02b.svg",nA,nB,econA,econB,hogarA,hogarB,verd))
    except Exception:
        pass
    # el pacto
    ingm=((_num(dA,"ingreso_mensual") or 0)+(_num(dB,"ingreso_mensual") or 0))
    umbral=max(500,round(ingm*0.15/100)*100) if ingm else 1000
    reglas=[
        "Tendremos una conversación de dinero al mes: solo números y planes, cero reproches.",
        "Cada uno tendrá su gasto libre intocable. Lo que el otro haga con él no se cuestiona.",
        "Las decisiones por encima de %s € las hablamos juntos, antes de decidir."%("{:,.0f}".format(umbral).replace(",",".")),
        "Reconocemos las dos monedas: quien aporta menos dinero puede sostener más hogar.",
        "Revisaremos nuestro número de libertad conjunto cada seis meses, como un equipo."]
    seq.append(LD.constitucion(tmp+"99.svg",reglas,"Firmado por %s y %s. Un equipo, un plan."%(nA,nB),accent=LD.GOLD,titulo="VUESTRA CONSTITUCIÓN",kicker="VUESTRO LIBRO FINANCIERO · EL CIERRE"))
    return seq
