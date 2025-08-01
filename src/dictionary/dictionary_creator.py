# src/dictionary/dictionary_creator.py

"""
Module for dictionary creation functionality.
Adapted from createdict.py script to work with Django models.
"""

import os
import re
import json
import zipfile
import tempfile
import shutil
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from django.conf import settings
from django.core.files import File

def read_file_preserving_cr(file_path):
    """
    Czyta plik zachowując oryginalne znaki \r jako separatory,
    ale normalizując końce linii pliku.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # KROK 1: Czytaj jako binary
    with open(file_path, 'rb') as f:
        raw_bytes = f.read()
    
    # KROK 2: Dekoduj do tekstu
    try:
        content = raw_bytes.decode('utf-8')
    except UnicodeDecodeError:
        # Fallback dla plików w innych kodowaniach
        content = raw_bytes.decode('utf-8', errors='ignore')
    
    logger.info(f"Raw content preview: {repr(content[:200])}")
    
    # KROK 3: Zamień tylko \r\n na \n (końce linii Windows)
    # ALE zostaw jednotne \r jako separatory
    content = content.replace('\r\n', '\n')
    
    logger.info(f"After CRLF normalization: {repr(content[:200])}")
    
    return content

def parse_line(line):
    """Parse a line of dictionary content to extract term, inflections and description."""
    match = re.match(r'^(.*?)\s*\|\s*(\{.*?\})?\s+(.*)$', line)
    if match:
        term = match.group(1).strip()
        inflections = match.group(2)
        description = match.group(3).strip()
        if inflections:
            # Remove curly braces and split by comma
            inflections = inflections.strip('{}').split(',')
            inflections = [inf.strip() for inf in inflections]
        else:
            inflections = []
        return {'term': term, 'inflections': inflections, 'description': description}
    else:
        return None

def process_dictionary_content(content, base_filename, work_dir, language_info, build_version=1):
    import logging
    logger = logging.getLogger(__name__)

    """
    Process dictionary content and generate all necessary files.
    
    Args:
        content: The content of the dictionary file
        base_filename: Base name for output files
        work_dir: Working directory path
        language_info: Dictionary with language settings
    
    Returns:
        Dictionary with paths to generated files
    """
    # Process entries        

    lines = content.split('\n')
    logger.info(f"Split into {len(lines)} lines")

    entries = []
    current_group = None
    
    for i, line in enumerate(lines):
        line = line.strip()        

        logger.info(f'Processing line: {line}')

        if not line:
            continue  # Skip empty lines

        # Check for leading character
        if line.startswith('~'):
            # Group entry
            line_content = line[1:].strip()
            entry = parse_line(line_content)
            if entry is None:
                continue  # Skip invalid lines
            entry['children'] = []
            entries.append(entry)
            current_group = entry
        elif line.startswith('+'):
            # Member of a group
            if current_group is None:
                continue  # Skip orphaned group members
            line_content = line[1:].strip()
            entry = parse_line(line_content)
            if entry is None:
                continue  # Skip invalid lines
            current_group['children'].append(entry)
        else:
            # Simple entry
            entry = parse_line(line)
            if entry is None:
                continue  # Skip invalid lines
            entries.append(entry)
            current_group = None  # Reset current group
    
    logger.info(f"Processed {len(entries)} total entries")

    # Generate files
    file_paths = {}
    
    # Generate HTML content
    html_content = generate_html(entries, base_filename, language_info)
    html_path = os.path.join(work_dir, f"{base_filename}.html")
    with open(html_path, 'w', encoding=language_info['output_encoding']) as f:
        f.write(html_content)
    file_paths['html'] = html_path
    
    # Copy CSS file
    css_source_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'styles.css')
    css_dest_path = os.path.join(work_dir, 'styles.css')
    shutil.copy(css_source_path, css_dest_path)
    file_paths['css'] = css_dest_path
    
    # Generate OPF content
    opf_content = generate_opf(base_filename, language_info)
    opf_path = os.path.join(work_dir, f"{base_filename}.opf")
    with open(opf_path, 'w', encoding=language_info['output_encoding']) as f:
        f.write(opf_content)
    file_paths['opf'] = opf_path
    
    # Generate JPG cover image
    jpg_path = os.path.join(work_dir, f"{base_filename}.jpg")
    generate_cover_image(base_filename, jpg_path)
    file_paths['jpg'] = jpg_path
    
    # Generate JSON metadata file
    json_path = os.path.join(work_dir, f"{base_filename}.json")
    current_time = datetime.now().isoformat()
    
    # Use the creation date from language_info if provided
    original_build_date = language_info.get('original_build_date')
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Original build date from model: {original_build_date}")
    
    metadata = {
        'build_version': build_version,
        'build_date': original_build_date if original_build_date else current_time,
        'updated_at': current_time,
        'created_by': language_info['creator_name'],
        'updated_by': language_info.get('updater_name', language_info['creator_name']),
        'dictionary_name': base_filename,
        'language_code': language_info['language_code']
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)
    file_paths['json'] = json_path
    
    # Nie tworzymy jeszcze pliku ZIP - zostanie on utworzony po wygenerowaniu pliku MOBI
    
    return file_paths

def generate_html(entries, base_filename, settings):
    """Generate HTML content for the dictionary."""
    # Header
    html_header = f'''<?xml version="1.0" encoding="utf-8"?>
<html 
    xmlns:idx="https://kindlegen.s3.amazonaws.com/AmazonKindlePublishingGuidelines.pdf"
    xmlns:mbp="https://kindlegen.s3.amazonaws.com/AmazonKindlePublishingGuidelines.pdf"
    xmlns:xlink="http://www.w3.org/1999/xlink">

<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <link rel="stylesheet" href="styles.css" type="text/css">
</head>
  <body>
    <mbp:pagebreak/>
    <mbp:frameset>
        <mbp:slave-frame display="bottom" device="all" breadth="auto" leftmargin="0" rightmargin="0" bottommargin="0" topmargin="0">
            <!--<div align="center" bgcolor="yellow"/><a onclick="index_search()">Dictionary Search</a></div>-->
        </mbp:slave-frame> 
        <mbp:pagebreak/>	
'''

    # Entries
    html_entries = ''
    for entry in entries:
        html_entries += generate_entry_html(entry)

    # Footer
    html_footer = '''    </mbp:frameset>
  </body>
</html>
'''

    return html_header + html_entries + html_footer

def generate_entry_html(entry, indent=0):
    """Generate HTML for a dictionary entry."""
    indent_str = '    ' * indent
    term = entry['term']
    inflections = entry['inflections']
    description = entry['description']
    idx_infl = ''
    if inflections:
        idx_infl = '\n' + indent_str + '                <idx:infl>\n'
        for inf in inflections:
            idx_infl += indent_str + f'                    <idx:iform value="{inf}"/>\n'
        idx_infl += indent_str + '                </idx:infl>\n'
    else:
        idx_infl = ''

    # Use <h2> for all entries
    header_tag = 'h2'

    # Process description to handle multiple paragraphs
    # Replace linebreaks with </p><p> to create separate paragraphs
    # processed_description = description.replace('\\n', '</p><p>') # old version
    processed_description = re.sub(r'(\\n|\r|<br>|<BR>)', '</p><p>', description)
    
    # Build entry
    entry_html = indent_str + f'''        <idx:entry name="word" scriptable="yes">
{indent_str}            <idx:orth value="{term.lower()}">
{indent_str}                <{header_tag}>{term}</{header_tag}>{idx_infl}{indent_str}            </idx:orth>
{indent_str}            <p>{processed_description}</p>
'''
    # Process children if any
    if 'children' in entry and entry['children']:
        for child in entry['children']:
            entry_html += generate_entry_html(child, indent=indent+2)
    entry_html += indent_str + f'''        </idx:entry>
'''
    return entry_html

def generate_opf(base_filename, settings):
    """Generate OPF content for the dictionary."""
    current_date = datetime.now().strftime("%m/%d/%Y")
    opf_content = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE package SYSTEM "oeb1.ent">
<package unique-identifier="uid" xmlns:dc="Dublin Core">
<metadata>
    <dc-metadata>
        <dc:Identifier id="uid">{base_filename}</dc:Identifier>
        <!-- Title of the document -->
        <dc:Title>{base_filename}</dc:Title>
        <dc:Language>{settings['language_code']}</dc:Language>
        <dc:Creator>{settings['creator_name']}</dc:Creator>
        <dc:Date>{current_date}</dc:Date>
    </dc-metadata>
    <x-metadata>
        <output encoding="{settings['output_encoding']}" flatten-dynamic-dir="yes"/>
        <DictionaryInLanguage>{settings['dictionary_in_language']}</DictionaryInLanguage>
        <DictionaryOutLanguage>{settings['dictionary_out_language']}</DictionaryOutLanguage>
        <EmbeddedCover>{base_filename}.jpg</EmbeddedCover>
    </x-metadata>
</metadata>
<manifest>
     <item id="dictionary" href="{base_filename}.html" media-type="text/x-oeb1-document"/>
     <item id="css" href="styles.css" media-type="text/css"/>
     <item id="cover" href="{base_filename}.jpg" media-type="image/jpeg"/>
</manifest>
<!-- list of the html files in the correct order  -->
<spine>
    <itemref idref="dictionary"/>
</spine>
<tours/>
<guide> <reference type="search" title="Dictionary Search" onclick="index_search()"/> </guide>
</package>
'''
    return opf_content

def generate_cover_image(title, output_path):
    """Generate a cover image for the dictionary."""
    img_width, img_height = 600, 800  # Portrait mode dimensions
    img = Image.new('RGB', (img_width, img_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Use default font
    font = ImageFont.load_default()

    # Calculate text size and position
    text = title
    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((img_width - text_width) / 2, (img_height - text_height) / 2)

    # Draw text onto image
    draw.text(position, text, fill=(0, 0, 0), font=font)

    # Save image
    img.save(output_path)

def run_kindlegen(opf_file, output_file=None):
    """
    Run kindlegen to generate a MOBI file from the OPF file.
    
    Args:
        opf_file: Path to the OPF file
        output_file: Optional output file name
    
    Returns:
        Path to the generated MOBI file or None if generation failed
    """
    import logging
    import time
    import json
    import shutil
    logger = logging.getLogger(__name__)
    
    # Get directory and base filename
    directory = os.path.dirname(opf_file)
    base_filename = os.path.splitext(os.path.basename(opf_file))[0]
    
    # Określenie ścieżki do pliku MOBI
    mobi_path = os.path.join(directory, output_file if output_file else f"{base_filename}.mobi")
    
    logger.info(f"Attempting to generate MOBI file for {opf_file}")
    logger.info(f"Expected MOBI output path: {mobi_path}")
    
    try:
        # Używamy tylko alternatywnego podejścia - kopiujemy pliki do katalogu media
        logger.info("Using external kindlegen processor")
        
        from django.conf import settings
        media_dir = os.path.join(settings.MEDIA_ROOT, 'kindlegen_jobs')
        os.makedirs(media_dir, exist_ok=True)
        
        # Tworzymy unikalny katalog dla tego zadania
        job_id = f"{base_filename}_{int(time.time())}"
        job_dir = os.path.join(media_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)
        
        # Kopiujemy wszystkie pliki z katalogu tymczasowego do katalogu zadania
        for file in os.listdir(directory):
            src_file = os.path.join(directory, file)
            if os.path.isfile(src_file):
                shutil.copy2(src_file, os.path.join(job_dir, file))
        
        # Tworzymy plik zadania
        job_file = os.path.join(job_dir, 'job.json')
        job_data = {
            'opf_file': os.path.basename(opf_file),
            'output_file': output_file if output_file else f"{base_filename}.mobi",
            'status': 'pending',
            'created_at': time.time()
        }
        
        with open(job_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"Created kindlegen job in {job_dir}")
        
        # Czekamy na zakończenie zadania (maksymalnie 60 sekund)
        max_wait = 60
        wait_interval = 2
        waited = 0
        
        while waited < max_wait:
            time.sleep(wait_interval)
            waited += wait_interval
            
            # Sprawdzamy, czy plik job.json został zaktualizowany
            try:
                with open(job_file, 'r', encoding='utf-8') as f:
                    updated_job = json.load(f)
                
                if updated_job.get('status') == 'completed':
                    logger.info(f"Job completed successfully: {job_file}")
                    
                    # Kopiujemy plik MOBI z powrotem do katalogu tymczasowego
                    mobi_file = os.path.join(job_dir, updated_job.get('output_file'))
                    if os.path.exists(mobi_file) and os.path.getsize(mobi_file) > 0:
                        shutil.copy2(mobi_file, mobi_path)
                        logger.info(f"Copied MOBI file to {mobi_path}")
                        
                        # Usuwamy katalog zadania po skopiowaniu pliku MOBI
                        try:
                            # Oznaczamy zadanie jako do usunięcia
                            updated_job['cleanup'] = True
                            with open(job_file, 'w', encoding='utf-8') as f:
                                json.dump(updated_job, f, ensure_ascii=False, indent=4)
                            
                            # Próbujemy usunąć katalog zadania
                            shutil.rmtree(job_dir)
                            logger.info(f"Removed job directory: {job_dir}")
                        except Exception as e:
                            logger.warning(f"Could not remove job directory {job_dir}: {str(e)}")
                        
                        return mobi_path
                    else:
                        logger.error(f"MOBI file not found or empty: {mobi_file}")
                        return None
                
                elif updated_job.get('status') == 'failed':
                    logger.error(f"Job failed: {updated_job.get('error', 'Unknown error')}")
                    return None
                
                logger.info(f"Waiting for job completion... ({waited}/{max_wait}s)")
            
            except Exception as e:
                logger.warning(f"Error checking job status: {str(e)}")
        
        logger.error(f"Timed out waiting for job completion after {max_wait}s")
        return None
    
    except Exception as e:
        logger.error(f"Exception during MOBI generation: {str(e)}", exc_info=True)
        return None

def create_dictionary_files(dictionary_instance):
    """
    Create all necessary files for a dictionary and update the dictionary instance.
    
    Args:
        dictionary_instance: A Dictionary model instance
    
    Returns:
        True if successful, False otherwise
    """
    import logging
    logger = logging.getLogger(__name__)
    try:
        # Get source file content
        content = read_file_preserving_cr(dictionary_instance.source_file.path)
        
        # Create a temporary working directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up language info
            language_info = {
                'css_path': 'styles.css',
                'language_code': dictionary_instance.language_code,
                'creator_name': dictionary_instance.creator_name,
                'updater_name': dictionary_instance.updater_name,
                'output_encoding': 'utf-8',
                'dictionary_in_language': 'pl',  # Default, could be customized later
                'dictionary_out_language': 'pl',  # Default, could be customized later
            }
            
            # Add original build date if this is an update
            if dictionary_instance.created_at:
                language_info['original_build_date'] = dictionary_instance.created_at.isoformat()
                logger.info(f"Using original build date from model: {language_info['original_build_date']}")
            
            # Process dictionary content
            file_paths = process_dictionary_content(
                content, 
                dictionary_instance.name, 
                temp_dir, 
                language_info,
                dictionary_instance.build_version
            )
            
            # Generate MOBI file
            mobi_path = run_kindlegen(file_paths['opf'])
            if mobi_path and os.path.exists(mobi_path):
                file_paths['mobi'] = mobi_path
            
            # Teraz tworzymy plik ZIP, który będzie zawierał również plik MOBI
            zip_path = os.path.join(temp_dir, f"{dictionary_instance.name}.zip")
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for file_key, file_path in file_paths.items():
                    if os.path.exists(file_path):
                        zipf.write(file_path, os.path.basename(file_path))
            file_paths['zip'] = zip_path
            
            # Upewnijmy się, że plik MOBI został dodany do pliku ZIP
            if 'mobi' in file_paths and os.path.exists(file_paths['mobi']):
                with zipfile.ZipFile(zip_path, 'a') as zipf:
                    mobi_filename = os.path.basename(file_paths['mobi'])
                    if mobi_filename not in zipf.namelist():
                        zipf.write(file_paths['mobi'], mobi_filename)
                        logger.info(f"Added MOBI file to ZIP: {mobi_filename}")
            
            # Save files to model
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Saving files to dictionary model. Available files: {list(file_paths.keys())}")
            
            for file_key, file_path in file_paths.items():
                if os.path.exists(file_path):
                    logger.info(f"Saving {file_key} file: {file_path}")
                    with open(file_path, 'rb') as f:
                        if file_key == 'html':
                            dictionary_instance.html_file.save(os.path.basename(file_path), File(f), save=False)
                        elif file_key == 'opf':
                            dictionary_instance.opf_file.save(os.path.basename(file_path), File(f), save=False)
                        elif file_key == 'jpg':
                            dictionary_instance.jpg_file.save(os.path.basename(file_path), File(f), save=False)
                        elif file_key == 'json':
                            dictionary_instance.json_file.save(os.path.basename(file_path), File(f), save=False)
                        elif file_key == 'zip':
                            dictionary_instance.zip_file.save(os.path.basename(file_path), File(f), save=False)
                        elif file_key == 'mobi':
                            logger.info(f"Saving MOBI file: {file_path} (size: {os.path.getsize(file_path)} bytes)")
                            dictionary_instance.mobi_file.save(os.path.basename(file_path), File(f), save=False)
                else:
                    logger.warning(f"File {file_path} does not exist, skipping")
            
            # Nie aktualizujemy numeru wersji z pliku JSON, ponieważ chcemy zachować wartość ustawioną w widoku
            # Numer wersji jest już zapisany w pliku JSON i zostanie zachowany w modelu
            
            # Save the instance
            dictionary_instance.save()
            
            return True
    
    except Exception as e:
        # Log the error
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error creating dictionary files: {str(e)}")
        
        # Update dictionary status
        dictionary_instance.status = 'failed'
        dictionary_instance.status_message = str(e)
        dictionary_instance.save(update_fields=['status', 'status_message', 'updated_at'])
        
        return False
