"""
This script converts Israblog html (complete) backup files to an XML file
"""
import logging
import re
import os

BACKUP_FOLDER = '/users/eliram/Documents/israblog'
TEMPLATE_FILE = 'template.html'


def get_backup_files():
    """
    Search folder for html backup files
    :return: A list of backup files
    :rtype: list
    """
    all_files = os.listdir(BACKUP_FOLDER)
    logging.debug(all_files)

    file_list = []
    for filename in all_files:
        if filename.endswith('.html') and filename != TEMPLATE_FILE:
            # check if there is a matching folder
            if filename[:-5] + '_files' in all_files:
                file_list.append(filename)

    logging.info('Found %d backup files to process', len(file_list))
    logging.debug(file_list)
    return file_list


def parse_backup_files(backup_files_list):
    """

    :param list backup_files_list: a list of html file names
    :type backup_files_list:
    :return: all parsed data
    :rtype: dict
    """
    parsed_data = {}
    return parsed_data


def save_parsed_data(parsed_data):
    """
    Save the data as XML
    :param dict parsed_data:
    """
    pass


def main():
    logging.basicConfig(level=logging.DEBUG)
    backup_files_list = get_backup_files()
    parsed_data = parse_backup_files(backup_files_list)
    save_parsed_data(parsed_data)


if __name__ == '__main__':
    main()
