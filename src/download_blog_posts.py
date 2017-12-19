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

# BLOG_NUMBER_START = 187  # Blog number. e.g. 11990
# BLOG_NUMBER_END = 1000
START_FROM_POST_NUMBER = None  # '3820213'  # Optional. Use None or a string containing the post number to move back from. e.g. '3754624'
STOP_AT_POST_NUMBER = None  # '3708275'  # Optional
SAVE_MONTHLY_PAGES = False

BLOG_URL = 'http://israblog.nana10.co.il/blogread.asp?blog=%s'
BASE_URL = 'http://israblog.nana10.co.il/blogread.asp'
BASE_URL_TBLOG = 'http://israblog.nana10.co.il/tblogread.asp'
POST_URL = 'http://israblog.nana10.co.il/blogread.asp?blog=%s&blogcode=%s'
COMMENTS_URL = 'http://israblog.nana10.co.il/comments.asp?blog=%s&user=%s'

BACKUP_FOLDER = '/users/eliram/Documents/israblog2'
if not os.path.exists(BACKUP_FOLDER):
    BACKUP_FOLDER = os.path.dirname(os.path.realpath(__file__))

# RegEx
RE_POST_URL_PATTERN = '\?blog=%s&a?m?p?;?blogcode=\d+'
RE_INITIAL_BLOG_CODE = 'blogcode=(\d+)'
RE_PREVIOUS_POST = '<a title="לקטע הקודם" href="/blogread.asp\?blog=%s&amp;blogcode=(\d+)" class="blog">'
RE_COMMENTS_NEXT_PAGE = 'href="comments\.asp\?.*&posnew=(\d+)">לדף הבא</a>'
RE_TIMESTAMP = '(\d\d?/\d\d?/\d\d\d\d(\xc2\xa0|/s|&nbsp;|\xa0)\d\d?:\d\d)\r?\n'
RE_DROPDOWN = '<select name="PeriodsForUser".*>(<option.*/option>)</select>'
RE_DROPDOWN_T = '<select .*?name=\'selMonth\'.*\r?\n(<option.*/option>\r?\n)*</select>'
# RE_DROPDOWN_T_START = '<select class=\'list\' name=\'selMonth\''
# RE_DROPDOWN_T_END = </select>
RE_POST_ONLY = '(<table width="100%"><tr><td class="blog">.*)<iframe id='
RE_COMMENTS_ONLY = "(<style>a:active.*)<a name='newcommentlocation'></a>"
POST_ONLY_START = '<table width="100%"><tr><td class="blog">'
POST_ONLY_END = '<iframe id='
COMMENTS_ONLY_START = '<style>a:active'
COMMENTS_ONLY_END = "<a name='newcommentlocation'></a>"


class BlogPost(object):
    def __init__(self, post_number, saved=True):
        self.post_nubmer = post_number
        self.saved = saved
        self.comments_saved = False
        self.comment_pages = 0
        self.timestamp = None  # type: int


class BlogCrawl(object):
    def __init__(self, blog_number):
        """

        :param int blog_number:
        """
        self.blog_number = blog_number  # type: int
        self.posts = {}
        self.comment_pages = 0
        self.re_post_url_pattern = RE_POST_URL_PATTERN % blog_number
        self.re_previous_post = RE_PREVIOUS_POST % blog_number
        self.base_url = BASE_URL  # Could also be tblog
        self.blog_url = BLOG_URL % blog_number
        self.blog_folder = os.path.join(BACKUP_FOLDER, str(blog_number))
        self.current_post = None  # type: BlogPost
        self.months = []
        self.nickname = ''
        self.email = ''
        self.age = ''
        self.title = ''
        self.description = ''
        self.save_template = True  # Save the first post with full html as well?
        self.save_comments_template = True  # Save the first (recent) comments page without modifications
        self.is_tblog = False

    @staticmethod
    def get_next_page_number(comments_html, comments_page_number=None):
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
                logging.debug('Found comments page #%s' % next_page)
        except Exception:
            if '>לדף הבא</a>' in comments_html:
                next_page = comments_page_number + 1
                logging.debug('Trying next comments page #%s' % next_page)
            else:
                return None

        return int(next_page)

    def parse_date(self, post_html):
        try:
            date_str = re.search(RE_TIMESTAMP, post_html).group(1)
        except AttributeError as ex:
            return None

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
        return date_obj

    def process_post(self, post_url, post_number):
        """

        :param str post_url:
        :param str post_number:
        :return:
        :rtype: str
        """
        post_html = urllib2.urlopen(post_url).read()  # type: str
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

        date_obj = self.parse_date(post_html)
        logging.info('Blog %s Post #%d [%s] %s', self.blog_number, len(self.posts), post_number, date_obj.strftime('%Y-%m-%d %H:%M') if date_obj else '')

        filename = os.path.join(self.blog_folder, 'post_%s.html' % post_number)

        if self.save_template:
            template_filename = os.path.join(self.blog_folder, 'template.html')
            self.save_template = False
            with open(template_filename, mode='w') as output_file:
                output_file.write(post_html)

        with open(filename, mode='w') as output_file:
            try:
                # minimum_html = re.search(RE_POST_ONLY, post_html).group(1)
                data_start = post_html.index(POST_ONLY_START)
                data_end = post_html.index(POST_ONLY_END)
                minimum_html = '<HTML DIR="LTR" xmlns:ms="urn:schemas-microsoft-com:xslt"><head>' \
                               '<meta charset="UTF-8">' \
                               '<body>%s</body></HTML>' % post_html[data_start:data_end]
                output_file.write(minimum_html)
            except Exception as ex:
                output_file.write(post_html)

        if self.current_post.timestamp is not None:
            os.utime(filename, (self.current_post.timestamp, self.current_post.timestamp))

        next_post_number = None
        try:
            next_post_number = re.search(self.re_previous_post, post_html).group(1)
            logging.debug('next_post_number=%s', next_post_number)
        except Exception:
            # logging.debug(post_html)
            # logging.debug(RE_PREVIOUS_POST)
            pass

        # Get post comments
        comments_page_number = 1
        comments_url = self.get_comments_url(post_number)

        while comments_url is not None:
            logging.debug(comments_url)
            comments_html = urllib2.urlopen(comments_url).read()
            self.comment_pages += 1
            self.current_post.comment_pages = comments_page_number
            try:
                # We're also converting to unicode, because it's the right thing to do
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
                if self.save_comments_template:
                    output_file.write(comments_html)
                    self.save_comments_template = False
                else:
                    try:
                        data_start = comments_html.index(COMMENTS_ONLY_START)
                        data_end = comments_html.index(COMMENTS_ONLY_END)

                        minimum_html = '<html><head><meta http-equiv="content-type" ' \
                                       'content="text/html;charset=utf-8" />' \
                                       '<link rel="stylesheet" type="text/css" href="blog.css" />%s' \
                                       '</td></tr></table></body></HTML>' % comments_html[data_start:data_end]
                        """
                        <style type="text/css">
                        <!--
                        p { margin: 0px;  }
                        span.class_disabled {color: #808080;}
                        body {
                            scrollbar-face-color: #CCCCCC;
                            scrollbar-highlight-color: #FFFFFF;
                            scrollbar-3dlight-color: #FFFFFF;
                            scrollbar-shadow-color: #FFFFFF;
                            scrollbar-darkshadow-color: #FFFFFF;
                            scrollbar-arrow-color: #FFFFFF;
                            scrollbar-track-color: #FFFFFF;
                        }
                        -->
                        </style>
                        """
                        output_file.write(minimum_html)
                    except Exception as ex:
                        output_file.write(comments_html)
            if self.current_post.timestamp is not None:
                os.utime(comments_filename, (self.current_post.timestamp, self.current_post.timestamp))

            comments_page_number = self.get_next_page_number(comments_html, comments_page_number=comments_page_number)
            if comments_page_number is None:
                comments_url = None
            else:
                comments_url = self.get_comments_url(post_number, comments_page_number)

        self.current_post.comments_saved = True
        return next_post_number

    def get_post_url(self, post_number):
        url = POST_URL % (self.blog_number, post_number)
        if self.is_tblog:
            url = url.replace('blogread=', 'tblogread=')
        return url

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
        initial_page = None
        if START_FROM_POST_NUMBER is None:
            initial_page = urllib2.urlopen(self.blog_url).read()
            next_post_url = None
            try:
                next_post_url = re.search(self.re_post_url_pattern, initial_page).group(0).replace('&amp;', '&')
                next_post_number = next_post_url.split('blogcode=')[1]
            except Exception as ex:
                # Check if this is a custom template blog
                if re.match(
                        '<script xmlns:ms="urn:schemas-microsoft-com:xslt">window\.location\.replace\(\'/tblogread.asp\' \+ document\.location\.search\);</script>',
                        initial_page):
                    self.is_tblog = True
                    self.base_url = BASE_URL_TBLOG
                    self.blog_url = self.blog_url.replace('blogread', 'tblogread')
                else:
                    logging.warning('Could not find blog %s', self.blog_url)
                    return
            if self.is_tblog:
                initial_page = urllib2.urlopen(self.blog_url).read()
                try:
                    next_post_url = re.search(self.re_post_url_pattern, initial_page).group(0).replace('&amp;', '&')
                    next_post_number = next_post_url.split('blogcode=')[1]
                except Exception as ex:
                    logging.warning('Could not find blog %s', self.blog_url)
                    return
            logging.debug(next_post_url)
            next_post_url = self.base_url + next_post_url
        else:
            next_post_url = self.get_post_url(START_FROM_POST_NUMBER)
            next_post_number = STOP_AT_POST_NUMBER

        if not os.path.exists(self.blog_folder):
            os.makedirs(self.blog_folder)

        if initial_page is not None:
            filename = os.path.join(self.blog_folder, 'index.html')
            with open(filename, mode='w') as output_file:
                output_file.write(initial_page)
            self.read_months(initial_page)

        self.parse_blog_info(initial_page)

        # Scroll back from the latest post to the previous one, until you hit a broken link
        while next_post_number is not None:
            logging.debug('Post #%d [%s] %s', len(self.posts), next_post_number, next_post_url)
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

        # Read the monthly pages, and download missing posts
        for month_data in self.months:
            self.crawl_month(month_data)

    def read_months(self, page_html):
        try:
            month_drop_down = re.search(RE_DROPDOWN, page_html).group(0)
        except Exception:
            try:
                month_drop_down = re.search(RE_DROPDOWN_T, page_html, flags=re.MULTILINE).group(0)
            except Exception:
                logging.error('Can not read months list on blog #%s', self.blog_number)
                return

        months = month_drop_down.replace('\r\n', '').replace('\n', '').split('<option value=')
        for month_str in months:
            month_str = month_str.lstrip('"').lstrip("'")  # type: str
            if re.match('\d\d?/\d{4}', month_str):
                year = month_str.split('"')[0].split('/')[1]
                month = month_str.split('"')[0].split('/')[0]
                self.months.append(
                    {
                        'year': year,
                        'month': month,
                        'url': '&year=%s&month=%s' % (year, month)
                    }
                )
            elif re.match('\d{5,6}\'', month_str):
                year = month_str[0:4]
                month = month_str[4:6].rstrip("'")
                self.months.append(
                    {
                        'year': year,
                        'month': month,
                        'url': '&year=%s&month=%s' % (year, month)
                    }
                )

    def crawl_month(self, month_data):
        month_page_url = self.blog_url + month_data['url']
        page_number = 1
        while page_number > 0:
            page_html = urllib2.urlopen(month_page_url).read()
            logging.debug('%s%s page %d', month_data['year'], month_data['month'], page_number)
            if SAVE_MONTHLY_PAGES:
                page_filename = os.path.join(self.blog_folder, 'blog_%s_%s%s_%s.html' % (
                    self.blog_number, month_data['year'], month_data['month'], str(page_number)))
                with open(page_filename, mode='w') as page_file:
                    page_file.write(page_html)
            posts = re.findall(self.re_post_url_pattern, page_html)
            for post_str in posts:
                post_number = post_str.split('blogcode=')[1]
                if self.posts.get(str(post_number), None) is None:
                    logging.debug('Found Missing Post #%s', post_number)
                    self.process_post(post_url=self.get_post_url(post_number), post_number=str(post_number))
                else:
                    logging.debug('Already got Post #%s, skipping', post_number)

            # Check for next page
            if re.search('[&;]pagenum=%s' % str(page_number + 1), page_html):
                page_number += 1
            else:
                page_number = 0

    @staticmethod
    def search_re(regex, text):
        try:
            return re.search(regex, text).group(1)
        except Exception as ex:
            return ''

    def parse_blog_info(self, initial_page):
        self.nickname = self.search_re('<b>כינוי:</b> (.*)<br>', initial_page)
        if self.nickname == '':
            self.nickname = self.search_re('<script>displayEmail(\'list\',\'.*\',\'.*\',"(.*)")</script>', initial_page)
        if self.nickname == '':
            self.nickname = self.search_re('displayEmail(\'blog\',\'.*\',\'.*\',"(.*)")', initial_page)

        self.age = self.search_re('<br></br><b>בן:</b> (.*)<br></br>', initial_page)

        email_domain = self.search_re('<script>displayEmail(\'list\',\'.*\',\'(.*)\',".*")</script>', initial_page)
        if email_domain == '':
            email_domain = self.search_re('displayEmail(\'blog\',\'.*\',\'(.*)\',".*")', initial_page)
        email_user = self.search_re('<script>displayEmail(\'list\',\'(.*)\',\'.*\',".*")</script>', initial_page)
        if email_user == '':
            email_user = self.search_re('displayEmail(\'blog\',\'(.*)\',\'.*\',".*")', initial_page)
        self.email = '%s@%s' % (email_user, email_domain)

        self.title = self.search_re('<META property="og:title" content="(.*?)" />', initial_page) or self.search_re(
            '<h1 Class="TDtitle">(.*?)</h1>', initial_page)
        self.description = self.search_re('<meta name="description" content="(.*?)" />', initial_page)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    if not os.path.exists(os.path.join(BACKUP_FOLDER, 'log')):
        os.makedirs(os.path.join(BACKUP_FOLDER, 'log'))

    logging.info('Israblog Batch Backup Script.')
    logging.info('This script backs up posts, template and comments. WITHOUT IMAGES!')
    backup_folder = raw_input('Backup folder [ %s ]: ' % BACKUP_FOLDER)

    if backup_folder:
        if not os.path.exists(backup_folder):
            logging.error('Folder does not exist: %s' % backup_folder)
            exit(1)
        BACKUP_FOLDER = backup_folder

    blog_number_start = input("Blog Number to Start: ")  # Blog number. e.g. 11990
    blog_number_end = input("Stop at blog number: ")

    log_filename = os.path.join(BACKUP_FOLDER, 'log/backup_log_%s-%s_%s.csv' % (
        blog_number_start, blog_number_end, datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')))

    with open(log_filename, mode='a') as log_file:
        log_file.write(
            '"Blog Number","Posts","Comment Pages","Timestamp","Nickname","Email","age","Title","Description"\n')

    blog_enum = 0
    for blog_number in range(blog_number_start, blog_number_end + 1):
        blog_crawl = BlogCrawl(blog_number)
        blog_crawl.process_blog()
        if len(blog_crawl.posts) > 0:
            blog_enum += 1
            with open(log_filename, mode='a') as log_file:
                line = '%d,%d,%d,%s,"%s","%s",%s,"%s","%s"\n' % (
                    blog_number,
                    len(blog_crawl.posts),
                    blog_crawl.comment_pages,
                    datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    blog_crawl.nickname,
                    blog_crawl.email,
                    blog_crawl.age,
                    blog_crawl.title,
                    blog_crawl.description)
                log_file.write(line.decode('windows-1255').encode('UTF-8'))

    logging.info('Finished. Found %d blogs.' % blog_enum)