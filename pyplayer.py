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

class termplayer(widget):
    def __init__(self, x=1, y=1, w=80, h=16, mode='play', files=[]): 
        self.player=pyplayer()
        self.icons={}
        self.icons['prev']   = {"label":'\u23ee', "key":'[', 'action':self.prev}
        self.icons['prev']   = {"label":'\u25ae\u25c0\u25c0', "key":'[', 'action':self.prev}
        self.icons['play']   = {"label":'\u25b6', "key":'P', 'action':self.play}
        self.icons['pause']  = {"label":'\u25ae'*2, "key":'p', 'action':self.pause}
        self.icons['play/pause']  = {"label":'\u25b6'+'\u25ae'*2, "key":'p', 'action':self.playpause}
        self.icons['stop']   = {"label":'\u25a0', "key":'s', 'action':self.stop}
        self.icons['record'] = {"label":'\u25cf', "key":'r', 'action':self.record}
        self.icons['next']   = {"label":'\u23ed', "key":']', 'action':self.next}
        self.icons['next']   = {"label":'\u25b6\u25b6\u25ae', "key":']', 'action':self.next}
        self.icons['eject']  = {"label":'\u23cf', "key":'j', 'action':self.eject}
        self.icons['random'] = {"label":'RND', "key":'d', 'action':self.shuffle}
        self.icons['repeat'] = {"label":'\u238c', "key":'t', 'action':self.repeat}
        self.icons['repeat'] = {"label":'RPT', "key":'t', 'action':self.repeat}
        self.icons['seek'] = {"label":'', "key":'k', 'action':self.seek}
        self.icons['seek-'] = {"label":'\u25c0'*2, "key":'-', 'action':self.seekBack}
        self.icons['seek+'] = {"label":'\u25b6'*2, "key":'+', 'action':self.seekFwd}
        self.icons['playlist'] = {"label":'\u2263', "key":'L', 'action':self.togglePlayList}
        self.icons['denoise'] = {"label":'NOI', "key":'N', 'action':self.denoise}
        self.icons['denoise'] = {"label":'\u2593\u2591\u2592', "key":'N', 'action':self.denoise}

        super().__init__(x=x, y=y, w=w, h=h)
        self.showPlayList=False
        self.playlist=files
        self.mode=mode
        if self.mode=='record':
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
        self.slider=widgetSlider(2, 9, self.w-(2*2), 0, self.player.length(), labelType='time' , key='k')
        self.playerbox.addWidget(self.slider)
        self.addButtons(mode)

    def addButtons(self,mode):
        playbuttons=['prev', 'play/pause', 'stop', 'next', '', 'eject', '', 'random', 'repeat', 'playlist']
        recordbuttons=['seek-', 'play', 'pause', 'stop', 'record', 'seek+', '', 'eject', '', 'denoise']
        buttons=playbuttons
        if mode=='record':
            buttons=recordbuttons
        else: 
            buttons=playbuttons
        self.btn={}
        btnX=2
        btnY=11
        btnW=7
        btnH=4 
        x=0
        for label in buttons:
            if self.icons.get(label):
                i=self.icons[label]
                self.btn[label]=widgetButton(x*btnW+btnX, btnY, btnW, btnH, fg=27, bg=233, caption=i['label'], key=i['key'], action=i['action'])
                self.playerbox.addWidget(self.btn[label])
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
            i=self.icons['play']
            self.timeBox.feed(self.t.ansicolor(46, 233, bold=True))
            self.timeBox.feed(i['label'])
        elif self.player.status==RECORD:
            i=self.icons['record']
            self.timeBox.feed(self.t.ansicolor(196, 233, bold=True))
            self.timeBox.feed(i['label'])
        else:
            i=self.icons['stop']
            self.timeBox.feed(self.t.ansicolor(27, 233, bold=True))
            self.timeBox.feed(i['label'])
        buffer+=self.playerbox.draw()
        #print(self.anim[self.frame % len(self.anim)])
        self.frame +=1
        return buffer

    def togglePlayList(self):
        pass

    def next(self):
        pass

    def prev(self):
        pass

    def selectFile(self, filename):
        pass

    def shuffle(self):
        pass

    def repeat(self):
        pass

    def seek(self, pos=0):
        pass

    def seekFwd(self):
        pass

    def seekBack(self):
        pass

    def eject(self):
        pass

    def play(self):
        self.player.play()

    def pause(self):
        self.player.pause()

    def playpause(self):
        self.player.pause()

    def stop(self):
        self.player.stop()

    def record(self):
        self.player.record()

    def denoise():
        pass

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
    mode='play'
    if options.record:
        mode='record'
    tp=termplayer(x=int(options.x), y=int(options.y), mode=mode, files=args)
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
