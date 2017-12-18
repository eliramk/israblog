#!/bin/python
# -*- coding: utf-8 -*-

"""
Try to download all posts for a certain blog (html only, post-by-post)
"""

import urllib2
import logging
import re
import os
from time import sleep
import datetime

BLOG_NUMBER_START = 860340  # A string containing the blog number. e.g. '11990'
BLOG_NUMBER_END = 860350
START_FROM_POST_NUMBER = None  # '3820213'  # Optional. Use None or a string containing the post number to move back from. e.g. '3754624'
STOP_AT_POST_NUMBER = None  # '3708275'  # Optional

BLOG_URL = 'http://israblog.nana10.co.il/blogread.asp?blog=%s'
BASE_URL = 'http://israblog.nana10.co.il/blogread.asp'
POST_URL = 'http://israblog.nana10.co.il/blogread.asp?blog=%s&blogcode=%s'
COMMENTS_URL = 'http://israblog.nana10.co.il/comments.asp?blog=%s&user=%s'
BACKUP_FOLDER = '/users/eliram/Documents/israblog2'
if not os.path.exists(BACKUP_FOLDER):
    BACKUP_FOLDER = os.path.dirname(os.path.realpath(__file__))
LOG_FILE = os.path.join(BACKUP_FOLDER, 'log/backup_%s-%s_%s.log' % (BLOG_NUMBER_START, BLOG_NUMBER_END, datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')))

# RegEx
RE_POST_URL_PATTERN = '\?blog=%s&amp;blogcode=\d+'
RE_INITIAL_BLOG_CODE = 'blogcode=(\d+)'
RE_PREVIOUS_POST = '<a title="לקטע הקודם" href="/blogread.asp\?blog=%s&amp;blogcode=(\d+)" class="blog">'
RE_COMMENTS_NEXT_PAGE = 'href="comments\.asp\?.*&posnew=(\d+)">לדף הבא</a>'
RE_TIMESTAMP = '(\d\d?/\d\d?/\d\d\d\d(\xc2\xa0|/s|&nbsp;|\xa0)\d\d?:\d\d)\r\n'


class BlogPost(object):
    def __init__(self, post_number, saved=True):
        self.post_nubmer = post_number
        self.saved = saved
        self.comments_saved = False
        self.comment_pages = 0
        self.timestamp = None  # type: int


class BlogCrawl(object):
    def __init__(self, blog_number):
        self.blog_number = blog_number  # type: int
        self.posts = {}
        self.comment_pages = 0
        self.re_post_url_pattern = RE_POST_URL_PATTERN % blog_number
        self.re_previous_post = RE_PREVIOUS_POST % blog_number
        self.blog_folder = os.path.join(BACKUP_FOLDER, str(blog_number))
        self.current_post = None  # type: BlogPost

    def get_next_page_number(self, comments_html, comments_page_number=None):
        """

        :param str comments_html:
        :param int comments_page_number:
        :return:
        :rtype: int
        """
        try:
            next_page = re.search(RE_COMMENTS_NEXT_PAGE, comments_html).group(1)
            if next_page != str(comments_page_number + 1):
                logging.warning('NEXT PAGE IS %s while current page is %d', next_page, comments_page_number)
            else:
                logging.info('Found comments page #%s' % next_page)
        except Exception:
            if '>לדף הבא</a>' in comments_html:
                next_page = comments_page_number + 1
                logging.info('Trying next comments page #%s' % next_page)
            else:
                return None

        return int(next_page)

    def parse_date(self, post_html):
        try:
            date_str = re.search(RE_TIMESTAMP, post_html).group(1)
        except AttributeError as ex:
            return

        date_array = date_str.split('\xc2\xa0')[0].split('/')
        time_array = date_str.split('\xc2\xa0')[1].split(':')
        date_obj = datetime.datetime(int(date_array[2]),
                                     int(date_array[1]),
                                     int(date_array[0]),
                                     int(time_array[0]),
                                     int(time_array[1]),
                                     0)
        # new_post.date_str = date_str
        ts = (date_obj - datetime.datetime(1970, 1, 1)).total_seconds()
        self.current_post.timestamp = ts

    def process_post(self, post_url, post_number):
        """

        :param str post_url:
        :param str post_number:
        :return:
        :rtype: str
        """
        post_html = urllib2.urlopen(post_url).read()
        self.current_post = BlogPost(post_number)
        self.posts[post_number] = self.current_post

        # We're also converting to unicode, because it's the right thing to do
        try:
            post_html = post_html.decode("cp1255", errors='ignore')
        except Exception as ex:
            logging.error('Could not decode post_html')

        try:
            post_html = post_html.encode('UTF-8', errors='ignore')
            post_html = post_html.replace('TEXT/HTML; CHARSET=WINDOWS-1255', 'TEXT/HTML; CHARSET=UTF-8')
        except Exception as ex:
            logging.error('Could not encode post_html to UTF-8')

        # logging.debug(post_html)

        # post_number = re.search(RE_INITIAL_BLOG_CODE, post_url).group(1)
        logging.info('Post #%s', post_number)

        filename = os.path.join(self.blog_folder, 'post_%s.html' % post_number)
        with open(filename, mode='w') as output_file:
            output_file.write(post_html)

        self.parse_date(post_html)
        if self.current_post.timestamp is not None:
            os.utime(filename, (self.current_post.timestamp, self.current_post.timestamp))

        next_post_number = None
        try:
            next_post_number = re.search(self.re_previous_post, post_html).group(1)
            logging.info('next_post_number=%s', next_post_number)
        except Exception:
            # logging.debug(post_html)
            # logging.debug(RE_PREVIOUS_POST)
            pass

        # Get post comments
        comments_page_number = 1
        comments_url = self.get_comments_url(post_number)

        while comments_url is not None:
            logging.info(comments_url)
            comments_html = urllib2.urlopen(comments_url).read()
            self.comment_pages += 1
            try:
                comments_html = comments_html.decode("cp1255", errors='ignore')
                comments_html = comments_html.encode('UTF-8', errors='ignore')
                comments_html = comments_html.replace('text/html;charset=windows-1255', 'text/html;charset=utf-8')
            except Exception:
                pass

            comments_filename = os.path.join(
                self.blog_folder,
                'post_%s_comments%s.html' % (
                    post_number,
                    '_p%s' % comments_page_number if comments_page_number > 1 else ''))
            with open(comments_filename, mode='w') as output_file:
                # We're also converting to unicode, because it's the right thing to do
                output_file.write(comments_html)
            if self.current_post.timestamp is not None:
                os.utime(comments_filename, (self.current_post.timestamp, self.current_post.timestamp))

            comments_page_number = self.get_next_page_number(comments_html, comments_page_number=comments_page_number)
            if comments_page_number is None:
                comments_url = None
            else:
                comments_url = self.get_comments_url(post_number, comments_page_number)

        return next_post_number

    def get_post_url(self, post_number):
        return POST_URL % (self.blog_number, post_number)

    def get_comments_url(self, post_number, page_number=1):
        """

        :param str post_number:
        :param int page_number:
        :return:
        :rtype: str
        """
        if page_number is None:
            return None
        comments_url = COMMENTS_URL % (post_number, self.blog_number)
        if page_number > 1:
            comments_url += '&posnew=%d' % page_number
        return comments_url

    def process_blog(self):
        """

        :rtype:
        """
        blog_url = BLOG_URL % self.blog_number
        if START_FROM_POST_NUMBER is None:
            initial_page = urllib2.urlopen(blog_url).read()
            try:
                next_post_url = re.search(self.re_post_url_pattern, initial_page).group(0).replace('&amp;', '&')
                next_post_number = next_post_url.split('blogcode=')[1]
                logging.info(next_post_url)
            except Exception as ex:
                logging.error('Could not find post URL for blog %s', blog_url)
                return

            next_post_url = BASE_URL + next_post_url
        else:
            next_post_url = self.get_post_url(START_FROM_POST_NUMBER)
            next_post_number = STOP_AT_POST_NUMBER

        if not os.path.exists(self.blog_folder):
            os.makedirs(self.blog_folder)

        while next_post_number is not None:
            logging.debug('Post %s %s', next_post_number, next_post_url)
            next_post_number = self.process_post(next_post_url, next_post_number)

            if STOP_AT_POST_NUMBER and next_post_number and next_post_number == STOP_AT_POST_NUMBER:
                logging.warning('Reached post marked as stop point %s', STOP_AT_POST_NUMBER)
                next_post_number = None

            if next_post_number is None:
                logging.warning('Could not find another post')
            else:
                next_post_url = self.get_post_url(next_post_number)
            # Don't strain the server too much.
            sleep(0.1)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    if not os.path.exists(os.path.join(BACKUP_FOLDER, 'log')):
        os.makedirs(os.path.join(BACKUP_FOLDER, 'log'))
    with open(LOG_FILE, mode='a') as log_file:
        log_file.write('"Blog Number","Posts","Comment Pages","Timestamp"\n')
    for blog_number in range(BLOG_NUMBER_START, BLOG_NUMBER_END + 1):
        blog_crawl = BlogCrawl(str(blog_number))
        blog_crawl.process_blog()
        with open(LOG_FILE, mode='a') as log_file:
            log_file.write('%d,%d,%d,%s\n' % (blog_number, len(blog_crawl.posts), blog_crawl.comment_pages, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
