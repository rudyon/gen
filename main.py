import os
import re
import markdown
import yaml
from jinja2 import Environment, FileSystemLoader
import shutil

def load_config(config_path):
    with open(config_path, 'r') as config_file:
        return yaml.safe_load(config_file)

def remove_frontmatter(content):
    frontmatter_pattern = re.compile(r'^---\s*\n(.*?\n)---\s*\n', re.DOTALL)
    return frontmatter_pattern.sub('', content)

def process_content(content, vault_path, output_path, config, depth=0):
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
        link_text = match.group(1)
        link_filename = link_text + '.md'
        if link_filename in config['pages']:
            return f'[{link_text}]({link_text}.html)'
        else:
            return link_text  # Remove brackets for non-config pages

    def process_images(match):
        image_path = match.group(1)
        full_image_path = os.path.join(vault_path, image_path)
        if os.path.exists(full_image_path):
            # Create 'images' directory in the output path if it doesn't exist
            output_images_dir = os.path.join(output_path, 'images')
            os.makedirs(output_images_dir, exist_ok=True)
            
            # Copy the image to the output directory
            image_filename = os.path.basename(image_path)
            shutil.copy(full_image_path, os.path.join(output_images_dir, image_filename))
            
            # Update the image path in the Markdown
            return f'![{match.group(2)}](images/{image_filename})'
        return match.group(0)  # Return original if image not found

    # Process embeds
    content = re.sub(r'!\[\[(.*?)\]\]', process_embeds, content)
    
    # Process links
    content = re.sub(r'\[\[(.*?)\]\]', process_links, content)

    # Process images
    content = re.sub(r'!\[(.*?)\]\((.*?)\)', process_images, content)

    return content

def generate_site(config):
    vault_path = config['vault_path']
    output_path = config['output_path']
    pages = config['pages']

    os.makedirs(output_path, exist_ok=True)

    env = Environment(loader=FileSystemLoader('templates'))
    page_template = env.get_template('page.html')
    index_template = env.get_template('index.html')

    # Set up Markdown with extensions
    md = markdown.Markdown(extensions=['tables', 'fenced_code'])

    # Copy style.css to output directory
    style_src = os.path.join('templates', 'style.css')
    style_dst = os.path.join(output_path, 'style.css')
    if os.path.exists(style_src):
        shutil.copy(style_src, style_dst)
        print(f"Copied style.css to {style_dst}")
    else:
        print("Warning: style.css not found in templates folder")

    processed_pages = []
    for page in pages:
        input_path = os.path.join(vault_path, page)
        output_file = os.path.splitext(page)[0] + '.html'
        output_file_path = os.path.join(output_path, output_file)

        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()

        content = remove_frontmatter(content)
        content = process_content(content, vault_path, output_path, config)

        # Convert Markdown to HTML using the configured Markdown instance
        html_content = md.convert(content)

        page_html = page_template.render(content=html_content, title=os.path.splitext(page)[0])

        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(page_html)

        processed_pages.append({'title': os.path.splitext(page)[0], 'link': output_file})

    index_html = index_template.render(pages=processed_pages)
    with open(os.path.join(output_path, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)

if __name__ == '__main__':
    print("Starting the static site generator...")
    try:
        config = load_config('config.yaml')
        print("Config loaded successfully:", config)
        generate_site(config)
        print("Site generation complete!")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
