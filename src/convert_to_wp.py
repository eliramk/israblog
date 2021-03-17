#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This script converts Israblog html (complete) backup files to an XML file
# Originally written by Eliram (@eliramk)
# Updated for wordpress by Shir (@shirblc)

import logging
import re
import os
import datetime
import json
from convert import (
                    get_post_enum,
                    get_comment_enum,
                    sanitize_text,
                    get_backup_files
                    )

BACKUP_FOLDER = './isra'
TEMPLATE_FILE = 'template.html'
OUTPUT_FORMAT = 'xml'
OUTPUT_FILENAME = os.path.join(BACKUP_FOLDER, 'blog.' + OUTPUT_FORMAT)

STATE_OUT = 1
STATE_POST = 2
STATE_COMMENT = 3

RE_COMMENT = '<p class="MsoNormal" dir="RTL" lang="HE" style="font-size:10.0pt; font-family: Arial; margin-right:([\d\.]+)in">(.*)'
RE_POST = '<p class="MsoNormal" dir="RTL" lang="HE" style="font-size:12.0pt; font-family: Arial">'
RE_BREAKER_AND_POST = '<br clear="all" style="mso-special-character:line-break;page-break-before:always"><p class="MsoNormal" dir="RTL" lang="HE" style="font-size:12.0pt; font-family: Arial">'
RE_DATE = '>(\d\d?/\d\d?/\d{1,4} \d\d?:\d\d?:\d\d?)<'
RE_PAGE_END = '<!--xgemius|<script '
RE_COMMENT_TS = ', (\d\d?:\d\d? \d\d?/\d\d?/\d{1,4}):<br>'
post_enum = 0
comment_enum = 0

class BlogPost(object):
    def __init__(self, post_id=None):
        """

        :param str post_id:
        """
        self.post_id = post_id or get_post_enum()  # type: int
        self.title = None  # type: unicode
        self.body = ''  # type: unicode
        self.ts = None  # type: float
        self.date_str = None  # type: str
        self.comments = []  # type: dict(BlogComment)

    def get_dict(self):
        d = {
            'post_id': self.post_id,
            'title': self.title,
            'body': self.body,
            'ts': self.ts,
            'date_str': self.date_str,
            'comments_num': len(self.comments),
            'comments': []
        }
        for comment in self.comments:  # type: BlogComment
            d['comments'].append(comment.get_dict())
        return d

    def __repr__(self):
        if OUTPUT_FORMAT == 'json':
            return json.dumps(self.get_dict(), ensure_ascii=False, indent=4)
        else:
            rep = '<item>\n'
            rep += '<title>%s</title>\n' % sanitize_text(self.title)
            rep += '<link>https://wordpress.com/</link>\n'
            rep += '<pubDate>%s</pubDate>\n' % self.date_str
            rep += """<dc:creator>user</dc:creator>
                    <guid isPermaLink="false">https://wordpress.com/</guid>
        	        <description></description>\n"""
            rep += '<content:encoded><![CDATA[\n%s]]></content:encoded>\n' % self.body
            rep += """<excerpt:encoded><![CDATA[]]></excerpt:encoded>
        	       <wp:post_id>{post_id}</wp:post_id>
                   <wp:comment_status>open</wp:comment_status>
               	   <wp:ping_status>open</wp:ping_status>\n""".format(post_id=self.post_id)
            rep += '<wp:post_name>%s</wp:post_name>' % sanitize_text(self.title)
            rep += """<wp:status>publish</wp:status>
                    <wp:post_parent>0</wp:post_parent>
               	    <wp:menu_order>0</wp:menu_order>
               	    <wp:post_type>post</wp:post_type>
               	    <wp:post_password></wp:post_password>
               	    <wp:is_sticky>0</wp:is_sticky>\n"""
            for comment in self.comments:
                rep += comment.__repr__()
            rep += '</item>\n'
            return rep


class BlogComment(object):
    def __init__(self, comment_id=None):
        """

        :param str comment_id:
        """
        self.comment_id = comment_id or get_comment_enum()  # type: int
        self.name = None  # type: str
        self.email = None  # type: str
        self.url = None  # type: str
        self.ts = None  # type: float
        self.date_str = None  # type: str
        self.indent = -1  # type: float
        self.level = -1  # type: int
        self.parent_id = None  # type: int
        self.post_id = None  # type: int
        self.body = None  # type: str

    def get_dict(self):
        d = {
            'id': self.comment_id,
            'name': self.name,
            'email': self.email,
            'url': self.url,
            'ts': self.ts,
            'date_str': self.date_str,
            'level': self.level,
            'post_id': self.post_id,
        }
        if self.parent_id:
            d['parent_id'] = self.parent_id
        return d

    def __repr__(self):
        rep = '<wp:comment>\n'
        rep += '<wp:comment_id>%s</wp:comment_id>\n' % self.comment_id
        rep += '<wp:comment_author><![CDATA[%s]]></wp:comment_author>\n' % sanitize_text(self.name)
        rep += '<wp:comment_author_email>%s</wp:comment_author_email>\n' % sanitize_text(self.email)
        rep += '<wp:comment_author_url>%s</wp:comment_author_url>\n' % sanitize_text(self.url)
        rep += '<wp:comment_author_IP></wp:comment_author_IP>\n'
        rep += '<wp:comment_date>%s</wp:comment_date>\n' % self.date_str
        rep += '<wp:comment_content><![CDATA[%s]]></wp:comment_content>\n' % self.body
        rep += '<wp:comment_approved>1</wp:comment_approved>\n<wp:comment_type></wp:comment_type>\n'
        rep += '<wp:comment_parent>{parent_id}</wp:comment_parent>\n'.format(parent_id=' parent_id="%d"' % self.parent_id if self.parent_id else 0)
        rep += '</wp:comment>\n'

        return rep


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
        # self.previous_state = self.state
        self.current_blog_post = None  # type: BlogPost
        self.current_blog_comment = None  # type: BlogComment
        self.posts = []
        self.comments = []
        self.internal_row_enum = 0
        self.comment_parent_track = {}  # Keeps the latest comment for each comment level

    def clear_data(self):
        self.current_blog_post = None  # type: BlogPost
        self.current_blog_comment = None  # type: BlogComment
        self.internal_row_enum = 0
        self.comment_parent_track = {}

    def parse_post_header(self, row):
        """
        Create a new blogpost object, add data and set as current post
        :param str row:
        """
        try:
            date_str = re.search(RE_DATE, row).group(1)
        except Exception:
            return None

        new_post = BlogPost()
        date_array = date_str.split(' ')[0].split('/')
        time_array = date_str.split(' ')[1].split(':')
        date_obj = datetime.datetime(int(date_array[2]),
                                     int(date_array[1]),
                                     int(date_array[0]),
                                     int(time_array[0]),
                                     int(time_array[1]),
                                     int(time_array[2]))
        new_post.date_str = date_str
        new_post.ts = (date_obj - datetime.datetime(1970, 1, 1)).total_seconds()
        new_post.body = ''

        self.current_blog_post = new_post
        self.posts.append(new_post)

    def parse_comment_header(self, row):
        comment_header = re.search(RE_COMMENT, row)
        new_comment = BlogComment()

        new_comment.post_id = self.current_blog_post.post_id
        new_comment.indent = float(comment_header.group(1))
        new_comment.level = int(round(new_comment.indent * 5))
        if new_comment.level > 0:
            new_comment.parent_id = self.comment_parent_track.get('L%d' % (new_comment.level - 1), None)
        self.comment_parent_track['L%d' % new_comment.level] = new_comment.comment_id

        try:
            details = comment_header.group(2).split('&nbsp;')
        except Exception:
            details = []

        if len(details) > 0:
            new_comment.name = details[0]
        if len(details) > 1:
            new_comment.email = details[1]
        if len(details) > 2:
            new_comment.url = details[2].lstrip('(').rstrip(')')

        new_comment.body = ''

        self.current_blog_comment = new_comment
        self.comments.append(new_comment)
        self.current_blog_post.comments.append(new_comment)

    def set_state(self, new_state):
        self.internal_row_enum = 0
        if self.state != new_state:
            if new_state != STATE_COMMENT:
                self.current_blog_comment = None
        self.state = new_state

    def process_row(self, row):
        """

        :type row: str
        """

        if self.state == STATE_OUT:
            if re.search(RE_POST, row):
                self.parse_post_header(row)
                self.set_state(STATE_POST)

        elif self.state == STATE_POST:
            self.internal_row_enum += 1
            if self.internal_row_enum == 1:
                # This is the post's title
                if row.endswith('<br>\n'):
                    self.current_blog_post.title = row[:-5]
                elif row.endswith('<br>'):
                    self.current_blog_post.title = row[:-4]
                else:
                    # We'll take what there is here
                    self.current_blog_post.title = row.rstrip('<br>')
            elif re.search(RE_COMMENT, row):
                # a blog comment started
                self.parse_comment_header(row)
                self.set_state(STATE_COMMENT)
            elif re.search(RE_BREAKER_AND_POST, row):
                self.parse_post_header(row)
                self.set_state(STATE_POST)
            elif re.search(RE_PAGE_END, row):
                self.set_state(STATE_OUT)
            else:
                self.current_blog_post.body += row.replace('<br>', '<br/>') + '\n'
        elif self.state == STATE_COMMENT:
            self.internal_row_enum += 1
            if self.internal_row_enum == 1:
                # This should be a timestamp
                if re.search(RE_COMMENT_TS, row):
                    date_str = re.search(RE_COMMENT_TS, row).group(1)
                    self.current_blog_comment.date_str = date_str
                    date_array = date_str.split(' ')[1].split('/')
                    time_array = date_str.split(' ')[0].split(':')
                    date_obj = datetime.datetime(int(date_array[2]),
                                                 int(date_array[1]),
                                                 int(date_array[0]),
                                                 int(time_array[0]),
                                                 int(time_array[1]),
                                                 int(time_array[2]) if len(time_array) > 2 else 0)
                    self.current_blog_comment.ts = (date_obj - datetime.datetime(1970, 1, 1)).total_seconds()
                else:
                    # Just add as-is
                    self.current_blog_comment.body += row + '\n'
            elif re.search(RE_POST, row) or re.search(RE_BREAKER_AND_POST, row):
                self.parse_post_header(row)
                self.set_state(STATE_POST)
            elif re.search(RE_COMMENT, row):
                # a new blog comment started
                self.parse_comment_header(row)
                self.set_state(STATE_COMMENT)
            elif re.search(RE_PAGE_END, row):
                self.set_state(STATE_OUT)
            else:
                self.current_blog_comment.body += row.replace('<br>', '<br/>') + '\n'

    def process(self):
        # rows = self.backup_file_text.splitlines()

        for row in self.backup_file_text:
            self.process_row(row)

        logging.info('Processed %d posts and %d comments', len(self.posts), len(self.comments))
        return self.posts


def parse_backup_files(backup_files_list):
    """
    :param list backup_files_list: a list of html file names
    :return: all parsed data
    :rtype: dict
    """
    parsed_data = []
    for filename in backup_files_list:
        with open(os.path.join(BACKUP_FOLDER, filename), encoding='cp1255') as backup_file:
            file_text = backup_file.read()
        #file_text = file_text.decode("cp1255", errors='ignore')
        #file_text = file_text.encode('UTF-8', errors='ignore')
        parse_obj = ParseBackupFile(file_text.splitlines())
        new_data = parse_obj.process()
        parsed_data += new_data

    logging.info('Total %d posts.', len(parsed_data))
    return parsed_data


def save_parsed_data(parsed_data):
    """
    Save the data as XML
    :param dict parsed_data:
    """
    with open(OUTPUT_FILENAME, mode='w') as output_file:
        output_file.write("""<?xml version="1.0" encoding="UTF-8" ?>
        <!-- This is a WordPress eXtended RSS file generated by WordPress as an export of your site. -->
        <!-- It contains information about your site's posts, pages, comments, categories, and other content. -->
        <!-- You may use this file to transfer that content from one site to another. -->
        <!-- This file is not intended to serve as a complete backup of your site. -->

        <!-- To import this information into a WordPress site follow these steps: -->
        <!-- 1. Log in to that site as an administrator. -->
        <!-- 2. Go to Tools: Import in the WordPress admin panel. -->
        <!-- 3. Install the "WordPress" importer from the list. -->
        <!-- 4. Activate & Run Importer. -->
        <!-- 5. Upload this file using the form provided on that page. -->
        <!-- 6. You will first be asked to map the authors in this export file to users -->
        <!--    on the site. For each author, you may choose to map to an -->
        <!--    existing user on the site or to create a new user. -->
        <!-- 7. WordPress will then import each of the posts, pages, comments, categories, etc. -->
        <!--    contained in this file into your site. -->

        <!-- generator="WordPress.com" created="2021-03-17 12:26"-->
        <rss version="2.0"
        	xmlns:excerpt="http://wordpress.org/export/1.2/excerpt/"
        	xmlns:content="http://purl.org/rss/1.0/modules/content/"
        	xmlns:wfw="http://wellformedweb.org/CommentAPI/"
        	xmlns:dc="http://purl.org/dc/elements/1.1/"
        	xmlns:wp="http://wordpress.org/export/1.2/"
        >

        <channel>
        	<title>Blog</title>
        	<link>https://wordpress.com</link>
        	<description></description>
        	<pubDate>Wed, 17 Mar 2021 12:26:39 +0000</pubDate>
        	<language></language>
        	<wp:wxr_version>1.2</wp:wxr_version>
        	<wp:base_site_url>http://wordpress.com/</wp:base_site_url>
        	<wp:base_blog_url>https://wordpress.com</wp:base_blog_url>

        	<wp:author><wp:author_id>0</wp:author_id><wp:author_login><![CDATA[user]]></wp:author_login></wp:author>


        	<generator>http://wordpress.com/</generator>
        <image>
        		<url>http://s0.wp.com/i/buttonw-com.png</url>
        		<title>Blog</title>
        		<link>https://wordpress.com</link>
        	</image>\n""")
        for post in parsed_data:
            output_file.write(post.__repr__())
        output_file.write('\n</channel>\n</rss>\n')


def main():
    backup_files_list = get_backup_files(BACKUP_FOLDER)
    parsed_data = parse_backup_files(backup_files_list)
    save_parsed_data(parsed_data)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
