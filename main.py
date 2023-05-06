from multiprocessing.connection import wait
import os
from xml.etree.ElementTree import tostring

for filename in os.listdir(os.getcwd() + "/src/"):
	os.system("pandoc -s -f markdown --template=template --wrap=preserve --css=style.css -M title={} -o {}.html .\src\{}".format(os.path.basename(filename)[:-3], os.path.basename(filename)[:-3], format(os.path.basename(filename))))

# This python file is temporary and is a quick hack.
# This will not be used in the future when I write a proper site generator.
# I am not using Hugo or Hakyll or Jekyll. I do not plan to.
# Because I like getting my hands dirty as much as possible.
# Probably not a good strategy. But I enjoy myself.