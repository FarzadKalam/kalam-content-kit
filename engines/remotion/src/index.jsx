import React from 'react';
import {AbsoluteFill,Audio,Composition,Sequence,interpolate,registerRoot,spring,staticFile,useCurrentFrame,useVideoConfig} from 'remotion';

const fontCss=`@font-face{font-family:Peyda;src:url('${staticFile('assets/fonts/Peyda-Black.woff2')}');font-weight:900}@font-face{font-family:Peyda;src:url('${staticFile('assets/fonts/Peyda-Regular.woff2')}');font-weight:400}`;
const ink='#14251c',green='#198754';
const ease=n=>1-Math.pow(1-n,3);
function Demo(){
  const frame=useCurrentFrame(),{fps}=useVideoConfig();
  const pop=spring({frame:frame-12,fps,config:{damping:17,stiffness:140}});
  const reveal=interpolate(frame,[0,24],[140,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp',easing:ease});
  const chart=frame>=120;
  return <AbsoluteFill style={{background:'#f4f6ef',color:ink,direction:'rtl',fontFamily:'Peyda'}}>
    <style>{fontCss}</style>
    <div style={{position:'absolute',top:260,right:150,fontSize:34,fontWeight:400}}>کیت تدوین کلام · نمونهٔ Remotion</div>
    {!chart?<div style={{position:'absolute',top:500,right:150,left:120}}>
      <div style={{overflow:'hidden'}}><h1 style={{fontSize:140,lineHeight:1.2,margin:0,transform:`translateY(${reveal}%)`}}>معنا را<br/><span style={{color:green}}>به حرکت تبدیل کن</span></h1></div>
      <div style={{marginTop:70,background:green,color:'white',borderRadius:32,padding:'28px 38px',fontSize:46,transform:`scale(${pop})`,transformOrigin:'right'}}>نمونه است، نسخهٔ همهٔ فیلم‌ها نیست</div>
    </div>:<div style={{position:'absolute',top:490,right:150,left:120}}>
      <h1 style={{fontSize:100,lineHeight:1.3,margin:'0 0 60px'}}>یک داده؛<br/>چند شیوهٔ نمایش</h1>
      {[24,52,86].map((v,i)=>{const progress=interpolate(frame,[132+i*5,166+i*5],[0,v],{extrapolateLeft:'clamp',extrapolateRight:'clamp',easing:ease});return <div key={v} style={{display:'flex',gap:28,alignItems:'center',marginBottom:35}}>
        <div style={{height:62,width:570,background:'#dce5df',borderRadius:25,overflow:'hidden'}}><div style={{height:'100%',width:`${progress}%`,background:green,borderRadius:25}}/></div>
        <div style={{fontSize:66,fontWeight:900}}>{Math.round(progress).toLocaleString('fa-IR')}</div>
      </div>})}
      <p style={{fontSize:34,fontWeight:400}}>دادهٔ آزمایشی؛ آمار خبر نیست</p>
    </div>}
    <div style={{position:'absolute',bottom:265,left:120,right:150,borderTop:'2px solid #b9cebf',paddingTop:24,fontSize:34}}>Peyda واقعی · فریم‌محور · رندر محلی</div>
    <Sequence from={12} durationInFrames={8}><Audio src={staticFile('assets/sfx/pop.wav')} volume={.25}/></Sequence>
    <Sequence from={132} durationInFrames={12}><Audio src={staticFile('assets/sfx/scan-ping.wav')} volume={.2}/></Sequence>
  </AbsoluteFill>;
}
registerRoot(()=> <Composition id="KalamDemo" component={Demo} durationInFrames={240} fps={30} width={1080} height={1920}/>);
