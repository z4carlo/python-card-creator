#!/usr/bin/env python
import csv
import os
import tkinter as tk
import pdb
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageStat
from collections import defaultdict
import sys
import re
from pathlib import Path

#pip install pillow

FactionColors = {
    "Martell":"#a96438",
    "Neutral":"#544334",
    "Night's Watch":"#212425",
    "Stark":"#515a62",
    "Targaryen":"#5e102b",
    "Baratheon":"#242829",
    "Bolton":"#855953",
    "Free Folk":"#2f2922",
    "Greyjoy":"#02363a",
    "Lannister":"#861b25",
}

ArmyAttackAndAbilitiesBorderColors = {
    "Neutral":"Silver",
    "Night's Watch":"Gold",
    "Stark":"Gold",
    "Targaryen":"Gold",
    "Baratheon":"Silver",
    "Bolton":"Gold",
    "Free Folk":"Gold",
    "Greyjoy":"Gold",
    "Martell":"Gold",
    "Lannister":"Silver",
}

def add_rounded_corners(im, rad):
    circle = Image.new('L', (rad * 2, rad * 2), 0)
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, rad * 2, rad * 2), fill=255)
    alpha = Image.new('L', im.size, "white")
    w,h = im.size
    alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
    alpha.paste(circle.crop((0, 0, rad, rad)).rotate(90), (0, h - rad))
    alpha.paste(circle.crop((0, 0, rad, rad)).rotate(180), (w - rad, h - rad))
    alpha.paste(circle.crop((0, 0, rad, rad)).rotate(270), (w - rad, 0))
    alpha.paste(255, (rad, 0, w - rad, h - rad))
    alpha.paste(255, (0, rad, rad, h - rad))
    alpha.paste(255, (w - rad, rad, w, h - rad))
    alpha.paste(255, (rad, rad, w - rad, h - rad))
    im = im.convert("RGBA")
    im.putalpha(alpha)
    return im

def load_fonts(fonts_folder):
    font_files = [f for f in os.listdir(fonts_folder) if f.lower().endswith(('.otf', '.ttf'))]
    fonts = {}
    for font_file in font_files:
        try:
            font_path = os.path.join(fonts_folder, font_file)
            fonts[font_file.split(".")[0]] = ImageFont.truetype(font_path, size=44)
            for i in range(2,61):
                fonts[font_file.split(".")[0]+f'-{i}'] = ImageFont.truetype(font_path, size=i)
            print(f"Successfully loaded font: {font_file}")
        except Exception as e:
            print(f"Failed to load font {font_file}: {str(e)}")
    return fonts

def import_csvs_to_dicts(assets_data_folder, lang=False):
    csv_files = [f for f in os.listdir(assets_data_folder) if f.endswith('.csv')]
    if lang:
        csv_files = [f for f in os.listdir(assets_data_folder) if f.endswith('.csv') and f'.{lang}.' in f]
    all_data = {}
    for csv_file in csv_files:
        file_path = os.path.join(assets_data_folder, csv_file)
        with open(file_path, mode='r', encoding='utf-8') as f:
            # Read the first line to get the headers
            original_headers = next(csv.reader(f))
            # Replace empty headers with incremental numbers as strings
            headers = [header if header else str(i) for i, header in enumerate(original_headers, 1)]
            # Go back to the start of the file before reading the rest
            f.seek(0)
            # Create a DictReader with the modified headers
            reader = csv.DictReader(f, fieldnames=headers)
            # Skip the original header row, since we already processed it
            next(reader)
            # Convert the content of the CSV file to a list of dictionaries
            data = [row for row in reader]
        all_data[csv_file.split('.')[0]] = data
    return all_data

# I use this so I can load the unit card and get x + y on the card so I can more easily get coordinates of images on click
class ImageEditor:
    def __init__(self, master, ncu_card_image):
        self.master = master
        master.title("Image Editor")

        self.ncu_card_image = ncu_card_image
        self.tk_image = ImageTk.PhotoImage(self.ncu_card_image)
        
        self.label = tk.Label(master, image=self.tk_image)
        self.label.pack()

        self.label.bind("<Button-1>", self.log_coordinates)

    def log_coordinates(self, event):
        x = event.x
        y = event.y
        print(f"Clicked at: {x}, {y}")


def draw_centered_text(draw, position, text_lines_list, font, fill, line_padding=0):
    """
    Draw multi-line text centered at the specified position.

    :param draw: ImageDraw object.
    :param position: Tuple (x, y) representing the position to center the text at.
    :param text: The text to draw.
    :param font: The font to use.
    :param fill: Color to use for the text.
    :param padding: Padding between lines of text.
    """
    total_height = sum([font.getbbox(line)[3] - font.getbbox(line)[1] for line in text_lines_list]) + line_padding * (len(text_lines_list) - 1)

    x, y = position
    y -= total_height / 2  # Adjust y-coordinate to start drawing from.

    for line in text_lines_list:
        text_width, text_height = font.getbbox(line)[2], font.getbbox(line)[3] - font.getbbox(line)[1]
        draw.text((x - text_width / 2, y), line, font=font, fill=fill)
        y += text_height + line_padding


def add_shadow(original_image, shadow_size, shadow_strength, sides=('left', 'top', 'right', 'bottom')):
    if original_image.mode != 'RGBA':
        original_image = original_image.convert('RGBA')
    original_width, original_height = original_image.size
    # Calculate new image size
    new_width = original_width + shadow_size * ('left' in sides) + shadow_size * ('right' in sides)
    new_height = original_height + shadow_size * ('top' in sides) + shadow_size * ('bottom' in sides)
    # Create a new image with the new size and a transparent background
    new_image = Image.new('RGBA', (new_width, new_height), (0, 0, 0, 0))
    # Create the shadow gradient
    shadow_gradient = [i * (255 - shadow_strength) // shadow_size for i in range(shadow_size)]
    # Create the shadow on each side
    for side in sides:
        for i, alpha in enumerate(shadow_gradient):
            if side == 'left':
                band = Image.new('RGBA', (1, original_height), (0, 0, 0, alpha))
                new_image.paste(band, (i, shadow_size * ('top' in sides)))
            elif side == 'right':
                band = Image.new('RGBA', (1, original_height), (0, 0, 0, alpha))
                new_image.paste(band, (new_width - i - 1, shadow_size * ('top' in sides)))
            elif side == 'top':
                band = Image.new('RGBA', (original_width, 1), (0, 0, 0, alpha))
                new_image.paste(band, (shadow_size * ('left' in sides), i))
            elif side == 'bottom':
                band = Image.new('RGBA', (original_width, 1), (0, 0, 0, alpha))
                new_image.paste(band, (shadow_size * ('left' in sides), new_height - i - 1))
    # Place the original image on top of the shadow
    original_position = (shadow_size * ('left' in sides), shadow_size * ('top' in sides))
    new_image.paste(original_image, original_position, original_image)
    return new_image


def split_name_string(s, amnt=15):
    # Split the string by comma if it exists
    if ',' in s:
        return s.split(','), True
    # Split the string if it's longer than 18 characters
    if len(s) > amnt:
        # Find the middle index of the string
        middle_idx = len(s) // 2
        # Search for the nearest space character to the middle
        left_space = s.rfind(' ', 0, middle_idx)  # search space to the left of the middle
        right_space = s.find(' ', middle_idx)  # search space to the right of the middle
        # Determine which space character is closer to the middle
        if left_space == -1:  # if there's no space to the left of the middle
            split_idx = right_space
        elif right_space == -1:  # if there's no space to the right of the middle
            split_idx = left_space
        else:
            # Choose the space that's closer to the middle
            split_idx = left_space if (middle_idx - left_space) < (right_space - middle_idx) else right_space
        # Split the string at the chosen space
        return [s[:split_idx], s[split_idx+1:]], False
    # If string doesn't need splitting
    return [s], False

def split_on_center_space(text):
    # If the length of the text is less than 10 or there's no space, return the text in a single-item list
    if len(text) < 10 or ' ' not in text:
        return [text]
    # Find the middle index of the string
    middle = len(text) // 2
    left_index = text.rfind(' ', 0, middle)  # Search for space going left from the middle
    right_index = text.find(' ', middle)     # Search for space going right from the middle
    # Determine the closest space to the middle to use as the split point
    # If no space to the left, use the right one; if both exist, choose the closest
    if left_index == -1 or (right_index != -1 and (middle - left_index) > (right_index - middle)):
        split_index = right_index
    else:
        split_index = left_index
    # Split the string into two parts
    part1 = text[:split_index]
    part2 = text[split_index+1:]  # +1 to exclude the space itself
    # Return the parts in a list
    return [part1, part2]

def draw_circle(draw, center, radius, fill):
    """Draws a circle on the ImageDraw object"""
    left_up_point = (center[0] - radius, center[1] - radius)
    right_down_point = (center[0] + radius, center[1] + radius)
    draw.ellipse([left_up_point, right_down_point], fill=fill)

def draw_icon(image, icon, x_current, y_current, max_height):
    # Scale the icon to fit the max_height while maintaining aspect ratio
    aspect_ratio = icon.width / icon.height
    scaled_height = max_height
    scaled_width = int(aspect_ratio * scaled_height)
    # Resize the icon using LANCZOS resampling
    icon = icon.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
    # Calculate the mean color of the icon
    stat = ImageStat.Stat(icon)
    mean_color = stat.mean[:3]  # Get the mean of the R, G, B channels
    # Determine if the color is close to white
    if all(x > 100 for x in mean_color):  # You can adjust the threshold value
        # Create a black image of the same size
        black_icon = Image.new('RGB', icon.size, color='black')
        # Use the alpha channel of the original icon to apply it to the black image
        black_icon.putalpha(icon.getchannel('A'))
        icon = black_icon
    # Get the coordinates for the icon's top-left corner
    icon_top_left = (x_current, y_current - (scaled_height // 2))  # Center vertically with the text
    # Paste the icon onto the image, using the alpha channel of the icon as the mask
    image.paste(icon, icon_top_left, mask=icon)
    # Return the new x position, which is to the right of the icon we just drew
    return x_current + scaled_width

def draw_markdown_text(image, bold_font, bold_font2, regular_font, regular_font_italic, title, text_body, color, y_top, x_left, x_right, graphics_folder, padding=2):
    # Initialize the drawing context
    draw = ImageDraw.Draw(image)
    
    # Draw the title using the bold font
    draw.text((x_left, y_top), title.strip().replace('\u202f', ''), font=bold_font, fill=color)
    
    # Get title height and update y-coordinate for text body
    title_bbox = draw.textbbox((x_left, y_top), title.strip(), font=bold_font)
    title_height = title_bbox[3] - title_bbox[1]
    y_current = y_top + title_height + int(padding * 2)
    
    # Define line height using the regular font
    max_height = draw.textbbox((0, 0), 'Hy', font=regular_font)[3]  # 'Hy' for descenders and ascenders

    text_body = text_body.replace('\u202f', '').replace('**.','.**').replace('*.','.*')
    # Split the text body by lines
    lines = [x.strip() for x in text_body.split('\n')]

    # Function to handle the drawing of text parts with the appropriate style
    def draw_text_part(draw, x_current, y_current, word, font, fill):
        word += ' '  # Add space after each word for separation
        bbox = draw.textbbox((x_current, y_current), word, font=font)
        width = bbox[2] - bbox[0]
        if x_current + width > x_right:
            # If the word exceeds the line, move to the next line
            x_current = x_left
            y_current += max_height + padding
        draw.text((x_current, y_current), word, font=font, fill=fill)
        return x_current + width, y_current

    for line in lines:
        # Initialize x-coordinate for line
        x_current = x_left

        # Check for markdown bold and italic syntax
        bold_parts = line.split('**')
        for b, bold_part in enumerate(bold_parts):
            if b % 2 == 1:
                # This part is bold
                font = bold_font2
            else:
                font = regular_font  # Reset to regular font for non-bold parts

            # Split the part into italic parts and draw each one
            italic_parts = bold_part.split('*')
            for i, italic_part in enumerate(italic_parts):
                if i % 2 == 1:
                    # This part is italic
                    font = regular_font_italic
                else:
                    font = bold_font2 if b % 2 == 1 else regular_font

                words = italic_part.split(' ')
                for word in words:
                    if '[' in word and ']' in word:
                        # Handle icons in text
                        icon_key = word.split('[')[1].split(']')[0]
                        word = word.split('[')[0]
                        # Draw the word before the icon
                        x_current, y_current = draw_text_part(draw, x_current, y_current, word, font, "black")
                        # Load and draw the icon
                        icon = Image.open(f"{graphics_folder}/{icon_key}.png").convert('RGBA')
                        if icon:
                            x_current = draw_icon(image, icon, x_current, y_current+14, max_height+18)
                        continue  # Skip the rest of the loop and don't draw this word as text
                    # Draw the word
                    x_current, y_current = draw_text_part(draw, x_current, y_current, word, font, "black")
        # After a line is processed, move to the next line
        y_current += max_height + padding + 100
    return image, y_current

def draw_markdown_text_centerv2(image, bold_font, bold_font2, regular_font, regular_font_italic, title, text_body, color, y_top, x_left, x_right, graphics_folder, padding=2):
    # Initialize the drawing context
    draw = ImageDraw.Draw(image)
    draw.text((x_left, y_top), title.strip(), font=bold_font, fill=color)
    # Define line height using the tallest font (usually the bold one) for consistency
    max_height = max(draw.textbbox((0, 0), 'Hy', font=font)[3] for font in [bold_font, bold_font2, regular_font, regular_font_italic])
    # Calculate the y-coordinate for the text body
    y_current = y_top + max_height + padding
    # Split the text body by lines
    lines = [x.strip() for x in text_body.split('\n')]
    for line in lines:
        words_and_icons = re.findall(r'\*\*.*?\*\*|\*.*?\*|\[.*?\]|\S+', line)
        x_current = x_left
        for word_or_icon in words_and_icons:
            # Strip markdown symbols for width calculation
            stripped_word = word_or_icon.strip('[]*')
            word_width = draw.textlength(stripped_word, font=regular_font) + padding
            # Check for line width overflow and wrap to the next line
            if x_current + word_width > x_right:
                y_current += max_height + padding  # Move to next line
                x_current = x_left  # Reset to left bound
            if word_or_icon.startswith('[') and word_or_icon.endswith(']'):
                # Handle icons in text
                icon_key = word_or_icon.strip('[]')
                icon_path = f"{graphics_folder}/{icon_key}.png"
                icon = Image.open(icon_path).convert('RGBA')
                aspect_ratio = icon.width / icon.height
                new_width = int(aspect_ratio * max_height)
                icon = icon.resize((new_width, max_height), Image.Resampling.LANCZOS)
                stat = ImageStat.Stat(icon)
                mean_color = stat.mean[:3] 
                if all(x > 100 for x in mean_color):
                    black_icon = Image.new('RGB', icon.size, color='black')
                    black_icon.putalpha(icon.getchannel('A'))
                    icon = black_icon
                icon_x_center = x_current
                icon_y_center = int(y_current + (max_height - icon.height) // 2)
                image.paste(icon, (int(icon_x_center), int(icon_y_center)), icon)
                x_current += new_width
            else:
                # Determine the font for this segment of text
                if '**' in word_or_icon:
                    font = bold_font2
                    word_or_icon = word_or_icon.strip('*')
                elif '*' in word_or_icon:
                    font = regular_font_italic
                    word_or_icon = word_or_icon.strip('*')
                else:
                    font = regular_font
                # Draw the text
                draw.text((x_current, y_current), stripped_word, font=font, fill=color)
                x_current += word_width
        # After a line is processed, move to the next line
        y_current += max_height + padding
    return image, y_current

def CreateTextImage(draw, astring, max_height, FontObj, color, padding):
    line_width = draw.textlength(astring, font=FontObj)
    line_image = Image.new('RGBA', (int(line_width), int(max_height)), (255, 255, 255, 0))
    line_draw = ImageDraw.Draw(line_image)
    line_draw.text((0, int(padding/2)), astring, font=FontObj, fill=color)
    return line_image

def attackType(atkstring):
    atktype = "Melee"
    atkrange = False
    if atkstring.startswith("[RL]"):
        atktype = "Ranged"
        atkrange = "Long"
    elif atkstring.startswith("[R]"):
        atktype = "Ranged"
    elif atkstring.startswith("[RS]"):
        atktype = "Ranged"
        atkrange = "Short"
    return atktype, atkrange, atkstring.split(']')[1]

def MakeAttackBar(atktype, atkrange, atkText, atk_ranks, tohit, ArmyAttackAndAbilitiesBorderColor, units_folder, graphics_folder, AsoiafFonts):
    canvas = LayeredImageCanvas(350, 150)
    xoffset = -5
    yoffset = -210
    silver_attack_type_sword = Image.open(f"{units_folder}AttackTypeBg{ArmyAttackAndAbilitiesBorderColor}.webp").convert('RGBA')
    silver_attack_type_border = Image.open(f"{units_folder}AttackType.{atktype}{ArmyAttackAndAbilitiesBorderColor}.webp").convert('RGBA')
    width, height = [int(x*1.1) for x in silver_attack_type_border.size]
    silver_attack_type_border = silver_attack_type_border.resize((width, height))
    silver_attack_tan_background = Image.open(f"{units_folder}AttackBg{ArmyAttackAndAbilitiesBorderColor}.webp").convert('RGBA')
    silver_attack_dice_background = Image.open(f"{units_folder}DiceBg.webp").convert('RGBA')
    atk_stat_bg_image = Image.open(f"{units_folder}StatBg.webp").convert('RGBA')
    atkColor = "#001a53"
    if atkrange:
        atkColor = "#a71208" # dark red
        range_bg_image = Image.open(f"{graphics_folder}/Range{atkrange}{ArmyAttackAndAbilitiesBorderColor}.png").convert('RGBA')
        canvas.add_layer(range_bg_image, xoffset+90, yoffset+210, depth=4)
    #silver_attack_tan_background
    GBFont = AsoiafFonts.get('Tuff-Italic-30', ImageFont.load_default())
    text_lines_list = split_on_center_space(atkText.upper())
    draw = ImageDraw.Draw(silver_attack_tan_background)
    x,y = [int(x/2) for x in silver_attack_tan_background.size]
    draw_centered_text(draw, (x+10, y - 12), text_lines_list, GBFont, atkColor, line_padding=4)
    #draw.text((17, 17), atkText, font=GBFont, fill=atkColor)
    canvas.add_layer(silver_attack_tan_background, xoffset+60, yoffset+220, depth=0)
    canvas.add_layer(silver_attack_dice_background, xoffset+100, yoffset+293, depth=2)
    draw = ImageDraw.Draw(atk_stat_bg_image)
    GBFont = AsoiafFonts.get('Garamond-Bold',ImageFont.load_default())
    draw.text((17, 17), tohit, font=GBFont, fill="white")
    canvas.add_layer(atk_stat_bg_image, xoffset+83, yoffset+280, depth=3)
    canvas.add_layer(silver_attack_type_border, xoffset+8, yoffset+210, depth=2)
    canvas.add_layer(silver_attack_type_sword, xoffset+20, yoffset+220, depth=1)
    colors = [(74,124,41,240),(231,144,14,240),(207,10,10,240)]
    yoffset += 10
    xoffset += 65
    #Garamond-Bold
    GBSmallFont = AsoiafFonts.get('Garamond-Bold-35',ImageFont.load_default())
    for i in range(len(atk_ranks)):
        #  Image.new('RGBA', [160, 40], (255, 255, 255, 0))
        img = Image.new("RGBA", (34, 34), colors[i])
        draw = ImageDraw.Draw(img)
        draw.text((8, 1), atk_ranks[i], font=GBSmallFont, fill="white")
        canvas.add_layer( add_rounded_corners( img , 4) , xoffset+100, yoffset+293, depth=3)
        xoffset += 42
    return canvas.render()

def create_icon_image(graphics_folder, units_folder, icon_key, max_height, faction, AsoiafFonts):
    # './assets/graphics/ATTACK:Ranged:Ranged Volley:3+3.png'
    imgfound = True
    icon = False
    icon_path = f"{graphics_folder}/{icon_key}.png"
    if 'SKILL:' in icon_key:
        skill = icon_key.split(':')[1]
        border = "Gold"
        if faction in ArmyAttackAndAbilitiesBorderColors:
            border = ArmyAttackAndAbilitiesBorderColors[faction]
        icon_path = f"{units_folder}/Skill{skill}{border}.webp"
        max_height = 100
    if 'ATTACK:' in icon_key:
        # ATTACK:Ranged:Ranged Volley:3+3
        # ATTACK:Ranged:Ranged Volley:3+3,2,1
        # ATTACK:LongRanged:Hurl Boulder:3+1
        border = "Gold"
        if faction in ArmyAttackAndAbilitiesBorderColors:
            border = ArmyAttackAndAbilitiesBorderColors[faction]
        atkrange = False
        p1, atktype, atkText, p4 = icon_key.split(':')
        if atktype == "LongRanged":
            atkrange = "Long"
            atktype = "Ranged"
        elif atktype == "ShortRanged":
            atkrange = "Short"
            atktype = "Ranged"
        tohit, atk_ranks = p4.split('+')
        tohit += "+"
        atk_ranks = atk_ranks.split(',')
        icon = MakeAttackBar(atktype, atkrange, atkText, atk_ranks, tohit, border, units_folder, graphics_folder, AsoiafFonts)
        max_height = 120
    if not os.path.isfile(icon_path) and not icon:
        imgfound = False
        print(f"Invalid icon image {icon_path}")
        icon_path = f"{graphics_folder}/IconQuestion.png"
    if not icon:
        icon = Image.open(icon_path).convert('RGBA')
    aspect_ratio = icon.width / icon.height
    new_width = int(aspect_ratio * max_height)
    icon = icon.resize((new_width, max_height), Image.Resampling.LANCZOS)
    stat = ImageStat.Stat(icon)
    mean_color = stat.mean[:3] 
    if all(x > 100 for x in mean_color) or not imgfound:
        black_icon = Image.new('RGB', icon.size, color='black')
        black_icon.putalpha(icon.getchannel('A'))
        icon = black_icon
    return icon, new_width

def insert_space_before_brackets(text):
    return re.sub(r'(\S)\[', r'\1 [', text)

def insert_padding_line_before_large_icon(text):
    return re.sub(r'\[(ATTACK|SKILL)(.+?)\]', r'\n[\1\2]\n', text)

def wrap_markdown_individual_words(text_body):
    def mark_indexes(text, marker):
        # Find all indexes of standalone markers
        if marker == '*':
            indexes = [m.start() for m in re.finditer(r'(?<!\*)\*(?!\*)', text)]
        elif marker == '**':
            indexes = [m.start() for m in re.finditer(r'(?<!\*)\*\*(?!\*)', text)]
        return indexes

    def wrap_text(text, indexes, marker):
        new_text = ''
        last_index = 0
        for start, end in zip(indexes[::2], indexes[1::2]):
            # Add the text before the marker
            new_text += text[last_index:start]
            # Wrap the words in the marked section
            marked_section = text[start + len(marker):end]
            # Split by words and preserve newlines
            wrapped_section = ''.join([f'{marker}{word}{marker}' if word.strip() else word
                                    for word in re.split(r'(\s+)', marked_section)])
            new_text += wrapped_section
            last_index = end + len(marker)
        # Add the remaining part of the text
        new_text += text[last_index:]
        return new_text
    # Process for italic
    italic_indexes = mark_indexes(text_body, '*')
    text_body = wrap_text(text_body, italic_indexes, '*')

    # Process for bold
    bold_indexes = mark_indexes(text_body, '**')
    text_body = wrap_text(text_body, bold_indexes, '**')
    return text_body

def insert_space_before_after_brackets(text):
    # Insert a space before '[' if it is preceded by a non-space character
    text = re.sub(r'(\S)\[', r'\1 [', text)
    # Insert a space after ']' if it is followed by a non-space character
    text = re.sub(r'\](\S)', r'] \1', text)
    return text

def draw_markdown_text_centerv3(image, bold_font, bold_font2, regular_font, regular_font_italic, title, text_body, color, y_top, x_left, x_right, graphics_folder, units_folder, faction, AsoiafFonts, padding=2):
    all_image_lines = []
    title = title.strip()
    draw = ImageDraw.Draw(image)
    title_length = draw.textlength(title, font=bold_font)
    # Define line height using the tallest font (usually the bold one) for consistency
    max_height = max(draw.textbbox((0, 0), 'Hy', font=font)[3] for font in [bold_font, bold_font2, regular_font, regular_font_italic])
    # Calculate the y-coordinate for the text body
    y_current = y_top + 10
    if title_length + x_left > x_right:
        title_line1, title_line2 = split_on_center_space(title)
        line_image = CreateTextImage(draw, title_line1, max_height, bold_font, color, padding)
        all_image_lines.append( {'img':line_image,'y':y_current, 'x':x_left} )
        y_current += max_height + padding
        line_image = CreateTextImage(draw, title_line2, max_height, bold_font, color, padding)
        all_image_lines.append( {'img':line_image,'y':y_current, 'x':x_left} )
    else:
        line_image = CreateTextImage(draw, title, max_height, bold_font, color, padding)
        all_image_lines.append( {'img':line_image,'y':y_top, 'x':x_left} )
    y_current += max_height + padding + 10
    #image.paste(line_image, (x_left, y_top), line_image)
    middle_x = (x_right + x_left) / 2
    # Split the text body by lines
    text_body = text_body.replace('**.','.**').replace('*.','.*')
    text_body = text_body.replace(' :',':')
    text_body = text_body.replace('**:',':**').replace('*:',':*')
    text_body = '\n'.join([x.strip() for x in text_body.split('\n') if x.strip() != ''])
    text_body = insert_space_before_after_brackets(text_body)
    text_body = insert_padding_line_before_large_icon(text_body)
    text_body = wrap_markdown_individual_words(text_body)
    text_body = text_body.replace('*[','[').replace('*[','[').replace(']*',']').replace(']*',']').replace('  ',' ')
    lines = [x.strip() for x in text_body.split('\n')]
    for line in lines:
        words_and_icons = re.findall(r'\*\*.*?\*\*|\*.*?\*|\[.*?\]|\S+', line)
        x_current = x_left
        for word_or_icon in words_and_icons:
            # Strip markdown symbols for width calculation
            if '**' in word_or_icon:
                font = bold_font2
                word_or_icon = word_or_icon.replace('*','')
                for subword in [x.strip() for x in word_or_icon.split(' ') if x.strip() != '']:
                    word_width = draw.textlength(subword, font=font)
                    if x_current + word_width > x_right:
                        y_current += max_height + padding  # Move to next line
                        x_current = x_left  # Reset to left bound
                    if subword.startswith('[') and subword.endswith(']'):
                        # Handle icons in text
                        icon_key = subword.strip('[]')
                        icon, new_width = create_icon_image(graphics_folder, units_folder, icon_key, max_height, faction, AsoiafFonts)
                        icon_x_center = x_current
                        icon_y_center = int(y_current + (max_height - icon.height) // 2)
                        #image.paste(icon, (int(icon_x_center), int(icon_y_center)), icon)
                        all_image_lines.append( {'img':icon,'y':int(icon_y_center), 'x':int(icon_x_center)} )
                        x_current += new_width
                    else:
                        line_image = CreateTextImage(draw, f"{subword} ", max_height, font, "#545454", padding)
                        all_image_lines.append( {'img':line_image,'y':y_current, 'x':x_current} )
                        x_current += word_width
            elif '*' in word_or_icon:
                font = regular_font_italic
                word_or_icon = word_or_icon.replace('*','')
                for subword in [x.strip() for x in word_or_icon.split(' ') if x.strip() != '']:
                    word_width = draw.textlength(subword, font=font)
                    if x_current + word_width > x_right:
                        y_current += max_height + padding  # Move to next line
                        x_current = x_left  # Reset to left bound
                    if subword.startswith('[') and subword.endswith(']'):
                        # Handle icons in text
                        icon_key = subword.strip('[]')
                        icon, new_width = create_icon_image(graphics_folder, units_folder, icon_key, max_height, faction, AsoiafFonts)
                        icon_x_center = x_current
                        icon_y_center = int(y_current + (max_height - icon.height) // 2)
                        #image.paste(icon, (int(icon_x_center), int(icon_y_center)), icon)
                        all_image_lines.append( {'img':icon,'y':int(icon_y_center), 'x':int(icon_x_center)} )
                        x_current += new_width
                    else:
                        line_image = CreateTextImage(draw, f"{subword} ", max_height, font, "#545454", padding)
                        all_image_lines.append( {'img':line_image,'y':y_current, 'x':x_current} )
                        x_current += word_width
            else:
                stripped_word = word_or_icon.strip('[]*')
                word_width = draw.textlength(stripped_word, font=regular_font) + padding
                # Check for line width overflow and wrap to the next line
                if x_current + word_width > x_right:
                    y_current += max_height + padding  # Move to next line
                    x_current = x_left  # Reset to left bound
                if word_or_icon.startswith('[') and word_or_icon.endswith(']'):
                    # Handle icons in text
                    icon_key = word_or_icon.strip('[]')
                    icon, new_width = create_icon_image(graphics_folder, units_folder, icon_key, max_height, faction, AsoiafFonts)
                    icon_x_center = x_current
                    icon_y_center = int(y_current + (max_height - icon.height) // 2)
                    #image.paste(icon, (int(icon_x_center), int(icon_y_center)), icon)
                    all_image_lines.append( {'img':icon,'y':int(icon_y_center), 'x':int(icon_x_center)} )
                    x_current += new_width
                else:
                    font = regular_font
                    line_image = CreateTextImage(draw, f"{stripped_word} ", max_height, font, "#545454", padding)
                    all_image_lines.append( {'img':line_image,'y':y_current, 'x':x_current} )
                    x_current += word_width
        # After a line is processed, move to the next line
        y_current += max_height + padding + 15
    # First, group all images by their y-coordinate
    lines_by_y = defaultdict(list)
    for img_dict in all_image_lines:
        lines_by_y[img_dict['y']].append(img_dict)
    # Now iterate over each line and center-align the words
    middle_x = (x_right + x_left) / 2
    for y, line_images in lines_by_y.items():
        # Calculate the total width of the line
        total_line_width = sum(img_dict['img'].width for img_dict in line_images)
        # Calculate the starting x-coordinate for the line
        line_start_x = middle_x - (total_line_width // 2)
        # Paste each image, offsetting each one to the right of the previous
        current_x = line_start_x
        for img_dict in line_images:
            img = img_dict['img']
            # Paste the image onto the background image
            image.paste(img, (int(current_x), int(y)), img)
            # Update the current x-coordinate
            current_x += img.width
    return image, y_current



class LayeredImageCanvas:

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.layers = []

    def add_layer(self, image, x, y, depth):
        self.layers.append({
            'image': image,
            'x': x,
            'y': y,
            'depth': depth
        })
        # Sort layers by depth so that higher depth layers are rendered last (on top)
        self.layers.sort(key=lambda layer: layer['depth'])

    def render(self):
        # Create a blank canvas
        canvas = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        for layer in self.layers:
            canvas.paste(layer['image'], (layer['x'], layer['y']), layer['image'])
        return canvas

def make_bottom_transparent(image, rows):
    # Check if the image has an alpha channel, if not, add one
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    # Load the alpha channel (mask) of the image
    alpha = image.split()[3]
    # Create a new alpha channel with the same size as the original image, fully opaque
    new_alpha = Image.new('L', image.size, 255)
    # Process the bottom 20 rows
    for y in range(image.height - rows, image.height):
        for x in range(image.size[0]):
            new_alpha.putpixel((x, y), 0)
    # Put the new alpha channel back into the image
    image.putalpha(new_alpha)
    return image

def crop_transparent_edges(image):
    # Ensure image has an alpha channel
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    # Get the alpha channel of the image
    alpha = image.split()[-1]
    # Get the bounding box of the non-zero regions in the alpha channel
    bbox = alpha.getbbox()
    # If the image is completely transparent, return the original image
    if bbox is None:
        return image
    # Crop the image with the bounding box
    cropped_image = image.crop(bbox)
    return cropped_image

def add_background_to_image(original_image, faction):
    faction_color = False
    if faction in FactionColors:
        faction_color = FactionColors[faction]
    # Set default background color to transparent if faction_color is None or False
    background_color = (0, 0, 0, 0) if not faction_color else faction_color
    # Create a new image with the same size as the original and the specified background color
    new_image = Image.new("RGBA", original_image.size, background_color)
    # Since the original image may have transparency, we use it as the mask for itself
    new_image.paste(original_image, (0, 0), original_image)
    return new_image

def generate_ncu_bar(hor_bar1, hor_large_bar):
    # Step 1 & 2
    first_new_image_height = int(hor_large_bar.height * 1.5)
    first_new_image = Image.new('RGBA', (hor_large_bar.width, first_new_image_height))
    first_new_image.paste(hor_large_bar, (0, 0))
    first_new_image.paste(hor_large_bar, (0, hor_large_bar.height))

    # Step 3 to 6
    second_new_image_height = first_new_image_height + hor_bar1.height
    second_new_image = Image.new('RGBA', (hor_large_bar.width, second_new_image_height))

    # Center the first new image vertically on the second new image
    offset_y = (second_new_image_height - first_new_image_height) // 2
    second_new_image.paste(first_new_image, (0, offset_y))

    # Paste hor_bar1 at the top and bottom
    second_new_image.paste(hor_bar1, (0, 0))
    second_new_image.paste(hor_bar1, (0, second_new_image_height - hor_bar1.height))

    # Calculate the positions for the additional hor_large_bar images
    third_bar_position = int(second_new_image_height * 0.333)
    sixth_bar_position = int(second_new_image_height * 0.666)

    second_new_image.paste(hor_bar1, (0, third_bar_position - hor_bar1.height // 2))
    second_new_image.paste(hor_bar1, (0, sixth_bar_position - hor_bar1.height // 2))
    return second_new_image


def BuildNcuCardFactionWithData(NcuData, units_folder, attachments_folder, graphics_folder, tactics_folder, AsoiafFonts, AsoiafData, ncus_folder, lang, AsoiafDataTranslations):
    print(f"Creating {NcuData['Name']}")
    # {'Faction': 'Neutral', 'Name': 'Lord Varys, The Spider', 'Character': 'Lord Varys', 'Cost': '4', 'Names': 'Little Birds', 'Descriptions': 
    # 'Varys begins the iendly unit.\n[SWORDS]: 1 enemy suffers 3 Hits.\n[LETTER]: Draw 1 Tactics card.\n[HORSE]: 1 friendly unit shifts 3".', 
    # 'Requirements': '', 'Boxes': 'SIF505', 'Id': '30403', 'Version': '2021-S03', 'Quote': '"Varys has ."', 'Restrictions': ''}
    #pdb.set_trace()
    faction = NcuData['Faction']
    faction_text_clean = re.sub(r'[^A-Za-z]', '', faction)
    NcuId = NcuData['Id']
    faction_crest = False
    scaled_faction_crest = False
    if f"{faction_text_clean}".strip() != "":
        faction_crest = Image.open(f"{tactics_folder}Crest{faction_text_clean}.webp").convert('RGBA').rotate(-11, expand=True)
        width, height = [int(x*0.63) for x in faction_crest.size]
        scaled_faction_crest = faction_crest.resize((width, height))
    ncu_faction_bg_image = Image.open(f"{tactics_folder}Bg_{faction_text_clean}.jpg").convert('RGBA')

    translated_ncu_data = False
    if AsoiafDataTranslations:
        translated_ncu_data = [x for x in AsoiafDataTranslations["ncus"] if x['Id'].strip() == NcuData['Id'].strip()][0]

    FactionColor = "#7FDBFF" 
    if faction in FactionColors:
        FactionColor = FactionColors[faction]
    #ArmyAttackAndAbilitiesBorderColor = "Gold"
    #if faction in ArmyAttackAndAbilitiesBorderColors:
    #    ArmyAttackAndAbilitiesBorderColor = ArmyAttackAndAbilitiesBorderColors[faction]
    canvas = LayeredImageCanvas(ncu_faction_bg_image.size[0], ncu_faction_bg_image.size[1])

    vert_bar1 = Image.open(f"{attachments_folder}Bar{faction_text_clean}.webp").convert('RGBA').rotate(90, expand=True)
    vert_bar2 = vert_bar1.copy()
    vert_bar3 = vert_bar1.copy()
    hor_large_bar = Image.open(f"{units_folder}LargeBar{faction_text_clean}.webp").convert('RGBA')
    hor_bar1 = Image.open(f"{attachments_folder}Bar{faction_text_clean}.webp").convert('RGBA')
    hor_bar2 = hor_bar1.copy()
    hor_bar3 = hor_bar1.copy()
    hor_bar4 = hor_bar1.copy()
    ncu_portrait = Image.open(f"{ncus_folder}{NcuId}.jpg").convert('RGBA').resize((273, 312))
    UnitTypeNcuForFactionImage = Image.open(f"{ncus_folder}UnitTypeNCU{faction_text_clean}.webp").convert('RGBA') 
    width, height = [int(x*0.98) for x in UnitTypeNcuForFactionImage.size]
    UnitTypeNcuForFactionImage = UnitTypeNcuForFactionImage.resize((width, height))
    UnitTypeNcuForFactionImage = UnitTypeNcuForFactionImage.crop((0,10,UnitTypeNcuForFactionImage.size[0],UnitTypeNcuForFactionImage.size[1]))
    #We'll add these in from left to right from top to bottom
    DecorStar1 = Image.open(f"{tactics_folder}Decor{faction_text_clean}.webp").convert('RGBA')
    DecorStar2 = DecorStar1.copy()
    DecorStar3 = DecorStar1.copy()
    DecorStar4 = DecorStar1.copy()
    DecorStar5 = DecorStar1.copy()
    DecorStar6 = DecorStar1.copy()
    DecorStar7 = DecorStar1.copy()
    DecorStar8 = DecorStar1.copy()
    DecorStar9 = DecorStar1.copy()
    DecorStar10 = DecorStar1.copy()
    DecorStar11 = DecorStar1.copy()
    DecorStar12 = DecorStar1.copy()
    tan_background_for_text = Image.open(f"{units_folder}SkillsBg.webp").convert('RGBA')
    #SkillDivider = Image.open(f"{units_folder}Divider{faction_text_clean}.webp").convert('RGBA')
    #SkillDivider = SkillDivider.crop((0,0, tan_background_for_text.size[0],SkillDivider.size[1]))
    hor_natticed_bar_below_portrait = generate_ncu_bar(hor_bar1, hor_large_bar)

    left_right_top_offset = 40
    top_to_bottom_border_height = ncu_faction_bg_image.size[1] - int(left_right_top_offset * 2)
    left_to_right_border_width = ncu_faction_bg_image.size[0] - int(left_right_top_offset * 2)
    

    vert_bar1 = vert_bar1.crop( (0, 0, vert_bar1.size[0], top_to_bottom_border_height) )
    vert_bar2 = vert_bar2.crop( (0, 0, vert_bar2.size[0], top_to_bottom_border_height) )
    vert_bar3 = vert_bar3.crop( (0, 0, vert_bar3.size[0], ncu_portrait.size[1]) )
    hor_bar1 = hor_bar1.crop((0, 0, left_to_right_border_width, hor_bar1.size[1]))
    hor_bar2 = hor_bar2.crop((0, 0, left_to_right_border_width, hor_bar2.size[1]))
    hor_bar3 = hor_bar3.crop((0, 0, left_to_right_border_width, hor_bar3.size[1]))

    hor_natticed_bar_below_portrait = hor_natticed_bar_below_portrait.crop((0,0, left_to_right_border_width - ncu_portrait.size[0], hor_natticed_bar_below_portrait.size[1]))
    hor_bar4 = hor_bar4.crop((0, 0, hor_natticed_bar_below_portrait.size[0], hor_bar3.size[1]))

    half_height_width = int(hor_bar1.size[1]/2)
    canvas.add_layer(ncu_faction_bg_image, 0, 0, depth=0)
    canvas.add_layer(ncu_portrait, left_right_top_offset, left_right_top_offset, depth=0)
    xoff = left_right_top_offset+ ncu_portrait.size[0]
    yoff = left_right_top_offset+ncu_portrait.size[1]-hor_natticed_bar_below_portrait.size[1]+half_height_width
    canvas.add_layer(hor_natticed_bar_below_portrait, xoff, yoff, depth=1)
    canvas.add_layer(UnitTypeNcuForFactionImage, xoff+half_height_width, yoff, depth=2)
    if scaled_faction_crest:
        canvas.add_layer(scaled_faction_crest, ncu_faction_bg_image.size[0]-left_right_top_offset-scaled_faction_crest.size[0]+2, yoff- (half_height_width*2), depth=4)
    canvas.add_layer(hor_bar4, xoff, yoff, depth=3)

    canvas.add_layer(vert_bar1, left_right_top_offset-half_height_width, left_right_top_offset, depth=1)
    canvas.add_layer(vert_bar2, ncu_faction_bg_image.size[0]-half_height_width-left_right_top_offset, left_right_top_offset, depth=1)
    canvas.add_layer(vert_bar3, left_right_top_offset+ncu_portrait.size[0]-half_height_width, left_right_top_offset, depth=1)

    canvas.add_layer(hor_bar1, left_right_top_offset, left_right_top_offset, depth=1)
    canvas.add_layer(hor_bar2, left_right_top_offset, left_right_top_offset+ncu_portrait.size[1]-half_height_width, depth=1)
    canvas.add_layer(hor_bar3, left_right_top_offset, ncu_faction_bg_image.size[1] - left_right_top_offset - half_height_width, depth=1)
    
    decorOffset = int(DecorStar1.size[0]/2)

    SkillDivider = Image.new('RGBA', (left_to_right_border_width+DecorStar1.size[0], DecorStar1.size[1]), (255, 255, 255, 0))
    SkillDivider.paste(hor_bar1, (decorOffset, decorOffset-half_height_width), hor_bar1)
    SkillDivider.paste(DecorStar1, (0, 0), DecorStar1)
    SkillDivider.paste(DecorStar1, (left_to_right_border_width, 0), DecorStar1)

    xoff = left_right_top_offset-decorOffset
    yoff = left_right_top_offset-decorOffset+half_height_width
    canvas.add_layer(DecorStar1, xoff, yoff, depth=5)
    canvas.add_layer(DecorStar5, xoff, yoff + int(ncu_portrait.size[1]/2)-half_height_width, depth=5)
    top_left_coords = [xoff+0, yoff + ncu_portrait.size[1]-half_height_width]
    canvas.add_layer(DecorStar7, top_left_coords[0], top_left_coords[1], depth=5)
    canvas.add_layer(DecorStar9, xoff+left_to_right_border_width, yoff, depth=5)
    top_right_coords = [xoff+left_to_right_border_width, yoff+ncu_portrait.size[1]-half_height_width]
    canvas.add_layer(DecorStar10, top_right_coords[0], top_right_coords[1], depth=5)
    xoff += ncu_portrait.size[0]
    canvas.add_layer(DecorStar2, xoff, yoff, depth=5)
    canvas.add_layer(DecorStar6, xoff, yoff + int(ncu_portrait.size[1]/2)-half_height_width, depth=5)
    canvas.add_layer(DecorStar8, xoff, yoff + ncu_portrait.size[1]-half_height_width, depth=5)
    
    xoff -= int(ncu_portrait.size[0]/2)
    canvas.add_layer(DecorStar3, xoff, yoff, depth=5)
    canvas.add_layer(DecorStar4, xoff, yoff + ncu_portrait.size[1]-half_height_width, depth=5)
    bottom_left_coords = [left_right_top_offset-decorOffset, left_right_top_offset + top_to_bottom_border_height-decorOffset]
    canvas.add_layer(DecorStar11, bottom_left_coords[0], bottom_left_coords[1], depth=5)
    bottom_right_coords = [left_right_top_offset-decorOffset+left_to_right_border_width, left_right_top_offset + top_to_bottom_border_height-decorOffset]
    canvas.add_layer(DecorStar12, bottom_right_coords[0], bottom_right_coords[1], depth=5)

    # Calculate the width and height based on the coordinates
    target_width = top_right_coords[0] - top_left_coords[0]  # Assuming top_right and top_left have the same 'y' value
    target_height = bottom_left_coords[1] - top_left_coords[1] 
    tan_background_for_text = tan_background_for_text.resize((target_width, target_height), Image.Resampling.LANCZOS)
    canvas.add_layer(tan_background_for_text, top_left_coords[0]+decorOffset, top_left_coords[1]+decorOffset, depth=0)
    #return canvas.render()
    ncu_card = canvas.render()
    GBFont = AsoiafFonts.get('Tuff-Bold-40',ImageFont.load_default())
    TN = AsoiafFonts.get('Tuff-Bold-40',ImageFont.load_default())
    TN30 = AsoiafFonts.get('Tuff-Normal-34',ImageFont.load_default())
    TN30I = AsoiafFonts.get('Tuff-Italic-34',ImageFont.load_default())
    
    descriptions_names = [x.strip() for x in NcuData['Names'].strip().split('/') if not any([x.strip().startswith("Loyalty:"), x.strip().startswith("Rules:")]) ]
    descriptions = [x.strip() for x in NcuData['Descriptions'].strip().split('/')]
    if (len(descriptions_names) >= 2 and len(NcuData['Descriptions']) > 300) or len(NcuData['Descriptions']) > 380:
        # Some cards had a bunch of text on them
        GBFont = AsoiafFonts.get('Tuff-Bold-36',ImageFont.load_default())
        TN = AsoiafFonts.get('Tuff-Bold-36',ImageFont.load_default())
        TN30 = AsoiafFonts.get('Tuff-Normal-31',ImageFont.load_default())
        TN30I = AsoiafFonts.get('Tuff-Italic-31',ImageFont.load_default())
        if lang == 'fr':
            GBFont = AsoiafFonts.get('Tuff-Bold-36',ImageFont.load_default())
            TN = AsoiafFonts.get('Tuff-Bold-36',ImageFont.load_default())
            TN30 = AsoiafFonts.get('Tuff-Normal-31',ImageFont.load_default())
            TN30I = AsoiafFonts.get('Tuff-Italic-31',ImageFont.load_default())
        if lang == 'de':
            GBFont = AsoiafFonts.get('Tuff-Bold-34',ImageFont.load_default())
            TN = AsoiafFonts.get('Tuff-Bold-34',ImageFont.load_default())
            TN30 = AsoiafFonts.get('Tuff-Normal-31',ImageFont.load_default())
            TN30I = AsoiafFonts.get('Tuff-Italic-31',ImageFont.load_default())
    textBoundLeft = 98
    textBoundRight = 650
    yAbilityOffset = 385
    dividerYPadding = 0
    dividerOffset = 20
    def addDivider(x, y):
        div = SkillDivider.copy()
        ncu_card.paste(div, (x, y+dividerYPadding), div)
        return div.size[1] + dividerOffset + int(dividerYPadding/2)
    for i in range(len(descriptions_names)):
        nm = descriptions_names[i]
        ds = descriptions[i]

        translated_ability_dict = False
        if AsoiafDataTranslations:
            try:
                translated_ability_dict = [x for x in AsoiafDataTranslations["newskills"] if x['Original Name'].strip().lower() == nm.strip().lower()][0]
            except Exception as e:
                print(f"ERROR FINDING SKILL: {str(e)}")

        ability_name = nm.upper()
        if translated_ability_dict:
            ability_name = translated_ability_dict['Translated Name'].upper()
            ds = [x.strip() for x in translated_ability_dict['Translated Description'].strip().split('/')][0]
            if (len(ds) > 450 and lang in ["fr","de"]) or (len(ds) > 220 and lang in ["de"] and len(descriptions_names) >=2):
                GBFont = AsoiafFonts.get('Tuff-Bold-34',ImageFont.load_default())
                TN = AsoiafFonts.get('Tuff-Bold-34',ImageFont.load_default())
                TN30 = AsoiafFonts.get('Tuff-Normal-31',ImageFont.load_default())
                TN30I = AsoiafFonts.get('Tuff-Italic-31',ImageFont.load_default())
        if not translated_ability_dict and i + 1 == len(descriptions_names) and len(descriptions_names) != len(descriptions):
            ds = "\n".join( descriptions[i:] )
        #if translated_ncu_data:
        #    ability_name = translated_ncu_data
        if len(ability_name) > 32:
            GBFont = AsoiafFonts.get('Tuff-Bold-34',ImageFont.load_default())
            TN = AsoiafFonts.get('Tuff-Bold-34',ImageFont.load_default())
        ncu_card, yAbilityOffset = draw_markdown_text_centerv3(ncu_card, GBFont, TN, TN30, TN30I, ability_name, ds, FactionColor, yAbilityOffset-4, textBoundLeft, textBoundRight, graphics_folder, units_folder, faction, AsoiafFonts, padding=4)
        if i < len(descriptions_names)-1:
            yAbilityOffset += addDivider(left_right_top_offset-decorOffset, yAbilityOffset)
    draw = ImageDraw.Draw(ncu_card)
    TuffBoldFont = AsoiafFonts.get('Tuff-Bold-47', ImageFont.load_default()) 
    TuffBoldFontSmall = AsoiafFonts.get('Tuff-Bold-25', ImageFont.load_default())
    if lang in ['de','fr']:
        TuffBoldFont = AsoiafFonts.get('Tuff-Bold-44', ImageFont.load_default()) 
    ncu_name = NcuData['Name'].upper()
    if AsoiafDataTranslations:
        if 'Translated Name' in translated_ncu_data:
            ncu_name = translated_ncu_data['Translated Name'].upper()
        else:
            ncu_name = translated_ncu_data['Name2'].upper()
    nameOffsetX = -26
    nameOffsetY = 20
    if ',' in ncu_name:
        lines = ncu_name.split(',')
        text_lines_list, hadAComma = split_name_string(lines[0], amnt=11)
        text_lines_list2, hadAComma = split_name_string(lines[1], amnt=27)
        if len(text_lines_list) == 1:
            draw_centered_text(draw, (540+nameOffsetX, 100+nameOffsetY), [lines[0]], TuffBoldFont, "white", line_padding=10)
            if len(text_lines_list2) == 1:
                draw_centered_text(draw, (540+nameOffsetX, 104+nameOffsetY + TuffBoldFont.size ), [lines[1]], TuffBoldFontSmall, "white", line_padding=10)
            else:
                draw_centered_text(draw, (540+nameOffsetX, 104+nameOffsetY + TuffBoldFont.size ), [text_lines_list2[0]], TuffBoldFontSmall, "white", line_padding=10)
                draw_centered_text(draw, (540+nameOffsetX, 104+nameOffsetY + TuffBoldFont.size + TuffBoldFontSmall.size), [text_lines_list2[1]], TuffBoldFontSmall, "white", line_padding=10)
        else:
            draw_centered_text(draw, (540+nameOffsetX, 80+nameOffsetY), [text_lines_list[0]], TuffBoldFont, "white", line_padding=10)
            draw_centered_text(draw, (540+nameOffsetX, 80+nameOffsetY + TuffBoldFont.size), [text_lines_list[1]], TuffBoldFont, "white", line_padding=10)
            if len(text_lines_list2) == 1:
                draw_centered_text(draw, (540+nameOffsetX, 88+nameOffsetY + (TuffBoldFont.size*1) + TuffBoldFontSmall.size+2 ), [lines[1]], TuffBoldFontSmall, "white", line_padding=10)
            else:
                #draw_centered_text(draw, (540+nameOffsetX, 88+nameOffsetY + (TuffBoldFont.size*2) ), [lines[1]], TuffBoldFontSmall, "white", line_padding=10)
                draw_centered_text(draw, (540+nameOffsetX, 88+nameOffsetY + (TuffBoldFont.size*1) + TuffBoldFontSmall.size+2 ), [text_lines_list2[0]], TuffBoldFontSmall, "white", line_padding=10)
                draw_centered_text(draw, (540+nameOffsetX, 88+nameOffsetY + (TuffBoldFont.size*1) + (TuffBoldFontSmall.size*2)+2 ), [text_lines_list2[1]], TuffBoldFontSmall, "white", line_padding=10)
    else:
        text_lines_list, hadAComma = split_name_string(NcuData['Name'].upper(), amnt=11)
        if len(text_lines_list) == 1:
            draw_centered_text(draw, (540+nameOffsetX, 120+nameOffsetY), [text_lines_list[0]], TuffBoldFont, "white", line_padding=10)
        else:
            draw_centered_text(draw, (540+nameOffsetX, 100+nameOffsetY), [text_lines_list[0]], TuffBoldFont, "white", line_padding=10)
            draw_centered_text(draw, (540+nameOffsetX, 104+nameOffsetY + TuffBoldFont.size ), [text_lines_list[1]], TuffBoldFont, "white", line_padding=10)
    VersionFont = AsoiafFonts.get('Tuff-Italic-25', ImageFont.load_default())
    text_image = Image.new('RGBA', [160, 40], (255, 255, 255, 0))  # transparent background
    text_draw = ImageDraw.Draw(text_image)
    text_draw.text((0, 0), NcuData['Version'], font=VersionFont, fill="white")
    # Rotate the text image
    rotated_text_image = text_image.rotate(90, expand=1)
    # Paste the rotated text image onto your main image (consider using the alpha channel for proper transparency)
    ncu_card.paste(rotated_text_image, (rotated_text_image.width - 30, ncu_card.size[1] - rotated_text_image.height - 60), rotated_text_image)
    return ncu_card

def BuildNcuProfile(NcuData, ncus_folder):
    print(f"Creating {NcuData['Name']} Profile")
    # {'Faction': 'Neutral', 'Name': 'Lord Varys, The Spider', 'Character': 'Lord Varys', 'Cost': '4', 'Names': 'Little Birds', 'Descriptions': 
    # 'Varys begins the iendly unit.\n[SWORDS]: 1 enemy suffers 3 Hits.\n[LETTER]: Draw 1 Tactics card.\n[HORSE]: 1 friendly unit shifts 3".', 
    # 'Requirements': '', 'Boxes': 'SIF505', 'Id': '30403', 'Version': '2021-S03', 'Quote': '"Varys has ."', 'Restrictions': ''}
    #pdb.set_trace()
    NcuId = NcuData['Id']

    canvas = LayeredImageCanvas(273, 273)

    ncu_portrait = Image.open(f"{ncus_folder}{NcuId}.jpg").convert('RGBA').resize((273, 312))
    canvas.add_layer(ncu_portrait, 0, 0, depth=0)
    return canvas.render()


def main():
    lang = "en"
    if len(sys.argv) > 1:
        lang = sys.argv[1]
    # Currently, this assumes you are running it from the assets/flutter_assets folder
    assets_folder="./assets/"
    fonts_dir=f"./fonts/"
    AsoiafFonts = load_fonts(fonts_dir)
    data_folder=f"{assets_folder}data/"
    units_folder=f"{assets_folder}Units/"
    attachments_folder=f"{assets_folder}Attachments/"
    graphics_folder = f"{assets_folder}graphics"
    tactics_folder = f"{assets_folder}Tactics/"
    ncus_folder = f"{assets_folder}NCUs/"
    NcuCardsOutputDir  = f"./{lang}/ncucards/"
    warcouncil_latest_csv_folder = './warcouncil_latest_csv/'
    if not os.path.exists(NcuCardsOutputDir):
        Path(NcuCardsOutputDir).mkdir(parents=True, exist_ok=True)
    if not os.path.exists(NcuCardsOutputDir+"png/"):
        Path(NcuCardsOutputDir+"png/").mkdir(parents=True, exist_ok=True)
    if not os.path.exists(NcuCardsOutputDir+"jpg/"):
        Path(NcuCardsOutputDir+"jpg/").mkdir(parents=True, exist_ok=True)
    AsoiafData = import_csvs_to_dicts(data_folder) # contains the keys: attachments,boxes,ncus,newskills,rules,special,tactics,units
    AsoiafDataTranslations = False
    if lang != "en":
        AsoiafDataTranslations = import_csvs_to_dicts(warcouncil_latest_csv_folder, lang)
    #SelectedNcuCardData = [x for x in AsoiafData['ncus'] if x['Name'] == "Lord Varys, The Spider"][0]
    #SelectedNcuCardData = [x for x in AsoiafData['ncus'] if x['Name'] == "Othell Yarwyck, Warmachine Specialist"][0]
    #ncu_card = BuildNcuCardFactionWithData(SelectedNcuCardData, units_folder, attachments_folder, graphics_folder, tactics_folder, AsoiafFonts, AsoiafData, ncus_folder)
    for SelectedNcuCardData in AsoiafData['ncus']:
        is_any_value_true = any(bool(value) for value in SelectedNcuCardData.values()) # check for empty dicts
        if not is_any_value_true:
            continue
        ncu_card = BuildNcuCardFactionWithData(SelectedNcuCardData, units_folder, attachments_folder, graphics_folder, tactics_folder, AsoiafFonts, AsoiafData, ncus_folder, lang, AsoiafDataTranslations)
        ncu_card = add_rounded_corners(ncu_card, 20)
        ncu_card_output_path = os.path.join(NcuCardsOutputDir+"png/", f"{SelectedNcuCardData['Id'].replace(' ', '_')}f.png")
        ncu_card.save(ncu_card_output_path)
        ncu_card_output_path = os.path.join(NcuCardsOutputDir+"jpg/", f"{SelectedNcuCardData['Id'].replace(' ', '_')}f.jpg")
        ncu_card = ncu_card.convert("RGB")
        ncu_card.save(ncu_card_output_path)

    for SelectedNcuCardData in AsoiafData['ncus']:
        is_any_value_true = any(bool(value) for value in SelectedNcuCardData.values()) # check for empty dicts
        if not is_any_value_true:
            continue
        ncu_card = BuildNcuProfile(SelectedNcuCardData, ncus_folder)
        ncu_card_output_path = os.path.join(NcuCardsOutputDir+"png/", f"{SelectedNcuCardData['Id'].replace(' ', '_')}p.png")
        ncu_card.save(ncu_card_output_path)
        ncu_card_output_path = os.path.join(NcuCardsOutputDir+"jpg/", f"{SelectedNcuCardData['Id'].replace(' ', '_')}p.jpg")
        ncu_card = ncu_card.convert("RGB")
        ncu_card.save(ncu_card_output_path)

    # If You Want to View the Card AND click debug to find positioning uncommont these lines:
    #root = tk.Tk()
    #app = ImageEditor(root, ncu_card)
    #root.mainloop()


if __name__ == "__main__":
    main()
