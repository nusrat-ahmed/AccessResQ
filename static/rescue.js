/* AccessResQ NET v1.1: offline-first SOS + protected reviewer desk.
   No real Bluetooth mesh, LoRa radio, automated rescue dispatch or trained AI is implemented.
*/
(() => {
  'use strict';
  const $ = q => document.querySelector(q);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let reviewerToken = null, sending = false, map = null, markers = [];
  let currentGPS = null;
  const formatDate = value => {try {return new Date(value).toLocaleString('en-BD');} catch {return 'Unknown time';}};
  function message(value, error=false) {
    const el = $('#resqLocationMessage');
    if(el && value) { el.textContent = value; el.classList.toggle('resq-error',error); }
  }
  function connection() {
    const online = navigator.onLine;
    const el = $('#resqConnection');
    if(el) {el.textContent=online?'● Network detected':'● Offline — queue only';el.classList.toggle('offline', !online);}
    return online;
  }
  function notify(msg) {
    const el=$('#toast');if(!el){alert(msg);return;}
    el.textContent=msg;el.className='toast show';setTimeout(()=>el.classList.remove('show'),6500);
  }
  function uuidv4() {
    if(window.crypto?.randomUUID) return crypto.randomUUID();
    if(window.crypto?.getRandomValues) {const a=new Uint8Array(16);crypto.getRandomValues(a);a[6]=(a[6]&15)|64;a[8]=(a[8]&63)|128;return [...a].map((v,i)=> (i===4||i===6||i===8||i===10?'-':'')+v.toString(16).padStart(2,'0')).join('');}
    throw new Error('A secure browser context (HTTPS or localhost) is required.');
  }
  function db() {
    return new Promise((resolve,reject)=>{
      if(!window.indexedDB) {reject(new Error('Offline storage is not supported in this browser.'));return;}
      const req=indexedDB.open('accessresq-pending-sos',1);
      req.onupgradeneeded=()=>{if(!req.result.objectStoreNames.contains('queue'))req.result.createObjectStore('queue',{keyPath:'client_id'});};
      req.onsuccess=()=>resolve(req.result);
      req.onerror=()=>reject(req.error||new Error('Device storage could not be opened.'));
    });
  }
  async function withStore(mode, run) {
    const database=await db();
    return new Promise((resolve,reject)=>{
      const tx=database.transaction('queue',mode),store=tx.objectStore('queue');
      let output;
      try {const req=run(store);if(req){req.onsuccess=()=>{output=req.result;};req.onerror=()=>reject(req.error);}}catch(e){database.close();reject(e);return;}
      tx.oncomplete=()=>{database.close();resolve(output);};
      tx.onerror=()=>{database.close();reject(tx.error||new Error('Offline storage failed.'));};
      tx.onabort=()=>{database.close();reject(tx.error||new Error('Storage operation cancelled.'));};
    });
  }
  const addQueued = item => withStore('readwrite',store=>store.put(item));
  const deleteQueued = id => withStore('readwrite',store=>store.delete(id));
  const readQueued = () => withStore('readonly',store=>store.getAll());
  async function renderQueue() {
    try {
      const items=await readQueued();
      $('#resqQueueCount').textContent=`${items.length} pending`;
      $('#resqQueueList').innerHTML=items.length ? items.map(x=>`<div class="resq-queued"><strong>${esc(x.area)}</strong><small>Saved ${esc(formatDate(x.saved_at))} · Not delivered to any responder<br>ID ${esc(x.client_id.slice(0,8))}</small><button type="button" data-drop="${esc(x.client_id)}">Delete from device</button></div>`).join(''):'<p class="resq-empty">Nothing waiting to sync.</p>';
      document.querySelectorAll('[data-drop]').forEach(b=>b.addEventListener('click',async()=>{
        if(!confirm('Delete this unsent SOS from this browser? It cannot be recovered.')) return;
        await deleteQueued(b.dataset.drop);await renderQueue();notify('Unsent SOS removed from this device.');
      }));
    } catch(e) {$('#resqQueueList').textContent='Offline storage is unavailable: '+e.message;}
  }
  async function sendToServer(item) {
    const payload={...item};delete payload.saved_at;
    const response=await fetch('/api/sos',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(payload),cache:'no-store'});
    if(!response.ok){const err=await response.json().catch(()=>({}));const e=new Error(typeof err.detail==='string'?err.detail:`Server rejected SOS (${response.status})`);e.code=response.status;throw e;}
    const result=await response.json();
    if(!result.server_received || !result.public_id) throw new Error('Server did not confirm receipt.');
    return result;
  }
  async function syncQueue() {
    if(sending)return;
    if(!connection()) {notify('Still offline. SOS remains on this browser, not delivered.');return;}
    sending=true;const b=$('#resqSync');b.disabled=true;b.textContent='Synchronizing…';
    try{
      const items=await readQueued();let sent=0, errors=[];
      for(const item of items){
        try{
          const result=await sendToServer(item);
          await deleteQueued(item.client_id);sent++;
          notify(`Server accepted SOS ${result.public_id}. This does not notify rescue teams.`);
        }catch(e){errors.push(e.message);if(!e.code || e.code>=500)break;}
      }
      await renderQueue();
      if(errors.length) notify(`Some messages could not sync: ${errors[0]}. They remain on this browser.`);
      else if(!sent && items.length===0)notify('No pending messages to sync.');
    }catch(e){notify('Sync failed. Unsent signals remain on your device: '+e.message);}
    finally{sending=false;b.disabled=false;b.textContent='↻ Sync queued SOS now';}
  }
  function payloadFromForm(form) {
    const f=new FormData(form);
    const data={client_id:uuidv4(),area:String(f.get('area')||'').trim(),details:String(f.get('details')||'').trim(),
      people_affected:Number(f.get('people_affected')),children_count:Number(f.get('children_count')),mobility_support:Number(f.get('mobility_support')),
      contact:String(f.get('contact')||'').trim(),trapped:f.has('trapped'),water_rising:f.has('water_rising'),medical_need:f.has('medical_need'),consent:f.has('consent')};
    if(currentGPS){data.lat=currentGPS.lat;data.lng=currentGPS.lng;}
    if(!Number.isInteger(data.people_affected)||data.people_affected<1||data.children_count>data.people_affected||data.mobility_support>data.people_affected) throw new Error('Check the affected people and group counts.');
    if(!data.consent)throw new Error('Consent must be checked.');
    return data;
  }
  $('#resqSOSForm').addEventListener('submit',async event=>{
    event.preventDefault();const form=event.currentTarget,button=$('#resqSendSOS');button.disabled=true;
    try {
      const item={...payloadFromForm(form),saved_at:new Date().toISOString()};
      // Store before network attempt so a sudden disconnect cannot lose the request.
      await addQueued(item);
      await renderQueue();form.reset();currentGPS=null;
      $('#resqCoordinates').textContent='Location not selected';message('Saved on this browser. No GPS location shared.');
      if(connection())await syncQueue();
      else notify('SOS saved on this device ONLY. It has not reached the server or any rescuer.');
    }catch(e){notify('SOS could not be saved: '+e.message);}
    finally{button.disabled=false;}
  });
  $('#resqUseLocation').addEventListener('click',()=>{
    if(!navigator.geolocation){message('Geolocation is unavailable. You can still submit an area name.',true);return;}
    message('Requesting your location…');
    navigator.geolocation.getCurrentPosition(pos=>{
      const {latitude:lat, longitude:lng}=pos.coords;
      // This prototype currently validates locations inside Bangladesh.
      if(lat<20.5||lat>26.8||lng<88||lng>92.8){currentGPS=null;message('Coordinates are outside this prototype’s Bangladesh coverage. Use the area description instead.',true);return;}
      currentGPS={lat:Number(lat.toFixed(6)),lng:Number(lng.toFixed(6))};
      $('#resqCoordinates').textContent=`${currentGPS.lat}, ${currentGPS.lng}`;
      message(`GPS accuracy: approximately ${Math.round(pos.coords.accuracy)} metres. Location added with your permission.`);
    },error=>{message(error.code===1?'Permission denied. Location remains optional.':'Could not get GPS. Location remains optional.',true);},{enableHighAccuracy:true,timeout:12000,maximumAge:60000});
  });
  $('#resqSync').addEventListener('click',syncQueue);
  window.addEventListener('online',()=>{connection();syncQueue();});
  window.addEventListener('offline',connection);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden && connection())syncQueue();});
  async function reviewerApi(path, options={}) {
    const response=await fetch(path,{...options,cache:'no-store',headers:{'X-Admin-Token':reviewerToken,'Content-Type':'application/json',...(options.headers||{})}});
    const body=await response.json().catch(()=>null);
    if(!response.ok)throw new Error(typeof body?.detail==='string'?body.detail:`Request failed (${response.status})`);
    return body;
  }
  function drawReviewerMap(rows) {
    if(!window.L || !$('#resqReviewerWorkspace') || $('#resqReviewerWorkspace').classList.contains('hidden'))return;
    if(!map){map=L.map('resqRescueMap',{scrollWheelZoom:false}).setView([24.0,90.2],7);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap',maxZoom:18}).addTo(map);}
    markers.forEach(m=>map.removeLayer(m));markers=[];const coords=[];
    rows.forEach(x=>{if(x.lat==null||x.lng==null)return;const m=L.marker([x.lat,x.lng]).addTo(map).bindPopup(`<strong>${esc(x.public_id)}</strong><div>${esc(x.area)}</div><div>${esc(x.triage_tier)} · ${esc(x.status)}</div>`);markers.push(m);coords.push([x.lat,x.lng]);});
    if(coords.length)map.fitBounds(coords,{padding:[20,20],maxZoom:10});setTimeout(()=>map.invalidateSize(),140);
  }
  async function refreshReviewer() {
    if(!reviewerToken)return;
    try{
      const rows=await reviewerApi('/api/rescue/sos');
      $('#resqReviewCount').textContent=`${rows.length} SOS signals`;
      const holder=$('#resqReviewList');
      holder.innerHTML=rows.length?rows.map(x=>`<article class="resq-review-item"><header><h3>${esc(x.public_id)}</h3><span class="resq-priority ${esc(x.triage_tier)}">${esc(x.triage_tier)} · ${Number(x.triage_score)}/100</span></header><p><strong>${esc(x.area)}</strong> · ${esc(formatDate(x.created_at))}</p><p>${esc(x.details)}</p><p>People: ${Number(x.people_affected)} · Children: ${Number(x.children_count)} · Mobility support: ${Number(x.mobility_support)}</p><p>GPS: ${x.lat==null?'Not shared':`${Number(x.lat).toFixed(5)}, ${Number(x.lng).toFixed(5)}`} · Contact: ${esc(x.contact||'Not provided')}</p><p class="resq-reason"><strong>Why this score:</strong> ${esc(x.triage_reasons)}. This rule-based score does not replace human triage.</p><div class="resq-review-status"><small>Source: ${esc(x.source)} · ${esc(x.status)}</small><select aria-label="Change SOS status for ${esc(x.public_id)}" data-sos-status="${esc(x.public_id)}"><option value="unreviewed" ${x.status==='unreviewed'?'selected':''}>Unreviewed</option><option value="reviewing" ${x.status==='reviewing'?'selected':''}>Reviewing</option><option value="contacted" ${x.status==='contacted'?'selected':''}>Contacted</option><option value="closed" ${x.status==='closed'?'selected':''}>Closed</option></select></div></article>`).join(''):'<div class="panel resq-queue-panel"><h3>No SOS signals</h3><p>The reviewer queue is empty. Use Offline SOS to create a test record.</p></div>';
      holder.querySelectorAll('[data-sos-status]').forEach(el=>el.addEventListener('change',async()=>{
        try {await reviewerApi('/api/rescue/sos/'+encodeURIComponent(el.dataset.sosStatus),{method:'PATCH',body:JSON.stringify({status:el.value})});notify('Status updated by reviewer. No automatic dispatch occurred.');await refreshReviewer();}
        catch(e){notify('Status update failed: '+e.message);}
      }));
      drawReviewerMap(rows);
    }catch(e){
      $('#resqReviewList').innerHTML=`<div class="resq-warning">Could not load protected signals: ${esc(e.message)}</div>`;
      if(/authorization/i.test(e.message)) lockReviewer();
    }
  }
  function lockReviewer(){reviewerToken=null;$('#resqReviewerGate').classList.remove('hidden');$('#resqReviewerWorkspace').classList.add('hidden');$('#resqReviewerToken').value='';$('#resqReviewList').innerHTML='';if(map){markers.forEach(m=>map.removeLayer(m));markers=[];}}
  $('#resqReviewerForm').addEventListener('submit',async e=>{
    e.preventDefault();const token=$('#resqReviewerToken').value.trim();if(!token)return;
    reviewerToken=token;
    try{
      // Authorisation is checked by server. Never save reviewer credentials in storage.
      await reviewerApi('/api/rescue/sos?limit=1');
      $('#resqReviewerToken').value='';$('#resqReviewerGate').classList.add('hidden');$('#resqReviewerWorkspace').classList.remove('hidden');
      await refreshReviewer();
    }catch(err){reviewerToken=null;notify('Reviewer sign-in failed: '+err.message);}
  });
  $('#resqReviewRefresh').addEventListener('click',refreshReviewer);
  $('#resqReviewLogout').addEventListener('click',lockReviewer);
  window.addEventListener('hashchange',()=>{if(location.hash==='#rescue' && reviewerToken)setTimeout(refreshReviewer,120);});
  // Only static app shell is available offline. External Leaflet assets and online maps need internet.
  if('serviceWorker' in navigator && (location.protocol==='https:'||location.hostname==='localhost'||location.hostname==='127.0.0.1')){
    window.addEventListener('load',()=>navigator.serviceWorker.register('/sw.js').catch(()=>{}));
  }
  connection();renderQueue();
  if(connection())setTimeout(syncQueue,700);
})();
