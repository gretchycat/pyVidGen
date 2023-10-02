#!/usr/bin/python3
import os, hashlib, subprocess, logging, colorlog, datetime, glob, shutil, io
import sys, requests, json, mistune, urllib.parse, xml.etree.ElementTree as ET
import string, xml.dom.minidom as minidom, pyte, configparser, pydub
from bs4 import BeautifulSoup
from pprint import pprint
from optparse import OptionParser
from gtts import gTTS
from icat import imageSelect
from urllib.parse import quote_plus
from SearchImages import SearchImages

image_types=['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tif', '.tiff', '.pcx']
video_types=['.mp4', '.mkv', '.mpg', '.avi', '.asf', '.qt', '.mov']
audio_types=['.mp3', '.wav', '.ogg', '.flac', '.alac', '.mp2', ]

def pause():
    print ('[pause]')
    return sys.stdin.readline()

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

class VidMaker:
    def __init__(self, script_file, resolution, debug):
        self.globals={}
        self.script_file=script_file
        self.basefn0,self.ext= os.path.splitext(script_file)
        self.basefn0=f"{script_file.split('.')[0]}"
        if resolution:
            basefn=f"{self.basefn0}.{resolution}"
            self.resolution=resolution
            self.xres, self.yres=map(int, self.resolution.split('x'))
        else:
            basefn=self.basefn0
            self.resolution=False
        # Log file
        self.log_file = basefn+".log"
        # Set up logging
        self.debug=debug
        self.setup_logging(debug)
        self.work_dir = self.basefn0+'.work'
        os.makedirs(self.work_dir, exist_ok=True)
        os.makedirs('search', exist_ok=True)
        self.sub_file = self.work_dir+'/'+self.basefn0+".srt"
        self.markdown=mistune.create_markdown(renderer=None)

    def setup_logging(self, debug):
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
        stderr_handler = logging.StreamHandler()
        stderr_handler.setLevel(level)
        stderr_handler.setFormatter(stderr_formatter)

        # Configure the root logger with the handlers
        logging.root.handlers = [file_handler, stderr_handler]
        logging.root.setLevel(logging.DEBUG)

    def pct_to_float(self, percentage_str):
        if type(percentage_str) == str:
            if "%" in percentage_str:
                # Remove "%" sign and convert to float
                value = float(percentage_str.replace("%", ""))
            else:
                # Convert string to float
                value = float(percentage_str)

            if value >= 0 and value <= 1:
                return value
            elif value >= 5 and value <= 100:
                return value / 100
            else:
                raise ValueError("Percentage value is outside the valid range")
        return 100.0

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
            anim='/-\|'
            frame=0
            output=""
            sepw=60
            logging.info('-'*sepw)
            logging.info(f"Executing command: {' '.join(command)}")
            #logging.info('-'*sepw)
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            for line in process.stdout:
                logging.debug(line.rstrip('\n'))
                output+=line
                print(f'{anim[frame%len(anim)]}\x1b[1A')
                frame+=1
            process.wait()
            process.output=output
            if(process.returncode>0):
                logging.error(f"Error executing command.")
            #logging.debug('-'*sepw)
            return process
        except Exception as e:
            logging.error(f"Error executing command: {e}")

    def file_exists(self, file_path):
        """
        Checks if a file exists at the given file path.
        Returns True if it exists, False otherwise.
        """
        if file_path:
            if os.path.isfile(file_path):
                return True
        return False

    def search_images(self, search_query, num_images, output_directory):
        self.si.search_images_pexels(search_query, num_images, output_directory)
        #self.si.search_images_google(search_query, num_images, output_directory)
        #self.si.search_images_bing(search_query, num_images, output_directory)
        self.si.search_images_pixabay(search_query, num_images, output_directory)

    def generate_tts_audio_buffer(self, audio_buffer_file, text_content, voice='gtts', lang='en', tld='com.au', speed=1.0, pitch=1.0):
        """
        Generates a TTS audio buffer using GTTS from the provided text content
        and saves it to the specified audio buffer file.
        """
        #TODO Add Mozilla TTS and pyTTS
        if not self.file_exists(audio_buffer_file):
            if voice=='gtts':
                tts = gTTS(text_content, lang=lang, tld=tld, slow=False)
                # Adjust speed and pitch if necessary
                    # Modify the speech with pydub
                if speed != 1.0 or pitch != 1.0 and False:
                    audio = pydub.AudioSegment.from_mp3(io.BytesIO(tts.save_to_buffer(format="mp3").getvalue()))
                    if speed!=1.0:
                        pass
                        #audio = audio.speedup(playback_speed=speed).set_frame_rate(audio.frame_rate)
                    if pitch != 1.0:
                        pass
                        #audio = audio.set_frame_rate(int(audio.frame_rate * pitch))
                    # Export the modified audio to the specified file
                    audio.export(audio_buffer_file)
                else:
                    # Save the original audio to the specified file
                    tts.save(audio_buffer_file)
            else:
                tts = gTTS(text_content, lang=lang, tld=tld, slow=False)
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
                    print(f"Checking {name}{e}")
                    if os.path.isfile(f'{name}{e}'):
                        print(f"Found {name}{e}")
                        return f'{name}{e}'
            elif ext.lower() in audio_types:
                for e in audio_types:
                    if os.path.isfile(f'{name}{e}'):
                        return f'{name}{e}'
            if os.path.isfile(file_path):
                return file_path
        return False

    def get_missing_file(self, type, file_path, description, script):
        copied=""
        if file_path:
            log=logging.info
            verb="Acquiring"
            log(f"{verb} {type}: {file_path}\n\tDescription: {description}\n\tScript: {script}")
            if type=="TTS":
                verb="Generated"
                self.generate_tts_audio_buffer(file_path, script)
            elif type=="Image":
                verb="Found"
                while not self.file_exists(file_path):
                    print(f'\x1b[2J\x1b[1;1H\x1b[0;44;1m\x1b[0KPlease enter new search terms.\x1b[0m')
                    print(f'\x1b[0;1;97mScript: \x1b[0;44;93m"{script}"\x1b[0m')
                    desc=input(f'[\x1b[0;1m{description}\x1b[0m]\n: ')
                    if(desc!=''):
                        description=desc

                    search_dir=f'search/{desc.lower()}'[:24]
                    if not self.dir_exists(search_dir):
                        self.search_images(description, 20, search_dir)
                    #reset logging
                    for handler in logging.root.handlers[:]:
                        logging.root.removeHandler(handler)
                    imgs=imageSelect.imageSelect()
                    copied=imgs.interface(file_path, glob.glob(f'{search_dir}/*'), description[:40])
                    if copied != file_path:
                        self.rename[file_path]=copied
                        file_path=copied
                    self.setup_logging(self.debug)
                    #shutil.rmtree('image_temp', ignore_errors=True)
            missing=0 if self.file_exists(file_path) else 1
            if missing>0:
                verb="Missing"
                log=logging.warning
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
            #pprint(json_data)
            return json_data
        else:
            if(file_path):
                logging.error(f"Missing File: {file_path}")
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
        context_items=len(self.globals['md_context'])
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
                logging.warning(f'Unhandled md data: {tp}')
            print("  "*level+tp+ ' ' +str(list_created))
            if ch:
                self.handle_md_children(xml, ch, level+1)
            if list_created:
                self.globals['md_join']=False
                print("  "*level+"====")
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
        if not self.globals['md_clip']:
            self.globals['md_clip']=ET.SubElement(xml, 'Clip')
            self.globals['md_filters']=None
            properties=ET.SubElement(self.globals['md_clip'], 'Properties')
        #TODO     create clip with media:
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
        ET.SubElement(tts_media, 'FilePath').text=f'{self.generate_temp_filename(text)}.wav'
        ET.SubElement(tts_media, 'StartTime').text=f'{ttsdelay}'
        ET.SubElement(tts_media, 'Duration').text=f'-1'
        ET.SubElement(tts_media, 'UseForCC').text=f'True'
        ET.SubElement(tts_media, 'Volume').text=f'100%'
        if(text):
            if not self.globals['md_filters']:
                self.globals['md_filters']=ET.SubElement(img_media, 'filters')
            if(img_media):
                ET.SubElement(img_media, 'Description').text=text
                ET.SubElement(img_media, 'FilePath').text=f'{self.generate_temp_filename(text)}.png'
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
            logging,warning('Missing "raw" text')#TODO get a better warning
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
            logging.error(f"cannot open markdown: {filename}")
            return
        filetext='\n'.join(file.readlines())
        logging.info(f"Processing md script")
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

            # Add clip filename metadata
            clip_dict["ClipFileName"] = self.generate_temp_filename() + ".mp4"
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
                            #pprint(filter)
                            f={}
                            f['type']=filter.attrib['type']
                            for prop in filter:
                                f[prop.tag]=prop.text
                            filters.append(f)
                        media_dict[child.tag]=filters
                media_list.append(media_dict)
            clip_dict["Media"] = media_list
            clips.append(clip_dict)
        return clips, global_defaults_dict, info_dict

    def fix_durations(self, clips):
        totalDuration=0
        for clip in clips:
            passes=0
            clipLength=0.0
            while passes<2:
                for media in clip['Media']:
                    #print('\x1b[1;31m',end='')
                    #pprint(media)
                    #print('\x1b[0m',end='')
                    if not media.get('Duration'):
                        media['Duration']=-1
                    if not media.get('StartTime'):
                        media['StartTime']=0
                    if float(media['StartTime'])==-1.0:
                        media['StartTime']=clipLength
                    if float(media['Duration'])==-1.0:
                        if media['MediaType']=='Image' or media['MediaType'] == 'TextOverlay':
                            if passes>0:
                                media['Duration']=clipLength-float(media['StartTime'])
                        else:
                            if media.get('FilePath'):
                                media['Duration']=self.get_file_duration(self.work_dir+'/'+media['FilePath'])
                                logging.debug(f'Setting media Duration '+str(media['Duration']))
                                clipLength=max(float(media['StartTime'])+float(media['Duration']), clipLength)
                    else:
                        clipLength=max(float(media['StartTime'])+float(media['Duration']), clipLength)
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
                clip['Duration']=clipLength
                clip['StartTime']=0#totalDuration
                #clip['Resolution']=self.resolution
                totalDuration+=clipLength
            #TODO check filter durations too

            logging.debug(f'Setting clip Duration '+str(clip['Duration']))
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
                print(f'{media["FilePath"]}')
                media["Position"]=self.fix_placement(media)
                script = media.get('Script')
                if script and len(script)>0:
                    full_script+=(script or "")+'\n'
                description = media.get("Description")
                if media_type:
                    # Process missing media
                    if file_path and not self.file_exists(file_path):
                        missing+=self.get_missing_file(media_type, self.work_dir+'/'+file_path, description, script)
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
            streams = ffprobe_data['streams']

            # Check if audio and video streams exist
            audio_stream_exists = any(stream['codec_type'] == 'audio' for stream in streams)
            video_stream_exists = any(stream['codec_type'] == 'video' for stream in streams)

            # Prepare FFmpeg command with conditional options
            ffmpeg_cmd = ['ffmpeg', '-i', input_file]
            acodec='copy'
            vcodec='copy'
            if not audio_stream_exists:
                logging.info(f'Adding a blank audio stream to {input_file}.')
                acodec='aac'
                ffmpeg_cmd.extend(['-f', 'lavfi', '-i', 'anullsrc'])
            if not video_stream_exists:
                logging.info(f'Adding a blank video stream to {input_file}.')
                vcodec='h264'
                ffmpeg_cmd.extend(['-f', 'lavfi', '-i', f'color=c=black:s={self.resolution}'])

            ffmpeg_cmd.extend(['-c:v', f'{vcodec}', '-c:a', f'{acodec}', '-map', '0', '-map', '1', '-shortest', temp_output_file])
            if acodec!='copy' or vcodec!='copy':
                # Run FFmpeg to add missing streams
                self.execute_command(ffmpeg_cmd)

                # Rename the temporary output file to the original file name
                os.remove(input_file)
                shutil.move(temp_output_file, input_file)

    def process_renames(self, xmlfile):
        #FIXME maybe
        return False
        def find_elements_and_replace(element, tag_name, replacement_dict):
            if element.tag == tag_name:
                element_text = element.text
                if replacement_dict.get(element.text):
                    element.text = replacement_dict[element_text]
            for child in element:
                find_elements_and_replace(child, tag_name, replacement_dict)

        if len(self.rename)>0:
            logging.info(f'Renaming {len(self.rename)} media files in {xmlfile}')
            tree = ET.parse(xmlfile)
            root = tree.getroot()
            find_elements_and_replace(root, "FilePath", self.rename)
            xml_str=ET.tostring(root, encoding='utf-8')
            with open(xmlfile, 'w') as xml_file:
                xml_file.write(minidom.parseString(xml_str).toprettyxml(indent='    '))
            return True
        return False

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

        def isImage(filepath):
            return os.path.splitext(filepath)[1].lower() in [ '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.xcf' ]

        def vid_graph(inputs, media):
            graph = []
            nonlocal v_output_num
            duration=clip['Duration']
            #scale=width:height[v]
            if media['Position'].get('fill'):
                mediastream=str(inputs['v'].pop())
                inputs['v'].append(mediastream)
                if media['MediaType'].lower()=='image':
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
            if media['MediaType'].lower()=='image': #FIXME
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
                    logging.warning(f"Unknown filter: {f['type']}")
            if(len(filter_text)>0):
                graph.append(f"[{inputs['v'].pop()}]{','.join(filter_text)}[{output}]")
                inputs['v'].append(output)
                v_output_num+=1

            return ';'.join(graph)

        def aud_graph(inputs, media):
            graph=[]
            nonlocal a_output_num

            #adelay filter
            adelay=float(media.get('StartTime') or 0.0)
            volume=float(self.pct_to_float(media.get('Volume'))) or 100.0
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
                logging.warning(f"Warning: Unknown media type encountered in clip: {media}")
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
            '-c:a', 'aac',
            '-t', str(clip['Duration']),
            self.work_dir+'/'+clip['ClipFileName']
        ])
        if not self.file_exists( self.work_dir+'/'+clip['ClipFileName']):
            self.execute_command(command)
            self.add_missing_streams(self.work_dir+'/'+clip['ClipFileName'])

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
        stream=0
        filter_graph_vid=""
        filter_graph_aud=""
        time=0.0
        with open(f'{self.work_dir}/clips.list', 'w') as f:
            for clip in clips:
                f.write(f"file '{clip['ClipFileName']}'\n")
            f.close()
        command.extend(['-f', 'concat'])
        command.extend(['-i', f'{self.work_dir}/clips.list'])
        command.extend(['-y'])
        command.extend(['-c:v', 'copy'])
        command.extend(['-c:a', 'copy'])
        command.extend([f'nobgm_{output_file}'])
        self.execute_command(command)
        command=['ffmpeg']
        #return
        command.extend(['-i', 'nobgm_'+output_file])
        filter_graph_vid+=f'[{stream}:v]'
        filter_graph_aud+=f'[{stream}:a]'
        stream+=1
        time+=self.get_file_duration(f'nobgm_{output_file}')
        amap='aa'
        if(stream>0):#use xfade filter for transitions
            filter_graph_vid+=f'concat=n={stream}:v=1:a=0[vv]'
            filter_graph_aud+=f'concat=n={stream}:v=0:a=1[aa]'
        if background_audio_file:
            loop=True
            music_volume=0.05
            if (loop):
                command.extend(['-stream_loop', '-1'])
            command.extend(['-i', self.work_dir+'/'+background_audio_file])
            filter_graph_aud+=f';[{stream}:a]volume={music_volume}[bgm]'
            filter_graph_aud+=f';[aa][bgm]amix[am]'
            amap='am'
        if sub_file:
            command.extend(['-i', sub_file])
        command.extend(['-filter_complex', ';'.join([filter_graph_vid, filter_graph_aud])])
        command.extend(['-map', f'[vv]'])
        command.extend(['-map', f'[{amap}]'])
        command.extend(['-y'])
        command.extend(['-t', f'{time}'])
        command.extend(['-c:v', 'h264'])
        command.extend(['-c:a', 'aac'])
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
        config_file=os.path.expanduser("~/.pyVidMaker.conf")
        default_config={
                'apikeys':{
                    'pexels':'',
                    'pixabay':''},
                'defaults':{
                    'resolution':'1920x1080'}
                }
        read=self.read_config_file(config_file)
        self.config=self.merge_dict_configs(default_config, read)
        if read != self.config:
            self.write_config_dict(self.config, config_file)
        self.si=SearchImages(self.config, logging)
        xml_file=None
        if self.ext.lower()==".md":
            xml_file = self.parse_md_video_script(self.script_file)
        elif self.ext.lower()=='.xml':
            clips, defaults, info = self.parse_xml_video_script(self.script_file)
            if info.get('Title'):
                basefn=info.get('Title')
                self.basefn0=info.get('Title')
                self.work_dir = self.basefn0+'.work'
            missing=self.check_missing_media(clips)
            if self.process_renames(self.script_file):
                logging.info(f'Reloading {self.script_file} after media renames.')
                clips, defaults, info = self.parse_xml_video_script(self.script_file)
                missing=self.check_missing_media(clips)
            if(missing):
                logging.error(f'There are {missing} missing media files.')
            else:
                logging.info(f'Found all media files.')
                if not check_only:
                    for clip in clips:
                        self.generate_clip(clip)
                    self.generate_srt(clips, self.sub_file)
                    self.output_file=f'{self.basefn0}.{self.resolution}.mp4'
                    self.join_clips(clips, defaults.get("BackgroundMusic"), self.sub_file, self.output_file)
        else:
            logging.error(f"Unknown script type: {ext.lower()}")
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
    script_file = args[0]
    if options.resolution:
        for rez in options.resolution.split(','):
            vm=VidMaker(script_file, rez.lower(), options.debug)
            morefiles.append(vm.create(options.check))
        for x in morefiles:
            if type(x)==str:
                print(f'{x} has been written.')
                vm=VidMaker(x, False, options.debug)
                vm.create(options.check)
    else:
        vm=VidMaker(script_file, False, options.debug)
        more=vm.create(options.check)
        if type(more)==str:
            print(f'{more} has been written.')
            vm=VidMaker(more, False, options.debug)
            vm.create(options.check)

if __name__ == "__main__":
    main()

