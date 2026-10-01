
const viewTitles={home:'Visão geral',scanner:'Corrigir prova',reports:'Relatórios',siap:'SIAP / GPA',students:'Alunos e turmas',users:'Professores'};
function openView(name){document.querySelectorAll('[data-view-panel]').forEach(x=>x.classList.toggle('active',x.dataset.viewPanel===name));document.querySelectorAll('.navBtn').forEach(x=>x.classList.toggle('active',x.dataset.view===name));const t=document.querySelector('#topTitle');if(t)t.textContent=viewTitles[name]||'TUPÃ';document.querySelector('#sidebar')?.classList.remove('open');window.scrollTo({top:0,behavior:'smooth'});}
document.querySelectorAll('.navBtn').forEach(b=>b.addEventListener('click',()=>openView(b.dataset.view)));
document.querySelectorAll('.quickNav').forEach(b=>b.addEventListener('click',()=>openView(b.dataset.target)));
document.querySelector('#menuToggle')?.addEventListener('click',()=>document.querySelector('#sidebar')?.classList.toggle('open'));

let currentUser=null;
let lastSavedResultId=null;
const loginScreen=document.querySelector('#loginScreen'), appScreen=document.querySelector('#appScreen'), loginBtn=document.querySelector('#loginBtn'), loginStatus=document.querySelector('#loginStatus');
async function apiFetch(url,opts={}){
  const options={...opts,headers:{...(opts.headers||{})}};
  if(!options.method || options.method.toUpperCase()==='GET'){options.cache='no-store';options.headers['Cache-Control']='no-cache';}
  const r=await fetch(url,options);
  if(r.status===401){showLogin();throw new Error('Sessão encerrada. Entre novamente.')}
  return r;
}
async function refreshData({students=true,report=true}={}){
  const selectedClass=classSelect.value;
  const selectedStudent=studentSelect.value;
  const selectedExam=reportExam.value;
  await loadClasses();
  await loadSiapClasses();
  if(currentUser?.tipo==='admin'){await loadAdminClasses();await loadUsers();}
  if(selectedClass && [...classSelect.options].some(o=>o.value===selectedClass)){
    classSelect.value=selectedClass;
    if(students){await loadStudents(); if(selectedStudent && [...studentSelect.options].some(o=>o.value===selectedStudent)) studentSelect.value=selectedStudent;}
    if(report){
      await loadReportExams();
      if(selectedExam && [...reportExam.options].some(o=>o.value===selectedExam)) reportExam.value=selectedExam;
      await showReport();
    }
  }else if(report){
    reportExam.innerHTML='<option value="">Todas as provas</option>';
    if(students){studentSelect.innerHTML='<option value="">Selecione a turma...</option>';studentSelect.disabled=true;}
    reportBody.innerHTML='';reportSummary.innerHTML='';diagnosticText.textContent='Selecione uma turma e atualize o relatório.';diagnosticQuestions.innerHTML='';
  }
}

function showLogin(){currentUser=null;appScreen.style.display='none';loginScreen.style.display='block';}
async function startApp(){
  try{const r=await fetch('/api/auth/me');if(!r.ok){showLogin();return;}currentUser=await r.json();loginScreen.style.display='none';appScreen.style.display='block';document.querySelector('#currentUserName').textContent=currentUser.nome;document.querySelector('#currentUserType').textContent=currentUser.tipo==='admin'?'Administrador':'Professor';document.querySelector('#adminImportCard').style.display=currentUser.tipo==='admin'?'block':'none';document.querySelector('#adminUsersCard').style.display=currentUser.tipo==='admin'?'block':'none';document.querySelectorAll('.adminNav').forEach(x=>x.style.display=currentUser.tipo==='admin'?'block':'none');await loadClasses();await loadSiapClasses();if(currentUser.tipo==='admin'){await loadUsers();await loadAdminClasses();}}catch(e){showLogin();}
}
loginBtn.addEventListener('click',async()=>{loginBtn.disabled=true;try{const r=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({login:document.querySelector('#loginUser').value,senha:document.querySelector('#loginPass').value})});const d=await r.json();if(!r.ok)throw new Error(d.detail||'Falha no login');loginStatus.style.display='none';await startApp();}catch(e){loginStatus.className='status error';loginStatus.textContent=e.message;loginStatus.style.display='block';}finally{loginBtn.disabled=false;}});
document.querySelector('#loginPass').addEventListener('keydown',e=>{if(e.key==='Enter')loginBtn.click();});
document.querySelector('#logoutBtn').addEventListener('click',async()=>{await fetch('/api/auth/logout',{method:'POST'});showLogin();});
const photo=document.querySelector('#photo'), preview=document.querySelector('#preview'), scanBtn=document.querySelector('#scan'), statusBox=document.querySelector('#status');
const resultCard=document.querySelector('#resultCard'), questionsBox=document.querySelector('#questions'), summary=document.querySelector('#summary'), keyBox=document.querySelector('#key'), keyInfo=document.querySelector('#keyInfo'), questionCountBox=document.querySelector('#questionCount'), reviewBox=document.querySelector('#reviewBox'), confirmReview=document.querySelector('#confirmReview');
let file=null, lastResult=null, reviewConfirmed=false, reviewSelections={};
const classSelect=document.querySelector('#classSelect'), studentSelect=document.querySelector('#studentSelect'), examName=document.querySelector('#examName'), saveResultBtn=document.querySelector('#saveResult'), saveStatus=document.querySelector('#saveStatus'), attendance1=document.querySelector('#attendance1'), attendance2=document.querySelector('#attendance2'), absenceSaveNotice=document.querySelector('#absenceSaveNotice');
const studentsFile=document.querySelector('#studentsFile'), importStudents=document.querySelector('#importStudents'), importStatus=document.querySelector('#importStatus'), loadReport=document.querySelector('#loadReport'), reportBody=document.querySelector('#reportBody'), reportSummary=document.querySelector('#reportSummary'), reportExam=document.querySelector('#reportExam'), diagnosticText=document.querySelector('#diagnosticText'), diagnosticQuestions=document.querySelector('#diagnosticQuestions'), exportClassPdf=document.querySelector('#exportClassPdf');
const siapClass=document.querySelector('#siapClass'), siapExam=document.querySelector('#siapExam'), siapDiscipline=document.querySelector('#siapDiscipline'), siapBimestre=document.querySelector('#siapBimestre'), prepareSiap=document.querySelector('#prepareSiap'), copySiap=document.querySelector('#copySiap'), copySiapGrid=document.querySelector('#copySiapGrid'), siapStatus=document.querySelector('#siapStatus'), siapResultCard=document.querySelector('#siapResultCard'), siapSummary=document.querySelector('#siapSummary'), siapHead=document.querySelector('#siapHead'), siapBody=document.querySelector('#siapBody'), pluginGpaCompatBody=document.querySelector('#pluginGpaCompatBody');
let lastSiapData=null;
let lastSiapViewData=null;

const KEY_STORAGE_PREFIX='eduscanner_gabarito_';
const COUNT_STORAGE='eduscanner_quantidade_questoes';

function parseKey(){
  return keyBox.value.toUpperCase().replace(/[^A-E]/g,'').split('');
}

function selectedCount(){
  return Number(questionCountBox.value);
}

function storageKey(){
  return KEY_STORAGE_PREFIX + selectedCount();
}

function updateKeyState(){
  const key=parseKey();
  const count=selectedCount();
  localStorage.setItem(COUNT_STORAGE,String(count));
  localStorage.setItem(storageKey(),key.join(''));
  keyInfo.style.display='block';
  if(key.length===count){
    keyInfo.className='status ok';
    keyInfo.textContent=`✓ Gabarito válido: ${count}/${count} respostas. As questões ${count+1}–45 serão ignoradas.`;
  } else {
    keyInfo.className='status error';
    keyInfo.textContent=`Gabarito incompleto: ${key.length}/${count} respostas. Informe exatamente ${count} alternativas (A–E).`;
  }
  scanBtn.disabled=!file || key.length!==count;
  if(lastResult && key.length===count) render(lastResult);
}

const savedCount=localStorage.getItem(COUNT_STORAGE);
if(['20','30','45'].includes(savedCount)) questionCountBox.value=savedCount;
keyBox.value=localStorage.getItem(storageKey())||'';
updateKeyState();

photo.addEventListener('change',()=>{
  file=photo.files?.[0]||null;
  if(!file)return;
  // Cada nova foto inicia uma nova leitura. Nunca reutilizar o resultado anterior.
  if(preview.src && preview.src.startsWith('blob:')) URL.revokeObjectURL(preview.src);
  preview.src=URL.createObjectURL(file);
  preview.style.display='block';
  statusBox.style.display='none';
  resultCard.style.display='none';
  lastResult=null;
  reviewConfirmed=false;
  reviewSelections={};
  reviewBox.style.display='none';
  confirmReview.style.display='none';
  saveStatus.style.display='none';
  lastSavedResultId=null;
  document.querySelector('#exportSavedPdf').style.display='none';
  updateKeyState();
});

function render(data){
  lastResult=data;
  const key=parseKey();
  const count=selectedCount();
  if(key.length!==count){
    statusBox.className='status error';
    statusBox.textContent=`Não foi possível corrigir: o gabarito tem ${key.length}/${count} respostas.`;
    statusBox.style.display='block';
    resultCard.style.display='none';
    return;
  }

  let correct=0, wrong=0, mult=0, blank=0;
  questionsBox.innerHTML='';
  const lowQuestions=[];
  const allQuestions=data.questions.filter(q=>q.number<=count);

  allQuestions.forEach(q=>{
    const el=document.createElement('div');
    el.className='q';
    const expected=key[q.number-1];
    const label=q.answer || (q.status==='MULT'?'ANULADA':'—');

    if(q.status==='MULT'){el.classList.add('mult'); mult++;}
    if(q.status==='BLANK'){el.classList.add('blank'); blank++;}

    const isCorrect=q.status==='OK' && q.answer===expected;
    if(isCorrect){ correct++; el.classList.add('correct'); }
    else { wrong++; el.classList.add('wrong'); }

    const low=Array.isArray(data.low_confidence_questions) && data.low_confidence_questions.includes(q.number);
    if(low){el.classList.add('lowconf'); lowQuestions.push(q.number);}

    const detail=isCorrect ? '✓ CERTA' : `✗ ERRADA · correta: ${expected}`;
    const conf=(q.confidence!=null && q.status==='OK') ? `<small style="display:block;margin-top:3px;opacity:.75">Confiança: ${Math.round(q.confidence*100)}%</small>` : '';
    const reviewTag=Object.prototype.hasOwnProperty.call(reviewSelections,q.number) ? `<small style="display:block;margin-top:3px;color:#16733a;font-weight:800">✓ Revisada manualmente</small>` : '';
    el.innerHTML=`<b>Questão ${q.number}</b><span class="ans">${label}</span><small style="display:block;margin-top:4px;font-weight:700">${detail}</small>${conf}${reviewTag}`;
    questionsBox.appendChild(el);
  });

  if(lowQuestions.length){
    reviewBox.style.display='block';
    const pending=lowQuestions.filter(n=>!Object.prototype.hasOwnProperty.call(reviewSelections,n));
    reviewBox.innerHTML=`
      <b>⚠️ Revisão manual das questões com baixa confiança</b>
      <div class="reviewIntro">Confira essas questões diretamente na foto. Para cada uma, selecione a alternativa que o aluno realmente marcou. Se não houver marca válida, use <b>Em branco</b>; se houver mais de uma marca, use <b>Anulada</b>.</div>
      <div class="reviewList">
        ${lowQuestions.map(number=>{
          const q=allQuestions.find(x=>x.number===number);
          const current=q?.answer || (q?.status==='MULT'?'MULT':q?.status==='BLANK'?'BLANK':'');
          const shown=Object.prototype.hasOwnProperty.call(reviewSelections,number) ? reviewSelections[number] : current;
          const expected=key[number-1];
          return `<div class="reviewItem">
            <div class="reviewItemHead"><strong>Questão ${number}</strong><span class="reviewMeta">Scanner: ${current || '—'} · Gabarito: ${expected}</span></div>
            <div class="reviewChoices" data-review-number="${number}">
              ${['A','B','C','D','E'].map(letter=>`<button type="button" class="reviewChoice ${shown===letter?'active':''}" data-review-answer="${letter}">${letter}</button>`).join('')}
              <button type="button" class="reviewChoice blankChoice ${shown==='BLANK'?'active':''}" data-review-answer="BLANK">Em branco</button>
              <button type="button" class="reviewChoice multChoice ${shown==='MULT'?'active':''}" data-review-answer="MULT">Anulada</button>
            </div>
            ${Object.prototype.hasOwnProperty.call(reviewSelections,number)?'<div class="reviewDone">✓ Conferida pelo professor</div>':''}
          </div>`;
        }).join('')}
      </div>
      <div style="margin-top:10px;font-size:12px;font-weight:700">${pending.length ? `Ainda falta conferir: ${pending.join(', ')}.` : '✓ Todas as questões sinalizadas foram conferidas. O salvamento está liberado.'}</div>
    `;
    reviewBox.querySelectorAll('[data-review-answer]').forEach(btn=>{
      btn.addEventListener('click',()=>{
        const number=Number(btn.closest('[data-review-number]').dataset.reviewNumber);
        applyReview(number,btn.dataset.reviewAnswer);
      });
    });
    confirmReview.style.display=pending.length ? 'none' : 'block';
    confirmReview.textContent='✓ Confirmar revisão e liberar salvamento';
    saveResultBtn.disabled=Boolean(pending.length) || !studentSelect.value;
  }else{
    reviewBox.style.display='none';
    confirmReview.style.display='none';
    saveResultBtn.disabled=!studentSelect.value;
  }

  summary.innerHTML='';
  [`Acertos: ${correct}`,`Erros: ${wrong}`,`Anuladas: ${mult}`,`Em branco: ${blank}`,`Nota: ${(correct/count*10).toFixed(1)}`].forEach(t=>{
    const p=document.createElement('span'); p.className='pill'; p.textContent=t; summary.appendChild(p);
  });
  resultCard.style.display='block';
  if(!lowQuestions.length) saveResultBtn.disabled=!studentSelect.value;
  saveStatus.style.display='none'; lastSavedResultId=null; document.querySelector('#exportSavedPdf').style.display='none';
  resultCard.scrollIntoView({behavior:'smooth',block:'start'});
}

function applyReview(number,value){
  if(!lastResult)return;
  const q=lastResult.questions.find(x=>Number(x.number)===number);
  if(!q)return;
  if(value==='BLANK'){ q.status='BLANK'; q.answer=null; }
  else if(value==='MULT'){ q.status='MULT'; q.answer=null; }
  else { q.status='OK'; q.answer=value; }
  reviewSelections[number]=value;
  render(lastResult);
}

keyBox.addEventListener('input',updateKeyState);
questionCountBox.addEventListener('change',()=>{
  keyBox.value=localStorage.getItem(storageKey())||'';
  resultCard.style.display='none';
  lastResult=null;
  updateKeyState();
});

scanBtn.addEventListener('click',async()=>{
  const key=parseKey();
  const count=selectedCount();
  if(!file)return;
  if(key.length!==count){
    statusBox.className='status error';
    statusBox.textContent=`Informe o gabarito completo antes de corrigir (${key.length}/${count}).`;
    statusBox.style.display='block';
    return;
  }

  scanBtn.disabled=true;
  scanBtn.textContent='Lendo...';
  statusBox.style.display='none';
  resultCard.style.display='none';
  const form=new FormData();
  form.append('file',file);
  try{
    const res=await apiFetch('/api/scan',{method:'POST',body:form});
    const data=await res.json();
    if(!res.ok)throw new Error(data.detail||'Erro na leitura');
    statusBox.className='status ok';
    statusBox.textContent='Cartão lido e corrigido com sucesso.';
    statusBox.style.display='block';
    render(data);
  }catch(e){
    statusBox.className='status error';
    statusBox.textContent=e.message;
    statusBox.style.display='block';
    resultCard.style.display='none';
  }finally{
    scanBtn.textContent='Ler e corrigir respostas';
    updateKeyState();
  }
});

async function loadClasses(){
  const res=await apiFetch('/api/turmas'); const items=await res.json();
  classSelect.innerHTML='<option value="">Selecione...</option>'+items.map(t=>`<option value="${t.id}">${t.nome} (${t.total_alunos})</option>`).join('');
}
async function loadAdminClasses(){
  if(!currentUser || currentUser.tipo!=='admin') return;
  const body=document.querySelector('#classesAdminBody');
  try{
    const res=await apiFetch('/api/turmas'); const items=await res.json();
    body.innerHTML=items.length?items.map(t=>`<tr><td><b>${t.nome}</b></td><td>${t.total_alunos}</td><td><button class="deleteClass btn secondary" data-id="${t.id}" data-name="${String(t.nome).replace(/"/g,'&quot;')}" data-total="${t.total_alunos}" style="width:auto;padding:7px 9px;margin:0">Excluir turma</button></td></tr>`).join(''):'<tr><td colspan="3">Nenhuma turma cadastrada.</td></tr>';
    body.querySelectorAll('.deleteClass').forEach(b=>b.addEventListener('click',async()=>{
      const total=Number(b.dataset.total||0);
      const msg=`Excluir a turma "${b.dataset.name}"?\n\nEsta ação é permanente e removerá ${total} aluno(s), resultados de provas e vínculos de professores desta turma.\n\nEssa ação não pode ser desfeita.`;
      if(!confirm(msg)) return;
      b.disabled=true; b.textContent='Excluindo...';
      try{
        const r=await apiFetch(`/api/admin/turmas/${b.dataset.id}`,{method:'DELETE'}); const d=await r.json();
        if(!r.ok) throw new Error(d.detail||'Erro ao excluir turma');
        const st=document.querySelector('#classDeleteStatus'); st.className='status ok'; st.textContent=`Turma "${d.nome}" excluída. ${d.alunos_excluidos||0} aluno(s) removido(s).`; st.style.display='block';
        await refreshData({students:true,report:true});
        if(classSelect.value===b.dataset.id){classSelect.value=''; await refreshData({students:true,report:true});}
      }catch(e){alert(e.message); b.disabled=false; b.textContent='Excluir turma';}
    }));
  }catch(e){body.innerHTML='<tr><td colspan="3">Não foi possível carregar as turmas.</td></tr>';}
}
async function loadStudents(){
  const id=classSelect.value; studentSelect.disabled=!id; saveResultBtn.disabled=true;
  if(!id){studentSelect.innerHTML='<option value="">Selecione a turma...</option>';return;}
  const res=await apiFetch(`/api/turmas/${id}/alunos`); const items=await res.json();
  studentSelect.innerHTML='<option value="">Selecione o aluno...</option>'+items.map(a=>`<option value="${a.id}">${a.numero_chamada ? a.numero_chamada+' · ' : ''}${a.nome} · ${a.matricula} · ${a.status||'ATIVO'}</option>`).join('');
}

function isAbsenceOnlyMode(){
  return (attendance1.value==='absent' || attendance2.value==='absent') && attendance1.value!=='present' && attendance2.value!=='present';
}

function updateAbsenceSaveState(){
  const absenceOnly=isAbsenceOnlyMode();
  if(absenceSaveNotice) absenceSaveNotice.style.display=absenceOnly?'block':'none';
  if(absenceOnly && studentSelect.value && !lastResult){
    resultCard.style.display='block';
    questionsBox.innerHTML='<div class="guide" style="grid-column:1/-1"><b>Aluno ausente.</b><br>Nenhuma foto é necessária. Ao salvar, o ScoreView registrará apenas a frequência e manterá as questões sem lançamento.</div>';
    summary.innerHTML='<span class="pill">Ausente — sem correção</span>';
    reviewBox.style.display='none';
    confirmReview.style.display='none';
    saveResultBtn.disabled=!studentSelect.value || !examName.value;
  } else if(!absenceOnly && !lastResult){
    if(absenceSaveNotice) absenceSaveNotice.style.display='none';
    if(resultCard.style.display==='block' && questionsBox.querySelector('.guide')?.textContent.includes('Aluno ausente.')){
      resultCard.style.display='none';
      questionsBox.innerHTML='';
      summary.innerHTML='';
      saveResultBtn.disabled=true;
    }
  }
}

function clearCorrectionSession({clearStudent=true}={}){
  // Limpa completamente o estado da correção atual para evitar reaproveitar
  // foto, resultado ou aluno da correção anterior. A turma, bloco e gabarito
  // permanecem selecionados para agilizar a próxima correção.
  if(preview.src && preview.src.startsWith('blob:')) URL.revokeObjectURL(preview.src);
  preview.removeAttribute('src');
  preview.style.display='none';
  photo.value='';
  file=null;
  lastResult=null;
  reviewConfirmed=false;
  reviewSelections={};
  questionsBox.innerHTML='';
  summary.innerHTML='';
  reviewBox.innerHTML='';
  reviewBox.style.display='none';
  confirmReview.style.display='none';
  saveResultBtn.disabled=true;
  saveStatus.style.display='none';
  if(absenceSaveNotice) absenceSaveNotice.style.display='none';
  statusBox.style.display='none';
  lastSavedResultId=null;
  document.querySelector('#exportSavedPdf').style.display='none';
  if(clearStudent){
    studentSelect.value='';
  }
  updateKeyState();
}

studentSelect.addEventListener('change',()=>{
  // Ao trocar manualmente de aluno, nunca reaproveitar o resultado da foto anterior.
  if(lastResult){
    clearCorrectionSession({clearStudent:false});
  }
  saveResultBtn.disabled=!studentSelect.value || !lastResult;
  updateAbsenceSaveState();
});

attendance1.addEventListener('change',()=>{
  // Se o aluno estiver ausente, não exigimos foto. Se houver presença em qualquer chamada, a foto volta a ser obrigatória.
  updateAbsenceSaveState();
});
attendance2.addEventListener('change',()=>{
  updateAbsenceSaveState();
});
examName.addEventListener('change',()=>{
  updateAbsenceSaveState();
});
studentsFile.addEventListener('change',()=>{importStudents.disabled=!studentsFile.files?.[0];});
importStudents.addEventListener('click',async()=>{
  const f=studentsFile.files?.[0]; if(!f)return; importStudents.disabled=true; importStudents.textContent='Importando...';
  const fd=new FormData(); fd.append('file',f);
  try{const r=await apiFetch('/api/alunos/importar',{method:'POST',body:fd}); const d=await r.json(); if(!r.ok)throw new Error(d.detail||'Erro na importação'); importStatus.className='status ok'; importStatus.textContent=`Importação concluída: ${d.criados} novos, ${d.atualizados} atualizados, ${d.ignorados} ignorados.`; importStatus.style.display='block'; await refreshData({students:true,report:true});}
  catch(e){importStatus.className='status error'; importStatus.textContent=e.message; importStatus.style.display='block';}
  finally{importStudents.textContent='Importar planilha'; importStudents.disabled=false;}
});
confirmReview.addEventListener('click',()=>{
  reviewConfirmed=true;
  confirmReview.style.display='none';
  reviewBox.style.display='block';
  reviewBox.innerHTML='<b>✓ Revisão confirmada</b>As questões de baixa confiança foram conferidas manualmente. O resultado pode ser salvo.';
  saveResultBtn.disabled=!studentSelect.value;
});

saveResultBtn.addEventListener('click',async()=>{
  if(!studentSelect.value)return;
  const absenceOnly=isAbsenceOnlyMode();
  if(!absenceOnly && !lastResult)return;
  const key=parseKey(), count=selectedCount();
  if(!examName.value){saveStatus.textContent='Selecione o bloco da prova antes de salvar.';saveStatus.className='status error';return;}
  if(!absenceOnly && key.length!==count){saveStatus.textContent=`Informe o gabarito completo antes de salvar (${key.length}/${count}).`;saveStatus.className='status error';saveStatus.style.display='block';return;}
  const body={aluno_id:Number(studentSelect.value),prova_nome:examName.value,quantidade_questoes:count,gabarito:absenceOnly?(key.length===count?key:Array(count).fill('')):key,questions:absenceOnly?[],presente_1:attendance1.value==='present',ausente_1:attendance1.value==='absent',presente_2:attendance2.value==='present',ausente_2:attendance2.value==='absent'};
  saveResultBtn.disabled=true; saveResultBtn.textContent='Salvando...';
  try{
    const r=await apiFetch('/api/resultados',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const d=await r.json();
    if(!r.ok)throw new Error(d.detail||'Erro ao salvar');
    saveStatus.className='status ok';
    saveStatus.textContent=absenceOnly ? 'Ausência registrada com sucesso. Nenhuma foto foi necessária.' : `Resultado salvo. Nota: ${Number(d.nota).toFixed(2)} · ${d.acertos} acertos.`;
    saveStatus.style.display='block';
    lastSavedResultId=d.id;
    document.querySelector('#exportSavedPdf').style.display='block';
    await refreshData({students:true,report:true});
    await showReport();
    // Após salvar, encerra a sessão da correção atual. Isso evita que a próxima
    // foto ou aluno reutilize o estado anterior por cache/estado do navegador.
    clearCorrectionSession({clearStudent:true});
    // Mantém apenas a confirmação visual por alguns segundos.
    saveStatus.className='status ok';
    saveStatus.textContent=absenceOnly ? '✓ Ausência registrada. Pronto para a próxima correção.' : `✓ Resultado salvo. Nota: ${Number(d.nota).toFixed(2)} · ${d.acertos} acertos. Pronto para a próxima correção.`;
    saveStatus.style.display='block';
  }
  catch(e){saveStatus.className='status error';saveStatus.textContent=e.message;saveStatus.style.display='block';}
  finally{saveResultBtn.textContent='💾 Salvar resultado do aluno';saveResultBtn.disabled=!studentSelect.value || (!lastResult && !isAbsenceOnlyMode());}
});
async function loadReportExams(){
  if(!classSelect.value){reportExam.innerHTML='<option value="">Todas as provas</option>';return;}
  const r=await apiFetch(`/api/turmas/${classSelect.value}/provas`); const provas=await r.json();
  const current=reportExam.value; reportExam.innerHTML='<option value="">Todas as provas</option>'+provas.map(p=>`<option value="${String(p).replace(/"/g,'&quot;')}">${p}</option>`).join('');
  if(provas.includes(current)) reportExam.value=current;
}
function renderDiagnostic(d){
  const x=d||{}; reportSummary.innerHTML=`<div class="diagnosticGrid" style="width:100%"><div class="diagnosticCard"><span>Alunos com resultado</span><strong>${x.alunos_com_resultado||0}</strong></div><div class="diagnosticCard"><span>Resultados</span><strong>${x.total_resultados||0}</strong></div><div class="diagnosticCard"><span>Média da turma</span><strong>${Number(x.media_nota||0).toFixed(2)}</strong></div><div class="diagnosticCard"><span>Aproveitamento</span><strong>${Number(x.aproveitamento||0).toFixed(1)}%</strong></div></div>`;
  diagnosticText.innerHTML=`<div class="diagnosticText">${x.texto||'Sem dados suficientes para gerar o diagnóstico.'}</div>`;
  const q=x.questoes||[];
  if(q.length){
    const strong=[...q].sort((a,b)=>b.percentual-a.percentual).slice(0,3); const weak=[...q].sort((a,b)=>a.percentual-b.percentual).slice(0,3);
    diagnosticQuestions.innerHTML=`<div class="diagStrength"><b>💡 Pontos de maior domínio:</b> ${strong.map(v=>`Q${v.questao} (${v.percentual.toFixed(0)}%)`).join(' · ')}</div><div class="diagAttention"><b>📚 Pontos para reforço:</b> ${weak.map(v=>`Q${v.questao} (${v.percentual.toFixed(0)}%)`).join(' · ')}</div><div class="tableWrap questionDiag"><table><thead><tr><th>Questão</th><th>Respostas</th><th>Acertos</th><th>Aproveitamento</th><th>Em branco</th><th>Anuladas</th></tr></thead><tbody>${q.map(v=>`<tr><td>${v.questao}</td><td>${v.respostas}</td><td>${v.acertos}</td><td>${v.percentual.toFixed(1)}%</td><td>${v.brancos}</td><td>${v.anuladas}</td></tr>`).join('')}</tbody></table></div>`;
  } else diagnosticQuestions.innerHTML='<div class="guide">O diagnóstico por questão fica disponível quando uma única prova/bloco é selecionado.</div>';
}
async function showReport(){
  if(!classSelect.value){reportBody.innerHTML='<tr><td colspan="9">Selecione uma turma.</td></tr>';diagnosticText.textContent='Selecione uma turma e atualize o relatório.';diagnosticQuestions.innerHTML='';return;}
  const params=reportExam.value?`?prova_nome=${encodeURIComponent(reportExam.value)}`:'';
  const r=await apiFetch(`/api/turmas/${classSelect.value}/relatorio${params}`); const d=await r.json();
  const rows=d.resultados||[]; renderDiagnostic(d.diagnostico);
  reportBody.innerHTML=rows.length?rows.map(x=>`<tr><td>${x.numero_chamada||'—'}</td><td>${x.aluno}</td><td>${x.matricula}</td><td>${x.status||'ATIVO'}</td><td>${x.presente_1?'X':x.ausente_1?'AUSENTE':'—'}</td><td>${x.presente_2?'X':x.ausente_2?'AUSENTE':'—'}</td><td>${x.prova}</td><td>${x.id?`${x.acertos}/${x.questoes}`:'—'}</td><td>${x.id?x.erros:'—'}</td><td>${x.id?x.anuladas:'—'}</td><td>${x.id?x.em_branco:'—'}</td><td>${x.nota==null?'—':Number(x.nota).toFixed(2)}</td><td>${x.id?`<button class="reportPdf btn secondary" data-id="${x.id}" style="width:auto;padding:7px 9px;margin:2px">PDF</button><button class="reportDelete btn secondary" data-id="${x.id}" data-name="${x.aluno}" style="width:auto;padding:7px 9px;margin:2px">Excluir</button>`:'—'}</td></tr>`).join(''):'<tr><td colspan="13">Nenhum aluno encontrado para esta turma.</td></tr>';
  reportBody.querySelectorAll('.reportPdf').forEach(b=>b.addEventListener('click',()=>window.open(`/api/resultados/${b.dataset.id}/pdf`,'_blank')));
  reportBody.querySelectorAll('.reportDelete').forEach(b=>b.addEventListener('click',async()=>{if(!confirm(`Excluir o resultado de ${b.dataset.name}? Esta ação não pode ser desfeita.`))return;const rr=await apiFetch(`/api/resultados/${b.dataset.id}`,{method:'DELETE'});const dd=await rr.json();if(!rr.ok){alert(dd.detail||'Erro ao excluir');return;}await refreshData({students:false,report:true});}));
}
classSelect.addEventListener('change',async()=>{
  // Trocar de turma inicia uma nova sessão de correção. Isso evita associar
  // a foto/resultado anterior ao primeiro aluno da nova turma.
  clearCorrectionSession({clearStudent:true});
  await loadStudents();
  reportBody.innerHTML='';reportSummary.innerHTML='';diagnosticText.textContent='Carregando provas...';
  await loadReportExams();await showReport();await loadSiapClasses();
});

examName.addEventListener('change',()=>{
  // Trocar o bloco/prova também invalida a leitura anterior. O gabarito fica
  // preservado para não atrapalhar a configuração, mas o resultado da foto é descartado.
  clearCorrectionSession({clearStudent:true});
});
reportExam.addEventListener('change',showReport);
loadReport.addEventListener('click',showReport);
exportClassPdf.addEventListener('click',()=>{if(!classSelect.value){alert('Selecione uma turma.');return;}const params=reportExam.value?`?prova_nome=${encodeURIComponent(reportExam.value)}`:'';window.open(`/api/turmas/${classSelect.value}/relatorio/pdf${params}`,'_blank');});
document.querySelector('#exportSavedPdf').addEventListener('click',()=>{if(lastSavedResultId)window.open(`/api/resultados/${lastSavedResultId}/pdf`,'_blank');});


async function loadSiapClasses(){
  const r=await apiFetch('/api/turmas');
  const items=await r.json();
  const current=siapClass.value;
  siapClass.innerHTML='<option value="">Selecione a turma...</option>'+items.map(t=>`<option value="${t.id}">${t.nome} (${t.total_alunos})</option>`).join('');
  if(current && items.some(t=>String(t.id)===String(current))) siapClass.value=current;
  else { siapExam.innerHTML='<option value="">Selecione a turma...</option>'; siapExam.disabled=true; }
}

async function loadSiapExams(){
  const id=siapClass.value;
  siapExam.disabled=!id;
  if(!id){siapExam.innerHTML='<option value="">Selecione a turma...</option>';return;}
  const r=await apiFetch(`/api/turmas/${id}/provas`);
  const provas=await r.json();
  const current=siapExam.value;
  siapExam.innerHTML='<option value="">Selecione a prova/bloco...</option>'+provas.map(p=>`<option value="${String(p).replace(/"/g,'&quot;')}">${p}</option>`).join('');
  if(provas.includes(current)) siapExam.value=current;
}

function siapEscape(value){
  return String(value??'').replace(/"/g,'""');
}

function normalizePluginName(value){
  return String(value??'').replace(/\s+/g,' ').trim();
}

// Recortes oficiais dos Blocos 01–06 para lançamento por disciplina no SIAP.
// As questões do cartão são globais dentro do bloco. O SIAP recebe somente
// o recorte da disciplina selecionada e renumera esse recorte a partir da Q01.
// Ex.: Bloco 02 / História = cartão Q16–Q30 -> SIAP Q01–Q15.
const SIAP_BLOCK_DISCIPLINES = {
  1: {
    'portugues': {start:1, end:20},
    'lingua portuguesa': {start:1, end:20},
  },
  2: {
    'geografia': {start:1, end:15},
    'historia': {start:16, end:30},
  },
  3: {
    'matematica': {start:1, end:20},
  },
  4: {
    'ingles': {start:1, end:10},
    'arte': {start:11, end:20},
    'artes': {start:11, end:20},
    'educacao fisica': {start:21, end:30},
  },
  5: {
    'fisica': {start:1, end:15},
    'quimica': {start:16, end:30},
  },
  6: {
    'biologia': {start:1, end:15},
    'sociologia': {start:16, end:23},
    'filosofia': {start:24, end:30},
  },
};

function normalizeDiscipline(value){
  return String(value??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').trim().toLowerCase();
}

function getSiapBlockNumber(examName){
  const m=String(examName??'').match(/\bbloco\s*0?([1-8])\b/i);
  return m ? Number(m[1]) : null;
}

function getSiapBlockDisciplineMap(examName){
  const block=getSiapBlockNumber(examName);
  return block ? (SIAP_BLOCK_DISCIPLINES[block]||null) : null;
}

function getSiapDisciplineRange(examName, discipline){
  if(!discipline) return null;
  const map=getSiapBlockDisciplineMap(examName);
  if(!map) return null;
  return map[normalizeDiscipline(discipline)] || null;
}

function requiresSiapDisciplineSelection(examName){
  return Boolean(getSiapBlockDisciplineMap(examName));
}

function projectSiapDataByDiscipline(sourceData){
  const discipline=siapDiscipline?.value||'';
  const map=getSiapBlockDisciplineMap(sourceData?.prova);
  const range=getSiapDisciplineRange(sourceData?.prova, discipline);
  if(!range){
    return {
      ...sourceData,
      _siapRecorte: map ? {required:true, invalid:Boolean(discipline), disciplina:discipline} : null
    };
  }

  const qCount=range.end-range.start+1;
  const resultados=(sourceData.resultados||[]).map(x=>{
    const globalHits=[...(x.acertos_questoes||[])].map(Number).filter(Number.isInteger);
    const localHits=globalHits
      .filter(q=>q>=range.start && q<=range.end)
      .map(q=>q-range.start+1);
    const localAcertos=x.tem_resultado?localHits.length:0;
    return {
      ...x,
      quantidade_questoes:qCount,
      acertos_questoes:localHits,
      acertos:localAcertos,
      percentual:x.tem_resultado ? roundPercent(localAcertos,qCount) : null,
      _questoesOriginais: [range.start, range.end]
    };
  });

  return {
    ...sourceData,
    quantidade_questoes:qCount,
    resultados,
    _siapRecorte:{
      disciplina:discipline,
      inicio:range.start,
      fim:range.end,
      quantidade:qCount
    }
  };
}

function roundPercent(value,total){
  return total ? Math.round((value/total)*10000)/100 : null;
}

function buildSiapPluginClipboard(data){
  // Formato principal para o Plugin GPA: uma linha por aluno, usando o nome
  // como chave e apenas os números das questões acertadas. Todos os alunos
  // da turma são mantidos, inclusive os que não possuem resultado.
  // Exemplo: NOME DO ALUNO<TAB>1,3,7,10
  const rows=[];
  for(const x of data.resultados||[]){
    const name=normalizePluginName(x.nome);
    const hits=[...(new Set((x.acertos_questoes||[]).map(Number)))].filter(Number.isInteger).sort((a,b)=>a-b);
    rows.push(`${name}\t${hits.join(',')}`);
  }
  return rows.join('\n');
}

function buildSiapGridClipboard(data,{includeHeader=false}={}){
  const qCount=Number(data.quantidade_questoes||0);
  const headers=['Aluno','1ª Pres.','1ª Aus.','2ª Pres.','2ª Aus.'];
  for(let i=1;i<=qCount;i++) headers.push(String(i));
  headers.push('Qtde Acertos','% Acertos');
  const rows=[];
  if(includeHeader) rows.push(headers);
  for(const x of data.resultados||[]){
    const id=String(x.numero_chamada??'').trim();
    const aluno=id?`${id} - ${normalizePluginName(x.nome)}`:normalizePluginName(x.nome);
    const cells=[aluno,x.presente_1?'1':'',x.ausente_1?'1':'',x.presente_2?'1':'',x.ausente_2?'1':''];
    const hits=new Set(x.acertos_questoes||[]);
    for(let i=1;i<=qCount;i++) cells.push(hits.has(i)?'1':'');
    cells.push(x.tem_resultado?String(x.acertos):'',x.tem_resultado&&x.percentual!=null?String(x.percentual).replace('.',','):'');
    rows.push(cells);
  }
  return rows.map(row=>row.map(v=>String(v??'').replace(/[\t\r\n]/g,' ')).join('\t')).join('\n');
}

async function copyTextToClipboard(text, htmlText=null, extraMimeText=null){
  // Mantém text/plain como formato principal para o Plugin GPA. Quando o
  // navegador permite ClipboardItem, também publicamos TSV/HTML para que a
  // mesma cópia possa ser colada em uma planilha para conferência.
  if(navigator.clipboard?.write && window.ClipboardItem){
    const items={ 'text/plain': new Blob([text],{type:'text/plain'}) };
    if(extraMimeText) items['text/tab-separated-values']=new Blob([extraMimeText],{type:'text/tab-separated-values'});
    if(htmlText) items['text/html']=new Blob([htmlText],{type:'text/html'});
    await navigator.clipboard.write([new ClipboardItem(items)]);
    return;
  }
  if(navigator.clipboard?.writeText){ await navigator.clipboard.writeText(text); return; }
  const ta=document.createElement('textarea');
  ta.value=text;ta.style.position='fixed';ta.style.left='-9999px';ta.style.opacity='0';
  document.body.appendChild(ta);ta.select();
  const ok=document.execCommand('copy');ta.remove();
  if(!ok) throw new Error('O navegador bloqueou a cópia automática.');
}

function buildSiapGridHtml(data){
  const qCount=Number(data.quantidade_questoes||0);
  const esc=v=>String(v??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  let html='<table><thead><tr><th>Aluno</th><th>1ª Pres.</th><th>1ª Aus.</th><th>2ª Pres.</th><th>2ª Aus.</th>';
  for(let i=1;i<=qCount;i++) html+=`<th>${i}</th>`;
  html+='<th>Qtde Acertos</th><th>% Acertos</th></tr></thead><tbody>';
  for(const x of data.resultados||[]){
    const id=String(x.numero_chamada??'').trim();
    const aluno=id?`${id} - ${normalizePluginName(x.nome)}`:normalizePluginName(x.nome);
    const hits=new Set(x.acertos_questoes||[]);
    html+=`<tr><td>${esc(aluno)}</td><td>${x.presente_1?'1':''}</td><td>${x.ausente_1?'1':''}</td><td>${x.presente_2?'1':''}</td><td>${x.ausente_2?'1':''}`;
    for(let i=1;i<=qCount;i++) html+=`<td>${hits.has(i)?'1':''}</td>`;
    html+=`<td>${x.tem_resultado?esc(x.acertos):''}</td><td>${x.tem_resultado&&x.percentual!=null?esc(String(x.percentual).replace('.',',')):' '}</td></tr>`;
  }
  html+='</tbody></table>';
  return html;
}

function renderPluginGpaCompat(data){
  if(!pluginGpaCompatBody)return;
  const qCount=Number(data.quantidade_questoes||0);
  const rows=data.resultados||[];
  // Fonte estruturada para a extensão. Assim ela não depende apenas do
  // estado visual dos checkboxes ocultos.
  const payload={version:2,qCount,rows:rows.map(x=>({
    numero:String(x.numero_chamada??'').trim(),
    nome:String(x.nome||''),
    // A frequência registrada no ScoreView é a fonte de verdade para o SIAP.
    // Os quatro campos precisam viajar no payload porque o SIAP inicia os alunos como ausentes.
    presente_1:Boolean(x.presente_1),
    ausente_1:Boolean(x.ausente_1),
    presente_2:Boolean(x.presente_2),
    ausente_2:Boolean(x.ausente_2),
    tem_resultado:Boolean(x.tem_resultado),
    acertos_questoes:[...(x.acertos_questoes||[])].map(Number).filter(Number.isInteger)
  }))};
  const dataNode=document.getElementById('scoreview-gpa-data');
  if(dataNode) dataNode.textContent=JSON.stringify(payload);
  pluginGpaCompatBody.innerHTML=rows.map(x=>{
    const id=String(x.numero_chamada??'').trim();
    const hits=new Set(x.acertos_questoes||[]);
    // Compatibilidade visual com o plugin original. Os quatro primeiros
    // checkboxes continuam existindo, mas a extensão nova usa o payload
    // estruturado acima para não perder os acertos.
    const checks=[!!x.presente_1,!!x.ausente_1,!!x.presente_2,!!x.ausente_2];
    for(let i=1;i<=qCount;i++) checks.push(x.tem_resultado && hits.has(i));
    const checkHtml=checks.map((v,i)=>`<input type="checkbox" ${v?'checked':''} aria-label="${i<4?'chamada':'questao '+(i-3)}">`).join('');
    return `<tr class="linhaAluno" data-number="${escapeHtml(id)}"><td>${escapeHtml(id)} - ${escapeHtml(x.nome||'')}</td>${checkHtml}<td><input type="text" value="${x.tem_resultado?Number(x.acertos||0):0}"></td></tr>`;
  }).join('');
}

function escapeHtml(value){
  return String(value??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function renderSiap(data){
  lastSiapData=data;
  const viewData=projectSiapDataByDiscipline(data);
  lastSiapViewData=viewData;
  renderPluginGpaCompat(viewData);
  const qCount=Number(viewData.quantidade_questoes||0);
  const validation=viewData.validacao||{ok:true,ids_ausentes:[],ids_duplicados:[]};
  if(!qCount){
    siapHead.innerHTML='';
    siapBody.innerHTML='<tr><td>Nenhum resultado salvo para esta prova.</td></tr>';
    siapResultCard.style.display='block';
    copySiap.disabled=true; copySiapGrid.disabled=true;
    return;
  }
  const qHeaders=Array.from({length:qCount},(_,i)=>`<th>${i+1}</th>`).join('');
  siapHead.innerHTML=`<tr><th rowspan="2">Aluno</th><th colspan="2">1ª Chamada</th><th colspan="2">2ª Chamada</th><th colspan="${qCount}">Acertos por questão</th><th rowspan="2">Qtde<br>Acertos</th><th rowspan="2">%<br>Acertos</th></tr><tr><th>Pres.</th><th>Aus.</th><th>Pres.</th><th>Aus.</th>${qHeaders}</tr>`;
  siapBody.innerHTML=(viewData.resultados||[]).map(x=>{
    const hits=new Set(x.acertos_questoes||[]);
    const attendance=(v)=>`<input class="siapCheck" type="checkbox" ${v?'checked':''} tabindex="-1" aria-label="${v?'marcado':'não marcado'}">`;
    const qCells=Array.from({length:qCount},(_,i)=>`<td>${x.tem_resultado?attendance(hits.has(i+1)):'<span class="siapEmpty">—</span>'}</td>`).join('');
    const rowClass=x.tem_resultado?'':'siapNoResult';
    const id=String(x.numero_chamada??'').trim();
    const aluno=id?`${id} - ${x.nome}`:`⚠ SEM ID - ${x.nome}`;
    return `<tr class="${rowClass}"><td><b>${aluno}</b>${!x.tem_resultado?'<div class="siapPending">Sem resultado</div>':''}</td><td>${attendance(x.presente_1)}</td><td>${attendance(x.ausente_1)}</td><td>${attendance(x.presente_2)}</td><td>${attendance(x.ausente_2)}</td>${qCells}<td>${x.tem_resultado?x.acertos:'—'}</td><td>${x.tem_resultado&&x.percentual!=null?x.percentual.toFixed(2).replace('.',',')+'%':'—'}</td></tr>`;
  }).join('');
  const s=data.resumo||{};
  const rangeInfo=viewData._siapRecorte;
  const disciplineRequired=requiresSiapDisciplineSelection(viewData.prova);
  const disciplineReady=!disciplineRequired || Boolean(rangeInfo && rangeInfo.inicio);
  const disciplineInvalid=disciplineRequired && !disciplineReady && Boolean(siapDiscipline?.value);
  const disciplineMissing=disciplineRequired && !disciplineReady && !siapDiscipline?.value;
  const warningParts=[];
  if(disciplineMissing) warningParts.push('Selecione a disciplina para aplicar o recorte correto das questões');
  if(disciplineInvalid) warningParts.push(`A disciplina "${siapDiscipline.value}" não pertence ao ${viewData.prova}`);
  if(validation.ids_ausentes?.length) warningParts.push(`${validation.ids_ausentes.length} aluno(s) sem ID de chamada`);
  if(validation.ids_duplicados?.length) warningParts.push(`ID(s) duplicado(s): ${validation.ids_duplicados.join(', ')}`);
  if(warningParts.length){
    siapStatus.className='status error';
    siapStatus.textContent=`⚠ ${warningParts.join(' · ')}. Corrija o cadastro antes de copiar para o GPA.`;
    siapStatus.style.display='block';
  }
  siapSummary.innerHTML=[
    `Alunos: ${s.alunos||0}`,
    `Com resultado: ${s.com_resultado||0}`,
    `Presentes 1ª: ${s.presentes_1||0}`,
    `Ausentes 1ª: ${s.ausentes_1||0}`,
    `Presentes 2ª: ${s.presentes_2||0}`,
    `Ausentes 2ª: ${s.ausentes_2||0}`,
    rangeInfo?.inicio ? `${rangeInfo.disciplina}: Q${String(rangeInfo.inicio).padStart(2,'0')}–Q${String(rangeInfo.fim).padStart(2,'0')} → ${qCount} questões` : (disciplineRequired ? `Disciplina: ${siapDiscipline.value||'selecione'} · recorte obrigatório` : `Questões: ${qCount}`),
    'Ordem: ID / chamada'
  ].map(t=>`<span class="pill">${t}</span>`).join('');
  siapResultCard.style.display='block';
  const canCopy=validation.ok && disciplineReady;
  copySiap.disabled=!canCopy; copySiapGrid.disabled=!canCopy;
}

async function prepareSiapData(){
  if(!siapClass.value){siapStatus.className='status error';siapStatus.textContent='Selecione uma turma.';siapStatus.style.display='block';return;}
  if(!siapExam.value){siapStatus.className='status error';siapStatus.textContent='Selecione uma prova/bloco.';siapStatus.style.display='block';return;}
  prepareSiap.disabled=true; prepareSiap.textContent='Preparando...';
  try{
    const r=await apiFetch(`/api/turmas/${siapClass.value}/siap?prova_nome=${encodeURIComponent(siapExam.value)}`);
    const d=await r.json(); if(!r.ok)throw new Error(d.detail||'Não foi possível preparar o lançamento.');
    renderSiap(d);
    if(d.validacao?.ok!==false){
      const range=getSiapDisciplineRange(d.prova,siapDiscipline.value);
      const required=requiresSiapDisciplineSelection(d.prova);
      siapStatus.className=(required && !range)?'status error':'status ok';
      siapStatus.textContent=range
        ? `Dados preparados para ${d.turma.nome} · ${d.prova}. ${siapDiscipline.value}: questões ${String(range.start).padStart(2,'0')}–${String(range.end).padStart(2,'0')} (${range.end-range.start+1} questões) → SIAP Q01–Q${range.end-range.start+1}.`
        : required
          ? `Selecione a disciplina correta para ${d.prova}. O recorte por disciplina é obrigatório antes de copiar para o GPA.`
          : `Dados preparados para ${d.turma.nome} · ${d.prova}. ${d.resumo?.alunos||0} alunos serão mantidos na cópia, inclusive os sem resultado.`;
      siapStatus.style.display='block';
    }
  }catch(e){
    siapStatus.className='status error';siapStatus.textContent=e.message;siapStatus.style.display='block';
  }finally{prepareSiap.disabled=false;prepareSiap.textContent='☑ Preparar lançamento';}
}

prepareSiap.addEventListener('click',prepareSiapData);
siapClass.addEventListener('change',async()=>{await loadSiapExams();siapResultCard.style.display='none';lastSiapData=null;lastSiapViewData=null;copySiap.disabled=true;copySiapGrid.disabled=true;});
siapExam.addEventListener('change',()=>{siapResultCard.style.display='none';lastSiapData=null;lastSiapViewData=null;copySiap.disabled=true;copySiapGrid.disabled=true;});
siapDiscipline.addEventListener('change',()=>{
  if(lastSiapData){
    renderSiap(lastSiapData);
    const range=getSiapDisciplineRange(lastSiapData.prova,siapDiscipline.value);
    const required=requiresSiapDisciplineSelection(lastSiapData.prova);
    siapStatus.className=(required && !range)?'status error':(range?'status ok':'status');
    siapStatus.textContent=range
      ? `✓ ${siapDiscipline.value}: serão enviadas somente as questões ${String(range.start).padStart(2,'0')}–Q${String(range.end).padStart(2,'0')} do cartão, renumeradas no SIAP de Q01–Q${range.end-range.start+1}.`
      : (required ? `⚠ ${siapDiscipline.value ? `"${siapDiscipline.value}" não possui recorte configurado para ${lastSiapData.prova}.` : 'Selecione a disciplina correspondente ao bloco.'}` : 'ℹ Este bloco não possui recorte por disciplina configurado; todas as questões salvas serão exibidas.');
    siapStatus.style.display='block';
  }
});

copySiap.addEventListener('click',async()=>{
  if(!lastSiapData || lastSiapData.validacao?.ok===false)return;
  const viewData=projectSiapDataByDiscipline(lastSiapData);
  lastSiapViewData=viewData;
  renderPluginGpaCompat(viewData);
  siapStatus.className='status ok';
  siapStatus.innerHTML=`✓ Página preparada para o PLUGIN GPA com <b>${viewData.resultados?.length||0} alunos</b>. Agora clique com o botão direito nesta página → <b>PLUGIN GPA → Copiar (GPA)</b>. Depois abra o SIAP e use <b>PLUGIN GPA → Colar (SIAP)</b>.`;
  siapStatus.style.display='block';
});

copySiapGrid.addEventListener('click',async()=>{
  if(!lastSiapData || lastSiapData.validacao?.ok===false)return;
  try{
    const viewData=projectSiapDataByDiscipline(lastSiapData);
    lastSiapViewData=viewData;
    const gridText=buildSiapGridClipboard(viewData,{includeHeader:true});
    const html=buildSiapGridHtml(viewData);
    await copyTextToClipboard(gridText,html,gridText);
    siapStatus.className='status ok';
    siapStatus.textContent=`✓ Grade completa com ${viewData.resultados?.length||0} alunos copiada. Esta opção é para colar em planilha/conferência; para o Plugin GPA, use o botão principal.`;
    siapStatus.style.display='block';
  }catch(e){
    siapStatus.className='status error';
    siapStatus.textContent=`Não foi possível copiar a grade: ${e.message||'erro do navegador'}`;
    siapStatus.style.display='block';
  }
});



async function loadUsers(){
  if(!currentUser||currentUser.tipo!=='admin')return;
  const tr=await apiFetch('/api/turmas'); const turmas=await tr.json();
  document.querySelector('#userClasses').innerHTML=turmas.length?turmas.map(t=>`<label style="display:inline-block;margin:6px 14px 6px 0"><input type="checkbox" class="userClass" value="${t.id}"> ${t.nome}</label>`).join(''):'Importe alunos para criar turmas.';
  const ur=await apiFetch('/api/admin/usuarios');const users=await ur.json();
  const names=Object.fromEntries(turmas.map(t=>[t.id,t.nome]));
  document.querySelector('#usersBody').innerHTML=users.map(u=>`<tr><td>${u.nome}</td><td>${u.login}</td><td>${u.tipo}</td><td>${u.tipo==='admin'?'Todas':u.turma_ids.map(id=>names[id]||id).join(', ')||'Nenhuma'}</td><td>${u.ativo?'Ativo':'Inativo'}</td><td>${u.id===currentUser.id?'Em uso':u.tipo!=='professor'?'Protegido':`<button class="deleteUser btn secondary" data-id="${u.id}" data-name="${u.nome}" style="width:auto;padding:7px 9px;margin:0">Excluir</button>`}</td></tr>`).join('');
  document.querySelectorAll('.deleteUser').forEach(b=>b.addEventListener('click',async()=>{if(!confirm(`Excluir o cadastro de ${b.dataset.name}? Esta ação não pode ser desfeita.`))return;const r=await apiFetch(`/api/admin/usuarios/${b.dataset.id}`,{method:'DELETE'});const d=await r.json();if(!r.ok){alert(d.detail||'Erro ao excluir usuário');return;}await refreshData({students:false,report:true});}));
}
document.querySelector('#createUser').addEventListener('click',async()=>{
  const body={nome:document.querySelector('#userName').value.trim(),login:document.querySelector('#userLogin').value.trim(),senha:document.querySelector('#userPass').value,tipo:document.querySelector('#userType').value,turma_ids:[...document.querySelectorAll('.userClass:checked')].map(x=>Number(x.value))};
  const st=document.querySelector('#userStatus');try{if(!body.nome||!body.login||!body.senha)throw new Error('Preencha nome, login e senha.');const r=await apiFetch('/api/admin/usuarios',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const d=await r.json();if(!r.ok)throw new Error(d.detail||'Erro ao criar usuário');st.className='status ok';st.textContent='Usuário criado com sucesso.';st.style.display='block';document.querySelector('#userName').value='';document.querySelector('#userLogin').value='';document.querySelector('#userPass').value='';document.querySelectorAll('.userClass').forEach(x=>x.checked=false);await refreshData({students:false,report:true});}catch(e){st.className='status error';st.textContent=e.message;st.style.display='block';}
});
document.addEventListener('visibilitychange',()=>{if(!document.hidden && currentUser) refreshData({students:true,report:true}).catch(()=>{});});
window.addEventListener('focus',()=>{if(currentUser) refreshData({students:true,report:true}).catch(()=>{});});
setInterval(()=>{if(currentUser && !document.hidden) refreshData({students:true,report:true}).catch(()=>{});},60000);
startApp();

