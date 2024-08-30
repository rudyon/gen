import os
import re
import markdown
import yaml
from jinja2 import Environment, FileSystemLoader
import shutil
from feedgen.feed import FeedGenerator
from datetime import datetime
import html
import pytz
from urllib.parse import urljoin

def load_config(config_path):
    with open(config_path, 'r') as config_file:
        return yaml.safe_load(config_file)

def remove_frontmatter(content):
    frontmatter_pattern = re.compile(r'^---\s*\n(.*?\n)---\s*\n', re.DOTALL)
    return frontmatter_pattern.sub('', content)

def process_content(content, vault_path, output_path, config, depth=0):
    if content is None:
        print("Warning: Received None content in process_content")
        return ""

    if depth > 10:  # Prevent infinite recursion
        return content

    def process_embeds(match):
        embed_filename = match.group(1) + '.md'
        embed_path = os.path.join(vault_path, embed_filename)
        if os.path.exists(embed_path):
            with open(embed_path, 'r', encoding='utf-8') as embed_file:
                embed_content = embed_file.read()
            embed_content = remove_frontmatter(embed_content)
            return process_content(embed_content, vault_path, output_path, config, depth + 1)
        return match.group(0)  # Return original if file not found

    def process_links(match):
        link_parts = match.group(1).split('|')
        link_text = link_parts[-1].strip()
        link_target = link_parts[0].strip()
        link_filename = link_target + '.md'

        if link_filename in config['pages']:
            return f'[{link_text}]({link_target}.html)'
        else:
            return link_text  # Remove brackets for non-config pages

    
    def process_images(match):
        full_match = match.group(0)
        image_parts = match.group(1).split('|')
        image_path = image_parts[0].strip()
        
        # Initialize variables for additional attributes
        size = None
        float_direction = None
        
        # Process additional attributes
        for part in image_parts[1:]:
            part = part.strip().lower()
            if part in ['left', 'right']:
                float_direction = part
            elif part.isdigit():
                size = part

        print(f"Processing image: {image_path}, Size: {size}, Float: {float_direction}")

        # Check if the image path is relative
        if not os.path.isabs(image_path):
            # First, check in the attachments folder
            full_image_path = os.path.join(vault_path, 'attachments', image_path)
            if not os.path.exists(full_image_path):
                # If not found in attachments, check in the vault root
                full_image_path = os.path.join(vault_path, image_path)
        else:
            full_image_path = image_path

        if os.path.exists(full_image_path):
            # Create 'images' directory in the output path if it doesn't exist
            output_images_dir = os.path.join(output_path, 'images')
            os.makedirs(output_images_dir, exist_ok=True)

            # Copy the image to the output directory
            image_filename = os.path.basename(full_image_path)
            shutil.copy2(full_image_path, os.path.join(output_images_dir, image_filename))

            print(f"Copied image: {full_image_path} to {os.path.join(output_images_dir, image_filename)}")

            # Construct the image tag with appropriate attributes
            img_tag = f'<img src="images/{image_filename}" alt="{image_filename}"'
            
            if size:
                img_tag += f' width="{size}"'
            
            if float_direction:
                img_tag += f' style="float: {float_direction}; margin: 10px;"'
            
            img_tag += '>'

            return img_tag

        print(f"Warning: Image not found: {image_path}")
        return full_match  # Return original if image not found

    # Apply all processing functions
    content = re.sub(r'!\[\[(.+?)\]\]', process_images, content)
    content = re.sub(r'\[\[(.+?)\]\]', process_links, content)
    content = re.sub(r'!\[(.*?)\]\((.+?)(\|.+?)?\)', process_images, content)

    return content

def generate_feeds(pages, output_path, config):
    fg = FeedGenerator()
    site_url = config.get('site_url', 'http://example.com')
    fg.id(site_url)
    fg.title(config.get('site_title', 'My Static Site'))
    fg.author({'name': config.get('author_name', 'Site Author'), 'email': config.get('author_email', 'author@example.com')})
    fg.link(href=site_url, rel='alternate')
    fg.logo(config.get('site_logo', 'http://ex.com/logo.jpg'))
    fg.subtitle(config.get('site_description', 'A static site generated from Markdown files'))
    fg.language('en')

    utc_tz = pytz.UTC

    for page in pages:
        fe = fg.add_entry()
        page_url = urljoin(site_url, page['link'])
        fe.id(page_url)
        fe.title(page['title'])
        fe.link(href=page_url)
        fe.description(html.escape(page['summary']))
        fe.pubDate(datetime.now(utc_tz))

    rss_path = os.path.join(output_path, 'rss.xml')
    fg.rss_file(rss_path)
    print(f"RSS feed generated: {rss_path}")

    atom_path = os.path.join(output_path, 'atom.xml')
    fg.atom_file(atom_path)
    print(f"Atom feed generated: {atom_path}")

def generate_site(config):
    vault_path = config['vault_path']
    output_path = config['output_path']
    pages = config['pages']

    os.makedirs(output_path, exist_ok=True)

    env = Environment(loader=FileSystemLoader('templates'))
    page_template = env.get_template('page.html')
    index_template = env.get_template('index.html')

    md = markdown.Markdown(extensions=['tables', 'fenced_code'])

    style_src = os.path.join('templates', 'style.css')
    style_dst = os.path.join(output_path, 'style.css')
    if os.path.exists(style_src):
        shutil.copy(style_src, style_dst)
        print(f"Copied style.css to {style_dst}")
    else:
        print("Warning: style.css not found in templates folder")

    processed_pages = []
    total_pages = len(pages)
    for index, page in enumerate(pages, start=1):
        print(f"Processing file {index}/{total_pages}: {page}")

        input_path = os.path.join(vault_path, page)
        output_file = os.path.splitext(page)[0] + '.html'
        output_file_path = os.path.join(output_path, output_file)

        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()

            content = remove_frontmatter(content)
            processed_content = process_content(content, vault_path, output_path, config)

            html_content = md.convert(processed_content)

            page_html = page_template.render(content=html_content, title=os.path.splitext(page)[0])

            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(page_html)

            summary = re.sub(r'<[^>]+>', '', html_content)[:150] + '...'

            processed_pages.append({
                'title': os.path.splitext(page)[0],
                'link': output_file,
                'summary': summary
            })

            print(f"Converted {page} to {output_file}")
        except Exception as e:
            print(f"Error processing {page}: {str(e)}")
            continue

    print("Generating index.html...")
    index_html = index_template.render(pages=processed_pages)
    with open(os.path.join(output_path, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)
    print("index.html generated")

    print("Generating RSS and Atom feeds...")
    generate_feeds(processed_pages, output_path, config)
    print("Feeds generated")

if __name__ == '__main__':
    print("Starting the static site generator...")
    try:
        config = load_config('config.yaml')
        print("Config loaded successfully:", config)
        generate_site(config)
        print("Site generation complete!")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
