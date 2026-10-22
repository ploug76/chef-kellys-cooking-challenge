# Chef Kelly's Cooking Challenge: phone-size UI overlap + controls + leaderboard test
import sys,asyncio,json
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8800/chef-kellys-cooking-challenge/'
VIEWS=[(390,844,None),(360,640,None),(375,667,None),(430,932,None),(320,568,None),(390,844,{'t':47,'r':0,'b':34,'l':0}),(844,390,{'t':0,'r':47,'b':21,'l':47}),(667,375,None),(740,360,None),(1024,768,None)]
CHECK=r'''(tag)=>{const L=__T.layout(),E=L.els,S=L.SAFE,bad=[];const o=(a,b)=>a.x<b.x+b.w-.01&&b.x<a.x+a.w-.01&&a.y<b.y+b.h-.01&&b.y<a.y+a.h-.01;
 for(let i=0;i<E.length;i++){const a=E[i];if(a.x<S.l-.5||a.y<S.t-.5||a.x+a.w>S.r+.5||a.y+a.h>S.b+.5)bad.push(tag+' edge '+a.k+' '+[a.x,a.y,a.w,a.h].map(Math.round));for(let j=i+1;j<E.length;j++)if(o(a,E[j]))bad.push(tag+' '+a.k+' x '+E[j].k)}
 const dk=['shareBtn','instBtn','lbBtn','dockHint'].map(i=>document.getElementById(i)).filter(e=>e&&getComputedStyle(e).display!=='none'&&e.getClientRects().length&&getComputedStyle(document.getElementById('dock')).display!=='none');
 for(const d of dk){const r=d.getBoundingClientRect();const q={x:r.left,y:r.top,w:r.width,h:r.height};for(const a of E)if(o(q,a))bad.push(tag+' dock '+d.id+' x '+a.k)}
 return bad}'''
async def main():
  tot=0;errsAll=[];fails=[]
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for vi,(w,h,safe) in enumerate(VIEWS):
      ctx=await b.new_context(viewport={'width':w,'height':h},is_mobile=True,has_touch=True);pg=await ctx.new_page();await pg.route('https://firestore.googleapis.com/**',lambda r:r.abort());errs=[];pg.on('pageerror',lambda e:errs.append(str(e)));pg.on('console',lambda m:errs.append(m.text) if m.type=='error' else None)
      if safe:await ctx.add_init_script('window.__SAFE='+json.dumps(safe))
      await pg.goto(URL);await pg.wait_for_timeout(700);await pg.evaluate('()=>{window.__CHECK=eval('+json.dumps(CHECK)+');__T.silent=true}')
      await pg.evaluate("()=>{if(window.__dock){__dock.forceInstall()}}");await pg.wait_for_timeout(400)
      bad=[]
      bad+=await pg.evaluate("()=>__CHECK('title')")
      await pg.evaluate("()=>{window.__MANUAL=1;__T.unlockAll()}")
      bad+=await pg.evaluate("()=>{__T.go('map');return __CHECK('map')}")
      for i in range(7):bad+=await pg.evaluate(f"()=>{{__T.go('map');window.sel={i};__T.layout();return []}}")
      for k in range(5):bad+=await pg.evaluate(f"()=>{{__T.setHow({k});return __CHECK('how{k}')}}")
      for i in range(7):
        bad+=await pg.evaluate(f"()=>{{__T.start({i});__T.go('map');sel={i};__T.go('intro');return __CHECK('intro{i}')}}")
        bad+=await pg.evaluate(f"()=>{{__T.start({i});window.__BOT=1;const out=[];for(let k=0;k<8;k++){{__T.step(120);out.push(...__CHECK('play{i}'))}}window.__BOT=0;return out}}")
      bad+=await pg.evaluate("()=>{__T.start(2);__T.step(30);__T.go('pause');return __CHECK('pause')}")
      bad+=await pg.evaluate("()=>{__T.start(0);__T.G.score=170;__T.G.time=.02;__T.step(3);return __CHECK('result')}")
      # real input: tap PLAY on the title, joystick drag + Pick button via pointer/touch events
      ctl={}
      if vi in (0,6):
        await pg.evaluate("()=>{window.__MANUAL=0;__T.go('title')}");await pg.wait_for_timeout(200)
        pb=await pg.evaluate("()=>{__T.layout();const b=BTN.find(b=>b.id==='play');return [b.x+b.w/2,b.y+b.h/2]}")
        await pg.touchscreen.tap(pb[0],pb[1]);await pg.wait_for_timeout(250);ctl['tapPlay']=await pg.evaluate("__T.state")
        await pg.evaluate("()=>{__T.start(0);__T.G.cd=0}");await pg.wait_for_timeout(100)
        L=await pg.evaluate("()=>{const o=playLayout();return {joy:o.joy,pick:o.pick,use:o.use,asg:o.asg,P:[__T.G.P.x,__T.G.P.y]}}")
        j=L['joy'];cx,cy=j[0]+j[2]/2,j[1]+j[3]/2
        await pg.mouse.move(cx,cy);await pg.mouse.down();await pg.mouse.move(cx,cy-60,steps=4);await pg.wait_for_timeout(700);await pg.mouse.up()
        P2=await pg.evaluate("[__T.G.P.x,__T.G.P.y,__T.G.P.dir]");ctl['joyMovedUp']=round(L['P'][1]-P2[1],2)
        # walk to the lettuce crate (top row), press Pick up with a touch tap
        await pg.evaluate("()=>{const G=__T.G;G.P.x=2.5;G.P.y=1.5;G.P.dir=1;G.P.vx=G.P.vy=0}")
        await pg.touchscreen.tap(L['pick'][0],L['pick'][1]);await pg.wait_for_timeout(150);ctl['pickTap']=await pg.evaluate("__T.G.P.hold&&__T.G.P.hold.id")
        if not ctl['pickTap']:ctl['dbg']=await pg.evaluate("(()=>{const G=__T.G;return [G.P.x,G.P.y,G.P.dir,__T.state,G.cd,JSON.stringify(G.P.hold)]})()")
        await pg.evaluate("()=>{const G=__T.G;G.P.x=6.5;G.P.y=1.5;G.P.dir=1}")
        await pg.touchscreen.tap(L['pick'][0],L['pick'][1]);await pg.wait_for_timeout(150)
        ctl['onBoard']=await pg.evaluate("(__T.tileAt(6,0).it||{}).id")
        # hold Chop with the mouse (pointer down for 2.2s)
        await pg.mouse.move(L['use'][0],L['use'][1]);await pg.mouse.down();await pg.wait_for_timeout(2300);await pg.mouse.up()
        ctl['chopped']=await pg.evaluate("(__T.tileAt(6,0).it||{}).id")
        await pg.touchscreen.tap(L['asg'][0],L['asg'][1]);await pg.wait_for_timeout(150);ctl['assignTap']=await pg.evaluate("__T.G.sous[0].task||__T.G.sous[0].say")
        # leaderboard: finish level 1 with no saved name -> name box must accept typing
        await pg.evaluate("()=>{localStorage.removeItem('pa_lb_name');__T.G.score=200;__T.G.time=.05}");await pg.wait_for_timeout(2600)
        inp=pg.locator('#palbCard input')
        if await inp.count():
          bb=await inp.bounding_box();await pg.touchscreen.tap(bb['x']+bb['width']/2,bb['y']+bb['height']/2);await pg.keyboard.type('Kelly');ctl['typed']=await inp.input_value()
          await pg.locator('#palbCard .b',has_text='Save').click();await pg.wait_for_timeout(600);ctl['lbName']=await pg.evaluate("localStorage.getItem('pa_lb_name')")
          ctl['lbRows']=await pg.evaluate("document.querySelectorAll('#palbList li').length")
        else: ctl['lb']='NO NAME BOX'
        ok=ctl.get('tapPlay')=='map' and ctl.get('joyMovedUp',0)>0.3 and ctl.get('pickTap')=='lettuce' and ctl.get('onBoard')=='lettuce' and ctl.get('chopped')=='lettuce_c' and ctl.get('typed')=='Kelly' and ctl.get('lbName')=='Kelly'
        if not ok:fails.append((w,h,ctl))
      print(f"{w}x{h}{' safe' if safe else ''}: overlaps {len(bad)} {bad[:6]} {('controls '+json.dumps(ctl)) if ctl else ''}",flush=True)
      if errs:print('  JS ERRORS',errs[:5])
      tot+=len(bad);errsAll+=errs;await ctx.close()
    await b.close()
  print(f'TOTAL overlaps {tot} js_errors {len(errsAll)} control_failures {len(fails)}');sys.exit(1 if tot or errsAll or fails else 0)
asyncio.run(main())
