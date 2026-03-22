/**
 * Homepage Dynamic Data Loader
 * Fetches real data from JSON files and updates hardcoded placeholders
 */
(function(){
  function fmt(n,d){return n?n.toFixed(d||2):'--'}
  function fmtUSD(n){
    if(!n)return'--';
    if(n>=1e12)return'$'+(n/1e12).toFixed(2)+'T';
    if(n>=1e9)return'$'+(n/1e9).toFixed(1)+'B';
    if(n>=1e6)return'$'+(n/1e6).toFixed(1)+'M';
    return'$'+n.toLocaleString();
  }
  function pctChange(arr,key,days){
    if(!arr||arr.length<days+1)return null;
    var cur=arr[arr.length-1][key],prev=arr[arr.length-1-days][key];
    if(!prev)return null;
    return((cur-prev)/prev*100);
  }
  function setText(sel,val){
    var el=document.querySelector(sel);
    if(el)el.textContent=val;
  }

  // Load AHR999
  fetch('./indicators/data/ahr999.json').then(function(r){return r.json()}).then(function(d){
    var cur=d.current||{};
    var hist=d.history||[];
    var val=cur.ahr999||hist[hist.length-1]?.ahr999;
    var price=cur.btc_price||hist[hist.length-1]?.btc_price;
    // Update indicator card
    var indEl=document.querySelector('a[href="./ahr999/"] .ind-val');
    if(indEl&&val)indEl.textContent=fmt(val,2);
    // Update zone
    var zoneEl=document.querySelector('a[href="./ahr999/"] .ind-zone');
    if(zoneEl&&val){
      if(val<0.45){zoneEl.textContent='抄底区';zoneEl.className='ind-zone g';}
      else if(val<1.2){zoneEl.textContent='定投区';zoneEl.className='ind-zone y';}
      else{zoneEl.textContent='过热区';zoneEl.className='ind-zone r';}
    }
    // Update sparkline data
    if(hist.length>7){
      var last7=hist.slice(-7).map(function(x){return x.ahr999});
      if(window.sp)sp('sp-a',last7,'#60a5fa');
    }
    // Update 7d change
    var chg=pctChange(hist,'ahr999',7);
    var chgEl=document.querySelector('a[href="./ahr999/"] .ind-chg');
    if(chgEl&&chg!==null){
      chgEl.textContent=(chg>=0?'+':'')+fmt(chg,1)+'%';
      chgEl.className='ind-chg '+(chg>=0?'up':'down')+' mono';
    }
    // Update hero price
    if(price){
      setText('.hero-price','$'+Math.round(price).toLocaleString());
    }
    // 24h change from ahr999 history
    var dayChg=pctChange(hist,'btc_price',1);
    var heroChg=document.querySelector('.hero-change');
    if(heroChg&&dayChg!==null){
      heroChg.textContent=(dayChg>=0?'+':'')+fmt(dayChg,1)+'%';
      heroChg.className='hero-change '+(dayChg>=0?'up':'down');
    }
  }).catch(function(){});

  // Load MVRV
  fetch('./indicators/data/mvrv.json').then(function(r){return r.json()}).then(function(d){
    var cur=d.current||{};
    var hist=d.history||[];
    var val=cur.mvrv||hist[hist.length-1]?.mvrv;
    var indEl=document.querySelector('a[href="./mvrv/"] .ind-val');
    if(indEl&&val)indEl.textContent=fmt(val,2);
    var zoneEl=document.querySelector('a[href="./mvrv/"] .ind-zone');
    if(zoneEl&&val){
      if(val<1){zoneEl.textContent='低估区';zoneEl.className='ind-zone g';}
      else if(val<2.5){zoneEl.textContent='合理区';zoneEl.className='ind-zone y';}
      else{zoneEl.textContent='过热区';zoneEl.className='ind-zone r';}
    }
    if(hist.length>7){
      var last7=hist.slice(-7).map(function(x){return x.mvrv});
      if(window.sp)sp('sp-m',last7,'#a78bfa');
    }
    var chg=pctChange(hist,'mvrv',7);
    var chgEl=document.querySelector('a[href="./mvrv/"] .ind-chg');
    if(chgEl&&chg!==null){
      chgEl.textContent=(chg>=0?'+':'')+fmt(chg,1)+'%';
      chgEl.className='ind-chg '+(chg>=0?'up':'down')+' mono';
    }
  }).catch(function(){});

  // Load BTC.D
  fetch('./indicators/data/btc-dominance.json').then(function(r){return r.json()}).then(function(d){
    var cur=d.current||{};
    var hist=d.history||[];
    var val=cur.dominance||cur.value||hist[hist.length-1]?.dominance||hist[hist.length-1]?.value;
    var indEl=document.querySelector('a[href="./btc-dominance/"] .ind-val');
    if(indEl&&val)indEl.textContent=fmt(val,1)+'%';
    // Hero BTC占比
    setText('.hero-meta-item:nth-child(3) .hero-meta-val',fmt(val,1)+'%');
    var zoneEl=document.querySelector('a[href="./btc-dominance/"] .ind-zone');
    if(zoneEl&&val){
      if(val>65){zoneEl.textContent='BTC主导';zoneEl.className='ind-zone y';}
      else if(val>50){zoneEl.textContent='平衡';zoneEl.className='ind-zone b';}
      else{zoneEl.textContent='山寨季';zoneEl.className='ind-zone g';}
    }
    if(hist.length>7){
      var last7=hist.slice(-7).map(function(x){return x.dominance||x.value});
      if(window.sp)sp('sp-d',last7,'#38bdf8');
    }
    var chg=pctChange(hist,hist[0]?.dominance!==undefined?'dominance':'value',7);
    var chgEl=document.querySelector('a[href="./btc-dominance/"] .ind-chg');
    if(chgEl&&chg!==null){
      chgEl.textContent=(chg>=0?'+':'')+fmt(chg,1)+'%';
      chgEl.className='ind-chg '+(chg>=0?'up':'down')+' mono';
    }
  }).catch(function(){});

  // Load governance data for governance cards
  fetch('./data/governance.json').then(function(r){return r.json()}).then(function(d){
    var proposals=d.proposals||[];
    if(!proposals.length)return;
    // Get 2 most recent TEV-related or active proposals
    var active=proposals.filter(function(p){return p.status==='active'||p.tev_related});
    if(!active.length)active=proposals;
    active.sort(function(a,b){return(b.created||0)-(a.created||0)});
    var cards=document.querySelectorAll('.gov-card');
    for(var i=0;i<Math.min(cards.length,active.length);i++){
      var p=active[i],c=cards[i];
      var titleEl=c.querySelector('.gov-card-title');
      var protoEl=c.querySelector('.gov-card-proto');
      var statusEl=c.querySelector('.gov-card-status');
      if(titleEl)titleEl.textContent=(p.summary_zh||p.title||'').substring(0,40);
      if(protoEl)protoEl.textContent=p.protocol+' · '+(p.status==='active'?'投票中':'已结束');
      if(statusEl){
        if(p.tev_related){statusEl.textContent='TEV 相关';statusEl.className='gov-card-status tev';}
        else if(p.status==='active'){statusEl.textContent='投票中';statusEl.className='gov-card-status active';}
        else{statusEl.textContent='已结束';statusEl.className='gov-card-status passed';}
      }
      // Update link
      c.href='./governance/';
    }
  }).catch(function(){});

})();
