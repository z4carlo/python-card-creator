# asoiaf_card_generator
Takes cmon data from war council apk to generate asoiaf cards. 

Builds the front side of the:
* Attachments
* NCUS
* Tactics
* Specials
* Combat Unis


If you want to build, be in the `flutter_assets` folder and run:

```
pip3 install pillow boto3 
python3 download_csvs.py
```

Then to generate german cards:

```
python3 ncu_card_generator.py de && python3 unit_card_generator.py de && python3 tactics_card_generator.py de && python3 special_card_generator.py de && python3 attachment_card_generator.py de
```

I only tested this on `de`, `fr`, and `en`. 

I dont think im going to work on `scn` or `tcn` translations for a while cause they are asian characters which cant use the default provided ASOIAF fonts (and I'd have to do a lot of work to account for this in my codes handling of fonts).

## Disclaimer:

I realize these cards are not exact copy of the CMON ones in the app. My main goal was to fit all the data onto the cards so they are playable. Please dont report bugs about alignment or spacing etc... Unless its like information doesnt fit on screen or something is rendered/displayed invalidly. 

### Credits:

Credit for tactics cards creation goes to Pf2eTools over at:

https://github.com/Pf2eTools/asoiaf_card_generator/tree/main

Although I tweaked what he started with so his stuff will probably better than mine in the long run once he finishes. 
