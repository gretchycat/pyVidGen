import sys,os,pydub,time
from optparse import OptionParser
import sounddevice as sd
import numpy as np
from termcontrol import termcontrol, pyteLogger, boxDraw, widget, widgetScreen
from termcontrol import widgetProgressBar, widgetSlider, widgetButton


"""
         0   1   2   3   4   5   6   7   8   9   A   B   C   D   E   F
U+250x   ─   ━   │   ┃   ┄   ┅   ┆   ┇   ┈   ┉   ┊   ┋   ┌   ┍   ┎   ┏
U+251x   ┐   ┑   ┒   ┓   └   ┕   ┖   ┗   ┘   ┙   ┚   ┛   ├   ┝   ┞   ┟
U+252x   ┠   ┡   ┢   ┣   ┤   ┥   ┦   ┧   ┨   ┩   ┪   ┫   ┬   ┭   ┮   ┯
U+253x   ┰   ┱   ┲   ┳   ┴   ┵   ┶   ┷   ┸   ┹   ┺   ┻   ┼   ┽   ┾   ┿
U+254x   ╀   ╁   ╂   ╃   ╄   ╅   ╆   ╇   ╈   ╉   ╊   ╋   ╌   ╍   ╎   ╏

         0   1   2   3   4   5   6   7   8   9   A   B   C   D   E   F
U+255x   ═   ║   ╒   ╓   ╔   ╕   ╖   ╗   ╘   ╙   ╚   ╛   ╜   ╝   ╞   ╟
U+256x   ╠   ╡   ╢   ╣   ╤   ╥   ╦   ╧   ╨   ╩   ╪   ╫   ╬   ╭   ╮   ╯
U+257x   ╰   ╱   ╲   ╳   ╴   ╵   ╶   ╷   ╸   ╹   ╺   ╻   ╼   ╽   ╾   ╿

         0   1   2   3   4   5   6   7   8   9   A   B   C   D   E   F
U+258x   ▀   ▁   ▂   ▃   ▄   ▅   ▆   ▇   █   ▉   ▊   ▋   ▌   ▍   ▎   ▏
U+259x   ▐   ░   ▒   ▓   ▔   ▕   ▖   ▗   ▘   ▙   ▚   ▛   ▜   ▝   ▞   ▟
"""

STOP=0
PLAY=1
RECORD=2

icons={}
icons['prev']   = ('\u23ee', 'v')
icons['prev']   = ('\u25ae\u25c0\u25c0', 'v')
icons['play']   = ('\u25b6', 'p')
icons['pause']  = ('\u25ae'*2, 'p')
icons['play/pause']  = ('\u25b6'+'\u25ae'*2, 'p')
icons['stop']   = ('\u25a0', 's')
icons['record'] = ('\u25cf', 'r')
icons['next']   = ('\u23ed', 'x')
icons['next']   = ('\u25b6\u25b6\u25ae', 'x')
icons['eject']  = ('\u23cf', 'j')
icons['random'] = ('RND', 'd')
icons['repeat'] = ('RPT', 't')

class termplayer(widget):
    def __init__(self, x=1, y=1, w=80, h=16, record_mode=False, files=[]):
        super().__init__(x=x, y=y, w=w, h=h)
        self.player=pyplayer()
        actions={
                    'play/pause': self.player.pause,
                    'stop': self.player.stop,
                    'record': self.player.record
                }
        self.playlist=files
        self.record_mode=record_mode
        if self.record_mode:
            if len(self.playlist)!=1:
                print("Record mode must reference one audio filename.")
                exit(1)
        else:
            pass
        self.frame=0
        self.anim="\\-/|"
        self.x=x
        self.y=y
        self.w=w
        self.h=h
        self.playerbox=widgetScreen(self.x, self.y, self.w, self.h, bg=234, fg=15, style='outside')
        self.addWidget(self.playerbox)
        boxHeight=8
        timeBoxW=30
        self.timeBox=widgetScreen(2, 1, timeBoxW, boxHeight, bg=233, fg=27, style='inside')
        self.playerbox.addWidget(self.timeBox)
        self.infoBox=widgetScreen(2+timeBoxW+2, 1, self.w-4-(timeBoxW+4), boxHeight, bg=233, fg=27, style='inside')
        self.playerbox.addWidget(self.infoBox)
        self.timeBox.box.tintFrame('#555')
        self.infoBox.box.tintFrame('#555')
        btn={}
        btnX=2
        btnY=11
        btnW=7
        btnH=4
        self.slider=widgetSlider(btnX, 9, self.w-(2*btnX), 0, self.player.length(), labelType='time' , key='k')
        self.playerbox.addWidget(self.slider)
        x=0
        for label in ['prev', 'play/pause', 'stop', 'record', 'next', '', 'eject', '', 'random', 'repeat']:
            if icons.get(label):
                caption, key=icons[label]
                action=actions.get(label)
                btn[label]=widgetButton(x*btnW+btnX, btnY, btnW, btnH, fg=27, bg=233, caption=caption, key=key, action=action)
                self.playerbox.addWidget(btn[label])
            x+=1

    def drawBigString(self, s):
        chars={}
        chars['Resolution']='5x4'
        chars['0']= " ▄▄  "\
                    "█  █ "\
                    "▄  ▄ "\
                    "▀▄▄▀ "
        chars['1']= "     "\
                    "   █ "\
                    "   ▄ "\
                    "   ▀ "
        chars['2']= " ▄▄  "\
                    "   █ "\
                    "▄▀▀  "\
                    "▀▄▄  "
        chars['3']= " ▄▄  "\
                    "   █ "\
                    " ▀▀▄ "\
                    " ▄▄▀ "
        chars['4']= "     "\
                    "█  █ "\
                    " ▀▀▄ "\
                    "   ▀ "
        chars['5']= " ▄▄  "\
                    "█    "\
                    " ▀▀▄ "\
                    " ▄▄▀ "
        chars['6']= " ▄▄  "\
                    "█    "\
                    "▄▀▀▄ "\
                    "▀▄▄▀ "
        chars['7']= " ▄▄  "\
                    "   █ "\
                    "   ▄ "\
                    "   ▀ "
        chars['8']= " ▄▄  "\
                    "█  █ "\
                    "▄▀▀▄ "\
                    "▀▄▄▀ "
        chars['9']= " ▄▄  "\
                    "█  █ "\
                    " ▀▀▄ "\
                    " ▄▄▀ "
        chars[':']= "     "\
                    "  ●  "\
                    "  ●  "\
                    "     "
        chars[' ']= "     "\
                    "     "\
                    "     "\
                    "     "
        col,row=chars['Resolution'].split('x')
        col=int(col)
        row=int(row)
        buffer=""
        for y in range(row):
            for c in s:
                fc=chars.get(c)
                if fc:
                    buffer+=fc[y*col:(y+1)*col]
                else:
                    buffer+=" "
            buffer+='\n'
        return buffer

    def drawMultiLine(self, x, y, s):
        lines=s.split('\n')
        dy=0
        buffer=""
        for l in lines:
            buffer+=self.t.gotoxy(x, y+dy)
            buffer+=l
            dy=dy+1
        return buffer

    def draw(self):
        t=self.player.get_cursor()
        min=int(t/60)
        sec=int(t%60)
        timestr=self.drawBigString(f"{min:02d}:{sec:02d}", )
        buffer=''
        fg=27
        if self.player.status==RECORD:
            fg=196
        self.timeBox.feed(self.t.ansicolor(fg,233, bold=True))
        self.timeBox.feed(self.t.clear())
        self.timeBox.feed(self.drawMultiLine(30-(5*5)-2, 1, timestr))
        self.timeBox.feed(self.t.gotoxy(1, 3))
        if self.player.status==PLAY:
            i, k=icons['play']
            self.timeBox.feed(self.t.ansicolor(46, 233, bold=True))
            self.timeBox.feed(i)
        elif self.player.status==RECORD:
            i, k=icons['record']
            self.timeBox.feed(self.t.ansicolor(196, 233, bold=True))
            self.timeBox.feed(i)
        else:
            i, k=icons['stop']
            self.timeBox.feed(self.t.ansicolor(27, 233, bold=True))
            self.timeBox.feed(i)
        buffer+=self.playerbox.draw()
        #print(self.anim[self.frame % len(self.anim)])
        self.frame +=1
        return buffer

class pyplayer:
    def __init__(self):
        self.x=1
        self.y=1
        self.status=STOP
        self.fps=48000
        self.cursor=0
        self.startTime=0
        self.selected=0
        self.selected_length=0
        self.buffer=[]
        self.record_buffer=[]

    def play(self):
        if self.status==STOP:
            self.status=PLAY
            self.startTime=time.time()
            c=int(self.cursor*self.fps)
            s=int(self.selected*self.fps)
            sl=int(self.selected_length*self.fps)
            if sl==0:
                sd.play(self.buffer[c:], self.fps)
            else:
                sd.play(self.buffer[c:s+sl], self.fps)

    def pause(self, restart=True):
        if self.status==STOP:
            if restart:
                self.play()
        elif self.status==PLAY:
            self.status=STOP
            sd.stop()
        elif self.status==RECORD:
            self.status=STOP
            sd.stop()
            length=(time.time()-self.startTime)
            record_buffer=self.record_buffer[:int(length*self.fps)]
            self.startTime=0
            c=int(self.cursor*self.fps)
            s=int(self.selected*self.fps)
            sl=int(self.selected_length*self.fps)
            pre, post = [], []
            if sl>0:
                pre=self.buffer[:s]
                post=self.buffer[s+sl:]
            else:
                pre=self.buffer[:c]
                post=self.buffer[c:]
            self.cursor=(s+(len(record_buffer))/self.fps)
            self.selected=0
            self.selected_length=0
            if len(pre)==0:
                self.buffer=record_buffer
            else:
                self.buffer=np.concatenate((pre, record_buffer))
            if len(post)>0:
                self.buffer=np.concatenate((self.buffer, post))
            self.record_buffer=[]

    def length(self):
        return len(self.buffer)/self.fps

    def stop(self):
        self.pause(restart=False)
        self.selected=0
        self.cursor=0

    def record(self):
        if self.status==STOP:
            self.status=RECORD
            self.startTime=time.time()
            self.record_buffer=sd.rec(self.fps*60*10, self.fps, channels=2)

    def seek(self, time):
        playing=self.status==PLAY
        if playing:
            self.pause()
        if self.status==STOP:
            if time<0:
                time=0
            if time>self.length():
                time=self.length()
            self.cursor=time
        if playing:
            self.play()

    def select(self, s, sl):
        if self.status==STOP:
            if s<0:
                s=0
            if sl<0:
                sl=0
            if sl>0:
                if s<self.length():
                    s=self.length()
                if s+sl>self.length():
                    sl=self.length()-s
                self.selected=s
                self.selected_length=sl

    def clear(self):
        if self.selected_length==0:
            self.buffer=[]
        else:
            self.clear_selected()

    def clear_selected(self):
        self.seek(self.selected)
        s=int(self.selected*self.fps)
        sl=int(self.selected_length*self.fps)
        pre=self.buffer[:s]
        post=self.buffer[s+sl:]
        if len(pre)>0:
            if len(post)>0:
                self.buffer=np.concatenate((pre, post))
            else:
                self.buffer=pre
        else:
            if len(post)>0:
                self.buffer=post
            else:
                self.buffer=[]

    def get_cursor(self):
        self.cursor=time.time()-self.startTime
        if self.cursor>self.length():
            self.cursor=self.length()
            #self.pause()
        return self.cursor

    def next(self):
        pass

    def prev(self):
        pass

    def load(self, filename):
        pass

def main():
    parser=OptionParser(usage="usage: %prog [options] AUDIO_FILES")
    parser.add_option("-r", "--record", action='store_true', dest="record", 
            default=False, help="Record mode.")
    parser.add_option("-v", "--verbose", dest="debug", default="info",
            help="Show debug messages.[debug, info, warning]")
    parser.add_option("-x", dest="x", default=1, help="Top left coordinate.")
    parser.add_option("-y", dest="y", default=1, help="Top left coordinate.")

    (options, args)=parser.parse_args()
    if len(args)==0:
        parser.print_help()
        return
 
    tp=termplayer(x=int(options.x), y=int(options.y), record_mode=options.record, files=args)
    tp.guiLoop()
    return
    p=pyplayer()
    print('recording')
    p.record()
    time.sleep(10)
    print('stopping')
    p.seek(0)
    print('playing')
    p.play()
    time.sleep(p.length())
    p.seek(5)
    print('recording')
    p.record()
    time.sleep(10)
    print('stopping')
    p.stop()
    print('playing')
    p.play()
    time.sleep(p.length())
    p.stop()
    pass

if __name__ == "__main__":
    main()
