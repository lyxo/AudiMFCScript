import argparse
import sys
import getpass
import logging

from CursesPrinter import CursesPrinter
from Database import Database
from WebCrawler import WebCrawler
from Watchdog import Watchdog


# encoding argument was added just in 3.9
#logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)
logging.basicConfig(filename='example.log', level=logging.DEBUG)

def setup_parser():
    parser = argparse.ArgumentParser(description="Collect data from the MFC Website")
    parser.add_argument(
        "-i",
        "--interval",
        dest="interval",
        type=int,
        metavar="SECONDS",
        default=60,
        help="time interval in seconds in which the data shall be retrieved from the website (Default 60)"
    )
    parser.add_argument(
        "-u",
        "--user",
        dest="user",
        type=str,
        metavar="USER",
        help="Audi social media username (this does NOT have to be the same as the NT-user!)"
    )
    parser.add_argument(
        "-p",
        "--password",
        dest="password",
        type=str,
        metavar="PASSWORD",
        help="Audi social media password"
    )
    parser.add_argument(
        "--curses",
        action='store_const',
        const=True,
        default=True,
        help="Use the curses library for display (Default True)"
    )
    parser.add_argument(
        "--proxy",
        dest="proxy",
        type=str,
        metavar="PROXY",
        help="IP and port of proxy to be used",
        default=None
    )
    return parser

def input_user_credentials(auth_string:str, parser:argparse.ArgumentParser):
    user = ""
    passw = ""
    if auth_string:
        split = auth_string.split(":")
        if len(split) != 2:
            sys.stderr.write("[!] Error: Syntax Error on authentication credentials")
            parser.print_help()
            sys.exit()
        user = split[0]
        passw = split[1]
    else:
        # user = getpass.getuser("Enter WeAreAudi username:") # Dont use! This would take already set environment variables and use it as user input without asking
        user = input("Enter WeAreAudi username:\n")
        passw = getpass.getpass("Enter your WeAreAudi password:\n")
    return user,passw




if __name__ == "__main__":
    parser = setup_parser()
    args = parser.parse_args()
    # Authenticate to website to get a valid session cookie """
    # user, password = input_user_credentials(args.auth, parser)

    # webcrawler = WebCrawler()
    # if webcrawler.mfc_login(user, password):
    #     sys.stderr.write("[!] Error: Authentication failure.")
    #     sys.exit()
    # else:
    #     print("[*] Authentication successful.")

    webcrawler = WebCrawler(args.user, args.password, args.proxy)
    database = Database(webcrawler)
    watchdog = Watchdog(webcrawler, database, update_interval=args.interval)
    if args.curses:
        printer = CursesPrinter(watchdog)
        printer.start_wrapper()
