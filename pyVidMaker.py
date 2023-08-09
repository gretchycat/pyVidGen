#!/usr/bin/python3
import os, hashlib, subprocess, logging, colorlog, datetime, glob, shutil
import requests, json, mistune, urllib.parse, xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from pprint import pprint
from optparse import OptionParser
from gtts import gTTS
from imageSelect import imageSelect
from urllib.parse import quote_plus
from SearchImages import SearchImages

pexels_API_KEY = "JMdcZ8E4lrykP2QSaZHNxuXKlJRRjmmlvBQRvgu5CrHnSI30BF7mGLI7"
pixabay_API_KEY = "38036450-c3aaf7be223f4d01b66e68cae"

class VidMaker:
    def __init__(self, script_file):
        self.script_file=script_file
        basefn,self.ext= os.path.splitext(script_file)
        # Output video file
        self.output_file =basefn+".mp4"
        # Log file
        log_file = basefn+".log"
        # Set up logging
        self.sub_file = basefn+".srt"
        self.setup_logging(log_file)
        self.markdown=mistune.create_markdown(renderer=None)

    def setup_logging(self, log_file):
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
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(log_formatter)

        # Create a stream handler for stderr
        stderr_handler = logging.StreamHandler()
        stderr_handler.setLevel(logging.DEBUG)
        stderr_handler.setFormatter(stderr_formatter)

        # Configure the root logger with the handlers
        logging.root.handlers = [file_handler, stderr_handler]
        logging.root.setLevel(logging.DEBUG)

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
        sekf.si.search_images_pixabay(search_query, num_images, output_directory)

    def generate_tts_audio_buffer(self, audio_buffer_file, text_content):
        """
        Generates a TTS audio buffer using GTTS from the provided text content
        and saves it to the specified audio buffer file.
        """
        if not self.file_exists(audio_buffer_file):
            tts = gTTS(text=text_content)
            tts.save(audio_buffer_file)

    def file_exists(self, file_path):
        """
        Checks if a file exists at the given file path.
        Returns True if it exists, False otherwise.
        """
        if file_path is not None:
            return os.path.isfile(file_path)
        return False

    def get_missing_file(self, type, file_path, description, script, si):
        if file_path:
            log=logging.info
            verb="Acquiring"
            log(f"{verb} {type}: {file_path}\n\tDescription: {description}\n\tScript: {script}")
            if type=="TTS": 
                verb="Generated"
                self.generate_tts_audio_buffer(file_path, script)
            elif type=="Image":
                verb="Found"
                shutil.rmtree('image_temp', ignore_errors=True)
                self,search_images(description, 20, 'image_temp', si)
                imgs=imageSelect()
                imgs.interface(file_path, glob.glob('image_temp/*'), description)
                shutil.rmtree('image_temp', ignore_errors=True)
            missing=0 if self.file_exists(file_path) else 1
            if missing>0:
                verb="Missing"
                log=logging.warning
            log(f"{verb} {type}: {file_path}")
            return missing
        return 0

    def generate_temp_filename(self, fnkey=None):
        if(fnkey):
            return "temp_"+hashlib.md5(fnkey).hexdigest()    
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
        #TODO     Video capable media, TTS
        #heading: add text overlay -- Title style
        #list:    add text overlay -- calculate position in a list style, keep text for duration of list
        #strong:  add text overlay -- calculate position keep for duration of text after the bold
        text=md.get('raw')
        if(text):
            #TODO handle contexts
            if len(context)>0:
                print(", ".join(context))
                print("*"*8)
            print(text)
            print('-'*80)
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
        xml=None #TODO generate header
        self.handle_md_children(xml, md)

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
                                media['Duration']=self.get_file_duration(media['FilePath'])
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
            i_w, i_h=self.get_file_resolution(media.get('FilePath'))
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

    def check_missing_media(self, clips, si):
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
                    if not self.file_exists(file_path):
                        missing+=self.get_missing_file(media_type, file_path, description, script, si)
                    if not self.file_exists(buffer_file):
                        missing+=self.get_missing_file(media_type, buffer_file, description, script, si)
            clip['Script']=full_script
        self.fix_durations(clips)
        return missing

    def add_missing_streams(self, input_file):
        if self.file_exists(input_file):
            temp_output_file = 'temp_output.mp4'    
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
            #"""
            #scale=width:height[v] 
            if media['Position'].get('fill'): 
                mediastream=str(inputs['v'].pop())
                inputs['v'].append(mediastream)
                duration=clip['Duration']+0.1
                fps=25
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
                            f"text={f.get('Text') or 'Lorem Ipsum'}:"\
                            f"fontsize={f.get('FontSize') or 24}:"\
                            f"fontfile={f.get('FontFile') or 'Arial'}:"\
                            f"borderw={f.get('BorderWidth') or 1}:"\
                            f"fontcolor={translate_color(f.get('FontColor'))}:"\
                            f"x={f.get('X') or 0}:"\
                            f"y={f.get('Y') or 0}:"\
                            #f"t={f.get('StartTime') or 0}:"\
                            #f"duration={f.get('Duration') or media['Duration']}:"\
                            f"alpha={f.get('Alpha') or 1.0}:"\
                            f"bordercolor={translate_color(f.get('BorderColor'))}"\
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
            volume=float(media.get('Volume') or 100.0)/100.0
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
                    "-i", media["FilePath"],
                ])
                hasaudio=has_audio(media['FilePath'])
                stream_num+=1
                inputs['v'].append(f"{stream_num}:v")
                if hasaudio:
                    inputs['a'].append(f"{stream_num}:a")
                #print("i"*80)
                #print(media['FilePath'])
                #pprint(inputs)
                filter_graph['v'].append(vid_graph(inputs, media))
                if hasaudio:
                    filter_graph['a'].append(aud_graph(inputs, media))

            elif media_type == 'Image':
                command.extend([
                    "-loop", "1",
                    "-i", media["FilePath"],
                ])
                stream_num+=1
                inputs['v'].append(f"{stream_num}:v")
                #print("i"*80)
                #print(media['FilePath'])
                #pprint(inputs)
                filter_graph['v'].append(vid_graph(inputs, media))
            elif media_type in [ 'Audio', "TTS" ]:
                command.extend([
                    "-i", media["FilePath"],
                ])
                stream_num+=1
                inputs['a'].append(f"{stream_num}:a")
                #print("i"*80)
                #print(media['FilePath'])
                #pprint(inputs)
                filter_graph['a'].append(aud_graph(inputs, media))
            else:
                # Log a warning for unknown media type
                logging.warning(f"Warning: Unknown media type encountered in clip: {media}")
        #pprint(filter_graph)

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
            clip['ClipFileName']
        ])
        self.execute_command(command)
        self.add_missing_streams(clip['ClipFileName'])

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
        command = ['ffmpeg']
        stream=0
        filter_graph_vid=""
        filter_graph_aud=""
        time=0.0
        for clip in clips:
            command.extend(['-i', clip['ClipFileName']])
            filter_graph_vid+=f'[{stream}:v]'
            filter_graph_aud+=f'[{stream}:a]'
            stream+=1
            time+=clip['Duration']
        amap='aa'
        if(stream>0):#use xfade filter for transitions
            filter_graph_vid+=f'concat=n={stream}:v=1:a=0[vv]'
            filter_graph_aud+=f'concat=n={stream}:v=0:a=1[aa]'
        if background_audio_file:
            loop=True
            music_volume=0.05
            if (loop):
                command.extend(['-stream_loop', '-1'])
            command.extend(['-i', background_audio_file])
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
        command.append(output_file)

        # Execute the command and capture the output
        self.execute_command(command)
    
    def create(self):
        si=SearchImages(pexels_API_KEY, pixabay_API_KEY, logging)
        if self.ext.lower()==".md":
            xml_file = self.parse_md_video_script(f"{self.script_file}")
        elif self.ext.lower()=='.xml':
            clips, defaults = self.parse_xml_video_script(f"{self.script_file}")
            missing=self.check_missing_media(clips, si)
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

