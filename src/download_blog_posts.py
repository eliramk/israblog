#!/bin/python
# -*- coding: utf-8 -*-

"""
Try to download all posts for a certain blog (html only, post-by-post)
"""
__author__ = 'eliram'

import urllib
import urllib2
import logging
import re
import os
from time import time, sleep
import datetime
import sys
from HTMLParser import HTMLParser

try:
    from awscli.compat import raw_input
except ImportError:
    pass

START_FROM_POST_NUMBER = None  # '3820213'  # Optional. Use None or a string containing the post number to move back from. e.g. '3754624'
STOP_AT_POST_NUMBER = None  # '12452501'  # Optional
SAVE_MONTHLY_PAGES = False

BLOG_URL = 'http://israblog.nana10.co.il/blogread.asp?blog=%s'
BASE_URL = 'http://israblog.nana10.co.il/blogread.asp'
BASE_URL_TBLOG = 'http://israblog.nana10.co.il/tblogread.asp'
POST_URL = 'http://israblog.nana10.co.il/blogread.asp?blog=%s&blogcode=%s'
COMMENTS_URL = 'http://israblog.nana10.co.il/comments.asp?blog=%s&user=%s'

USER_BACKUP_FOLDERS = [
    '/users/eliram/Documents/israblog2',
    "/home/avihay/tmp/backup"
]

# RegEx
RE_POST_URL_PATTERN = '\?blog=%s&a?m?p?;?blogcode=\d+'
RE_INITIAL_BLOG_CODE = 'blogcode=(\d+)'
RE_PREVIOUS_POST = '<a title="לקטע הקודם" href="/blogread.asp\?blog=%s&amp;blogcode=(\d+)" class="blog">'
RE_COMMENTS_NEXT_PAGE = 'href="comments\.asp\?.*&posnew=(\d+)">לדף הבא</a>'
RE_TIMESTAMP = '(\d\d?/\d\d?/\d\d\d\d(\xc2\xa0|\s|&nbsp;|\xa0)\d\d?:\d\d)\r?\n'
RE_DROPDOWN = '<select name="PeriodsForUser".*>(<option.*/option>)</select>'
RE_DROPDOWN_T = '<select .*?name=\'selMonth\'.*\r?\n(<option.*/option>\r?\n)*</select>'
RE_IMAGE_URL = 'https?:\/\/(?:[a-z\-]+\.)+[a-z]{2,6}(?:\/[^\/#?]+)+\.(?:jpe?g|gif|png|css)'
# RE_DROPDOWN_T_START = '<select class=\'list\' name=\'selMonth\''
# RE_DROPDOWN_T_END = </select>
RE_POST_ONLY = '(<table width="100%"><tr><td class="blog">.*)<iframe id='
RE_COMMENTS_ONLY = "(<style>a:active.*)<a name='newcommentlocation'></a>"

POST_ONLY_START = '<table width="100%"><tr><td class="blog">'
POST_ONLY_END = '<iframe id='
COMMENTS_ONLY_START = '<style>a:active'
COMMENTS_ONLY_END = "<a name='newcommentlocation'></a>"

platform = sys.platform
nbsp = HTMLParser().unescape('&nbsp;')
# RE_NICKNAME = u'<b>כינוי:</b>(?:\xc2\xa0|\s|&nbsp;|\xa0|..?)\n?(.*?)<br>'
# RE_AGE = u'<br></br><b>ב[ןת]:</b>(?:\xc2\xa0|\s|&nbsp;|\xa0|..?)(\d*)<br></br>'
RE_NICKNAME = u'<b>.{5}:</b>(?:\s|&nbsp;|.?)(.*?)<br>'
RE_AGE = u'<br></br><b>..:</b>(?:\s|&nbsp;|.?)(\d*)<br></br>'

COMMON_TEMPLATE_IMAGES = [
    'http://f.nanafiles.co.il/Partner48/Service87/Images/Header/headerBGGrad11.png',
    'http://f.nanafiles.co.il/Partner48/Service87/Images/\\Header\\IsraLogo11.png',
    'http://f.nanafiles.co.il/Partner48/Service87/Images/\\Header\\NanaLogo11.png',
    'http://f.nanafiles.co.il/Partner48/Service87/Images/israblog_radio_off.gif',
    'http://f.nanafiles.co.il/Partner48/Service87/Images/israblog_radio_on.gif',
    'http://f.nanafiles.co.il/Partner48/Service87/Images/lineBG.gif',
    'http://f.nanafiles.co.il/Partner1/Service87/Images/sign_in_button.gif',
    'http://f.nanafiles.co.il/Partner48/Service87/Images/israblogcellular.gif',
    'http://f.nanafiles.co.il/Common/Images/pixel.gif',

    'http://f.nanafiles.co.il/Partner1/Service87/Styles/Styles_1_87.css',
    'http://f.nanafiles.co.il/Partner48/Service87/Styles/Header.css',
    'http://f.nanafiles.co.il/Partner48/Service87/Styles/combobox.css',
]


class BlogPost(object):
    def __init__(self, post_number, saved=True):
        self.post_nubmer = post_number
        self.saved = saved
        self.comments_saved = False
        self.comment_pages = 0
        self.comments = 0
        self.timestamp = None  # type: float
        self.post_title = ''


class BlogCrawl(object):
    def __init__(self, blog_number, backup_folder, backup_images=False):
        """

        :param int blog_number:
        :param str backup_folder:
        :param bool backup_images:
        """
        self.blog_number = blog_number  # type: int
        self.posts = {}
        self.posts_list = []
        self.comment_pages = 0
        self.re_post_url_pattern = RE_POST_URL_PATTERN % blog_number
        self.re_previous_post = RE_PREVIOUS_POST % blog_number
        self.base_url = BASE_URL  # Could also be tblog
        self.blog_url = BLOG_URL % blog_number
        self.backup_folder = backup_folder
        self.blog_folder = os.path.join(backup_folder, str(blog_number))
        self.current_post = None  # type: BlogPost
        self.months = []
        self.nickname = ''
        self.email = ''
        self.age = ''
        self.title = ''
        self.description = ''
        self.total_comments = 0
        self.save_template = True  # Save the first post with full html as well?
        self.save_comments_template = True  # Save the first (recent) comments page without modifications
        self.is_tblog = False
        self.backup_images = backup_images

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

    @staticmethod
    def read_url(url):
        # Try 3 times to read URL, in case of failure, print error and exit
        """

        :param str url:
        :return:
        :rtype: str
        """
        attempts = 3
        while attempts > 0:
            try:
                data = urllib2.urlopen(url).read()
                return data
            except urllib2.HTTPError as ex:
                attempts -= 1
                logging.error('HTTP Error, %d retries left, trying to read url %s' % (attempts, url))
            except Exception as ex:
                attempts -= 1
                logging.error('Error, %d retries left, trying to read url %s' % (attempts, url))
            sleep(5)

        results['errors_blogs'] = results.get('errors_blogs', []).append(url)
        return 'error'

    def parse_date(self, post_html):
        try:
            date_str = re.search(RE_TIMESTAMP, post_html).group(1)
        except AttributeError as ex:
            return None

        if '&nbsp;' in date_str:
            date_split = date_str.split('&nbsp;')
        elif ' ' in date_str:
            date_split = date_str.split(' ')
        else:
            date_split = date_str.split('\xc2\xa0')
        date_array = date_split[0].split('/')

        if len(date_split) > 1:
            time_array = date_split[1].split(':')
        else:
            time_array = [0, 0]

        try:
            date_obj = datetime.datetime(int(date_array[2]),
                                         int(date_array[1]),
                                         int(date_array[0]),
                                         int(time_array[0]),
                                         int(time_array[1]),
                                         0)
        except Exception:
            date_obj = datetime.datetime(1970, 1, 1, 0, 0, 0)

        # new_post.date_str = date_str
        if int(date_array[2]) < 1970:
            # Fake date
            ts = 0
        else:
            ts = (date_obj - datetime.datetime(1970, 1, 1)).total_seconds()
        self.current_post.timestamp = ts
        return date_obj

    def download_page_images(self, post_html, post_number='template'):
        relative_folder = 'template' if post_number == 'template' else 'pics'
        images_folder = os.path.join(self.blog_folder, relative_folder)
        image_links = re.findall(RE_IMAGE_URL, post_html, flags=re.IGNORECASE)
        if len(image_links) > 0 and not os.path.exists(images_folder):
            os.makedirs(images_folder)
        enum = 0
        downloaded_images = []
        used_filenames = []
        modified_html = post_html
        for link in image_links:
            if link in downloaded_images:
                continue

            downloaded_images.append(link)
            enum += 1
            filename = link.split('/')[-1].split('\\')[-1]
            full_filename = os.path.join(images_folder, filename)
            if link in COMMON_TEMPLATE_IMAGES:
                full_filename = os.path.join(self.backup_folder, 'main_template', filename)
                if not os.path.exists(os.path.join(self.backup_folder, 'main_template')):
                    os.makedirs(os.path.join(self.backup_folder, 'main_template'))
                relative_path = '../main_template/'
            else:
                relative_path = './' + relative_folder + '/'

            if full_filename in used_filenames:
                enum += 1
                filename = filename.replace('.', '_%d.' % enum)
                full_filename = os.path.join(images_folder, filename)

            used_filenames.append(full_filename)
            try:
                if not os.path.exists(full_filename):
                    urllib.urlretrieve(link, full_filename)
                modified_html = modified_html.replace(link, relative_path + filename)
            except Exception:
                logging.error('Post %s Could not download %s to file %s', post_number, link, full_filename)

        return modified_html

    def process_post(self, post_url, post_number):
        """

        :param str post_url:
        :param str post_number:
        :return:
        :rtype: str
        """
        post_html = self.read_url(post_url)  # type: str
        self.current_post = BlogPost(post_number)
        self.posts[post_number] = self.current_post
        self.posts_list.insert(0, self.current_post)

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
        post_title = self.search_re('<h2 class="title">(.*?)</h2>', post_html) or self.search_re(
            '<meta property="og:title" content="(.*?)"/>', post_html)
        self.current_post.post_title = post_title
        filename = os.path.join(self.blog_folder, 'post_%s.html' % post_number)

        try:
            data_start = post_html.index(POST_ONLY_START)
            data_end = post_html.index(POST_ONLY_END)
            data_html = post_html[data_start:data_end]
            template_html = post_html[:data_start] + '<!-- POST_PLACE_HOLDER -->' + post_html[data_end:]
            # remove iframes, like the facebook button etc.
            iframes = re.findall('<iframe.*?/iframe>', data_html)
            for iframe in iframes:
                data_html.replace(iframe, '')
            minimum_html = '<HTML DIR="RTL" xmlns:ms="urn:schemas-microsoft-com:xslt"><head>' \
                           '<meta charset="UTF-8">' \
                           '<body>%s</body></HTML>' % data_html
        except Exception as ex:
            minimum_html = post_html
            template_html = post_html

        if self.backup_images:
            minimum_html = self.download_page_images(minimum_html, post_number)

        with open(filename, mode='w') as output_file:
            output_file.write(minimum_html)

        if self.save_template:
            template_filename = os.path.join(self.blog_folder, 'template.html')
            self.save_template = False
            if self.backup_images:
                template_html = self.download_page_images(template_html, 'template')
            with open(template_filename, mode='w') as output_file:
                output_file.write(template_html)

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
            comments_html = self.read_url(comments_url)
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
            if self.save_comments_template:
                comments_count = max(0, len(re.findall("<a name='", comments_html)) - 2)
                if comments_count > 0:
                    self.save_comments_template = False
                    with open(comments_filename, mode='w') as output_file:
                        output_file.write(comments_html)
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
                    comments_count = len(re.findall("<a name='", minimum_html))
                    if comments_count > 0:
                        with open(comments_filename, mode='w') as output_file:
                            output_file.write(minimum_html)
                except Exception as ex:
                    comments_count = max(0, len(re.findall("<a name='", comments_html)) - 2)
                    if comments_count > 0:
                        with open(comments_filename, mode='w') as output_file:
                            output_file.write(comments_html)

            if self.current_post.timestamp is not None and os.path.exists(comments_filename):
                os.utime(comments_filename, (self.current_post.timestamp, self.current_post.timestamp))

            self.current_post.comments += comments_count
            self.total_comments += comments_count
            comments_page_number = self.get_next_page_number(comments_html, comments_page_number=comments_page_number)
            if comments_page_number is None:
                comments_url = None
            else:
                comments_url = self.get_comments_url(post_number, comments_page_number)

        self.current_post.comments_saved = True
        if platform != 'darwin' and not re.search('[A-Za-z]', post_title):  # Don't reverse english titles
            post_title = u''.join(reversed(post_title.decode('UTF-8', errors='ignore')))  # [::-1]
            post_title = post_title.encode('UTF-8')
        logging.info('Blog %s Post #%d [%s] %s [%d comments] %s', self.blog_number, len(self.posts), post_number,
                     date_obj.strftime('%Y-%m-%d %H:%M') if date_obj else '', self.current_post.comments, post_title)

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
            initial_page = self.read_url(self.blog_url)
            next_post_url = None
            next_post_number = None
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
                    if 'window.location.replace(\'/noblog.htm\');' in initial_page:
                        logging.info('No blog #%s', str(self.blog_number))
                        return 'no_blog'
                    self.parse_blog_info(initial_page)
                    logging.warning('Empty blog %s', self.blog_url)
                    return 'blog_empty'
            if self.is_tblog:
                logging.info('Blog %s Using tblogread', blog_number)
                initial_page = self.read_url(self.blog_url)
                try:
                    next_post_url = re.search(self.re_post_url_pattern, initial_page).group(0).replace('&amp;', '&')
                    next_post_number = next_post_url.split('blogcode=')[1]
                except Exception as ex:
                    self.parse_blog_info(initial_page)
                    logging.warning('Empty t-blog %s  %s by %s', self.blog_url, self.title, self.nickname)
                    return 'tblog_empty'

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
        try:
            if platform == 'darwin' or re.search('[A-Za-z]', self.title):
                nick = self.nickname.decode('windows-1255', errors='ignore').encode('UTF-8')
                title = self.title.decode('windows-1255', errors='ignore').encode('UTF-8')
            else:
                # reverse strings
                nick = self.nickname.decode('windows-1255', errors='ignore')[::-1].encode('UTF-8')
                title = self.title.decode('windows-1255', errors='ignore')[::-1].encode('UTF-8')
        except (UnicodeDecodeError, Exception) as ex:
            logging.error('Bad Unicode decode')
            nick = self.nickname
            title = self.title

        logging.info('Found blog %s by %s - %s', self.blog_number, nick, title)

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

        return 'tblog' if self.is_tblog else 'blog'

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
            page_html = self.read_url(month_page_url)
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
    def search_re(regex, text, multiline=False):
        try:
            if multiline:
                result = re.search(regex, text, flags=re.MULTILINE).group(1)  # type: str
            else:
                result = re.search(regex, text).group(1)  # type: str
            return result.strip()
        except Exception as ex:
            return ''

    def parse_blog_info(self, initial_page):
        self.nickname = self.search_re(RE_NICKNAME, initial_page)
        if self.nickname == '':
            self.nickname = self.search_re('<script>displayEmail\(\'list\',\'.*\',\'.*\',"(.*)"\)</script>',
                                           initial_page)
        else:
            pass
        if self.nickname == '':
            self.nickname = self.search_re('displayEmail\(\'blog\',\'.*\',\'.*\',"(.*)"\)', initial_page)

        self.age = self.search_re(RE_AGE, initial_page)

        email_domain = self.search_re("<script>displayEmail\('list','.*','(.*)',\".*\"\)</script>", initial_page)
        if email_domain == '':
            email_domain = self.search_re('displayEmail\(\'blog\',\'.*\',\'(.*)\',".*"\)', initial_page)
        email_user = self.search_re('<script>displayEmail\(\'list\',\'(.*)\',\'.*\',".*"\)</script>', initial_page)
        if email_user == '':
            email_user = self.search_re('displayEmail\(\'blog\',\'(.*)\',\'.*\',".*"\)', initial_page)
        self.email = '' if email_user == '' and email_domain == '' else '%s@%s' % (email_user, email_domain)

        self.title = self.search_re('<META property="og:title" content="(.*?)" />', initial_page) or self.search_re(
            '<h1 Class="TDtitle">(.*?)</h1>', initial_page)
        self.description = self.search_re('<meta name="description" content="(.*?)" />', initial_page)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    logging.info('Israblog Batch Backup Script. Version 10')
    logging.info('This script backs up posts, template and comments. [running on %s]' % platform)

    blog_number_start = long(sys.argv[1]) if len(sys.argv) > 2 else input(
        "Blog Number to Start: ")  # Blog number. e.g. 11990
    blog_number_end = long(sys.argv[2]) if len(sys.argv) > 2 else input("Stop at blog number: ")

    backup_images = blog_number_start == blog_number_end
    if backup_images:
        logging.info('Downloading a single blog - WITH IMAGES')
    else:
        logging.info('Downloading multiple blogs - Images are NOT saved. To backup images, download a single blog.')

    backup_folder = None

    for try_backup_folder in USER_BACKUP_FOLDERS:
        if os.path.exists(try_backup_folder):
            backup_folder = try_backup_folder

    if backup_folder is None:
        default_backup_folder = os.path.dirname(os.path.realpath(__file__))
        backup_folder = raw_input('Specify Backup folder, or press ENTER to use [ %s ]: ' % default_backup_folder)
        if backup_folder:
            if not os.path.exists(backup_folder):
                logging.error('Folder does not exist: %s' % backup_folder)
                exit(1)
        else:
            backup_folder = default_backup_folder
    else:
        logging.info('Saving to folder: %s' % backup_folder)
    print ''

    if not os.path.exists(os.path.join(backup_folder, 'log')):
        os.makedirs(os.path.join(backup_folder, 'log'))

    log_filename = os.path.join(backup_folder, 'log', 'backup_log_%s-%s_%s.csv' % (
        blog_number_start, blog_number_end, datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')))
    log_posts_filename = os.path.join(backup_folder, 'log', 'backup_log_posts_%s-%s_%s.csv' % (
        blog_number_start, blog_number_end, datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')))

    with open(log_filename, mode='a+') as log_file:
        log_file.write(
            '"Blog Number","Posts","Comment Pages","Timestamp","Nickname","Email","age","Title","Description","Comments"\n')
    with open(log_posts_filename, mode='a+') as log_file:
        log_file.write(
            '"Blog Number","Post Number","Comments","Post Timestamp","Post Epoch","Post Title"\n')

    blog_enum = 0
    results = {}
    start_time = time()
    blogs_total = (blog_number_end - blog_number_start + 1)
    for blog_number in range(blog_number_start, blog_number_end + 1):
        blog_crawl = BlogCrawl(blog_number, backup_folder, backup_images=backup_images)
        result = blog_crawl.process_blog()
        results[result] = results.get(result, 0) + 1
        if len(blog_crawl.posts) > 0 or result != 'no_blog':
            with open(log_filename, mode='a') as log_file:
                line = '%d,%d,%d,%s,"%s","%s",%s,"%s","%s",%d\r\n' % (
                    blog_number,
                    len(blog_crawl.posts),
                    blog_crawl.comment_pages,
                    datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    blog_crawl.nickname,
                    blog_crawl.email,
                    blog_crawl.age,
                    blog_crawl.title,
                    blog_crawl.description,
                    blog_crawl.total_comments
                )
                log_file.write(line.decode('windows-1255', errors='ignore').encode('UTF-8'))

        if len(blog_crawl.posts) > 0:
            blog_enum += 1
            with open(log_posts_filename, mode='a') as log_file:
                for post in blog_crawl.posts_list:  # type: BlogPost
                    line = '%d,%d,%d,"%s",%s,"%s"\r\n' % (
                        blog_number,
                        int(post.post_nubmer),
                        post.comments,
                        datetime.datetime.fromtimestamp(post.timestamp).strftime(
                            '%Y-%m-%d %H:%M:%S') if post.timestamp else '',
                        str(int(post.timestamp)) if post.timestamp else '',
                        post.post_title)
                    log_file.write(line)

        if blog_number % 100 == 0:
            elapsed_time = time() - start_time
            blogs_completed = (blog_number - blog_number_start + 1)
            blogs_left = blogs_total - blogs_completed
            time_passed = datetime.datetime.utcfromtimestamp(elapsed_time).strftime('%H:%M:%S')
            time_left = datetime.datetime.utcfromtimestamp(blogs_left * elapsed_time / blogs_completed).strftime('%H:%M:%S')
            logging.info('Completed %d/%d blogs (%d%%). Time passed: %s Time Left: %s Stats: %s' % (
                         blogs_completed,
                         blogs_total,
                         blogs_completed * 100 / blogs_total,
                         time_passed,
                         time_left,
                         results))

    ratio = blog_enum * 100 / (blog_number_end - blog_number_start + 1)
    elapsed_time = time() - start_time
    time_passed = datetime.datetime.utcfromtimestamp(elapsed_time).strftime('%H:%M:%S')
    logging.info('Finished. Found %d blogs in range %d-%d. Ratio %d%%. Time to complete: %s' % (
        blog_enum, blog_number_start, blog_number_end, ratio, time_passed))
    logging.info('Results: %s', results)
    wait = raw_input('Press ENTER')
