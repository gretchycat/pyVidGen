#!/usr/bin/python3
import io, os,sys,termios,tty, subprocess, base64, sixel
from optparse import OptionParser
from icat import ICat 
from PIL import Image
from base64 import standard_b64encode

class boxDraw:
    def __init__(self, bgColor='#157', \
                chars="\u2584\u2584\u2584\u2588\u2593\u2588\u2580\u2580\u2580",\
                frameColors=['#FFF', '#AAA','#777','#AAA', 0, '#555', '#777','#555','#333'],\
                title="", statusBar=''):
        self.bgColor=bgColor
        self.chars=chars
        self.frameColors=frameColors
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

    def getRGB(self, hex_triplet):
        if type(hex_triplet) != str:
            hex_triplet="#000"
        hex_triplet = hex_triplet.lstrip('#')  # Remove the '#' character if present
        if len(hex_triplet) == 3:
            hex_triplet = ''.join([c * 2 for c in hex_triplet])  # Expand shorthand format
        r = int(hex_triplet[0:2], 16)
        g = int(hex_triplet[2:4], 16)
        b = int(hex_triplet[4:6], 16)
        return r, g, b

    def color(self,fg,bg): 
        bgS=""
        fgS=""
        if type(fg)==int:
            fgS=F"38;5;{fg}"    
        if type(fg)==str:
            (r,g,b)=self.getRGB(fg)
            fgS=F"38;2;{r};{g};{b}"
        if type(bg)==int:
            bgS=F"48;5;{fg}"    
        if type(bg)==str:
            (r,g,b)=self.getRGB(bg)
            bgS=F"48;2;{r};{g};{b}"
        if bgS=="" and fgS!="":
            return F"\x1b[{fgS}m"
        if bgS!="" and fgS!="":
            return F"\x1b[{fgS};{bgS}m"
        if bgS!="" and fgS=="":
            return F"\x1b[{bgS}m"
        return ""

    def move(self,x,y):
        buf=""
        buf+=F"\u001b[{y};{x}H"
        return buf

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
                 "\x1bOR":"F3", "\x1bOS": "F4",\
                 "\x1b[15~":"F5", "\x1b[17~": "F6",\
                 "\x1b[18~":"F7", "\x1b[19~": "F8",\
                 "\x1b[20~":"F9", "\x1b[21~": "F10",\
                 "\x1b[23~":"F11", "\x1b[24~": "F12",\
                 "\x1b[32~":"SyRq", "\x1b[34~": "Brk" }

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

    def read_keyboard_input(self): # Get the current settings of the terminal
        filedescriptors = termios.tcgetattr(sys.stdin)

        # Set the terminal to cooked mode
        tty.setcbreak(sys.stdin)

        # Read a character from the terminal
        char = sys.stdin.read(1)
        buffer=char
        # Check if the character is an arrow key or a function key
        if char == "\x1b":
            char = sys.stdin.read(1)
            buffer+=char
            if(char=='O'):
                char = sys.stdin.read(1)
                buffer+=char
            elif char=='[':
                char = sys.stdin.read(1)
                buffer+=char
                while char>='0' and char<='9' or char==';':
                    char = sys.stdin.read(1)
                    buffer+=char
        # Restore the original settings of the terminal
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, filedescriptors)
        key=self.keymap.get(buffer)
        return key or buffer

class imageSelect:
    def __init__(self):
        pass

    def showImage(self, image, x=0, y=0, w=30, h=15, showInfo=False):
        def write_chunked(data, items):
            def serialize_gr_command(payload, items):
                cmd = ','.join(f'{k}={v}' for k, v in items.items())
                ans = []
                w = ans.append
                w('\x1b_G'), w(cmd)
                if payload:
                    w(';')
                    w(payload)
                w('\x1b\\')
                return ''.join(ans)
            out=''
            base64=standard_b64encode(data).decode('ascii')
            while base64:
                chunk, base64 = base64[:4096], base64[4096:]
                m = 1 if base64 else 0
                items['m']=m
                out+=(serialize_gr_command(chunk, items ))
                items.clear()
            return out

        def get_terminal_size():
            import array, fcntl, sys, termios
            buf = array.array('H', [0, 0, 0, 0])
            fcntl.ioctl(sys.stdout, termios.TIOCGWINSZ, buf)
            return {
                        "rows": buf[0],
                        "columns": buf[1],
                        "width": buf[2],
                        "height": buf[3]
                    }

        desc=""
        if(showInfo):
            img = Image.open(image)
            imgX,imgY=img.size
            imgAR=imgY/imgX
            img.close()
            filename=os.path.basename(image)
            desc=f'({imgX}x{imgY}) {filename}'[:w]
            descX=int(x+(w/2)-(len(desc)/2))+1
            descY=int(y+h)-1
            desc=f'\x1b[s\x1b[48;5;245;30m\x1b[{descY};{descX}H{desc}\n'
        start_pos = f'\x1b[{y};{x+1}H'
        has_kitty, has_sixel= 'kitty' in os.environ.get('TERM', ''), True
        if has_kitty or has_sixel:
            size=get_terminal_size()
            img = Image.open(image)
            # Calculate the scaling factor while preserving the aspect ratio
            cell_w=size['width']/size['columns']
            cell_h=size['height']/size['rows']
            newW=cell_h*w/imgAR
            newH=cell_w*h*imgAR
            if newH>h*cell_h:
                newH=h*cell_h
            if newW>w*cell_w:
                newW=w*cell_w
            # Resize the image
            img = img.resize((int(newW), int(newH)), Image.LANCZOS)
            # Generate a PNG stream
            png_stream = io.BytesIO()
            img.save(png_stream, format='PNG')
            png_stream.seek(0)
            if has_kitty:
                items={"a": "T", "f":100}
                out=f'{start_pos}{write_chunked(png_stream.getvalue(), items)}'
            if has_sixel:
                #sxi=sixel.SixelImage.from_pil_image(img)
                #out=f'{start_pos}{image_size}{sxi.get_sixel_string()}'
                pass
            png_stream.close()
            return out+desc
        ic=ICat(w=int(w), h=int(h), zoom='aspect', f=True, x=int(x), y=int(y)) 
        return ic.print(image)+desc

    def convert_to_escape(self, text):
        escape_text = ""
        for char in text:
            if char.isprintable():
                escape_text += char
            else:
                escape_text += "\\x" + hex(ord(char))[2:]
        return escape_text

    def copy_image(self, source_path, destination_path):
        try:
            # Open the source image
            source_image = Image.open(source_path)
            # Save a copy of the source image to the destination path
            source_image.save(destination_path, format='PNG')
            print(f"Image copied from {source_path} to {destination_path}")
        except IOError as e:
            print(f"Unable to copy image from {source_path} to {destination_path} ({e})")

    def interface(self, target, images, describe):
        buffer=""
        kb=termKeyboard()
        # Save the current terminal settings
        stdin_fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(stdin_fd)
        kb.disable_keyboard_echo()
        #start reporting mouse events
        print("\x1b[?1000h\x1b[?25l",end='')
        cols=3
        rows=3
        selected=int((cols*rows)/2)
        page=0
        x0=4
        xsep=2
        y0=2
        ysep=0
        backBox=boxDraw( bgColor='#157',\
                chars="\u2588\u2580\u2588\u2588 \u2588\u2588\u2584\u2588",\
                title=describe, statusBar='')
        backBox.tintFrame("#9DF")
        box=boxDraw()
        key=''
        refresh=True
        while True:
            screenrows, screencolumns = os.popen('stty size', 'r').read().split()
            w=int((int(screencolumns)+1-((x0-1)*2)-((cols-1)*xsep))/cols)
            h=int((int(screenrows)+1-((y0-1)*2)-((rows-1)*ysep))/rows)
            buffer=""
            if refresh:
                buffer+=(backBox.draw(1,1, int(screencolumns), int(screenrows)))
                drawBoxes=True
                fillBoxes=True
            for x in range(0,cols):
                for y in range(0,rows):
                    c=x0+(w*x)+(xsep*x)
                    r=y0+(h*y)+(ysep*y)
                    index=x+(y+page)*cols
                    if index==selected:
                        box.tintFrame("#F00")
                    else:
                        box.unTintFrame()
                    if drawBoxes:
                        buffer+=(box.draw(c,r,w,h,fillBoxes))
                    if index<len(images) and refresh:
                        buffer+=self.showImage(images[index], x=c, y=r+1, w=w-2, h=h-2, showInfo=True)
            refresh=False
            drawBoxes=False
            fillBoxes=False
            print(buffer,end='')
            print(F"\x1b[0;0H",end='')
            key=kb.read_keyboard_input()

            page0=page
            if key=="Up":
                if selected-cols>=0:
                    selected=selected-cols
                    drawBoxes=True
            if key=="Down":
                if selected+cols<len(images):
                    selected=selected+cols
                    drawBoxes=True
            if key=="Left":
                if selected%cols>0:
                    selected=selected-1
                    drawBoxes=True
            if key=="Right":
                if selected%cols<cols-1:
                    selected=selected+1
                    drawBoxes=True
            if key=="Enter":
                if selected<len(images):
                    print(self.showImage(images[selected],\
                        w=int(screencolumns),\
                        h=int(screenrows))+'-'*(int(screencolumns)))
                    print("\x1b[KSelect this image? (y/n)")
                    key=kb.read_keyboard_input()
                    if key=='y' or key=='Y':
                        imagefile=images[selected]
                        print(F"\x1b[Jchose:'{imagefile}'")
                        print("writing target image: "+target)
                        self.copy_image(imagefile, target)
                        break
                    refresh=True

            if key=='q' or key=='Esc' or key=='Q' or key=='Backspace':
                print("\x1b[2J",end='')
                break
            while(selected<(x+((page-1))*cols)):
                page=page-1
            while(selected>(x+(y+page)*cols)):
                page=page+1
            if(page0!=page):
                refresh=True

        print(F"\x1b[1000l\x1b[?25h")
        kb.enable_keyboard_echo()
        termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_settings)

def main():
    parser=OptionParser(usage="usage: %prog [options] filelist")
    parser.add_option('-t', '--target', dest='target', default='selected.png',
            help='the target filename for the image.')
    parser.add_option('-d', '--describe', dest='describe', default='',
            help='Text to describe the image.')
    (options, args)=parser.parse_args()
    if len(args)==0:
        parser.print_help()
    else:
        imgs=imageSelect()
        imgs.interface(options.target, args, options.describe)

if __name__ == "__main__":
    main()

