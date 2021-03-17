# Israblog Backup

## Version

Version 12.4.

## Requirements

- Python 3

## Installation and Usage (Source directory!)

1. Save your Israblog backup (in accordance with the main [README](https://github.com/shirblc/israblog/blob/master/README.md)).
2. Download or clone the repo.
3. cd into the project directory.
4. cd into src.
5. Run ```pip install -r requirements.txt``` to install dependencies (they're necessary for the Wordpress conversion).
6. Update the ```BACKUP_FOLDER``` constant to the location of your downloaded backup.
  - If you want to use the Wordpress converter, do it in the [convert_to_wp file](https://github.com/shirblc/israblog/blob/master/src/convert_to_wp.py).
  - Otherwise, do it in the [convert file](https://github.com/shirblc/israblog/blob/master/src/convert.py).
7. Run the script:
  - If using the Wordpress converter, run ```python convert_to_wp.py``` (run ```python3 convert_to_wp.py``` if you're on macOS).
  - If using the regular converter, run ```python convert.py``` (run ```python3 convert.py``` if you're on macOS).

## Contents

1. **convert.py** - Converts the Israblog HTML backup into XML/JSON.
2. **convert_to_wp.py** - Converts the Israblog HTML backup into a Wordpress XML.
3. **download_blog_posts.py** - Crawls over the given blog and saves its posts.

## Dependencies

1. **pytz** - A timezone utility for Python. For more information, check their [PyPI page](https://pypi.org/project/pytz/).

## Known Issues

There are no current issues at the time.
