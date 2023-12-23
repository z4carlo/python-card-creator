#!/usr/bin/env python
import csv
import os
import tkinter as tk
import pdb
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageStat
import sys
import re
from pathlib import Path


#pip install pillow

#ALLICONS = {
#CROWN
#HORSE
#LETTER
#LONGRANGE
#MONEY
#MOVEMENT
#OASIS
#SWORDS
#UNDYING
#WOUND
#}

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
    def __init__(self, master, unit_card_image):
        self.master = master
        master.title("Image Editor")

        self.unit_card_image = unit_card_image
        self.tk_image = ImageTk.PhotoImage(self.unit_card_image)
        
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

def BuildUnitCardFactionBackground(UnitData, units_folder, attachmentsfolder, graphics_folder):
    print(f"Creating {UnitData['Name']}")
    faction = UnitData['Faction'] # faction file names dont include spaces
    faction_text_clean = re.sub(r'[^A-Za-z]', '', faction)
    UnitType = UnitData['Type'].replace(' ','')
    # Images points of origin are always top-left most corner of the loaded image.
    unit_faction_bg_image = Image.open(f"{units_folder}UnitBg{faction_text_clean}.jpg").convert('RGBA')
    shadow_size = 4
    shadow_strength = 125

    # Left most bar
    top_left_red_gold_bar = crop_transparent_edges(Image.open(f"{attachmentsfolder}Bar{faction_text_clean}.webp").convert('RGBA'))
    large_bar = crop_transparent_edges(Image.open(f"{units_folder}LargeBar{faction_text_clean}.webp").convert('RGBA'))
    top_left_red_gold_bar = top_left_red_gold_bar.resize((1063, 16))
    large_bar = large_bar.resize((954, 85))
    #top_left_red_gold_bar  = add_background_to_image(top_left_red_gold_bar, faction)
    large_bar = add_background_to_image(large_bar, faction)
    #print(top_left_red_gold_bar.size, large_bar.size)
    # (1063, 16) (954, 85)
    next_red_gold_bar_below = top_left_red_gold_bar.copy()

    # Shield and Morale stuff
    shield_top_gold_bar = next_red_gold_bar_below.copy()
    shield_large_bar = large_bar.copy()
    shield_next_gold_bar = next_red_gold_bar_below.copy()

    #First Vertical Gold bar left of portrait
    # Have to rotate them
    left_onleft_vertical_gold_bar = next_red_gold_bar_below.copy().rotate(90, expand=True)
    large_onleft_vertical_gold_bar = large_bar.copy().rotate(90, expand=True)
    right_onleft_vertical_gold_bar = next_red_gold_bar_below.copy().rotate(90, expand=True)
    #Unit Type on bottom of the left side portrait gold bar

    # Unit Portrait Stuff
    left_bottom_gold_corner = Image.open(f"{units_folder}Corner{faction_text_clean}.webp").convert('RGBA')
    left_bottom_gold_corner = left_bottom_gold_corner.resize((229, 702))
    right_bottom_gold_corner = left_bottom_gold_corner.copy().transpose(Image.FLIP_LEFT_RIGHT)
    left_gold_corner_top = left_bottom_gold_corner.copy().transpose(Image.FLIP_TOP_BOTTOM)
    right_gold_corner = left_gold_corner_top.copy().transpose(Image.FLIP_LEFT_RIGHT)
    unit_portrait = crop_transparent_edges(Image.open(f"{units_folder}{UnitData['Id']}.jpg").convert('RGBA'))
    #unit_portrait = unit_portrait.resize((460, 707)) # There was some slight variation in the portrait size but this was the consistent size
    unit_portrait = unit_portrait.resize((468, 719))
    # Need to transparent the bottom part of the portrait so it doesnt go outside of bounds but keeps the same dimensions
    unit_portrait = make_bottom_transparent(unit_portrait, 64)
    portrait_attachment_on_middleof_trim = Image.open(f"{graphics_folder}/attachment{faction_text_clean}.png").convert('RGBA')
    faction_crest = Image.open(f"{units_folder}Crest{faction_text_clean}.webp").convert('RGBA')

    # Tan Skills Background:
    skills_tan_background_for_text = Image.open(f"{units_folder}SkillsBg.webp").convert('RGBA')

    # Gold bars to the right of the portrait:
    left_onright_vertical_gold_bar = left_onleft_vertical_gold_bar.copy()
    large_onright_vertical_gold_bar = large_onleft_vertical_gold_bar.copy()
    right_onright_vertical_gold_bar = right_onleft_vertical_gold_bar.copy()

    leftFirstVertBarXOffset = 190
    topBarYOffset = 60
    bottomBarYOffset = 600

    # Custom Canvas Class so I dont have to worry about layering in order
    canvas = LayeredImageCanvas(unit_faction_bg_image.size[0], unit_faction_bg_image.size[1])

    # Create our image to draw to
    unit_card = Image.new('RGBA', unit_faction_bg_image.size)
    #unit_card.paste(unit_faction_bg_image, (0, 0), unit_faction_bg_image) # background first
    canvas.add_layer(unit_faction_bg_image, 0, 0, depth=0)

    # Add Shadows To Objects
    top_left_red_gold_bar = add_shadow(top_left_red_gold_bar, shadow_size, shadow_strength, sides=('top', 'bottom')) # ('left', 'top', 'right', 'bottom')
    next_red_gold_bar_below = add_shadow(next_red_gold_bar_below, shadow_size, shadow_strength, sides=('top', 'bottom'))
    large_bar = add_shadow(large_bar, shadow_size, shadow_strength, sides=('top', 'bottom'))

    shield_large_bar = add_shadow(shield_large_bar, shadow_size, shadow_strength, sides=('top', 'bottom'))
    shield_top_gold_bar = add_shadow(shield_top_gold_bar, shadow_size, shadow_strength, sides=('top', 'bottom'))
    shield_next_gold_bar = add_shadow(shield_next_gold_bar, shadow_size, shadow_strength, sides=('top', 'bottom'))

    large_onleft_vertical_gold_bar = add_shadow(large_onleft_vertical_gold_bar, shadow_size, shadow_strength, sides=('left', 'right'))
    left_onleft_vertical_gold_bar = add_shadow(left_onleft_vertical_gold_bar, shadow_size, shadow_strength, sides=('left', 'right'))
    right_onleft_vertical_gold_bar = add_shadow(right_onleft_vertical_gold_bar, shadow_size, shadow_strength, sides=('left', 'right'))

    # Drawing Top Left Horozontal Gold Bar
    top_left_red_gold_bar = top_left_red_gold_bar.crop( (0, 0, leftFirstVertBarXOffset, top_left_red_gold_bar.size[1]) )
    next_red_gold_bar_below = next_red_gold_bar_below.crop( (0, 0, leftFirstVertBarXOffset, next_red_gold_bar_below.size[1]) )
    large_bar = large_bar.crop( (0, 0, leftFirstVertBarXOffset, large_bar.size[1]) )
    # After cropping, we draw
    yOffset = topBarYOffset+0
    canvas.add_layer(large_bar, 0, yOffset, depth=1)
    yOffset -= top_left_red_gold_bar.size[1] - (shadow_size*2)
    canvas.add_layer(top_left_red_gold_bar, 0, yOffset+4, depth=2)
    yOffset += large_bar.size[1] + top_left_red_gold_bar.size[1] - (shadow_size*4)
    canvas.add_layer(next_red_gold_bar_below, 0, yOffset-4, depth=2)
    yOffset -= large_bar.size[1]
    unit_card = add_rounded_corners(unit_card, 20)

    # Drawing Bottom Left Horo Gold Bar
    shield_large_bar = shield_large_bar.crop( (0, 0, leftFirstVertBarXOffset, shield_large_bar.size[1]) ) # (left, top, right, bottom)
    shield_top_gold_bar = shield_top_gold_bar.crop( (0, 0, leftFirstVertBarXOffset, shield_top_gold_bar.size[1]) )
    shield_next_gold_bar = shield_next_gold_bar.crop( (0, 0, leftFirstVertBarXOffset, shield_next_gold_bar.size[1]) )
    # After cropping, we draw
    yOffset = bottomBarYOffset+0
    xtraYOffset = 7
    canvas.add_layer(shield_large_bar, 0, yOffset+xtraYOffset, depth=1)
    yOffset -= shield_top_gold_bar.size[1] - (shadow_size*2)
    canvas.add_layer(shield_top_gold_bar, 0, yOffset+4+xtraYOffset, depth=2)
    yOffset += shield_large_bar.size[1] + shield_top_gold_bar.size[1] - (shadow_size*4)
    canvas.add_layer(shield_next_gold_bar, 0, yOffset-4+xtraYOffset, depth=2)

    # Draw First Vertical Gold bar left of portrait
    xOffset = leftFirstVertBarXOffset+(shadow_size*2)
    yOffset = 0
    canvas.add_layer(large_onleft_vertical_gold_bar, xOffset, yOffset, depth=1)
    xOffset -= left_onleft_vertical_gold_bar.size[0] - (shadow_size*2)
    canvas.add_layer(left_onleft_vertical_gold_bar, xOffset, yOffset, depth=2)
    xOffset += large_onleft_vertical_gold_bar.size[0] + left_onleft_vertical_gold_bar.size[0]
    num = int(large_onleft_vertical_gold_bar.size[0]/1.5)
    yOffset -= num
    canvas.add_layer(unit_portrait, xOffset-shadow_size - 4, yOffset + num, depth=0)
    xOffset -= (shadow_size*4)
    canvas.add_layer(right_onleft_vertical_gold_bar, xOffset, 0, depth=2)

    # Unit Portrait Stuff
    xOffset += (shadow_size*3)
    yOffset +=  unit_portrait.size[1]
    #unit_card.paste(left_bottom_gold_corner, (xOffset, yOffset), left_bottom_gold_corner)
    canvas.add_layer(left_bottom_gold_corner, xOffset, yOffset, depth=1)
    xOffset += left_bottom_gold_corner.size[0] + (shadow_size*1)
    canvas.add_layer(right_bottom_gold_corner, xOffset, yOffset, depth=1)
    frameYOffset = -46
    canvas.add_layer(right_gold_corner, xOffset, frameYOffset, depth=1)
    xOffset -= left_bottom_gold_corner.size[0] + (shadow_size*1)
    canvas.add_layer(left_gold_corner_top, xOffset, frameYOffset, depth=1)
    canvas.add_layer(portrait_attachment_on_middleof_trim, 510, 632, depth=2)
    width, height = [int(x*0.55) for x in faction_crest.size]
    faction_crest = faction_crest.rotate(-8)
    scaled_faction_crest = faction_crest.resize((width, height))
    canvas.add_layer(scaled_faction_crest, 610, 506, depth=3)
    #UnitData['Name']

    # Gold bars to the right of the portrait:
    left_onright_vertical_gold_bar = add_shadow(left_onright_vertical_gold_bar, shadow_size, shadow_strength, sides=('left', 'right'))
    large_onright_vertical_gold_bar = add_shadow(large_onright_vertical_gold_bar, shadow_size, shadow_strength, sides=('left', 'right'))
    right_onright_vertical_gold_bar = add_shadow(right_onright_vertical_gold_bar, shadow_size, shadow_strength, sides=('left', 'right'))
    canvas.add_layer(left_onright_vertical_gold_bar, 745, 0, depth=2)
    canvas.add_layer(large_onright_vertical_gold_bar, 745+(shadow_size*4), 0, depth=1)
    canvas.add_layer(right_onright_vertical_gold_bar, 825+(shadow_size*5), 0, depth=2)
    canvas.add_layer(skills_tan_background_for_text, 825+(shadow_size*6), 0, depth=1)

    #Foot Movement Placement
    movement_foot_image = Image.open(f"{units_folder}Movement.webp").convert('RGBA')
    movement_foot_stat_bg_image = Image.open(f"{units_folder}StatBg.webp").convert('RGBA')

    # Shield and Morale stuff
    shield_top_gold_bar = next_red_gold_bar_below.copy()
    shield_large_bar = large_bar.copy()
    shield_next_gold_bar = next_red_gold_bar_below.copy()
    shield_image = Image.open(f"{units_folder}Defense.webp").convert('RGBA')
    shield_stat_bg_image = movement_foot_stat_bg_image.copy()
    Morale_image = Image.open(f"{units_folder}Morale.webp").convert('RGBA')
    Morale_stat_bg_image = movement_foot_stat_bg_image.copy()

    # unit type
    unit_type_image = Image.open(f"{units_folder}UnitType.{UnitType}{faction_text_clean}.webp").convert('RGBA')

    canvas.add_layer(movement_foot_image, 56, 48, depth=4)
    canvas.add_layer(movement_foot_stat_bg_image, 156, 66, depth=3)

    canvas.add_layer(shield_image, 56, 595, depth=4)
    canvas.add_layer(shield_stat_bg_image, 156, 613, depth=3)
    xmore = 100
    canvas.add_layer(Morale_image, 156+xmore, 595, depth=4)
    canvas.add_layer(Morale_stat_bg_image, 256+xmore, 613, depth=3)
    canvas.add_layer(unit_type_image, 196, 665, depth=2)
    return canvas.render()

def split_name_string(s):
    # Split the string by comma if it exists
    if ',' in s:
        return s.split(','), True
    # Split the string if it's longer than 18 characters
    if len(s) > 15:
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

# Function to replace patterns with placeholders
def replace_with_placeholders(text, patterns):
    placeholders = {}
    for i, pattern in enumerate(patterns):
        matches = re.findall(pattern, text)
        for match in matches:
            placeholder = f"UNIQUE_PLACEHOLDER_{i}_{matches.index(match)}"
            placeholders[placeholder] = match
            text = text.replace(match, placeholder)
    # Replace newline characters with a unique placeholder
    text = text.replace('\n', 'UNIQUE_NEWLINE_PLACEHOLDER')
    return text, placeholders

# Function to restore patterns from placeholders
def restore_placeholders(text, placeholders):
    # Restore newline characters from the placeholder
    text = text.replace('UNIQUE_NEWLINE_PLACEHOLDER', '\n')
    for placeholder, original in placeholders.items():
        text = text.replace(placeholder, original)
    return text

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

def insert_padding_line_before_large_icon(text):
    return re.sub(r'\[(ATTACK|SKILL)(.+?)\]', r'\n[\1\2]\n', text)

def clean_up_colon(text):
    text = text.strip().replace('\u202f', '').replace('**:',':**').replace('*:',':*')
    while " : " in text:
        text = text.replace(' : ',':')
    while " :" in text:
        text = text.replace(' :',':')
    while "  " in text:
        text = text.replace('  ',' ')
    return text.replace('**:',':**').replace('*:',':*')

def draw_markdown_text(image, bold_font, bold_font2, regular_font, regular_font_italic, title, text_body, color, y_top, x_left, x_right, graphics_folder, lang, padding=2):
    # Initialize the drawing context
    draw = ImageDraw.Draw(image)
    title = clean_up_colon(title)
    # Draw the title using the bold font
    draw.text((x_left, y_top), title, font=bold_font, fill=color)
    
    # Get title height and update y-coordinate for text body
    title_bbox = draw.textbbox((x_left, y_top), title, font=bold_font)
    title_height = title_bbox[3] - title_bbox[1]
    y_current = y_top + title_height + int(padding * 2)
    
    # Define line height using the regular font
    max_height = draw.textbbox((0, 0), 'Hy', font=regular_font)[3]  # 'Hy' for descenders and ascenders
    # Split the text body by lines
    text_body = text_body.replace('**.','.**').replace('*.','.*')
    text_body = clean_up_colon(text_body)
    text_body = text_body.replace('**:',':**').replace('*:',':*')
    text_body = '\n'.join([x.strip() for x in text_body.split('\n') if x.strip() != ''])
    text_body = insert_space_before_after_brackets(text_body)
    text_body = insert_padding_line_before_large_icon(text_body)
    text_body = wrap_markdown_individual_words(text_body)
    text_body = text_body.replace('*[','[').replace('*[','[').replace(']*',']').replace(']*',']')
    text_body = clean_up_colon(text_body)
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
            italic_parts = [x for x in bold_part.split('*') if x != '']
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
                        x_current, y_current = draw_text_part(draw, x_current, y_current, word, font, "#545454")
                        # Load and draw the icon
                        icon = Image.open(f"{graphics_folder}/{icon_key}.png").convert('RGBA')
                        if icon:
                            aspect_ratio = icon.width / icon.height
                            scaled_height = max_height+16
                            scaled_width = int(aspect_ratio * scaled_height)
                            if x_current + scaled_width  > x_right:
                                x_current = x_left
                                y_current += max_height + padding
                            x_current = draw_icon(image, icon, x_current, y_current+12, scaled_height)
                        continue  # Skip the rest of the loop and don't draw this word as text
                    # Draw the word
                    x_current, y_current = draw_text_part(draw, x_current, y_current, word, font, "#545454")
        # After a line is processed, move to the next line
        y_current += max_height + padding
    return image, y_current

def BuildUnitCardWithData(unit_card, UnitData, units_folder, graphics_folder, AsoiafFonts, AsoiafData, lang, AsoiafDataTranslations):
    canvas = LayeredImageCanvas(unit_card.size[0], unit_card.size[1])
    canvas.add_layer(unit_card, 0, 0, depth=0)
    faction = UnitData['Faction']
    faction_text_clean = re.sub(r'[^A-Za-z]', '', faction)
    FactionColor = "#7FDBFF" # AQUA default in case new army or somethign
    translated_unit_data = False
    if AsoiafDataTranslations:
        translated_unit_data = [x for x in AsoiafDataTranslations["units"] if x['Id'].strip() == UnitData['Id'].strip()][0]
    if faction in FactionColors:
        FactionColor = FactionColors[faction]
    ArmyAttackAndAbilitiesBorderColor = "Gold"
    if faction in ArmyAttackAndAbilitiesBorderColors:
        ArmyAttackAndAbilitiesBorderColor = ArmyAttackAndAbilitiesBorderColors[faction]
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
    
    def MakeAttackBar(atkdata, atk_ranks, tohit, atk1_or_atk2, xoffset=0, yoffset=0):
        atktype, atkrange, atkText = attackType(atkdata)
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
        if lang in ['de','fr']:
            GBFont = AsoiafFonts.get('Tuff-Italic-29', ImageFont.load_default())
        atk_text_to_draw = atkText.upper()
        if translated_unit_data:
            atk_text_to_draw = translated_unit_data[atk1_or_atk2]
        text_lines_list = split_on_center_space(atk_text_to_draw)
        x,y = [int(x/2) for x in silver_attack_tan_background.size]
        tmp_for_atkname = Image.new('RGBA', silver_attack_tan_background.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(tmp_for_atkname)
        draw_centered_text(draw, (x+10, y - 11), text_lines_list, GBFont, atkColor, line_padding=4)
        #draw.text((17, 17), atkText, font=GBFont, fill=atkColor)
        canvas.add_layer(silver_attack_tan_background, xoffset+60, yoffset+220, depth=0)
        canvas.add_layer(tmp_for_atkname, xoffset+60, yoffset+220, depth=4)
        canvas.add_layer(silver_attack_dice_background, xoffset+100, yoffset+293, depth=2)
        draw = ImageDraw.Draw(atk_stat_bg_image)
        GBFont = AsoiafFonts.get('Garamond-Bold',ImageFont.load_default())
        draw.text((17, 17), tohit, font=GBFont, fill="white")
        canvas.add_layer(atk_stat_bg_image, xoffset+83, yoffset+280, depth=3)
        canvas.add_layer(silver_attack_type_border, xoffset+8, yoffset+210, depth=2)
        canvas.add_layer(silver_attack_type_sword, xoffset+20, yoffset+220, depth=1)
        tmp_for_atkname
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
    atk_text1 = 'Attack 1'
    if atk_text1 in UnitData and UnitData[atk_text1]:
        atk1 = UnitData[atk_text1]
        xoffset = 40
        yoffset = 0
        tohit = UnitData['8']
        atk_ranks = UnitData['9'].split('.')
        MakeAttackBar(atk1, atk_ranks, tohit, atk_text1, xoffset=xoffset, yoffset=yoffset)
    atk_text2 = 'Attack 2'
    if atk_text2 in UnitData and UnitData[atk_text2]:
        atk2 = UnitData[atk_text2]
        xoffset = 40
        yoffset = 200
        tohit = UnitData['11']
        atk_ranks = UnitData['12'].split('.')
        MakeAttackBar(atk2, atk_ranks, tohit, atk_text2, xoffset=xoffset, yoffset=yoffset)
    # AsoiafData
    SkillBottom = Image.open(f"{units_folder}SkillBottom{faction_text_clean}.webp").convert('RGBA')
    SkillTop = SkillBottom.copy().transpose(Image.FLIP_TOP_BOTTOM)
    SkillDivider = Image.open(f"{units_folder}Divider{faction_text_clean}.webp").convert('RGBA')
    yAbilityOffset = 40
    dividerOffset = 20
    SkillBarsOffset = 860
    canvas.add_layer( SkillTop , SkillBarsOffset-5, yAbilityOffset - SkillTop.size[1], depth=3)
    unit_card = canvas.render()
    yAbilityOffset += dividerOffset
    def MakeAttackIcon(atktype):
        # Load the images
        AtkTypeBg = Image.open(f"{units_folder}AttackTypeBg{ArmyAttackAndAbilitiesBorderColor}.webp").convert('RGBA')
        AtkTypeIcon = Image.open(f"{units_folder}AttackType.{atktype}{ArmyAttackAndAbilitiesBorderColor}.webp").convert('RGBA')
        # Resize border to be slightly larger than its original size
        border_scaling_factor = 1.1  # 10% larger than the original size
        new_border_width, new_border_height = [int(x * border_scaling_factor) for x in AtkTypeIcon.size]
        AtkTypeIcon = AtkTypeIcon.resize((new_border_width, new_border_height), resample=Image.LANCZOS)
        # Create a new image with the same size as the resized border
        new_image = Image.new('RGBA', (new_border_width, new_border_height), (255, 255, 255, 0))
        # Calculate the position to paste the sword image so it is centered left and right
        sword_width, sword_height = AtkTypeBg.size
        x_position = (new_image.width - sword_width) // 2
        y_position = (new_image.height - sword_height) // 2
        # Paste the sword image onto the new image
        new_image.paste(AtkTypeBg, (x_position, y_position), AtkTypeBg)
        # Paste the resized border image onto the new image with sword
        new_image.paste(AtkTypeIcon, (0, 0), AtkTypeIcon)
        #width, height = [int(x*1.1) for x in new_image.size]
        #new_image = new_image.resize((width, height))
        return new_image
    def CheckImagePath(imgtype):
        imagepath = f"{units_folder}Skill{imgtype}{ArmyAttackAndAbilitiesBorderColor}.webp"
        if not os.path.exists(imagepath):
            if ArmyAttackAndAbilitiesBorderColor == "Gold":
                imagepath = f"{units_folder}Skill{imgtype}Silver.webp"
            else:
                imagepath = f"{units_folder}Skill{imgtype}Gold.webp"
        return imagepath
    SkillsAndAbiitiesIconsTable = {
        "F": Image.open(CheckImagePath("Faith")).convert('RGBA'),
        "Fire": Image.open(CheckImagePath("Fire")).convert('RGBA'),
        "M":MakeAttackIcon("Melee"),
        "Morale":Image.open(f"{graphics_folder}/IconMorale.png").convert('RGBA'),
        "P":Image.open(CheckImagePath("Pillage")).convert('RGBA'),
        "R":MakeAttackIcon("Ranged"),
        "V":Image.open(CheckImagePath("Venom")).convert('RGBA'),
        "W":Image.open(CheckImagePath("Wounds")).convert('RGBA'),
    }

    def create_combined_vertical_image(skill_icon_image, skill_stat_image, font, text):
        # Calculate the width and height needed for the new image
        width = max(skill_icon_image.width, skill_stat_image.width)
        height = skill_icon_image.height + skill_stat_image.height - 20  # Overlap by 20px
        # Create a new image with the calculated width and height
        combined_image = Image.new('RGBA', (width, height), (0, 0, 0, 0))  # Transparent background
        # Calculate X-axis and Y-axis centering for the text on the stat image
        draw = ImageDraw.Draw(skill_stat_image)
        text_width, text_height = draw.textsize(text, font=font)
        text_x = (skill_stat_image.width - text_width) // 2
        text_y = (skill_stat_image.height - text_height) // 2
        # Draw the text onto the stat image
        draw.text((text_x, text_y), text, font=font, fill="white")
        # Calculate X-axis centering for the Morale image
        Morale_x_center = (width - skill_icon_image.width) // 2
        # Paste the Morale image onto the combined image, centered
        combined_image.paste(skill_icon_image, (Morale_x_center, 0), skill_icon_image)
        # Calculate X-axis centering for the stat image
        stat_x_center = (width - skill_stat_image.width) // 2
        # Calculate the Y-axis position for the stat image (right below the Morale image -20px)
        stat_y_position = skill_icon_image.height - 20
        # Paste the stat image onto the combined image, centered and below the Morale image
        combined_image.paste(skill_stat_image, (stat_x_center, stat_y_position), skill_stat_image)
        return combined_image

    def split_string_by_trailing_digits(s):
        match = re.search(r'^(.*?)(\d+)$', s)
        if match:
            return True, match.group(1), match.group(2)
        else:
            return False, s, ''
    dividerYPadding = 10
    def addDivider(x, y):
        div = SkillDivider.copy()
        unit_card.paste(div, (x, y+dividerYPadding), div)
        return div.size[1] + dividerOffset + int(dividerYPadding/2)
    if 'Abilities' in UnitData and UnitData['Abilities']:
        backofcardabilities = [x.lower() for x in ['adaptive']] # There is nothing in the data that differentiates a back of card ability so we will have to manually set it here.
        all_abilities = [x.strip() for x in UnitData['Abilities'].strip().split('/') if x.strip().lower() not in backofcardabilities and not x.strip().lower().startswith('loyalty:')]
        copy_all_abilities = all_abilities.copy()
        for ability_text in copy_all_abilities:
            try:
                [x for x in AsoiafData['newskills'] if x['Name'].lower() == ability_text.lower()][0]
            except IndexError as e:
                all_abilities.remove(ability_text)
                continue
        tmp_ability_text = ""
        for ability in all_abilities:
            tmpt = [x['Description'] for x in AsoiafData['newskills'] if x['Name'].strip().lower() == ability.lower()][0]
            if AsoiafDataTranslations:
                try:
                    tmpt = [x['Translated Description'] for x in AsoiafDataTranslations["newskills"] if x['Original Name'].strip().lower() == ability.lower()][0]
                except Exception as e:
                    pass
            tmp_ability_text += tmpt
        GBFontSize = 38
        TNSize = 37
        TN30Size = 32
        TN30ISize = 32
        if len(all_abilities) > 2:
            GBFontSize = 33
            TNSize = 32
            TN30Size = 28
            TN30ISize = 28
        elif len(tmp_ability_text) > 580:
            GBFontSize = 30
            TNSize = 30
            TN30Size = 27
            TN30ISize = 27
        if lang in ['de','fr']:
            # german words tend to me long:
            title_mod = 0.85
            mod = 0.9
            GBFontSize = int(GBFontSize*title_mod)
            TNSize = int(TNSize*title_mod)
            TN30Size = int(TN30Size*mod)
            TN30ISize = int(TN30ISize*mod)
        GBFont = AsoiafFonts.get(f'Tuff-Bold-{GBFontSize}',ImageFont.load_default())
        TN = AsoiafFonts.get(f'Tuff-Bold-{TNSize}',ImageFont.load_default())
        TN30 = AsoiafFonts.get(f'Tuff-Normal-{TN30Size}',ImageFont.load_default())
        TN30I = AsoiafFonts.get(f'Tuff-Italic-{TN30ISize}',ImageFont.load_default())
        for index in range(len(all_abilities)):
            ability = all_abilities[index]
            skillability_icon_images = []
            translated_ability_dict = False
            try:
                skilldata = [x for x in AsoiafData['newskills'] if x['Name'].strip().lower() == ability.lower()][0]
                if AsoiafDataTranslations:
                    translated_ability_dict = [x for x in AsoiafDataTranslations["newskills"] if x['Original Name'].strip().lower() == ability.lower()][0]
            except Exception as e:
                print("Ran into an error at:\nskilldata = [x for x in AsoiafData['newskills'] if x['Name'].lower() == ability.lower()][0]")
                #pdb.set_trace()
            if ability.startswith(f"Order:"):
                skillability_icon_images.append( [Image.open(f"{units_folder}SkillOrder{ArmyAttackAndAbilitiesBorderColor}.webp").convert('RGBA'),[0,0]] )
            elif 'Icons' in skilldata and skilldata['Icons']:
                split_skills = skilldata['Icons'].split(',')
                for skill in split_skills:
                    # Some units have a Morale5 ability which is unique so we have to handle that (but I made it so it can handle other situations too just in case)
                    ended_with_digits, text, digits = split_string_by_trailing_digits(skill)
                    if ended_with_digits:
                        skill_icon_image = Image.open(f"{units_folder}{text}.webp").convert('RGBA')
                        skill_stat_image = Image.open(f"{units_folder}StatBg.webp").convert('RGBA')
                        skillability_icon_images.append( [create_combined_vertical_image(skill_icon_image, skill_stat_image, AsoiafFonts.get('Garamond-Bold'), f"{digits}+"),[0,-5]] )
                    elif skill in SkillsAndAbiitiesIconsTable:
                        off = [0,-10]
                        if skill in ['M','R']: # if melee or ranged
                            off = [10,-5]
                        skillability_icon_images.append( [SkillsAndAbiitiesIconsTable[skill].copy(),off] )
            starty = yAbilityOffset+0
            ability_name = ability.upper().split('(')[0].strip()
            skill_data_string = skilldata['Description'].strip()
            if translated_ability_dict:
                ability_name = translated_ability_dict['Translated Name'].upper().split('(')[0].strip()
                skill_data_string = translated_ability_dict['Translated Description'].strip()
            unit_card, yAbilityOffset = draw_markdown_text(unit_card, GBFont, TN, TN30, TN30I, ability_name, skill_data_string, FactionColor, yAbilityOffset, 885, 1400, graphics_folder, lang, padding=10)
            midy = starty + int((yAbilityOffset-starty) / 2 )
            if len(skillability_icon_images) > 0:
                if len(skillability_icon_images) == 1:
                    icon = skillability_icon_images[0][0]
                    offx, offy = skillability_icon_images[0][1]
                    if index < len(all_abilities)-1:
                        yAbilityOffset += addDivider(SkillBarsOffset - 52, yAbilityOffset)
                    unit_card.paste(icon, (SkillBarsOffset - icon.size[0] + offx, midy - int(icon.size[0]/2)+ offy), icon)
                elif len(skillability_icon_images) == 2:
                    icon1 = skillability_icon_images[0][0]
                    icon2 = skillability_icon_images[1][0]
                    offx1, offy1 = skillability_icon_images[0][1]
                    offx2, offy2 = skillability_icon_images[1][1]
                    #if UnitData['Name'].upper() == "PYROMANCERS":
                    #    pdb.set_trace()
                    if index < len(all_abilities)-1:
                        yAbilityOffset += addDivider(SkillBarsOffset - 52, yAbilityOffset)
                    unit_card.paste(icon1, (SkillBarsOffset - icon1.size[0] + offx1, midy - icon1.size[1] + offy1), icon1)
                    unit_card.paste(icon2, (SkillBarsOffset - icon2.size[0] + offx2, midy + offy2), icon2)
                else:
                    pass # found no occurence where a single ability panel had more than 2 icons
            elif index < len(all_abilities)-1:
                yAbilityOffset += addDivider(SkillBarsOffset - 52, yAbilityOffset)

    unit_card.paste(SkillBottom, (SkillBarsOffset, yAbilityOffset + dividerYPadding), SkillBottom)
    draw = ImageDraw.Draw(unit_card)
    GaramondBoldFont = AsoiafFonts.get('Garamond-Bold', ImageFont.load_default())
    draw.text((183, 86), UnitData['Spd'], font=GaramondBoldFont, fill="white")
    draw.text((175, 630), UnitData['Def'], font=GaramondBoldFont, fill="white")
    draw.text((375, 630), UnitData['Moral'], font=GaramondBoldFont, fill="white")
    # Version Text:
    # Create an image for the text
    text_image = Image.new('RGBA', [160, 40], (255, 255, 255, 0))  # transparent background
    text_draw = ImageDraw.Draw(text_image)
    # Draw the text onto this image (consider using textsize to determine size dynamically)
    VersionFont = AsoiafFonts.get('Tuff-Italic-25', ImageFont.load_default())
    text_draw.text((0, 0), UnitData['Version'], font=VersionFont, fill="white")
    # Rotate the text image
    rotated_text_image = text_image.rotate(90, expand=1)
    # Paste the rotated text image onto your main image (consider using the alpha channel for proper transparency)
    unit_card.paste(rotated_text_image, (rotated_text_image.width - 10, unit_card.size[1] - rotated_text_image.height - 20), rotated_text_image)
    TuffBoldFont = AsoiafFonts.get('Tuff-Bold-50', ImageFont.load_default()) 
    TuffBoldFontSmall = AsoiafFonts.get('Tuff-Bold-25', ImageFont.load_default())
    if lang in ['de','fr']:
        TuffBoldFont = AsoiafFonts.get('Tuff-Bold-42', ImageFont.load_default()) 
    unit_name = UnitData['Name'].upper()
    if AsoiafDataTranslations:
        unit_name = translated_unit_data['Translated Name'].upper()
    text_lines_list, hadAComma = split_name_string(unit_name)
    if not hadAComma:
        draw_centered_text(draw, (530, 750), text_lines_list, TuffBoldFont, "white", line_padding=10)
    else:
        draw_centered_text(draw, (530, 750), [text_lines_list[0]], TuffBoldFont, "white", line_padding=10)
        draw_centered_text(draw, (530, 750 + int(TuffBoldFont.size/1.3) ), [text_lines_list[1]], TuffBoldFontSmall, "white", line_padding=10)
    #unit_card = add_rounded_corners(unit_card, 20)
    return unit_card

def BuildUnitProfile(UnitData, units_folder):
    print(f"Creating {UnitData['Name']} Profile")
    # {'Faction': 'Neutral', 'Name': 'Lord Varys, The Spider', 'Character': 'Lord Varys', 'Cost': '4', 'Names': 'Little Birds', 'Descriptions': 
    # 'Varys begins the iendly unit.\n[SWORDS]: 1 enemy suffers 3 Hits.\n[LETTER]: Draw 1 Tactics card.\n[HORSE]: 1 friendly unit shifts 3".', 
    # 'Requirements': '', 'Boxes': 'SIF505', 'Id': '30403', 'Version': '2021-S03', 'Quote': '"Varys has ."', 'Restrictions': ''}
    #pdb.set_trace()
    UnitId = UnitData['Id']

    canvas = LayeredImageCanvas(273, 273)

    unit_portrait = Image.open(f"{units_folder}{UnitId}.jpg").convert('RGBA').resize((273, 423))
    canvas.add_layer(unit_portrait, 0, 0, depth=0)
    return canvas.render()

def main():
    lang = "en"
    if len(sys.argv) > 1:
        lang = sys.argv[1]
    # Currently, this assumes you are running it from the assets/flutter_assets folder
    assets_folder="./assets/"
    fonts_dir=f"./fonts/"
    warcouncil_latest_csv_folder = './warcouncil_latest_csv/'
    AsoiafFonts = load_fonts(fonts_dir)
    data_folder=f"{assets_folder}data/"
    units_folder=f"{assets_folder}Units/"
    attachments_folder=f"{assets_folder}Attachments/"
    graphics_folder = f"{assets_folder}graphics"
    UnitCardsOutputDir  = f"./{lang}/unitscards/"
    if not os.path.exists(UnitCardsOutputDir):
        Path(UnitCardsOutputDir).mkdir(parents=True, exist_ok=True)
    if not os.path.exists(UnitCardsOutputDir+"png/"):
        Path(UnitCardsOutputDir+"png/").mkdir(parents=True, exist_ok=True)
    if not os.path.exists(UnitCardsOutputDir+"jpg/"):
        Path(UnitCardsOutputDir+"jpg/").mkdir(parents=True, exist_ok=True)
    AsoiafData = import_csvs_to_dicts(data_folder) # contains the keys: attachments,boxes,ncus,newskills,rules,special,tactics,units
    AsoiafDataTranslations = False
    if lang != "en":
        AsoiafDataTranslations = import_csvs_to_dicts(warcouncil_latest_csv_folder, lang)
    #SelectedUnitCardData = [x for x in AsoiafData['units'] if x['Name'] == "Gregor Clegane, The Mountain That Rides"][0]
    #SelectedUnitCardData = [x for x in AsoiafData['units'] if x['Name'] == "Lannister Crossbowmen"][0]
    #SelectedUnitCardData = [x for x in AsoiafData['units'] if x['Name'] == "Crannogman Trackers"][0]
    for SelectedUnitCardData in AsoiafData['units']:
        is_any_value_true = any(bool(value) for value in SelectedUnitCardData.values())# check for empty dicts
        if not is_any_value_true:
            continue
        unit_card = BuildUnitCardFactionBackground(SelectedUnitCardData, units_folder, attachments_folder, graphics_folder)
        unit_card = BuildUnitCardWithData(unit_card, SelectedUnitCardData, units_folder, graphics_folder, AsoiafFonts, AsoiafData, lang, AsoiafDataTranslations)
        if unit_card:
            unit_card = add_rounded_corners(unit_card,15)
            # This is just for viewing / debugging purposes. Can click to get coordinates on image:
            unit_card_output_path = os.path.join(UnitCardsOutputDir+"png/", f"{SelectedUnitCardData['Id'].replace(' ', '_')}f.png")
            unit_card.save(unit_card_output_path)
            unit_card_output_path = os.path.join(UnitCardsOutputDir+"jpg/", f"{SelectedUnitCardData['Id'].replace(' ', '_')}f.jpg")
            unit_card = unit_card.convert("RGB")
            unit_card.save(unit_card_output_path)

    for SelectedUnitCardData in AsoiafData['units']:
        is_any_value_true = any(bool(value) for value in SelectedUnitCardData.values())# check for empty dicts
        if not is_any_value_true:
            continue
        unit_card = BuildUnitProfile(SelectedUnitCardData, units_folder)
        if unit_card:
            # This is just for viewing / debugging purposes. Can click to get coordinates on image:
            unit_card_output_path = os.path.join(UnitCardsOutputDir+"png/", f"{SelectedUnitCardData['Id'].replace(' ', '_')}p.png")
            unit_card.save(unit_card_output_path)
            unit_card_output_path = os.path.join(UnitCardsOutputDir+"jpg/", f"{SelectedUnitCardData['Id'].replace(' ', '_')}p.jpg")
            unit_card = unit_card.convert("RGB")
            unit_card.save(unit_card_output_path)
    # If You Want to View the Card AND click debug to find positioning uncommont these lines:
    #root = tk.Tk()
    #app = ImageEditor(root, unit_card)
    #root.mainloop()


if __name__ == "__main__":
    main()
