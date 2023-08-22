#!/usr/bin/python3
import os, hashlib, subprocess, logging, colorlog, datetime, glob, shutil, io
import requests, json, mistune, urllib.parse, xml.etree.ElementTree as ET
import string, xml.dom.minidom as minidom, pyte
from bs4 import BeautifulSoup
from pprint import pprint
from optparse import OptionParser
from gtts import gTTS
from imageSelect import imageSelect
from urllib.parse import quote_plus
from SearchImages import SearchImages

import nltk
from nltk import pos_tag, word_tokenize
from nltk.corpus import stopwords

# Download necessary NLTK resources (only needed once)
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('stopwords')

pexels_API_KEY = "JMdcZ8E4lrykP2QSaZHNxuXKlJRRjmmlvBQRvgu5CrHnSI30BF7mGLI7"
pixabay_API_KEY = "38036450-c3aaf7be223f4d01b66e68cae"

class VidMaker:
    def __init__(self, script_file):
        self.script_file=script_file
        basefn,self.ext= os.path.splitext(script_file)
        # Output video file
        self.output_file =basefn+".mp4"
        # Log file
        self.log_file = basefn+".log"
        # Set up logging
        self.work_dir = basefn+'.work'
        os.makedirs(self.work_dir, exist_ok=True)
        os.makedirs('search', exist_ok=True)
        self.sub_file = self.work_dir+'/'+basefn+".srt"
        self.setup_logging()
        self.markdown=mistune.create_markdown(renderer=None)

    def setup_logging(self):
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

        # Create a file handler for the log file
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setFormatter(log_formatter)

        # Create a stream handler for stderr
        stderr_handler = logging.StreamHandler()
        stderr_handler.setLevel(logging.DEBUG)
        stderr_handler.setFormatter(stderr_formatter)

        # Configure the root logger with the handlers
        logging.root.handlers = [file_handler, stderr_handler]
        logging.root.setLevel(logging.DEBUG)

    def filter_text(self, text):
        # Tokenize the text
        tokens = word_tokenize(text)

        # Perform part-of-speech tagging
        pos_tags = pos_tag(tokens)

        # Filter out nouns, verbs, and adjectives
        allowed_tags = ['NN', 'NNS', 'NNP', 'NNPS']
        #allowed_tags = ['NN', 'NNS', 'NNP', 'NNPS', 'VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ', 'JJ', 'JJR', 'JJS']
        filtered_words = [word for word, tag in pos_tags if tag in allowed_tags]

        # Eliminate duplicates
        filtered_words = list(set(filtered_words))

        return filtered_words

    def pct_to_float(self, percentage_str):
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

    def translate_color(self, color):
        if len(color) == 4 and color.startswith("#"):  # Handle 3-character color code
            r = color[1]
            g = color[2]
            b = color[3]
            return f"#{r}{r}{g}{g}{b}{b}"
        else:
            return color  # Return the color code as is if not in the expected format

    def format_time(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return "{:02d}:{:02d}:{:02d},{:03d}".format(hours, minutes, seconds, milliseconds)

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
                #logging.debug(line.rstrip('\n'))
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

    def search_images(self, search_query, num_images, output_directory):
        self.si.search_images_pexels(search_query, num_images, output_directory)
        #self.si.search_images_google(search_query, num_images, output_directory)
        #self.si.search_images_bing(search_query, num_images, output_directory)
        self.si.search_images_pixabay(search_query, num_images, output_directory)

    def generate_tts_audio_buffer(self, audio_buffer_file, text_content):
        """
        Generates a TTS audio buffer using GTTS from the provided text content
        and saves it to the specified audio buffer file.
        """
        if not self.file_exists(audio_buffer_file):
            tts = gTTS(text=text_content)
            #tts.speed=(7.0/8.0)
            tts.save(audio_buffer_file)

    def dir_exists(self, file_path):
        """
        Checks if a file exists at the given file path.
        Returns True if it exists, False otherwise.
        """
        if file_path is not None:
            return os.path.isdir(file_path)
        return False

    def file_exists(self, file_path):
        """
        Checks if a file exists at the given file path.
        Returns True if it exists, False otherwise.
        """
        if file_path is not None:
            return os.path.isfile(file_path)
        return False

    def get_missing_file(self, type, file_path, description, script):
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
                    imgs=imageSelect()
                    imgs.interface(file_path, glob.glob(f'{search_dir}/*'), description[:40])
                    self.setup_logging()
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

    def handle_md_children(self, xml, md, context=None, level=0):
        if not context:
            context=[]
        context_items=len(context)
        for e in md:
            tp=e['type']
            ch=e.get("children")
            if tp=="heading":
                self.generate_md_heading(xml, e, context)
                pass
            elif tp=="list":
                self.generate_md_list(xml, e, context)
                pass
            elif tp=="list_item":
                self.generate_md_list_item(xml, e, context)
                pass
            elif tp=="paragraph":
                self.generate_md_paragraph(xml, e, context)
                pass
            elif tp=="blank_line":
                self.generate_md_blank_line(xml, e, context)
                pass
            elif tp=="text":
                self.generate_md_text(xml, e, context)
                pass
            elif tp=="strong":
                self.generate_md_strong(xml, e, context)
                pass
            else:
                logging.warning(f'Unhandled md data: {tp}')
            if ch: 
                self.handle_md_children(xml, ch, context, level+1)
        while len(context)>context_items:
            context.pop()
        pass

    def generate_md_heading(self, xml, md, context):
        context.append('heading')

    def generate_md_list(self, xml, md, context):
        pass

    def generate_md_paragraph(self, xml, md, context):
        pass

    def generate_md_blank_line(self, xml, md, context):
        pass

    def generate_md_list_item(self, xml, md, context):
        context.append('list')

    def generate_md_text(self, xml, md, context):
        clip=ET.SubElement(xml, 'Clip')
        properties=ET.SubElement(clip, 'Properties')
        #TODO     create clip with media:
        #normal:  Video capable media, TTS
        #heading: add text overlay -- Title style
        #list:    add text overlay -- calculate position in a list style, keep text for duration of list
        #strong:  add text overlay -- calculate position keep for duration of text after the bold
        text=md.get('raw')
        tts_media=ET.SubElement(clip, 'Media')
        tts_media.set("type", "TTS")
        img_media=ET.SubElement(clip, 'Media')
        img_media.set('type', 'Image')
        if(text):
            ttsdelay=0.0
            ET.SubElement(img_media, 'Description').text=text#f'{" ".join(self.filter_text(text))}'
            ET.SubElement(img_media, 'FilePath').text=f'{self.generate_temp_filename(text)}.png'
            ET.SubElement(img_media, 'StartTime').text=f'0.0'
            ET.SubElement(img_media, 'Duration').text=f'-1'
            ET.SubElement(img_media, 'Position').text=f'Aspect'
            filters=ET.SubElement(img_media, 'filters')
            if('list' in context or 'strong' in context or 'heading' in context):
                size=48
                if 'heading' in context:
                    size=48*3
                ttsdelay=0.0
                drawtext=ET.SubElement(filters, 'filter')
                drawtext.set('type', 'drawtext')
                ET.SubElement(drawtext, 'Text').text=f"{text}"
                ET.SubElement(drawtext, 'StartTime').text=f'0'
                ET.SubElement(drawtext, 'Duration').text=f'-1'
                ET.SubElement(drawtext, 'FontSize').text=f'size'
                ET.SubElement(drawtext, 'FontColor').text=f'#FFF'
                ET.SubElement(drawtext, 'FontFile').text=f'font.ttf'
                ET.SubElement(drawtext, 'BorderColor').text=f'#000'
                ET.SubElement(drawtext, 'BorderWidth').text=f'5'
                ET.SubElement(drawtext, 'X').text='(w-text_w)/2'
                ET.SubElement(drawtext, 'Y').text='(h-text_h)/2'
            ET.SubElement(tts_media, 'Script').text=f'{text}'
            ET.SubElement(tts_media, 'FilePath').text=f'{self.generate_temp_filename(text)}.wav'
            ET.SubElement(tts_media, 'StartTime').text=f'{ttsdelay}'
            ET.SubElement(tts_media, 'Duration').text=f'-1'
            ET.SubElement(tts_media, 'UseForCC').text=f'True'
            ET.SubElement(tts_media, 'Volume').text=f'100%'


            #TODO add drawtext filter for contexts
            #TODO handle contexts
        else:
            logging,warning('Missing "raw" text')#TODO get a better warning
        if len(context)>0:
            context.pop()
        pass

    def generate_md_strong(self, xml, md, context=[]):
        context.append('strong')

    def parse_md_video_script(self, filename):
        file=None
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
        ET.SubElement(info, 'Title')
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
        ET.SubElement(defaults, 'Resolution').text='1920x1080'
        clips=ET.SubElement(xml, 'Clips')
        self.handle_md_children(clips, md)
        xml_str=ET.tostring(xml, encoding='utf-8')
        with open(f'{os.path.splitext(filename)[0]}.xml', 'w') as xml_file:
            xml_file.write(minidom.parseString(xml_str).toprettyxml(indent='    '))

    def parse_xml_video_script(self, filename):
        tree = ET.parse(filename)
        root = tree.getroot()
        
        clips = []
        
        # Retrieve global defaults
        global_defaults = root.find("Defaults")
        global_defaults_dict = {}
        parent_map = {c: p for p in root.iter() for c in p}
        if global_defaults is not None:
            for child in global_defaults:
                global_defaults_dict[child.tag] = child.text
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
        return clips, global_defaults_dict

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
                passes=passes+1
                clip['Duration']=clipLength
                clip['StartTime']=totalDuration
                #clip['Resolution']='1920x1080'
                totalDuration+=clipLength
            logging.debug(f'Setting clip Duration '+str(clip['Duration']))
        pass

    def fix_placement(self, media):
        o_w, o_h=1920, 1080
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
            i_w, i_h=self.get_file_resolution(self.work_dir+'/'+media.get('FilePath'))
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
                media["Position"]=self.fix_placement(media)
                media_type = media.get("MediaType")
                file_path = media.get("FilePath")
                buffer_file = media.get("BufferFile")
                script = media.get('Script')
                if script and len(script)>0:
                    full_script+=(script or "")+'\n'
                description = media.get("Description")
                if media_type:
                    # Process missing media
                    if file_path and not self.file_exists(file_path):
                        missing+=self.get_missing_file(media_type, self.work_dir+'/'+file_path, description, script)
                    if buffer_file and not self.file_exists(buffer_file):
                        missing+=self.get_missing_file(media_type, self.work_dir+'/'+buffer_file, description, script)
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
                ffmpeg_cmd.extend(['-f', 'lavfi', '-i', 'color=c=black:s=1920x1080'])

            ffmpeg_cmd.extend(['-c:v', f'{vcodec}', '-c:a', f'{acodec}', '-map', '0', '-map', '1', '-shortest', temp_output_file])
            if acodec!='copy' or vcodec!='copy':
                # Run FFmpeg to add missing streams
                self.execute_command(ffmpeg_cmd)

                # Rename the temporary output file to the original file name
                os.remove(input_file)
                shutil.move(temp_output_file, input_file)

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
        command.extend(['-f', 'lavfi', '-i', f'color={self.translate_color(clip["BackgroundColor"])}:size=1920x1080:duration={clip["Duration"]}'])
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
            duration=clip['Duration']+0.1
            fps=25
 
            #scale=width:height[v] 
            if media['Position'].get('fill'): 
                mediastream=str(inputs['v'].pop())
                inputs['v'].append(mediastream)
                if media['MediaType'].lower()=='image': 
                    output=f"v{v_output_num}"
                    graph.append(f"[{str(inputs['v'].pop())}]"\
                            "zoompan="\
                            f"'min(zoom+0.0005,1.5)':"\
                            f"d={int(duration*fps)}:"\
                            f"fps={fps}:"\
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
            #"""
            #zoompan 
            output=f"v{v_output_num}"

            if media['MediaType'].lower()=='image': #FIXME
                graph.append(f"[{str(inputs['v'].pop())}]"\
                        "zoompan="\
                        f"'min(zoom+0.0005,1.5)':"\
                        f"d={int(duration*fps)}:"\
                        f"fps={fps}:"\
                        f"x='iw/2-(iw/zoom/2)':"\
                        f"y='ih/2-(ih/zoom/2)'"\
                        f"[{output}]")
                inputs['v'].append(output)
                v_output_num+=1

            #scale=width:height[v] 
            output=f"v{v_output_num}"
            graph.append(f"[{str(inputs['v'].pop())}]"\
                    "scale="\
                    f"{str(media['Position']['width'])}:"\
                    f"{str(media['Position']['height'])}"\
                    f"[{output}]")
            inputs['v'].append(output)
            v_output_num+=1

            filters=media.get('filters') or []
            for f in filters:
                if f['type'].lower()=='drawtext':
                    #apply video filters
                    output=f"v{v_output_num}"
                    graph.append(f"[{str(inputs['v'].pop())}]"\
                            f"{f.get('type')}="\
                            f"text={(f.get('Text') or 'Lorem Ipsum').replace(':', '')}:"\
                            f"fontsize={f.get('FontSize') or 24}:"\
                            f"fontfile={f.get('FontFile') or 'Arial'}:"\
                            f"borderw={f.get('BorderWidth') or 1}:"\
                            f"fontcolor={self.translate_color(f.get('FontColor'))}:"\
                            f"x={f.get('X') or 0}:"\
                            f"y={f.get('Y') or 0}:"\
                            #f"t={f.get('StartTime') or 0}:"\
                            #f"duration={f.get('Duration') or media['Duration']}:"\
                            f"alpha={f.get('Alpha') or 1.0}:"\
                            f"bordercolor={self.translate_color(f.get('BorderColor'))}"\
                            f"[{output}]")
                    inputs['v'].append(output)
                    v_output_num+=1
                else:
                    logging.warning(f"Unknown filter: {f['type']}")
            #overlay filter
            output=f"v{v_output_num}"
            swap(inputs['v'])
            graph.append(f"[{str(inputs['v'].pop())}]"\
                    f"[{str(inputs['v'].pop())}]"\
                    "overlay="\
                    f"x={str(media['Position']['x'])}:"\
                    f"y={str(media['Position']['y'])}:"\
                    f"enable='between(t,{str(media['StartTime'])},{str(media['Duration'])})'"\
                    f"[{output}]")
            inputs['v'].append(output)
            v_output_num+=1

            return ';'.join(graph)

        def aud_graph(inputs, media): 
            graph=[]
            nonlocal a_output_num
            
            #volume filter
            volume=float(self.pct_to_float(media.get('Volume') or 100.0))
            output=f"a{a_output_num}"
            graph.append(f"[{str(inputs['a'].pop())}]"\
                    f"volume={volume}"\
                    f"[{output}]")
            inputs['a'].append(output)
            a_output_num+=1
            
            #amix filter
            swap(inputs['a'])
            output=f"a{a_output_num}"
            graph.append(f"[{str(inputs['a'].pop())}]"\
                    f"[{str(inputs['a'].pop())}]"\
                    "amix"\
                    f"[{output}]")
            inputs['a'].append(output)
            a_output_num+=1

            return ';'.join(graph)

        # Add media inputs and generate filter_graph data
        for media in clip['Media']:
            media_type = media['MediaType']
            if media_type == 'Video':
                command.extend([
                    "-i", self.work_dir+'/'+media["FilePath"],
                ])
                hasaudio=has_audio(self.work_dir+'/'+media['FilePath'])
                stream_num+=1
                inputs['v'].append(f"{stream_num}:v")
                if hasaudio:
                    inputs['a'].append(f"{stream_num}:a")
                filter_graph['v'].append(vid_graph(inputs, media))
                if hasaudio:
                    filter_graph['a'].append(aud_graph(inputs, media))

            elif media_type == 'Image':
                command.extend([
                    "-loop", "1",
                    "-i", self.work_dir+'/'+media["FilePath"],
                ])
                stream_num+=1
                inputs['v'].append(f"{stream_num}:v")
                filter_graph['v'].append(vid_graph(inputs, media))
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
        #FIXME this is not right yet
        """
        ffmpeg\
            -i temp_20230801231344616581.mp4\
            -i temp_20230801231344616624.mp4\
            -i temp_20230801231344616640.mp4\
            -i temp_20230801231344616650.mp4\
            -stream_loop -1 -i music.mp3\
            -i domestication.srt\
            -filter_complex\
            "[0:v][1:v]xfade=transition=fade:duration=1:offset=0.5[v01];\
            [1:v][2:v]xfade=transition=fade:duration=1:offset=0.5[v12];\
            [2:v][3:v]xfade=transition=fade:duration=1:offset=0.5[v23];\
            [0:v][v01][v12][v23]concat=n=4:v=1:a=0[vv];\
            [0:a][1:a][2:a][3:a]concat=n=4:v=0:a=1[aa];\
            [4:a]volume=0.05[bgm];\
            [aa][bgm]amix[am]"\
                -map "[vv]" -map "[am]" -y -t 60 
                -c:v h264 -c:a aac -pix_fmt yuv420p domestication.mp4
        """
        #enforce a maximum stream count for the join
        command = ['ffmpeg']
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
        command.extend([output_file])

        # Execute the command and capture the output
        self.execute_command(command)
    
    def create(self):
        self.si=SearchImages(pexels_API_KEY, pixabay_API_KEY, logging)
        if self.ext.lower()==".md":
            xml_file = self.parse_md_video_script(f"{self.script_file}")
        elif self.ext.lower()=='.xml':
            clips, defaults = self.parse_xml_video_script(f"{self.script_file}")
            missing=self.check_missing_media(clips)
            if(missing):
                logging.error(f'There are {missing} missing media files.')
            else:
                for clip in clips: 
                    self.generate_clip(clip)
                self.generate_srt(clips, self.sub_file)
                self.join_clips(clips, defaults.get("BackgroundMusic"), self.sub_file, self.output_file)
        else:
            logging.error(f"Unknown script type: {ext.lower()}")

def main():
    parser=OptionParser(usage="usage: %prog [options] xmlVideoScript.xml")
    parser.add_option("-c", "--check", dest="check", default=False,
            help="Don't render, only check the XML and find missing media.")
    parser.add_option("-d", "--debug", dest="debug", default=False,
            help="Show debug messages.")
    (options, args)=parser.parse_args()
    if len(args)==0:
        parser.print_help()
        return
    script_file = args[0]
    vm=VidMaker(script_file)
    vm.create()

if __name__ == "__main__":
    main()

