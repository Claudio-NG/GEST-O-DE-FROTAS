import os
import sys
import re
import json
import shutil
import unicodedata
import pandas as pd
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from flask import Flask, request, send_file, Response, jsonify
import threading
import webbrowser

USERS_FILE = 'users.csv'
MODULES = [
    "Combustível",
    "Condutores",
    "Infrações e Multas",
    "Acidentes",
    "Avarias Corretivas (Acidentes e Mau Uso)",
    "Relatórios"
]
MULTAS_ROOT = r"T:\\Veiculos\\VEÍCULOS - RN\\MULTAS"
GERAL_MULTAS_CSV = r"T:\\Veiculos\\VEÍCULOS - RN\\CPO-VEÍCULOS\\GERAL_MULTAS.csv"
ORGAOS = ["DETRAN","DEMUTRAM","STTU","DNIT","PRF","SEMUTRAM","DMUT"]
PORTUGUESE_MONTHS = {1:"JANEIRO",2:"FEVEREIRO",3:"MARÇO",4:"ABRIL",5:"MAIO",6:"JUNHO",7:"JULHO",8:"AGOSTO",9:"SETEMBRO",10:"OUTUBRO",11:"NOVEMBRO",12:"DEZEMBRO"}
DATE_FORMAT = "%d-%m-%Y"
DATE_COLS = ["DATA INDITACAO","BOLETO","LANÇAMENTO NFF","VALIDACAO NFF","CONCLUSAO","SGU"]
STATUS_OPS = ["","Pendente","Pago","Vencido"]
STATUS_COLOR = {"Pago":"#2ecc71","Pendente":"#ffd166","Vencido":"#ef5350"}
PASTORES_DIR = r"T:\\Veiculos\\VEÍCULOS - RN\\CPO-VEÍCULOS"
PASTORES_XLSX = os.path.join(PASTORES_DIR, "Notificações de Multas - Fase Pastores.xlsx")
DETALHAMENTO_XLSX = os.path.join(PASTORES_DIR, "Notificações de Multas - Detalhamento.xlsx")

app = Flask(__name__)

HTML = r"""
<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Gestão de Frota</title>
<style>
:root{--navy:#0B2A4A;--navy2:#123C69;--primary:#214D80;--glass:rgba(255,255,255,0.85);--danger:#C62828;--muted:#F3F6FA}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:#fff;color:var(--navy);font-family:Inter,system-ui,Arial,sans-serif}
.container{max-width:1200px;margin:0 auto;padding:16px}
.card{background:#fff;border:1px solid var(--primary);border-radius:18px;padding:18px;box-shadow:0 8px 20px rgba(0,0,0,.08)}
.glass{background:var(--glass);border:1px solid rgba(11,42,74,.25);border-radius:18px;padding:18px;box-shadow:0 8px 32px rgba(0,0,0,.12)}
.h1{font-size:32px;font-weight:800;text-align:center;margin:8px 0}
.row{display:flex;gap:12px;flex-wrap:wrap}
.col{flex:1 1 280px}
.btn{background:linear-gradient(90deg,var(--navy),var(--navy2));color:#fff;border:none;border-radius:12px;padding:10px 16px;font-weight:700;cursor:pointer}
.btn:hover{filter:brightness(.95)}
.btn:active{filter:brightness(.85)}
.btn-danger{background:linear-gradient(90deg,#C62828,#B71C1C)}
.input,select{width:100%;background:#fff;color:var(--navy);border:2px solid var(--navy2);border-radius:10px;padding:8px}
label{font-weight:600;color:var(--primary)}
.table{width:100%;border-collapse:separate;border-spacing:0}
.table th{background:var(--navy);color:#fff;padding:10px;border:none;position:sticky;top:0;z-index:2}
.table td{background:#fff;color:var(--navy);border-bottom:1px solid #D5DFEC;padding:8px;vertical-align:top}
.table tr:nth-child(even) td{background:var(--muted)}
.badge{display:inline-block;padding:4px 8px;border-radius:8px;color:#fff;font-size:12px;font-weight:700}
.toolbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.hidden{display:none}
.grid4{display:grid;grid-template-columns:repeat(4,minmax(220px,1fr));gap:12px}
@media(max-width:1024px){.grid4{grid-template-columns:repeat(2,minmax(220px,1fr))}}
@media(max-width:600px){.grid4{grid-template-columns:1fr}}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.35);display:none;align-items:center;justify-content:center;padding:16px}
.modal.show{display:flex}
.modal>.content{background:#fff;border-radius:16px;max-width:640px;width:100%;padding:16px}
.kpi{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.kpi .card{display:flex;flex-direction:column;align-items:center;justify-content:center}
.kpi .big{font-size:28px;font-weight:800}
.navtabs{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.navtabs .tab{background:rgba(11,42,74,.10);padding:10px 16px;border-radius:14px;cursor:pointer}
.navtabs .tab.active{background:rgba(11,42,74,.18)}
.header{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
.small{font-size:12px;color:#456}
</style>
</head>
<body>
<div id="app" class="container"></div>
<script>
const STATUS_COLOR={"Pago":"#2ecc71","Pendente":"#ffd166","Vencido":"#ef5350"}
const DATE_COLS=["DATA INDITACAO","BOLETO","LANÇAMENTO NFF","VALIDACAO NFF","CONCLUSAO","SGU"]
const MODULES=["Combustível","Condutores","Infrações e Multas","Acidentes","Avarias Corretivas (Acidentes e Mau Uso)","Relatórios"]
let state={user:null,perms:[],geral:[],geralCols:[],geralFilter:{},geralText:{},relCols:[],relData:[],relFilter:{},relText:{}}
function el(t,a={},...c){const e=document.createElement(t);for(const k in a){if(k=="class")e.className=a[k];
const ORGAOS = [[ORGAOS]];
const STATUS_OPS = [[STATUS_OPS]];
else if(k=="style")Object.assign(e.style,a[k]);else if(k.startsWith("on"))e.addEventListener(k.slice(2),a[k]);else if(a[k]!==null&&a[k]!==undefined)e.setAttribute(k,a[k])}c.flat().forEach(x=>{if(x===null||x===undefined)return; if(typeof x==="string")e.appendChild(document.createTextNode(x)); else e.appendChild(x)});return e}
function api(u,m="GET",d=null){return fetch(u,{method:m,headers:d instanceof FormData?{}:{"Content-Type":"application/json"},body:d instanceof FormData?d:(d?JSON.stringify(d):null)}).then(r=>{if(!r.ok)throw new Error("erro");const ct=r.headers.get("content-type")||"";if(ct.includes("application/json"))return r.json();return r.text()})}
function mountLogin(){const root=document.getElementById("app");root.innerHTML="";const email=el("input",{class:"input",type:"email",placeholder:"E-mail"});const pass=el("input",{class:"input",type:"password",placeholder:"Senha"});const remember=el("input",{type:"checkbox"});const entrar=el("button",{class:"btn",onclick:async()=>{try{const r=await api('/api/login','POST',{email:email.value.trim().toLowerCase(),password:pass.value,remember:remember.checked});if(r.ok){state.user=r.email;state.perms=r.permissions==='todos'?MODULES:r.permissions;mountHome()}else alert('Acesso negado')}catch(e){alert('Falha')}}},"Entrar");const req=el("button",{class:"btn",onclick:()=>mountCadastro()},"Solicitar Acesso");root.appendChild(el("div",{class:"glass"},el("div",{class:"h1"},"Gestão de Frota"),el("div",{class:"row"},el("div",{class:"col"},el("label",{},"E-mail"),email),el("div",{class:"col"},el("label",{},"Senha"),pass)),el("div",{class:"row"},el("label",{},el("input",{type:"checkbox",id:"rem"})," ","Lembrar por 30 dias")),el("div",{class:"toolbar"},entrar,req))) ;document.getElementById('rem').addEventListener('change',e=>remember.checked=e.target.checked)}
function mountCadastro(){const root=document.getElementById("app");root.innerHTML="";const email=el("input",{class:"input",type:"email"});const pass=el("input",{class:"input",type:"password"});const box=el("div",{class:"grid4"},...MODULES.map(m=>el("label",{},el("input",{type:'checkbox',value:m})," ",m)));const salvar=el("button",{class:"btn",onclick:async()=>{const perms=[...box.querySelectorAll('input[type=checkbox]')].filter(i=>i.checked).map(i=>i.value);try{const r=await api('/api/register','POST',{email:email.value.trim().toLowerCase(),password:pass.value,permissions:perms});if(r.ok){mountLogin()}else alert('Erro')}catch(e){alert('Falha')}}},"Salvar");const voltar=el("button",{class:"btn",onclick:()=>mountLogin()},"Voltar");root.appendChild(el("div",{class:"card"},el("div",{class:"h1"},"Cadastro de Usuário"),el("div",{class:"row"},el("div",{class:"col"},el("label",{},"E-mail"),email),el("div",{class:"col"},el("label",{},"Senha"),pass)),el("div",{},el("label",{},"Permissões"),box),el("div",{class:"toolbar"},salvar,voltar))) }
function headerBar(t){return el("div",{class:"header"},el("div",{class:"h1"},t),el("div",{},el("button",{class:"btn",onclick:()=>mountHome()},"Início"),el("button",{class:"btn btn-danger",onclick:()=>{state.user=null;state.perms=[];mountLogin()}},"Sair"))) }
function mountHome(){const root=document.getElementById("app");root.innerHTML="";const mods=state.perms;const grid=el("div",{class:"grid4"},...mods.map(m=>el("button",{class:"btn",style:{minHeight:'64px',fontSize:'18px',fontWeight:'800'},onclick:()=>openModule(m)},m)));root.appendChild(el("div",{class:"glass"},el("div",{class:"h1"},"Gestão de Frota")));root.appendChild(el("div",{class:"card"},grid))}
function openModule(m){if(m==="Infrações e Multas")mountMultas(); else if(m==="Relatórios")mountRelatorios(); else if(m==="Combustível")mountCombustivel(); else mountHome()}
function buildFilters(cols,data,withText=true){const wrap=el("div",{class:"grid4"});cols.forEach(c=>{const select=el("select",{},el("option",{value:"__all"},"Todos"),el("option",{value:"__nz"},"Excluir vazios"),el("option",{value:"__z"},"Somente vazios"));const input=withText?el("input",{class:"input",placeholder:"Filtrar "+c}):null;const box=el("div",{class:"col"},el("label",{},c),select,withText?input:null);wrap.appendChild(box)});return wrap}
function filterData(cols,data,wrap,stateMap,textMap){let rows=[...data];cols.forEach((c,i)=>{const b=wrap.children[i];const sel=b.querySelector('select').value;const txt=(b.querySelector('input')?b.querySelector('input').value.trim().toLowerCase():"");if(sel=="__nz")rows=rows.filter(r=>(r[c]||"")!=="");else if(sel=="__z")rows=rows.filter(r=>(r[c]||"")==="");else if(sel!=='__all')rows=rows.filter(r=>String(r[c]||"")===sel);if(txt){const terms=txt.split(/\s+/).filter(Boolean);rows=rows.filter(r=>terms.every(t=>String(r[c]||"").toLowerCase().includes(t)))}stateMap[c]=sel;textMap[c]=txt});return rows}
function colorize(td,val){if(!val)return;const bg=STATUS_COLOR[val];if(bg){td.style.background=bg;const d=document.createElement('div');d.style.color=(luminance(bg)>=0.63?'#000':'#fff')}}
function luminance(hex){const c=parseInt(hex.slice(1),16);const r=(c>>16)&255;const g=(c>>8)&255;const b=c&255;return (0.299*r+0.587*g+0.114*b)/255}
function tableFrom(rows,cols){const table=el("table",{class:"table"});const thead=el("thead",{},el("tr",{},...cols.map(c=>el("th",{},c))));const tbody=el("tbody");rows.forEach(r=>{const tr=el("tr");cols.forEach(c=>{const td=el("td",{},String(r[c]??""));if(DATE_COLS.includes(c)){const st=r[c+"_STATUS"]||"";if(st){const bg=STATUS_COLOR[st];if(bg){td.style.background=bg;td.style.color=(luminance(bg)>=0.63?'#000':'#fff')}}}tr.appendChild(td)});tbody.appendChild(tr)});table.appendChild(thead);table.appendChild(tbody);return table}
function ensureStatus(df){DATE_COLS.forEach(c=>{if(!df.columns.includes(c+"_STATUS"))df.columns.push(c+"_STATUS")});return df}
async function loadGeral(){const r=await api('/api/geral');state.geral=r.rows;state.geralCols=r.columns.filter(c=>!c.endsWith('_STATUS'))}
function mountMultas(){const root=document.getElementById("app");root.innerHTML="";root.appendChild(headerBar("Infrações e Multas"));const host=el("div");root.appendChild(host);api('/api/geral').then(r=>{state.geral=r.rows;state.geralCols=r.columns.filter(c=>!c.endsWith('_STATUS'));renderMultas(host)}).catch(()=>host.innerHTML='')}
function renderMultas(host){host.innerHTML="";const filters=buildFilters(state.geralCols,state.geral);const tabela=el("div",{class:"card"});const tools=el("div",{class:"toolbar"});const visao=el("button",{class:"btn",onclick:()=>{const rows=filterData(state.geralCols,state.geral,filters,state.geralFilter,state.geralText);showVisao(rows)}},"Visão Geral");const limpar=el("button",{class:"btn",onclick:()=>{filters.querySelectorAll('select').forEach(s=>s.value='__all');filters.querySelectorAll('input').forEach(i=>i.value='');renderMultas(host)}},"Limpar filtros");const inserir=el("button",{class:"btn",onclick:()=>openInserir()},"Inserir");const editar=el("button",{class:"btn",onclick:()=>openEditar()},"Editar");const excluir=el("button",{class:"btn btn-danger",onclick:()=>openExcluir()},"Excluir");const conferir=el("button",{class:"btn",onclick:()=>openConferir()},"CONFERIR FLUIG");const past=el("button",{class:"btn",onclick:()=>fasePastores()},"FASE PASTORES");const exportar=el("a",{class:"btn",href:"/api/geral/download"},"Exportar CSV");tools.appendChild(visao);tools.appendChild(limpar);tools.appendChild(inserir);tools.appendChild(editar);tools.appendChild(excluir);tools.appendChild(conferir);tools.appendChild(past);tools.appendChild(exportar);host.appendChild(el("div",{class:"card"},filters));host.appendChild(el("div",{class:"card"},tools));function refresh(){const rows=filterData(state.geralCols,state.geral,filters,state.geralFilter,state.geralText);tabela.innerHTML="";tabela.appendChild(tableFrom(rows,state.geralCols))}filters.addEventListener('change',refresh);filters.addEventListener('input',e=>{if(e.target.tagName==='INPUT')refresh()});refresh();host.appendChild(tabela)}
function showVisao(rows){const cols=Object.keys(rows[0]||{});const s={};cols.forEach(c=>{let sum=0,uni=new Set();rows.forEach(r=>{const v=r[c];const n=parseFloat(String(v).replace(/[^0-9,.-]/g,'').replace('.','').replace(',','.'));if(!isNaN(n))sum+=n;uni.add(String(v))});s[c]=isFinite(sum)&&sum!==0?sum.toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2}):uni.size});const body=el("div",{},...Object.entries(s).map(([k,v])=>el("div",{},el("b",{},k+": "),String(v))));openModal("Visão Geral",body)}
function inputRow(labelTxt,input){return el("div",{class:"row"},el("div",{class:"col"},el("label",{},labelTxt),input))}
function openModal(title,content,actions){const modal=el("div",{class:"modal show"});const c=el("div",{class:"content"},el("div",{class:"h1"},title),content,el("div",{class:"toolbar"},...(actions||[el("button",{class:"btn",onclick:()=>modal.remove()},"Fechar")]));modal.addEventListener('click',e=>{if(e.target===modal)modal.remove()});document.body.appendChild(modal)}
function openInserir(prefill){const form=el("form");const F=(id,type='text')=>el("input",{class:"input",id,required:type!=='optional',type});const FLUIG=F('FLUIG');if(prefill)FLUIG.value=prefill;const ORGAO=el('select',{},...['',...ORGAOS].map(x=>el('option',{value:x},x)));
const base=["INFRATOR","ANO","MES","PLACA","NOTIFICACAO"];base.forEach(k=>form.appendChild(inputRow(k,F(k))));form.appendChild(inputRow('ORGÃO',ORGAO));DATE_COLS.forEach(k=>{const d=F(k,'date');const s=el('select',{},...STATUS_OPS.map(x=>el('option',{value:x},x)));const row=el('div',{class:'row'},el('div',{class:'col'},el('label',{},k),d),el('div',{class:'col'},el('label',{},k+'_STATUS'),s));form.appendChild(row)});const pdf=el('input',{type:'file',accept:'application/pdf'});form.appendChild(inputRow('PDF',pdf));const salvar=el("button",{class:"btn",type:"button",onclick:async()=>{const fd=new FormData();const obj={};[...form.querySelectorAll('input,select')].forEach(i=>{if(i.type==='file')return;obj[i.id||i.previousElementSibling?.textContent||'']=i.value});fd.append('json',JSON.stringify(obj));if(pdf.files[0])fd.append('pdf',pdf.files[0]);const r=await fetch('/api/geral/insert',{method:'POST',body:fd});if(r.ok){document.querySelector('.modal').remove();mountMultas()}else alert('Erro')}},'Salvar');openModal('Inserir Multa',form,[salvar,el('button',{class:'btn',onclick:()=>document.querySelector('.modal').remove()},'Fechar')])}
function openEditar(){const key=prompt('Digite FLUIG');if(!key)return;const row=state.geral.find(r=>String(r['FLUIG']||'').trim()===String(key).trim());if(!row){alert('FLUIG não encontrado');return}const form=el("form");const mk=(k,v)=>{const i=el('input',{class:'input',id:k,value:v||''});return inputRow(k,i)};state.geralCols.forEach(k=>{if(!DATE_COLS.includes(k)&&k!=='ORGÃO')form.appendChild(mk(k,row[k]));});const org=el('select',{id:'ORGÃO'},...['',...ORGAOS].map(x=>el('option',{value:x,selected:row['ORGÃO']===x},x)));form.appendChild(inputRow('ORGÃO',org));DATE_COLS.forEach(k=>{const d=el('input',{class:'input',id:k,type:'date'});const st=el('select',{id:k+'_STATUS'},...STATUS_OPS.map(x=>el('option',{value:x,selected:(row[k+'_STATUS']||'')===x},x)));if(row[k]){const parts=row[k].split('-');if(parts.length===3){const dd=parts[0].padStart(2,'0');const mm=parts[1].padStart(2,'0');const yy=parts[2];d.value=`${yy}-${mm}-${dd}`}}const roww=el('div',{class:'row'},el('div',{class:'col'},el('label',{},k),d),el('div',{class:'col'},el('label',{},k+'_STATUS'),st));form.appendChild(roww)});const salvar=el('button',{class:'btn',type:'button',onclick:async()=>{const obj={};[...form.querySelectorAll('input,select')].forEach(i=>{obj[i.id]=i.value});obj['FLUIG']=row['FLUIG'];const r=await api('/api/geral/edit','POST',obj);if(r.ok){document.querySelector('.modal').remove();mountMultas()}else alert('Erro')}},'Salvar');openModal('Editar Multa',form,[salvar,el('button',{class:'btn',onclick:()=>document.querySelector('.modal').remove()},'Fechar')])}
function openExcluir(){const key=prompt('Digite FLUIG para excluir');if(!key)return;api('/api/geral/delete','POST',{fluig:key}).then(r=>{if(r.ok)mountMultas();else alert('Erro')}).catch(()=>{})}
function openConferir(){const wrap=el('div');const up=el('input',{type:'file',accept:'.xlsx,.xls,.csv'});wrap.appendChild(el('div',{},el('label',{},'Detalhamento (.xlsx/.csv)'),up));const run=el('button',{class:'btn',onclick:async()=>{const fd=new FormData();if(up.files[0])fd.append('detalhamento',up.files[0]);const r=await fetch('/api/conferir_fluig',{method:'POST',body:fd});const j=await r.json();const left=tableFrom(j.left,j.left.length?Object.keys(j.left[0]):[]);const right=tableFrom(j.right,j.right.length?Object.keys(j.right[0]):[]);wrap.appendChild(el('div',{},el('h3',{},'Detalhamento → faltando no CSV'),left,el('h3',{},'CSV → faltando no Detalhamento'),right))}},'Executar');openModal('Conferir Fluig',el('div',{},wrap),[run,el('button',{class:'btn',onclick:()=>document.querySelector('.modal').remove()},'Fechar')])}
function fasePastores(){api('/api/fase_pastores','POST',{}).then(r=>{alert(r.msg||'OK');mountMultas()}).catch(()=>{})}
function mountRelatorios(){const root=document.getElementById('app');root.innerHTML='';root.appendChild(headerBar('Relatórios'));const up=el('input',{type:'file',accept:'.xlsx,.xls,.csv'});const run=el('button',{class:'btn',onclick:async()=>{const fd=new FormData();if(!up.files[0])return;fd.append('file',up.files[0]);const r=await fetch('/api/relatorio/load',{method:'POST',body:fd});const j=await r.json();state.relCols=j.columns;state.relData=j.rows;renderRelatorios()}},'Carregar');root.appendChild(el('div',{class:'card'},el('div',{},el('label',{},'Arquivo'),up),el('div',{class:'toolbar'},run)));const host=el('div');root.appendChild(host);function renderRelatorios(){host.innerHTML='';const filters=buildFilters(state.relCols,state.relData);const tabela=el('div',{class:'card'});function refresh(){const rows=filterData(state.relCols,state.relData,filters,state.relFilter,state.relText);tabela.innerHTML='';tabela.appendChild(tableFrom(rows,state.relCols))}filters.addEventListener('change',refresh);filters.addEventListener('input',e=>{if(e.target.tagName==='INPUT')refresh()});refresh();host.appendChild(el('div',{class:'card'},filters));host.appendChild(tabela)} }
function mountCombustivel(){const root=document.getElementById('app');root.innerHTML='';root.appendChild(headerBar('Combustível'));const host=el('div',{class:'card'},el('div',{class:'small'},'Carregue os extratos na versão desktop atual para cálculos avançados.'));root.appendChild(host)}
mountLogin()
</script>
</body>
</html>
"""

def ensure_status_cols_df(df):
    changed=False
    for c in DATE_COLS:
        sc=f"{c}_STATUS"
        if sc not in df.columns:
            df[sc]=""
            changed=True
    return df

def to_brl_decimal(x):
    s=str(x).strip()
    if not s:
        return Decimal("0")
    s=re.sub(r"[^\d,.-]","",s)
    if "," in s and "." in s:
        dec="," if s.rfind(",")>s.rfind(".") else "."
        mil="." if dec=="," else ","
        s=s.replace(mil,"")
        if dec==",":
            s=s.replace(",",".")
    elif "," in s and "." not in s:
        s=s.replace(".","")
        s=s.replace(",",".")
    try:
        return Decimal(s)
    except:
        return Decimal("0")

def build_multa_dir(infrator,ano,mes,placa,notificacao,fluig):
    sub=f"{placa}_{notificacao}_FLUIG({fluig})"
    return os.path.join(MULTAS_ROOT,str(infrator).strip(),str(ano).strip(),str(mes).strip(),sub)

def load_users_csv():
    if os.path.exists(USERS_FILE):
        try:
            df=pd.read_csv(USERS_FILE,parse_dates=['last_login'])
        except:
            df=pd.read_csv(USERS_FILE)
        if 'last_login' not in df.columns:
            df['last_login']=""
        if 'permissions' not in df.columns:
            df['permissions']="todos"
        if 'remember' not in df.columns:
            df['remember']=False
        return df
    df=pd.DataFrame(columns=['email','password','last_login','permissions','remember'])
    df.to_csv(USERS_FILE,index=False)
    return df

def save_users_csv(df):
    df.to_csv(USERS_FILE,index=False)

def read_table_file(fp):
    ext=os.path.splitext(fp)[1].lower()
    if ext in ('.xlsx','.xls'):
        return pd.read_excel(fp,dtype=str).fillna("")
    if ext=='.csv':
        try:
            return pd.read_csv(fp,dtype=str,encoding='utf-8').fillna("")
        except UnicodeDecodeError:
            return pd.read_csv(fp,dtype=str,encoding='latin1').fillna("")
    return pd.DataFrame()

def ensure_base_csv():
    os.makedirs(os.path.dirname(GERAL_MULTAS_CSV),exist_ok=True)
    if not os.path.exists(GERAL_MULTAS_CSV):
        pd.DataFrame(columns=["INFRATOR","ANO","MES","PLACA","NOTIFICACAO","FLUIG","ORGÃO"]+DATE_COLS).to_csv(GERAL_MULTAS_CSV,index=False)

@app.route('/')
def index():
    return Response(HTML.replace('[[ORGAOS]]', json.dumps(ORGAOS, ensure_ascii=False)).replace('[[STATUS_OPS]]', json.dumps(STATUS_OPS, ensure_ascii=False)), mimetype='text/html')

@app.route('/api/login',methods=['POST'])
def api_login():
    data=request.get_json(force=True)
    email=str(data.get('email','')).strip().lower()
    password=str(data.get('password','')).strip()
    remember=bool(data.get('remember',False))
    df=load_users_csv()
    idx=df.index[df['email'].astype(str).str.lower()==email].tolist()
    if idx:
        i=idx[0]
        if str(df.at[i,'password']).strip()==password:
            df.at[i,'last_login']=datetime.now()
            df.at[i,'remember']=remember
            save_users_csv(df)
            perms=df.at[i,'permissions']
            try:
                perms_eval=eval(perms) if isinstance(perms,str) else perms
            except:
                perms_eval='todos'
            return jsonify(ok=True,email=email,permissions=perms_eval)
    return jsonify(ok=False)

@app.route('/api/register',methods=['POST'])
def api_register():
    data=request.get_json(force=True)
    email=str(data.get('email','')).strip().lower()
    password=str(data.get('password','')).strip()
    perms=data.get('permissions',[])
    df=load_users_csv()
    if email in df['email'].astype(str).str.lower().tolist():
        return jsonify(ok=False)
    now=datetime.now()
    df.loc[len(df)]=[email,password,now,perms,False]
    save_users_csv(df)
    return jsonify(ok=True)

@app.route('/api/geral')
def api_geral():
    ensure_base_csv()
    df=pd.read_csv(GERAL_MULTAS_CSV,dtype=str).fillna("")
    df=ensure_status_cols_df(df)
    return jsonify(columns=df.columns.tolist(),rows=df.to_dict(orient='records'))

@app.route('/api/geral/download')
def api_geral_download():
    ensure_base_csv()
    return send_file(GERAL_MULTAS_CSV,as_attachment=True,download_name='GERAL_MULTAS.csv')

@app.route('/api/geral/insert',methods=['POST'])
def api_geral_insert():
    ensure_base_csv()
    df=pd.read_csv(GERAL_MULTAS_CSV,dtype=str).fillna("")
    df=ensure_status_cols_df(df)
    js=json.loads(request.form.get('json','{}'))
    if str(js.get('FLUIG','')).strip() in df.get('FLUIG',pd.Series([],dtype=str)).astype(str).tolist():
        return jsonify(ok=False),400
    for c in df.columns:
        if c not in js:
            js[c]=""
    df.loc[len(df)]=js
    os.makedirs(os.path.dirname(GERAL_MULTAS_CSV),exist_ok=True)
    df.to_csv(GERAL_MULTAS_CSV,index=False)
    try:
        infr=js.get('INFRATOR','')
        ano=js.get('ANO','')
        mes=js.get('MES','')
        placa=js.get('PLACA','')
        notificacao=js.get('NOTIFICACAO','')
        fluig=js.get('FLUIG','')
        dest=build_multa_dir(infr,ano,mes,placa,notificacao,fluig)
        os.makedirs(dest,exist_ok=True)
        if 'pdf' in request.files and request.files['pdf']:
            f=request.files['pdf']
            fp=os.path.join(dest,f.filename)
            f.save(fp)
    except:
        pass
    return jsonify(ok=True)

@app.route('/api/geral/edit',methods=['POST'])
def api_geral_edit():
    ensure_base_csv()
    data=request.get_json(force=True)
    key=str(data.get('FLUIG','')).strip()
    if not key:
        return jsonify(ok=False),400
    df=pd.read_csv(GERAL_MULTAS_CSV,dtype=str).fillna("")
    df=ensure_status_cols_df(df)
    rows=df.index[df['FLUIG'].astype(str)==key].tolist()
    if not rows:
        return jsonify(ok=False),404
    i=rows[0]
    for c,v in data.items():
        if c in df.columns:
            if c in DATE_COLS and v:
                try:
                    dt=pd.to_datetime(v,errors='coerce')
                    if pd.notna(dt):
                        df.at[i,c]=dt.strftime(DATE_FORMAT)
                        continue
                except:
                    pass
            df.at[i,c]=v
    df.to_csv(GERAL_MULTAS_CSV,index=False)
    return jsonify(ok=True)

@app.route('/api/geral/delete',methods=['POST'])
def api_geral_delete():
    data=request.get_json(force=True)
    key=str(data.get('fluig','')).strip()
    if not key:
        return jsonify(ok=False),400
    df=pd.read_csv(GERAL_MULTAS_CSV,dtype=str).fillna("")
    df=ensure_status_cols_df(df)
    rows=df.index[df['FLUIG'].astype(str)==key].tolist()
    if not rows:
        return jsonify(ok=False),404
    i=rows[0]
    try:
        infr=str(df.at[i,'INFRATOR']) if 'INFRATOR' in df.columns else ''
        ano=str(df.at[i,'ANO']) if 'ANO' in df.columns else ''
        mes=str(df.at[i,'MES']) if 'MES' in df.columns else ''
        placa=str(df.at[i,'PLACA']) if 'PLACA' in df.columns else ''
        notificacao=str(df.at[i,'NOTIFICACAO']) if 'NOTIFICACAO' in df.columns else ''
        fluig=str(df.at[i,'FLUIG']) if 'FLUIG' in df.columns else ''
        path=build_multa_dir(infr,ano,mes,placa,notificacao,fluig)
        if os.path.isdir(path):
            shutil.rmtree(path,ignore_errors=True)
            p=os.path.dirname(path)
            root=os.path.normpath(MULTAS_ROOT)
            for _ in range(3):
                if p and os.path.isdir(p) and not os.listdir(p) and os.path.commonpath([os.path.normpath(p),root])==root:
                    try:
                        os.rmdir(p)
                    except:
                        pass
                    p=os.path.dirname(p)
    except:
        pass
    df=df.drop(i).reset_index(drop=True)
    df.to_csv(GERAL_MULTAS_CSV,index=False)
    return jsonify(ok=True)

@app.route('/api/conferir_fluig',methods=['POST'])
def api_conferir_fluig():
    df_csv=pd.read_csv(GERAL_MULTAS_CSV,dtype=str).fillna("")
    f=request.files.get('detalhamento')
    if f:
        tmp=os.path.join(Path.cwd(),f"_tmp_{int(datetime.now().timestamp())}_{f.filename}")
        f.save(tmp)
        df_det=read_table_file(tmp)
        try:
            os.remove(tmp)
        except:
            pass
    else:
        if os.path.exists(DETALHAMENTO_XLSX):
            df_det=read_table_file(DETALHAMENTO_XLSX)
        else:
            return jsonify(left=[],right=[])
    if df_det.empty:
        return jsonify(left=[],right=[])
    status_col=next((c for c in df_det.columns if c.strip().lower()=="status"),df_det.columns[1])
    mask_aberta=df_det[status_col].astype(str).str.strip().str.lower().eq("aberta")
    df_open=df_det[mask_aberta].copy()
    if "Nº Fluig" in df_open.columns:
        fcol="Nº Fluig"
    else:
        fcol=next((c for c in df_open.columns if "fluig" in c.lower()),None)
    if not fcol:
        return jsonify(left=[],right=[])
    fluig_det=set(df_open[fcol].astype(str).str.strip())
    fluig_csv=set(df_csv.get('FLUIG',pd.Series([],dtype=str)).astype(str).str.strip())
    no_csv=[c for c in fluig_det if c and c not in fluig_csv]
    no_det=[c for c in fluig_csv if c and c not in fluig_det]
    left_cols=[fcol]+[c for c in ["Placa","Nome","AIT","Data Limite","Data Infração","Status"] if c in df_open.columns]
    df_left=df_open[df_open[fcol].astype(str).str.strip().isin(no_csv)][left_cols].copy()
    right_cols=[c for c in ["FLUIG","PLACA","INFRATOR","NOTIFICACAO","ANO","MES"] if c in df_csv.columns]
    df_right=df_csv[df_csv['FLUIG'].astype(str).str.strip().isin(no_det)][right_cols].copy()
    return jsonify(left=df_left.to_dict(orient='records'),right=df_right.to_dict(orient='records'))

@app.route('/api/fase_pastores',methods=['POST'])
def api_fase_pastores():
    if not os.path.exists(PASTORES_XLSX):
        return jsonify(ok=False,msg='Planilha Fase Pastores não encontrada')
    dfp=read_table_file(PASTORES_XLSX)
    if dfp.empty:
        return jsonify(ok=False,msg='Planilha inválida')
    fcol=next((c for c in dfp.columns if 'fluig' in str(c).lower()),None)
    dcol=next((c for c in dfp.columns if 'data' in str(c).lower() and 'pastor' in str(c).lower()),None)
    tcol=next((c for c in dfp.columns if 'tipo' in str(c).lower()),None)
    if not (fcol and dcol and tcol):
        return jsonify(ok=False,msg='Colunas não localizadas')
    df=pd.read_csv(GERAL_MULTAS_CSV,dtype=str).fillna("")
    df=ensure_status_cols_df(df)
    idx={str(f).strip():i for i,f in enumerate(df.get('FLUIG',pd.Series([],dtype=str)).astype(str))}
    changed=False
    for _,r in dfp.iterrows():
        f=str(r[fcol]).strip()
        tipo=str(r[tcol]).upper()
        data=str(r[dcol]).strip()
        if not f or f not in idx:
            continue
        if 'PASTOR' not in tipo or not data:
            continue
        try:
            dt=pd.to_datetime(data,dayfirst=True,errors='coerce')
        except:
            dt=None
        if dt is None or pd.isna(dt):
            continue
        i=idx[f]
        df.at[i,'SGU']=dt.strftime(DATE_FORMAT)
        df.at[i,'SGU_STATUS']='Pago'
        changed=True
    if changed:
        df.to_csv(GERAL_MULTAS_CSV,index=False)
        return jsonify(ok=True,msg='Atualizado')
    return jsonify(ok=True,msg='Nada para atualizar')

@app.route('/api/relatorio/load',methods=['POST'])
def api_relatorio_load():
    f=request.files.get('file')
    if not f:
        return jsonify(columns=[],rows=[])
    tmp=os.path.join(Path.cwd(),f"_tmp_{int(datetime.now().timestamp())}_{f.filename}")
    f.save(tmp)
    df=read_table_file(tmp)
    try:
        os.remove(tmp)
    except:
        pass
    df=ensure_status_cols_df(df)
    return jsonify(columns=df.columns.tolist(),rows=df.to_dict(orient='records'))

def run_server():
    threading.Timer(0.8,lambda:webbrowser.open('http://127.0.0.1:5000')).start()
    app.run(host='127.0.0.1',port=5000,debug=False)

if __name__=='__main__':
    ensure_base_csv()
    run_server()