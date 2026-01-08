#! /usr/bin/env python3

# Modules requiring installation
import getch

# Built-in modules
from email import policy
from email.parser import BytesParser, Parser
from glob import glob
from os.path import getctime, isfile
from pathlib import Path
from sys import exit
import subprocess
import re


intro = '''

####  ######  ##     ## #### 
 ##  ##    ## ##     ##  ##  
 ##  ##       ##     ##  ##  
 ##  ##       #########  ##  
 ##  ##       ##     ##  ##  
 ##  ##    ## ##     ##  ##  
####  ######  ##     ## #### 
 ######   ######  ########  #### ########  ######## 
##    ## ##    ## ##     ##  ##  ##     ##    ##    
##       ##       ##     ##  ##  ##     ##    ##    
 ######  ##       ########   ##  ########     ##    
      ## ##       ##   ##    ##  ##           ##    
##    ## ##    ## ##    ##   ##  ##           ##    
 ######   ######  ##     ## #### ##           ## 


Feed Ichi your email header to get some help.

Warning: this script can cause complacency, abuse, confusion, 
errors, headaches, indigestion, upset stomach, fainting, 
and spontaneous combustion. Do not use without first consulting your T2.


'''

instruct = '''
Copy your email header to the clipboard.
Press return to feed Ichi and begin.
'''


def mk_heading(title):
    """
    Produces a clean heading
    
    :param title: The title to include in the heading
    """
    width = max(30, (len(title) + 6))

    return "\n\n" + ("=" * width) + "\n\n" + \
            str(title).upper() + (" " * 6) + "\n\n" + \
            ("=" * width) + "\n"


def mk_highlight(*args):
    """
    Takes multiple string arguments and returns as single
    string to highlight a result.
    
    :param args: Accepts as many string arguments as necessary.
    """
    highlight = "\n\n***"
    for text in args:
        highlight += " " + str(text)
    highlight = highlight + "\n\n"
    return highlight


# Puts on clipboard
# Used from pyperclip module, originally to prevent external dependency
def pbcopy(txt):
    task = subprocess.Popen(
        ['pbcopy'],
        stdin=subprocess.PIPE,
        close_fds=True
    )
    task.communicate(input=txt.encode('utf-8'))

# Pulls from clipboard
# Used from pyperclip module, originally to prevent external dependency
def pbpaste():
    task = subprocess.Popen(
        ['pbpaste'],
        stdout=subprocess.PIPE,
        close_fds=True
    )
    stdout, stderr = task.communicate()
    return(stdout.decode('utf-8'))


def get_latest_eml(given_path):
    '''
    Uses timstamps to find the most recently created 
    eml file in a directory.
    Returns the full path.
    '''
    if not given_path.endswith('/'):
        given_path = given_path + '/'
    given_path = given_path + '*.eml'
    try:
        list_of_files = glob(given_path)
        return max(list_of_files, key=getctime)
    except ValueError:
        print("Seems like you may have forgotten to download the eml file...")
        exit()


# Pulls header from clipboard
# Validates that text was pasted as string
def capture_clipboard_input():
    error_blank = (
            '\n\n### Error. Pulled contents were blank. ###'\
            '\n\nCopy your email header to the clipboard.'\
            '\nPress return after copying. Do not paste manually.'\
            '\nTroubles? Press Ctrl+c to exit.\n')
    error_type = (
            '\n\n### Error. Something was copied. '\
            'But not a header. ###'\
            '\n\nCopy your email header to the clipboard.'\
            '\nPress return after copying. Do not paste manually.'\
            '\nTroubles? Press Ctrl+c to exit.\n')
    error_content = (
            '\n\n### Error. No contents were pulled from the clipboard. '\
            '###\n\nCopy your email header to the clipboard.'\
            '\nPress return after copying. Do not paste manually.'\
            '\n\nTroubles? Press Ctrl+c to exit.\n')
    success_ms = ('Success. Input copied from clipboard.')
    header_str_input = ''
    attempt_count = 0
    while not header_str_input:
        if not header_str_input:
            user_direct_input = pbpaste().lstrip()
            attempt_count += 1
            if re.search(
                r'(from:\s.*)|(subject:\s.*)|(date:\s.*)', \
                    user_direct_input, re.I):
                header_str_input = user_direct_input
                print(mk_highlight(success_ms))
                break
            elif re.match(r'^\s*$', user_direct_input, re.I):
                input(error_blank)
            elif not re.search(r'(from:\s.*)|(subject:\s.*)|(date:\s.*)', \
                                user_direct_input, re.I):
                input(error_type)
            elif not user_direct_input:
                input(error_content)
    return header_str_input


def email_from_file(filepath):
    """
    Takes a filepath given as a string and returns
    a parsed email object. Handles minor bytes normalization.
    
    :param filepath: filepath as string
    """
    with open(filepath, 'rb') as eml_open:
        raw = eml_open.read()

        if raw.startswith(b'\xef\xbb\xbf'):
            raw = raw[3:]

        if raw.startswith(b'"Received: ') and raw.endswith(b'"'):
            raw = raw[1:-1]

        parsed_msg = BytesParser( 
            policy=policy.default).parsebytes(
                raw)
    
    return parsed_msg


def capture_input(usr_args, wrk_dir):
    '''
    Primary function to capture and parse user input. 
    Returns a parsed email object.

    :param usr_args: cli arguments from argparse
    :param wrk_dir: working directory from config file
    '''

    if not usr_args.input or usr_args.input == 'clipboard':
        raw_txt = capture_clipboard_input()

        parsed_msg = Parser( 
            policy=policy.default).parsestr(
                raw_txt)

    elif usr_args.input == 'working':
        if wrk_dir == '/path/to/working/dir':
            wrk_dir = str(Path.home()) + '/Downloads'
        target_email = get_latest_eml(wrk_dir)

        parsed_msg = email_from_file(target_email)

    else:
        filepath = usr_args.input
        if not isfile(filepath):
            print("Couldn't find the specified file.")
            exit()
        elif not filepath.endswith(".eml"):
            print("Specified file isn't EML.")
            exit()

        parsed_msg = email_from_file(filepath)

    return parsed_msg
 

def get_client_cli(clinfo):
    """
    Uses cli prompts based on the client dictionary
    to enable the user's choice of clients.
    
    :param clinfo: dictionary of client info
    """
    instruct = ('\n\nUse a number to select client this ticket is for.\n'
                'Hit return to bypass.\n\n')
    error_type = ("\n\n### You have chosen... poorly. ###\n"
                "### Use a number or return to bypass. ###")
    error_range = ("\n\n### Selection is outside the expected range. ###\n"
                    "### Use the number next to the desired client. ###")
    error_gen = "\n\n### Try that again. Something is wrong. ###"

    for i in range(1, 6):
        try:
            print(instruct)
            key_lst = list(clinfo.keys())
            for x in range(len(key_lst)):
                print(f"({x + 1}): {key_lst[x]}")
            client_select = getch.getch()
            if client_select == '\n' or not client_select:
                client_name = None
                return client_name
            else:
                client_select_int = int(client_select) - 1
                if 0 <= client_select_int < len(key_lst):
                    client_name = key_lst[client_select_int]
                    print(mk_highlight("Client selected:", client_name))
                    return client_name
                elif client_select_int < 0 or \
                    client_select_int > len(key_lst):
                    print(error_range)
                else:
                    print(error_gen)
        except NameError:
            print(error_gen)
        except (ValueError, TypeError):
            print(error_type)
    return client_name


def client_detection(clinfo, clselect, msg):
    """
    Outputs the name of the client whose environment produced the eml.
    Prioritizes 1) command parameter 2) automated matching 
    3) manual input.
    
    :param clinfo: Dictionary of client info from config file
    :param clselect: Client specified as cli command parameter
    :param msg: Parsed email message
    """

    if clselect:
        for client_name in clinfo.keys():
            if clselect == client_name:
                print(mk_highlight("Client selected:", client_name))
                return client_name
    
    elif msg['to'] or msg['cc']:
        for client_name in clinfo:
            for domain in clinfo[client_name]['domains']:
                if msg['to'] and domain in msg['to']:
                    print(mk_highlight("Client detected:", client_name))
                    return client_name
                elif msg['cc'] and domain in msg['cc']:
                    print(mk_highlight("Client detected:", client_name))
                    return client_name

        return get_client_cli(clinfo)

    else:
        return get_client_cli(clinfo)


def get_client_domains(clname, clinfo):
    """
    Returns a list of domains for the selected client.
    
    :param clname: Name of selected client
    :param clinfo: Full client information dictionary
    """
    if not clname:
        return []
    else:
        return clinfo[clname]["domains"]