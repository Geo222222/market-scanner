import requests
from bs4 import BeautifulSoup

url = "https://en.wikipedia.org/wiki/Main_Page"
response = requests.get(url)
html_content = response.text

soup = BeautifulSoup(html_content, 'html.parser')
headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
header_titles = [header.get_text() for header in headers]

for title in header_titles:
    print(title)
    