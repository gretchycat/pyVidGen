import os, hashlib, subprocess, logging, pprint
import requests
from bs4 import BeautifulSoup
import urllib.parse
import xml.etree.ElementTree as ET
from optparse import OptionParser
from gtts import gTTS

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to search and download images from Google Images
def search_and_download_images(query, num_images, destination_dir):
    # Create the destination directory if it doesn't exist
    os.makedirs(destination_dir, exist_ok=True)

    # Prepare the search query and URL
    search_query = urllib.parse.quote(query)
    url = f"https://www.google.com/search?q={search_query}&tbm=isch"

    # Send a GET request to Google Images
    response = requests.get(url)

    # Parse the HTML response using BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all image elements on the page
    image_elements = soup.find_all('img')

    # Iterate over the specified number of images or until there are no more images available
    count = 0
    for img in image_elements:
        if count == num_images:
            break

        try:
            # Extract the image URL
            image_url = img['src']

            # Download the image and save it to the destination directory
            image_name = f"image{count+1}.jpg"  # You can modify the image name as desired
            image_path = os.path.join(destination_dir, image_name)
            urllib.request.urlretrieve(image_url, image_path)

            print(f"Downloaded {image_name}")

            # Increment the count of downloaded images
            count += 1
        except Exception as e:
            print(f"Error downloading image: {str(e)}")



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

def get_longest_media_duration(media_list):
    """
    Returns the duration of the longest piece of media with audio
    (video, audio, or TTS) from a list of media elements.
    """
    longest_duration = 0
    for media in media_list:
        if 'Duration' in media:
            duration = media['Duration']
            if duration > longest_duration:
                longest_duration = duration
        else:
            """Also get natural durations"""
            """set 'duration' to the natural duration"""
            pass
    return longest_duration

def generate_clip(xml_clip_data):
    """
    Generates a video clip based on the provided XML clip data,
    handling the positioning and timing of media elements within the clip.
    """
    # Implement clip generation logic based on XML data

def concatenate_clips(clips_list, background_audio_file, output_file):
    """
    Concatenates the video clips from a list into a final video,
    overlays the background audio, and saves it to the output file.
    """
    # Implement clip concatenation and background audio merging logic using FFmpeg

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
            for child in media_element:
                media_dict[child.tag] = child.text
            if media_dict.get("MediaType") == "TTS":
                if media_dict.get('FilePath')=="":
                    media_dict['FilePath']=generate_temp_filename()+".wav"
            media_list.append(media_dict)

        clip_dict["Media"] = media_list
        clips.append(clip_dict)
    return clips

def generate_temp_filename(fnkey=None):
    # Add your code to generate a unique temporary filename here
    # Example implementation: Use a timestamp-based filename
    import datetime
    if(fnkey):
        return "temp_"+hashlib.md5(fnkey).hexdigest()
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    return f"temp_{timestamp}"

def check_missing_media(clips):
    """ also check for background audio file from global, chapter, clip """
    missing=0
    for clip in clips:
        media_list = clip.get("Media", [])
        for media in media_list:
            media_type = media.get("MediaType")
            file_path = media.get("FilePath")
            buffer_file = media.get("BufferFile")
            script = media.get('Script')
            description = media.get("Description")
            if media_type:
                # Process missing media
                if not file_exists(file_path):
                    missing+=get_missing_file(media_type, file_path, description, script)
                if not file_exists(buffer_file):
                    missing+=get_missing_file(media_type, buffer_file, description, script)
    return missing

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
            search_and_download_images(description, 20, 'image_temp')
            print(';getting image')
            #imageSelect('imagetemp/*', file_path)
            #rm -rf image_temp
        missing=0 if file_exists(file_path) else 1
        if missing>0:
            verb="Missing"
            log=logging.warning
        log(f"{verb} {type}: {file_path}")
        return missing
    return 0

def create_subtitle_track(clips_list, output_file):
    """
    Creates a subtitle track for the video based on the durations of the clips
    and saves it to the output file.
    """
    # Implement subtitle track creation logic

def setup_logging(log_file):
    """
    Configures logging settings to record events, errors, and status messages.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename=log_file)

def execute_command(command):
    """
    Executes a command in the system and logs the command line and output.
    """
    try:
        logging.info(f"Executing command: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        logging.info(f"Command output: {result.stdout.strip()}")
        if result.stderr:
            logging.error(f"Command error: {result.stderr.strip()}")
    except Exception as e:
        logging.error(f"Error executing command: {e}")

def main():
    parser=OptionParser(usage="usage: %prog [options] xmlVideoScript.xml")
    parser.add_option("-c", "--check", dest="check", default=False,
            help="Don't render, only check the XML and find missing media.")
 
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
    setup_logging(log_file)

    try:
        clips = parse_video_script(xml_file)
        for clip in clips:
            pprint.pprint(clip)

        missing=check_missing_media(clips)
        if(missing):
            logging.error(f'There are {missing} missing media files.')
        else:
            pass
        # Parse the XML file
        #xml_data = parse_xml_file(xml_file)
        #print(ET.tostring(xml_data, encoding="unicode"))
        # Generate TTS audio buffers
#        for clip in xml_data['clips']:
#            for media in clip['media']:
#                if media['type'] == 'TTS':
#                    generate_tts_audio_buffer(media['content'], media['AudioBufferFile'])

        # Generate video clips
#        clips_list = []
#        for clip in xml_data['clips']:
#            generated_clip = generate_clip(clip)
#            clips_list.append(generated_clip)

        # Concatenate clips and merge background audio
#        concatenate_clips(clips_list, xml_data['BackgroundMusic'], output_file)

        # Create subtitle track
#        create_subtitle_track(clips_list, output_file)

            logging.info("Video generation completed successfully.")
    except Exception as e:
        logging.error(f"Error during video generation: {e}")

if __name__ == "__main__":
    main()



