import argparse
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import urllib.parse
import os

pexels_API_KEY = "JMdcZ8E4lrykP2QSaZHNxuXKlJRRjmmlvBQRvgu5CrHnSI30BF7mGLI7"
pixabay_API_KEY = "38036450-c3aaf7be223f4d01b66e68cae"

class SearchImages:
    def __init__(self, pexels, pixabay, log):
        self.pexels_API_KEY=pexels
        self.pixabay_API_KEY=pixabay
        self.log=log

    def search_images_pexels(self, query, num_images, output_directory):
        base_url = "https://api.pexels.com/v1/search"
        headers = {"Authorization": self.pexels_API_KEY}
        params = {"query": query, "per_page": num_images}

        response = requests.get(base_url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            photos = data.get("photos", [])

            if not photos:
                self.log.warning("No images found.")
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
                    self.log.info(f"Downloaded image: {image_filename}")
                else:
                    self.log.error(f"Error downloading image {image_filename}. Status code: {response.status_code}")

            self.log.info(f"{num_images} images downloaded to {output_directory}")
        else:
            self.log.error(f"Error occurred while searching images. Status code: {response.status_code}")

    def search_images_pixabay(self, query, num_images, output_directory):
        base_url = "https://pixabay.com/api/"
        params = {
            "key": self.pixabay_API_KEY,
            "q": query,
            "per_page": num_images
        }
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            data = response.json()
            images = data.get("hits", [])
            if not images:
                self.log.error("No images found.")
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
                    self.log.info(f"Downloaded image {i+1}/{num_images}: {image_filename}")
                else:
                    self.log.error(f"Error downloading image {i+1}/{num_images}. Status code: {response.status_code}")
            self.log.info(f"{num_images} images downloaded to {output_directory}")
        else:
            self.log.error(f"Error occurred while searching images. Status code: {response.status_code}")

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
    args = parser.parse_args()
    si=SearchImages(pexels_API_KEY, pixabay_API_KEY, logging);
    si.search_images_google(args.query, args.num_images, args.destination_dir)
    si.search_images_bing(args.query, args.num_images, args.destination_dir)
    si.search_images_pexels(args.query, args.num_images, args.destination_dir)
    si.search_images_pixabay(args.query, args.num_images, args.destination_dir)

if __name__ == "__main__":
    main()

