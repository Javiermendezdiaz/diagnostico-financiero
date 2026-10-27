/* Adapta · medición propia y anónima.
   Sin cookies, sin datos personales, sin IP. Un identificador aleatorio que vive solo
   mientras la pestaña está abierta (sessionStorage) para unir los pasos de una misma visita.
   Origen: ?de=... (p. ej. ?de=li-post-12), utm_source o, si no hay nada, el dominio de procedencia. */
(function(){
  var API = "https://diagnostico-financiero-app.onrender.com";
  var ss = {get:function(k){try{return sessionStorage.getItem(k)||""}catch(e){return ""}},
            set:function(k,v){try{sessionStorage.setItem(k,v)}catch(e){}}};
  var limpia = function(s,n){return String(s||"").replace(/[^a-z0-9_.:-]/gi,"").slice(0,n||40)};
  var q; try{q=new URLSearchParams(location.search)}catch(e){q={get:function(){return null}}}
  var ref=""; try{ref=document.referrer?new URL(document.referrer).hostname:""}catch(e){}
  if(ref===location.hostname) ref="";
  if(!ref){ try{ var _r=ss.get("adaptaRef"); if(_r){ ref=new URL(_r).hostname; } }catch(e){} }
  var de = limpia(q.get("de")||q.get("utm_source")||"");
  if(de){ ss.set("adaptaDe",de); }
  else { de = ss.get("adaptaDe"); }
  if(!de && ref){
    de = /linkedin|lnkd/i.test(ref) ? "linkedin" : /google\./i.test(ref) ? "google" :
         /facebook|instagram|fb\./i.test(ref) ? "meta" : /whatsapp|wa\.me/i.test(ref) ? "whatsapp" : limpia(ref,30);
    ss.set("adaptaDe",de);
  }
  if(!de && /LinkedInApp/i.test(navigator.userAgent||"")){ de="linkedin-app"; ss.set("adaptaDe",de); }
  var vid = ss.get("adaptaVid");
  if(!vid){ vid=(Date.now().toString(36)+Math.random().toString(36).slice(2,10)); ss.set("adaptaVid",vid); }
  var pag = (location.pathname.split("/").pop()||"inicio.html").replace(".html","")||"inicio";
  var movil = /Mobi|Android|iPhone/i.test(navigator.userAgent||"") ? 1 : 0;
  var n=0;
  function ev(nombre, valor){
    if(n++>120) return;
    try{
      var p = JSON.stringify({s:vid, e:limpia(nombre,30), p:pag, de:de||"directo", r:limpia(ref,40), v:String(valor==null?"":valor).slice(0,60), m:movil});
      var url = API+"/api/ev";
      if(navigator.sendBeacon && navigator.sendBeacon(url, new Blob([p],{type:"text/plain"}))) return;
      fetch(url,{method:"POST",body:p,headers:{"Content-Type":"text/plain"},keepalive:true,mode:"no-cors"}).catch(function(){});
    }catch(e){}
  }
  window.adaptaEv = ev;
  window.adaptaDe = de;
  ev("vista", q.get("tier")||"");
  // Profundidad de lectura
  var hechos={};
  addEventListener("scroll",function(){
    var h=document.documentElement, tot=(h.scrollHeight-innerHeight)||1, pc=Math.round(100*scrollY/tot);
    [25,50,75,100].forEach(function(t){ if(pc>=t-2 && !hechos[t]){hechos[t]=1; ev("scroll",t);} });
  },{passive:true});
  // Tiempo en página al salir
  var t0=Date.now(), salido=0;
  function salir(){ if(salido) return; salido=1; ev("salida", Math.round((Date.now()-t0)/1000)); }
  addEventListener("pagehide", salir);
  document.addEventListener("visibilitychange", function(){ if(document.visibilityState==="hidden") salir(); });
  // Clics: data-ev explícito o enlaces clave
  document.addEventListener("click", function(e){
    var a = e.target.closest ? e.target.closest("[data-ev],a") : null; if(!a) return;
    var de_ = a.getAttribute("data-ev"), h = a.getAttribute("href")||"";
    if(de_){ ev(de_, a.getAttribute("data-evv")||""); return; }
    if(/wa\.me|whatsapp/i.test(h)) ev("whatsapp");
    else if(/empezar2\.html/.test(h)) ev("cta_diagnostico", (h.match(/tier=(\d)/)||[])[1]||"");
    else if(/\.pdf$/i.test(h)) ev("ver_muestra", h);
    else if(/indice\.html/.test(h)) ev("cta_nota");
    else if(/planes\.html/.test(h)) ev("cta_planes");
  }, true);
  // Arrastra el origen a los enlaces internos
  if(de){
    document.addEventListener("DOMContentLoaded", function(){
      document.querySelectorAll('a[href^="indice.html"],a[href^="planes.html"],a[href^="empezar2.html"],a[href^="inicio.html"]').forEach(function(a){
        var h=a.getAttribute("href"); if(h.indexOf("de=")<0){
          var i=h.indexOf("#"), base=i<0?h:h.slice(0,i), hash=i<0?"":h.slice(i);
          a.setAttribute("href", base+(base.indexOf("?")<0?"?":"&")+"de="+encodeURIComponent(de)+hash);
        }
      });
    });
  }
})();
