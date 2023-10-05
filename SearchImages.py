import argparse
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import urllib.parse
import os

class SearchImages:
    def __init__(self, config, log):
        self.pexels_API_KEY=config['apikeys']['pexels']
        self.pixabay_API_KEY=config['apikeys']['pixabay']
        self.log=log

    def search_media_pexels(self, query, num_media, output_directory, media_type='video'):
        if media_type.lower()=='video':
            base_url = "https://api.pexels.com/videos/search"   #videos
        else:
            base_url = "https://api.pexels.com/v1/search"       #images
        headers = {"Authorization": self.pexels_API_KEY}
        params = {"query": query, "per_page": num_media}

        response = requests.get(base_url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            videos = data.get("videos", [])
            photos = data.get("photos", [])

            if not photos+photos:
                self.log.warning("No pexels media found.")
                return

            # Create output directory if it doesn't exist
            os.makedirs(output_directory, exist_ok=True)

            # Download and save media
            for media in photos+videos:
                media_url = media["src"]["original"]
                media_id = media["id"]
                media_extension = media_url.split(".")[-1].split('?')[0]
                media_filename = f"pexels_{media_id}.{media_extension}"
                media_path = os.path.join(output_directory, media_filename)

                response = requests.get(media_url)
                if response.status_code == 200:
                    with open(media_path, "wb") as file:
                        file.write(response.content)
                    self.log.info(f"Downloaded media {i+1}/{len(media)}: {media_filename}")
                else:
                    self.log.error(f"Error downloading media {i+1}/{len(media)} {media_filename}. Status code: {response.status_code}")

            self.log.info(f"{num_media} media downloaded to {output_directory}")
        else:
            self.log.error(f"Error occurred while searching media. Status code: {response.status_code}")

    def search_media_pixabay(self, query, num_media, output_directory, media_type='video'):
        if media_type.lower()=='video':
            base_url = "https://pixabay.com/api/videos/"    #videos
        else:
            base_url = "https://pixabay.com/api/"           #images
        params = {
            "key": self.pixabay_API_KEY,
            "q": query,
            "per_page": num_media
        }
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            data = response.json()
            media = data.get("hits", [])
            if not media:
                self.log.warning("No pixabay media found.")
                return
            # Create output directory if it doesn't exist
            os.makedirs(output_directory, exist_ok=True)
            # Download and save media
            for i, media in enumerate(media):
                media_url = media.get("largeImageURL")
                if not media_url:
                    media_url=media['videos']['large']['url']
                if media_url and len(media_url)!=0:
                    media_id = media["id"]
                    media_extension = media_url.split(".")[-1].split('?')[0]
                    media_filename = f"pixabay_{media_id}.{media_extension}"
                    media_path = os.path.join(output_directory, media_filename)

                    response = requests.get(media_url)
                    if response.status_code == 200:
                        with open(media_path, "wb") as file:
                            file.write(response.content)
                        self.log.info(f"Downloaded media {i+1}/{len(media)}: {media_filename}")
                    else:
                        self.log.error(f"Error downloading media {i+1}/{len(media)}. Status code: {response.status_code}")
            self.log.info(f"{num_media} media downloaded to {output_directory}")
        else:
            self.log.error(f"Error occurred while searching media. Status code: {response.status_code}")

    def search_images_bing(self, search_query, num_images, output_directory):
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
                    self.log.warning(f"Error downloading image: {e}")

        self.log.info(f"Downloaded {count} images to {output_directory}")

    def search_images_google(self, search_query, num_images, output_directory):
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
                self.log.warning(f"Error downloading image: {e}")
        self.log.info(f"Downloaded {count} images to {output_directory}")

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Download images from Google Images')
    parser.add_argument('query', type=str, help='search query')
    parser.add_argument('num_images', type=int, help='number of images to download')
    parser.add_argument('destination_dir', type=str, help='destination directory')
    parser.add_argument('pexels_key', type=str, help='pexels API key')
    parser.add_argument('pixabay_key', type=str, help='pixabay API key')

    args = parser.parse_args()
    si=SearchImages(args.pexels_key or "", args.pixabay_key or "", logging);
    si.search_images_google(args.query, args.num_images, args.destination_dir)
    si.search_images_bing(args.query, args.num_images, args.destination_dir)
    si.search_media_pexels(args.query, args.num_images, args.destination_dir)
    si.search_media_pixabay(args.query, args.num_images, args.destination_dir)

if __name__ == "__main__":
    main()

