const file=decodeURIComponent(location.pathname.split('/').pop());
const el=id=>document.getElementById(id);
let page=Number(new URLSearchParams(location.search).get('page')||1),count=0,serial=0;
el('download').href='/api/source/'+encodeURIComponent(file);
async function show(){
  const request=++serial;
  el('page-image').hidden=true;el('error').hidden=true;el('status').hidden=false;
  el('status').textContent='กำลังแสดงหน้าต้นฉบับ…';el('previous').disabled=true;el('next').disabled=true;
  try{
    if(!Number.isInteger(page)||page<1)throw new Error('กรุณาระบุหมายเลข PDF หน้าเป็นจำนวนเต็มตั้งแต่ 1');
    const response=await fetch('/api/source-info/'+encodeURIComponent(file)+'?page='+page);
    if(!response.ok){const body=await response.json();throw new Error(body.detail||'เปิดเอกสารไม่ได้');}
    const info=await response.json();if(request!==serial)return;
    count=info.page_count;el('page').value=page;el('page').max=count;
    el('identity').textContent=file+' · PDF หน้า '+page+' จาก '+count;
    el('mapping').textContent=info.printed_page===null?'หน้าในเล่มยังไม่ยืนยัน หรือคู่เลขหน้าขัดแย้งกัน':'หน้าในเล่ม '+info.printed_page;
    const image=el('page-image');image.alt=file+' PDF หน้า '+page+(info.printed_page===null?'':' / หน้า '+info.printed_page+' ในเล่ม');
    image.onload=()=>{if(request!==serial)return;image.hidden=false;el('status').hidden=true;el('previous').disabled=page===1;el('next').disabled=page===count;};
    image.onerror=()=>{if(request===serial)failure('โหลดภาพหน้าต้นฉบับไม่ได้ โปรดลองอีกครั้ง');};
    image.src='/api/source-page/'+encodeURIComponent(file)+'/'+page+'?document='+info.sha256;
    history.replaceState(null,'','?page='+page);
  }catch(error){if(request===serial)failure(error.message);}
}
function failure(message){el('status').hidden=true;el('error').hidden=false;el('error-text').textContent=message;el('mapping').textContent='';el('page-image').hidden=true;}
el('page-form').addEventListener('submit',event=>{event.preventDefault();page=Number(el('page').value);show();});
el('previous').addEventListener('click',()=>{page--;show();});el('next').addEventListener('click',()=>{page++;show();});el('retry').addEventListener('click',show);
show();
