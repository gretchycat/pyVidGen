import os, hashlib, subprocess, logging, colorlog, pprint, datetime, glob
import shutil, requests, json
from bs4 import BeautifulSoup
import urllib.parse
import xml.etree.ElementTree as ET
from optparse import OptionParser
from gtts import gTTS
from imageSelect import imageSelect
from urllib.parse import quote_plus

# Set up logging
#logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
pexels_API_KEY = "JMdcZ8E4lrykP2QSaZHNxuXKlJRRjmmlvBQRvgu5CrHnSI30BF7mGLI7"
pixabay_API_KEY = "38036450-c3aaf7be223f4d01b66e68cae"

def setup_logging(log_file):
    # Create a formatter with color
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

def translate_color(color):
    if len(color) == 4 and color.startswith("#"):  # Handle 3-character color code
        r = color[1]
        g = color[2]
        b = color[3]
        return f"#{r}{r}{g}{g}{b}{b}"
    else:
        return color  # Return the color code as is if not in the expected format

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return "{:02d}:{:02d}:{:02d},{:03d}".format(hours, minutes, seconds, milliseconds)

def execute_command(command):
    """
    Executes a command in the system and logs the command line and output.
    """
    try:
        output=""
        sepw=60
        logging.info('-'*sepw)
        logging.info(f"Executing command: {' '.join(command)}")
        logging.info('-'*sepw)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        for line in process.stdout:
            logging.debug(line.rstrip('\n'))
            output+=line
        process.wait()
        process.output=output
        if(process.returncode>0):
            logging.error(f"Error executing command.") 
        logging.debug('-'*sepw)
        return process
    except Exception as e:
        logging.error(f"Error executing command: {e}")
        logging.error('-'*sepw)

def search_images(search_query, num_images, output_directory):
    search_images_pexels(search_query, num_images, output_directory)
    search_images_pixabay(search_query, num_images, output_directory)
    #search_images_google(search_query, num_images, output_directory)
    #search_images_bing(search_query, num_images, output_directory)

def search_images_pexels(query, num_images, output_directory):
    base_url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": pexels_API_KEY}
    params = {"query": query, "per_page": num_images}

    response = requests.get(base_url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        photos = data.get("photos", [])

        if not photos:
            print("No images found.")
            return

        # Create output directory if it doesn't exist
        os.makedirs(output_directory, exist_ok=True)

        # Download and save images
        for photo in photos:
            image_url = photo["src"]["original"]
            image_id = photo["id"]
            image_extension = image_url.split(".")[-1]
            image_filename = f"pexels_{image_id}.{image_extension}"
            image_path = os.path.join(output_directory, image_filename)

            response = requests.get(image_url)
            if response.status_code == 200:
                with open(image_path, "wb") as file:
                    file.write(response.content)
                print(f"Downloaded image: {image_filename}")
            else:
                print(f"Error downloading image {image_filename}. Status code: {response.status_code}")

        print(f"{num_images} images downloaded to {output_directory}")
    else:
        print(f"Error occurred while searching images. Status code: {response.status_code}")

def search_images_pixabay(query, num_images, output_directory):
    base_url = "https://pixabay.com/api/"
    params = {
        "key": pixabay_API_KEY,
        "q": query,
        "per_page": num_images
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        data = response.json()
        images = data.get("hits", [])
        if not images:
            print("No images found.")
            return
        # Create output directory if it doesn't exist
        os.makedirs(output_directory, exist_ok=True)
        # Download and save images
        for i, image in enumerate(images):
            image_url = image["largeImageURL"]
            image_id = image["id"]
            image_extension = image_url.split(".")[-1]
            image_filename = f"pixabay_{image_id}.{image_extension}"
            image_path = os.path.join(output_directory, image_filename)
            response = requests.get(image_url)
            if response.status_code == 200:
                with open(image_path, "wb") as file:
                    file.write(response.content)
                print(f"Downloaded image {i+1}/{num_images}: {image_filename}")
            else:
                print(f"Error downloading image {i+1}/{num_images}. Status code: {response.status_code}")
        print(f"{num_images} images downloaded to {output_directory}")
    else:
        print(f"Error occurred while searching images. Status code: {response.status_code}")

def search_images_bing(search_query, num_images, output_directory):
    search_query_encoded = quote_plus(search_query)
    url = f"https://www.bing.com/images/search?q={search_query_encoded}"

    # Send a GET request to Bing Images
    response = requests.get(url)

    # Create BeautifulSoup object
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find all image elements
    image_elements = soup.find_all('img')

    # Create output directory if it doesn't exist
    os.makedirs(output_directory, exist_ok=True)

    # Download and save images
    count = 0
    for image in image_elements:
        if count >= num_images:
            break

        if 'src' in image.attrs:
            image_url = image['src']
            try:
                response = requests.get(image_url)
                image_path = os.path.join(output_directory, f"bing_image{count}.jpg")
                with open(image_path, 'wb') as file:
                    file.write(response.content)
                count += 1
            except Exception as e:
                logging.warning(f"Error downloading image: {e}")

    logging.info(f"Downloaded {count} images to {output_directory}")

def search_images_google(search_query, num_images, output_directory):
    search_query_encoded = quote_plus(search_query)
    url = f"https://www.google.com/search?q={search_query_encoded}&tbm=isch"
    # Send a GET request to Google Images
    response = requests.get(url)
    # Create BeautifulSoup object
    soup = BeautifulSoup(response.content, 'html.parser')
    # Find all image elements
    image_elements = soup.find_all('img')
    # Create output directory if it doesn't exist
    os.makedirs(output_directory, exist_ok=True)
    # Download and save full-resolution images
    count = 0
    for image in image_elements:
        if count >= num_images:
            break
        if 'src' in image.attrs:
            image_url = image['src']
        elif 'data-src' in image.attrs:
            image_url = image['data-src']
        else:
            continue
        try:
            response = requests.get(image_url)
            image_path = os.path.join(output_directory, f"google_image{count}.jpg")
            with open(image_path, 'wb') as file:
                file.write(response.content)
            count += 1
        except Exception as e:
            logging.warning(f"Error downloading image: {e}")
    logging.info(f"Downloaded {count} images to {output_directory}")

def generate_tts_audio_buffer(audio_buffer_file, text_content):
    """
    Generates a TTS audio buffer using GTTS from the provided text content
    and saves it to the specified audio buffer file.
    """
    if not file_exists(audio_buffer_file):
        tts = gTTS(text=text_content)
        tts.save(audio_buffer_file)

def file_exists(file_path):
    """
    Checks if a file exists at the given file path.
    Returns True if it exists, False otherwise.
    """
    if file_path is not None:
        return os.path.isfile(file_path)
    return None

def get_missing_file(type, file_path, description, script):
    if file_path:
        log=logging.info
        verb="Acquiring"
        log(f"{verb} {type}: {file_path}\n\tDescription: {description}\n\tScript: {script}")
        if type=="TTS": 
            verb="Generated"
            generate_tts_audio_buffer(file_path, script)
        elif type=="Image":
            verb="Found"
            search_images(description, 20, 'image_temp')
            #print(';getting image')
            imgs=imageSelect()
            imgs.interface(file_path, glob.glob('image_temp/*'), description)
            shutil.rmtree('image_temp')
        missing=0 if file_exists(file_path) else 1
        if missing>0:
            verb="Missing"
            log=logging.warning
        log(f"{verb} {type}: {file_path}")
        return missing
    return 0

def generate_temp_filename(fnkey=None):
    if(fnkey):
        return "temp_"+hashlib.md5(fnkey).hexdigest()    
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    return f"temp_{timestamp}"

def get_file_duration(file_path):
    command = [
        'ffprobe',
        '-v',
        'error',
        '-show_entries',
        'format=duration',
        '-of',
        'json',
        file_path
    ]
    
    #print('\x1b[1;32m',end='')
    #pprint.pprint(command)
    output = subprocess.check_output(command).decode('utf-8')

    duration_data = json.loads(output)

    #print('\x1b[1;33m',end='')
    #pprint.pprint(output)
    #print('\x1b[0m',end='')
    duration = float(duration_data['format']['duration'])
    return duration

def parse_video_script(filename):
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
        clip_dict["ClipFileName"] = generate_temp_filename() + ".mp4"
        media_elements = clip_element.findall(".//Media")
        media_list = []
        for media_element in media_elements:
            media_dict = {"MediaType": media_element.get("type")}
            if media_dict.get("MediaType") == "TTS":
                if media_dict.get('FilePath')=="":
                    media_dict['FilePath']=generate_temp_filename()+".wav"

            for child in media_element:
                media_dict[child.tag] = child.text
            media_list.append(media_dict)

        clip_dict["Media"] = media_list
        clips.append(clip_dict)
    return clips, global_defaults_dict

def fix_durations(clips):
    totalDuration=0
    for clip in clips:
        passes=0
        clipLength=0.0
        while passes<2:
            for media in clip['Media']:
                #print('\x1b[1;31m',end='')
                #pprint.pprint(media)
                #print('\x1b[0m',end='')
                if not media.get('Duration'):
                    media['Duration']=-1
                if not media.get('StartTime'):
                    media['StartTime']=0
                if float(media['Duration'])==-1.0:
                    if media['MediaType']=='Image' or media['MediaType'] == 'TextOverlay':
                        if passes>0:
                            media['Duration']=clipLength-float(media['StartTime'])
                            logging.debug(f'Setting max Duration '+str(media['Duration']))
                    else:
                        if media.get('FilePath'):
                            media['Duration']=get_file_duration(media['FilePath'])
                            logging.debug(f'Setting media Duration '+str(media['Duration']))
                            clipLength=max(float(media['StartTime'])+float(media['Duration']), clipLength)
                else:
                    clipLength=max(float(media['StartTime'])+float(media['Duration']), clipLength)

            passes=passes+1
            clip['Duration']=clipLength
            clip['StartTime']=totalDuration
            clip['Resolution']='1920x1080'
            totalDuration+=clipLength
            logging.debug(f'Setting clip Duration '+str(clip['Duration']))
    pass

def fix_placement(media):
    defaultPosition = { "x":0, "y":0, "width":1920, "height":1080, "rotation":0.0 }
    return defaultPosition

def check_missing_media(clips):
    """ also check for background audio file from global, chapter, clip """
    missing=0
    for clip in clips:
        full_script=""
        clip['Position']=fix_placement(None)
        media_list = clip.get("Media", [])
        for media in media_list:
            media["Position"]=fix_placement(media)
            media_type = media.get("MediaType")
            file_path = media.get("FilePath")
            buffer_file = media.get("BufferFile")
            script = media.get('Script')
            if script and len(script)>0:
                full_script+=(script or "")+'\n'
            description = media.get("Description")
            if media_type:
                # Process missing media
                if not file_exists(file_path):
                    missing+=get_missing_file(media_type, file_path, description, script)
                if not file_exists(buffer_file):
                    missing+=get_missing_file(media_type, buffer_file, description, script)
        clip['Script']=full_script
    fix_durations(clips)
    return missing

def convert_file_format(input_file, output_file, output_format):
    """
    Converts a media file from one format to another using FFmpeg.
    """
    command = f"ffmpeg -i {input_file} -y {output_file}"
    execute_command(command)

def adjust_volume(input_file, output_file, volume_level):
    """
    Adjusts the volume level of an audio file using FFmpeg.
    """
    command = f"ffmpeg -i {input_file} -af 'volume={volume_level}' -y {output_file}"
    execute_command(command)

def add_missing_streams(input_file):
    if file_exists(input_file):
        temp_output_file = 'temp_output.mp4'    
        # Run FFprobe to get the stream information
        ffprobe_cmd = ['ffprobe', '-v', 'quiet', '-show_streams', '-print_format', 'json', input_file]
        result = execute_command(ffprobe_cmd)
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
            execute_command(ffmpeg_cmd)

            # Rename the temporary output file to the original file name
            os.remove(input_file)
            shutil.move(temp_output_file, input_file)

def generate_clip_lib(clip):
    # Create a list to store the input sources
    inputs = []

    # Add background color as input
    if 'BackgroundColor' in clip:
        background_color = translate_color(clip['BackgroundColor'])
        inputs.append(ffmpeg.filter('color=c={0}:s={1}:duration={2}:f=lavfi'.format(background_color, clip['Resolution'], clip['Duration'])))

    # Add other media types as input
    for media in clip['Media']:
        media_type = media['MediaType']
        file_path = media['FilePath']
        start_time = media['StartTime']
        duration = media['Duration']
        position = media['Position']
        volume = media.get('Volume', '100%')
        # Handle different media types
        if media_type == 'Video':
            inputs.append(ffmpeg.input(file_path, ss=start_time, t=duration).filter('scale',\
                    w=position['width'], h=position['height']).filter('setpts',\
                    'PTS-STARTPTS').filter('volume', volume))
        elif media_type == 'Image':
            inputs.append(ffmpeg.input(file_path, loop=1,\
                    t=duration, fr=clip['FrameRate']).filter('scale',\
                    w=position['width'], h=position['height']).filter('setpts',\
                    'PTS-STARTPTS').filter('volume', volume))
        elif media_type == 'Audio' or media_type=='TTS':
            inputs.append(ffmpeg.input(file_path, ss=start_time, t=duration).filter('volume', volume))
        elif media_type == 'TextOverlay':
            inputs.append(ffmpeg.input('aevalsrc=0', t=duration).filter('volume', volume).output(file_path,\
                    t=duration, vf="drawtext=text='{0}':fontsize={1}:fontcolor={2}:x={3}:y={4}".format(media['Text'], media['FontSize'],\
                    translate_color(media['FontColor']), position['x'], position['y'])))
    # Concatenate all the input sources
    output = ffmpeg.concat(*inputs, v=1, a=1).output(clip['ClipFileName'],\
            **{'c:v': 'libx264', 'c:a': 'aac', 'shortest': None,\
            'vf': 'pad={0}:padcolor=black'.format(clip['Resolution']),\
            'af': 'apad=pad_len=2*duration'})
    # Run the FFmpeg command
    ffmpeg.run(output, overwrite_output=True)
    add_missing_streams(file_path)

def generate_clip(clip):
    """
    Generates a video clip based on the provided XML clip data,
    handling the positioning and timing of media elements within the clip.

    ffmpeg 
        -f lavfi -i color=#000000:size=1920x1080:duration=23.0 
        -i video.mp4 
        -loop 1 -i image.jpg 
        -i audio.mp3 
        -i tts_audio1.wav 
        -filter_complex [0:v][1:v]overlay=x=0:y=0:enable='between(t,0,9.0)'[v0];
                        [v0][2:v]overlay=x=0:y=0:enable='between(t,2,6)';
                        [3:a][4:a]amix 
        -c:v h264 
        -c:a aac 
        -y 
        temp_20230716013512387103.mp4 
    """
    filter_graph=""
    command = ['ffmpeg']
    stream_num=0
    # Add background color input
    command.extend(['-f', 'lavfi', '-i', f'color={translate_color(clip["BackgroundColor"])}:size=1920x1080:duration={clip["Duration"]}'])
    filter_graph+=f"[{stream_num}:v]"

    # Add media inputs
    for media in clip['Media']:
        media_type = media['MediaType']
        def vid_graph(stream_num, media): 
            return f"[{str(stream_num)}:v]overlay="\
                    "x="+str(media['Position']['x'])+":"\
                    "y="+str(media['Position']['y'])+":"\
                    "enable='between(t,"+str(media['StartTime'])+","+str(media['Duration'])+")';"
        def aud_graph(stream_num, media):
            return f"[{str(stream_num)}:a]amix;"
        if media_type == 'Video':
            command.extend([
                "-i", media["FilePath"],
            ])
            stream_num+=1
            filter_graph+=vid_graph(stream_num, media)
        elif media_type == 'Image':
            command.extend([
                "-loop", "1",
                "-i", media["FilePath"],
            ])
            stream_num+=1
            filter_graph+=vid_graph(stream_num, media)
        elif media_type == 'Audio':
            command.extend([
                "-i", media["FilePath"],
            ])
            stream_num+=1
            filter_graph+=aud_graph(stream_num, media)
        elif media_type == 'TTS':
            command.extend([
                "-i", f"{media['FilePath']}",
            ])
            stream_num+=1
            filter_graph+=aud_graph(stream_num, media)
        elif media_type == 'TextOverlayX':
            command.extend([
                "-f", "lavfi",
                "-i", f"color=c=black:s={media['Position']['width']}x{media['Position']['height']}:r=25:d={media['Duration']}",
                "-vf", f"drawtext=text='{media['Text']}':fontsize={media['FontSize']}:fontcolor={translate_color(media['FontColor'])}:x={media['Position']['x']}:y={media['Position']['y']}",
            ])
            stream_num+=1
            filter_graph+=vid_graph(stream_num, media)
        elif media_type == 'Clips':
            # Ignore Clips media type for now (implementation details depend on handling nested clips)
            continue
        else:
            # Log a warning for unknown media type
            logging.warning(f"Warning: Unknown media type encountered in clip: {media}")
    # Add output filename
    command.extend([
        '-filter_complex', filter_graph,
        '-c:v', 'h264',
        '-c:a', 'aac',
        clip['ClipFileName']
    ])
    execute_command(command)
    add_missing_streams(clip['ClipFileName'])

def generate_srt(clips, filename):
    """
    Creates a subtitle track for the video based on the durations of the clips
    and saves it to the output file.
    """
    with open(filename, 'w') as f:
        count = 1
        for clip in clips:
            start_time = format_time(clip['StartTime'])
            end_time = format_time(float(clip['StartTime']) + float(clip['Duration']))
            subtitle = clip['Script']
            if len(subtitle)>0:
                f.write(str(count) + '\n')
                f.write(str(start_time) + ' --> ' + str(end_time) + '\n')
                f.write(subtitle + '\n')
                count += 1
        f.close()

def join_clips_basic(clips, background_audio_file, sub_file, output_file):
    """
    ffmpeg -f concat -i file.txt -c:v libx264  -pix_fmt yuv420p  -c:a aac output.mp4
    """
    with open('temp_inputs.txt', 'w') as file:
        for clip in clips:
            file.write(f'file {clip["ClipFileName"]}\n')
        file.close()

    command = ['ffmpeg']
    command.extend(['-f', 'concat','-i', 'temp_inputs.txt'])

    if background_audio_file:
        command.extend(['-i', background_audio_file])
    if sub_file:
        command.extend(['-i', sub_file])
    command.extend(['-y'])
    command.extend(['-c:v', 'h264'])
    command.extend(['-c:a', 'aac'])
    command.extend(['-pix_fmt', 'yuv420p'])
    command.append(output_file)

    # Execute the command and capture the output
    execute_command(command)

def join_clips(clips, background_audio_file, sub_file, output_file):
    command = ['ffmpeg']
    for clip in clips:
        command.extend(['-i', clip['ClipFileName']])
    if background_audio_file:
        command.extend(['-i', background_audio_file])
    if sub_file:
        command.extend(['-i', sub_file])
    """
    filter_graph = ''
    input_index = 0
    for i in range(len(clips)):
        filter_graph += '[{0}:v]setsar=1[v{0}];'.format(i)
        input_index += 1
    input_index = 0
    for i in range(len(clips)):
        filter_graph += '[v{0}]'.format(i)
        input_index += 1
    filter_graph += 'hstack=inputs={0}[v];'.format(len(clips))
    input_index = 0
    for i in range(len(clips)):
        filter_graph += '[{0}:a]'.format(i)
        input_index += 1
    filter_graph += 'amerge=inputs={0}[a]'.format(len(clips))

    command.extend(['-filter_complex', filter_graph])
    command.extend(['-map', '[v]'])
    command.extend(['-map', '[a]'])
    """
    command.extend(['-filter_complex', 'xfade=transition=fade:offset=0:duration=2,format=yuv420p'])
    command.extend(['-movflags', '+faststart'])
    command.extend(['-y'])
    command.extend(['-c:v', 'h264'])
    command.extend(['-c:a', 'aac'])
    command.extend(['-pix_fmt', 'yuv420p'])
    command.append(output_file)

    # Execute the command and capture the output
    execute_command(command)

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
    # Input XML file
    xml_file = args[0]
    basefn,ext= os.path.splitext(xml_file)
    # Output video file
    output_file =basefn+".mp4"
    # Log file
    log_file = basefn+".log"
    # Set up logging
    sub_file = basefn+".srt"
    setup_logging(log_file)
    #try:
    if True:
        clips, defaults = parse_video_script(xml_file)
        missing=check_missing_media(clips)
        if(missing):
            logging.error(f'There are {missing} missing media files.')
        else:
            for clip in clips: 
                generate_clip(clip)
            generate_srt(clips, sub_file)
            join_clips(clips, defaults.get("BackgroundMusic"), sub_file, output_file)

if __name__ == "__main__":
    main()



