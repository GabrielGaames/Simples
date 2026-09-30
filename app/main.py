from io import BytesIO
import os
from pathlib import Path
from typing import Any
from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openpyxl import load_workbook
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, A3
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from .database import Base, SessionLocal, engine, get_db
from .models import Aluno, Resultado, Turma, Usuario
from .scanner import ScanError, scan_card
from .auth import admin_user, can_access_turma, clear_login_cookie, current_user, hash_password, set_login_cookie, verify_password

BASE_DIR = Path(__file__).resolve().parent
Base.metadata.create_all(bind=engine)

def ensure_schema_updates():
    """Add columns introduced by the reporting/import format to existing databases."""
    insp = inspect(engine)
    def add_missing(table, columns):
        existing = {c['name'] for c in insp.get_columns(table)}
        with engine.begin() as conn:
            for name, ddl in columns.items():
                if name not in existing:
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}'))
    add_missing('alunos', {
        'numero_chamada': 'VARCHAR(30)',
        'status': "VARCHAR(30) DEFAULT 'ATIVO'",
    })
    add_missing('resultados', {
        'presente_1': 'BOOLEAN DEFAULT FALSE',
        'ausente_1': 'BOOLEAN DEFAULT FALSE',
        'presente_2': 'BOOLEAN DEFAULT FALSE',
        'ausente_2': 'BOOLEAN DEFAULT FALSE',
    })
    # Backfill status for existing rows.
    with engine.begin() as conn:
        conn.execute(text("UPDATE alunos SET status = 'ATIVO' WHERE status IS NULL OR TRIM(status) = ''"))

ensure_schema_updates()

def bootstrap_admin():
    login = os.getenv('ADMIN_LOGIN', '').strip().lower()
    password = os.getenv('ADMIN_PASSWORD', '')
    name = os.getenv('ADMIN_NAME', 'Administrador').strip() or 'Administrador'
    if not login or not password: return
    db = SessionLocal()
    try:
        if not db.query(Usuario).filter(Usuario.login == login).first():
            db.add(Usuario(nome=name, login=login, senha_hash=hash_password(password), tipo='admin', ativo=True)); db.commit()
    finally: db.close()
bootstrap_admin()

app = FastAPI(title='ScoreView')
app.mount('/static', StaticFiles(directory=BASE_DIR / 'static'), name='static')
@app.get('/')
def home(): return FileResponse(BASE_DIR / 'static' / 'index.html')
@app.get('/health')
def health(): return {'ok': True}

class LoginIn(BaseModel): login: str; senha: str
class UserIn(BaseModel): nome: str; login: str; senha: str; tipo: str = 'professor'; turma_ids: list[int] = []
class UserUpdate(BaseModel): nome: str; login: str; senha: str | None = None; tipo: str = 'professor'; ativo: bool = True; turma_ids: list[int] = []

@app.post('/api/auth/login')
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.login == payload.login.strip().lower()).first()
    if not user or not user.ativo or not verify_password(payload.senha, user.senha_hash): raise HTTPException(401, 'Usuário ou senha inválidos.')
    set_login_cookie(response, user.id); return {'ok': True, 'nome': user.nome, 'tipo': user.tipo}
@app.post('/api/auth/logout')
def logout(response: Response): clear_login_cookie(response); return {'ok': True}
@app.get('/api/auth/me')
def me(user: Usuario = Depends(current_user)): return {'id': user.id, 'nome': user.nome, 'login': user.login, 'tipo': user.tipo}

@app.post('/api/scan')
async def scan(file: UploadFile = File(...), user: Usuario = Depends(current_user)):
    try: return scan_card(await file.read())
    except ScanError as exc: return JSONResponse(status_code=422, content={'detail': str(exc)})
    except Exception: return JSONResponse(status_code=500, content={'detail': 'Não foi possível processar a foto. Tente outra imagem.'})

@app.get('/api/turmas')
def listar_turmas(db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    turmas = db.query(Turma).order_by(Turma.nome).all() if user.tipo == 'admin' else sorted(user.turmas, key=lambda t:t.nome)
    return [{'id': t.id, 'nome': t.nome, 'total_alunos': len(t.alunos)} for t in turmas]
@app.delete('/api/admin/turmas/{turma_id}')
def delete_turma(turma_id: int, db: Session = Depends(get_db), admin: Usuario = Depends(admin_user)):
    turma = db.get(Turma, turma_id)
    if not turma:
        raise HTTPException(404, 'Turma não encontrada.')
    nome = turma.nome
    total_alunos = len(turma.alunos)
    # A relação Turma.alunos usa delete-orphan; ao excluir a turma,
    # os alunos e seus resultados associados também são removidos.
    # A relação usuário-turma é removida pelo relacionamento many-to-many.
    db.delete(turma)
    db.commit()
    return {'ok': True, 'nome': nome, 'alunos_excluidos': total_alunos}

@app.get('/api/turmas/{turma_id}/alunos')
def listar_alunos(turma_id: int, db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    turma = db.get(Turma, turma_id)
    if not turma: raise HTTPException(404, 'Turma não encontrada.')
    if not can_access_turma(user, turma_id): raise HTTPException(403, 'Você não tem acesso a esta turma.')
    alunos = db.query(Aluno).filter(Aluno.turma_id == turma_id).order_by(Aluno.nome).all()
    return [{'id': a.id, 'numero_chamada': a.numero_chamada, 'nome': a.nome, 'matricula': a.matricula, 'status': a.status or 'ATIVO'} for a in alunos]

@app.post('/api/alunos/importar')
async def importar_alunos(file: UploadFile = File(...), db: Session = Depends(get_db), user: Usuario = Depends(admin_user)):
    if not (file.filename or '').lower().endswith(('.xlsx', '.xlsm')):
        raise HTTPException(400, 'Envie uma planilha .xlsx.')
    try:
        wb = load_workbook(BytesIO(await file.read()), read_only=True, data_only=True)
        rows = list(wb.active.iter_rows(values_only=True))
    except Exception:
        raise HTTPException(400, 'Não foi possível ler a planilha.')
    if not rows:
        raise HTTPException(400, 'A planilha está vazia.')

    def norm(v):
        import unicodedata
        value = str(v or '').strip().lower()
        return ''.join(c for c in unicodedata.normalize('NFD', value) if unicodedata.category(c) != 'Mn')

    headers = [norm(v) for v in rows[0]]
    aliases = {
        'numero_chamada': ['id', 'numero', 'numero chamada', 'nº', 'n'],
        'nome': ['nome', 'nome do aluno', 'aluno'],
        'turma': ['turma', 'sala'],
        'matricula': ['matricula', 'registro', 'ra'],
        'status': ['status', 'status escola', 'situacao', 'situação'],
    }
    indexes = {}
    for field, names in aliases.items():
        normalized = [norm(n) for n in names]
        for i, h in enumerate(headers):
            if h in normalized:
                indexes[field] = i
                break
    required = {'nome', 'turma', 'matricula'}
    if not required.issubset(indexes):
        raise HTTPException(400, 'A planilha precisa conter as colunas Nome do aluno, Turma e Matrícula. A coluna ID é recomendada para o número da chamada.')

    criados = atualizados = ignorados = 0
    for row in rows[1:]:
        def value(field):
            i = indexes.get(field)
            if i is None or i >= len(row) or row[i] is None:
                return ''
            return str(row[i]).strip()

        numero, nome, turma_nome, matricula, status = (value('numero_chamada'), value('nome'), value('turma'), value('matricula'), value('status'))
        # Excel pode entregar o número da chamada como 1.0 quando a célula é numérica.
        # O SIAP usa o número inteiro da chamada, então normalizamos antes de salvar.
        if numero:
            try:
                numero_float = float(numero.replace(',', '.'))
                if numero_float.is_integer():
                    numero = str(int(numero_float))
            except ValueError:
                pass
        if not nome or not turma_nome or not matricula:
            ignorados += 1
            continue
        status_norm = norm(status) if status else 'ativo'
        status = 'ATIVO' if status_norm in ('ativo', 'cursando') else 'NÃO ATIVO'
        turma = db.query(Turma).filter(Turma.nome == turma_nome).first()
        if not turma:
            turma = Turma(nome=turma_nome)
            db.add(turma)
            db.flush()
        aluno = db.query(Aluno).filter(Aluno.matricula == matricula).first()
        if aluno:
            aluno.nome = nome
            aluno.turma_id = turma.id
            aluno.numero_chamada = numero or aluno.numero_chamada
            aluno.status = status
            atualizados += 1
        else:
            db.add(Aluno(nome=nome, matricula=matricula, numero_chamada=numero or None, status=status, turma_id=turma.id))
            criados += 1
    db.commit()
    return {'criados': criados, 'atualizados': atualizados, 'ignorados': ignorados}

@app.get('/api/admin/usuarios')
def list_users(db: Session=Depends(get_db), _:Usuario=Depends(admin_user)):
    users=db.query(Usuario).order_by(Usuario.nome).all(); return [{'id':u.id,'nome':u.nome,'login':u.login,'tipo':u.tipo,'ativo':u.ativo,'turma_ids':[t.id for t in u.turmas]} for u in users]
@app.post('/api/admin/usuarios')
def create_user(payload:UserIn, db:Session=Depends(get_db), _:Usuario=Depends(admin_user)):
    login=payload.login.strip().lower()
    if len(payload.senha)<6: raise HTTPException(400,'A senha deve ter pelo menos 6 caracteres.')
    if payload.tipo not in ('admin','professor'): raise HTTPException(400,'Tipo inválido.')
    if db.query(Usuario).filter(Usuario.login==login).first(): raise HTTPException(409,'Este login já está cadastrado.')
    turmas=db.query(Turma).filter(Turma.id.in_(payload.turma_ids)).all() if payload.turma_ids else []
    u=Usuario(nome=payload.nome.strip(),login=login,senha_hash=hash_password(payload.senha),tipo=payload.tipo,ativo=True,turmas=turmas); db.add(u); db.commit(); db.refresh(u); return {'id':u.id}
@app.put('/api/admin/usuarios/{user_id}')
def update_user(user_id:int,payload:UserUpdate,db:Session=Depends(get_db),admin:Usuario=Depends(admin_user)):
    u=db.get(Usuario,user_id)
    if not u: raise HTTPException(404,'Usuário não encontrado.')
    login=payload.login.strip().lower(); existing=db.query(Usuario).filter(Usuario.login==login,Usuario.id!=user_id).first()
    if existing: raise HTTPException(409,'Este login já está cadastrado.')
    if payload.tipo not in ('admin','professor'): raise HTTPException(400,'Tipo inválido.')
    if user_id==admin.id and (payload.tipo!='admin' or not payload.ativo): raise HTTPException(400,'Você não pode remover seu próprio acesso de administrador.')
    u.nome=payload.nome.strip();u.login=login;u.tipo=payload.tipo;u.ativo=payload.ativo
    if payload.senha:
        if len(payload.senha)<6: raise HTTPException(400,'A senha deve ter pelo menos 6 caracteres.')
        u.senha_hash=hash_password(payload.senha)
    u.turmas=db.query(Turma).filter(Turma.id.in_(payload.turma_ids)).all() if payload.turma_ids else []
    db.commit(); return {'ok':True}



def _pdf_resultado(r: Resultado, turma: Turma) -> BytesIO:
    out = BytesIO()
    doc = SimpleDocTemplate(out, pagesize=A4, rightMargin=12*mm, leftMargin=12*mm, topMargin=12*mm, bottomMargin=12*mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle('SchoolTitle', parent=styles['Title'], alignment=TA_CENTER, fontSize=15, leading=18, spaceAfter=3)
    sub = ParagraphStyle('SchoolSub', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9, textColor=colors.HexColor('#555555'))
    small = ParagraphStyle('Small', parent=styles['Normal'], fontSize=7.5, leading=10)
    story = []
    logo = BASE_DIR / 'static' / 'logo-escola.png'
    if logo.exists():
        story += [RLImage(str(logo), width=28*mm, height=28*mm), Spacer(1, 1*mm)]
    story += [Paragraph('Colégio Estadual em Período Integral João Barbosa Reis', title), Paragraph('ScoreView - Relatório individual da prova', sub), Spacer(1, 5*mm)]
    info = [
        ['ID / chamada', r.aluno.numero_chamada or '—'], ['Matrícula', r.aluno.matricula], ['Aluno', r.aluno.nome],
        ['Turma', turma.nome], ['Status', r.aluno.status or 'ATIVO'], ['Prova / bloco', r.prova_nome],
        ['1ª chamada', 'PRESENTE' if r.presente_1 else ('AUSENTE' if r.ausente_1 else 'NÃO INFORMADO')],
        ['2ª chamada', 'PRESENTE' if r.presente_2 else ('AUSENTE' if r.ausente_2 else 'NÃO INFORMADO')],
        ['Acertos', str(r.acertos)], ['Erros', str(r.erros)], ['Anuladas', str(r.anuladas)], ['Em branco', str(r.em_branco)],
        ['Nota', f'{r.nota:.2f}'.replace('.', ',')], ['Data', r.criado_em.strftime('%d/%m/%Y %H:%M') if r.criado_em else '—'],
    ]
    table = Table(info, colWidths=[42*mm, 135*mm])
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),colors.HexColor('#f1f3f5')),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#d6d9dc')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('PADDING',(0,0),(-1,-1),5)]))
    story += [table, Spacer(1, 6*mm), Paragraph('Respostas da prova', ParagraphStyle('H', parent=styles['Heading2'], fontSize=12, leading=14, spaceAfter=4))]
    respostas = (r.respostas or '').split(',')
    gabarito = (r.gabarito or '').split(',')
    # No relatório individual, mostrar somente as questões efetivamente acertadas.
    # Questões erradas, em branco ou anuladas não aparecem nesta tabela.
    qrows = [['Questão','Resposta acertada']]
    for i in range(r.quantidade_questoes):
        ans = respostas[i].strip().upper() if i < len(respostas) and respostas[i].strip() else ''
        key = gabarito[i].strip().upper() if i < len(gabarito) and gabarito[i].strip() else ''
        if ans and ans != 'MULT' and key and ans == key:
            qrows.append([str(i+1), ans])
    if len(qrows) == 1:
        qrows.append(['—', 'Nenhuma questão acertada'])
    qt = Table(qrows, colWidths=[35*mm,55*mm], repeatRows=1)
    qt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#263746')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#d6d9dc')),('ALIGN',(0,0),(-1,-1),'CENTER'),('FONTSIZE',(0,0),(-1,-1),8),('PADDING',(0,0),(-1,-1),3)]))
    story += [qt, Spacer(1, 5*mm), Paragraph('Documento gerado pelo ScoreView. O ID/chamada é independente do identificador interno do banco e corresponde ao número do aluno na lista escolar.', small)]
    doc.build(story); out.seek(0); return out

@app.delete('/api/admin/usuarios/{user_id}')
def delete_user(user_id:int, db:Session=Depends(get_db), admin:Usuario=Depends(admin_user)):
    u=db.get(Usuario,user_id)
    if not u: raise HTTPException(404,'Usuário não encontrado.')
    if u.id==admin.id: raise HTTPException(400,'Você não pode excluir o usuário administrador que está em uso.')
    if u.tipo!='professor': raise HTTPException(400,'Por segurança, somente cadastros de professor podem ser excluídos por esta opção.')
    db.delete(u); db.commit(); return {'ok':True}

@app.delete('/api/resultados/{resultado_id}')
def delete_resultado(resultado_id:int, db:Session=Depends(get_db), user:Usuario=Depends(current_user)):
    r=db.get(Resultado,resultado_id)
    if not r: raise HTTPException(404,'Resultado não encontrado.')
    if not can_access_turma(user,r.aluno.turma_id): raise HTTPException(403,'Você não tem acesso a este resultado.')
    db.delete(r); db.commit(); return {'ok':True}

@app.get('/api/resultados/{resultado_id}/pdf')
def resultado_pdf(resultado_id:int, db:Session=Depends(get_db), user:Usuario=Depends(current_user)):
    r=db.get(Resultado,resultado_id)
    if not r: raise HTTPException(404,'Resultado não encontrado.')
    if not can_access_turma(user,r.aluno.turma_id): raise HTTPException(403,'Você não tem acesso a este resultado.')
    pdf=_pdf_resultado(r,r.aluno.turma)
    safe=''.join(c if c.isalnum() or c in '-_' else '_' for c in f'{r.aluno.nome}_{r.prova_nome}')[:100]
    return StreamingResponse(pdf, media_type='application/pdf', headers={'Content-Disposition':f'attachment; filename="relatorio_{safe}.pdf"'})

class ResultadoIn(BaseModel):
    aluno_id:int
    prova_nome:str='Prova'
    quantidade_questoes:int
    gabarito:list[str]
    questions:list[dict[str,Any]]
    presente_1:bool=False
    ausente_1:bool=False
    presente_2:bool=False
    ausente_2:bool=False

@app.post('/api/resultados')
def salvar_resultado(payload:ResultadoIn,db:Session=Depends(get_db),user:Usuario=Depends(current_user)):
    aluno=db.get(Aluno,payload.aluno_id)
    if not aluno: raise HTTPException(404,'Aluno não encontrado.')
    if not can_access_turma(user,aluno.turma_id): raise HTTPException(403,'Você não tem acesso a este aluno.')
    count=payload.quantidade_questoes
    if count not in (20,30,45): raise HTTPException(400,'Quantidade de questões inválida.')
    if payload.presente_1 and payload.ausente_1: raise HTTPException(400,'A 1ª chamada não pode ser presente e ausente ao mesmo tempo.')
    if payload.presente_2 and payload.ausente_2: raise HTTPException(400,'A 2ª chamada não pode ser presente e ausente ao mesmo tempo.')

    # Ausência pode ser registrada sem foto. Só permitimos esse modo quando
    # não existe nenhuma chamada marcada como presente, pois uma presença
    # exige a correção da prova para gerar o resultado.
    absent_only = (payload.ausente_1 or payload.ausente_2) and not (payload.presente_1 or payload.presente_2) and not payload.questions
    if absent_only:
        normalized_key = list(payload.gabarito or [])
        if len(normalized_key) != count:
            normalized_key = [''] * count
        result=Resultado(
            aluno_id=aluno.id,
            prova_nome=payload.prova_nome.strip() or 'Prova',
            quantidade_questoes=count,
            gabarito=','.join(normalized_key),
            respostas='',
            acertos=0,
            erros=0,
            anuladas=0,
            em_branco=0,
            nota=0,
            presente_1=payload.presente_1,
            ausente_1=payload.ausente_1,
            presente_2=payload.presente_2,
            ausente_2=payload.ausente_2,
        )
        db.add(result); db.commit(); db.refresh(result)
        return {'id':result.id,'acertos':0,'erros':0,'anuladas':0,'em_branco':0,'nota':0,'ausente_sem_foto':True}

    if len(payload.gabarito)!=count: raise HTTPException(400,'Quantidade/gabarito inválido.')
    qs=sorted(payload.questions,key=lambda q:int(q.get('number',0)))[:count]
    if len(qs)<count: raise HTTPException(400,'Leitura incompleta do cartão.')
    correct=mult=blank=0;answers=[]
    for i,q in enumerate(qs):
        status=q.get('status');answer=q.get('answer') if status=='OK' else None;answers.append(answer or ('MULT' if status=='MULT' else ''))
        if status=='MULT':mult+=1
        elif status=='BLANK':blank+=1
        if status=='OK' and answer==payload.gabarito[i]:correct+=1
    wrong=count-correct
    nota=round(correct/count*10,2)
    result=Resultado(aluno_id=aluno.id,prova_nome=payload.prova_nome.strip() or 'Prova',quantidade_questoes=count,gabarito=','.join(payload.gabarito),respostas=','.join(answers),acertos=correct,erros=wrong,anuladas=mult,em_branco=blank,nota=nota,presente_1=payload.presente_1,ausente_1=payload.ausente_1,presente_2=payload.presente_2,ausente_2=payload.ausente_2)
    db.add(result);db.commit();db.refresh(result);return {'id':result.id,'acertos':correct,'erros':wrong,'anuladas':mult,'em_branco':blank,'nota':nota}

def _turma_resultados(db: Session, turma_id: int, prova_nome: str | None = None):
    query = db.query(Resultado).join(Aluno).filter(Aluno.turma_id == turma_id)
    if prova_nome:
        query = query.filter(Resultado.prova_nome == prova_nome)
    return query.order_by(Aluno.nome, Resultado.criado_em.desc()).all()

def _turma_report_rows(db: Session, turma_id: int, prova_nome: str | None = None):
    """Return one row per enrolled student, keeping the latest matching result when available."""
    alunos = db.query(Aluno).filter(Aluno.turma_id == turma_id).order_by(Aluno.nome).all()
    results = _turma_resultados(db, turma_id, prova_nome)
    latest = {}
    for r in results:
        if r.aluno_id not in latest:
            latest[r.aluno_id] = r
    return [(a, latest.get(a.id)) for a in alunos]

def _diagnostico_turma(resultados):
    if not resultados:
        return {'total_resultados':0,'alunos_com_resultado':0,'media_nota':0,'aproveitamento':0,'media_acertos':0,'media_erros':0,'media_brancos':0,'media_anuladas':0,'distribuicao':[],'questoes':[],'texto':'Ainda não há resultados suficientes para gerar um diagnóstico.'}
    alunos=len({r.aluno_id for r in resultados})
    media_nota=sum(r.nota for r in resultados)/len(resultados)
    media_acertos=sum(r.acertos for r in resultados)/len(resultados)
    media_erros=sum(r.erros for r in resultados)/len(resultados)
    media_brancos=sum(r.em_branco for r in resultados)/len(resultados)
    media_anuladas=sum(r.anuladas for r in resultados)/len(resultados)
    aproveitamento=sum((r.acertos/r.quantidade_questoes*100) if r.quantidade_questoes else 0 for r in resultados)/len(resultados)
    faixas={'0–39%':0,'40–59%':0,'60–79%':0,'80–100%':0}
    for r in resultados:
        pct=(r.acertos/r.quantidade_questoes*100) if r.quantidade_questoes else 0
        if pct<40: faixas['0–39%']+=1
        elif pct<60: faixas['40–59%']+=1
        elif pct<80: faixas['60–79%']+=1
        else: faixas['80–100%']+=1
    questoes=[]
    if len({r.prova_nome for r in resultados})==1:
        maxq=max((r.quantidade_questoes for r in resultados),default=0)
        for i in range(maxq):
            attempted=correct=blank=multi=0
            for r in resultados:
                if i>=r.quantidade_questoes: continue
                rs=(r.respostas or '').split(','); gs=(r.gabarito or '').split(',')
                ans=rs[i].strip().upper() if i<len(rs) else ''; key=gs[i].strip().upper() if i<len(gs) else ''
                attempted+=1
                if ans=='MULT': multi+=1
                elif not ans: blank+=1
                elif key and ans==key: correct+=1
            if attempted:
                questoes.append({'questao':i+1,'respostas':attempted,'acertos':correct,'percentual':round(correct/attempted*100,1),'brancos':blank,'anuladas':multi})
    fortes=sorted(questoes,key=lambda x:(-x['percentual'],x['questao']))[:3]
    atencao=sorted(questoes,key=lambda x:(x['percentual'],x['questao']))[:3]
    if questoes:
        fortes_txt=', '.join(f"Q{x['questao']} ({x['percentual']:.0f}%)" for x in fortes)
        atencao_txt=', '.join(f"Q{x['questao']} ({x['percentual']:.0f}%)" for x in atencao)
        texto=(f"A turma apresentou aproveitamento médio de {aproveitamento:.1f}%. Como pontos de maior domínio, destacam-se {fortes_txt}. "
               f"As questões que merecem retomada ou reforço são {atencao_txt}. A média de questões em branco foi {media_brancos:.1f} por resultado e a média de anuladas foi {media_anuladas:.1f}.")
    else:
        texto=(f"A turma apresentou aproveitamento médio de {aproveitamento:.1f}%. A média foi {media_nota:.2f} e houve, em média, {media_brancos:.1f} questões em branco por resultado. "
               "Para um diagnóstico por questão, selecione uma única prova no relatório.")
    return {'total_resultados':len(resultados),'alunos_com_resultado':alunos,'media_nota':round(media_nota,2),'aproveitamento':round(aproveitamento,1),'media_acertos':round(media_acertos,2),'media_erros':round(media_erros,2),'media_brancos':round(media_brancos,2),'media_anuladas':round(media_anuladas,2),'distribuicao':[{'faixa':k,'quantidade':v} for k,v in faixas.items()],'questoes':questoes,'texto':texto}

def _pdf_relatorio_turma(turma, resultados, diagnostico, prova_nome=None, db=None):
    from reportlab.lib.pagesizes import landscape
    out=BytesIO()
    doc=SimpleDocTemplate(out,pagesize=landscape(A3),rightMargin=7*mm,leftMargin=7*mm,topMargin=9*mm,bottomMargin=9*mm)
    styles=getSampleStyleSheet(); title=ParagraphStyle('RTTitle',parent=styles['Title'],alignment=TA_CENTER,fontSize=14,leading=16,spaceAfter=2); sub=ParagraphStyle('RTSub',parent=styles['Normal'],alignment=TA_CENTER,fontSize=8,textColor=colors.HexColor('#555555')); h=ParagraphStyle('RTH',parent=styles['Heading2'],fontSize=10,leading=12,spaceBefore=5,spaceAfter=4)
    story=[Paragraph('Colégio Estadual em Período Integral João Barbosa Reis',title),Paragraph(f'ScoreView - Relatório da turma · {turma.nome} · {prova_nome or "Todas as provas"}',sub),Spacer(1,4*mm)]
    if not prova_nome:
        story += [Paragraph('Para exportação no formato de migração, selecione uma prova/bloco específica. Este relatório reúne os resultados salvos quando nenhuma prova é filtrada.', sub), Spacer(1,3*mm)]
    info=[['Resultados',str(diagnostico['total_resultados']), 'Alunos com resultado',str(diagnostico['alunos_com_resultado']), 'Média',f"{diagnostico['media_nota']:.2f}".replace('.',','), 'Aproveitamento',f"{diagnostico['aproveitamento']:.1f}%"]]
    it=Table(info,colWidths=[25*mm,22*mm,32*mm,22*mm,18*mm,20*mm,32*mm,25*mm]); it.setStyle(TableStyle([('BACKGROUND',(0,0),(0,0),colors.HexColor('#e9ecef')),('BACKGROUND',(2,0),(2,0),colors.HexColor('#e9ecef')),('BACKGROUND',(4,0),(4,0),colors.HexColor('#e9ecef')),('BACKGROUND',(6,0),(6,0),colors.HexColor('#e9ecef')),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#d6d9dc')),('ALIGN',(1,0),(-1,-1),'CENTER'),('FONTSIZE',(0,0),(-1,-1),7.5),('PADDING',(0,0),(-1,-1),4)])); story += [it,Spacer(1,4*mm)]
    # Each result becomes one SIAP-oriented row.
    headers=['ID','MATRÍCULA','NOME DO ALUNO','STATUS','PRES. 1ª','AUS. 1ª','PRES. 2ª','AUS. 2ª']+[f'Q{i}' for i in range(1,46)]+['NOTA']
    rows=[headers]
    for aluno, r in _turma_report_rows(db, turma.id, prova_nome):
        if r is None:
            rows.append([aluno.numero_chamada or '—',aluno.matricula,aluno.nome,aluno.status or 'ATIVO','','','','']+['—']*45+['—'])
            continue
        answers=(r.respostas or '').split(',')
        keys=(r.gabarito or '').split(',')
        qcells=[]
        for i in range(45):
            ans = answers[i].strip().upper() if i < r.quantidade_questoes and i < len(answers) and answers[i].strip() else ''
            key = keys[i].strip().upper() if i < r.quantidade_questoes and i < len(keys) and keys[i].strip() else ''
            # No relatório da turma, cada Qn só recebe a resposta quando ela foi acertada.
            qcells.append(ans if ans and ans != 'MULT' and key and ans == key else '')
        rows.append([aluno.numero_chamada or '—',aluno.matricula,aluno.nome,aluno.status or 'ATIVO','X' if r.presente_1 else '', 'X' if r.ausente_1 else '', 'X' if r.presente_2 else '', 'X' if r.ausente_2 else '']+qcells+[f'{r.nota:.2f}'.replace('.',',')])
    if len(rows)==1:
        rows.append(['—','—','Nenhum resultado','','','','','']+['—']*45+['—'])
    widths=[10*mm,24*mm,42*mm,19*mm,12*mm,12*mm,12*mm,12*mm]+[5.1*mm]*45+[13*mm]
    rt=Table(rows,colWidths=widths,repeatRows=1,splitByRow=1)
    rt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#263746')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('GRID',(0,0),(-1,-1),.25,colors.HexColor('#cfd4d8')),('ALIGN',(0,0),(-1,-1),'CENTER'),('FONTSIZE',(0,0),(-1,-1),4.7),('LEADING',(0,0),(-1,-1),5.2),('PADDING',(0,0),(-1,-1),2),('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    story += [Paragraph('Dados da prova',h),rt,Spacer(1,3*mm),Paragraph('Estrutura: ID/chamada · matrícula · nome · status escolar · presença/ausência nas duas chamadas · Q1–Q45 · nota. Nas colunas Q1–Q45 aparece somente a alternativa quando o aluno acertou a questão; erros, brancos e anuladas ficam em branco.',sub)]
    doc.build(story); out.seek(0); return out


def _normalize_numero_chamada(value):
    """Normaliza o ID/número da chamada sem alterar IDs textuais válidos."""
    raw = str(value or '').strip()
    if not raw:
        return ''
    try:
        number = float(raw.replace(',', '.'))
        if number.is_integer():
            return str(int(number))
    except ValueError:
        pass
    return raw


def _numero_chamada_sort_key(value):
    """Ordenação compatível com a chamada do SIAP: 1, 2, 3... 10, 11..."""
    raw = _normalize_numero_chamada(value)
    try:
        return (0, int(raw), '')
    except ValueError:
        return (1, 10**9, raw.casefold())


def _siap_rows(db: Session, turma_id: int, prova_nome: str):
    # O SIAP apresenta os alunos pela ordem da chamada. Não usamos ordem alfabética
    # nem ordenação textual do banco, pois ela colocaria 10 antes de 2.
    alunos = db.query(Aluno).filter(Aluno.turma_id == turma_id).all()
    alunos.sort(key=lambda a: (_numero_chamada_sort_key(a.numero_chamada), a.nome.casefold()))

    resultados = _turma_resultados(db, turma_id, prova_nome)
    latest = {}
    for r in resultados:
        if r.aluno_id not in latest:
            latest[r.aluno_id] = r

    rows = []
    for aluno in alunos:
        r = latest.get(aluno.id)
        if r is None:
            rows.append({
                'resultado_id': None,
                'aluno_id': aluno.id,
                'numero_chamada': _normalize_numero_chamada(aluno.numero_chamada),
                'nome': aluno.nome,
                'presente_1': False, 'ausente_1': False,
                'presente_2': False, 'ausente_2': False,
                'quantidade_questoes': 0,
                'acertos': 0,
                'percentual': None,
                'acertos_questoes': [],
                'tem_resultado': False,
            })
            continue

        respostas = (r.respostas or '').split(',')
        gabarito = (r.gabarito or '').split(',')
        acertos_questoes = []
        for i in range(r.quantidade_questoes):
            ans = respostas[i].strip().upper() if i < len(respostas) else ''
            key = gabarito[i].strip().upper() if i < len(gabarito) else ''
            if ans and ans != 'MULT' and key and ans == key:
                acertos_questoes.append(i + 1)

        rows.append({
            'resultado_id': r.id,
            'aluno_id': aluno.id,
            'numero_chamada': _normalize_numero_chamada(aluno.numero_chamada),
            'nome': aluno.nome,
            'presente_1': r.presente_1, 'ausente_1': r.ausente_1,
            'presente_2': r.presente_2, 'ausente_2': r.ausente_2,
            'quantidade_questoes': r.quantidade_questoes,
            'acertos': r.acertos,
            'percentual': round((r.acertos / r.quantidade_questoes) * 100, 2) if r.quantidade_questoes else None,
            'acertos_questoes': acertos_questoes,
            'tem_resultado': True,
        })
    return rows

@app.get('/api/turmas/{turma_id}/siap')
def siap_preview(turma_id: int, prova_nome: str, db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    turma = db.get(Turma, turma_id)
    if not turma:
        raise HTTPException(404, 'Turma não encontrada.')
    if not can_access_turma(user, turma_id):
        raise HTTPException(403, 'Você não tem acesso a esta turma.')
    prova_nome = prova_nome.strip()
    if not prova_nome:
        raise HTTPException(400, 'Selecione uma prova/bloco.')
    rows = _siap_rows(db, turma_id, prova_nome)
    ids = [str(x.get('numero_chamada') or '').strip() for x in rows]
    missing_ids = [x['nome'] for x in rows if not str(x.get('numero_chamada') or '').strip()]
    duplicate_ids = sorted({value for value in ids if value and ids.count(value) > 1}, key=_numero_chamada_sort_key)
    counts = {
        'alunos': len(rows),
        'com_resultado': sum(1 for x in rows if x['tem_resultado']),
        'presentes_1': sum(1 for x in rows if x['presente_1']),
        'ausentes_1': sum(1 for x in rows if x['ausente_1']),
        'presentes_2': sum(1 for x in rows if x['presente_2']),
        'ausentes_2': sum(1 for x in rows if x['ausente_2']),
    }
    max_q = max((x['quantidade_questoes'] for x in rows if x['tem_resultado']), default=0)
    return {
        'turma': {'id': turma.id, 'nome': turma.nome},
        'prova': prova_nome,
        'quantidade_questoes': max_q,
        'resumo': counts,
        'resultados': rows,
        'validacao': {
            'ok': not missing_ids and not duplicate_ids,
            'ids_ausentes': missing_ids,
            'ids_duplicados': duplicate_ids,
        },
    }

@app.get('/api/turmas/{turma_id}/provas')
def listar_provas_turma(turma_id:int, db:Session=Depends(get_db), user:Usuario=Depends(current_user)):
    turma=db.get(Turma,turma_id)
    if not turma: raise HTTPException(404,'Turma não encontrada.')
    if not can_access_turma(user,turma_id): raise HTTPException(403,'Você não tem acesso a esta turma.')
    return [x[0] for x in db.query(Resultado.prova_nome).join(Aluno).filter(Aluno.turma_id==turma_id).distinct().order_by(Resultado.prova_nome).all()]

@app.get('/api/turmas/{turma_id}/relatorio')
def relatorio(turma_id:int,prova_nome:str|None=None,db:Session=Depends(get_db),user:Usuario=Depends(current_user)):
    turma=db.get(Turma,turma_id)
    if not turma: raise HTTPException(404,'Turma não encontrada.')
    if not can_access_turma(user,turma_id): raise HTTPException(403,'Você não tem acesso a esta turma.')
    resultados=_turma_resultados(db,turma_id,prova_nome); diagnostico=_diagnostico_turma(resultados)
    rows=[]
    for aluno,r in _turma_report_rows(db,turma_id,prova_nome):
        if r is None:
            rows.append({'id':None,'aluno':aluno.nome,'numero_chamada':aluno.numero_chamada,'matricula':aluno.matricula,'status':aluno.status or 'ATIVO','presente_1':False,'ausente_1':False,'presente_2':False,'ausente_2':False,'prova':prova_nome or '—','questoes':0,'respostas':[],'gabarito':[],'acertos':0,'erros':0,'anuladas':0,'em_branco':0,'nota':None,'data':None})
        else:
            rows.append({'id':r.id,'aluno':aluno.nome,'numero_chamada':aluno.numero_chamada,'matricula':aluno.matricula,'status':aluno.status or 'ATIVO','presente_1':r.presente_1,'ausente_1':r.ausente_1,'presente_2':r.presente_2,'ausente_2':r.ausente_2,'prova':r.prova_nome,'questoes':r.quantidade_questoes,'respostas':(r.respostas or '').split(','),'gabarito':(r.gabarito or '').split(','),'acertos':r.acertos,'erros':r.erros,'anuladas':r.anuladas,'em_branco':r.em_branco,'nota':r.nota,'data':r.criado_em.isoformat()})
    return {'turma':turma.nome,'prova':prova_nome or 'Todas as provas','diagnostico':diagnostico,'resultados':rows}

@app.get('/api/turmas/{turma_id}/relatorio/pdf')
def relatorio_turma_pdf(turma_id:int,prova_nome:str|None=None,db:Session=Depends(get_db),user:Usuario=Depends(current_user)):
    turma=db.get(Turma,turma_id)
    if not turma: raise HTTPException(404,'Turma não encontrada.')
    if not can_access_turma(user,turma_id): raise HTTPException(403,'Você não tem acesso a esta turma.')
    resultados=_turma_resultados(db,turma_id,prova_nome); diagnostico=_diagnostico_turma(resultados); pdf=_pdf_relatorio_turma(turma,resultados,diagnostico,prova_nome,db)
    safe=''.join(c if c.isalnum() or c in '-_' else '_' for c in f'{turma.nome}_{prova_nome or "todas"}')[:100]
    return StreamingResponse(pdf,media_type='application/pdf',headers={'Content-Disposition':f'inline; filename="relatorio_turma_{safe}.pdf"'})
