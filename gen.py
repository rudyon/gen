import os
import shutil
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

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
            file_name_without_extension = os.path.splitext(filename)[0]
            index_file.write(f"- [{file_name_without_extension}]({filename})\n")

    logging.info("Generated index.md")

    return index_file_path

def convert_markdown_to_html(source, destination, markdown_file, index_file):
    file_name_without_extension = os.path.splitext(markdown_file)[0]
    markdown_file_path = os.path.join(source, markdown_file)
    html_file_path = os.path.join(destination, f"{file_name_without_extension}.html")

    logging.info(f"Converting {markdown_file} to {html_file_path}...")

    os.system(f"pandoc --quiet --lua-filter=links-to-html.lua --css=style.css --output={html_file_path} --to=html5 --standalone {markdown_file_path}")

    logging.info(f"Generated {file_name_without_extension}.html")

def generate_website(source, destination):
    logging.info("Generating website...")
    clear_destination_directory(destination)
    index_file = generate_index_file(source, destination)

    # Convert markdown files to HTML
    for filename in os.listdir(source):
        if filename.endswith(".md"):
            convert_markdown_to_html(source, destination, filename, index_file)

    os.remove(index_file)
    logging.info("Removed index.md")
    logging.info(f"Generated site. You can visit it at file://{destination}/index.html")

if __name__ == "__main__":
    print("[INFO] You must use the full path directory.")

    source = input("Where is the markdown source directory? ")
    destination = input("Where is the HTML destination directory? ")

    i = input("The destination directory you chose will be wiped. Type 'YES' to confirm. ")
    if i == "YES":
        generate_website(source, destination)
    else:
        print("[INFO] Cancelling.")
