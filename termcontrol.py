#!/usr/bin/python3
import sys, os, logging, pyte, re, icat

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

grchr={}
grchr['ascii']={'hline':'-', 'vline':'|',
                'TH':'^', 'BH':'o',
                'B0':' ', 'B25':':', 'BN60':'$', 'B75':'#', 'B100':'@',
                'BLC':'\\', 'TLC':'/', 'BRC':'/', 'TRC':'\\',
                'BLB':'+', 'TLB':'+', 'BRB':'+', 'TRB':'+',
                'TBR':'|', 'TBL':'|', 'BLR':'-', 'TLR':'-', 'TBLR':'+',
                }

grchr['utf8']={ 'hline':'\u2500', 'vline':'\u2502',
                'TH':'\u2580', 'BH':'\u2584',
                'B0':' ', 'B25':'\u2591', 'B50':'\u2593', 'B75':'\u2593', 'B100':'\u2588',
                'BLC':'\u256E', 'TLC':'\u256F', 'BRC':'\u256D', 'TRC':'\u2570',
                'BLB':'\u2510', 'TLB':'\u2518', 'BRB':'\u250C', 'TRB':'\u2514',
                'TBR':'\u251C', 'TBL':'\u2524', 'BLR':'\u252C', 'TLR':'\u2534', 'TBLR':'\u253C',
               }

theme={}
theme['inside']={
        'TL': 'BH', 'TC': 'BH', 'TR': 'BH',
        'ML': 'B100', 'MC': 'B75', 'MR': 'B100',
        'BL': 'TH', 'BC': 'TH', 'BR': 'TH'
        }


theme['outside']={
        'TL': 'B100', 'TC': 'TH', 'TR': 'B100',
        'ML': 'B100', 'MC': 'B0', 'MR': 'B100',
        'BL': 'B100', 'BC': 'BH', 'BR': 'B100'
        }

theme['curve']={
        'TL': 'BRC', 'TC': 'hline', 'TR': 'BLC',
        'ML': 'vline', 'MC': 'B0', 'MR': 'vline',
        'BL': 'TRC', 'BC': 'hline', 'BR': 'TLC'
        }

rgb_file_path = '/usr/share/X11/rgb.txt'

class termcontrol:
    def __init__(self):
        self.x11_colors = self.parse_rgb_file(rgb_file_path)
        self.image_support=[]
        self.img_cache={}
        term=os.environ.get('TERM', '')
        konsole_ver=os.environ.get('KONSOLE_VERSION', '')
        if 'kitty' in term:
            self.image_support.append('kitty')
        if 'vt340' in term or len(konsole_ver or '')>0:
            self.image_support.append('sixel')

    def enable_mouse(self, utf8=True):
        if(utf8):
            return "\x1b[?1005h"
        return "\x1b[?1000h"

    def disable_mouse(self, urf8=True):
        if(utf8):
            return "\x1b[?1005l"
        return "\x1b[?1000l"

    def enable_cursor(self):
        return "\x1b[?25h"
 
    def disable_cursor(self):
        return "\x1b[?25l"

    def normal_screen(self):
        return "\x1b[?1049l"

    def alt_screen(self):
        return "\x1b[?1049h"

    def set_title(self, title):
        return f"\x1b]0;{title}\\a"

    def pause_terminal_output(self):
        sys.stdout.flush()
        os.system('stty -icanon -echo')

    def resume_terminal_output(self):
        sys.stdout.flush()
        os.system('stty icanon echo')

    def parse_rgb_file(self, file_path):
        colors = {}
        if not os.path.isfile(file_path):
            return colors
        return colors
        with open(file_path, 'r') as file:
            for line in file:
                if not line.startswith('!'):
                    parts = line.strip().split('\t')
                    if len(parts) >= 4:
                        name = parts[3].lower()
                        red, green, blue = int(parts[0]), int(parts[1]), int(parts[2])
                        colors[name] = {'red':red, 'green':green, 'blue':blue}
        return colors

    def pause(self):
        print ('[pause]')
        return sys.stdin.readline()

    def get_terminal_size(self):
        import array, fcntl, sys, termios
        buf = array.array('H', [0, 0, 0, 0])
        fcntl.ioctl(sys.stdout, termios.TIOCGWINSZ, buf)
        # Create a dictionary with meaningful keys
        window_info = {
            "rows": buf[0],
            "columns": buf[1],
            "width": buf[2],
            "height": buf[3]
        }
        return window_info

    def color(self, color):
        if type(color)==int:
            return color
        co={
                'black'  : 0,
                'red'    : 1,
                'green'  : 2,
                'yellow' : 3,
                'brown'  : 3,
                'blue'   : 4,
                'magenta': 5,
                'cyan'   : 6,
                'white'  : 7,
                'brightblack'  : 8,
                'brightred'    : 9,
                'brightgreen'  : 10,
                'brightbrown'  : 11,
                'brightyellow' : 11,
                'brightblue'   : 12,
                'brightmagenta': 13,
                'brightcyan'   : 14,
                'brightwhite'  : 15,
            }
        if type(color)==str:
            regex = r'^([A-Fa-f0-9]{6})$'
            if re.match(regex, color) is not None:
                color={
                        'red'  :int(color[0:2], 16),
                        'green':int(color[2:4], 16),
                        'blue' :int(color[4:6], 16),
                      }
                return color
            regex = r'^([A-Fa-f0-9]{3})$'
            if re.match(regex, color) is not None:
                color={
                        'red'  :int(color[0:1], 16)*16,
                        'green':int(color[1:2], 16)*16,
                        'blue' :int(color[2:3], 16)*16,
                      }
                return color
            regex = r'^#([A-Fa-f0-9]{6})$'
            if re.match(regex, color) is not None:
                color={
                        'red'  :int(color[1:3], 16),
                        'green':int(color[3:5], 16),
                        'blue' :int(color[5:7], 16),
                      }
                return color
            regex = r'^#([A-Fa-f0-9]{3})$'
            if re.match(regex, color) is not None:
                color={
                        'red'  :int(color[1:2], 16)*16,
                        'green':int(color[2:3], 16)*16,
                        'blue' :int(color[3:4], 16)*16,
                      }
                return color
            if co.get(color):
                return co.get(color)
            return self.x11_colors.get(color)
        return None

    def ansicolor(self, fg=7, bg=None, 
                  bold=False, dim=False, italic=False, underline=False,
                  strike=False, blink=False, blink2=False, reverse=False):
        if fg=='default':
            fg=7
        if bg=='default':
            bg=None
        fg=self.color(fg)
        bg=self.color(bg)
        fgs=""
        bgs=""
        if type(fg)==int:
            if fg<16:
                if fg<8:
                    fgs=f"{fg+30}"
                else:
                    fgs=f"{(fg-8)+90}"
            else:
                fgs=f'38;5;{fg}'
        elif type(fg)==dict:
            fgs=f'38;2;{fg["red"]};{fg["green"]};{fg["blue"]}'
        if type(bg)==int:
            if bg<16:
                if bg<8:
                    bgs=f"{bg+40}"
                else:
                    bgs=f"{(bg-8)+100}"
            else:
                bgs=f'48;5;{bg}'
        elif type(bg)==dict:
            bgs=f'48;2;{bg["red"]};{bg["green"]};{bg["blue"]}'
        bo, bl, bl2, dm, it, ul, st, rv="","","","","","","", ""
        if bold:bo='1;'
        if dim:bdm='2;'
        if italic:it='3;'
        if underline:ul='4;'
        if blink:bl='5;'
        if blink2:bl2='6;'
        if reverse:rv='7;'
        ansi=""
        if len(bgs) and len(fgs):
            ansi=f'{fgs};{bgs}'
        elif len(bgs):
            ansi=bgs
        elif len(fgs):
            ansi=fgs
        if len(ansi)>0:
            return f"\x1b[{bo}{dm}{it}{ul}{bl}{bl2}{rv}{ansi}m"
        return ""

    def pyte_render(self, x, y, screen, line=1):
        fg='default'
        bg='default'
        bold=False
        blink=False
        w=screen.columns
        h=screen.screen_lines
        start_line=line-1
        if start_line<0:
            start_line=int(screen.cursor.y-h+2)
        if start_line<0:
            start_line=0
        if start_line>int(screen.cursor.y-h+2):
            start_line=int(screen.cursor.y-h+2)
        buffer = self.ansicolor(fg, bg, bold=False, blink=blink)
        for yy in range(start_line, start_line+h):
            buffer += self.gotoxy(x, y+yy-(start_line))
            for xx in range(w):
                if screen.buffer[yy][xx].fg!=fg or screen.buffer[yy][xx].bold!=bold:
                    fg=screen.buffer[yy][xx].fg
                    bold=screen.buffer[yy][xx].bold
                    buffer += self.ansicolor(fg, None, bold=bold)
                if screen.buffer[yy][xx].bg!=bg or screen.buffer[yy][xx].blink!=blink:
                    bg=screen.buffer[yy][xx].bg
                    blink=screen.buffer[yy][xx].blink
                    buffer += self.ansicolor(None, bg, blink=blink)
                buffer += screen.buffer[yy][xx].data
        return buffer

    def gotoxy(self, x, y):
        return f'\x1b[{int(y)};{int(x)}H'

    def clear(self):
        return '\x1b[2J'

    def setbg(self, c):
        return self.ansicolor(None, c)

    def setfg(self, c):
        return self.ansicolor(c, None)

    def clear_images(self):
        out=''
        if 'kitty' in self.image_support:
            out+='\x1b_Ga=d\x1b\\'
        if 'sixel' in self.image_support:
            pass
        return out

    def showImage(self, image, x=0, y=0, w=30, h=15, showInfo=False, mode='auto', charset='utf8'):
        desc=""
        imgX,imgY=0,0
        if(showInfo):
            try:
                img = Image.open(image)
                imgX,imgY=img.size
                img.close()
            except:
                pass
                #logging.WARNING(f"can't open {image} as an image.")
            filename=os.path.basename(image)
            desc=f'({imgX}x{imgY}) {filename}'[:w]
            descX=int(x+(w/2)-(len(desc)/2))+1
            descY=int(y+h)-1
            desc=f'\x1b[s\x1b[48;5;245;30m\x1b[{descY};{descX}H{desc}\n'
        start_pos = f'\x1b[{y};{x+1}H'
        if not self.img_cache.get(image):
            ic=ICat(w=int(w), h=int(h), zoom='aspect', f=True, x=int(0), y=int(0), place=True, mode=mode, charset=charset)
            self.img_cache[image]=ic.print(image)
        return f'{start_pos}{self.img_cache[image]}{desc}'

    class pyteLogger(logging.Logger):
        def __init__(self, refresh_class=None):
            self.refresh_class=refresh_class

        def debug(self, msg, *args, **kwargs):
            logging.debug(msg, *args, **kwargs)
            if self.refresh_class: self.refresh_class.refresh()

        def info(self, msg, *args, **kwargs):
            logging.info(msg, *args, **kwargs)
            if self.refresh_class: self.refresh_class.refresh()

        def warning(self, msg, *args, **kwargs):
            logging.warning(msg, *args, **kwargs)
            if self.refresh_class: self.refresh_class.refresh()

        def error(self, msg, *args, **kwargs):
            logging.error(msg, *args, **kwargs)
            if self.refresh_class: self.refresh_class.refresh()

        def critical(self, msg, *args, **kwargs):
            logging.critical(msg, *args, **kwargs)
            if self.refresh_class: self.refresh_class.refresh()
            exit()

    class boxDraw:
        def __init__(self, bgColor=24,
                    chars="",
                    frameColors=[],
                    title="", statusBar='',
                    mode='auto', charset='utf8',
                    style='inside'):
            self.bgColor=bgColor
            if len(chars)!=9:
                cd=grchr['utf8']
                if charset.lower() in ['utf8', 'utf-8']:
                    cd=grchr['utf8']
                else:
                    cd=grchr['ascii']
                self.chars=f'{cd[theme[style]["TL"]]}{cd[theme[style]["TC"]]}{cd[theme[style]["TR"]]}'\
                            f'{cd[theme[style]["ML"]]}{cd[theme[style]["MC"]]}{cd[theme[style]["MR"]]}'\
                            f'{cd[theme[style]["BL"]]}{cd[theme[style]["BC"]]}{cd[theme[style]["BR"]]}'
            else:
                self.chars=chars
            fr=False
            if len(frameColors)!=9:
                fr=True
            if mode in ['sixel', 'kitty', '24bit', '24-bit', 'auto']:
                if fr:
                    self.frameColors=['#FFF', '#AAA','#777','#AAA', 0, '#555', '#777','#555','#333']
                if type(bgColor)==int and bgColor>255:
                    self.bgColor=0
                else:
                    self.bgColor=bgColor
            elif mode in ['8bit', '8-bit', '256color', '8bitgrey', 'grey', '8bitbright']:
                if fr:
                    self.frameColors=[255, 245, 240, 245, 0, 237, 240, 237, 235]
                if type(bgColor)!=int or bgColor>255:
                    self.bgColor=0
                else:
                    self.bgColor=bgColor
            elif mode in ['4bit', '4-bit', '16color', '4bitgrey']:
                if fr:
                    self.frameColors=[15, 7, 8, 7, 0, 8, 7, 8, 0]
                if type(bgColor)!=int or bgColor>15:
                    self.bgColor=0
                else:
                    self.bgColor=bgColor
            else:
                if fr:
                    self.frameColors=[7, 7, 7, 7, 0, 7, 7, 7, 7]
                self.bgColor=0
            self.tinted=None
            self.title=title
            self.statusBar=statusBar

        def setColors(self, bgcolor, frameColors):
            self.bgColor=bgColor
            self.frameColors=frameColors

        def tintFrame(self, color):
            r,g,b=self.getRGB(color)
            r=r/255.0
            g=g/255.0
            b=b/255.0
            self.tinted=[]
            for i in range(0, len(self.frameColors)):
                fr,fg,fb=self.getRGB(self.frameColors[i])
                fr=int(fr/16*r)
                fg=int(fg/16*g)
                fb=int(fb/16*b)
                self.tinted.append(F"#{fr:X}{fg:X}{fb:X}")

        def unTintFrame(self):
            self.tinted=None

        def setCharacters(self):
            self.chars=chars

        def draw(self, x, y, w, h, fill=True):
            if(w<3): w=3
            if(h<3): h=3
            colors=self.frameColors
            if(self.tinted):
                colors=self.tinted
            buff=self.move(x,y)+\
                self.color(colors[0], self.bgColor)+self.chars[0]+\
                self.color(colors[1], self.bgColor)+self.chars[1]*(w-2)+\
                self.color(colors[2], self.bgColor)+self.chars[2]
            for i in range(1,h-1):
                buff+=self.move(x,y+i)+\
                    self.color(colors[3], self.bgColor)+self.chars[3]
                if(fill):
                    buff+=self.color(colors[4], self.bgColor)+self.chars[4]*(w-2)
                else:
                    iw=w-2
                    buff+=F"\x1b[{iw}C"
                buff+=self.color(colors[5], self.bgColor)+self.chars[5]
            buff+=self.move(x,y+h-1)+\
                self.color(colors[6], self.bgColor)+self.chars[6]+\
                self.color(colors[7], self.bgColor)+self.chars[7]*(w-2)+\
                self.color(colors[8], self.bgColor)+self.chars[8]+"\x1b[0m"
            if self.title!='':
                desc=self.title
                descX=int(x+(w/2)-(len(desc)/2))+1
                descY=int(y)
                descPos=self.move(descX, descY)
                descColor=self.color(16, colors[1])
                buff+=f'{descPos}{descColor}{desc}\n'
            if self.statusBar!='':
                pass
            return buff

    class termKeyboard:
        def __init__(self):
            self.keymap={ "\x1b[A":"Up", "\x1b[B":"Down",\
                     "\x1b[C":"Right", "\x1b[D":"Left",\
                     "\x7f":"Backspace", "\x09":"Tab",\
                     "\x0a":"Enter", "\x1b\x1b":"Esc",\
                     "\x1b[H":"Home", "\x1b[F":"End",\
                     "\x1b[5~":"PgUp", "\x1b[6~":"PgDn",\
                     "\x1b[2~":"Ins", "\x1b[3~":"Del",\
                     "\x1bOP":"F1", "\x1bOQ":"F2",\
                     "\x1bOR":"F3", "\x1bOS":"F4",\
                     "\x1b[15~":"F5", "\x1b[17~": "F6",\
                     "\x1b[18~":"F7", "\x1b[19~": "F8",\
                     "\x1b[20~":"F9", "\x1b[21~": "F10",\
                     "\x1b[23~":"F11", "\x1b[24~": "F12",\
                     "\x1b[32~":"SyRq", "\x1b[34~": "Brk",
                     "\x1b[Z":"Shift Tab"}

        def disable_keyboard_echo(self): # Get the current terminal attributes
            attributes = termios.tcgetattr(sys.stdin)
            # Disable echo flag
            attributes[3] = attributes[3] & ~termios.ECHO
            # Apply the modified attributes
            termios.tcsetattr(sys.stdin, termios.TCSANOW, attributes)

        def enable_keyboard_echo(self): # Get the current terminal attributes
            attributes = termios.tcgetattr(sys.stdin)
            # Enable echo flag
            attributes[3] = attributes[3] | termios.ECHO
            # Apply the modified attributes
            termios.tcsetattr(sys.stdin, termios.TCSANOW, attributes)

        def binread(self):
            return sys.stdin.buffer.read(1)

        def read(self):
            try:
                return sys.stdin.read(1)
            except:
                return sys.stdin.buffer.read(1)
            return ''

        def ord(self, d):
            if(type(d)==int):
                return d
            if(type(d)==str):
                return ord(d[0])
            if(type(d)==bytes):
                return int.from_bytes(d)
            return int(d)

        def read_keyboard_input(self): # Get the current settings of the terminal
            filedescriptors = termios.tcgetattr(sys.stdin)
            # Set the terminal to cooked mode
            tty.setcbreak(sys.stdin)
            char = self.read()
            buffer=char
            # Check if the character is an arrow key or a function key
            if char == "\x1b":
                char = self.read()
                buffer+=char
                if(char=='O'):
                    char = self.read()
                    buffer+=char
                elif char=='[':
                    char = self.read()
                    buffer+=char
                    if char=='M':
                        b = self.ord(self.read())-32
                        x = self.ord(self.read())-32
                        y = self.ord(self.read())-32
                        #TODO handle mouse code ---
                        buffer+=f'{b};{x};{y}'
                    else:
                        while char>='0' and char<='9' or char==';':
                            char = self.read()
                            buffer+=char

            # Restore the original settings of the terminal
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, filedescriptors)
            key=self.keymap.get(str(buffer))
            return key or str(buffer)


