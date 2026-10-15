// Pixel character kit: Western, selective outline, 1.5x. Shared by the kit page and the mockups.

const Wd=24,Ht=28,BY=18; // body starts at row 18
const HEADS={
 oval:['........................','........................','........................',
  '........SSSSSSSS........','.......SSSSSSSSSS.......','......SSSSSSSSSSSS......','......SSSSSSSSSSSS......','......SSSSSSSSSSSS......',
  '.....SSSSSSSSSSSSSS.....','.....SSSSSSSSSSSSSS.....','.....SSSSSSSSSSSSSS.....','......SSSSSSSSSSSS......','......SSSSSSSSSSSS......',
  '.......SSSSSSSSSS.......','........SSSSSSSS........','.........SSSSSS.........','.........SSSSSS.........','.........SSSSSS.........'],
 square:['........................','........................','........................',
  '.......SSSSSSSSSS.......','......SSSSSSSSSSSS......','......SSSSSSSSSSSS......','......SSSSSSSSSSSS......','......SSSSSSSSSSSS......',
  '.....SSSSSSSSSSSSSS.....','.....SSSSSSSSSSSSSS.....','.....SSSSSSSSSSSSSS.....','......SSSSSSSSSSSS......','......SSSSSSSSSSSS......',
  '......SSSSSSSSSSSS......','.......SSSSSSSSSS.......','........SSSSSSSS........','.........SSSSSS.........','.........SSSSSS.........'],
 round:['........................','........................','........................',
  '........SSSSSSSS........','......SSSSSSSSSSSS......','.....SSSSSSSSSSSSSS.....','.....SSSSSSSSSSSSSS.....','.....SSSSSSSSSSSSSS.....',
  '.....SSSSSSSSSSSSSS.....','.....SSSSSSSSSSSSSS.....','.....SSSSSSSSSSSSSS.....','.....SSSSSSSSSSSSSS.....','......SSSSSSSSSSSS......',
  '.......SSSSSSSSSS.......','........SSSSSSSS........','.........SSSSSS.........','.........SSSSSS.........','.........SSSSSS.........'],
};
const BODY=Array(BY).fill('').concat([
'.......CCCCCCCCCC.......','.....CCCCCCCCCCCCCC.....','....CCCCCCCCCCCCCCCC....','...CCCCCCCCCCCCCCCCCC...',
'..CCCCCCCCCCCCCCCCCCCC..','..CCCCCCCCCCCCCCCCCCCC..','..CCCCCCCCCCCCCCCCCCCC..','..CCCCCCCCCCCCCCCCCCCC..','..CCCCCCCCCCCCCCCCCCCC..','..CCCCCCCCCCCCCCCCCCCC..']);
const HAIR={
 sidepart:['........................','........HHHHHHHH........','......HHHHHHHHHHHH......','.....HHHHHHHHHHHHHH.....','.....HHHHHHHHHHHHHHH....','.....HHH.....HHHHHHH....','.....HH.........HHH.....','.....H...........H......'],
 curly:['.......H.HH.HH.H........','.....HHHHHHHHHHHHH......','....HHHHHHHHHHHHHHHH....','...HHHHHHHHHHHHHHHHHH...','...HHHHHHHHHHHHHHHHHH...','...HHHHH......HHHHHHH...','...HHH..........HHHH....','....HH...........HH.....','....H.............H.....'],
 long:['........................','........HHHHHHHH........','......HHHHHHHHHHHH......','.....HHHHHHHHHHHHHH.....','....HHHHHHHHHHHHHHHH....','....HHHHH......HHHHH....','....HHH..........HHH....',
   ...Array(10).fill('....HH............HH....'),'....HHH..........HHH....','.....HH..........HH.....'],
 ponytail:['........................','........HHHHHHHH........','......HHHHHHHHHHHH......','.....HHHHHHHHHHHHHHHH...','.....HHHHHHHHHHHHHHHHH..','.....HHH.......HHHHHHH..','.....HH..........HH.HH..','.....H...........H..HH..','....................HH..','....................HH..','...................HH...'],
 buzz:['........................','........................','........................','......HHHHHHHHHHHH......','......HHHHHHHHHHHH......','......HH........HH......'],
 bald:[...Array(8).fill('........................'),'.....HH..........HH.....','.....HH..........HH.....'],
 bob:['........................','........HHHHHHHH........','......HHHHHHHHHHHH......','.....HHHHHHHHHHHHHH.....','....HHHHHHHHHHHHHHHH....','....HHHHHHHHHHHHHHHH....','....HHH..........HHH....',
   ...Array(6).fill('....HH............HH....'),'....HHH..........HHH....'],
 cap:['........................','........NNNNNNNN........','......NNNNNNNNNNNN......','.....NNNNNNYYNNNNNN.....','.....NNNNNNNNNNNNNN.....','....KKKKKKKKKKKKKKKK....','.....HH..........HH.....'],
 beanie:['..........NN............','........NNNNNNNN........','......NNNNNNNNNNNN......','.....NNNNNNNNNNNNNN.....','.....YYYYYYYYYYYYYY.....','.....HH..........HH.....'],
 strawhat:['........NNNNNNNN........','.......NNNNNNNNNN.......','.......NNNNNNNNNN.......','.......KKKKKKKKKK.......','..NNNNNNNNNNNNNNNNNNNN..','.....HH..........HH.....'],
 bun:['..........HHHH..........','.........HHHHHH.........','.......HHHHHHHHHH.......','.....HHHHHHHHHHHHHH.....','.....HHHHHHHHHHHHHH.....','.....HHH........HHH.....','.....HH..........HH.....'],
};
function outfit(kind){const o=Array(Ht).fill('');const p=(dy,s)=>o[BY+dy]=s;
 if(kind==='apron'){p(0,'.......CCCcccccCCC......');p(1,'.....CCCCCccccCCCCC.....');p(2,'....CCCCCCCccCCCCCCC....');p(3,'...CCCAAAAAAAAAAAACCC...');for(let d=4;d<10;d++)p(d,'..CCCAAAAAAAAAAAAAACCC..');p(6,'..CCCAAAAAAYYAAAAAACCC..')}
 if(kind==='coat'){p(0,'.......CCCcBBBBcCCC......');p(1,'.....CCCCCcBBBBcCCCC.....');p(2,'....CCCCCCCcBBcCCCCCC...');for(let d=3;d<10;d++)p(d,'..CCCCCCCCCDCCCCCCCCCC..');p(5,'..CCCKKCCCCDCCCCCCCCCC..')}
 if(kind==='uniform'){p(2,'....CCCCCCCYCCCCCCCC....');p(3,'...YCCCCCCCCCCCCCCCCY...');p(4,'..CCCCCCCCCYCCCCCCCCCC..');p(6,'..CCCCCCCCCYCCCCCCCCCC..');p(8,'..CCCCCCCCCYCCCCCCCCCC..')}
 if(kind==='blazer'){p(0,'.......CCCcccccCCC......');p(1,'.....CCCCCccRRccCCCC....');p(2,'....CCCCCCccRRccCCCCC...');p(3,'...CCCCCCCCcRRcCCCCCCC..');p(4,'..CCCCCCCCCCRRCCCCCCCCC.');p(5,'..CCCCCCCCCCDCCCCCCCCC..')}
 if(kind==='flannel'){for(let d=0;d<10;d++){let s='';const row=BODY[BY+d];for(let x=0;x<Wd;x++)s+=row[x]==='C'?((x+d)%4<2?'C':'D'):'.';p(d,s)}p(0,'.......CCCcccccCCC......')}
 if(kind==='hoodie'){p(1,'.....CCCDCCCCCCDCCC.....');p(2,'....CCCCcCCCCCCcCCCC....');p(3,'...CCCCCcCCCCCCcCCCCC...');p(7,'..CCCCCDDDDDDDDCCCCCCC..');p(8,'..CCCCCDCCCCCCDCCCCCCC..')}
 if(kind==='cardigan'){p(0,'.......CCCcccccCCC......');p(1,'.....CCCCCcccccCCCC.....');p(2,'....CCCCCCCcccCCCCCC....');for(let d=3;d<10;d++)p(d,'..CCCCCCCCCDDCCCCCCCCC..');p(4,'..CCCCCCCCCYDCCCCCCCCC..');p(7,'..CCCCCCCCCYDCCCCCCCCC..')}
 if(kind==='tank'){p(0,'.......SSSSSSSSSS.......');p(1,'.....SSSSCCCCCCSSSS.....');p(2,'....SSSSCCCCCCCCSSSS....');p(3,'...SSSSCCCCCCCCCCSSSS...')}
 if(kind==='winvest'){ // Thai motorcycle-taxi vest: orange, number patch, reflective strips, over a shirt
   ['.......BBBcccccBBB......','.....BBBBCCcccCCBBBB....','....BBBCCCCCcCCCCCBBB...','...BBBCCCCCCCCCCCCCBBB..',
    '..BBBBCCYYYYYYYYYCCBBBB.','..BBBBCCCcccCCCCCCCBBBB.','..BBBBCCCcDcCCCCCCCBBBB.','..BBBBCCCcccCCCCCCCBBBB.',
    '..BBBBCCYYYYYYYYYCCBBBB.','..BBBBCCCCCCCCCCCCCBBBB.'].forEach((r,d)=>p(d,r))}
 if(kind==='barvest'){ // bartender: white shirt, black waistcoat, bow tie
   ['.......ccccRRcccc.......','.....cccccRRRRccccc.....','....ccCCCccRRccCCCcc....','...cccCCCCcccccCCCCccc..',
    '..ccccCCCCCccCCCCCcccc..','..ccccCCCCCcDCCCCCcccc..','..ccccCCCCCccCCCCCcccc..','..ccccCCCCCcDCCCCCcccc..',
    '..ccccCCCCCccCCCCCcccc..','..ccccCCCCCccCCCCCcccc..'].forEach((r,d)=>p(d,r))}
 if(kind==='gown'){ // prom: off-shoulder gown
   ['.......SSSSSSSSSS.......','.....SSSSSSSSSSSSSS.....','....SSSSSSSSSSSSSSSS....','...SSSSCCCCCCCCCCSSSS...',
    '..SSSSCCCCCCCCCCCCSSSS..','..SSSSCCCCCYCCCCCCSSSS..','..SSSSCCCCCCCCCCCCSSSS..','..SSSSCCCCCCCCCCCCSSSS..',
    '..SSSSCCCCCCCCCCCCSSSS..','..SSSSCCCCCCCCCCCCSSSS..'].forEach((r,d)=>p(d,r))}
 return o}
// faces: brows (b), eye whites (w), pupils (p), mouth (m), teeth (t), dark (d)
const FACES={
 neutral:{b:[[8,7],[9,7],[10,7],[13,7],[14,7],[15,7]],w:[[8,8],[9,8],[14,8],[15,8]],p:[[9,8],[14,8]],m:[[10,12],[11,12],[12,12]]},
 smile:{b:[[8,7],[9,6],[10,7],[13,7],[14,6],[15,7]],w:[[8,8],[9,8],[14,8],[15,8]],p:[[9,8],[14,8]],m:[[9,11],[10,12],[13,12],[14,11]],t:[[11,12],[12,12]]},
 surprised:{b:[[8,6],[9,5],[10,6],[13,6],[14,5],[15,6]],w:[[8,8],[9,8],[14,8],[15,8],[8,9],[9,9],[14,9],[15,9]],p:[[9,8],[14,8]],m:[[11,12],[12,12],[11,13],[12,13]]},
 confused:{b:[[8,7],[9,7],[10,7],[13,6],[14,5],[15,6]],w:[[8,8],[9,8],[14,8],[15,8]],p:[[8,8],[14,8]],m:[[10,12],[11,12],[12,13],[13,13]]},
 annoyed:{b:[[8,6],[9,6],[10,7],[13,7],[14,6],[15,6]],w:[[8,8],[9,8],[14,8],[15,8]],p:[[9,8],[14,8]],m:[[9,12],[10,12],[11,12],[12,12],[13,12]]},
 sad:{b:[[8,7],[9,7],[10,6],[13,6],[14,7],[15,7]],w:[[8,9],[9,9],[14,9],[15,9]],p:[[9,9],[14,9]],m:[[9,13],[10,12],[11,12],[12,12],[13,13]]},
};
const SKIN={a:'#f2cfae',b:'#e2ad84',c:'#bf855a',d:'#8a5a3c',e:'#5e3a28'};
const HAIRC={brown:'#6e4328',black:'#2c2830',blond:'#d4a64c',ginger:'#b5552e',gray:'#9d9aa3',white:'#e6e2dc',auburn:'#7d3324'};
function compose(ch){
  const g=Array.from({length:Ht},()=>Array(Wd).fill('.'));
  const lay=rows=>rows.forEach((r,y)=>[...(r||'')].forEach((c,x)=>{if(c!=='.')g[y][x]=c}));
  lay(BODY);lay(outfit(ch.outfit));lay(HEADS[ch.head||'oval']);
  for(const y of [9,10]){g[y][4]='S';g[y][19]='S'}
  lay(HAIR[ch.hair]);
  if(ch.beard){for(let y=11;y<=16;y++)for(let x=5;x<19;x++){if(g[y][x]==='S'&&(y>=13||x<8||x>15))g[y][x]='Hf'}}
  return g;
}
function rgb(c){return [1,3,5].map(i=>parseInt(c.slice(i,i+2),16))}
function sh(c,f){const [r,g,b]=rgb(c);const m=v=>Math.max(0,Math.min(255,Math.round(f>1?v+(255-v)*(f-1):v*f)));return '#'+[m(r),m(g),m(b)].map(v=>v.toString(16).padStart(2,'0')).join('')}
function mix(a,b,t){const A=rgb(a),B=rgb(b);return '#'+A.map((v,i)=>Math.round(v+(B[i]-v)*t).toString(16).padStart(2,'0')).join('')}
// hi-res faces (48-wide grid). Left eye x16..19, right eye x28..31, eye row 16..17.
function face(m){
  const F={brows:[],eyes:[],mouth:[]};
  const brow=(x0,dir,lift)=>{ // 6px brow, dir +1 = left brow
    const ys=lift; for(let i=0;i<6;i++){const x=x0+i;const y=13+ys[i];F.brows.push([x,y]);if(i===2||i===3)F.brows.push([x,y+1])}};
  const flat=[0,0,0,0,0,1].map(v=>v),
    L={neutral:[1,0,0,0,0,1],smile:[1,0,-1,-1,0,0],surprised:[0,-1,-2,-2,-1,-1],confused:[1,0,0,0,0,1],annoyed:[-1,-1,0,0,1,2],sad:[1,1,0,0,-1,-2]},
    R={neutral:[1,0,0,0,0,1],smile:[0,0,-1,-1,0,1],surprised:[-1,-1,-2,-2,-1,0],confused:[-1,-2,-3,-3,-2,-1],annoyed:[2,1,0,0,-1,-1],sad:[-2,-1,0,0,1,1]};
  brow(15,1,L[m]);brow(27,-1,R[m]);
  const eyeOpen=m==='surprised'?3:m==='annoyed'?1:2, eyeTop=m==='sad'?17:16;
  F.eyeOpen=eyeOpen;F.eyeTop=eyeTop;F.look=m==='confused'?-1:0;
  const M={
   neutral:{lip:[[21,26],[22,26],[23,26],[24,26],[25,26]],low:[[22,27],[23,27],[24,27]]},
   smile:{lip:[[19,25],[20,26],[21,27],[22,27],[23,27],[24,27],[25,27],[26,26],[27,25]],teeth:[[21,26],[22,26],[23,26],[24,26],[25,26]],low:[[22,28],[23,28],[24,28]]},
   surprised:{lip:[[22,25],[23,25],[24,25],[25,25],[21,26],[26,26],[21,27],[26,27],[22,28],[23,28],[24,28],[25,28]],dark:[[22,26],[23,26],[24,26],[25,26],[22,27],[23,27],[24,27],[25,27]]},
   confused:{lip:[[20,26],[21,26],[22,26],[23,27],[24,27],[25,27],[26,26]],low:[[22,28],[23,28],[24,28]]},
   annoyed:{lip:[[19,26],[20,26],[21,26],[22,26],[23,26],[24,26],[25,26],[26,26],[27,26],[28,26]],low:[]},
   sad:{lip:[[19,27],[20,26],[21,26],[22,26],[23,26],[24,26],[25,26],[26,26],[27,26],[28,27]],low:[[22,27],[23,27],[24,27],[25,27]]},
  }[m];F.mouth=M;return F;
}

// Hand-drawn faces, one per mood, at the final 36x42 resolution.
// b/B brow, l lid, w white, i iris, I iris light, h catch-light, e/s soft shade, n/N/H nose, m/M lips, p lower lip, t teeth, o open mouth, c cheek warmth
const HANDFACES={
 neutral:[
  '....................',
  '...Bbbb.....bbbB....',
  '....................',
  '...llll.....llll....',
  '...whiw.....wihw....',
  '...eiie.....eiie....',
  '.........H..........',
  '..c.......n......c..',
  '..cc....NnnN....cc..',
  '....................',
  '.......mmmmmm.......',
  '........pppp........',
  '.........ss.........'],
 smile:[
  '....................',
  '...Bbbb.....bbbB....',
  '....................',
  '...llll.....llll....',
  '...whiw.....wihw....',
  '...ssss.....ssss....',
  '.........H..........',
  '.cc.......n.....cc..',
  '.ccc....NnnN....ccc.',
  '......m......m......',
  '.......mttttm.......',
  '........pppp........',
  '.........ss.........'],
 surprised:[
  '...Bbbb.....bbbB....',
  '....................',
  '...llll.....llll....',
  '...whiw.....wihw....',
  '...wiiw.....wiiw....',
  '...eeee.....eeee....',
  '.........H..........',
  '..c.......n......c..',
  '..cc....NnnN....cc..',
  '........mmmm........',
  '.......moooom.......',
  '........mppm........',
  '.........ss.........'],
 confused:[
  '.............bbbB...',
  '...Bbbb.....b.......',
  '....................',
  '...llll.....llll....',
  '...hiww.....hiww....',
  '...iiee.....iiee....',
  '.........H..........',
  '..c.......n......c..',
  '..cc....NnnN....cc..',
  '....................',
  '.......mm..mmm......',
  '.........mm.........',
  '.........ss.........'],
 annoyed:[
  '....................',
  '...BBb.......bBB....',
  '......b.....b.......',
  '...llll.....llll....',
  '...wiiw.....wiiw....',
  '...ssss.....ssss....',
  '.........H..........',
  '..........n.........',
  '........NnnN........',
  '....................',
  '.......MMMMMM.......',
  '....................',
  '.........ss.........'],
 sad:[
  '.....bB.....Bb......',
  '...Bb.........bB....',
  '....................',
  '...llll.....llll....',
  '...whiw.....wihw....',
  '...eiie.....eiie....',
  '.........H..........',
  '..........n.........',
  '........NnnN........',
  '....................',
  '........mmmm........',
  '.......m....m.......',
  '.........ss.........'],
};
function draw(cv,ch){
  const lo=compose(ch);const SC=0.75,W4=Wd*2,H4=Ht*2,W2=Math.round(W4*SC),H2=Math.round(H4*SC);
  cv.width=W2+2;cv.height=H2+2;const c=cv.getContext('2d');c.clearRect(0,0,cv.width,cv.height);
  // EPX / Scale2x on the part labels: diagonals become smooth curves instead of 2x2 stairs
  const L=(x,y)=>(lo[y]||[])[x]||'.';
  const g48=Array.from({length:H4},()=>Array(W4).fill('.'));
  for(let y=0;y<Ht;y++)for(let x=0;x<Wd;x++){const P0=L(x,y),A=L(x,y-1),B=L(x+1,y),C=L(x-1,y),D=L(x,y+1);
    let e1=P0,e2=P0,e3=P0,e4=P0;
    if(C===A&&C!==D&&A!==B)e1=A; if(A===B&&A!==C&&B!==D)e2=B; if(D===C&&D!==B&&C!==A)e3=C; if(B===D&&B!==A&&D!==C)e4=D;
    g48[2*y][2*x]=e1;g48[2*y][2*x+1]=e2;g48[2*y+1][2*x]=e3;g48[2*y+1][2*x+1]=e4}
  const g=Array.from({length:H2},(_,y)=>Array.from({length:W2},(_,x)=>g48[Math.min(H4-1,Math.round(y/SC))][Math.min(W4-1,Math.round(x/SC))]));
  const S=SKIN[ch.skin],Hc=HAIRC[ch.hairColor];
  const col={S,H:Hc,Hf:sh(Hc,.92),C:ch.cloth,c:'#efece4',A:ch.accent||'#b8834a',D:sh(ch.cloth,.74),N:ch.hatColor||'#2f3f6b',Y:ch.badge||'#e2b64a',K:sh(ch.hatColor||'#2f3f6b',.62),R:ch.tie||'#b23a48',B:'#7da2d6'};
  const region=k=>k==='S'?'S':(k==='H'||k==='Hf')?'H':'NYK'.includes(k)?'N':k==='.'?'.':'C';
  const buf=Array.from({length:H2},()=>Array(W2).fill(null));
  const inR=(x,y,r)=>x>=0&&y>=0&&x<W2&&y<H2&&region(g[y][x])===r;
  // 1) base + 3-tone volume shading (light from top-left)
  for(let y=0;y<H2;y++)for(let x=0;x<W2;x++){const k=g[y][x];if(k==='.')continue;const r=region(k);let v=col[k]||col.C;
    let dr=0;while(dr<5&&inR(x+dr+1,y,r)&&inR(x,y+dr+1,r))dr++;
    let dl=0;while(dl<3&&inR(x-dl-1,y,r)&&inR(x,y-dl-1,r))dl++;
    if(r==='S'){ // skin: one soft step, only on the shadow side of the face, so the jaw never reads as stubble
      let hr=0;while(hr<3&&inR(x+hr+1,y,r))hr++;
      if(hr<=1&&x>W2/2)v=sh(v,.92);
    }else if(dr<=0)v=sh(v,.76);else if(dr<=2)v=sh(v,.88);
    else if(dl===0)v=sh(v,r==='S'?1.05:1.14);
    if(r==='H'){ // strands + shine band
      if((x*2+y)%9===0)v=sh(v,.84);
      if((x+y*3)%11===0)v=sh(v,1.12);
      const top=(()=>{let t=0;while(t<6&&inR(x,y-t-1,'H'))t++;return t})();
      if(top>=2&&top<=3&&x<W2/2+4&&k==='H')v=mix(v,'#ffffff',.22);
    }
    if(r==='C'&&k==='C'){ // cloth folds
      if((x-y)%13===0&&y>H2*0.75)v=sh(v,.86);
      if((x+y)%17===0&&y>H2*0.8)v=sh(v,.9);
    }
    buf[y][x]=v}
  const P=(x,y,v)=>{if(x>=0&&y>=0&&x<W2&&y<H2)buf[y][x]=v};
  const skin=(x,y,f)=>{if(region(g[y]?.[x])==='S')P(x,y,sh(S,f))};
  // 2) under-hair and under-chin shadows
  for(let y=1;y<H2;y++)for(let x=0;x<W2;x++){
    if(g[y][x]==='S'&&region(g[y-1][x])==='H')P(x,y,sh(S,.9));
    if(g[y][x]==='S'&&y>=2&&g[y-2][x]==='S'&&region(g[y-2]?.[x])==='S'&&y>=Math.round(30*SC)&&y<Math.round(36*SC))P(x,y,sh(S,.8));
  }
  const Q=(x,y,v)=>P(Math.round(x*SC),Math.round(y*SC),v);
  const skinQ=(x,y,f)=>skin(Math.round(x*SC),Math.round(y*SC),f);
  // ear inner
  [[9,19],[9,20],[38,19],[38,20]].forEach(([x,y])=>skinQ(x,y,.78));
  // 3) face — hand-drawn per mood at the final resolution (origin x9,y10; 20x13). Only paints over skin.
  const lash=mix(sh(Hc,.55),'#5a3a30',.4),iris=ch.iris||'#5b7a9a';
  const lipC=mix(sh(S,.8),'#c25f5f',.4);
  const FP={b:sh(Hc,.8),B:sh(Hc,.94),l:lash,w:'#f4f1ea',i:mix(iris,'#2a2230',.45),I:mix(iris,'#ffffff',.1),h:'#ffffff',
    e:sh(S,.93),s:sh(S,.93),n:sh(S,.9),N:sh(S,.8),H:sh(S,1.06),m:lipC,M:sh(lipC,.75),p:mix(S,'#c8706a',.3),t:'#f6f1e6',o:'#7a3a3a',c:mix(S,'#e88a7a',.16)};
  const rows=HANDFACES[ch.mood||'neutral']||HANDFACES.neutral;
  rows.forEach((r,dy)=>[...r].forEach((k,dx)=>{const x=9+dx,y=10+dy;if(k==='.'||!FP[k])return;
    if(region(g[y]?.[x])!=='S')return;P(x,y,FP[k])}));
  if(ch.old){[[19,10],[20,10],[21,10],[26,10],[27,10],[28,10],[14,17],[14,18],[33,17],[33,18],[20,23],[20,24],[27,23],[27,24]].forEach(([x,y])=>skinQ(x,y,.8))}
  if(ch.mustache){for(let x=19;x<=28;x++){Q(x,24,sh(Hc,.9));if(x>19&&x<28)Q(x,25,sh(Hc,x%2?.8:.95))}}
  if(ch.stubble){for(let y=24;y<=32;y++)for(let x=12;x<36;x++)if(region(g[Math.round(y*SC)]?.[Math.round(x*SC)])==='S'&&(x*3+y*5)%4===0&&!(y>=25&&y<=28&&x>=19&&x<=28))skinQ(x,y,.84)}
  if(ch.beard){for(let y=22;y<36;y++)for(let x=8;x<40;x++)if(region(g[Math.round(y*SC)]?.[Math.round(x*SC)])==='H'&&(x+y*2)%5===0)Q(x,y,sh(Hc,.78))}
  if(ch.glasses){const fr='#3e3848';for(const ex of [15,27]){for(let i=0;i<6;i++){Q(ex+i,15,fr);Q(ex+i,19,fr)}for(let y=15;y<=19;y++){Q(ex,y,fr);Q(ex+5,y,fr)}}Q(21,16,fr);Q(22,16,fr);Q(23,16,fr);Q(24,16,fr);Q(25,16,fr);Q(26,16,fr)
    for(const ex of [16,28]){Q(ex,16,mix(buf[Math.round(16*SC)][Math.round(ex*SC)]||'#fff','#ffffff',.5))}}
  // 4) paint
  for(let y=0;y<H2;y++)for(let x=0;x<W2;x++)if(buf[y][x]){c.fillStyle=buf[y][x];c.fillRect(x+1,y+1,1,1)}
  // 5) selective outline at hi-res
  const at=(x,y)=>(g[y]||[])[x]||'.';
  for(let y=-1;y<=H2;y++)for(let x=-1;x<=W2;x++){
    const k=at(x,y);const nb=[[1,0],[-1,0],[0,1],[0,-1]].map(([a,b])=>at(x+a,y+b));
    if(k==='.'){const src=nb.find(n=>n!=='.');if(src){const r=region(src);const base=r==='S'?S:r==='H'?Hc:r==='N'?col.N:(col[src]||col.C);c.fillStyle=sh(base,r==='S'?.62:.48);c.fillRect(x+1,y+1,1,1)}}
    else if(region(k)==='H'&&nb.some(n=>region(n)==='S')){c.fillStyle=sh(Hc,.68);c.fillRect(x+1,y+1,1,1)}
    else if(region(k)==='S'&&nb.some(n=>region(n)==='C')&&y>=Math.round(34*SC)){c.fillStyle=sh(S,.72);c.fillRect(x+1,y+1,1,1)}
  }
}
