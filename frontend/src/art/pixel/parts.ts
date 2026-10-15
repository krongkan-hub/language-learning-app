// The parts the pixel characters are composed from: three head shapes, the
// shoulders, hair and hats, and outfits. A 24x28 grid of part labels, scaled
// to the final 36x42 bust by the renderer (render.ts).
//
// Everything between the two "kit.js" banners is docs/design/pixel/kit.js,
// spliced in unchanged, so kit.test.ts can hold the port to it pixel for
// pixel. Parts added for the catalogue's jobs (#62) come after it.
//
// Labels: S skin, H hair, C cloth, c shirt, D cloth shadow, A apron/accent,
// B shirt blue (or vest trim), Y badge, R tie, N hat, K hat shadow.
/* eslint-disable */

// ---------------------------------------------------------------- kit.js ---
export const Wd=24,Ht=28,BY=18; // body starts at row 18
export const HEADS: Record<string, string[]>={
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
export const BODY: string[]=Array(BY).fill('').concat([
'.......CCCCCCCCCC.......','.....CCCCCCCCCCCCCC.....','....CCCCCCCCCCCCCCCC....','...CCCCCCCCCCCCCCCCCC...',
'..CCCCCCCCCCCCCCCCCCCC..','..CCCCCCCCCCCCCCCCCCCC..','..CCCCCCCCCCCCCCCCCCCC..','..CCCCCCCCCCCCCCCCCCCC..','..CCCCCCCCCCCCCCCCCCCC..','..CCCCCCCCCCCCCCCCCCCC..']);
export const HAIR: Record<string, string[]>={
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
function kitOutfit(kind: string): string[] {const o: string[]=Array(Ht).fill('');const p=(dy: number,s: string)=>o[BY+dy]=s;
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
// ---------------------------------------------------------- end kit.js ---

// ------------------------------------------------- added for the catalogue ---
// Parts the 58 speakers' jobs need that the approved kit has no part for
// (docs/design/pixel/speakers.md says who wears which). Drawn on the same
// grid with the same labels, so they go through the same renderer.

/** Outfit rows for `kind`: a kit outfit, or one added below. */
export function outfit(kind: string): string[] {
  return kitOutfit(kind)
}
