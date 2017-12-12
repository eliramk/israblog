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

BLOG_NUMBER = 'ENTER POST NUMBER HERE'  # A string containing the blog number. e.g. '11990'
START_FROM_POST_NUMBER = None  # Optional. Use None or a string containing the post number to move back from. e.g. '3754624'
STOP_AT_POST_NUMBER = None  # Optional

BLOG_URL = 'http://israblog.nana10.co.il/blogread.asp?blog=%s' % BLOG_NUMBER
BASE_URL = 'http://israblog.nana10.co.il/blogread.asp'
POST_URL = 'http://israblog.nana10.co.il/blogread.asp?blog={0:s}&blogcode=%s'.format(BLOG_NUMBER)
COMMENTS_URL = 'http://israblog.nana10.co.il/comments.asp?blog=%s&user={0:s}'.format(BLOG_NUMBER)
BACKUP_FOLDER = '/users/eliram/Documents/israblog2'

# RegEx
RE_POST_URL_PATTERN = '\?blog=%s&amp;blogcode=\d+' % BLOG_NUMBER
RE_INITIAL_BLOG_CODE = 'blogcode=(\d+)'
RE_PREVIOUS_POST = '<a title="לקטע הקודם" href="/blogread.asp\?blog=%s&amp;blogcode=(\d+)" class="blog">' % BLOG_NUMBER
RE_COMMENTS_NEXT_PAGE = 'href="comments\.asp\?.*&posnew=(\d+)">לדף הבא</a>'.format(BLOG_NUMBER)


def get_next_page_url(comments_html, comments_page_number=None):
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


def process_post(post_url):
    """

    :param str post_url:
    :return:
    :rtype: str
    """
    next_post_url = None
    post_html = urllib2.urlopen(post_url).read()

    # We're also converting to unicode, because it's the right thing to do
    try:
        post_html = post_html.decode("cp1255", errors='ignore')
    except Exception as ex:
        logging.error('Could not decode post_html')

    try:
        post_html = post_html.encode('UTF-8', errors='ignore')
    except Exception as ex:
        logging.error('Could not encode post_html to UTF-8')

    # logging.debug(post_html)

    post_number = re.search(RE_INITIAL_BLOG_CODE, post_url).group(1)
    logging.info('Post #%s', post_number)

    filename = os.path.join(BACKUP_FOLDER, 'post_%s.html' % post_number)
    with open(filename, mode='w') as output_file:
        output_file.write(post_html)

    next_post_number = None
    try:
        next_post_number = re.search(RE_PREVIOUS_POST, post_html).group(1)
        logging.info('next_post_number=%s', next_post_number)
    except Exception:
        # logging.debug(post_html)
        # logging.debug(RE_PREVIOUS_POST)
        pass

    # Get post comments
    comments_url = COMMENTS_URL % post_number
    comments_page_number = 1

    while comments_url is not None:
        logging.info(comments_url)
        comments_html = urllib2.urlopen(comments_url).read()
        try:
            comments_html = comments_html.decode("cp1255", errors='ignore')
            comments_html = comments_html.encode('UTF-8', errors='ignore')
        except Exception:
            pass
        # logging.debug(comments_html)

        comments_filename = os.path.join(
            BACKUP_FOLDER,
            'post_%s_comments%s.html' % (
                post_number,
                '_p%s' % comments_page_number if comments_page_number > 1 else ''))
        with open(comments_filename, mode='w') as output_file:
            # We're also converting to unicode, because it's the right thing to do
            output_file.write(comments_html)

        comments_page_number = get_next_page_url(comments_html, comments_page_number=comments_page_number)
        if comments_page_number is None:
            comments_url = None
        else:
            comments_url = COMMENTS_URL % post_number
            comments_url += '&posnew=%d' % comments_page_number

    return next_post_number


def main(blog_url):
    """

    :param str blog_url:
    :type blog_url:
    :rtype:
    """
    if START_FROM_POST_NUMBER is None:
        initial_page = urllib2.urlopen(blog_url).read()
        try:
            next_post_url = re.search(RE_POST_URL_PATTERN, initial_page).group(0).replace('&amp;', '&')
            logging.info(next_post_url)
        except Exception as ex:
            logging.error('Could not find post URL for blog %s', blog_url)
            return
        next_post_url = BASE_URL + next_post_url
    else:
        next_post_url = POST_URL % START_FROM_POST_NUMBER

    while next_post_url is not None:
        logging.info('Post %s', next_post_url)
        next_post_number = process_post(next_post_url)
        if STOP_AT_POST_NUMBER and next_post_number == STOP_AT_POST_NUMBER:
            logging.warning('Reached post marked as stop point %s', STOP_AT_POST_NUMBER)
            next_post_number = None

        if next_post_number is None:
            logging.warning('Could not find previous post')
            next_post_url = None
        else:
            next_post_url = POST_URL % next_post_number
        # Don't strain the server too much.
        sleep(1)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main(BLOG_URL)
