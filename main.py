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
import traceback

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

    def process_image(path, attributes):
        # Initialize variables for additional attributes
        size = None
        float_direction = None
        
        # Process additional attributes
        for attr in attributes:
            attr = attr.strip().lower()
            if attr in ['left', 'right']:
                float_direction = attr
            elif attr.isdigit():
                size = attr

        # Check if the image path is relative
        if not os.path.isabs(path):
            # First, check in the attachments folder
            full_image_path = os.path.join(vault_path, 'attachments', path)
            if not os.path.exists(full_image_path):
                # If not found in attachments, check in the vault root
                full_image_path = os.path.join(vault_path, path)
        else:
            full_image_path = path

        if os.path.exists(full_image_path):
            # Create 'images' directory in the output path if it doesn't exist
            output_images_dir = os.path.join(output_path, 'images')
            os.makedirs(output_images_dir, exist_ok=True)

            # Copy the image to the output directory
            image_filename = os.path.basename(full_image_path)
            shutil.copy2(full_image_path, os.path.join(output_images_dir, image_filename))

            # Construct the image tag with appropriate attributes
            img_tag = f'<img src="images/{image_filename}" alt="{image_filename}"'
            
            if size:
                img_tag += f' width="{size}"'
            
            if float_direction:
                img_tag += f' style="float: {float_direction}; margin: 10px;"'
            
            img_tag += '>'

            return img_tag

        return None  # Return None if image not found

    def process_embeds(match):
        embed_path = match.group(1)
        parts = embed_path.split('|')
        path = parts[0].strip()
        attributes = parts[1:] if len(parts) > 1 else []
        
        # Check if it's an image embed or a note embed
        if any(path.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
            result = process_image(path, attributes)
            return result if result is not None else match.group(0)
        else:
            # It's a note embed
            embed_filename = f"{path}.md"
            full_embed_path = os.path.join(vault_path, embed_filename)
            
            if os.path.exists(full_embed_path):
                with open(full_embed_path, 'r', encoding='utf-8') as embed_file:
                    embed_content = embed_file.read()
                embed_content = remove_frontmatter(embed_content)
                return process_content(embed_content, vault_path, output_path, config, depth + 1)
            return match.group(0)  # Return original if file not found

    def process_markdown_images(match):
        alt_text = match.group(1) or ''
        path = match.group(2)
        attributes_str = match.group(3) or ''
        attributes = attributes_str.strip('|').split('|') if attributes_str else []
        
        result = process_image(path, attributes)
        return result if result is not None else match.group(0)

    def process_links(match):
        link_parts = match.group(1).split('|')
        link_text = link_parts[-1].strip()
        link_target = link_parts[0].strip()
        link_filename = link_target + '.md'

        if link_filename in config['pages']:
            return f'[{link_text}]({link_target}.html)'
        else:
            return link_text  # Remove brackets for non-config pages

    # Apply all processing functions
    content = re.sub(r'!\[\[(.+?)\]\]', process_embeds, content)
    content = re.sub(r'\[\[(.+?)\]\]', process_links, content)
    content = re.sub(r'!\[(.*?)\]\((.+?)(\|.+?)?\)', process_markdown_images, content)

    return content

def generate_feeds(pages, output_path, config):
    fg = FeedGenerator()
    site_url = config.get('site_url', 'http://example.com')
    fg.id(site_url)
    fg.title(config.get('site_title', 'My Static Site'))
    fg.author({'name': config.get('author_name', 'Site Author'), 
               'email': config.get('author_email', 'author@example.com')})
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
        
        # Use full content instead of summary
        fe.content(content=page['content'], type='html')
        
        # Use the last modified timestamp as both published and updated
        last_modified_utc = page['last_modified'].astimezone(utc_tz)
        fe.published(last_modified_utc)
        fe.updated(last_modified_utc)

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

        markdown_path = os.path.join(vault_path, page)
        output_file = os.path.splitext(page)[0] + '.html'
        output_file_path = os.path.join(output_path, output_file)

        try:
            # Get the last modification time for the file
            local_tz = datetime.now().astimezone().tzinfo
            last_modified = datetime.fromtimestamp(
                os.path.getmtime(markdown_path)
            ).replace(tzinfo=local_tz)

            with open(markdown_path, 'r', encoding='utf-8') as f:
                content = f.read()

            content = remove_frontmatter(content)
            processed_content = process_content(content, vault_path, output_path, config)

            html_content = md.convert(processed_content)

            page_html = page_template.render(
                content=html_content,
                title=os.path.splitext(page)[0],
                last_modified=last_modified
            )

            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(page_html)

            processed_pages.append({
                'title': os.path.splitext(page)[0],
                'link': output_file,
                'content': html_content,
                'last_modified': last_modified
            })

            print(f"Converted {page} to {output_file} (Last modified: {last_modified})")
        except Exception as e:
            print(f"Error processing {page}: {str(e)}")
            traceback.print_exc()
            continue

    # Sort pages by last modified timestamp, newest first
    processed_pages.sort(key=lambda x: x['last_modified'], reverse=True)

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
        traceback.print_exc()
