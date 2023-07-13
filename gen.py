import os
import shutil
import logging
import configparser

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def copy_css_file(css_source, destination):
    css_destination = os.path.join(destination, "style.css")
    shutil.copy2(css_source, css_destination)
    logging.info("Copied CSS file.")

def copy_images(source, destination):
    os.system(f"cp {source}/*.png {destination}/")

def clear_destination_directory(destination):
    logging.info("Clearing destination directory...")
    shutil.rmtree(destination)
    os.makedirs(destination)

def generate_index_file(source, destination):
    logging.info("Generating index.md...")
    index_file_path = os.path.join(destination, "index.md")

    with open(index_file_path, "w") as index_file:
        index_file.write("# index\n")

        for filename in os.listdir(source):
            if filename.endswith(".md"):
                file_name_without_extension = os.path.splitext(filename)[0]
                index_file.write(f"- [{file_name_without_extension}]({filename})\n")

    logging.info("Generated index.md")

    return index_file_path

def convert_index_file(css_source, source, destination, index_file):
    html_file_path = os.path.join(destination, "index.html")
    logging.info("Converting index.md to index.html...")
    os.system(f"pandoc --quiet --lua-filter=links-to-html.lua --css={css_source} --output={html_file_path} --to=html5 --standalone {index_file}")
    logging.info("Generated index.html")
    return html_file_path

def convert_markdown_to_html(css_source, source, destination, markdown_file):
    file_name_without_extension = os.path.splitext(markdown_file)[0]
    markdown_file_path = os.path.join(source, markdown_file)
    html_file_path = os.path.join(destination, f"{file_name_without_extension}.html")

    logging.info(f"Converting {markdown_file} to {html_file_path}...")

    os.system(f"pandoc --quiet --lua-filter=links-to-html.lua --css={css_source} --output={html_file_path} --to=html5 --standalone {markdown_file_path}")

    logging.info(f"Generated {file_name_without_extension}.html")

def generate_website(css_source, source, destination):
    logging.info("Generating website...")
    clear_destination_directory(destination)

    copy_css_file(css_source, destination)
    copy_images(source, destination)

    index_file = generate_index_file(source, destination)

    html_index_file = convert_index_file(css_source, source, destination, index_file)

    # Convert markdown files to HTML
    for filename in os.listdir(source):
        if filename.endswith(".md"):
            convert_markdown_to_html(css_source, source, destination, filename)

    os.remove(index_file)
    logging.info("Removed index.md")
    logging.info(f"Generated site. You can visit it at file://{destination}/index.html")

if __name__ == "__main__":
    print("[INFO] Reading configuration from config.ini file.")

    config = configparser.ConfigParser()
    config.read("config.ini")

    source = config.get("Paths", "MarkdownSource")
    destination = config.get("Paths", "HTMLDestination")
    css_source = config.get("Paths", "CSSFile")

    i = input("The destination directory you chose will be wiped. Type 'YES' to confirm. ")
    if i == "YES":
        generate_website(css_source, source, destination)
    else:
        print("[INFO] Cancelling.")
