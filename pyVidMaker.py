#!/usr/bin/python3
import sys, hashlib, subprocess, logging, colorlog, datetime, glob, shutil, io
import os, json, mistune, xml.etree.ElementTree as ET, binascii, fcntl, termios
import string, xml.dom.minidom as minidom, pyte, configparser, pydub, re, array
from pprint import pprint
from optparse import OptionParser
from gtts import gTTS
from icat import imageSelect
from SearchImages import SearchImages
from rich.text import Text

image_types=['.image', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tif', '.tiff', '.pcx']
video_types=['.video', '.mp4', '.mkv', '.mpg', '.avi', '.asf', '.qt', '.mov']
audio_types=['.audio', '.mp3', '.wav', '.ogg', '.flac', '.alac', '.mp2', ]

def isImage(filepath):
    return os.path.splitext(filepath)[1].lower() in image_types

def isVideo(filepath):
    return os.path.splitext(filepath)[1].lower() in video_types

def isAudio(filepath):
    return os.path.splitext(filepath)[1].lower() in audio_types

def get_terminal_size():
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

def page_fit(text, max_length):
    # Split the text into words
    words = text.split()
    # Initialize variables
    result = []
    current_line = []
    for word in words:
        if len(' '.join(current_line + [word])) <= max_length:
            # If adding the word to the current line doesn't exceed the max length, add it
            current_line.append(word)
        else:
            # If adding the word would exceed the max length, start a new line
            if current_line:
                result.append(' '.join(current_line))
            current_line = [word]
    # Add the last line to the result
    if current_line:
        result.append(' '.join(current_line))
    return result

def color(color):
    if type(color)==int:
        return color
    co={
            'black'  : 0, # 'bg':0 },
            'red'    : 1, #'bg':1 },
            'green'  : 2, #'bg':2 },
            'yellow' : 3, #'bg':3 },
            'brown'  : 3, #'bg':3 },
            'blue'   : 4, #'bg':4 },
            'magenta': 5, #'bg':5 },
            'cyan'   : 6, #'bg':6 },
            'white'  : 7, #'bg':7 },
            'brightblack'  : 8,
            'brightred'    : 9,
            'brightgreen'  : 10,
            'brightbrown'  : 11,
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
        if co.get(color):
            return co.get(color)
    return None

def ansicolor(fg=7, bg=0, bold=False, blink=False):
    if fg=='default':
        fg=7
    if bg=='default':
        bg=None
    fg=color(fg)
    bg=color(bg)
    fgs=""
    bgs=""
    if type(fg)==int:
        fgs=f'38;5;{fg}'
    elif type(fg)==dict:
        fgs=f'38;2;{fg["red"]};{fg["green"]};{fg["blue"]}'
    if type(bg)==int:
        bgs=f'48;5;{bg}'
    elif type(bg)==dict:
        bgs=f'48;2;{bg["red"]};{bg["green"]};{bg["blue"]}'
    bo, bl="",""
    if bold:
        bo='1;'
    if blink:
        bl='5;'
    ansi=""
    if len(bgs) and len(fgs):
        ansi=f'{fgs};{bgs}'
    elif len(bgs):
        ansi=bgs
    elif len(fgs):
        ansi=fgs
    if len(ansi)>0:
        return f"\x1b[{bo}{bl}{ansi}m"
    return ""

def gotoxy(x, y):
    return f'\x1b[{y};{x}H'

def clear():
    return '\x1b[2J'

def setbg(c):
    return ansicolor(None, c)

def setfg(c):
    return ansicolor(c, None)

def pyte_render(x, y, screen, line=1):
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
    buffer = ansicolor(fg, bg, bold=False, blink=blink)
    for yy in range(start_line, start_line+h):
        buffer += gotoxy(x, y+yy-(start_line))
        for xx in range(w):
            if screen.buffer[yy][xx].fg!=fg or screen.buffer[yy][xx].bold!=bold:
                fg=screen.buffer[yy][xx].fg
                bold=screen.buffer[yy][xx].bold
                buffer += ansicolor(fg, None, bold=bold)
            if screen.buffer[yy][xx].bg!=bg or screen.buffer[yy][xx].blink!=blink:
                bg=screen.buffer[yy][xx].bg
                blink=screen.buffer[yy][xx].blink
                buffer += ansicolor(None, bg, blink=blink)
            buffer += screen.buffer[yy][xx].data
    return buffer

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

class VidMaker:
    def __init__(self, script_file, resolution, debug):
        self.clips=None
        self.backbox=imageSelect.boxDraw(style='outside')
        self.statusbox=imageSelect.boxDraw(style='outside', bgColor=234)
        self.statusbox.tintFrame('#FF0000')
        print('\x1b[2J')
        self.globals={}
        self.script_file=script_file
        self.basefn0,self.ext= os.path.splitext(script_file)
        self.basefn0=os.path.basename(script_file)
        if resolution:
            basefn=f"{self.basefn0}.{resolution}"
            self.resolution=resolution
            self.xres, self.yres=map(int, self.resolution.split('x'))
        else:
            basefn=self.basefn0
            self.resolution=False
        self.term_size=get_terminal_size()
        col=self.term_size['columns']
        row=self.term_size['rows']
        sts_col=col-(4*2)
        sts_row=int(row/2)-4
        log_col=col
        log_row=row-sts_row-(2*2)
        scrollback=10000
        self.log_screen = pyte.HistoryScreen(log_col, log_row)
        self.log_screen.screen_lines=log_row
        self.log_screen.mode.add(pyte.modes.LNM)
        self.status_screen = pyte.HistoryScreen(sts_col, scrollback)
        self.status_screen.screen_lines=sts_row
        self.status_screen.mode.add(pyte.modes.LNM)
        # Create a pyte stream.
        self.log_stream = pyte.Stream(self.log_screen)
        self.log_stream.write=self.log_stream.feed
        self.status_stream = pyte.Stream(self.status_screen)
        self.res=get_terminal_size()
        self.resize()
        # Log file
        self.log_file = basefn+".log"
        # Set up logger
        self.debug=debug
        self.setup_logger(debug)
        self.work_dir = self.basefn0+'.work'
        os.makedirs(self.work_dir, exist_ok=True)
        os.makedirs('search', exist_ok=True)
        self.sub_file = self.work_dir+'/'+self.basefn0+".srt"
        self.markdown=mistune.create_markdown(renderer=None)

    def resize(self):
        if self.res!=get_terminal_size():
            self.res=get_terminal_size()
            col=self.term_size['columns']
            row=self.term_size['rows']
            sts_col=col-(4*2)
            sts_row=int(row/2)-4
            log_col=col
            log_row=row-sts_row-(2*2)
            #self.log_screen.resize(log_col, log_row)
            #self.status_screen.resize(sts_col, sts_row)
            return True
        return False

    def interface(self, decoration=True):
        lines=0
        decoration=decoration or self.resize()
        def print_fn(fn):
            missing=True
            buffer=""
            if self.file_exists(f'{self.work_dir}/{fn}'):
                missing=False
                buffer+=setfg(10)
            else:
                buffer+=setfg(9)
            buffer+=fn
            return buffer, missing

        def draw_clip(box, clip):
            buffer=""
            buffer+=setbg(box.bgColor)
            out, missingClip=print_fn(clip.get('FilePath') or 'no file yet')
            buffer+=f'{out}\n'
            buffer+=setfg(7)
            buffer+=' '*4
            all_media=clip.get('Media')
            media_files=[]
            missing=False
            if all_media:
                for media in all_media:
                    out,m=print_fn(media['FilePath'])
                    missing=missing or m
                    media_files.extend([ out ])
            if missing or True:
                buffer+=f"{setfg(15)}, ".join(media_files)
            return f'{buffer}\n', missing, missingClip
        buffer=""
        col=self.term_size['columns']
        row=self.term_size['rows']
        if decoration:
            buffer +=self.backbox.draw(1, 1, col, self.status_screen.screen_lines+4)
            buffer += self.statusbox.draw(3, 2, col-4, self.status_screen.screen_lines+2)
        #display process summary
        first_missing_clip=None
        first_missing_media=None
        self.status_stream.feed(setbg(self.statusbox.bgColor)+gotoxy(1,1)+clear())
        if self.clips:
            n=len(self.clips)
            if self.clips:
                for clip in self.clips:
                    out, missing, missingClip=draw_clip(self.statusbox, clip)
                    self.status_stream.feed(out)
                    c=self.status_screen.cursor
                    if missing and first_missing_media==None:
                        first_missing_media=[c.x, c.y]
                    if missingClip and first_missing_clip==None:
                        first_missing_clip=[c.x, c.y]
        cursor=None
        if first_missing_media:
            cursor=first_missing_media
        else:
            cursor=first_missing_clip
        line=1
        if cursor:
            line=cursor[1]-int(self.status_screen.screen_lines/2)
        if line<1:
            line=1
        buffer += ansicolor(None, self.statusbox.bgColor)
        buffer += pyte_render(5, 3, self.status_screen, line)
        #display log terminal
        buffer += ansicolor(None, 0)
        buffer += pyte_render(1, int(self.status_screen.screen_lines+(2*2)+1), self.log_screen)
        return buffer

    def refresh(self):
        self.buffer=self.interface(decoration=False)
        self.blit_buffer()

    def full_refresh(self):
        self.buffer=self.interface(decoration=True)
        self.blit_buffer()

    def setup_logger(self, debug):  #, x. y. screen):
        """ Create a formatter with color """
        stderr_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(levelname)s:%(reset)s%(message)s',
            log_colors={
                'DEBUG': 'bold_blue',
                'INFO': 'bold_green',
                'WARNING': 'bold_yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            }
        )
        log_formatter = colorlog.ColoredFormatter(
            '%(levelname)s:%(message)s'
        )
        level=logging.WARNING
        if debug.lower()=="debug":
            level=logging.DEBUG
        elif debug.lower()=="info":
            level=logging.INFO
        elif debug.lower()=="warning":
            level=logging.WARNING
        else:
            level=logging.WARNING

        # Create a file handler for the log file
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setFormatter(log_formatter)

        # Create a stream handler for stderr
        stderr_handler = logging.StreamHandler(self.log_stream)
        stderr_handler.setLevel(level)
        stderr_handler.setFormatter(stderr_formatter)

        # Configure the root logging with the handlers
        logging.root.handlers = [file_handler, stderr_handler]
        logging.root.setLevel(logging.DEBUG)
        logging.setLoggerClass(pyteLogger)
        logging.refresh_class=self
        logger.refresh_class=self

    def blit_buffer(self):
        sys.stdout.write(self.buffer)
        sys.stdout.flush()
        self.buffer=""

    def pct_to_float(self, percentage_str):
        if type(percentage_str) == str:
            if "%" in percentage_str:
                # Remove "%" sign and convert to float
                value = float(percentage_str.replace("%", ""))
            else:
                # Convert string to float
                value = float(percentage_str)
            if value >= 0.0 and value <= 1.0:
                return value
            elif value >= 5.0 and value <= 100.0:
                return value / 100.0
            else:
                raise ValueError("Percentage value is outside the valid range")
        return 1.0

    def translate_color(self, color):
        if len(color) == 4 and color.startswith("#"):  # Handle 3-character color code
            r = color[1]
            g = color[2]
            b = color[3]
            return f"#{r}{r}{g}{g}{b}{b}"
        else:
            return color  # Return the color code as is if not in the expected format

    def format_time(self, seconds):
        seconds=float(seconds)
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return "{:02d}:{:02d}:{:02d}.{:02d}".format(hours, minutes, seconds, milliseconds)

    def execute_command(self, command):
        """
        Executes a command in the system and logs the command line and output.
        """
        try:
            anim='\U0001f311\U0001f312\U0001f313\U0001f314' #moon phase animation
            anim+='\U0001f315\U0001f316\U0001f317\U0001f318'
            frame=0.0
            output=""
            sepw=60
            logger.info('-'*sepw)
            logger.info(f"Executing command: {' '.join(command)}")
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            outbuffer=''
            ts=get_terminal_size()
            x,y=int(ts['columns']/2),int(ts['rows']/4*3)
            for line in process.stdout:
                logger.debug(line.rstrip('\n'))
                output+=line
                outbuffer+=line
                print(f'{gotoxy(x,y)}{ansicolor(15,0)}{anim[int(frame)%len(anim)]}{gotoxy(int(ts["columns"]), int(ts["rows"])-1)}')
                frame+=0.2
            process.wait()
            process.output=output
            if(process.returncode>0):
                logger.error(process.output)
                logger.critical(f"Error executing command. ({process.returncode})")

            return process
        except Exception as e:
            logger.critical(f"Error executing command: {e}")
            self.blit_buffer()

    def file_exists(self, file_path):
        """
        Checks if a file exists at the given file path.
        Returns True if it exists, False otherwise.
        """
        #return self.update_type(file_path)
        if file_path:
            if os.path.isfile(file_path):
                return True
        return False

    def search_media(self, search_query, num_images, output_directory):
        self.si.search_media_pexels(search_query, num_images, output_directory)
        #self.si.search_images_google(search_query, num_images, output_directory)
        #self.si.search_images_bing(search_query, num_images, output_directory)
        self.si.search_media_pixabay(search_query, num_images, output_directory)

    def generate_tts_audio_buffer(self, audio_buffer_file, text_content, voice='gtts', lang='en', tld='com.au', speed=1.0, pitch=1.0):
        """
        Generates a TTS audio buffer using GTTS from the provided text content
        and saves it to the specified audio buffer file.
        """
        #TODO Add Mozilla TTS and pyTTS
        audio_buffer_file=os.path.splitext(audio_buffer_file)[0]+'.mp3'
        if not self.file_exists(audio_buffer_file):
            if voice=='gtts':
                tts = gTTS(text_content, lang=lang, tld=tld, slow=False)
                # Adjust speed and pitch if necessary
                    # Modify the speech with pydub
                speed=1.2
                if speed != 1.0 or pitch != 1.0 or True:
                    buffer=io.BytesIO()
                    tts.write_to_fp(buffer)
                    buffer.seek(0)
                    audio = pydub.AudioSegment.from_mp3(buffer)
                    audio = audio.set_frame_rate(48000)
                    audio = audio.set_channels(2)
                    #audio = audio.set_balance(0)
                    if speed!=1.0:
                        audio = audio.speedup(playback_speed=speed)
                    if pitch != 1.0:
                        pass
                        #audio = audio.set_frame_rate(int(audio.frame_rate * pitch))
                    # Export the modified audio to the specified file
                    audio.export(audio_buffer_file, format='mp3', bitrate='192k')
                else:
                    # Save the original audio to the specified file
                    tts.save(audio_buffer_file)

    def dir_exists(self, file_path):
        """
        Checks if a file exists at the given file path.
        Returns True if it exists, False otherwise.
        """
        if file_path is not None:
            return os.path.isdir(file_path)
        return False

    def update_type(self, file_path):
        """
        Checks if a alternate file exists at the given file path.
        Returns the existing  file or alt if it exists, False otherwise.
        """
        if file_path:
            ext=os.path.splitext(file_path)[1]
            name=os.path.splitext(file_path)[0]
            if ext.lower() in image_types+video_types:
                for e in image_types+video_types:
                    logger.debug(f"Checking {name}{e}")
                    if os.path.isfile(f'{name}{e}'):
                        logger.info(f"Found {name}{e}")
                        return f'{name}{e}'
            elif ext.lower() in audio_types:
                for e in audio_types:
                    if os.path.isfile(f'{name}{e}'):
                        logger.info(f"Found {name}{e}")
                        return f'{name}{e}'
            if os.path.isfile(file_path):
                logger.info(f"Found {file_path}")
                return file_path
        logger.warning(f"{file_path} not found")
        return False

    def get_missing_file(self, type, file_path, description, script):
        copied=""
        if file_path:
            log=logger.info
            verb="Acquiring"
            log(f"{verb} {type}: {file_path}\n\tDescription: {description}\n\tScript: {script}")
            if type.lower()=="tts":
                verb="Generated"
                self.generate_tts_audio_buffer(file_path, script)
            elif type.lower() in ["image", "video"]:
                verb="Found"
                while not self.file_exists(file_path):
                    print('\x1b[2;3H\x1b[97mPlease enter new search terms.')
                    print(f'\x1b[3;3H\x1b[97mScript: \x1b[93m"{script}"')
                    desc=input(f'\x1b[4;3H\x1b[97m[{description}]: \x1b[0m'+' '*25+"\x1b[25D")
                    if(desc!=''):
                        description=desc
                    search_dir=f'search/{description.lower()}'[:24]
                    if not self.dir_exists(search_dir):
                        logger.info(f"Downloading media: '{description}'")
                        self.search_media(description, 20, search_dir)
                    logger.info(f"Loading media: '{description}'")
                    imgs=imageSelect.imageSelect()
                    for handler in logging.root.handlers[:]:
                        logging.root.removeHandler(handler)
                    copied=imgs.interface(file_path, glob.glob(f'{search_dir}/*'), description[:40])
                    imgs.clear_images()
                    clear()
                    self.setup_logger(self.debug)
                    if copied != file_path:
                        self.rename[file_path]=copied
                        file_path=copied
                    self.full_refresh()
            missing=0 if self.file_exists(self.update_type(file_path)) else 1
            if missing>0:
                verb="Missing"
                log=logger.warning
            log(f"{verb} {type}: {file_path}")
            return missing
        return 0

    def generate_temp_filename(self, fnkey=None):
        if(fnkey):
            translation_table = str.maketrans('', '', string.punctuation + string.whitespace)
            fnkey = fnkey.translate(translation_table).replace(' ', '_')[:30]
            if(len(fnkey)<32):
                return f"temp_{fnkey}"
            else:
                return "temp_"+hashlib.md5(fnkey.encode('utf-8')).hexdigest()
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        return f"temp_{timestamp}"

    def get_file_format(self, file_path):
        if self.file_exists(file_path):
            command = [
                'ffprobe',
                '-v',
                'quiet',
                '-show_streams',
                '-show_format',
                '-print_format',
                'json',
                file_path
            ]
            output = subprocess.check_output(command).decode('utf-8')
            json_data = json.loads(output)
            return json_data
        else:
            if(file_path):
                logger.warning(f"Missing File: {file_path}")
        return None

    def get_file_duration(self, file_path):
        json_data=self.get_file_format(file_path)

        if json_data:
            duration = float(json_data['format']['duration'])
            return duration
        return 0.0

    def get_file_resolution(self, file_path):
        json_data=self.get_file_format(file_path)
        if json_data:
            for st in json_data['streams']:
                if st['codec_type']=='video':
                    return st['width'], st['height']
        return 0, 0

    def has_audio(self, file_path):
        json_data=self.get_file_format(file_path)
        if json_data:
            for st in json_data['streams']:
                if st['codec_type']=='audio':
                    return True
        return False

    def handle_md_children(self, xml, md, level=0):
        list_created=False
        for e in md:
            tp=e['type']
            ch=e.get("children")
            if tp=="heading":
                self.generate_md_heading(xml, e)
            elif tp=="list":
                if not 'list' in self.globals['md_context']:
                    self.globals['md_join']=True
                    self.globals['md_count']=0
                    list_created=True
                    self.globals['md_filters']=None
                    self.globals['md_clip']=None
                    self.generate_md_list(xml, e)
            elif tp=="list_item":
                self.generate_md_list_item(xml, e)
            elif tp=="paragraph":
                self.generate_md_paragraph(xml, e)
            elif tp=="blank_line":
                self.generate_md_blank_line(xml, e)
            elif tp=="text":
                self.generate_md_text(xml, e)
            elif tp=="strong":
                self.generate_md_strong(xml, e)
            elif tp=="emphasis":
                self.generate_md_emphasis(xml, e)
            else:
                logger.warning(f'Unhandled md data: {tp}')
            #print("  "*level+tp+ ' ' +str(list_created))
            if ch:
                self.handle_md_children(xml, ch, level+1)
            if list_created:
                self.globals['md_join']=False
                #print("  "*level+"====")
                list_created=False
            if not self.globals['md_join']:
                while len(self.globals['md_context'])>0:#context_items:
                    self.globals['md_context'].pop()
                self.globals['md_filters']=None
                self.globals['md_clip']=None
                self.globals['md_count']=0
        return

    def generate_md_heading(self, xml, md):
        self.globals['md_context'].append('heading')

    def generate_md_emphasis(self, xml, md):
        self.globals['md_context'].append('emphasis')

    def generate_md_list(self, xml, md):
        self.globals['md_context'].append('list')

    def generate_md_paragraph(self, xml, md):
        pass

    def generate_md_blank_line(self, xml, md):
        pass

    def generate_md_list_item(self, xml, md):
        pass

    def generate_md_text(self, xml, md):
        text=md.get('raw')
        img_media=None
        tts_media=None
        ttsdelay=0.0
        if self.globals.get('md_clip_num')==None:
            self.globals['md_clip_num']=0
        else:
            self.globals['md_clip_num']+=1
        if not self.globals['md_clip']:
            self.globals['md_clip']=ET.SubElement(xml, 'Clip')
            self.globals['md_filters']=None
            ET.SubElement(self.globals['md_clip'], 'FilePath').text=f"Clip{self.globals['md_clip_num']:04}.mp4"
            properties=ET.SubElement(self.globals['md_clip'], 'Properties')
        if not self.globals['md_filters']:
            #normal:  Video capable media, TTS
            #heading: add text overlay -- Title style
            #list:    add text overlay -- calculate position in a list style, keep text for duration of list
            #strong:  add text overlay -- calculate position keep for duration of text after the bold
            img_media=ET.SubElement(self.globals['md_clip'], 'Media')
            img_media.set('type', 'Image')
            ttsdelay=0.0
        else:
            ttsdelay=-1

        tts_media=ET.SubElement(self.globals['md_clip'], 'Media')
        tts_media.set("type", "TTS")
        ET.SubElement(tts_media, 'Script').text=f'{text}'
        ET.SubElement(tts_media, 'FilePath').text=f'{self.generate_temp_filename(text)}.audio'
        ET.SubElement(tts_media, 'StartTime').text=f'{ttsdelay}'
        ET.SubElement(tts_media, 'Duration').text=f'-1'
        ET.SubElement(tts_media, 'UseForCC').text=f'True'
        ET.SubElement(tts_media, 'Volume').text=f'100%'
        if(text):
            if not self.globals['md_filters']:
                self.globals['md_filters']=ET.SubElement(img_media, 'filters')
            if(img_media):
                ET.SubElement(img_media, 'Description').text=text
                ET.SubElement(img_media, 'FilePath').text=f'{self.generate_temp_filename(text)}.image'
                ET.SubElement(img_media, 'StartTime').text=f'0.0'
                ET.SubElement(img_media, 'Duration').text=f'-1'
                ET.SubElement(img_media, 'Position').text=f'Aspect'
            if(any(itm in self.globals['md_context'] for itm in ['list','strong','heading','emphasis'])):
                base_size=1
                size=1
                if 'heading' in self.globals['md_context']:
                    size=3
                cr='\n'
                words_per_line=72/size
                drawtext=ET.SubElement(self.globals['md_filters'], 'filter')
                drawtext.set('type', 'drawtext')
                ET.SubElement(drawtext, 'Text').text=f"{cr.join(page_fit(text, words_per_line))}"
                ET.SubElement(drawtext, 'StartTime').text=f'{ttsdelay*0}'
                ET.SubElement(drawtext, 'Duration').text=f'-1'
                ET.SubElement(drawtext, 'FontSize').text=f'{size*base_size}'
                ET.SubElement(drawtext, 'FontColor').text=f'#FFF'
                ET.SubElement(drawtext, 'FontFile').text=f'font.ttf'
                ET.SubElement(drawtext, 'BorderColor').text=f'#000'
                ET.SubElement(drawtext, 'BorderWidth').text=f'5'
                if 'list' in self.globals['md_context']:
                    ET.SubElement(drawtext, 'BoxColor').text=f'#DDFF007F'
                else:
                    ET.SubElement(drawtext, 'BoxColor').text=f'#0000007F'
                if 'list' in self.globals['md_context']:
                    ET.SubElement(drawtext, 'X').text='w/4'
                    ET.SubElement(drawtext, 'Y').text=f'(h/10)-(text_h-ascent)+{self.globals["md_count"]*(self.xres/40)*size*1.125}'
                else:
                    ET.SubElement(drawtext, 'TextAlign').text='MC'
                    ET.SubElement(drawtext, 'X').text='(w-tw)/2'
                    ET.SubElement(drawtext, 'Y').text=f'(h-th)/2'
                self.globals['md_count']+=1
            #TODO add drawtext filter for contexts
            #TODO handle contexts
        else:
            logger.warning('Missing "raw" text')#TODO get a better warning
        return

    def generate_md_strong(self, xml, md):
        self.globals['md_context'].append('strong')

    def parse_md_video_script(self, filename):
        if not self.resolution:
            self.resolution='1920x1080'
        self.xres, self.yres=map(int, self.resolution.split('x'))
        file=None
        self.globals['md_context']=[]
        self.globals['md_filters']=None
        self.globals['md_clip']=None
        self.globals['md_count']=0
        self.globals['md_join']=False
        try:
            file=open(filename,"r")
        except:
            logger.critical(f"cannot open markdown: {filename}")
            return
        filetext='\n'.join(file.readlines())
        logger.info(f"Processing md script")
        md=self.markdown(filetext)
        xml=ET.Element('VideoScript')
        ET.SubElement(xml, 'Version').text='1'
        info=ET.SubElement(xml, 'Info')
        ET.SubElement(info, 'Title').text=f"{filename.split('.')[0]}"
        ET.SubElement(info, 'SubTitle')
        ET.SubElement(info, 'Genre')
        ET.SubElement(info, 'Author')
        ET.SubElement(info, 'Description')
        ET.SubElement(info, 'Date')
        ET.SubElement(info, 'Time')
        defaults=ET.SubElement(xml, 'Defaults')
        ET.SubElement(defaults, 'BackgroundColor').text='#000'
        ET.SubElement(defaults, 'BackgroundMusic').text='bgm.mp3'
        ET.SubElement(defaults, 'LoopBGM').text='true'
        ET.SubElement(defaults, 'BackgroundVolume').text='5%'
        ET.SubElement(defaults, 'TranstionType').text='fade'
        ET.SubElement(defaults, 'TransitionTime').text='0.5'
        ET.SubElement(defaults, 'Resolution').text=f'{self.resolution or "1920x1080"}'
        ET.SubElement(defaults, 'FrameRate').text='25'
        clips=ET.SubElement(xml, 'Clips')
        self.handle_md_children(clips, md)
        xml_str=ET.tostring(xml, encoding='utf-8')
        outfn=f'{os.path.splitext(filename)[0]}.{self.resolution}.xml'
        with open(outfn, 'w') as xml_file:
            xml_file.write(minidom.parseString(xml_str).toprettyxml(indent='    '))
        return outfn

    def parse_xml_video_script(self, filename):
        tree = ET.parse(filename)
        root = tree.getroot()
        self.rename={}
        clips = []

        # Retrieve Video Info
        info = root.find("Info")
        info_dict = {}
        if info is not None:
            for child in info:
                info_dict[child.tag] = child.text

        # Retrieve global defaults
        global_defaults = root.find("Defaults")
        global_defaults_dict = {}
        parent_map = {c: p for p in root.iter() for c in p}
        if global_defaults is not None:
            for child in global_defaults:
                global_defaults_dict[child.tag] = child.text
        if not self.resolution:
            self.resolution=global_defaults_dict.get ('Resolution') or '1920x1080'

        self.fps=info_dict.get('FrameRate') or 25
        self.resolution=self.resolution.lower()
        self.xres, self.yres=map(int, self.resolution.split('x'))
        # Retrieve all clips in the script
        all_clips = root.findall(".//Clip")
        for clip_element in all_clips:
            clip_dict = global_defaults_dict.copy()
            # Check if the clip is within a chapter
            parent = parent_map[clip_element]
            if parent.tag == "Chapter":
                chapter_defaults = parent.find("Defaults")
                if chapter_defaults is not None:
                    for child in chapter_defaults:
                        clip_dict[child.tag] = child.text

            # Override defaults with clip-specific settings
            clip_defaults = clip_element.find("Properties")
            if clip_defaults is not None:
                for child in clip_defaults:
                    clip_dict[child.tag] = child.text

            # Add Media
            media_elements = clip_element.findall(".//Media")
            media_list = []
            for media_element in media_elements:
                media_dict = {"MediaType": media_element.get("type")}
                if media_dict.get("MediaType") == "TTS":
                    if not media_dict.get('FilePath') or media_dict.get('FilePath')=="":
                        media_dict['FilePath']=self.generate_temp_filename(media_element.get('Script'))+".wav"

                for child in media_element:
                    media_dict[child.tag] = child.text
                    if child.tag=='filters':
                        filters=[]
                        for filter in child:
                            f={}
                            f['type']=filter.attrib['type']
                            for prop in filter:
                                f[prop.tag]=prop.text
                            filters.append(f)
                        media_dict[child.tag]=filters
                media_list.append(media_dict)
            clip_dict["Media"] = media_list

            # Add clip filename metadata
            clip_dict['FilePath'] = clip_element.find('FilePath').text
            if not clip_dict.get('FilePath'):
                clip_dict["FilePath"] = self.generate_temp_filename() + ".mp4"

            clips.append(clip_dict)
        self.clips=clips
        return clips, global_defaults_dict, info_dict

    def fix_durations(self, clips):
        totalDuration=0
        for clip in clips:
            passes=0
            clipLength=0.0
            while passes<2:
                for media in clip['Media']:
                    if not media.get('Duration'):
                        media['Duration']=-1
                    if not media.get('StartTime'):
                        media['StartTime']=0
                    if float(media['StartTime'])==-1.0:
                        media['StartTime']=round(clipLength, 3)
                    if float(media['Duration'])==-1.0:
                        if media['MediaType']=='Image' or media['MediaType'] == 'TextOverlay':
                            if passes>0:
                                media['Duration']=round(clipLength-float(media['StartTime']), 3)
                        else:
                            if media.get('FilePath'):
                                media['Duration']=round(self.get_file_duration(self.work_dir+'/'+media['FilePath']),3)
                                logger.debug(f'Setting media Duration '+str(media['Duration']))
                                clipLength=round(max(float(media['StartTime'])+float(media['Duration']), clipLength),3)
                    else:
                        clipLength=round(max(float(media['StartTime'])+float(media['Duration']), clipLength), 3)
                    filters=media.get('filters')
                    if filters:
                        for f in filters:
                            st=float(f.get('StartTime') or 0)
                            d=float(f.get('Duration') or 0)
                            if st==-1.0:
                                st=clipLength
                            if d==-1.0:
                                d=totalDuration-clipLength
                            #f['StartTime']=st
                            #f['Duration']=d
                            #clipLength=max(st+d, float(clipLength))

                passes=passes+1
                clip['Duration']=round(clipLength, 3)
                clip['StartTime']=0#totalDuration
                #clip['Resolution']=self.resolution
                totalDuration+=round(clipLength, 3)
            #TODO check filter durations too

            logger.debug(f'Setting clip Duration '+str(clip['Duration']))
        pass

    def fix_placement(self, media):
        o_w, o_h=map(int, self.resolution.split('x'))
        w,h=o_w,o_h
        x,y = 0,0
        rot = 0.0
        pad=0.05
        PiP_scale=0.5
        w_pad=pad*o_w
        h_pad=pad*o_h
        fill={}
        pos_type=''
        if(media):
            if media.get("FilePath"):
                i_w, i_h=self.get_file_resolution(f'{self.work_dir}/{media.get("FilePath")}')
                if i_w>0 and i_h>0:
                    h=o_h
                    w=i_w/i_h*o_h
                    if w>o_w:
                        fill['width']=int(w)
                        fill['height']=int(h)
                        w=o_w
                        h=i_h/i_w*o_w
                    else:
                        fill['width']=o_w
                        fill['height']=int(i_h/i_w*o_w)
                    fill['x'],fill['y']=int((o_w/2)-(fill['width']/2)), int((o_h/2)-(fill['height']/2))
                    if media.get('Position'):
                        pos_type=media['Position']
                        if pos_type.lower()=="stretch":
                            x, y, w, h=0, 0, o_w, o_h
                        if pos_type.lower()=="aspect":

                            x,y=(o_w-w)/2, (o_h-h)/2
                        if pos_type.lower()=="fill":
                            w, h, x, y=fill['width'],fill['height'], fill['x'], fill['y']
                            fill=None
                        if pos_type.lower()=="topleft":
                            w=w*PiP_scale-h_pad
                            h=h*PiP_scale-h_pad
                            x=h_pad
                            y=h_pad
                        if pos_type.lower()=="topright":
                            w=w*PiP_scale-h_pad
                            h=h*PiP_scale-h_pad
                            x=o_w-h_pad-w
                            y=h_pad
                        if pos_type.lower()=="bottomleft":
                            w=w*PiP_scale-h_pad
                            h=h*PiP_scale-h_pad
                            x=h_pad
                            y=o_h-h_pad-h
                        if pos_type.lower()=="bottomright":
                            w=w*PiP_scale-h_pad
                            h=h*PiP_scale-h_pad
                            x=o_w-h_pad-w
                            y=o_h-h_pad-h
        if pos_type.lower()!='aspect':
            fill=None
        return { "x":int(x), "y":int(y), "width":int(w), "height":int(h), "rotation":rot, 'fill':fill, 'pos':pos_type }

    def check_missing_media(self, clips):
        """ also check for background audio file from global, chapter, clip """
        missing=0
        for clip in clips:
            full_script=""
            clip['Position']=self.fix_placement(None)
            media_list = clip.get("Media", [])
            for media in media_list:
                if self.update_type(f'{self.work_dir}/{media.get("FilePath")}'):
                    media['FilePath'] = os.path.basename(self.update_type(f'{self.work_dir}/{media.get("FilePath")}'))
                file_path = media.get("FilePath")
                media_type = media.get("MediaType")
                if media_type.lower()=='image':
                    if os.path.splitext(file_path)[1].lower() in video_types:
                        media['Volume']="0%" #FIXME this isn't working
                media["Position"]=self.fix_placement(media)
                script = media.get('Script')
                if script and len(script)>0:
                    full_script+=(script or "")+'\n'
                description = media.get("Description")
                if media_type:
                    # Process missing media
                    if file_path and not self.file_exists(file_path):
                        missing+=self.get_missing_file(media_type, self.work_dir+'/'+file_path, description, script)
                        if self.update_type(f'{self.work_dir}/{media.get("FilePath")}'): #TODO restructure, eliminate dup
                            media['FilePath'] = os.path.basename(self.update_type(f'{self.work_dir}/{media.get("FilePath")}'))
                        file_path = media.get("FilePath")
            clip['Script']=full_script
        self.fix_durations(clips)
        return missing

    def add_missing_streams(self, input_file):
        if self.file_exists(input_file):
            temp_output_file = self.work_dir+'/'+'temp_output.mp4'
            # Run FFprobe to get the stream information
            ffprobe_cmd = ['ffprobe', '-v', 'quiet', '-show_streams', '-print_format', 'json', input_file]
            result = self.execute_command(ffprobe_cmd)
            ffprobe_output=result.output
            # Parse the FFprobe output
            ffprobe_data = json.loads(ffprobe_output)
            streams=0
            if ffprobe_data.get('streams'):
                streams = ffprobe_data['streams']
            else:
                logger.critical(f'{input_file} has no streams!')
                return

            # Check if audio and video streams exist
            audio_stream_exists = any(stream['codec_type'] == 'audio' for stream in streams)
            video_stream_exists = any(stream['codec_type'] == 'video' for stream in streams)

            # Prepare FFmpeg command with conditional options
            ffmpeg_cmd = ['ffmpeg', '-i', input_file]
            acodec='copy'
            vcodec='copy'
            if not audio_stream_exists:
                logger.info(f'Adding a blank audio stream to {input_file}.')
                acodec='mp3'
                ffmpeg_cmd.extend(['-f', 'lavfi', '-i', 'anullsrc'])
            if not video_stream_exists:
                logger.info(f'Adding a blank video stream to {input_file}.')
                vcodec='h264'
                ffmpeg_cmd.extend(['-f', 'lavfi', '-i', f'color=c=black:s={self.resolution}'])

            ffmpeg_cmd.extend(['-c:v', f'{vcodec}', '-c:a', f'{acodec}', '-map', '0', '-map', '1', '-shortest', temp_output_file])
            if acodec!='copy' or vcodec!='copy':
                # Run FFmpeg to add missing streams
                self.execute_command(ffmpeg_cmd)

                # Rename the temporary output file to the original file name
                os.remove(input_file)
                shutil.move(temp_output_file, input_file)
        else:
            logger.critical(f'{input_file} does not exist and cannot recover.')

    def generate_clip(self, clip):
        """
        Generates a video clip based on the provided XML clip data,
        handling the positioning and timing of media elements within the clip.
        """
        command = ['ffmpeg']
        filter_graph={"v":[], "a":[]}
        inputs={"v":[], "a":[]}
        v_output_num=0
        a_output_num=0
        # Add background color input
        stream_num=0
        if not self.resolution:
            self.resolution='1920x1080'
        self.xres, self.yres=map(int, self.resolution.split('x'))
        command.extend(['-f', 'lavfi', '-i', f'color={self.translate_color(clip["BackgroundColor"])}:size={self.resolution}:duration={clip["Duration"]}'])
        inputs['v'].append(f"{stream_num}:v")

        #Add blank Audio (set the format)
        stream_num+=1
        command.extend(['-f', 'lavfi', '-i', f'anullsrc=channel_layout=stereo:sample_rate=44100:duration={clip["Duration"]}'])
        inputs['a'].append(f"{stream_num}:a")

        def swap(list):
            list[-1], list[-2] = list[-2], list[-1]

        def vid_graph(inputs, media):
            graph = []
            nonlocal v_output_num
            duration=clip['Duration']
            #scale=width:height[v]
            if media['Position'].get('fill'):
                mediastream=str(inputs['v'].pop())
                inputs['v'].append(mediastream)
                if isImage(media['FilePath']):
                    output=f"v{v_output_num}"
                    graph.append(f"[{str(inputs['v'].pop())}]"\
                            "zoompan="\
                            f"'min(zoom+0.0005,1.5)':"\
                            f"d={int(duration*self.fps)}:"\
                            f"fps={self.fps}:"\
                            f"x='iw/2-(iw/zoom/2)':"\
                            f"y='ih/2-(ih/zoom/2)'"\
                            f"[{output}]")
                    inputs['v'].append(output)
                    v_output_num+=1

                output=f"v{v_output_num}"
                graph.append(f"[{str(inputs['v'].pop())}]"\
                        "eq="\
                        f"brightness=-0.25"\
                        f"[{output}]")
                inputs['v'].append(output)
                v_output_num+=1

                output=f"v{v_output_num}"
                graph.append(f"[{str(inputs['v'].pop())}]"\
                        "boxblur=5:1"\
                        f"[{output}]")
                inputs['v'].append(output)
                v_output_num+=1

                output=f"v{v_output_num}"
                graph.append(f"[{str(inputs['v'].pop())}]"\
                        "scale="\
                        f"{str(media['Position']['fill']['width'])}:"\
                        f"{str(media['Position']['fill']['height'])}"\
                        f"[{output}]")
                inputs['v'].append(output)
                v_output_num+=1
                output=f"v{v_output_num}"

                swap(inputs['v'])
                if media['StartTime']==-1:
                    media['StartTime']=0.0
                graph.append(f"[{str(inputs['v'].pop())}]"\
                        f"[{str(inputs['v'].pop())}]"\
                        "overlay="\
                        f"x={str(media['Position']['fill']['x'])}:"\
                        f"y={str(media['Position']['fill']['y'])}:"\
                        f"enable='between(t,{str(media['StartTime'])},{str(media['Duration'])})'"\
                        f"[{output}]")
                inputs['v'].append(output)
                inputs['v'].append(mediastream)
                v_output_num+=1

            #zoompan
            output=f"v{v_output_num}"
            #if media['MediaType'].lower()=='image': #FIXME
            if isImage(media['FilePath']):
                graph.append(f"[{str(inputs['v'].pop())}]"\
                        "zoompan="\
                        f"'min(zoom+0.0005,1.5)':"\
                        f"d={int(duration*self.fps)}:"\
                        f"fps={self.fps}:"\
                        f"x='iw/2-(iw/zoom/2)':"\
                        f"y='ih/2-(ih/zoom/2)'"\
                        f"[{output}]")
                inputs['v'].append(output)
                v_output_num+=1

            output=f"v{v_output_num}"
            graph.append(f"[{str(inputs['v'].pop())}]"\
                    "scale="\
                    f"{str(media['Position']['width'])}:"\
                    f"{str(media['Position']['height'])}"\
                    f"[{output}]")
            inputs['v'].append(output)
            v_output_num+=1

            output=f"v{v_output_num}"
            swap(inputs['v'])
            graph.append(f"[{str(inputs['v'].pop())}]"\
                    f"[{str(inputs['v'].pop())}]"\
                    "overlay="\
                    f"x={str(media['Position']['x'])}:"\
                    f"y={str(media['Position']['y'])}:"\
                    f"enable='between(t,{media['StartTime']},{media['Duration']})'"\
                    f"[{output}]")
            inputs['v'].append(output)
            v_output_num+=1

            #handle filter
            filters=media.get('filters') or []
            output=f"v{v_output_num}"
            filter_text=[]
            for f in filters:
                if f['type'].lower()=='drawtext':
                    #apply vidoeo filters
                    st=f.get('StartTime') or media['StartTime']
                    d=f.get('Duration') or media['Duration']
                    if float(d)==-1.0:
                        d=duration
                    fontsize=float(f.get('FontSize') or 1)*(self.xres/40)
                    boxcolor=f.get('BoxColor')
                    if boxcolor:
                        boxcolor=f'box=1:boxcolor={boxcolor}:boxborderw=5:'
                    else:
                        boxcolor=""
                    drawtext_str=(f.get('Text') or 'Lorem Ipsum').replace(':', '\\:')
                    filter_text.append(f"{f.get('type')}="\
                            f"text='{drawtext_str}':"\
                            f"fontsize={fontsize}:"\
                            f"fontfile={f.get('FontFile') or 'Arial'}:"\
                            f"borderw={f.get('BorderWidth') or 1}:"\
                            f"fontcolor={self.translate_color(f.get('FontColor'))}:"\
                            f"x={f.get('X') or '(w-tw)/2'}:"\
                            f"y={f.get('Y') or '(h-th)/2'}:"\
                            f"enable='between(t,{st},{d})':"\
                            f"alpha={f.get('Alpha') or 1.0}:"\
                            f'{boxcolor}'\
                            f"bordercolor={self.translate_color(f.get('BorderColor'))}")
                else:
                    logger.warning(f"Unknown filter: {f['type']}")
            if(len(filter_text)>0):
                graph.append(f"[{inputs['v'].pop()}]{','.join(filter_text)}[{output}]")
                inputs['v'].append(output)
                v_output_num+=1
            return ';'.join(graph)

        def aud_graph(inputs, media):
            graph=[]
            nonlocal a_output_num
            adelay=float(media.get('StartTime') or 0.0)
            volume=float(self.pct_to_float(media.get('Volume')))
            #print(f'Volume={volume}  ({media.get("Volume") or "None"}) ')
            output=f"a{a_output_num}"
            graph.append(f"[{str(inputs['a'].pop())}]"\
                    f"adelay=delays={int(adelay*1000)}:all=1,"\
                    f"volume={volume}"\
                    f"[{output}]")
            inputs['a'].append(output)
            a_output_num+=1
            return ';'.join(graph)

        # Add media inputs and generate filter_graph data
        for media in clip['Media']:
            media_type = media['MediaType']
            if media_type in [ 'Video', 'Image' ]:
                if isImage(media['FilePath']):
                    command.extend([
                        "-loop", "1",
                    ])
                command.extend([
                    "-i", self.work_dir+'/'+media["FilePath"],
                ])
                hasaudio=self.has_audio(f"{self.work_dir}/{media['FilePath']}")
                stream_num+=1
                inputs['v'].append(f"{stream_num}:v")
                if hasaudio:
                    inputs['a'].append(f"{stream_num}:a")
                filter_graph['v'].append(vid_graph(inputs, media))
                if hasaudio:
                    filter_graph['a'].append(aud_graph(inputs, media))
            elif media_type in [ 'Audio', "TTS" ]:
                command.extend([
                    "-i", self.work_dir+'/'+media["FilePath"],
                ])
                stream_num+=1
                inputs['a'].append(f"{stream_num}:a")
                filter_graph['a'].append(aud_graph(inputs, media))
            else:
                # Log a warning for unknown media type
                logger.warning(f"Warning: Unknown media type encountered in clip: {media}")
        #amix the sources in filter_graph['a']
        amix=''
        output=f"a{a_output_num}"
        for inp in inputs['a']:
            amix+=f'[{inp}]'
        amix+=f'amix=inputs={len(inputs["a"])}:duration=longest[{output}]'
        inputs['a'].append(output)
        a_output_num+=1
        filter_graph['a'].append(amix)

        #generate the full filter graph
        v_s= ";".join(filter_graph['v'])
        a_s= ";".join(filter_graph['a'])

        if v_s !="" and a_s!="":
            filter_graph_str=';'.join([v_s, a_s])
        else:
            filter_graph_str=f"{v_s}{a_s}"

        command.extend(['-filter_complex', filter_graph_str])
        if v_s!="":
            command.extend(['-map', f'[{str(inputs["v"].pop())}]'])
        if a_s!="":
            command.extend(['-map', f'[{str(inputs["a"].pop())}]'])
        command.extend(['-c:v', 'h264',
            '-c:a', 'mp3',
            '-y',
            '-t', str(round(clip['Duration'], 3)),
            self.work_dir+'/'+clip['FilePath']
        ])
        if not self.file_exists( self.work_dir+'/'+clip['FilePath']):
            self.execute_command(command)
            self.add_missing_streams(self.work_dir+'/'+clip['FilePath'])

    def generate_srt(self, clips, filename):
        #FIXME times are wrong
        """
        Creates a subtitle track for the video based on the durations of the clips
        and saves it to the output file.
        """
        with open(filename, 'w') as f:
            count = 1
            for clip in clips:
                start_time = self.format_time(clip['StartTime'])
                end_time = self.format_time(float(clip['StartTime']) + float(clip['Duration']))
                subtitle = clip['Script']
                if len(subtitle)>0:
                    f.write(str(count) + '\n')
                    f.write(str(start_time) + ' --> ' + str(end_time) + '\n')
                    f.write(subtitle + '\n')
                    count += 1
            f.close()

    def join_clips(self, clips, background_audio_file, sub_file, output_file):
        #FIXME this is not right yet-- add transitions
        command = ['ffmpeg']
        #command.extend(['-framerate', self.fps])
        with open(f'{self.work_dir}/clips.list', 'w') as f:
            for clip in clips:
                f.write(f"file '{clip['FilePath']}'\n")
            f.close()
        command.extend(['-f', 'concat'])
        command.extend(['-i', f'{self.work_dir}/clips.list'])
        command.extend(['-y'])
        command.extend(['-c:v', 'copy'])
        command.extend(['-c:a', 'mp3'])
        command.extend([f'nobgm_{output_file}'])
        self.execute_command(command)

        stream=0
        filter_graph=""
        time=0.0
        command=['ffmpeg']
        command.extend(['-i', 'nobgm_'+output_file])
        time=self.get_file_duration(f'nobgm_{output_file}')
        if sub_file:
            stream+=1
            command.extend(['-i', sub_file])
        vmap='0:v'
        amap='0:a'
        if background_audio_file:
            stream+=1
            loop=True   #TODO read from xml
            music_volume=0.1 #TODO read from xml
            if (loop):
                command.extend(['-stream_loop', '-1'])
            command.extend(['-i', self.work_dir+'/'+background_audio_file])
            filter_graph+=f'[v:0]null[vv]'
            vmap='vv'
            filter_graph+=f';[{stream}]volume={music_volume}[bgm]'
            filter_graph+=f';[{amap}][bgm]amerge=inputs=2[am]'
            amap='am'
        if len(filter_graph):
            command.extend(['-filter_complex', filter_graph])
            command.extend(['-map', f'[{vmap}]'])
            command.extend(['-map', f'[{amap}]'])
        command.extend(['-y'])
        command.extend(['-t', f'{time}'])
        command.extend(['-c:v', 'h264'])
        command.extend(['-c:a', 'mp3'])
        command.extend(['-pix_fmt', 'yuv420p'])
        #command.extend(['fps', f'{self.fps}'])
        command.extend([output_file])
        # Execute the command and capture the output
        self.execute_command(command)

    def read_config_file(self, config_file_path):
        """Reads a config file into a dict of dicts.
        Args:
          config_file_path: The path to the config file.
        Returns:
          A dict of dicts, where the outer keys are the section names and the inner
          keys are the key-value pairs in the config file.
        """
        config = configparser.ConfigParser()
        config.read(config_file_path)
        config_dict = {}
        for section in config.sections():
            config_dict[section] = {}
            for option, value in config.items(section):
                config_dict[section][option] = value
        return config_dict

    def merge_dict_configs(self, defaults, read):
        """Merges two dict configs.
        Args:
            defaults: The default config dict.
            read: The read config dict.
        Returns:
            A merged config dict.
        """
        merged_config = {}
        for section in defaults:
            merged_config[section] = defaults[section].copy()
            if section in read:
                merged_config[section].update(read[section])
        return merged_config

    def write_config_dict(config_dict, config_file_path):
        """Writes a config dict back to the config file.
        Args:
            config_dict: The config dict to write.
            config_file_path: The path to the config file.
        """
        config = configparser.ConfigParser()
        for section, options in config_dict.items():
            config.add_section(section)
            for option, value in options.items():
                config.set(section, option, value)
        with open(config_file_path, "w") as f:
            config.write(f)

    def create(self, check_only):
        self.buffer="\x1b[0m\x1b[2J"
        config_file=os.path.expanduser("~/.pyVidMaker.conf")
        default_config={
                'apikeys':{
                    'pexels':'',
                    'pixabay':''},
                'defaults':{
                    'resolution':'1920x1080'}
                }

        self.full_refresh()
        read=self.read_config_file(config_file)
        self.config=self.merge_dict_configs(default_config, read)
        if read != self.config:
            self.write_config_dict(self.config, config_file)
        self.si=SearchImages(self.config, logger)
        xml_file=None
        if self.ext.lower()==".md":
            xml_file = self.parse_md_video_script(self.script_file)
        elif self.ext.lower()=='.xml':
            clips, defaults, info = self.parse_xml_video_script(self.script_file)
            if info.get('Title'):
                self.basefn0=info.get('Title')
                self.work_dir = self.basefn0+'.work'
            missing=self.check_missing_media(clips)
            if(missing):
                logger.error(f'There are {missing} missing media files.')
            else:
                logger.info(f'Found all media files.')
                if not check_only:
                    for clip in clips:
                        self.generate_clip(clip)
                    self.generate_srt(clips, self.sub_file)
                    self.output_file=f'{self.basefn0}.{self.resolution}.mp4'
                    self.join_clips(clips, defaults.get("BackgroundMusic"), self.sub_file, self.output_file)
        else:
            logger.critical(f"Unknown script type: {self.ext.lower()}")
        return xml_file

def main():
    parser=OptionParser(usage="usage: %prog [options] xmlVideoScript.xml")
    parser.add_option("-c", "--check", action='store_true', dest="check", default=False,
            help="Don't render, only check the XML and find missing media.")
    parser.add_option("-v", "--verbose", dest="debug", default="info",
            help="Show debug messages.[debug, info, warning]")
    parser.add_option("-r", "--resolution", dest="resolution", default=False,
            help="Set render resolution.")

    (options, args)=parser.parse_args()
    if len(args)==0:
        parser.print_help()
        return
    morefiles=[]
    global logger
    logger=pyteLogger()
    script_file = args[0]
    if options.resolution:
        for rez in options.resolution.split(','):
            vm=VidMaker(script_file, rez.lower(), options.debug)
            logger=pyteLogger(vm)
            morefiles.append(vm.create(options.check))
        for x in morefiles:
            if type(x)==str:
                logger.info(f'{x} has been written.')
                vm=VidMaker(x, False, options.debug)
                vm.create(options.check)
    else:
        vm=VidMaker(script_file, False, options.debug)
        logger=pyteLogger(vm)
        more=vm.create(options.check)
        if type(more)==str:
            logger.info(f'{more} has been written.')
            vm=VidMaker(more, False, options.debug)
            vm.create(options.check)

if __name__ == "__main__":
    main()

