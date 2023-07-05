from multiprocessing.connection import wait
import os
from xml.etree.ElementTree import tostring

loc = input("where is the memx located? (enter full path)\n-> ")

os.system("rm site/*")
os.system("echo '# index' > site/index.md")

for filename in os.listdir(loc):
    os.system(f"echo '- [{filename[:-3]}]({filename})' >> site/index.md")
print("generated index.md")
os.system("pandoc --lua-filter=links-to-html.lua --css=style.css --output=site/index.html --to=html5 --standalone site/index.md")
print("generated index.html")
os.system("rm -v site/index.md")

for filename in os.listdir(loc):
    os.system(f"pandoc --lua-filter=links-to-html.lua --css=style.css --output=site/{filename[:-3]}.html --to=html5 --standalone {loc}/{filename}")
    print(f"generated {filename[:-3]}.html")
