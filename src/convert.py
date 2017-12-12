"""
This script converts Israblog html (complete) backup files to an XML file
"""
import logging
import re
import os
import codecs

BACKUP_FOLDER = '/users/eliram/Documents/israblog'
TEMPLATE_FILE = 'template.html'

STATE_OUT = 1
STATE_POST = 2
STATE_COMMENT = 3


class BlogPost(object):
    def __init__(self, post_id):
        """

        :param str post_id:
        """
        self.post_id = post_id  # type: str
        self.title = None  # type: str
        self.body = None  # type: str
        self.ts = None  # type: float
        self.comments = {}


class BlogComment(object):
    def __init__(self, comment_id):
        """

        :param str comment_id:
        """
        self.comment_id = comment_id
        self.name = None
        self.ts = None


class ParseBackupFile(object):
    """
    Parse the HTML

    """

    def __init__(self, backup_file_text):
        """

        :param list backup_file_text: a list of lines
        """
        self.backup_file_text = backup_file_text  # type: str
        self.state = STATE_OUT
        self.previous_state = self.state
        self.current_blog_post = None
        self.current_blog_comment = None

    def clear_data(self):
        self.current_blog_post = None
        self.current_blog_comment = None

    def process_row(self, row):
        pass

    def process(self):
        rows = self.backup_file_text.splitlines()
        for row in rows:
            self.process_row(row)
            self.previous_state = self.state



def parse_backup_files(backup_files_list):
    """
    :param list backup_files_list: a list of html file names
    :return: all parsed data
    :rtype: dict
    """
    parsed_data = {}
    for filename in backup_files_list:
        with codecs.open(os.path.join(BACKUP_FOLDER, filename), encoding='cp1255') as backup_file:
            file_text = backup_file.readlines()
        parse_obj = ParseBackupFile(file_text)
        parsed_data.update(parse_obj.process())
    return parsed_data


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


def save_parsed_data(parsed_data):
    """
    Save the data as XML
    :param dict parsed_data:
    """
    pass


def main():
    backup_files_list = get_backup_files()
    parsed_data = parse_backup_files(backup_files_list)
    save_parsed_data(parsed_data)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
