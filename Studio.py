import pygame_sdl2, sys, colorsys, copy, os, time
pygame.init()

info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
TOUCH_W, TOUCH_H = screen.get_size()
clock = pygame.time.Clock()

# ANINDA SPLASH
screen.fill((10,10,15))
_sf = pygame.font.SysFont("monospace", int(WIDTH//8), bold=True)
_t  = _sf.render("Pixel Editor", True, (0,150,255))
screen.blit(_t, (WIDTH//2-_t.get_width()//2, HEIGHT//2-_t.get_height()//2))
_sub = _sf.render("Yukleniyor...", True, (60,60,90))
screen.blit(_sub, (WIDTH//2-_sub.get_width()//2, HEIGHT//2+_t.get_height()+10))
pygame.display.flip()
pygame.event.pump()

ACCENT=(0,150,255); WHITE=(250,250,250); BLACK=(10,10,10)
GRID_COLOR=(10,50,50); UI_PANEL=(20,20,20)
BG_COLOR=(15,15,15)
CANVAS_BG=(40,40,40)

CANVAS_SIZE=64

def make_canvas(size=None):
    sz = size or CANVAS_SIZE
    s = pygame.Surface((sz, sz))
    s.fill(CANVAS_BG)
    return s

canvas_surf = make_canvas()

undo_stack=[]; redo_stack=[]; MAX_UNDO=20

BASE_GRID=WIDTH//15; grid_size=BASE_GRID
zoom, cam_x, cam_y = 1.0, 0, 0
draw_tool="Draw"; brush_size=1
active_slider=None

selection_start=None; selection_rect=None
moving_selection=False; selected_data={}
copy_data=None

_sel_last_gx = None
_sel_last_gy = None
_sel_surface = None
_sel_baked_gs = 0

_scaled_surf = None
_scaled_gs = 0

def save_state():
    undo_stack.append(canvas_surf.copy())
    if len(undo_stack)>MAX_UNDO: undo_stack.pop(0)
    redo_stack.clear()

def bake_selection_surface(sel_data, gs):
    global _sel_surface, _sel_baked_gs
    if not sel_data:
        _sel_surface = None; _sel_baked_gs = 0; return
    xs=[ox for (ox,oy) in sel_data]; ys=[oy for (ox,oy) in sel_data]
    w=max(1,(max(xs)+1)*gs); h=max(1,(max(ys)+1)*gs)
    w=min(w,WIDTH*2); h=min(h,HEIGHT*2)
    TRANSPARENT=(1,1,1)
    surf=pygame.Surface((w,h)); surf.fill(TRANSPARENT); surf.set_colorkey(TRANSPARENT)
    for (ox,oy),val in sel_data.items():
        px,py=ox*gs,oy*gs
        if px<w and py<h:
            col=val if isinstance(val,tuple) else int_to_rgb(val)
            surf.fill(col,(px,py,min(gs,w-px),min(gs,h-py)))
    _sel_surface=surf; _sel_baked_gs=gs

def hsl_to_int(h,l,s):
    r,g,b=colorsys.hls_to_rgb(h,l,s)
    return (int(r*255)<<16)|(int(g*255)<<8)|int(b*255)

def int_to_rgb(col):
    return ((col>>16)&255,(col>>8)&255,col&255)

safe_y=HEIGHT; bar_w=int(WIDTH*1)-20

font = pygame.font.SysFont("monospace", int(WIDTH//26), bold=True)
font_small = pygame.font.SysFont("monospace", int(WIDTH//35), bold=True)
#hue konumları
SLIDER_Y = HEIGHT - 600
hue_rect   = pygame.Rect(10, SLIDER_Y,      bar_w, 36)
sat_rect   = pygame.Rect(10, SLIDER_Y+86,   bar_w, 36)
light_rect = pygame.Rect(10, SLIDER_Y+170,   bar_w, 36)
size_rect  = pygame.Rect(10, SLIDER_Y+250,  bar_w, 28)

hue_surf  = pygame.Surface((bar_w,40))
sat_surf  = pygame.Surface((bar_w,40))
light_surf= pygame.Surface((bar_w,40))

current_hue, current_sat, current_light = 0, 1, 0.5
current_color=0

def _fill_surf_hsl(surf, h_arr, l_arr, s_arr):
    import numpy as np
    w=surf.get_width()
    arr=pygame.surfarray.pixels3d(surf)
    # colorsys ile doğru renk, ama vektörize şekilde
    h=np.asarray(h_arr); l=np.asarray(l_arr); s=np.asarray(s_arr)
    rgb=np.array([colorsys.hls_to_rgb(float(h[i]),float(l[i]),float(s[i])) for i in range(w)], dtype=np.float32)
    arr[:,0,0]=(rgb[:,0]*255).astype(np.uint8)
    arr[:,0,1]=(rgb[:,1]*255).astype(np.uint8)
    arr[:,0,2]=(rgb[:,2]*255).astype(np.uint8)
    arr[:]=arr[:,0:1,:]
    del arr

def _build_hue_surf():
    import numpy as np
    steps=np.linspace(0,1,bar_w)
    _fill_surf_hsl(hue_surf,steps,np.full(bar_w,0.5),np.ones(bar_w))

_last_update_hue=-1
_last_update_sat=-1

def update_color():
    global current_color, _last_update_hue, _last_update_sat
    import numpy as np
    current_color=hsl_to_int(current_hue,current_light,current_sat)
    steps=np.linspace(0,1,bar_w)
    if abs(current_hue-_last_update_hue)>0.001 or abs(current_sat-_last_update_sat)>0.001:
        _fill_surf_hsl(sat_surf,  np.full(bar_w,current_hue),np.full(bar_w,0.5),steps)
        _fill_surf_hsl(light_surf,np.full(bar_w,current_hue),steps,np.full(bar_w,current_sat))
        _last_update_hue=current_hue; _last_update_sat=current_sat

def draw_pixel(gx,gy,val):
    col = CANVAS_BG if val is None else (int_to_rgb(val) if isinstance(val,int) else val)
    if brush_size==1:
        if 0<=gx<CANVAS_SIZE and 0<=gy<CANVAS_SIZE:
            canvas_surf.set_at((gx,gy),col)
            if _scaled_surf and _scaled_gs==grid_size:
                _scaled_surf.fill(col,(gx*grid_size,gy*grid_size,grid_size,grid_size))
        return
    offset=brush_size//2
    for ox in range(-offset,brush_size-offset):
        for oy in range(-offset,brush_size-offset):
            tx,ty=gx+ox,gy+oy
            if 0<=tx<CANVAS_SIZE and 0<=ty<CANVAS_SIZE:
                canvas_surf.set_at((tx,ty),col)
                if _scaled_surf and _scaled_gs==grid_size:
                    _scaled_surf.fill(col,(tx*grid_size,ty*grid_size,grid_size,grid_size))

def bucket_fill(gx,gy,new_color):
    if not (0<=gx<CANVAS_SIZE and 0<=gy<CANVAS_SIZE): return
    new_rgb=int_to_rgb(new_color) if isinstance(new_color,int) else new_color
    target_rgb=canvas_surf.get_at((gx,gy))[:3]
    if target_rgb==new_rgb: return
    try:
        pygame.draw.flood_fill(canvas_surf,new_rgb,(gx,gy))
    except AttributeError:
        stack=[(gx,gy)]; visited=set()
        while stack:
            x,y=stack.pop()
            if (x,y) in visited: continue
            visited.add((x,y))
            if 0<=x<CANVAS_SIZE and 0<=y<CANVAS_SIZE and canvas_surf.get_at((x,y))[:3]==target_rgb:
                canvas_surf.set_at((x,y),new_rgb)
                stack.extend([(x+1,y),(x-1,y),(x,y+1),(x,y-1)])
    globals()['_scaled_gs']=-1

SAVE_FOLDERS=[
    ("Pictures/PixelEditor","Pictures/\nPixelEditor"),
    ("Pictures","Pictures"),
    ("Downloads","Downloads"),
    ("DCIM/PixelArt","DCIM/\nPixelArt"),
]
sel_folder=0
EXPORT_SIZE_CFG=16
save_error_msg=""

def make_preview():
    return pygame.transform.scale(canvas_surf,(300,300))

def save_image():
    global save_error_msg
    EXPORT=EXPORT_SIZE_CFG
    # surfarray ile hızlı alpha export
    tmp_surf=pygame.Surface((CANVAS_SIZE,CANVAS_SIZE),pygame.SRCALPHA)
    rgb=pygame.surfarray.pixels3d(canvas_surf)
    dst=pygame.surfarray.pixels3d(tmp_surf)
    alpha=pygame.surfarray.pixels_alpha(tmp_surf)
    dst[:]=rgb[:]
    # CANVAS_BG piksellerini şeffaf yap
    bg=CANVAS_BG
    mask=((rgb[:,:,0]==bg[0])&(rgb[:,:,1]==bg[1])&(rgb[:,:,2]==bg[2]))
    alpha[:]=255
    alpha[mask]=0
    del rgb,dst,alpha
    surf=pygame.transform.scale(tmp_surf,(EXPORT,EXPORT))
    fname=f"pixel_{int(time.time())}.png"
    folder=SAVE_FOLDERS[sel_folder][0]
    try:
        direct=f"/storage/emulated/0/{folder}/{fname}"
        os.makedirs(os.path.dirname(direct),exist_ok=True)
        pygame.image.save(surf,direct)
        save_error_msg=f"OK: {direct}"; return
    except: pass
    try:
        from jnius import autoclass
        CV=autoclass("android.content.ContentValues")
        MS=autoclass("android.provider.MediaStore")
        PA=autoclass("org.kivy.android.PythonActivity")
        ctx=PA.mActivity
        tmp=f"/data/data/{ctx.getPackageName()}/cache/{fname}"
        os.makedirs(os.path.dirname(tmp),exist_ok=True)
        pygame.image.save(surf,tmp)
        res=ctx.getContentResolver(); v=CV()
        v.put(MS.Images.Media.DISPLAY_NAME,fname)
        v.put(MS.Images.Media.MIME_TYPE,"image/png")
        v.put(MS.Images.Media.RELATIVE_PATH,folder)
        v.put(MS.Images.Media.IS_PENDING,1)
        uri=res.insert(MS.Images.Media.EXTERNAL_CONTENT_URI,v)
        s=res.openOutputStream(uri)
        with open(tmp,"rb") as f: data=f.read()
        s.write(bytearray(data)); s.flush(); s.close()
        v2=CV(); v2.put(MS.Images.Media.IS_PENDING,0)
        res.update(uri,v2,None,None)
        save_error_msg=f"OK(MediaStore): {fname}"
    except Exception as e:
        save_error_msg=f"Hata: {e}"

tool_list=["Draw","Erase","Pick","Fill","Sel","Rect","Undo","Redo",":"]

TOOLBAR_W = int(WIDTH*0.10)
TOOLBAR_X = WIDTH - TOOLBAR_W - 15
def get_btn_rect(i):
    n=len(tool_list)
    bh=HEIGHT//n - 80
    return pygame.Rect(TOOLBAR_X, 4+i*(bh+6), TOOLBAR_W, bh)

SEL_TOOL_Y=120
HAM_W=int(WIDTH*0.28)
HAM_X=TOOLBAR_X-HAM_W-8
HAM_BH=int(HEIGHT*0.08)
ham_save_rect=pygame.Rect(HAM_X, 4,            HAM_W, HAM_BH)
ham_cfg_rect =pygame.Rect(HAM_X, 4+HAM_BH+8,  HAM_W, HAM_BH)
SEL_TOOL_W=WIDTH//4
SEL_TOOL_H=60
copy_btn_rect  =pygame.Rect(50,              SEL_TOOL_Y,SEL_TOOL_W-20,SEL_TOOL_H)
paste_btn_rect =pygame.Rect(50+SEL_TOOL_W,  SEL_TOOL_Y,SEL_TOOL_W-20,SEL_TOOL_H)
delete_btn_rect=pygame.Rect(50+SEL_TOOL_W*2,SEL_TOOL_Y,SEL_TOOL_W-20,SEL_TOOL_H)

show_cfg_panel=False
show_save_panel=False
show_selection_tools=False
show_hamburger=False
_cfg_cache={}
_last_btn_time=0
_cfg_rects_dirty=True
_cfg_rects=None
_prev_surf=None
save_feedback_timer=0
copy_feedback_timer=0
copy_feedback_msg=""
cfg_active=None
cfg_canvas_str=str(CANVAS_SIZE)
cfg_export_str=str(EXPORT_SIZE_CFG)

fingers,last_midpoint={},None
is_drawing=zoom_mode=False
last_gx=last_gy=None
start_dist=start_zoom=1.0

BH=int(HEIGHT*0.08)
BW=WIDTH-160
BX=80

def draw_loading(msg,progress):
    screen.fill((10,10,15))
    title=font.render("Pixel Editor",True,ACCENT)
    sub=font.render("by you",True,(60,60,80))
    screen.blit(title,(WIDTH//2-title.get_width()//2,HEIGHT//3-30))
    screen.blit(sub,(WIDTH//2-sub.get_width()//2,HEIGHT//3+title.get_height()+4))
    bar_total=WIDTH-160; bar_fill=int(bar_total*progress)
    pygame.draw.rect(screen,(25,25,35),(80,HEIGHT//2,bar_total,20),border_radius=10)
    pygame.draw.rect(screen,ACCENT,(80,HEIGHT//2,max(0,bar_fill),20),border_radius=10)
    pygame.draw.rect(screen,(60,60,90),(80,HEIGHT//2,bar_total,20),border_radius=10,width=1)
    lbl=font.render(msg,True,(130,130,160))
    screen.blit(lbl,(WIDTH//2-lbl.get_width()//2,HEIGHT//2+32))
    pygame.display.flip(); pygame.event.pump()

def animated_load(msg,p_start,p_end,duration_ms):
    start=time.time()
    while True:
        elapsed=(time.time()-start)*1000
        t=min(1.0,elapsed/duration_ms)
        draw_loading(msg,p_start+(p_end-p_start)*t)
        if t>=1.0: break

animated_load("Starting...",0.0,0.15,1500)
animated_load("Colors...",0.15,0.35,1000)
_build_hue_surf(); update_color()
animated_load("Canvas...",0.35,0.6,1000)
for _s in [64,128,256,512,WIDTH,CANVAS_SIZE*grid_size]:
    _w=pygame.transform.scale(canvas_surf,(_s,_s))
    screen.blit(_w,(0,0)); pygame.display.flip(); pygame.event.pump()
del _w
animated_load("UI...",0.6,0.85,1000)
animated_load("Ready!",0.85,1.0,1500)

# İlk kullanım kasmasını önlemek için tüm ağır işlemleri warmup'ta çalıştır
import numpy
_tmp=pygame.Surface((CANVAS_SIZE,CANVAS_SIZE),pygame.SRCALPHA)
_rgb=pygame.surfarray.pixels3d(canvas_surf)
_dst=pygame.surfarray.pixels3d(_tmp)
_alpha=pygame.surfarray.pixels_alpha(_tmp)
_dst[:]=_rgb[:]
_alpha[:]=255
del _rgb,_dst,_alpha,_tmp
# surfarray slider warmup
update_color()
_build_hue_surf()
# scaled_surf warmup
for _gs in [BASE_GRID, BASE_GRID*2]:
    _cs=CANVAS_SIZE*_gs
    _s=pygame.Surface((_cs,_cs)); _s.fill(CANVAS_BG)
    del _s
# flood_fill warmup
_wc=make_canvas(); _wc.set_at((0,0),(255,0,0))
try: pygame.draw.flood_fill(_wc,(255,0,0),(0,0))
except: pass
del _wc
# font warmup — tüm olası stringleri pre-render et
_chars="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-/*:. "
for _ch in _chars:
    font.render(_ch,True,WHITE)
    font_small.render(_ch,True,WHITE)
# numpad pre-render
_np_labels=["1","2","3","4","5","6","7","8","9","CLR","0","DEL"]
for _lbl in _np_labels:
    font.render(_lbl,True,WHITE)
pygame.time.wait(300)

shape_start_g=None; shape_end_g=None
pending_draw=False; pending_pos=None

while True:
    mx,my=pygame.mouse.get_pos()
    cur_gx,cur_gy=int((mx+cam_x)//grid_size),int((my+cam_y)//grid_size)

    if selection_rect and not moving_selection:
        show_selection_tools=True
    else:
        show_selection_tools=False

    # CFG PANELİ
    if show_cfg_panel:
        _c=_cfg_cache
        bh2=_c['bh2']; bw2=_c['bw2']; lbl_y=_c['lbl_y']; lbl_y2=_c['lbl_y2']
        minus_cs=_c['minus_cs']; val_cs=_c['val_cs']; plus_cs=_c['plus_cs']
        minus_ex=_c['minus_ex']; val_ex=_c['val_ex']; plus_ex=_c['plus_ex']
        np_w=_c['np_w']; np_h=_c['np_h']; np_y=_c['np_y']
        np_labels=_c['np_labels']; np_rects=_c['np_rects']
        R_OK=_c['R_OK']; R_CX=_c['R_CX']

        for event in pygame.event.get():
            if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            if event.type==pygame.FINGERDOWN:
                _now=time.time()
                if _now-_last_btn_time<0.1: continue
                globals()['_last_btn_time']=_now
                px2=event.x*TOUCH_W; py2=event.y*TOUCH_H
                if val_cs.collidepoint(px2,py2): cfg_active="canvas"
                elif val_ex.collidepoint(px2,py2): cfg_active="export"
                cs_val=int(cfg_canvas_str) if cfg_canvas_str.isdigit() else CANVAS_SIZE
                ex_val=int(cfg_export_str) if cfg_export_str.isdigit() else EXPORT_SIZE_CFG
                if minus_cs.collidepoint(px2,py2):
                    cfg_canvas_str=str(max(4,cs_val-1))
                elif plus_cs.collidepoint(px2,py2):
                    cfg_canvas_str=str(min(256,cs_val+1))
                elif minus_ex.collidepoint(px2,py2):
                    cfg_export_str=str(max(1,ex_val-16))
                elif plus_ex.collidepoint(px2,py2):
                    cfg_export_str=str(min(4096,ex_val+16))
                else:
                    for ni,nr2 in enumerate(np_rects):
                        if nr2.collidepoint(px2,py2):
                            lbl=np_labels[ni]
                            if lbl=="DEL":
                                if cfg_active=="canvas" and cfg_canvas_str: cfg_canvas_str=cfg_canvas_str[:-1]
                                elif cfg_active=="export" and cfg_export_str: cfg_export_str=cfg_export_str[:-1]
                            elif lbl=="CLR":
                                if cfg_active=="canvas": cfg_canvas_str=""
                                elif cfg_active=="export": cfg_export_str=""
                            else:
                                if cfg_active=="canvas" and len(cfg_canvas_str)<3: cfg_canvas_str+=lbl
                                elif cfg_active=="export" and len(cfg_export_str)<4: cfg_export_str+=lbl
                            break
                if R_OK.collidepoint(px2,py2):
                    try:
                        new_cs=int(cfg_canvas_str)
                        if 4<=new_cs<=256 and new_cs!=CANVAS_SIZE:
                            globals()['CANVAS_SIZE']=new_cs
                            globals()['canvas_surf']=make_canvas(new_cs)
                            undo_stack.clear(); redo_stack.clear()
                            globals()['_scaled_gs']=-1
                    except: pass
                    try:
                        new_ex=int(cfg_export_str)
                        if 1<=new_ex<=4096: globals()['EXPORT_SIZE_CFG']=new_ex
                    except: pass
                    show_cfg_panel=False; cfg_active=None
                elif R_CX.collidepoint(px2,py2):
                    show_cfg_panel=False; cfg_active=None
        screen.fill((20,20,30))
        # Statik elemanları cache'den al (sadece değer değişince yeniden render et)
        if not hasattr(pygame,'_cfg_surf') or pygame._cfg_cs!=cfg_canvas_str or pygame._cfg_ex!=cfg_export_str:
            pygame._cfg_cs=cfg_canvas_str; pygame._cfg_ex=cfg_export_str
            _cs=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); _cs.fill((0,0,0,0))
            # Canvas size
            _cs.blit(font.render(f"Canvas: {cfg_canvas_str}x{cfg_canvas_str}",True,WHITE),(BX,lbl_y))
            for _r,_t in [(minus_cs,"-"),(val_cs,cfg_canvas_str),(plus_cs,"+")]:
                pygame.draw.rect(_cs,(60,60,80),_r,border_radius=10)
                _s=font.render(_t,True,ACCENT if _t==cfg_canvas_str else WHITE)
                _cs.blit(_s,(_r.centerx-_s.get_width()//2,_r.centery-_s.get_height()//2))
            # Export size
            _cs.blit(font.render(f"Export: {cfg_export_str}px",True,WHITE),(BX,lbl_y2))
            for _r,_t in [(minus_ex,"-"),(val_ex,cfg_export_str),(plus_ex,"+")]:
                pygame.draw.rect(_cs,(60,60,80),_r,border_radius=10)
                _s=font.render(_t,True,ACCENT if _t==cfg_export_str else WHITE)
                _cs.blit(_s,(_r.centerx-_s.get_width()//2,_r.centery-_s.get_height()//2))
            # OK/Cancel
            pygame.draw.rect(_cs,(0,140,80),R_OK,border_radius=12)
            pygame.draw.rect(_cs,(140,40,40),R_CX,border_radius=12)
            for _r,_t in [(R_OK,"OK"),(R_CX,"Cancel")]:
                _s=font.render(_t,True,WHITE)
                _cs.blit(_s,(_r.centerx-_s.get_width()//2,_r.centery-_s.get_height()//2))
            # Numpad
            for ni,nr2 in enumerate(np_rects):
                lbl=np_labels[ni]
                pygame.draw.rect(_cs,(100,40,40) if lbl in ("DEL","CLR") else (60,60,80),nr2,border_radius=8)
                _s=font.render(lbl,True,WHITE)
                _cs.blit(_s,(nr2.centerx-_s.get_width()//2,nr2.centery-_s.get_height()//2))
            pygame._cfg_surf=_cs
        screen.blit(pygame._cfg_surf,(0,0))
        pygame.display.flip(); clock.tick(60); continue

    # KAYIT PANELİ
    if show_save_panel:
        R_PREV=pygame.Rect(WIDTH//2-150,int(HEIGHT*0.05),300,300)
        folder_rects=[]
        for fi,(fp,fl) in enumerate(SAVE_FOLDERS):
            fr=pygame.Rect(BX,int(HEIGHT*0.42)+fi*(BH+10),BW,BH)
            folder_rects.append(fr)
        R_SV2=pygame.Rect(BX,int(HEIGHT*0.42)+len(SAVE_FOLDERS)*(BH+10),BW,BH)
        R_CX2=pygame.Rect(BX,R_SV2.bottom+10,BW,BH)
        for event in pygame.event.get():
            if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            if event.type==pygame.FINGERDOWN:
                _now=time.time()
                if _now-_last_btn_time<0.1: continue
                globals()['_last_btn_time']=_now
                px2=event.x*TOUCH_W; py2=event.y*TOUCH_H
                for fi,fr in enumerate(folder_rects):
                    if fr.collidepoint(px2,py2): sel_folder=fi
                if R_SV2.collidepoint(px2,py2):
                    save_image(); show_save_panel=False; save_feedback_timer=120
                elif R_CX2.collidepoint(px2,py2):
                    show_save_panel=False
        screen.fill((20,20,30))
        if _prev_surf: screen.blit(_prev_surf,R_PREV.topleft)
        for fi,(fp,fl) in enumerate(SAVE_FOLDERS):
            fr=folder_rects[fi]
            clr=(0,120,200) if fi==sel_folder else (40,40,60)
            pygame.draw.rect(screen,clr,fr,border_radius=12)
            ft=font.render(fl.replace("\n"," "),True,WHITE)
            screen.blit(ft,(fr.centerx-ft.get_width()//2,fr.centery-ft.get_height()//2))
        pygame.draw.rect(screen,(0,160,80),R_SV2,border_radius=12)
        pygame.draw.rect(screen,(140,40,40),R_CX2,border_radius=12)
        ts=font.render("SAVE",True,WHITE); tc=font.render("Cancel",True,WHITE)
        screen.blit(ts,(R_SV2.centerx-ts.get_width()//2,R_SV2.centery-ts.get_height()//2))
        screen.blit(tc,(R_CX2.centerx-tc.get_width()//2,R_CX2.centery-tc.get_height()//2))
        if save_error_msg:
            em=font.render(save_error_msg[:40],True,(255,200,0))
            screen.blit(em,(20,R_CX2.bottom+10))
        pygame.display.flip(); clock.tick(60); continue

    for event in pygame.event.get():
        if event.type==pygame.QUIT: pygame.quit(); sys.exit()

        if event.type==pygame.FINGERDOWN:
            pos=pygame.Vector2(event.x*TOUCH_W,event.y*TOUCH_H)
            fingers[event.finger_id]=pos
            gx,gy=int((pos.x+cam_x)//grid_size),int((pos.y+cam_y)//grid_size)
            ui_hit=any(r.collidepoint(pos.x,pos.y) for r in [hue_rect,sat_rect,light_rect,size_rect])

            btn_hit=False
            for i,t_n in enumerate(tool_list):
                r=get_btn_rect(i)
                if r.collidepoint(pos.x,pos.y):
                    _now=time.time()
                    if _now-_last_btn_time<0.1: break
                    globals()['_last_btn_time']=_now
                    btn_hit=True
                    if t_n=="Undo" and undo_stack:
                        redo_stack.append(canvas_surf.copy())
                        canvas_surf.blit(undo_stack.pop(),(0,0))
                        globals()['_scaled_gs']=-1
                    elif t_n=="Redo" and redo_stack:
                        undo_stack.append(canvas_surf.copy())
                        canvas_surf.blit(redo_stack.pop(),(0,0))
                        globals()['_scaled_gs']=-1
                    elif t_n==":":
                        globals()['show_hamburger']=not show_hamburger
                        globals()['_cfg_rects_dirty']=True
                    else:
                        draw_tool=t_n
                    break

            if btn_hit:
                pass
            elif show_hamburger and not btn_hit:
                _now=time.time()
                if _now-_last_btn_time<0.1: pass
                elif ham_save_rect.collidepoint(pos.x,pos.y):
                    globals()['show_hamburger']=False; show_save_panel=True; _prev_surf=make_preview()
                elif ham_cfg_rect.collidepoint(pos.x,pos.y):
                    globals()['show_hamburger']=False; show_cfg_panel=True
                    cfg_canvas_str=str(CANVAS_SIZE); cfg_export_str=str(EXPORT_SIZE_CFG)
                    # Rect'leri bir kere hesapla
                    _bh2=int(HEIGHT*0.07); _bw2=(BW-20)//3
                    _ly=int(HEIGHT*0.04); _ly2=int(HEIGHT*0.17)
                    _npw=(BW-20)//3; _nph=int(HEIGHT*0.08); _npy=int(HEIGHT*0.30)
                    _oky=_npy+4*(_nph+8)+10
                    globals()['_cfg_cache']={
                        'bh2':_bh2,'bw2':_bw2,'lbl_y':_ly,'lbl_y2':_ly2,
                        'minus_cs':pygame.Rect(BX,_ly+40,_bw2,_bh2),
                        'val_cs':pygame.Rect(BX+_bw2+10,_ly+40,_bw2,_bh2),
                        'plus_cs':pygame.Rect(BX+_bw2*2+20,_ly+40,_bw2,_bh2),
                        'minus_ex':pygame.Rect(BX,_ly2+40,_bw2,_bh2),
                        'val_ex':pygame.Rect(BX+_bw2+10,_ly2+40,_bw2,_bh2),
                        'plus_ex':pygame.Rect(BX+_bw2*2+20,_ly2+40,_bw2,_bh2),
                        'np_w':_npw,'np_h':_nph,'np_y':_npy,
                        'np_labels':["1","2","3","4","5","6","7","8","9","CLR","0","DEL"],
                        'np_rects':[pygame.Rect(BX+(ni%3)*(_npw+8),_npy+(ni//3)*(_nph+8),_npw,_nph) for ni in range(12)],
                        'R_OK':pygame.Rect(BX,_oky,(BW-20)//2,_bh2),
                        'R_CX':pygame.Rect(BX+(BW-20)//2+20,_oky,(BW-20)//2,_bh2),
                    }
                else:
                    globals()['show_hamburger']=False
            elif show_selection_tools:
                if copy_btn_rect.collidepoint(pos.x,pos.y) and selection_rect:
                    if moving_selection:
                        x1,y1=selection_rect[0],selection_rect[1]
                        for (ox,oy),val in selected_data.items():
                            tx,ty=x1+ox,y1+oy
                            if 0<=tx<CANVAS_SIZE and 0<=ty<CANVAS_SIZE:
                                canvas_surf.set_at((tx,ty),val if isinstance(val,tuple) else int_to_rgb(val))
                        moving_selection=False
                        globals()['_scaled_gs']=-1
                    globals()['copy_data']={}
                    for x in range(selection_rect[0],selection_rect[2]+1):
                        for y in range(selection_rect[1],selection_rect[3]+1):
                            if 0<=x<CANVAS_SIZE and 0<=y<CANVAS_SIZE:
                                globals()['copy_data'][(x-selection_rect[0],y-selection_rect[1])]=canvas_surf.get_at((x,y))[:3]
                    globals()['copy_feedback_timer']=90
                    globals()['copy_feedback_msg']="Copied!"
                elif paste_btn_rect.collidepoint(pos.x,pos.y) and copy_data:
                    if moving_selection:
                        x1,y1=selection_rect[0],selection_rect[1]
                        for (ox,oy),val in selected_data.items():
                            tx,ty=x1+ox,y1+oy
                            if 0<=tx<CANVAS_SIZE and 0<=ty<CANVAS_SIZE:
                                canvas_surf.set_at((tx,ty),val if isinstance(val,tuple) else int_to_rgb(val))
                        moving_selection=False
                    save_state()
                    px2,py2=(selection_rect[0],selection_rect[1]) if selection_rect else (0,0)
                    for (ox,oy),val in copy_data.items():
                        tx,ty=px2+ox,py2+oy
                        col=val[:3] if isinstance(val,tuple) else int_to_rgb(val)
                        if col==CANVAS_BG: continue
                        if 0<=tx<CANVAS_SIZE and 0<=ty<CANVAS_SIZE:
                            canvas_surf.set_at((tx,ty),col)
                    globals()['_scaled_gs']=-1
                    globals()['copy_feedback_timer']=90
                    globals()['copy_feedback_msg']="Pasted!"
                elif delete_btn_rect.collidepoint(pos.x,pos.y) and selection_rect:
                    save_state()
                    for x in range(selection_rect[0],selection_rect[2]+1):
                        for y in range(selection_rect[1],selection_rect[3]+1):
                            if 0<=x<CANVAS_SIZE and 0<=y<CANVAS_SIZE:
                                canvas_surf.set_at((x,y),CANVAS_BG)
                    globals()['_scaled_gs']=-1
                elif len(fingers)==1 and not ui_hit and pos.y<safe_y:
                    if draw_tool=="Sel":
                        if selection_rect and selection_rect[0]<=gx<=selection_rect[2] and selection_rect[1]<=gy<=selection_rect[3]:
                            moving_selection=True; _sel_last_gx=gx; _sel_last_gy=gy
                            save_state(); selected_data={}
                            for x in range(selection_rect[0],selection_rect[2]+1):
                                for y in range(selection_rect[1],selection_rect[3]+1):
                                    if 0<=x<CANVAS_SIZE and 0<=y<CANVAS_SIZE:
                                        col=canvas_surf.get_at((x,y))[:3]
                                        selected_data[(x-selection_rect[0],y-selection_rect[1])]=col
                                        canvas_surf.set_at((x,y),CANVAS_BG)
                            bake_selection_surface(selected_data,grid_size)
                            globals()['_scaled_gs']=-1
                        else: selection_start,selection_rect=(gx,gy),None

            elif len(fingers)==1 and not ui_hit and pos.y<safe_y:
                if draw_tool=="Sel":
                    if selection_rect and selection_rect[0]<=gx<=selection_rect[2] and selection_rect[1]<=gy<=selection_rect[3]:
                        moving_selection=True; _sel_last_gx=gx; _sel_last_gy=gy
                        save_state(); selected_data={}
                        for x in range(selection_rect[0],selection_rect[2]+1):
                            for y in range(selection_rect[1],selection_rect[3]+1):
                                if 0<=x<CANVAS_SIZE and 0<=y<CANVAS_SIZE:
                                    col=canvas_surf.get_at((x,y))[:3]
                                    selected_data[(x-selection_rect[0],y-selection_rect[1])]=col
                                    canvas_surf.set_at((x,y),CANVAS_BG)
                        bake_selection_surface(selected_data,grid_size)
                        globals()['_scaled_gs']=-1
                    else: selection_start,selection_rect=(gx,gy),None
                elif draw_tool=="Rect":
                    shape_start_g=(gx,gy); shape_end_g=(gx,gy)
                elif draw_tool=="Fill":
                    save_state(); bucket_fill(gx,gy,current_color)
                elif draw_tool in ["Draw","Erase"]:
                    save_state(); pending_draw=True; pending_pos=(gx,gy); last_gx,last_gy=gx,gy
                elif draw_tool=="Pick":
                    if 0<=gx<CANVAS_SIZE and 0<=gy<CANVAS_SIZE:
                        r,g,b=[c/255 for c in canvas_surf.get_at((gx,gy))[:3]]
                        current_hue,current_light,current_sat=colorsys.rgb_to_hls(r,g,b); update_color()

            elif len(fingers)>=2:
                zoom_mode=True; is_drawing=False; shape_start_g=None; pending_draw=False
                f_list=list(fingers.values())
                start_dist,start_zoom,last_midpoint=f_list[0].distance_to(f_list[1]),zoom,(f_list[0]+f_list[1])/2

            # Slider
            if len(fingers)==1 and ui_hit:
                if hue_rect.collidepoint(pos.x,pos.y):
                    active_slider='hue'; current_hue=max(0.0,min(1.0,(pos.x-10)/bar_w)); update_color()
                elif sat_rect.collidepoint(pos.x,pos.y):
                    active_slider='sat'; current_sat=max(0.0,min(1.0,(pos.x-10)/bar_w)); update_color()
                elif light_rect.collidepoint(pos.x,pos.y):
                    active_slider='light'; current_light=max(0.0,min(1.0,(pos.x-10)/bar_w)); update_color()
                elif size_rect.collidepoint(pos.x,pos.y):
                    active_slider='size'; brush_size=max(1,min(7,int((pos.x-10)/bar_w*6)+1))

        if event.type==pygame.FINGERMOTION:
            pos=pygame.Vector2(event.x*TOUCH_W,event.y*TOUCH_H)
            fingers[event.finger_id]=pos
            gx,gy=int((pos.x+cam_x)//grid_size),int((pos.y+cam_y)//grid_size)

            if len(fingers)==1 and not zoom_mode:
                if moving_selection:
                    if gx!=_sel_last_gx or gy!=_sel_last_gy:
                        dx,dy=gx-_sel_last_gx,gy-_sel_last_gy
                        x1,y1,x2,y2=selection_rect
                        selection_rect=(x1+dx,y1+dy,x2+dx,y2+dy)
                        _sel_last_gx,_sel_last_gy=gx,gy
                elif draw_tool=="Sel" and selection_start:
                    selection_rect=(min(selection_start[0],gx),min(selection_start[1],gy),
                                   max(selection_start[0],gx),max(selection_start[1],gy))
                elif draw_tool=="Rect" and shape_start_g:
                    shape_end_g=(gx,gy)
                elif pending_draw and draw_tool in ["Draw","Erase"]:
                    val=None if draw_tool=="Erase" else current_color
                    sx,sy=pending_pos; ex,ey=gx,gy
                    dx=abs(ex-sx); dy=abs(ey-sy); cx=sx; cy=sy
                    sx_step=1 if sx<ex else -1; sy_step=1 if sy<ey else -1
                    err=dx-dy
                    while True:
                        draw_pixel(cx,cy,val)
                        if cx==ex and cy==ey: break
                        e2=2*err
                        if e2>-dy: err-=dy; cx+=sx_step
                        if e2<dx: err+=dx; cy+=sy_step
                    is_drawing=True; pending_draw=False; last_gx,last_gy=gx,gy
                elif is_drawing:
                    val=None if draw_tool=="Erase" else current_color
                    if last_gx is not None:
                        dx,dy,cx,cy=abs(gx-last_gx),abs(gy-last_gy),last_gx,last_gy
                        sx,sy=(1 if last_gx<gx else -1),(1 if last_gy<gy else -1)
                        err=dx-dy
                        while True:
                            draw_pixel(cx,cy,val)
                            if cx==gx and cy==gy: break
                            e2=2*err
                            if e2>-dy: err-=dy; cx+=sx
                            if e2<dx: err+=dx; cy+=sy
                    last_gx,last_gy=gx,gy

                if active_slider=='hue':
                    current_hue=max(0.0,min(1.0,(pos.x-10)/bar_w)); update_color()
                elif active_slider=='sat':
                    current_sat=max(0.0,min(1.0,(pos.x-10)/bar_w)); update_color()
                elif active_slider=='light':
                    current_light=max(0.0,min(1.0,(pos.x-10)/bar_w)); update_color()
                elif active_slider=='size':
                    brush_size=max(1,min(7,int((pos.x-10)/bar_w*6)+1))

            elif len(fingers)>=2:
                f_list=list(fingers.values())
                curr_dist,curr_mid=f_list[0].distance_to(f_list[1]),(f_list[0]+f_list[1])/2
                zoom=max(0.2,min(20.0,start_zoom*(curr_dist/max(start_dist,1))))
                max_grid=(WIDTH*2)//CANVAS_SIZE
                zoom=min(zoom,max_grid/BASE_GRID)
                old_grid,grid_size=grid_size,max(1,int(BASE_GRID*zoom))
                if old_grid!=grid_size:
                    ratio=grid_size/old_grid
                    cam_x,cam_y=(cam_x+curr_mid.x)*ratio-curr_mid.x,(cam_y+curr_mid.y)*ratio-curr_mid.y
                if last_midpoint: cam_x-=(curr_mid.x-last_midpoint.x); cam_y-=(curr_mid.y-last_midpoint.y)
                last_midpoint=curr_mid

        if event.type==pygame.FINGERUP:
            fx=event.x*TOUCH_W; fy=event.y*TOUCH_H
            if pending_draw and draw_tool in ["Draw","Erase"] and not zoom_mode:
                draw_pixel(pending_pos[0],pending_pos[1],None if draw_tool=="Erase" else current_color)
                pending_draw=False
            if draw_tool=="Rect" and shape_start_g and shape_end_g:
                save_state()
                lx=min(shape_start_g[0],shape_end_g[0]); ly=min(shape_start_g[1],shape_end_g[1])
                hx=max(shape_start_g[0],shape_end_g[0]); hy=max(shape_start_g[1],shape_end_g[1])
                col=int_to_rgb(current_color)
                for tx in range(lx,hx+1):
                    for ty in range(ly,hy+1):
                        if 0<=tx<CANVAS_SIZE and 0<=ty<CANVAS_SIZE:
                            canvas_surf.set_at((tx,ty),col)
                shape_start_g=shape_end_g=None
                globals()['_scaled_gs']=-1
            if moving_selection:
                x1,y1=selection_rect[0],selection_rect[1]
                for (ox,oy),val in selected_data.items():
                    tx,ty=x1+ox,y1+oy
                    if 0<=tx<CANVAS_SIZE and 0<=ty<CANVAS_SIZE:
                        canvas_surf.set_at((tx,ty),val if isinstance(val,tuple) else int_to_rgb(val))
                moving_selection=False; _sel_last_gx=None; _sel_last_gy=None
                globals()['_scaled_gs']=-1
            fingers.pop(event.finger_id,None)
            if not fingers: zoom_mode=False; is_drawing=False; last_gx=last_midpoint=None; pending_draw=False; globals()['active_slider']=None

    # --- RENDER ---
    screen.fill(BG_COLOR)

    if _scaled_gs!=grid_size or _scaled_surf is None:
        cs=CANVAS_SIZE*grid_size
        _s=pygame.Surface((cs,cs)); _s.fill(CANVAS_BG)
        for gy2 in range(CANVAS_SIZE):
            for gx2 in range(CANVAS_SIZE):
                col=canvas_surf.get_at((gx2,gy2))[:3]
                if col!=CANVAS_BG:
                    _s.fill(col,(gx2*grid_size,gy2*grid_size,grid_size,grid_size))
        globals()['_scaled_surf']=_s
        globals()['_scaled_gs']=grid_size

    screen.blit(_scaled_surf,(-int(cam_x),-int(cam_y)))

    if draw_tool=="Rect" and shape_start_g and shape_end_g:
        gx1=min(shape_start_g[0],shape_end_g[0]); gy1=min(shape_start_g[1],shape_end_g[1])
        gx2=max(shape_start_g[0],shape_end_g[0]); gy2=max(shape_start_g[1],shape_end_g[1])
        r2,g2,b2=int_to_rgb(current_color)
        pr=int(gx1*grid_size-cam_x); pt=int(gy1*grid_size-cam_y)
        pw=int((gx2-gx1+1)*grid_size); ph=int((gy2-gy1+1)*grid_size)
        pygame.draw.rect(screen,(r2//2,g2//2,b2//2),(pr,pt,pw,ph))
        pygame.draw.rect(screen,(r2,g2,b2),(pr,pt,pw,ph),2)

    if moving_selection:
        if _sel_baked_gs!=grid_size: bake_selection_surface(selected_data,grid_size)
        if _sel_surface is not None:
            x1,y1=selection_rect[0],selection_rect[1]
            screen.blit(_sel_surface,(x1*grid_size-cam_x,y1*grid_size-cam_y))

    if selection_rect:
        x1,y1,x2,y2=selection_rect
        pygame.draw.rect(screen,(0,255,255),(x1*grid_size-cam_x,y1*grid_size-cam_y,(x2-x1+1)*grid_size,(y2-y1+1)*grid_size),2)

    pygame.draw.rect(screen,UI_PANEL,(TOOLBAR_X-4,-650,TOOLBAR_W+12,HEIGHT))
    screen.blit(hue_surf,(10,hue_rect.y))
    screen.blit(sat_surf,(10,sat_rect.y))
    screen.blit(light_surf,(10,light_rect.y))
    pygame.draw.rect(screen,WHITE,(10+int(current_hue*bar_w)-2,hue_rect.y,5,36))
    pygame.draw.rect(screen,WHITE,(10+int(current_sat*bar_w)-2,sat_rect.y,5,36))
    pygame.draw.rect(screen,WHITE,(10+int(current_light*bar_w)-2,light_rect.y,5,36))
    pygame.draw.rect(screen,ACCENT,(10+int(((brush_size-1)/6)*bar_w),size_rect.y,10,28))

    for i,t_n in enumerate(tool_list):
        r=get_btn_rect(i)
        if t_n==":": clr=(60,60,80) if not show_hamburger else (100,80,160)
        elif t_n=="Fill": clr=(200,100,50) if draw_tool==t_n else (80,40,20)
        else: clr=ACCENT if draw_tool==t_n else (40,40,50)
        pygame.draw.rect(screen,clr,r,border_radius=10)
        txt=font_small.render(t_n,True,WHITE)
        screen.blit(txt,(r.centerx-txt.get_width()//2,r.centery-txt.get_height()//2))

    if show_hamburger:
        pygame.draw.rect(screen,(35,35,50),pygame.Rect(HAM_X-4,0,HAM_W+12,HAM_BH*2+20),border_radius=12)
        pygame.draw.rect(screen,(0,130,60),ham_save_rect,border_radius=10)
        pygame.draw.rect(screen,(90,50,140),ham_cfg_rect,border_radius=10)
        ts=font_small.render("Save",True,WHITE)
        tc=font_small.render("Settings",True,WHITE)
        screen.blit(ts,(ham_save_rect.centerx-ts.get_width()//2,ham_save_rect.centery-ts.get_height()//2))
        screen.blit(tc,(ham_cfg_rect.centerx-tc.get_width()//2,ham_cfg_rect.centery-tc.get_height()//2))

    if show_selection_tools:
        pygame.draw.rect(screen,(0,100,200),copy_btn_rect,border_radius=10)
        pygame.draw.rect(screen,(200,100,0),paste_btn_rect,border_radius=10)
        pygame.draw.rect(screen,(200,0,0),delete_btn_rect,border_radius=10)
        copy_txt=font.render("COPY",True,WHITE)
        paste_txt=font.render("PASTE",True,WHITE)
        delete_txt=font.render("DEL",True,WHITE)
        screen.blit(copy_txt,(copy_btn_rect.centerx-copy_txt.get_width()//2,copy_btn_rect.centery-copy_txt.get_height()//2))
        screen.blit(paste_txt,(paste_btn_rect.centerx-paste_txt.get_width()//2,paste_btn_rect.centery-paste_txt.get_height()//2))
        screen.blit(delete_txt,(delete_btn_rect.centerx-delete_txt.get_width()//2,delete_btn_rect.centery-delete_txt.get_height()//2))

    if save_feedback_timer>0:
        save_feedback_timer-=1
        fb=font.render("Saved!",True,(0,255,100))
        screen.blit(fb,(WIDTH//2-fb.get_width()//2,safe_y-60))

    if copy_feedback_timer>0:
        copy_feedback_timer-=1
        fb=font.render(copy_feedback_msg,True,(0,200,255))
        screen.blit(fb,(WIDTH//2-fb.get_width()//2,safe_y-120))

    pygame.display.flip()
    clock.tick(60)
