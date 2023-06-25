import argparse
import requests
from bs4 import BeautifulSoup
import urllib.parse
import os

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

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Download images from Google Images')
parser.add_argument('query', type=str, help='search query')
parser.add_argument('num_images', type=int, help='number of images to download')
parser.add_argument('destination_dir', type=str, help='destination directory')
args = parser.parse_args()

search_and_download_images(args.query, args.num_images, args.destination_dir)
