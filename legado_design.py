# -*- coding: utf-8 -*-
"""Legado Financiero — generadores de páginas-imagen 'hero' (banca privada, navy + azul eléctrico)."""
import os, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams['svg.fonttype']='path'   # glifos como trazos vectoriales: nitidez total, sin depender de fuentes del visor
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyBboxPatch, Rectangle

_FD=os.path.join(os.path.dirname(os.path.abspath(__file__)),"fonts")
def _fp(f,sz): return FontProperties(fname=os.path.join(_FD,f),size=sz)
def L(sz):  return _fp("Lora-Bold.ttf",sz)        # serif display
def Lr(sz): return _fp("Lora-Regular.ttf",sz)
def Li(sz): return _fp("Lora-Italic.ttf",sz)
def P(sz):  return _fp("Poppins-Regular.ttf",sz)
def Pm(sz): return _fp("Poppins-Medium.ttf",sz)
def Pb(sz): return _fp("Poppins-Bold.ttf",sz)
def Pl(sz): return _fp("Poppins-Light.ttf",sz)

BG0="#0A0A0C"; BG1="#121215"; GLOW="#2A2410"
BLUE="#FDD731"; BLUE_L="#FFE36A"; WHITE="#F3F6FC"; MUTE="#9A958A"; FAINT="#6B655A"; RULE="#33312A"
GOLD="#E3B341"; GREEN="#3FB984"
A4=(8.27,11.69)  # portrait inches

def _bg(ax, glow_xy=(0.78,0.84), tint=GLOW):
    n=600
    yy,xx=np.mgrid[0:1:n*1j,0:1:n*1j]
    # vertical gradient BG0->BG1
    import matplotlib.colors as mc
    c0=np.array(mc.to_rgb(BG0)); c1=np.array(mc.to_rgb(BG1)); cg=np.array(mc.to_rgb(tint))
    base=c0[None,None,:]*(1-yy[...,None])+c1[None,None,:]*yy[...,None]
    d=np.sqrt((xx-glow_xy[0])**2+(yy-glow_xy[1])**2)
    halo=np.clip(1-d/0.55,0,1)**2.2
    img=base*(1-halo[...,None]*0.55)+cg[None,None,:]*halo[...,None]*0.55
    ax.imshow(np.clip(img,0,1),extent=[0,1,0,1],origin="lower",zorder=0,aspect="auto")

def _canvas():
    fig=plt.figure(figsize=A4,dpi=200); ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis("off")
    return fig,ax

def _emblem(ax,x,y,s=0.030):
    # marca Adapta: wordmark (sin triángulo placeholder)
    ax.text(x,y,"ADAPTA",ha="center",va="center",color=BLUE,fontproperties=Pb(16),transform=ax.transAxes,zorder=6)

def _spaced(t,n=3): return (" "*n).join(list(t))

def cover(out, cliente, fecha, tier_txt="Informe Avanzado · Tier II", ref="ITAP"):
    fig,ax=_canvas(); _bg(ax,(0.80,0.86))
    _emblem(ax,0.5,0.845)
    ax.text(0.5,0.78,_spaced("FAMILY  OFFICE",1),ha="center",va="center",color=MUTE,fontproperties=P(8.5),transform=ax.transAxes)
    ax.text(0.5,0.66,_spaced("TU LIBRO FINANCIERO"),ha="center",va="center",color=BLUE_L,fontproperties=Pm(10),transform=ax.transAxes)
    ax.text(0.5,0.575,"DIAGNÓSTICO",ha="center",va="center",color=WHITE,fontproperties=L(43),transform=ax.transAxes)
    ax.text(0.5,0.485,"PATRIMONIAL",ha="center",va="center",color=BLUE,fontproperties=L(43),transform=ax.transAxes)
    ax.plot([0.42,0.58],[0.43,0.43],color=BLUE,lw=1.6,transform=ax.transAxes)
    ax.text(0.5,0.385,_spaced("PASADO · PRESENTE · FUTURO",1),ha="center",va="center",color=MUTE,fontproperties=P(10.5),transform=ax.transAxes)
    ax.text(0.5,0.175,"Preparado en exclusiva para",ha="center",va="center",color=FAINT,fontproperties=P(9.5),transform=ax.transAxes)
    ax.text(0.5,0.14,cliente,ha="center",va="center",color=WHITE,fontproperties=L(17),transform=ax.transAxes)
    ax.text(0.5,0.075,_spaced("DOCUMENTO CONFIDENCIAL · %s · USO PRIVADO"%ref,0).replace("  "," "),ha="center",va="center",color=FAINT,fontproperties=P(7),transform=ax.transAxes)
    ax.text(0.5,0.05,fecha,ha="center",va="center",color=FAINT,fontproperties=P(7.5),transform=ax.transAxes)
    fig.savefig(out,dpi=130); plt.close(fig); return out

def divider(out, seccion, titulo_lines, subtitle, tint=GLOW, accent=BLUE):
    fig,ax=_canvas(); _bg(ax,(0.82,0.80),tint)
    ax.text(0.5,0.66,_spaced(seccion.upper()),ha="center",va="center",color=accent,fontproperties=Pm(12),transform=ax.transAxes)
    ys=0.55 if len(titulo_lines)>1 else 0.50
    for i,ln in enumerate(titulo_lines):
        ax.text(0.5,ys-i*0.085,ln.upper(),ha="center",va="center",color=WHITE,fontproperties=L(40),transform=ax.transAxes)
    ry=ys-len(titulo_lines)*0.085+0.02
    ax.plot([0.45,0.55],[ry,ry],color=accent,lw=1.4,transform=ax.transAxes)
    # subtitle (wrap)
    import textwrap
    wl=textwrap.wrap(subtitle,46)
    for i,ln in enumerate(wl):
        ax.text(0.5,ry-0.05-i*0.034,ln,ha="center",va="center",color=MUTE,fontproperties=P(11.5),transform=ax.transAxes)
    fig.savefig(out,dpi=130); plt.close(fig); return out

def bignum(out, titulo, numero, sufijo, caption, side_head, side_body, bullets, accent=BLUE):
    fig,ax=_canvas(); _bg(ax,(0.85,0.82))
    # título con barra vertical de acento (arriba-izq)
    ax.add_patch(Rectangle((0.085,0.85),0.006,0.055,color=accent,transform=ax.transAxes,zorder=5))
    ax.text(0.11,0.878,titulo.upper(),ha="left",va="center",color=WHITE,fontproperties=L(26),transform=ax.transAxes)
    # número gigante (izq) — medimos su ancho REAL para que el sufijo no se solape
    _tn=ax.text(0.10,0.46,numero,ha="left",va="center",color=WHITE,fontproperties=L(96),transform=ax.transAxes,zorder=5)
    fig.canvas.draw()
    try:
        _bb=_tn.get_window_extent(renderer=fig.canvas.get_renderer())
        _xr=ax.transAxes.inverted().transform((_bb.x1,_bb.y0))[0]
    except Exception:
        _xr=0.10+0.060*len(str(numero))
    if sufijo:
        ax.text(_xr+0.012,0.46,sufijo,ha="left",va="center",color=accent,fontproperties=L(96),transform=ax.transAxes,zorder=5)
    ax.text(0.11,0.345,_spaced(caption.upper(),1),ha="left",va="center",color=MUTE,fontproperties=P(10.5),transform=ax.transAxes)
    # columna derecha
    x=0.56
    ax.text(x,0.60,side_head,ha="left",va="top",color=accent,fontproperties=Pm(13),transform=ax.transAxes)
    import textwrap
    yy=0.55
    for ln in textwrap.wrap(side_body,40):
        ax.text(x,yy,ln,ha="left",va="top",color=MUTE,fontproperties=P(10.5),transform=ax.transAxes); yy-=0.032
    yy-=0.02
    for b in bullets:
        ax.text(x,yy,"•",ha="left",va="top",color=accent,fontproperties=Pb(11),transform=ax.transAxes)
        for j,ln in enumerate(textwrap.wrap(b,38)):
            ax.text(x+0.022,yy,ln,ha="left",va="top",color=WHITE if j==0 else MUTE,fontproperties=P(10),transform=ax.transAxes); yy-=0.030
        yy-=0.012
    fig.savefig(out,dpi=130); plt.close(fig); return out

if __name__=="__main__":
    O="/sessions/jolly-beautiful-cray/mnt/outputs/"
    cover(O+"d_cover.png","Javier Méndez","17 de junio de 2026",ref="AFO-X-00CBD")
    divider(O+"d_div1.png","Sección I",
            ["Arqueología del","Comportamiento"],
            "Las decisiones y creencias heredadas que construyeron, en silencio, tus cimientos de hoy.")
    bignum(O+"d_big.png","Tu número de libertad","1,21","M","euros de patrimonio que te liberan",
           "El objetivo de seguridad",
           "Es el capital que, al 4% de retiro prudente, genera tus 3.500 € de vida ideal sin que tengas que trabajar.",
           ["Escenario base: lo alcanzas en 9 años.","Con disciplina extra: en 6 años.","Hoy ya tienes el 74% del camino hecho."])
    print("OK demo pngs")

# ============ páginas-joya (maqueta vertical) ============
import textwrap as _tw
from matplotlib.patches import Wedge, Circle, FancyArrow

def _vbar(ax,x,y,title,accent=BLUE,sz=24):
    ax.add_patch(Rectangle((x,y),0.006,0.052,color=accent,transform=ax.transAxes,zorder=5))
    ax.text(x+0.022,y+0.027,title.upper(),ha="left",va="center",color=WHITE,fontproperties=L(sz),transform=ax.transAxes,zorder=6)

def efecto_espejo(out, kicker, frase, dato_num, dato_txt, cierre, accent=BLUE):
    fig,ax=_canvas(); _bg(ax,(0.82,0.85))
    ax.text(0.10,0.86,_spaced(kicker.upper()),ha="left",va="center",color=accent,fontproperties=Pm(11),transform=ax.transAxes)
    ax.text(0.10,0.78,"Dijiste",ha="left",va="center",color=MUTE,fontproperties=Pm(12),transform=ax.transAxes)
    yy=0.71
    for ln in _tw.wrap("«"+frase+"»",34):
        ax.text(0.10,yy,ln,ha="left",va="top",color=WHITE,fontproperties=Li(25),transform=ax.transAxes); yy-=0.052
    yy-=0.03
    ax.plot([0.10,0.34],[yy,yy],color=RULE,lw=1.2,transform=ax.transAxes); yy-=0.06
    ax.text(0.10,yy,"Tus datos dicen",ha="left",va="center",color=MUTE,fontproperties=Pm(12),transform=ax.transAxes); yy-=0.10
    ax.text(0.10,yy,dato_num,ha="left",va="center",color=accent,fontproperties=L(62),transform=ax.transAxes); yy-=0.085
    for ln in _tw.wrap(dato_txt,52):
        ax.text(0.10,yy,ln,ha="left",va="top",color=MUTE,fontproperties=P(11),transform=ax.transAxes); yy-=0.034
    ax.text(0.10,0.10,cierre,ha="left",va="center",color=WHITE,fontproperties=L(20),transform=ax.transAxes)
    fig.savefig(out,dpi=130); plt.close(fig); return out

def guion_dinero(out, arq_nombre, arq_lema, parrafos, cierre, accent=GOLD):
    """Raíz emocional del Pasado: el 'guion del dinero' derivado del arquetipo. Página editorial narrativa."""
    fig,ax=_canvas(); _bg(ax,(0.80,0.84),tint="#0E1622")
    ax.text(0.10,0.865,_spaced("TU GUION DEL DINERO"),ha="left",va="center",color=accent,fontproperties=Pm(11),transform=ax.transAxes)
    ax.text(0.10,0.775,(arq_nombre or "").upper(),ha="left",va="center",color=WHITE,fontproperties=L(38),transform=ax.transAxes)
    if arq_lema:
        ax.text(0.10,0.705,"«"+arq_lema+"»",ha="left",va="center",color=accent,fontproperties=Li(16),transform=ax.transAxes)
    ax.plot([0.10,0.28],[0.668,0.668],color=RULE,lw=1.2,transform=ax.transAxes)
    yy=0.61
    for par in parrafos:
        if not par: continue
        for ln in _tw.wrap(par,60):
            ax.text(0.10,yy,ln,ha="left",va="top",color=MUTE,fontproperties=P(11.5),transform=ax.transAxes); yy-=0.0345
        yy-=0.028
    ax.text(0.10,0.115,cierre,ha="left",va="center",color=WHITE,fontproperties=L(19),transform=ax.transAxes)
    fig.savefig(out,dpi=130); plt.close(fig); return out

def el_salto(out, arq_nombre, hoy, manana, cierre, accent=GOLD):
    """El salto: misma identidad, sin el punto ciego. HOY (apagado) -> EN 12 MESES (vivo)."""
    fig,ax=_canvas(); _bg(ax,(0.84,0.16),tint="#0E1622")
    ax.text(0.10,0.90,_spaced("EL SALTO"),ha="left",va="center",color=accent,fontproperties=Pm(11),transform=ax.transAxes)
    ax.text(0.10,0.825,"La misma raíz, sin el peaje.",ha="left",va="center",color=WHITE,fontproperties=L(32),transform=ax.transAxes)
    # ---- HOY (apagado) ----
    ax.text(0.10,0.715,_spaced("HOY"),ha="left",va="center",color=FAINT,fontproperties=Pm(11),transform=ax.transAxes)
    ax.text(0.105,0.675,(arq_nombre or "").upper(),ha="left",va="center",color=MUTE,fontproperties=Lr(15),transform=ax.transAxes)
    yy=0.625
    for ln in _tw.wrap(hoy,58):
        ax.text(0.10,yy,ln,ha="left",va="top",color="#67768F",fontproperties=P(11.5),transform=ax.transAxes); yy-=0.0345
    # ---- flecha de salto ----
    ax.plot([0.12,0.12],[0.47,0.40],color=accent,lw=2.2,transform=ax.transAxes,zorder=4)
    ax.fill([0.108,0.132,0.12],[0.402,0.402,0.382],color=accent,transform=ax.transAxes,zorder=4)
    # ---- EN 12 MESES (vivo) ----
    ax.text(0.10,0.345,_spaced("EN 12 MESES"),ha="left",va="center",color=accent,fontproperties=Pm(11),transform=ax.transAxes)
    ax.text(0.105,0.305,(arq_nombre or "").upper(),ha="left",va="center",color=WHITE,fontproperties=Lr(15),transform=ax.transAxes)
    yy=0.255
    for ln in _tw.wrap(manana,58):
        ax.text(0.10,yy,ln,ha="left",va="top",color="#D7DEEA",fontproperties=P(11.5),transform=ax.transAxes); yy-=0.0345
    ax.text(0.10,0.10,cierre,ha="left",va="center",color=WHITE,fontproperties=Li(18),transform=ax.transAxes)
    fig.savefig(out,dpi=130); plt.close(fig); return out

def termometro(out, titulo, indice, etiqueta, drivers, accent=BLUE):
    # indice 0..100 (vulnerabilidad). gauge semicircular verde->ambar->rojo
    fig,ax=_canvas(); _bg(ax,(0.84,0.84))
    _vbar(ax,0.085,0.85,titulo,accent,sz=18)
    cx,cy,Rr=0.39,0.50,0.25
    segs=[(180,180-0.4*180,GREEN),(180-0.4*180,180-0.7*180,GOLD),(180-0.7*180,0,"#D9534F")]
    for a0,a1,col in segs:
        ax.add_patch(Wedge((cx,cy),Rr,a1,a0,width=0.052,facecolor=col,edgecolor="none",transform=ax.transAxes,zorder=4))
    # aguja
    ang=np.radians(180-indice/100*180)
    ax.plot([cx,cx+ (Rr-0.02)*np.cos(ang)],[cy,cy+(Rr-0.02)*np.sin(ang)*A4[0]/A4[1]],
            color=WHITE,lw=2.4,transform=ax.transAxes,zorder=6,solid_capstyle="round")
    ax.add_patch(Circle((cx,cy),0.012,color=WHITE,transform=ax.transAxes,zorder=7))
    ax.text(cx,cy-0.10,str(int(indice)),ha="center",va="center",color=WHITE,fontproperties=L(50),transform=ax.transAxes)
    ax.text(cx,cy-0.165,_spaced(etiqueta.upper(),1),ha="center",va="center",color=accent,fontproperties=Pm(10),transform=ax.transAxes)
    ax.text(cx,cy-0.215,"0 = BLINDADO   ·   100 = EXPUESTO",ha="center",va="center",color=MUTE,fontproperties=P(7.5),transform=ax.transAxes)
    ax.text(cx,cy+Rr+0.03,"ÍNDICE DE VULNERABILIDAD",ha="center",va="center",color=MUTE,fontproperties=P(9.5),transform=ax.transAxes)
    # drivers columna derecha
    x=0.70; yy=0.62
    ax.text(x,yy+0.06,"Qué lo mueve",ha="left",va="center",color=accent,fontproperties=Pm(12),transform=ax.transAxes)
    ax.text(x,yy+0.028,"barra llena = factor sano",ha="left",va="center",color=MUTE,fontproperties=Li(8.5),transform=ax.transAxes)
    for nombre,val,estado in drivers:  # val 0..1, estado color
        ax.text(x,yy,nombre,ha="left",va="center",color=WHITE,fontproperties=P(10),transform=ax.transAxes)
        ax.add_patch(Rectangle((x,yy-0.028),0.22,0.012,color="#1E2C46",transform=ax.transAxes))
        ax.add_patch(Rectangle((x,yy-0.028),0.22*val,0.012,color=estado,transform=ax.transAxes))
        yy-=0.085
    import textwrap as _tw2
    _expv="Mide cuánto te afectaría un imprevisto —un paro, un gasto grande—. Cuanto más alto el número, más expuesto estás; cuanto más bajo, más blindado."
    _ey=0.155
    for _ln in _tw2.wrap(_expv,90):
        ax.text(0.085,_ey,_ln,ha="left",va="top",color=MUTE,fontproperties=P(9),transform=ax.transAxes); _ey-=0.028
    fig.savefig(out,dpi=130); plt.close(fig); return out

def constitucion(out, reglas, subtit, accent=GOLD):
    fig,ax=_canvas(); _bg(ax,(0.80,0.82),tint="#14202E")
    ax.text(0.5,0.88,_spaced("TU LIBRO FINANCIERO · EL CIERRE"),ha="center",va="center",color=MUTE,fontproperties=P(9),transform=ax.transAxes)
    ax.text(0.5,0.80,"TU CONSTITUCIÓN",ha="center",va="center",color=WHITE,fontproperties=L(34),transform=ax.transAxes)
    ax.text(0.5,0.735,"FINANCIERA",ha="center",va="center",color=accent,fontproperties=L(34),transform=ax.transAxes)
    ax.plot([0.45,0.55],[0.70,0.70],color=accent,lw=1.3,transform=ax.transAxes)
    yy=0.63
    for i,r in enumerate(reglas,1):
        ax.text(0.13,yy,"%02d"%i,ha="left",va="top",color=accent,fontproperties=L(22),transform=ax.transAxes)
        for j,ln in enumerate(_tw.wrap(r,58)):
            ax.text(0.20,yy-j*0.030,ln,ha="left",va="top",color=WHITE if j==0 else MUTE,fontproperties=(Lr(12.5) if j==0 else P(10.5)),transform=ax.transAxes)
        yy-=0.030*(len(_tw.wrap(r,58)))+0.028
    ax.text(0.5,0.06,subtit,ha="center",va="center",color=FAINT,fontproperties=Li(11),transform=ax.transAxes)
    fig.savefig(out,dpi=130); plt.close(fig); return out

# ============ joyas adicionales ============
def matriz_tiempo(out, pct_pasivo, ing_activo, ing_pasivo, accent=BLUE):
    """¿Trabajas tú o trabaja tu dinero? Barra activo (sangre) vs pasivo (libre)."""
    fig,ax=_canvas(); _bg(ax,(0.84,0.84))
    _vbar(ax,0.085,0.85,"¿Trabajas tú, o trabaja tu dinero?",accent,sz=17)
    ax.text(0.10,0.715,"De cada euro que ganas hoy: cuánto exige tu tiempo (rojo) y cuánto trabaja sin ti (oro).",ha="left",va="center",color=MUTE,fontproperties=P(9.5),transform=ax.transAxes)
    pp=max(0.0,min(1.0,pct_pasivo)); pa=1-pp
    x0,w,y,h=0.10,0.80,0.52,0.075
    ax.add_patch(Rectangle((x0,y),w*pa,h,color="#C65C4E",transform=ax.transAxes,zorder=4))
    ax.add_patch(Rectangle((x0+w*pa,y),w*pp,h,color=GOLD,transform=ax.transAxes,zorder=4))
    # etiquetas grandes
    ax.text(x0,y+0.13,"%d%%"%round(pa*100),ha="left",va="center",color="#E2796B",fontproperties=L(40),transform=ax.transAxes)
    ax.text(x0+w,y+0.13,"%d%%"%round(pp*100),ha="right",va="center",color=GOLD,fontproperties=L(40),transform=ax.transAxes)
    ax.text(x0,y-0.04,"DEPENDE DE TU ESFUERZO",ha="left",va="top",color=MUTE,fontproperties=P(9.5),transform=ax.transAxes)
    ax.text(x0+w,y-0.04,"TRABAJA SIN TI",ha="right",va="top",color=MUTE,fontproperties=P(9.5),transform=ax.transAxes)
    # interpretación
    import textwrap
    if pp<0.05:
        txt="Hoy, prácticamente cada euro que entra lo cambias por tu tiempo: es sangre, sudor y horas. Nada trabaja por ti todavía. Esa es, exactamente, la palanca que cambia una vida: convertir parte de ese esfuerzo en activos que generen renta mientras duermes."
    elif pp<0.4:
        txt="Has empezado a construir ingresos que no dependen de tu tiempo, pero el grueso sigue siendo esfuerzo directo. Cada punto que muevas de rojo a oro es una hora de tu vida que recuperas."
    else:
        txt="Una parte importante de tu dinero ya trabaja sin ti. Estás cerca del punto en que tu tiempo deja de ser la fuente y pasa a ser la elección. Protégelo y amplíalo."
    yy=0.40
    for ln in textwrap.wrap(txt,72):
        ax.text(0.10,yy,ln,ha="left",va="top",color=WHITE if yy>0.37 else MUTE,fontproperties=P(11),transform=ax.transAxes); yy-=0.036
    # Tesis incómoda: la razón de fondo por la que esta página existe
    ax.plot([0.10,0.17],[0.265,0.265],color=accent,lw=1.4,transform=ax.transAxes)
    ax.text(0.10,0.225,"Nadie ha logrado nada grande dependiendo solo de su esfuerzo.",ha="left",va="center",color=WHITE,fontproperties=Lr(12.5),transform=ax.transAxes)
    ax.text(0.10,0.185,"La libertad empieza cuando tu dinero trabaja sin ti.",ha="left",va="center",color=accent,fontproperties=Lr(12.5),transform=ax.transAxes)
    ax.text(0.10,0.10,"Donde tu dinero pierde el tiempo.",ha="left",va="center",color=accent,fontproperties=Li(15),transform=ax.transAxes)
    fig.savefig(out,dpi=130); plt.close(fig); return out

def mapa_100(out, hitos, accent=GOLD):
    """Tu mapa de escape: los próximos 100 días. hitos=[(dia,titulo,detalle),...]"""
    fig,ax=_canvas(); _bg(ax,(0.82,0.82),tint="#13202A")
    _vbar(ax,0.085,0.85,"Tu mapa de escape",accent,sz=22)
    ax.text(0.107,0.79,_spaced("LOS PRÓXIMOS 100 DÍAS",1),ha="left",va="center",color=MUTE,fontproperties=P(9.5),transform=ax.transAxes)
    import textwrap
    xline=0.16; ytop=0.66; ybot=0.20
    ax.plot([xline,xline],[ybot,ytop],color="#33425E",lw=2,transform=ax.transAxes,zorder=3)
    n=len(hitos)
    for i,(dia,titulo,det) in enumerate(hitos):
        y=ytop-(ytop-ybot)*(i/(max(1,n-1)))
        ax.add_patch(Circle((xline,y),0.013,color=accent,transform=ax.transAxes,zorder=5))
        ax.text(xline-0.02,y,dia,ha="right",va="center",color=accent,fontproperties=L(15),transform=ax.transAxes)
        _tl=textwrap.wrap(titulo,46)[:2]
        for k,_tln in enumerate(_tl):
            ax.text(xline+0.04,y+0.026-k*0.030,_tln,ha="left",va="top",color=WHITE,fontproperties=Lr(13.5),transform=ax.transAxes)
        _dy=y+0.026-len(_tl)*0.030-0.006
        for j,ln in enumerate(textwrap.wrap(det,58)):
            ax.text(xline+0.04,_dy-j*0.026,ln,ha="left",va="top",color=MUTE,fontproperties=P(10),transform=ax.transAxes)
    ax.text(0.10,0.10,"No es una lista de deseos. Son tres movimientos con fecha.",ha="left",va="center",color=accent,fontproperties=Li(14),transform=ax.transAxes)
    fig.savefig(out,dpi=130); plt.close(fig); return out

def qr_golden(out, url, titulo, sub, accent=GOLD):
    """Golden Ticket: QR al simulador, sobre panel claro para escaneo."""
    import qrcode
    qr=qrcode.QRCode(border=1,box_size=10,error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url); qr.make(fit=True)
    img=qr.make_image(fill_color="#0B1A39",back_color="#F3F0E6").convert("RGB")
    qpath=out.replace(".png","_qr.png"); img.save(qpath)
    fig,ax=_canvas(); _bg(ax,(0.84,0.20),tint="#16202E")
    ax.text(0.5,0.82,_spaced("ACCESO EXCLUSIVO",2),ha="center",va="center",color=accent,fontproperties=Pm(11),transform=ax.transAxes)
    ax.text(0.5,0.73,titulo,ha="center",va="center",color=WHITE,fontproperties=L(30),transform=ax.transAxes)
    # panel claro con QR
    from matplotlib.patches import FancyBboxPatch
    ax.add_patch(FancyBboxPatch((0.37,0.36),0.26,0.26,boxstyle="round,pad=0.012,rounding_size=0.02",
                 facecolor="#F3F0E6",edgecolor=accent,lw=1.2,transform=ax.transAxes,zorder=4))
    ax.imshow(np.asarray(img),extent=[0.385,0.615,0.375,0.605],transform=ax.transAxes,zorder=5,aspect="auto")
    import textwrap
    yy=0.28
    for ln in textwrap.wrap(sub,60):
        ax.text(0.5,yy,ln,ha="center",va="top",color=MUTE,fontproperties=P(10.5),transform=ax.transAxes); yy-=0.034
    ax.text(0.5,0.08,_spaced("ADAPTA FAMILY OFFICE",1),ha="center",va="center",color=FAINT,fontproperties=P(8),transform=ax.transAxes)
    fig.savefig(out,dpi=130); plt.close(fig); return out

def sistema_scorecard(out, items, weakest, accent=BLUE):
    """Scorecard del método S.I.S.T.E.M.A. items=[(letra,nombre,health|None,status),...]; weakest=idx."""
    fig,ax=_canvas(); _bg(ax,(0.84,0.84))
    _vbar(ax,0.085,0.88,"Tu S.I.S.T.E.M.A.",accent,sz=24)
    ax.text(0.107,0.825,_spaced("LOS 7 PASOS DEL MÉTODO ADAPTA, MEDIDOS EN TI",0).replace("  "," "),
            ha="left",va="center",color=MUTE,fontproperties=P(9),transform=ax.transAxes)
    x0=0.10; ytop=0.74; row=0.092
    barx=0.40; barw=0.34
    def hc(h): return "#3FB984" if h>=67 else ("#E3B341" if h>=34 else "#D9534F")
    for i,(letra,nombre,health,status) in enumerate(items):
        y=ytop-i*row
        ax.text(x0,y,letra,ha="left",va="center",color=accent,fontproperties=L(30),transform=ax.transAxes)
        ax.text(x0+0.075,y+0.012,nombre,ha="left",va="center",color=WHITE,fontproperties=Lr(13.5),transform=ax.transAxes)
        if health is None:
            # capa que se revisa en tu sesion (no la puntua el test): etiqueta intencional, nunca barra vacia
            ax.add_patch(Rectangle((barx,y-0.013),barw,0.026,facecolor=accent,alpha=0.12,edgecolor=accent,lw=0.7,transform=ax.transAxes,zorder=3))
            ax.text(barx+barw/2.0,y,"Revisión personalizada",ha="center",va="center",color=accent,fontproperties=Pm(8.5),transform=ax.transAxes,zorder=4)
            ax.text(barx+barw+0.03,y,status,ha="left",va="center",color=accent,fontproperties=P(9),transform=ax.transAxes)
        else:
            ax.add_patch(Rectangle((barx,y-0.006),barw,0.010,color="#1E2C46",transform=ax.transAxes,zorder=3))
            ax.add_patch(Rectangle((barx,y-0.006),barw*max(.04,health/100.0),0.010,color=hc(health),transform=ax.transAxes,zorder=4))
            ax.text(barx+barw+0.03,y,status,ha="left",va="center",color=hc(health),fontproperties=Pm(9.5),transform=ax.transAxes)
        ax.text(x0+0.075,y-0.018,_SIS_SUB[i],ha="left",va="center",color=FAINT,fontproperties=P(8.5),transform=ax.transAxes)
        if i==weakest:
            ax.text(barx+barw+0.03,y-0.020,"← tu eslabón más débil",ha="left",va="center",color="#D9534F",fontproperties=Li(9),transform=ax.transAxes)
    ax.text(0.10,0.075,"Una cadena se rompe por su eslabón más débil. Ahí empieza tu plan.",
            ha="left",va="center",color=accent,fontproperties=Li(13),transform=ax.transAxes)
    fig.savefig(out,dpi=130); plt.close(fig); return out

_SIS_SUB=["Limpiar deuda cara y fugas","Cuántas fuentes te sostienen","Proteger el suelo antes de optimizar",
          "La capa fiscal de cada decisión","Asignar el excedente, no dejarlo parado","Revisar, reequilibrar, repensar",
          "Tener con quién pensar"]

# ============ joyas 0,001% ============
RED="#C9514049"; SANGRE="#C0473B"
def blood_money(out, eur_hora, coste_items, mensaje, accent="#C0473B"):
    """€/hora real vs coste de salud. coste_items=[(etiqueta,sev 0..1),...]"""
    fig,ax=_canvas(); _bg(ax,(0.84,0.84),tint="#231019")
    _vbar(ax,0.085,0.86,"El precio real de tu hora",accent,sz=22)
    ax.text(0.10,0.70,"Te pagan",ha="left",va="center",color=MUTE,fontproperties=P(12),transform=ax.transAxes)
    ax.text(0.10,0.59,"%d"%round(eur_hora),ha="left",va="center",color=WHITE,fontproperties=L(78),transform=ax.transAxes)
    ax.text(0.10+0.030+0.060*len(str(round(eur_hora))),0.585,"€/hora",ha="left",va="center",color=accent,fontproperties=L(30),transform=ax.transAxes)
    ax.text(0.10,0.47,"…pero esa hora te cuesta:",ha="left",va="center",color=MUTE,fontproperties=Pm(12),transform=ax.transAxes)
    yy=0.40; barx=0.10; barw=0.46
    for et,sev in coste_items:
        col="#3FB984" if sev<0.34 else ("#E3B341" if sev<0.67 else accent)
        ax.text(barx,yy+0.018,et,ha="left",va="center",color=WHITE,fontproperties=P(10.5),transform=ax.transAxes)
        ax.add_patch(Rectangle((barx,yy-0.006),barw,0.010,color="#2A1C22",transform=ax.transAxes,zorder=3))
        ax.add_patch(Rectangle((barx,yy-0.006),barw*max(.05,sev),0.010,color=col,transform=ax.transAxes,zorder=4))
        yy-=0.072
    import textwrap; yy-=0.01
    for ln in textwrap.wrap(mensaje,74):
        ax.text(0.10,yy,ln,ha="left",va="top",color=MUTE,fontproperties=P(10.5),transform=ax.transAxes); yy-=0.034
    ax.text(0.10,0.075,"Cambias salud por un capital que luego gastas en recuperar la salud.",
            ha="left",va="center",color=accent,fontproperties=Li(13),transform=ax.transAxes)
    fig.savefig(out,dpi=130); plt.close(fig); return out

def escudo(out, escenarios, accent=BLUE):
    """escenarios=[(nombre,detalle,salud 0..1),...] 3 elementos. Escudo dividido en bandas."""
    fig,ax=_canvas(); _bg(ax,(0.84,0.82))
    _vbar(ax,0.085,0.88,"Tu escudo financiero",accent,sz=22)
    ax.text(0.107,0.825,_spaced("TRES GOLPES QUE LA VIDA PUEDE DAR, Y CÓMO RESISTES",0).replace("  "," "),
            ha="left",va="center",color=MUTE,fontproperties=P(8.5),transform=ax.transAxes)
    def col(s): return "#3FB984" if s>=0.6 else ("#E3B341" if s>=0.34 else "#C0473B")
    cx=0.27; top=0.70; w=0.17
    # bandas del escudo (de arriba a abajo): 2 trapecios + triángulo punta
    bands=[(top,top-0.13),(top-0.13,top-0.26)]
    tip_y=top-0.26
    for i,(y0,y1) in enumerate(bands):
        s=escenarios[i][2]; c=col(s)
        ax.add_patch(plt.Polygon([(cx-w,y0),(cx+w,y0),(cx+w,y1),(cx-w,y1)],closed=True,
                     facecolor=c,edgecolor="#0A1220",lw=1.2,transform=ax.transAxes,zorder=4))
    s3=escenarios[2][2]; c3=col(s3)
    ax.add_patch(plt.Polygon([(cx-w,tip_y),(cx+w,tip_y),(cx,tip_y-0.16)],closed=True,
                 facecolor=c3,edgecolor="#0A1220",lw=1.2,transform=ax.transAxes,zorder=4))
    # contorno escudo
    ax.add_patch(plt.Polygon([(cx-w,top),(cx+w,top),(cx+w,tip_y),(cx,tip_y-0.16),(cx-w,tip_y)],
                 closed=True,fill=False,edgecolor=GOLD,lw=1.6,transform=ax.transAxes,zorder=6))
    # etiquetas a la derecha
    import textwrap
    lx=0.52; ys=[0.635,0.50,0.365]
    for i,(nombre,det,s) in enumerate(escenarios):
        c=col(s)
        ax.add_patch(Circle((lx-0.03,ys[i]+0.008),0.009,color=c,transform=ax.transAxes,zorder=5))
        ax.text(lx,ys[i]+0.02,nombre,ha="left",va="center",color=WHITE,fontproperties=Lr(13),transform=ax.transAxes)
        for j,ln in enumerate(textwrap.wrap(det,46)):
            ax.text(lx,ys[i]-0.008-j*0.026,ln,ha="left",va="top",color=MUTE,fontproperties=P(9.3),transform=ax.transAxes)
    ax.text(0.10,0.085,"Un escudo no se forja en la tormenta. Se forja antes.",
            ha="left",va="center",color=accent,fontproperties=Li(13),transform=ax.transAxes)
    fig.savefig(out,dpi=130); plt.close(fig); return out

def coste_ego(out, gasto_mes, anos, capital, n_anos=25, accent=GOLD):
    fig,ax=_canvas(); _bg(ax,(0.84,0.82),tint="#1A1726")
    _vbar(ax,0.085,0.86,"El precio que pagas por parecer rico",accent,sz=19)
    ax.text(0.10,0.62,"Ese gasto de imagen te roba",ha="left",va="center",color=MUTE,fontproperties=P(12),transform=ax.transAxes)
    txt=("%.1f"%anos).replace(".",",")
    ax.text(0.10,0.50,txt,ha="left",va="center",color=accent,fontproperties=L(86),transform=ax.transAxes)
    ax.text(0.12+0.066*len(txt)+0.02,0.495,"AÑOS",ha="left",va="center",color=WHITE,fontproperties=L(30),transform=ax.transAxes)
    ax.text(0.10,0.40,_spaced("DE LIBERTAD, ADELANTADOS",1),ha="left",va="center",color=MUTE,fontproperties=P(10),transform=ax.transAxes)
    import textwrap
    msg=("Gastas %s €/mes en sostener una imagen. Invertido al 7%% hasta tu jubilación (unos %d años), ese mismo "
         "dinero sumaría unos %s y adelantaría tu libertad %s años. Ese coche, esa marca, esa mesa del mejor "
         "restaurante: su precio real no es lo que pagaste, son los años de tu vida que cuestan.") % (
         "{:,.0f}".format(gasto_mes).replace(",","."), int(n_anos), "{:,.0f} €".format(capital).replace(",","."), txt)
    yy=0.30
    for ln in textwrap.wrap(msg,74):
        ax.text(0.10,yy,ln,ha="left",va="top",color=MUTE,fontproperties=P(10.5),transform=ax.transAxes); yy-=0.034
    ax.text(0.10,0.085,"No pagas por el objeto. Pagas por los años.",ha="left",va="center",color=accent,fontproperties=Li(13),transform=ax.transAxes)
    fig.savefig(out,dpi=130); plt.close(fig); return out

def arrepentimiento(out, findes, edad_hijo, accent=GOLD):
    fig,ax=_canvas(); _bg(ax,(0.82,0.80),tint="#14202A")
    _vbar(ax,0.085,0.87,"Lo que el dinero no te devuelve",accent,sz=20)
    ax.text(0.10,0.70,"Te quedan, aproximadamente,",ha="left",va="center",color=MUTE,fontproperties=P(12),transform=ax.transAxes)
    ax.text(0.10,0.575,"{:,}".format(findes).replace(",","."),ha="left",va="center",color=accent,fontproperties=L(86),transform=ax.transAxes)
    ax.text(0.10,0.475,_spaced("FINES DE SEMANA DE SU INFANCIA",1),ha="left",va="center",color=WHITE,fontproperties=P(11),transform=ax.transAxes)
    # puntos: findes restantes vs vividos (hasta 18*52)
    total=18*52; viv=max(0,total-findes)
    import numpy as _np
    cols=14; rows=12; n=cols*rows
    for k in range(n):
        rx=0.10+(k%cols)*0.018; ry=0.38-(k//cols)*0.020
        frac=k/n
        c=accent if frac>=viv/total else "#2A3850"
        ax.add_patch(Circle((rx,ry),0.004,color=c,transform=ax.transAxes,zorder=4))
    import textwrap
    msg=("Tu hijo tiene %d años. Cada fin de semana que cambias por una hora más de trabajo para pagar algo más grande, no vuelve. El patrimonio se reconstruye; estos sábados, no.") % edad_hijo
    yy=0.37
    for ln in textwrap.wrap(msg,30):
        ax.text(0.55,yy,ln,ha="left",va="top",color=MUTE,fontproperties=P(10.5),transform=ax.transAxes); yy-=0.036
    ax.text(0.10,0.085,"Tu libertad financiera no es para ti: es para estar.",ha="left",va="center",color=accent,fontproperties=Li(13),transform=ax.transAxes)
    fig.savefig(out,dpi=130); plt.close(fig); return out

def acelerador_10x10(out, cilindros, anos_delta, enemy_nombre, enemy_motivo, accent=GOLD):
    """4 cilindros (panel de control) + payoff en años. cilindros=[(nombre,actual,objetivo,signo),...]"""
    fig,ax=_canvas(); _bg(ax,(0.84,0.20),tint="#13202A")
    _vbar(ax,0.085,0.90,"El Acelerador 10×10",accent,sz=23)
    ax.text(0.107,0.85,"Cuatro ajustes del 10% que no se suman: se multiplican.",
            ha="left",va="center",color=MUTE,fontproperties=Li(12),transform=ax.transAxes)
    # 4 cilindros
    xs=[0.16,0.37,0.58,0.79]; cy0=0.50; cy1=0.74; w=0.052
    for i,(nombre,actual,objetivo,signo) in enumerate(cilindros):
        x=xs[i]
        ax.text(x,0.80,nombre.upper(),ha="center",va="center",color=WHITE,fontproperties=Pm(9.5),transform=ax.transAxes)
        ax.text(x,0.768,signo,ha="center",va="center",color=accent,fontproperties=Pm(9),transform=ax.transAxes)
        ax.add_patch(FancyBboxPatch((x-w,cy0),2*w,cy1-cy0,boxstyle="round,pad=0.002,rounding_size=0.014",
                     facecolor="#0E1C30",edgecolor="#2C3E5C",lw=1.2,transform=ax.transAxes,zorder=3))
        fillh=(cy1-cy0)*0.45
        ax.add_patch(Rectangle((x-w+0.004,cy0+0.004),2*w-0.008,fillh,color=BLUE,alpha=0.55,transform=ax.transAxes,zorder=4))
        ax.plot([x-w,x+w],[cy0+(cy1-cy0)*0.82]*2,color=accent,lw=2,transform=ax.transAxes,zorder=5)
        ax.text(x,cy0-0.035,actual,ha="center",va="center",color=MUTE,fontproperties=P(9),transform=ax.transAxes)
        ax.fill([x-0.008,x+0.008,x],[cy0-0.058,cy0-0.058,cy0-0.072],color=accent,transform=ax.transAxes,zorder=5)
        ax.text(x,cy0-0.098,objetivo,ha="center",va="center",color=WHITE,fontproperties=Pm(10),transform=ax.transAxes)
    # payoff
    ax.text(0.5,0.30,"Resultado: tu libertad llega",ha="center",va="center",color=MUTE,fontproperties=P(12),transform=ax.transAxes)
    txt=("%.0f"%anos_delta) if anos_delta==int(anos_delta) else ("%.1f"%anos_delta).replace(".",",")
    ax.text(0.5,0.205,txt+" años antes",ha="center",va="center",color=accent,fontproperties=L(46),transform=ax.transAxes)
    import textwrap
    cap="Tu cilindro más difícil será %s: %s. Ahí es donde se gana o se pierde la fórmula."%(enemy_nombre,enemy_motivo)
    yy=0.115
    for ln in textwrap.wrap(cap,86):
        ax.text(0.5,yy,ln,ha="center",va="top",color=MUTE,fontproperties=P(9.5),transform=ax.transAxes); yy-=0.028
    ax.text(0.5,0.04,"Objetivo de rentabilidad ilustrativo; no es una garantía.",ha="center",va="center",color=FAINT,fontproperties=P(7.5),transform=ax.transAxes)
    fig.savefig(out,dpi=130); plt.close(fig); return out

def barrera_100k(out, p0, aho_m, r, valle_caption, accent=GOLD):
    """El gráfico de la inflexión cruzada: aportaciones (esfuerzo) vs interés (tu dinero)."""
    import numpy as _np
    aho_y=aho_m*12.0; rr=r/100.0
    YRS=25
    aport=[]; total=[]; w=p0; ac=p0
    for t in range(YRS+1):
        aport.append(ac); total.append(w)
        w=w*(1+rr)+aho_y; ac=ac+aho_y
    aport=_np.array(aport); total=_np.array(total); interes=_np.clip(total-aport,0,None)
    # punto de inflexión: interés anual > aportación anual  => patrimonio = aho_y/rr
    infl=aho_y/rr if rr>0 else None
    # año en que se alcanza 100k
    y100=next((t for t in range(YRS+1) if total[t]>=100000),None)
    fig=plt.figure(figsize=A4,dpi=200); axm=fig.add_axes([0,0,1,1]); axm.set_xlim(0,1); axm.set_ylim(0,1); axm.axis("off")
    _bg(axm,(0.84,0.20),tint="#13202A")
    _vbar(axm,0.085,0.90,"El nacimiento de tu empleado invisible",accent,sz=18)
    axm.text(0.107,0.85,_spaced("LA BARRERA DE LOS 100.000 €",1),ha="left",va="center",color=MUTE,fontproperties=P(9),transform=axm.transAxes)
    # eje del gráfico
    ax=fig.add_axes([0.11,0.30,0.80,0.45]); ax.set_facecolor("none")
    yrs=_np.arange(YRS+1)
    ax.fill_between(yrs,0,aport,color="#2E6BFF",alpha=0.45,zorder=3,label="Tu esfuerzo (lo que aportas)")
    ax.fill_between(yrs,aport,total,color=accent,alpha=0.55,zorder=4,label="El esfuerzo de tu dinero (interés)")
    ax.plot(yrs,total,color="#FFFFFF",lw=1.4,zorder=5)
    ax.axhline(100000,color=accent,lw=1,ls=(0,(4,3)),zorder=6)
    ax.text(YRS*0.02,104000,"100.000 €",color=accent,fontproperties=P(8.5))
    if y100 is not None:
        ax.scatter([y100],[total[y100]],s=42,color="#FFFFFF",zorder=8)
    for sp in ax.spines.values(): sp.set_color("#2A3A5C")
    ax.tick_params(colors="#7A8AA8",labelsize=7.5)
    ax.set_xlabel("años",color="#7A8AA8",fontsize=8); ax.set_xlim(0,YRS)
    ax.set_ylim(0,max(total)*1.05)
    import matplotlib.ticker as _mt
    ax.yaxis.set_major_formatter(_mt.FuncFormatter(lambda v,_: ("%dk"%(v/1000)) if v>=1000 else "0"))
    # leyenda manual
    axm.add_patch(Rectangle((0.12,0.245),0.018,0.010,color="#2E6BFF",alpha=0.7,transform=axm.transAxes))
    axm.text(0.145,0.25,"Tu esfuerzo (lo que aportas de tu bolsillo)",ha="left",va="center",color=MUTE,fontproperties=P(8.5),transform=axm.transAxes)
    axm.add_patch(Rectangle((0.55,0.245),0.018,0.010,color=accent,alpha=0.8,transform=axm.transAxes))
    axm.text(0.575,0.25,"El esfuerzo de tu dinero (interés compuesto)",ha="left",va="center",color=MUTE,fontproperties=P(8.5),transform=axm.transAxes)
    # headline
    if p0>=100000:
        head="Tu reactor ya está encendido."
    elif y100 is not None:
        head="Enciendes tu reactor en %d años." % y100
    else:
        head="Tu primer objetivo: los 100.000 €."
    axm.text(0.11,0.185,head,ha="left",va="center",color=WHITE,fontproperties=L(24),transform=axm.transAxes)
    import textwrap
    sub=""
    if infl:
        sub="Tu punto de inflexión real está en %s: a partir de ahí, tu dinero gana más cada año de lo que tú ahorras. " % ("{:,.0f} €".format(infl).replace(",","."))
    yy=0.14
    for ln in textwrap.wrap(sub+valle_caption,96):
        axm.text(0.11,yy,ln,ha="left",va="top",color=MUTE,fontproperties=P(9.3),transform=axm.transAxes); yy-=0.027
    axm.text(0.11,0.045,"Asume una cartera diversificada a ~%d%% anual. Ilustrativo, no garantizado."%round(r),
             ha="left",va="center",color=FAINT,fontproperties=P(7.5),transform=axm.transAxes)
    fig.savefig(out,dpi=130); plt.close(fig); return out

def mapa_friccion(out, nA, nB, zonas, accent=BLUE):
    """Zonas €-exactas de conflicto de la pareja. zonas=[(titulo,a_stance,b_stance,trigger),...]"""
    fig,ax=_canvas(); _bg(ax,(0.84,0.84))
    _vbar(ax,0.085,0.90,"Vuestro Mapa de Fricción",accent,sz=21)
    ax.text(0.107,0.85,"Las zonas exactas donde el dinero os enfrenta — y el momento en que salta.",
            ha="left",va="center",color=MUTE,fontproperties=Li(11.5),transform=ax.transAxes)
    cA="#3D7DFF"; cB="#E3B341"
    # cabecera nombres
    ax.text(0.27,0.795,nA.upper(),ha="center",va="center",color=cA,fontproperties=Pm(10),transform=ax.transAxes)
    ax.text(0.73,0.795,nB.upper(),ha="center",va="center",color=cB,fontproperties=Pm(10),transform=ax.transAxes)
    import textwrap
    top=0.74; h=0.205
    for i,(tit,a,b,trig) in enumerate(zonas[:3]):
        y=top-i*h
        ax.add_patch(FancyBboxPatch((0.09,y-h+0.03),0.82,h-0.04,boxstyle="round,pad=0.004,rounding_size=0.012",
                     facecolor="#0E1A2E",edgecolor="#27384F",lw=1,transform=ax.transAxes,zorder=2))
        ax.text(0.5,y-0.005,tit,ha="center",va="center",color=WHITE,fontproperties=Lr(14),transform=ax.transAxes)
        # stances enfrentados
        ax.fill([0.49,0.51,0.50],[y-0.055,y-0.055,y-0.075],color="#C0473B",transform=ax.transAxes,zorder=4)
        ax.text(0.495,y-0.048,"",ha="center")
        yy=y-0.05
        for j,ln in enumerate(textwrap.wrap("«%s»"%a,30)):
            ax.text(0.27,yy-j*0.026,ln,ha="center",va="top",color="#BFD3F5",fontproperties=P(9.3),transform=ax.transAxes)
        for j,ln in enumerate(textwrap.wrap("«%s»"%b,30)):
            ax.text(0.73,yy-j*0.026,ln,ha="center",va="top",color="#F0D79A",fontproperties=P(9.3),transform=ax.transAxes)
        # detonante
        ax.text(0.5,y-h+0.072,"SALTA CUANDO  ·  %s"%trig.upper(),ha="center",va="center",
                color="#C9756A",fontproperties=Pm(8),transform=ax.transAxes)
    ax.text(0.10,0.06,"Ver la grieta no la abre: la desactiva. Lo que se nombra, se puede negociar.",
            ha="left",va="center",color=accent,fontproperties=Li(12),transform=ax.transAxes)
    fig.savefig(out,dpi=130); plt.close(fig); return out

def _eur0(n):
    try: return "{:,.0f} €".format(float(n)).replace(",",".")
    except Exception: return "—"

def esfuerzo_vital(out, nA, nB, pctA, pctB, modelo, micro, accent=BLUE, capA=None, capB=None):
    """50/50 en dinero != 50/50 en esfuerzo. Barras: % del sueldo en lo comun + capacidad de ahorro restante."""
    fig,ax=_canvas(); _bg(ax,(0.84,0.84))
    _vbar(ax,0.085,0.90,"El esfuerzo no se reparte como el dinero",accent,sz=18)
    ax.text(0.107,0.852,_spaced("VUESTRO MODELO: %s"%modelo.upper(),0).replace("  "," "),
            ha="left",va="center",color=MUTE,fontproperties=P(9),transform=ax.transAxes)
    ax.text(0.10,0.79,"Qué porcentaje del sueldo de cada uno se evapora en los gastos comunes:",
            ha="left",va="center",color=MUTE,fontproperties=P(10.5),transform=ax.transAxes)
    cA="#3D7DFF"; cB="#E3B341"
    def row(y,nombre,pct,c):
        ax.text(0.10,y+0.035,nombre,ha="left",va="center",color=WHITE,fontproperties=Lr(13),transform=ax.transAxes)
        ax.text(0.90,y+0.035,"%d%%"%round(pct),ha="right",va="center",color=c,fontproperties=L(24),transform=ax.transAxes)
        ax.add_patch(Rectangle((0.10,y),0.80,0.026,color="#16243A",transform=ax.transAxes,zorder=3))
        ax.add_patch(Rectangle((0.10,y),0.80*max(.02,min(1,pct/100.0)),0.026,color=c,transform=ax.transAxes,zorder=4))
    row(0.665,nA,pctA,cA); row(0.565,nB,pctB,cB)
    my=0.40
    if capA is not None and capB is not None:
        ax.text(0.10,0.485,"Y LO QUE LE QUEDA A CADA UNO PARA AHORRAR LO SUYO, TRAS LO COMÚN:",
                ha="left",va="center",color="#8FA1BC",fontproperties=P(8.5),transform=ax.transAxes)
        def cap(x,nombre,val,c):
            ax.text(x,0.435,nombre,ha="left",va="center",color=c,fontproperties=Pm(9.5),transform=ax.transAxes)
            ax.text(x,0.388,_eur0(val),ha="left",va="center",color=WHITE,fontproperties=L(23),transform=ax.transAxes)
        cap(0.10,nA,capA,cA); cap(0.52,nB,capB,cB)
        my=0.31
    import textwrap; yy=my
    for ln in textwrap.wrap(micro,84):
        ax.text(0.10,yy,ln,ha="left",va="top",color=MUTE,fontproperties=P(10),transform=ax.transAxes); yy-=0.030
    ax.text(0.10,0.075,"Un reparto justo de dinero puede ser un reparto injusto de futuro.",
            ha="left",va="center",color=accent,fontproperties=Li(13),transform=ax.transAxes)
    fig.savefig(out,dpi=130); plt.close(fig); return out

def balanza_aportacion(out, nA, nB, econA, econB, hogarA, hogarB, verdict, accent=BLUE):
    """Las dos monedas: aportación económica (%) y aportación al hogar (%). econA+econB=100, idem hogar."""
    fig,ax=_canvas(); _bg(ax,(0.84,0.84))
    _vbar(ax,0.085,0.90,"Las dos monedas de una familia",accent,sz=20)
    ax.text(0.107,0.85,"Una casa no se sostiene solo con dinero. Esto es lo que cada uno aporta de verdad.",
            ha="left",va="center",color=MUTE,fontproperties=Li(11.5),transform=ax.transAxes)
    cA="#3D7DFF"; cB="#E3B341"
    ax.text(0.27,0.80,nA.upper(),ha="center",va="center",color=cA,fontproperties=Pm(10),transform=ax.transAxes)
    ax.text(0.73,0.80,nB.upper(),ha="center",va="center",color=cB,fontproperties=Pm(10),transform=ax.transAxes)
    def split(y,titulo,a,b):
        ax.text(0.10,y+0.052,titulo,ha="left",va="center",color=WHITE,fontproperties=Lr(13),transform=ax.transAxes)
        ax.add_patch(Rectangle((0.10,y),0.80*(a/100.0),0.034,color=cA,transform=ax.transAxes,zorder=4))
        ax.add_patch(Rectangle((0.10+0.80*(a/100.0),y),0.80*(b/100.0),0.034,color=cB,transform=ax.transAxes,zorder=4))
        ax.text(0.11,y+0.017,"%d%%"%round(a),ha="left",va="center",color="#06101F",fontproperties=Pb(10),transform=ax.transAxes)
        ax.text(0.89,y+0.017,"%d%%"%round(b),ha="right",va="center",color="#06101F",fontproperties=Pb(10),transform=ax.transAxes)
    split(0.64,"Aportación económica",econA,econB)
    split(0.50,"Aportación al hogar y los cuidados",hogarA,hogarB)
    # veredicto
    import textwrap
    ax.add_patch(FancyBboxPatch((0.09,0.20),0.82,0.16,boxstyle="round,pad=0.006,rounding_size=0.012",
                 facecolor="#0E1A2E",edgecolor="#27384F",lw=1,transform=ax.transAxes,zorder=2))
    yy=0.325
    for ln in textwrap.wrap(verdict,84):
        ax.text(0.12,yy,ln,ha="left",va="top",color=WHITE,fontproperties=P(10),transform=ax.transAxes); yy-=0.030
    ax.text(0.10,0.10,"Antes de repartir el dinero, reconoced las dos monedas. Ahí empieza la justicia real.",
            ha="left",va="center",color=accent,fontproperties=Li(12),transform=ax.transAxes)
    fig.savefig(out,dpi=130); plt.close(fig); return out

def anzuelo(out, items, url, accent=GOLD):
    """Página-anzuelo T1: lo que espera en el Libro completo (T2)."""
    fig,ax=_canvas(); _bg(ax,(0.84,0.20),tint="#16202E")
    _vbar(ax,0.085,0.86,"Has visto tu diagnóstico.",accent,sz=21)
    ax.text(0.107,0.805,"No has visto tu Libro.",ha="left",va="center",color=WHITE,fontproperties=L(21),transform=ax.transAxes)
    ax.text(0.10,0.73,"Esto es solo el espejo. El Libro Financiero completo abre, con tus mismos datos:",
            ha="left",va="top",color=MUTE,fontproperties=P(11),transform=ax.transAxes)
    yy=0.66
    for it in items:
        ax.fill([0.105,0.119,0.112],[yy-0.004,yy-0.004,yy+0.010],color=accent,transform=ax.transAxes,zorder=5)
        ax.text(0.14,yy+0.004,it,ha="left",va="center",color=WHITE,fontproperties=P(10.5),transform=ax.transAxes); yy-=0.048
    ax.add_patch(FancyBboxPatch((0.09,0.10),0.82,0.12,boxstyle="round,pad=0.006,rounding_size=0.012",
                 facecolor="#0E1A2E",edgecolor=accent,lw=1.2,transform=ax.transAxes,zorder=2))
    ax.text(0.5,0.175,"Desbloquea El Libro Financiero completo",ha="center",va="center",color=accent,fontproperties=L(15),transform=ax.transAxes)
    ax.text(0.5,0.135,url,ha="center",va="center",color=MUTE,fontproperties=P(9),transform=ax.transAxes)
    fig.savefig(out,dpi=130); plt.close(fig); return out

def cover_pareja(out, nA, nB, fecha, ref="ITAP"):
    fig,ax=_canvas(); _bg(ax,(0.80,0.86))
    _emblem(ax,0.5,0.845)
    ax.text(0.5,0.78,_spaced("ADAPTA  FAMILY  OFFICE",1),ha="center",va="center",color=MUTE,fontproperties=P(8.5),transform=ax.transAxes)
    ax.text(0.5,0.66,_spaced("VUESTRO LIBRO FINANCIERO"),ha="center",va="center",color=BLUE_L,fontproperties=Pm(10),transform=ax.transAxes)
    ax.text(0.5,0.565,"EL LIBRO DE",ha="center",va="center",color=WHITE,fontproperties=L(30),transform=ax.transAxes)
    nombres=("%s  &  %s"%(nA.upper(),nB.upper()))
    fs=34 if len(nombres)<=22 else (26 if len(nombres)<=30 else 20)
    ax.text(0.5,0.475,nombres,ha="center",va="center",color=BLUE,fontproperties=L(fs),transform=ax.transAxes)
    ax.plot([0.42,0.58],[0.42,0.42],color=BLUE,lw=1.6,transform=ax.transAxes)
    ax.text(0.5,0.375,_spaced("DOS VIDAS · UNA ECONOMÍA",1),ha="center",va="center",color=MUTE,fontproperties=P(10),transform=ax.transAxes)
    ax.text(0.5,0.17,"Edición de Pareja · Tier III",ha="center",va="center",color=FAINT,fontproperties=P(9.5),transform=ax.transAxes)
    ax.text(0.5,0.075,"DOCUMENTO CONFIDENCIAL · %s · USO PRIVADO"%ref,ha="center",va="center",color=FAINT,fontproperties=P(7),transform=ax.transAxes)
    ax.text(0.5,0.05,fecha,ha="center",va="center",color=FAINT,fontproperties=P(7.5),transform=ax.transAxes)
    fig.savefig(out,dpi=130); plt.close(fig); return out
