import sys,os,time, random
from optparse import OptionParser
from pyplayer import pyplayer
from termcontrol import termcontrol, pyteLogger, boxDraw, widget, widgetScreen
from termcontrol import widgetProgressBar, widgetSlider, widgetButton

"""
         0   1   2   3   4   5   6   7   8   9   A   B   C   D   E   F
U+250x   ─   ━   │   ┃   ┄   ┅   ┆   ┇   ┈   ┉   ┊   ┋   ┌   ┍   ┎   ┏
U+251x   ┐   ┑   ┒   ┓   └   ┕   ┖   ┗   ┘   ┙   ┚   ┛   ├   ┝   ┞   ┟
U+252x   ┠   ┡   ┢   ┣   ┤   ┥   ┦   ┧   ┨   ┩   ┪   ┫   ┬   ┭   ┮   ┯
U+253x   ┰   ┱   ┲   ┳   ┴   ┵   ┶   ┷   ┸   ┹   ┺   ┻   ┼   ┽   ┾   ┿
U+254x   ╀   ╁   ╂   ╃   ╄   ╅   ╆   ╇   ╈   ╉   ╊   ╋   ╌   ╍   ╎   ╏
U+255x   ═   ║   ╒   ╓   ╔   ╕   ╖   ╗   ╘   ╙   ╚   ╛   ╜   ╝   ╞   ╟
U+256x   ╠   ╡   ╢   ╣   ╤   ╥   ╦   ╧   ╨   ╩   ╪   ╫   ╬   ╭   ╮   ╯
U+257x   ╰   ╱   ╲   ╳   ╴   ╵   ╶   ╷   ╸   ╹   ╺   ╻   ╼   ╽   ╾   ╿
U+258x   ▀   ▁   ▂   ▃   ▄   ▅   ▆   ▇   █   ▉   ▊   ▋   ▌   ▍   ▎   ▏
U+259x   ▐   ░   ▒   ▓   ▔   ▕   ▖   ▗   ▘   ▙   ▚   ▛   ▜   ▝   ▞   ▟
U+25Ax   ■   □   ▢   ▣   ▤   ▥   ▦   ▧   ▨   ▩   ▪   ▫   ▬   ▭   ▮   ▯
U+25Bx   ▰   ▱   ▲   △   ▴   ▵   ▶   ▷   ▸   ▹   ►   ▻   ▼   ▽   ▾   ▿
U+25Cx   ◀   ◁   ◂   ◃   ◄   ◅   ◆   ◇   ◈   ◉   ◊   ○   ◌   ◍   ◎   ●
U+25Dx   ◐   ◑   ◒   ◓   ◔   ◕   ◖   ◗   ◘   ◙   ◚   ◛   ◜   ◝   ◞   ◟
U+25Ex   ◠   ◡   ◢   ◣   ◤   ◥   ◦   ◧   ◨   ◩   ◪   ◫   ◬   ◭   ◮   ◯
U+25Fx   ◰   ◱   ◲   ◳   ◴   ◵   ◶   ◷   ◸   ◹   ◺   ◻   ◼   ◽  ◾  ◿
"""

STOP=0
PLAY=1
RECORD=2

def minsec(s):
    mins=int(s//60)
    secs=int(s%60)
    return f'{mins:02d}:{secs:02d}'

class termplayer(widget):
    def __init__(self, x=1, y=1, w=80, h=15, mode='play', files=[], script=""): 
        self.icons={}
        self.icons['prev']     = {"label":'\u23ee',   "key":'[', 'action':self.prev}
        self.icons['prev']     = {"label":'\u25ae'+'\u25c0'*2, "key":'[', 'action':self.prev}
        self.icons['next']     = {"label":'\u23ed',   "key":']', 'action':self.next}
        self.icons['next']     = {"label":'\u25b6'*2+'\u25ae', "key":']', 'action':self.next}
        self.icons['play']     = {"label":'\u25b6',   "key":'P', 'action':self.play}
        self.icons['pause']    = {"label":'\u25ae'*2, "key":'p', 'action':self.pause}
        self.icons['play/pause']={"label":'\u25b6'+'\u25ae'*2, "key":'p', 'action':self.playpause}
        self.icons['stop']     = {"label":'\u25a0',   "key":'s', 'action':self.stop}
        self.icons['record']   = {"label":'\u25cf',   "key":'r', 'action':self.record}
        self.icons['eject']    = {"label":'\u23cf',   "key":'j', 'action':self.eject}
        self.icons['shuffle']  = {"label":'\u292e',   "key":'S', 'action':self.shuffle}
        self.icons['repeat']   = {"label":'\u21bb',   "key":'R', 'action':self.repeat}
        self.icons['seek']     = {"label":'',         "key":'k', 'action':self.seek}
        self.icons['seek-']    = {"label":'\u25c0'*2, "key":'-', 'action':self.seekBack}
        self.icons['seek+']    = {"label":'\u25b6'*2, "key":'+', 'action':self.seekFwd}
        self.icons['playlist'] = {"label":'\u2263',   "key":'L', 'action':self.togglePlayList}
        self.icons['denoise']  = {"label":'\u2593\u2592\u2591', "key":'N', 'action':self.denoise}
        self.icons['normalize']= {"label":'\u224b',   "key":'Z', 'action':self.normalize}
        self.icons['quit']=      {"label":'Quit',     "key":'q', 'action':self.quit}
        super().__init__(x=x, y=y, w=w, h=h)
        self.showPlayList=False
        self.clearPlayList=False
        self.playlist=files
        self.playlistinorder=files.copy()
        self.playListInfo={}
        self.repeat=False
        self.mode=mode
        for f in files:
            self.playListInfo[f]=self.mediaInfo(f)
        if self.mode=='record':
            if len(self.playlist)!=1:
                print("Record mode must reference one audio filename.")
                exit(1)
        else:
            pass
        self.filename=files[0]
        self.player=pyplayer()
        if self.mode=='play':
            self.load(self.filename)
        self.script=script
        self.frame=0
        self.anim="\\-/|"
        self.x=x
        self.y=y
        self.w=w
        self.h=h
        self.playerbox=widgetScreen(self.x, self.y, self.w, self.h, bg=234, fg=15, style='outside')
        self.playlistbox=widgetScreen(self.x, self.y+self.h, self.w, self.h, bg=234, fg=15, style='outside')
        self.addWidget(self.playerbox)
        self.addWidget(self.playlistbox)
        boxHeight=7
        timeBoxW=30
        self.timeBox=widgetScreen(2, 1, timeBoxW, boxHeight, bg=233, fg=27, style='inside')
        self.playerbox.addWidget(self.timeBox)
        self.infoBox=widgetScreen(2+timeBoxW+2, 1, self.w-4-(timeBoxW+4), boxHeight, bg=233, fg=27, style='inside')
        self.playerbox.addWidget(self.infoBox)
        self.timeBox.box.tintFrame('#555')
        self.infoBox.box.tintFrame('#555')
        self.slider=widgetSlider(2, boxHeight+1, self.w-(2*2), 0, self.player.length(), labelType='time' , key='k')
        self.playerbox.addWidget(self.slider)
        self.addButtons(mode)

    def addButtons(self,mode):
        playbuttons=['prev', 'play/pause', 'stop', 'next', '', 'shuffle', 'repeat', 'playlist', '', 'quit']
        recordbuttons=['seek-', 'play/pause', 'stop', 'record', 'seek+', '', 'denoise', 'normalize', '', 'quit']
        buttons=playbuttons
        if mode=='record':
            buttons=recordbuttons
        else: 
            buttons=playbuttons
        self.btn={}
        btnX=2
        btnY=10
        btnW=7
        btnH=4 
        x=0
        for label in buttons:
            if self.icons.get(label):
                i=self.icons[label]
                self.btn[label]=widgetButton(x*btnW+btnX, btnY, btnW, btnH, fg=27, bg=233, caption=i['label'], key=i['key'], action=i['action'])
                self.playerbox.addWidget(self.btn[label])
            x+=1

    def mediaInfo(self, f):
        title=f
        length=0
        bitrate=0
        quality=0
        channels=1
        info={'title':title, 'length':length, 'bitrate':bitrate, 'quality':quality, 'channels':channels}
        self.playListInfo[f]=info
        return info

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
        t=self.player.get_cursor_time()
        timestr=self.drawBigString(minsec(t))
        buffer=''
        fg=27
        if self.player.status==RECORD:
            fg=196
        else:
            fg=27
        if self.mode=='record':
            self.infoBox.feed(self.t.clear())
            self.infoBox.feed(self.t.gotoxy(1, 1))
            self.infoBox.feed(self.t.ansicolor(27))
            self.infoBox.feed(self.script)
            pass
        elif self.mode=='play':
            self.infoBox.feed(self.t.clear())
            self.infoBox.feed(self.t.ansicolor(27))
            title=""
            title=f'{self.playlist.index(self.filename)+1}. '
            if self.playListInfo[self.filename]: 
                title+=self.playListInfo[self.filename]['title']
                title+=f' ({minsec(self.playListInfo[self.filename]["length"])})'
            self.infoBox.feed(self.t.gotoxy(1, 1))
            self.infoBox.feed(title)
            quality=0
            bitrate=0
            channels=0
            if self.playListInfo[self.filename]: 
                quality=int(self.playListInfo[self.filename]["quality"])
                bitrate=int(self.playListInfo[self.filename]["bitrate"])
                channels=int(self.playListInfo[self.filename]["channels"])
            self.infoBox.feed(self.t.gotoxy(1, 3))
            self.infoBox.feed(f'{int(quality)}kbps')
            self.infoBox.feed(self.t.gotoxy(14, 3))
            self.infoBox.feed(f'{bitrate}kHz')
            self.infoBox.feed(self.t.gotoxy(31, 3))
            if channels==0:
                self.infoBox.feed(f'No Audio')
            elif channels==1:
                self.infoBox.feed(f'    Mono')
            elif channels==2:
                self.infoBox.feed(f'  Stereo')
            else:
                self.infoBox.feed(f' Stereo+')

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
        elif self.player.status==STOP:
            i=self.icons['stop']
            self.timeBox.feed(self.t.ansicolor(27, 233, bold=True))
            self.timeBox.feed(i['label'])
        buffer+=self.playerbox.draw()
        if self.showPlayList:
            self.playlistbox.feed(f'{self.t.clear()}')
            startline=self.playlist.index(self.filename)
            if startline+self.h-3>len(self.playlist):
                startline=len(self.playlist)-(self.h-2)
            if startline<0:
                startline=0
            for n in range(self.h-2):
                color=27
                if n+startline<len(self.playlist):
                    f=self.playlist[startline+n]
                    if f==self.filename:
                        color=46
                    self.playlistbox.feed(f'{self.t.gotoxy(1,n+1)}')
                    self.playlistbox.feed(f'{self.t.ansicolor(color)}')
                    title=f
                    tm="00:00"
                    if self.playListInfo[f]:
                        title=f"{self.playListInfo[f]['title']}"
                        tm=f"{minsec(self.playListInfo[f]['length'])}"
                    self.playlistbox.feed(f'{n+startline+1}. {title}')
                    self.playlistbox.feed(f'{self.t.gotoxy(self.w-3-len(tm),n+1)}')
                    self.playlistbox.feed(f'{tm}')
                else:
                    self.playlistbox.feed(f'{self.t.gotoxy(1,n+1)} ') 
            buffer+=self.playlistbox.draw()
        else:
            if self.clearPlayList:
                self.clearPlayList=False
                buffer+=self.t.reset()
                for y in range(self.y+self.h,self.y+2*self.h):
                    buffer+=self.t.gotoxy(self.x, y)
                    for x in range(0, self.w):
                        buffer+=' '
        #print(self.anim[self.frame % len(self.anim)])
        self.frame +=1
        return buffer

    def togglePlayList(self):
        self.showPlayList=not self.showPlayList
        if not self.showPlayList:
            self.clearPlayList=True

    def load(self, filename):
        info=self.player.load(filename)
        self.playListInfo[filename]=info
        self.filename=filename

    def save(self, filename):
        self.player.save(filename)

    def quit(self):
        if self.mode=='record':
            #save recording?
            self.save(self.filename)
            pass
        #self.player.quit()

    def next(self):
        i=self.playlist.index(self.filename)
        i+=1
        if i>=len(self.playlist):
            i=0
        self.load(self.playlist[i])

    def prev(self):
        i=self.playlist.index(self.filename)
        i-=1
        if i<0:
            i=len(self.playlist)-1
        self.load(self.playlist[i])

    def trackDone(self):
        if player.status==PLAY:
            if self.repeat:
                self.stop()
                self.play()
            else:
                self.next()

    def shuffle(self):
        if self.playlist==self.playlistinorder:
            random.shuffle(self.playlist)
        else:
            self.playlist=self.playlistinorder.copy()

    def repeat(self):
        self.repeat = not self.repeat

    def seek(self, pos=0):
        self.player.seek_time(pos)

    def seekFwd(self):
        self.player.seekFwd_time(10)

    def seekBack(self):
        self.player.seekBack_time(10)

    def eject(self):
        pass

    def play(self):
        self.player.play()

    def pause(self):
        self.player.pause()

    def playpause(self):
        self.player.playpause()

    def stop(self):
        self.player.stop()

    def record(self):
        self.player.record()

    def denoise(self):
        pass

    def normalize(self):
        pass

def main():
    parser=OptionParser(usage="usage: %prog [options] AUDIO_FILES")
    parser.add_option("-r", "--record", action='store_true', dest="record", 
            default=False, help="Record mode.")
    parser.add_option("-v", "--verbose", dest="debug", default="info",
            help="Show debug messages.[debug, info, warning]")
    parser.add_option("-s", dest="script", default="No script was given.",
            help="Script for record mode.")
    parser.add_option("-x", dest="x", default=1, help="Top left coordinate.")
    parser.add_option("-y", dest="y", default=1, help="Top left coordinate.")

    (options, args)=parser.parse_args()
    if len(args)==0:
        parser.print_help()
        return
    mode='play'
    if options.record:
        mode='record'
    tp=termplayer(x=int(options.x), y=int(options.y), mode=mode, script=options.script, files=args)
    tp.guiLoop()
    return

if __name__ == "__main__":
    main()
