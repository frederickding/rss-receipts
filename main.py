#!/usr/bin/env python3

import configparser
import feedparser
import datetime
import sys
import textwrap
import time
from urllib.parse import urlparse
from escpos.printer import Network
from unidecode import unidecode

global _config
NEWLINE = 128
HR = 129


def setup():
    global _config

    _config = configparser.ConfigParser(interpolation=None)
    config_files = _config.read(['default.ini', 'config.ini'])

    # some sanity checks
    if 'config.ini' not in config_files:
        print("Configuration file required - config.ini", file=sys.stderr)
        exit(1)
    if not _config.sections():
        print("You need to define at least one RSS feed with a section", file=sys.stderr)
        exit(2)

    # validate URLs
    for section in _config.sections():
        try:
            result = urlparse(_config[section].get('url'))
            if not result.scheme or not result.netloc:
                print("URL error - this section will be skipped: [%s]" % section, file=sys.stderr)
                print(result, file=sys.stderr)
                _config.remove_section(section)
                continue
        except BaseException as e:
            print("URL malformed", file=sys.stderr)
            print(e, file=sys.stderr)
            _config.remove_section(section)
            continue
    if len(_config.sections()) == 0:
        print("All sections are invalid", file=sys.stderr)
        exit(2)

def rss_section_loop():
    global _config
    return_value = []
    wrapper = textwrap.TextWrapper(width=_config['DEFAULT'].getint('printer_width', 48), tabsize=4)
    date_format = _config['DEFAULT'].get('date_format', '%Y-%m-%d %H:%M:%S')

    for section in _config.sections():
        print("Starting with section %s ..." % section)
        url = _config[section].get('url')
        print(url)

        if _config[section].getboolean('print_title', False):
            if _config[section].get('title', False):
                return_value.append(_config[section].get('title'))
            else:
                return_value.append(section)
            return_value.append(HR)
        feed = feedparser.parse(url)
        if len(feed.entries) > 0:
            limit = _config[section].getint('limit_entries_per_feed', 4)
            sort_order = _config[section].get('sort_date', 'descending') != 'ascending'

            # sort entries
            entries = [item for item in feed.entries]
            if any([i.published for i in entries]):
                entries.sort(key=lambda x: x.published_parsed, reverse=sort_order)
            elif any([i.updated for i in entries]):
                entries.sort(key=lambda x: x.updated_parsed, reverse=sort_order)

            for e in entries[0:limit]:
                return_value.extend(wrapper.wrap(unidecode(e.title, errors='replace')))
                if 'published' in e:
                    return_value.extend(wrapper.wrap("- %s" % time.strftime(date_format, e.published_parsed)))
                elif 'updated_parsed' in e:
                    return_value.extend(wrapper.wrap("- %s" % time.strftime(date_format, e.updated_parsed)))

        if len(_config.sections()) > 1:
            return_value.append(HR)
            return_value.append(NEWLINE)

    return return_value


def print_to_receipt(text):
    global _config
    p = Network(_config['DEFAULT'].get('printer_ip'))
    p.set("left")

    p.ln()
    for line in text:
        if line == HR:
            p.textln("-" * _config['DEFAULT'].getint('printer_width', 48))
        elif line == NEWLINE:
            p.ln()
        else:
            p.textln(line)

    p.ln()

    if _config['DEFAULT'].getboolean('print_date_footer'):
        now = datetime.datetime.now().strftime(_config['DEFAULT'].get('date_format', '%Y-%m-%d %H:%M:%S'))
        p.set("center")
        p.textln(now)

    p.cut()


if __name__ == '__main__':
    setup()
    fetched_text = rss_section_loop()
    print_to_receipt(fetched_text)
