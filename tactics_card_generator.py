import re
import csv
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageChops, ImageStat
#from image_editor import ImageEditor
import itertools
import os
import sys
from collections import defaultdict
from pathlib import Path

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


FONT_SIZE_MODIFIER = 1
USE_FONT_SIZE_MODIFIER = False
CSV_PATH = "./assets/data"
ASSETS_DIR = "./assets"

def add_rounded_corners(im, rad):
    circle = Image.new('L', (rad * 2, rad * 2), 0)
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, rad * 2, rad * 2), fill=255)
    alpha = Image.new('L', im.size, "white")
    w, h = im.size
    alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
    alpha.paste(circle.crop((0, 0, rad, rad)).rotate(90), (0, h - rad))
    alpha.paste(circle.crop((0, 0, rad, rad)).rotate(180), (w - rad, h - rad))
    alpha.paste(circle.crop((0, 0, rad, rad)).rotate(270), (w - rad, 0))
    alpha.paste(255, (rad, 0, w - rad, h - rad))
    alpha.paste(255, (0, rad, rad, h - rad))
    alpha.paste(255, (w - rad, rad, w, h - rad))
    alpha.paste(255, (rad, rad, w - rad, h - rad))

    im = im.convert("RGBA")
    old_alpha = im.getchannel("A")
    im.putalpha(ImageChops.darker(alpha, old_alpha))

    return im


def split_on_center_space(text, maxlen=14):
    # If the length of the text is less than the maximum length or there's no space, return the text in a single-item list
    if len(text) < maxlen or ' ' not in text:
        return [text]

    # Find the middle index of the string
    middle = len(text) // 2
    left_index = text.rfind(' ', 0, middle)  # Search for space going left from the middle
    right_index = text.find(' ', middle)  # Search for space going right from the middle

    # Determine the closest space to the middle to use as the split point
    # If no space to the left, use the right one; if both exist, choose the closest
    if left_index == -1 or (right_index != -1 and (middle - left_index) > (right_index - middle)):
        split_index = right_index
    else:
        split_index = left_index

    # Split the string into two parts
    part1 = text[:split_index]
    part2 = text[split_index + 1:]  # +1 to exclude the space itself

    # Return the parts in a list
    return [part1, part2]


def make_attack_bar(atk_type, atk_name, atk_ranks, tohit, border_color="Gold"):
    units_folder = f"{ASSETS_DIR}/Units/"
    attack_type_bg = Image.open(f"{ASSETS_DIR}/Units/AttackTypeBg{border_color}.webp").convert('RGBA')
    attack_type = Image.open(f"{ASSETS_DIR}/Units/AttackType.{'Melee' if atk_type == 'melee' else 'Ranged'}{border_color}.webp").convert('RGBA')
    attack_type = attack_type.resize((124, 124))
    attack_bg = Image.open(f"{ASSETS_DIR}/Units/AttackBg{border_color}.webp").convert('RGBA')
    attack_dice_bg = Image.open(f"{units_folder}DiceBg.webp").convert('RGBA')
    attack_stat_bg = Image.open(f"{units_folder}StatBg.webp").convert('RGBA')

    attack_bar = Image.new("RGBA", (367, 166))
    attack_bar.alpha_composite(attack_bg, (
    14 + attack_type_bg.size[0] // 2, 14 + (attack_bg.size[1] - attack_type_bg.size[1]) // 2))
    attack_bar.alpha_composite(attack_type_bg, (14, 14))
    attack_bar.alpha_composite(apply_drop_shadow(attack_type), (-15, -14))

    atk_name_color = "#0e2e45" if atk_type == "melee" else "#87282a"
    text_lines_list = split_on_center_space(atk_name.upper())
    rd_atk_name = render_paragraph(text_lines_list, atk_name_color, 30, 6, font_family="Tuff-Italic",
                                   thickness_factor=1.8)
    attack_bar.alpha_composite(rd_atk_name, (224 - rd_atk_name.size[0] // 2, 56 - rd_atk_name.size[1] // 2))

    if atk_type != "melee":
        range_graphic = Image.open(f"{ASSETS_DIR}/graphics/Range{atk_type.capitalize()}{border_color}.png").convert('RGBA')
        attack_bar.alpha_composite(apply_drop_shadow(range_graphic), (60, -14))

    rd_statistics = Image.new("RGBA", attack_bar.size)
    rd_statistics.alpha_composite(attack_dice_bg, (84, 68))
    rd_statistics.alpha_composite(attack_stat_bg, (58, 56))
    rd_tohit = render_text_line(f"{tohit}+", "white", 44, font_family="Garamond-Bold")
    rd_statistics.alpha_composite(rd_tohit, (
    58 + (attack_stat_bg.size[0] - rd_tohit.size[0]) // 2, 56 + (attack_stat_bg.size[1] - rd_tohit.size[1]) // 2))
    rank_colors = ["#648f4a", "#dd8e29", "#bd1a2b"]
    for i in range(len(atk_ranks)):
        rank_bg = Image.new("RGBA", (35, 35), rank_colors[i])
        rd_num_dice = render_text_line(str(atk_ranks[i]), "#cdcecb", 37, "Garamond-Bold", thickness_factor=0)

        # This was an interesting programming journey, but having a transparent font makes it pretty hard to read the text
        # rd_num_dice = render_text_line(str(atk_ranks[i]), "black", 35, "Garamond-Bold", thickness_factor=0)
        rd_num_dice = rd_num_dice.crop(rd_num_dice.getbbox())
        rank_bg.alpha_composite(rd_num_dice, (16 - rd_num_dice.size[0] // 2, 6))
        # mask = Image.new("RGBA", (35, 35))
        # mask.alpha_composite(rd_num_dice, (16 - rd_num_dice.size[0] // 2, 5))
        # r,g,b,_ = rank_bg.split()
        # rank_bg = Image.merge("RGBA", (r,g,b,ImageChops.invert(mask.getchannel("A"))))
        rd_statistics.alpha_composite(add_rounded_corners(rank_bg, 10), (144 + i * 42, 78))
    attack_bar.alpha_composite(apply_drop_shadow(rd_statistics))

    return attack_bar


def get_faction_color(faction):
    faction_colors = {
        "martell": "#9e4c00",
        "neutral": "#3e2a19",
        "nightswatch": "#302a28",
        "stark": "#3b6680",
        "targaryen": "#530818",
        "baratheon": "#904523",
        "bolton": "#7a312b",
        "freefolk": "#4b4138",
        "greyjoy": "#10363b",
        "lannister": "#9d1323",
    }
    faction = re.sub(r"[^a-z]", "", faction.lower())
    return faction_colors.get(faction) or "#7FDBFF"


def apply_drop_shadow(image, shadow_size=3, color="black", passes=5):
    border = 20
    shadow = Image.new('RGBA',
                       (image.size[0] + shadow_size * 2 + border * 2, image.size[1] + shadow_size * 2 + border * 2))
    mask = image.copy()
    # mask = mask.resize((image.size[0] + shadow_size * 2, image.size[1] + shadow_size * 2))
    # shadow.paste(color, (border - shadow_size, border - shadow_size), mask=mask)
    shadow.paste(color, (border, border), mask=mask)
    for i in range(passes):
        shadow = shadow.filter(ImageFilter.BLUR)
    shadow.alpha_composite(image, (border, border))
    return shadow


def combine_images_horizontal_center(images, vertical_padding, fixed_height=0, offsets=None):
    if USE_FONT_SIZE_MODIFIER:
        vertical_padding = int(FONT_SIZE_MODIFIER * vertical_padding * 0.9)
    if offsets is None:
        offsets = [(0, 0) for _ in images]
    max_width = max([im.size[0] for im in images])
    if fixed_height != 0:
        # The last line should be full height, because we only care about line spacing.
        # Letters such as "g" or "y" might be clipped otherwise.
        total_height = images[-1].size[1] + (len(images) - 1) * (vertical_padding + fixed_height)
    else:
        total_height = sum([im.size[1] for im in images]) + vertical_padding * (len(images) - 1)

    out = Image.new("RGBA", (max_width, total_height))
    x, y = 0, 0
    for offset, image in zip(offsets, images):
        x = (max_width - image.size[0]) // 2
        out.alpha_composite(image, (x, y + offset[0]))
        y += (fixed_height or image.size[1]) + vertical_padding + offset[1]
    return out


def text_to_image(text, font_path, font_size, font_color, thickness_factor=3):
    if USE_FONT_SIZE_MODIFIER:
        font_size = int(FONT_SIZE_MODIFIER * font_size)
    # The stroke_width property (see below) would be really nice if it worked with smaller font sizes
    # As a workaround, we use a bigger fontsize, then downscale the image later
    stroke_width = 0 if thickness_factor == 0 else 1
    thickness_factor = thickness_factor or 1
    font = ImageFont.truetype(font_path, int(font_size * thickness_factor))
    bbox = font.getbbox(text)
    # Offset of 1, otherwise tall letters are clipped
    offset_x, offset_y = 0, 1
    # For vertical center alignment, ensure the height is consistent. "yjg" are the tallest letters.
    # Usually, this means h == font_size
    w, h = bbox[2], font.getbbox("yjg")[3] + 1
    # Avoid clipping of letters such as "j"
    if bbox[0] < 0:
        w -= bbox[0]
        offset_x += bbox[0]
    canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.text((offset_x, offset_y), text, font_color, font=font, stroke_width=stroke_width)

    return canvas.resize((int(canvas.size[0] / thickness_factor), int(canvas.size[1] / thickness_factor)))


def render_text_icon(token, font_color, font_size):
    token = token.strip('[]')
    icons = {
        "CROWN": "simple",
        "MONEY": "simple",
        "LETTER": "simple",
        "SWORDS": "simple",
        "HORSE": "simple",
        "UNDYING": "simple",
        "OASIS": "simple",

        "MOVEMENT": "image",
        "WOUND": "image",
        "LONGRANGE": "image",
    }

    if token.startswith("ATTACK"):
        # [ATTACK:LongRanged:Hurl Boulder:3+1]
        # _, atk_range, atk_name, atk_stats = token.split(":")
        # rendered = make_attack_bar("Ranged", "Long", "Hurl Boulder", [1], "3+")
        raise NotImplementedError(
            "Tried to render [ATTACK] inline. You should parse it first and leave it to paragraph rendering.")
    else:
        icon = Image.open(f"{ASSETS_DIR}/graphics/{token}.png").convert("RGBA")
        icon = icon.crop(icon.getbbox())
        icon_h = int(font_size * 1.15)
        if USE_FONT_SIZE_MODIFIER:
            icon_h = int(FONT_SIZE_MODIFIER * icon_h)
        icon = icon.resize((int(icon_h * icon.size[0] / icon.size[1]), icon_h))
        rendered = Image.new("RGBA", (icon.size[0] + 2, icon.size[1]))
        if icons[token] == "simple":
            rendered.paste(font_color, (1, 0), mask=icon)
        elif icons[token] == "image":
            rendered.alpha_composite(icon, (1, 0))

    return rendered


def render_text_line(line, font_color, font_size, font_family=None, thickness_factor=3):
    is_bold = False
    is_italic = False
    rendered_tokens = []
    for token in re.split(r"(\*+|\[[A-Z]+])", line):
        if token == "":
            continue
        elif token.startswith("["):
            rendered = render_text_icon(token, font_color, font_size)
            rendered_tokens.append({"im": rendered, "type": "icon"})
        elif token == "*":
            is_italic = not is_italic
        elif token == "**":
            is_bold = not is_bold
        else:
            font_style = f"{'Bold' if is_bold else ''}{'Italic' if is_italic else ''}{'Normal' if not is_italic and not is_bold else ''}"
            font_path = f"./fonts/Tuff-{font_style}.ttf" if font_family is None else f"./fonts/{font_family}.ttf"
            rendered = text_to_image(token, font_path, font_size, font_color, thickness_factor)
            rendered_tokens.append({"im": rendered, "type": "text"})

    total_width = sum([tkn["im"].size[0] for tkn in rendered_tokens])
    max_height = max([tkn["im"].size[1] for tkn in rendered_tokens])
    rendered_line = Image.new("RGBA", (total_width, max_height + 7))
    x = 0
    for token in rendered_tokens:
        image = token["im"]
        # It's disgusting, but icons need to be rendered higher than the font. So we pad each text line by 7px.
        if token["type"] == "icon":
            rendered_line.paste(image, (x, 0), image)
        else:
            rendered_line.paste(image, (x, 7), image)
        x += image.size[0]

    out = Image.new("RGBA", rendered_line.size, "red")
    out.alpha_composite(rendered_line)
    return rendered_line


def render_paragraph(paragraph, font_color, font_size, padding_lines, font_family=None, thickness_factor=3):
    rendered_lines = []
    for line in paragraph:
        rendered_line = render_text_line(line, font_color, font_size, font_family=font_family,
                                         thickness_factor=thickness_factor)
        rendered_lines.append(rendered_line)

    return combine_images_horizontal_center(rendered_lines, padding_lines, int(font_size * 0.7))


def render_paragraphs(paragraphs, font_color="#5d4d40", font_size=41, line_padding=18, padding_paragraph=16):
    rendered_paragraphs = []
    offsets = []
    for paragraph in paragraphs:
        offset = (0, 0)
        if isinstance(paragraph, dict) and paragraph.get("content") is None:
            atk_name = paragraph.get("name")
            atk_type = paragraph.get("type")
            tohit = paragraph.get("hit")
            atk_ranks = paragraph.get("dice")
            bar = make_attack_bar(atk_type, atk_name, atk_ranks, tohit)
            rendered_paragraph = apply_drop_shadow(bar, color="#00000099")
            offset = (-38, -82)
        else:
            if isinstance(paragraph, dict):
                content = paragraph.get("content")
                color = paragraph.get("font_color") or font_color
                size = paragraph.get("font_size") or font_size
                padding = paragraph.get("line_padding") or line_padding
            else:
                content = paragraph
                color = font_color
                size = font_size
                padding = line_padding
            rendered_paragraph = render_paragraph(content, color, size, padding)
        rendered_paragraphs.append(rendered_paragraph)
        offsets.append(offset)

    return combine_images_horizontal_center(rendered_paragraphs, padding_paragraph, offsets=offsets)

flatten = lambda x: ' '.join([''.join([y for y in item]) for sublist in x for subsublist in sublist.values() for item in (subsublist if isinstance(subsublist, list) else [subsublist])])

def scale_font_size(text, max_length=40, default_size=32):
    if len(text) > max_length:
        # Calculate the scale factor
        scale_factor = max_length / len(text)
        # Apply the scale factor to the default size, with a minimum size limit if needed
        new_size = max(int(default_size * scale_factor), 12)  # 12 is an arbitrary minimum font size
    else:
        new_size = default_size
    return int(new_size)

def build_tactics_card(card_info):
    global FONT_SIZE_MODIFIER, USE_FONT_SIZE_MODIFIER
    faction = re.sub(r"[^A-Za-z]", "", card_info.get("faction"))
    name = card_info.get("name")
    card_text = card_info.get("text")
    card_text_len = len(flatten(card_text).replace('*',''))
    version = card_info.get("version")
    commander_id = card_info.get("commander_id")
    commander_name = card_info.get("commander_name")
    USE_FONT_SIZE_MODIFIER = False
    nm = ' '.join(name).lower()
    if card_text_len > 390 or all([len(card_text)>=3, card_text_len > 270]) or all([len(card_text)>=2, card_text_len > 180]):
        FONT_SIZE_MODIFIER = 0.8
        if any([x in nm for x in ['counterplot']]):
            FONT_SIZE_MODIFIER = 0.76
    else:
        FONT_SIZE_MODIFIER = 1
    #if 'counterplot' in nm:
    #    import pdb
    #    pdb.set_trace()
    #else:
    #    return
    tactics_bg = Image.open(f"{ASSETS_DIR}/Tactics/Bg_{faction}.jpg").convert('RGBA')
    tactics_bg2 = Image.open(f"{ASSETS_DIR}/Tactics/Bg2.jpg").convert('RGBA')
    tactics_card = Image.new('RGBA', tactics_bg.size)
    tactics_card.paste(tactics_bg.rotate(180))
    tactics_card.paste(tactics_bg2, (47, 336))

    if commander_id is not None:
        cmdr_image = Image.open(f"{ASSETS_DIR}/Tactics/{commander_id}.jpg").convert('RGBA')
        tactics_card.paste(cmdr_image, (-1, -2))

    bars = Image.new('RGBA', tactics_bg.size)
    large_bar = Image.open(f"{ASSETS_DIR}/Units/LargeBar{faction}.webp").convert('RGBA')
    small_bar = Image.open(f"{ASSETS_DIR}/Attachments/Bar{faction}.webp").convert('RGBA')
    weird_bar = Image.open(f"{ASSETS_DIR}/Units/Corner{faction}.webp").convert('RGBA')
    # They arent all the same size so im pasting to the standard size
    tmp = Image.new("RGBA", (229,702), (0, 0, 0, 0))
    tmp.paste(weird_bar, (0,0), weird_bar)
    weird_bar = tmp

    bars.alpha_composite(large_bar.rotate(180), (-96, 252))
    if commander_id is not None:
        bars.paste(Image.new("RGBA", (646, 82), (0, 0, 0, 0)), (55, 246))

    bars.alpha_composite(ImageOps.flip(weird_bar.rotate(270, expand=1)), (-460, 25))
    bars.alpha_composite(weird_bar.rotate(270, expand=1), (-460, -95))
    if commander_id is not None:
        bars.alpha_composite(large_bar.rotate(90, expand=1), (240, 235 - large_bar.size[0]))
        bars.alpha_composite(weird_bar.rotate(90, expand=1), (323, 25))
        bars.alpha_composite(ImageOps.flip(weird_bar.rotate(90, expand=1)), (323, -95))
        bars.alpha_composite(small_bar.rotate(90, expand=1), (234, 255 - small_bar.size[0]))
        bars.alpha_composite(small_bar.rotate(90, expand=1), (314, 255 - small_bar.size[0]))
    else:
        bars.alpha_composite(weird_bar.rotate(90, expand=1), (243, 25))
        bars.alpha_composite(ImageOps.flip(weird_bar.rotate(90, expand=1)), (243, -95))
        bars.alpha_composite(small_bar.rotate(90, expand=1), (234, 255 - small_bar.size[0]))

    if commander_id is None:
        bars.alpha_composite(small_bar.rotate(90, expand=1).crop((0, 0, 100, tactics_bg2.size[1])), (46, 336))
        bars.alpha_composite(small_bar.rotate(90, expand=1).crop((0, 0, 100, tactics_bg2.size[1])), (692, 336))
    else:
        bars.alpha_composite(small_bar.rotate(90, expand=1).crop((0, 0, 100, tactics_bg2.size[1] + 82)), (46, 246))
        bars.alpha_composite(small_bar.rotate(90, expand=1).crop((0, 0, 100, tactics_bg2.size[1] + 82)), (692, 246))
    bars.alpha_composite(small_bar.crop((0, 0, tactics_bg2.size[0], 100)),
                         ((tactics_bg.size[0] - tactics_bg2.size[0]) // 2, 985))
    bars.alpha_composite(small_bar, (0, 246))
    bars.alpha_composite(small_bar, (0, 328))

    decor = Image.open(f"{ASSETS_DIR}/Tactics/Decor{faction}.webp").convert('RGBA')
    bars.alpha_composite(decor, (33, 316))
    bars.alpha_composite(decor, (678, 316))
    bars.alpha_composite(decor, (33, 971))
    bars.alpha_composite(decor, (678, 971))
    if commander_id is not None:
        bars.alpha_composite(decor, (33, 232))
        bars.alpha_composite(decor, (678, 232))

    all_text = Image.new('RGBA', tactics_bg.size)
    max_cmdr_name_length = 35 
    default_commander_name_font_size = 32
    #rendered_name = render_paragraph([f"**{l.upper()}**" for l in name], font_color="white", font_size=51, padding_lines=12)
    
    if commander_name is not None:
        nm_font_size = scale_font_size(commander_name, max_length=max_cmdr_name_length, default_size=default_commander_name_font_size)
        rendered_cmdr_name = render_text_line(commander_name.upper(), font_color="white", font_size=nm_font_size)
        #all_text.alpha_composite(rendered_cmdr_name, ((tactics_bg.size[0] - rendered_cmdr_name.size[0]) // 2, 275))
        #all_text.alpha_composite(rendered_name, (
        #(tactics_bg.size[0] - rendered_name.size[0]) // 2 + 162, 136 - rendered_name.size[1] // 2))
    else:
        pass
        #all_text.alpha_composite(rendered_name, (
        #(tactics_bg.size[0] - rendered_name.size[0]) // 2 + 128, 140 - rendered_name.size[1] // 2))
    USE_FONT_SIZE_MODIFIER = True

    card_text_y = 360
    for ix, trigger_effect in enumerate(card_text):
        trigger = trigger_effect.get("trigger")
        effect = trigger_effect.get("effect")
        is_remove_text = ix > 0 and card_info.get("remove") is not None
        if ix > 0:
            card_text_y += 15
            #bars.alpha_composite(small_bar.crop((0, 0, tactics_bg2.size[0], 100)),
            #                     ((tactics_bg.size[0] - tactics_bg2.size[0]) // 2, card_text_y))
            #bars.alpha_composite(decor, (33, card_text_y + (small_bar.size[1] - decor.size[1]) // 2))
            #bars.alpha_composite(decor, (678, card_text_y + (small_bar.size[1] - decor.size[1]) // 2))
            card_text_y += small_bar.size[1] + 15

        font_color = get_faction_color(faction) if not is_remove_text  else "#5d4d40"
        rd_trigger = render_paragraph(trigger, font_color=font_color, font_size=41, padding_lines=18)
        trigger_x, trigger_y = (tactics_bg.size[0] - rd_trigger.size[0]) // 2, card_text_y
        #all_text.alpha_composite(rd_trigger, (trigger_x, trigger_y))
        card_text_y += rd_trigger.size[1]

        if not is_remove_text:
            if type(effect) != list:
                effect = [[effect]]
            elif type(effect[0]) != list:
                effect = [effect]
            #rd_effect_text = render_paragraphs(effect)
            #effect_text_x, effect_text_y = (tactics_bg.size[0] - rd_effect_text.size[0]) // 2, card_text_y + 12
            #all_text.alpha_composite(rd_effect_text, (effect_text_x, effect_text_y))
            #card_text_y += rd_effect_text.size[1]
    USE_FONT_SIZE_MODIFIER = False
    #rendered_version = render_text_line(version, font_color="white", font_size=30)
    #version_x, version_y = 21, tactics_bg.size[1] - rendered_version.size[0] - 70
    #all_text.alpha_composite(rendered_version.rotate(90, expand=1), (version_x-15, version_y-10))

    tactics_card.alpha_composite(apply_drop_shadow(bars), (-20, -20))

    crest = Image.open(f"{ASSETS_DIR}/Tactics/Crest{faction}.webp").convert('RGBA')
    if commander_id is None:
        tactics_card.alpha_composite(
            apply_drop_shadow(crest.rotate(16, expand=1, resample=Image.BILINEAR), shadow_size=2), (54, 48))
    else:
        tactics_card.alpha_composite(
            apply_drop_shadow(crest.resize((int(crest.size[0] * 0.68), int(crest.size[1] * 0.68)))), (200, 100))


    tactics_card.alpha_composite(all_text)
    return tactics_card

def csv_to_dict(path):
    with open(path, "r", encoding="utf-8") as csv_file:
        line = csv_file.readline()
        headers = [h if h else str(ix) for ix, h in enumerate(line.strip().split(","))]
        csv_reader = csv.DictReader(csv_file, fieldnames=headers)
        data = [dict(row) for row in csv_reader]
    return data


def parse_tactics(csv_path=f"{CSV_PATH}/tactics.csv"):
    data = csv_to_dict(csv_path)
    parsed_cards = []
    for card_data in data:
        parsed = {
            "id": card_data.get("Id"),
            "name": card_data.get("Name").split("\n"),
            "version": card_data.get("Version"),
            "faction": card_data.get("Faction",""),
            "text": [parse_ability_trigger(parse_ability_text(p.strip())) for p in card_data.get("Text").split(" /")],
        }
        if card_data.get("Remove") != "":
            parsed["remove"] = card_data.get("Remove")
        if card_data.get("Unit") != "":
            parsed["commander_id"] = card_data.get("Unit")
            parsed["commander_name"] = card_data.get("Deck").replace(", ", " - ")
        parsed_cards.append(parsed)
    return parsed_cards


def parse_ability_trigger(paragraphs):
    if len(paragraphs) > 1:
        return {
            "trigger": [f"**{l.strip('*')}**" for l in paragraphs[0]],
            "effect": paragraphs[1:],
        }
    else:
        ix_end_bold = [i for i, v in enumerate(paragraphs[0]) if v.endswith("**")][0]
        return {
            "trigger": [f"**{l.strip('*')}**" for l in paragraphs[0][:ix_end_bold + 1]],
            "effect": paragraphs[0][ix_end_bold + 1:],
        }


def parse_ability_text(text):
    def parse_para(para):
        match = re.match(r"^\[ATTACK:(.*)]$", para)
        if match:
            atk_type, atk_name, atk_stats = match.group(1).split(":")
            hit, dice = atk_stats.split("+")
            return {
                "name": atk_name,
                "type": "long" if "Long" in atk_type else "short" if "Short" in atk_type else "melee",
                "hit": int(hit),
                "dice": [int(d) for d in dice.split(",")]
            }
        else:
            return [line.strip() for line in para.split("\n")]

    paragraphs = [parse_para(p.strip()) for p in text.split("\n\n")]

    return paragraphs

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

def draw_markdown_text_centerv3(image, bold_font, bold_font2, regular_font, regular_font_italic, text_body, color, y_top, x_left, x_right, graphics_folder, units_folder, faction, AsoiafFonts, padding=2):
    all_image_lines = []
    draw = ImageDraw.Draw(image)
    # Define line height using the tallest font (usually the bold one) for consistency
    max_height = max(draw.textbbox((0, 0), 'Hy', font=font)[3] for font in [bold_font, bold_font2, regular_font, regular_font_italic])
    # Calculate the y-coordinate for the text body
    y_current = y_top + 0
    #image.paste(line_image, (x_left, y_top), line_image)
    middle_x = (x_right + x_left) / 2
    # Split the text body by lines
    text_body = text_body.replace('\u202f', '').replace('**.','.**').replace('*.','.*')
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
        y_current += max_height + padding
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

def split_name_stringV0(s, amnt=15):
    # Split the string by comma if it exists
    if ',' in s:
        return s.split(','), True
    if ' ' not in s:
        return [s], False
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

def split_name_string(s, amnt=15):
    # Split the string by comma if it exists
    #if ',' in s:
    #    parts = [part.strip() for part in s.split(',')]
    #    return parts, True if len(parts) > 1 else False
    s = s.replace(',','')
    if ' ' not in s:
        return [s], False
    # Split the string if it's longer than the amnt characters
    if len(s) > amnt:
        # Find all indices of space characters
        space_indices = [i for i, char in enumerate(s) if char == ' ']
        
        # Function to find the best split index
        def find_best_split(indices, target):
            # Find the space closest to the target index
            closest = min(indices, key=lambda x: abs(x - target))
            return closest
        
        # Calculate the ideal section length
        ideal_section_length = len(s) // 3 if len(s) > (2 * amnt) else len(s) // 2
        
        # Find the best indices to split
        first_split = find_best_split(space_indices, ideal_section_length)
        second_split = find_best_split(space_indices, 2 * ideal_section_length) if len(s) > (2 * amnt) else None
        
        # Perform the split
        if second_split is not None:
            return [s[:first_split], s[first_split + 1:second_split], s[second_split + 1:]], False
        else:
            return [s[:first_split], s[first_split + 1:]], False
    
    # If string doesn't need splitting
    return [s], False


def draw_centered_text(draw, position, text_lines_list, font, fill, line_padding=0):
    total_height = sum([font.getbbox(line)[3] - font.getbbox(line)[1] for line in text_lines_list]) + line_padding * (len(text_lines_list) - 1)

    x, y = position
    y -= total_height / 2  # Adjust y-coordinate to start drawing from.

    for line in text_lines_list:
        text_width, text_height = font.getbbox(line)[2], font.getbbox(line)[3] - font.getbbox(line)[1]
        draw.text((x - text_width / 2, y), line, font=font, fill=fill)
        y += text_height + line_padding

def AddTacticsCardTextWithTranslations(card_image, TacticsCardData, units_folder, attachments_folder, graphics_folder, tactics_folder, AsoiafFonts, AsoiafData, ncus_folder, lang, AsoiafDataTranslations):
    # {'Faction': 'Lannister', 'Deck': 'Lannister Basic Deck', 'Unit': '', 
    # 'Name': 'Intrigue and\nSubterfuge', 'Text': '**When an enemy NCU Activates:**\n\nThat NCU loses all Abilities\nuntil the end of the Round.\n\nIf you Control [MONEY], target\n1 enemy Combat Unit. That\nenemy becomes **Weakened**.',
    # 'Id': '40101', 'Remove': '', 'Version': '2021'}
    faction = TacticsCardData['Faction']
    faction_text_clean = re.sub(r'[^A-Za-z]', '', faction)
    TacticsId = TacticsCardData['Id']
    name = TacticsCardData['Name'].replace('\n',' ')
    Deck = TacticsCardData.get("Deck", False)
    isCommander = bool(Deck) and 'basic' not in Deck.lower()
    CardText = TacticsCardData['Text']

    translated_tactics_data = False
    if AsoiafDataTranslations:
        translated_tactics_data = [x for x in AsoiafDataTranslations['tactics'] if x['Id'].strip() == TacticsCardData['Id'].strip()][0]
        name = translated_tactics_data['Name'].replace('\n',' ')
        Deck = translated_tactics_data.get("Deck", False)
        CardText = translated_tactics_data['Text']
    commander_name = Deck
    tmp_line = [[y.strip() for y in x.split('/\n')] for x in CardText.split(' /')]
    lines_of_CardText = []
    for elem in tmp_line:
        for e in elem:
            lines_of_CardText.append(e)
    left_right_top_offset = 40
    top_to_bottom_border_height = card_image.size[1] - int(left_right_top_offset * 2)
    left_to_right_border_width = card_image.size[0] - int(left_right_top_offset * 2) - 40

    hor_bar1 = Image.open(f"./assets/Attachments/Bar{faction_text_clean}.webp").convert('RGBA')
    DecorStar1 = Image.open(f"./assets/Tactics/Decor{faction_text_clean}.webp").convert('RGBA')
    SkillDivider = Image.new('RGBA', (left_to_right_border_width+DecorStar1.size[0]+ 15, DecorStar1.size[1]), (255, 255, 255, 0))
    decorOffset = int(DecorStar1.size[0]/2)
    half_height_width = int(hor_bar1.size[1]/2)
    hor_bar1 = hor_bar1.crop((0, 0, left_to_right_border_width+DecorStar1.size[0] - 15, DecorStar1.size[1]))
    SkillDivider.paste(hor_bar1, (decorOffset, decorOffset-half_height_width), hor_bar1)
    SkillDivider.paste(DecorStar1, (0, 0), DecorStar1)
    SkillDivider.paste(DecorStar1, (left_to_right_border_width + 15, 0), DecorStar1)

    GBFont = AsoiafFonts.get('Tuff-Bold-40',ImageFont.load_default())
    TN = AsoiafFonts.get('Tuff-Bold-40',ImageFont.load_default())
    TN30 = AsoiafFonts.get('Tuff-Normal-34',ImageFont.load_default())
    TN30I = AsoiafFonts.get('Tuff-Italic-34',ImageFont.load_default())
    if (len(lines_of_CardText) >= 2 and len(CardText) > 300) or len(CardText) > 430:
        # Some cards had a bunch of text on them
        GBFont = AsoiafFonts.get('Tuff-Bold-38',ImageFont.load_default())
        TN = AsoiafFonts.get('Tuff-Bold-38',ImageFont.load_default())
        TN30 = AsoiafFonts.get('Tuff-Normal-32',ImageFont.load_default())
        TN30I = AsoiafFonts.get('Tuff-Italic-32',ImageFont.load_default())
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
    FactionColor = "#7FDBFF" 
    if faction in FactionColors:
        FactionColor = FactionColors[faction]
    textBoundLeft = 98
    textBoundRight = 650
    yAbilityOffset = 370
    dividerYPadding = 0
    dividerOffset = 10
    def addDivider(x, y):
        div = SkillDivider.copy()
        card_image.paste(div, (x+ 15, y+dividerYPadding), div)
        return div.size[1] + dividerOffset + int(dividerYPadding/2)
    for i in range(len(lines_of_CardText)):
        line = lines_of_CardText[i]
        card_image, yAbilityOffset = draw_markdown_text_centerv3(card_image, GBFont, TN, TN30, TN30I, line, FactionColor, yAbilityOffset-4, textBoundLeft, textBoundRight, graphics_folder, units_folder, faction, AsoiafFonts, padding=4)
        if i < len(lines_of_CardText)-1:
            yAbilityOffset += addDivider(left_right_top_offset-decorOffset, yAbilityOffset)
    isCommanderOffsetX = 0 if isCommander else -24
    isCommanderOffsetY = 32
    draw = ImageDraw.Draw(card_image)
    #if not isCommander:
    #    
    TuffBoldFont = AsoiafFonts.get('Tuff-Bold-43', ImageFont.load_default())
    if lang in ['de','fr']:
        TuffBoldFont = AsoiafFonts.get('Tuff-Bold-40', ImageFont.load_default()) 
    if isCommander:
        CmdrTuffBoldFont = AsoiafFonts.get('Tuff-Bold-38', ImageFont.load_default())
        if len(commander_name) > 46:
            CmdrTuffBoldFont = AsoiafFonts.get('Tuff-Bold-28', ImageFont.load_default())
        elif len(commander_name) > 40:
            CmdrTuffBoldFont = AsoiafFonts.get('Tuff-Bold-30', ImageFont.load_default())
        elif len(commander_name) > 30:
            CmdrTuffBoldFont = AsoiafFonts.get('Tuff-Bold-34', ImageFont.load_default())
        draw_centered_text(draw, (int(card_image.size[0]/2), 297), [commander_name.upper()], CmdrTuffBoldFont, "white", line_padding=10)
    #print(name)
    line_limit = 16
    text_lines_list, hadAComma = split_name_string(name.upper(), amnt=line_limit)
    if len(text_lines_list) == 1:
        if len(text_lines_list[0]) > line_limit:
            TuffBoldFont = AsoiafFonts.get('Tuff-Bold-39', ImageFont.load_default())
            if lang in ['de','fr']:
                TuffBoldFont = AsoiafFonts.get('Tuff-Bold-36', ImageFont.load_default())
        draw_centered_text(draw, (540+isCommanderOffsetX, 90+isCommanderOffsetY), [text_lines_list[0]], TuffBoldFont, "white", line_padding=10)
    elif len(text_lines_list) == 2:
        if any([len(x) > line_limit for x in text_lines_list]):
            TuffBoldFont = AsoiafFonts.get('Tuff-Bold-39', ImageFont.load_default())
            if lang in ['de','fr']:
                TuffBoldFont = AsoiafFonts.get('Tuff-Bold-36', ImageFont.load_default())
        draw_centered_text(draw, (540+isCommanderOffsetX, 70+isCommanderOffsetY), [text_lines_list[0]], TuffBoldFont, "white", line_padding=10)
        draw_centered_text(draw, (540+isCommanderOffsetX, 74+isCommanderOffsetY + TuffBoldFont.size ), [text_lines_list[1]], TuffBoldFont, "white", line_padding=10)
    else:
        if any([len(x) > line_limit for x in text_lines_list]):
            TuffBoldFont = AsoiafFonts.get('Tuff-Bold-39', ImageFont.load_default())
            if lang in ['de','fr']:
                TuffBoldFont = AsoiafFonts.get('Tuff-Bold-36', ImageFont.load_default())
        draw_centered_text(draw, (540+isCommanderOffsetX, 55+isCommanderOffsetY), [text_lines_list[0]], TuffBoldFont, "white", line_padding=10)
        draw_centered_text(draw, (540+isCommanderOffsetX, 58+isCommanderOffsetY + TuffBoldFont.size ), [text_lines_list[1]], TuffBoldFont, "white", line_padding=10)
        draw_centered_text(draw, (540+isCommanderOffsetX, 63+isCommanderOffsetY + TuffBoldFont.size + TuffBoldFont.size ), [text_lines_list[2]], TuffBoldFont, "white", line_padding=10)
    VersionFont = AsoiafFonts.get('Tuff-BoldItalic-30', ImageFont.load_default())
    text_image = Image.new('RGBA', [160, 40], (255, 255, 255, 0))  # transparent background
    text_draw = ImageDraw.Draw(text_image)
    text_draw.text((0, 0), TacticsCardData['Version'], font=VersionFont, fill="white")
    # Rotate the text image
    rotated_text_image = text_image.rotate(90, expand=1)
    # Paste the rotated text image onto your main image (consider using the alpha channel for proper transparency)
    card_image.paste(rotated_text_image, (rotated_text_image.width - 27, card_image.size[1] - rotated_text_image.height - 80), rotated_text_image)
    return card_image
    #else:
    #    text_lines_list, hadAComma = split_name_string(AttachData['Name'].upper(), amnt=11)
    #    if len(text_lines_list) == 1:
    #        draw_centered_text(draw, (540+isCommanderOffsetX, 120+isCommanderOffsetY), [text_lines_list[0]], TuffBoldFont, "white", line_padding=10)
    #    else:
    #        if "SCORPION MODIFICATION" in AttachData['Name'].upper():
    #            TuffBoldFont = AsoiafFonts.get('Tuff-Bold-28', ImageFont.load_default())
    #        draw_centered_text(draw, (540+isCommanderOffsetX, 100+isCommanderOffsetY), [text_lines_list[0]], TuffBoldFont, "white", line_padding=10)
    #        draw_centered_text(draw, (540+isCommanderOffsetX, 104+isCommanderOffsetY + TuffBoldFont.size ), [text_lines_list[1]], TuffBoldFont, "white", line_padding=10)

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

def main():
    lang = "en"
    if len(sys.argv) > 1:
        lang = sys.argv[1]
    fonts_dir=f"./fonts/"
    warcouncil_latest_csv_folder = './warcouncil_latest_csv/'
    AsoiafFonts = load_fonts(fonts_dir)
    assets_folder="./assets/"
    data_folder=f"{assets_folder}data/"
    units_folder=f"{assets_folder}Units/"
    attachments_folder=f"{assets_folder}Attachments/"
    graphics_folder = f"{assets_folder}graphics"
    tactics_folder = f"{assets_folder}Tactics/"
    ncus_folder = f"{assets_folder}NCUs/"
    warcouncil_latest_csv_folder = './warcouncil_latest_csv/'
    TacticCardsOutputDir  = f"./{lang}/tacticscards/"
    if not os.path.exists(TacticCardsOutputDir):
        Path(TacticCardsOutputDir).mkdir(parents=True, exist_ok=True)
    if not os.path.exists(TacticCardsOutputDir+"png/"):
        Path(TacticCardsOutputDir+"png/").mkdir(parents=True, exist_ok=True)
    if not os.path.exists(TacticCardsOutputDir+"jpg/"):
        Path(TacticCardsOutputDir+"jpg/").mkdir(parents=True, exist_ok=True)
    tactics = parse_tactics()
    AsoiafData = import_csvs_to_dicts(data_folder) # contains the keys: attachments,boxes,ncus,newskills,rules,special,tactics,units
    AsoiafDataTranslations = False
    if lang != "en":
        AsoiafDataTranslations = import_csvs_to_dicts(warcouncil_latest_csv_folder, lang)
    for ix, t in enumerate(tactics):
        # if ix < 187:
        #     continue
        gen = build_tactics_card(t)
        if not gen:
            continue
        TacticsCardData = [x for x in AsoiafData['tactics'] if t['id'].strip() == x['Id']][0]
        gen = AddTacticsCardTextWithTranslations(gen, TacticsCardData, units_folder, attachments_folder, graphics_folder, tactics_folder, AsoiafFonts, AsoiafData, ncus_folder, lang, AsoiafDataTranslations)
        gen = add_rounded_corners(gen, 15)
        tactic_card_output_path = os.path.join(TacticCardsOutputDir+"png/", f"{t['id']}.png")
        gen.save(tactic_card_output_path)
        gen = gen.convert("RGB")
        tactic_card_output_path = os.path.join(TacticCardsOutputDir+"jpg/", f"{t['id']}.jpg")
        gen.save(tactic_card_output_path)

if __name__ == "__main__":
    main()
