#! /usr/bin/env python3

# Modules requiring installation
from dateutil.parser import parse as du_parse
import getch
# Built-in modules
from email import policy
from email.parser import BytesParser, Parser
from email.header import decode_header, make_header
from email.utils import parseaddr, getaddresses, formataddr
from glob import glob
from os.path import getctime, isfile
from pathlib import Path
from sys import exit
import re
import subprocess
import textwrap

ipv4_regex = re.compile(r'(?:^|\b(?<!\.))'
                      r'(?:1?\d?\d|2[0-4]\d|25[0-5])'
                      r'(?:\.(?:1?\d?\d|2[0-4]\d|25[0-5])){3}(?=$|[^\w.])'
                      )
rfc1918_regex = re.compile(r'(^127\.)|(^10\.)|(^172\.1[6-9]\.)'
                           r'|(^172\.2[0-9]\.)|(^172\.3[0-1]\.)|(^192\.168\.)'
                           )
ipv6_regex = re.compile(r"""
    ([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|          # 1:2:3:4:5:6:7:8
    ([0-9a-fA-F]{1,4}:){1,7}:|                         # 1::                              1:2:3:4:5:6:7::
    ([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|         # 1::8             1:2:3:4:5:6::8  1:2:3:4:5:6::8
    ([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|  # 1::7:8           1:2:3:4:5::7:8  1:2:3:4:5::8
    ([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|  # 1::6:7:8         1:2:3:4::6:7:8  1:2:3:4::8
    ([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|  # 1::5:6:7:8       1:2:3::5:6:7:8  1:2:3::8
    ([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|  # 1::4:5:6:7:8     1:2::4:5:6:7:8  1:2::8
    [0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|       # 1::3:4:5:6:7:8   1::3:4:5:6:7:8  1::8  
    :((:[0-9a-fA-F]{1,4}){1,7}|:)|                     # ::2:3:4:5:6:7:8  ::2:3:4:5:6:7:8 ::8       ::     
    fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|     # fe80::7:8%eth0   fe80::7:8%1     (link-local IPv6 addresses with zone index)
    ::(ffff(:0{1,4}){0,1}:){0,1}
    ((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}
    (25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|          # ::255.255.255.255   ::ffff:255.255.255.255  ::ffff:0:255.255.255.255  (IPv4-mapped IPv6 addresses and IPv4-translated addresses)
    ([0-9a-fA-F]{1,4}:){1,4}:
    ((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}
    (25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])           # 2001:db8:3:4::192.0.2.33  64:ff9b::192.0.2.33 (IPv4-Embedded IPv6 Address)
    """, re.IGNORECASE | re.VERBOSE)
domain_only_regex = re.compile(r'^((?!-))(xn--)?[a-z0-9][a-z0-9-_]{0,61}'
                               r'[a-z0-9]{0,1}\.(xn--)?([a-z0-9\-]{1,61}'
                               r'|[a-z0-9-]{1,30}\.[a-z]{2,})$', re.IGNORECASE
                               )
regex_for_smtpfrom = re.compile(r'(smtp\.mailfrom\=)'
                                r'([^=\s\[]*@[a-z0-9\-]*\.[^;>\)\]\s]*)', re.I
                                )

ichi_intro = '''

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

ichi_instruct = '''
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


def defang(text):
    """
    Takes a single string input. 
    Makes IPs (v4 and v6) and URLs safe.
    
    :param defang_this: single string input
    """
    return (text
                .replace('.', '[.]')\
                .replace('@', '[@]')\
                .replace('http', '[hxxp]')\
                .replace(':', '[:]')
    )

def simplify_string(text):
    """
    Flattens inputs into strings and simplies by removing
    carriage returns, newlines, and leading+trailing spaces.
    
    :param text: single string input
    """
    replacements = str.maketrans({"\r": "", "\n": ""})
    return (str(text).translate(replacements)).strip()


def decode_simple(header):
    """
    Applies email package standard for header field decode.
    Will not flatten strings. 
    
    :param heaheaderder_str: single header
    """
    return make_header(decode_header(header)) if header else None


def decode_pretty(to_decode):
    """
    Handles multiple text input types and makes them print ready.
    Applies decode and formatting. Returns lists and strings as such.
    Flattens 2-tuples (addresses) into strings.
    
    :param decode_this: str, lst, lst of tuples, or None
    """

    if to_decode is None:
        return None
    
    elif isinstance(to_decode, str):
        return simplify_string(
            decode_simple(to_decode))
    
    elif isinstance(to_decode, tuple):
        return simplify_string(
                decode_simple(
                    formataddr(to_decode)))
    
    elif isinstance(to_decode, list):
        for i in range(len(to_decode)):
            if isinstance(to_decode[i], str):
                to_decode[i] = simplify_string(
                    decode_simple(to_decode[i]))
            elif isinstance(to_decode[i], tuple):
                to_decode[i] = simplify_string(
                    decode_simple(
                        formataddr(to_decode[i])))
        return to_decode


def decode_safe(to_decode):
    """
    Makes multiple input types safe with defang
    and print ready with decode.
    Returns lists and strings as such.
    Flattens 2-tuples (addresses) into strings.
    
    :param decode_this: str, lst, lst of tuples, or None
    """
    if to_decode is None:
        return None
    
    elif isinstance(to_decode, str):
        return defang(
            simplify_string(
                decode_simple(to_decode)))
    
    elif isinstance(to_decode, tuple):
        return defang(
                simplify_string(
                    decode_simple(
                        formataddr(to_decode))))
    
    elif isinstance(to_decode, list):
        for i in range(len(to_decode)):
            if isinstance(to_decode[i], str):
                to_decode[i] = defang(
                    simplify_string(
                        decode_simple(to_decode[i])))
            elif isinstance(to_decode[i], tuple):
                to_decode[i] = defang(
                    simplify_string(
                        decode_simple(
                            formataddr(to_decode))))
        return to_decode
    

def truncate_str(long_str):
    """
    Shrinks a string to 100 characters ending in an elipsis.
    
    :param long_str: accepts a single long string
    """
    trunc_length = 100
    try:
        if len(long_str) > 100:
            return long_str[:97].rstrip() + "..."
        else:
            return long_str
    except TypeError:
        return long_str


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


def get_email_from(field_value):
    """
    Gets the email portion of a header field, removing
    the display name.
    
    :param field_value: header field
    """
    return parseaddr(field_value)[1]


def get_name_from(field_value):
    """
    Gets the display name portion of a header field, removing
    the email.
    
    :param field_value: header field
    """
    return parseaddr(field_value)[0]


def emails_to_string(emails):
    """
    Turns a list of emails into a nicely formatted string.
    Can handle header tuples or email addresses. 
    Returns display names and emails.
    
    :param recip_lst: list of strings or tuples
    """
    out_str = ''
    for i in emails:
        if isinstance(i,tuple):
            if not out_str:
                out_str = formataddr(i)
            else:
                out_str = (out_str + ', ' + formataddr(i))
        elif isinstance(i, str):
            if not out_str:
                out_str = i
            else:
                out_str = (out_str + ', ' + i)            
    return out_str
    

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
        with open(target_email, 'rb') as eml_open:
            raw = eml_open.read()
            if raw.startswith(b'\xef\xbb\xbf'):
                raw = raw[3:]

            parsed_msg = BytesParser( 
                policy=policy.default).parsebytes(
                    raw)

    else:
        filepath = usr_args.input
        if not isfile(filepath):
            print("Couldn't find the specified file.")
            exit()
        elif not filepath.endswith('.eml'):
            print("Specified file isn't EML.")
            exit()

        with open(filepath, 'rb') as eml_open:
            raw = eml_open.read()
            if raw.startswith(b'\xef\xbb\xbf'):
                raw = raw[3:]

            parsed_msg = BytesParser( 
                policy=policy.default).parsebytes(
                    raw)
            
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


def get_origin_ip(parsed_header):
    """
    Attempts to find the originating IP for an email 
    from multiple header fields. Currently relies on:

    Most common fields for originating IP:
        X-Forefront-Antispam-Report # Microsoft
        Received-SPF # General
        Earliest IP in Received # General

    To parse in future:
        Authentication-Results # General
        X-Originating-IP # Antiquated
    
    :param parsed_header: parsed email object
    """
    # parse earliest ipv4 in hops
    earliest_ipv4_in_hops = ''
    raw_received = parsed_header.get_all('received')
    try:
        for i in reversed(raw_received):
            i_temporary = i.replace('\n', '').replace('\r', '')
            i_without_by = re.sub(r'by.*', '', i_temporary, re.S)
            ips_found_in_received = ipv4_regex.findall(i_without_by)
            if len(ips_found_in_received) > 0:
                if rfc1918_regex.match(ips_found_in_received[-1]):
                    continue
                else:
                    earliest_ipv4_in_hops = ips_found_in_received[-1]
                    break
            elif not earliest_ipv4_in_hops and len(ips_found_in_received) == 0:
                continue
            elif earliest_ipv4_in_hops and len(ips_found_in_received) == 0:
                continue
    except (AttributeError, TypeError):
        earliest_ipv4_in_hops = ''

    # parse IP from X-Forefront-Antispam-Report
    ip_xforefront_antispam = ''
    fld_xforefront_antispam = parsed_header['X-Forefront-Antispam-Report']
    if fld_xforefront_antispam:
        ip_xforefront_antispam = re.search(r'CIP:([^;]+)', 
                                    fld_xforefront_antispam).group(1)
        
    # return the first 'client-ip' found from all Received-SPF records
    client_ip_regex = re.compile(r'client-ip=([^;]+)', re.IGNORECASE)
    all_rec_spf = parsed_header.get_all('Received-SPF') or []
    m_all_rec_spf = next((m for rec_spf in all_rec_spf 
              if (m := client_ip_regex.search(rec_spf))), None)
    ip_all_rec_spf = (m_all_rec_spf.group(1).strip(' []') 
                      if m_all_rec_spf else None)

    # Analyze available records and determine origin IP
    ip_from = 'Originating IP was not found'
    ip_from_determined_by = '' # for debuging use
    if ip_xforefront_antispam and ip_xforefront_antispam != '255.255.255.255':
        ip_from = ip_xforefront_antispam
        ip_from_determined_by = 'ip_xforefront_antispam'
    elif ip_all_rec_spf:
        ip_from = ip_all_rec_spf
        ip_from_determined_by = 'ip_all_rec_spf'
    elif earliest_ipv4_in_hops:
        ip_from = earliest_ipv4_in_hops
        ip_from_determined_by = 'earliest_ipv4_in_hops'
    return ip_from


# Determines the address from which the SMTP flow was received
# Returns the 'from' field if all else fails
def get_origin_email(p_header, r_header):
    try:
        origin_email = ''
        if regex_for_smtpfrom.search(r_header):
            origin_email = regex_for_smtpfrom.search(r_header).group(2)
        elif p_header['return-path']:
            origin_email = p_header['return-path']
        elif p_header['sender']:
            origin_email = p_header['sender']
        elif p_header['from']:
            origin_email = p_header['from']
        else:
            origin_email = ("An originating email could not be found. "
                            "This header is likely not standard compliant.")
        return origin_email
    except TypeError:
        origin_email = "The header may include multiple return-path values."


def get_sender(header):
    """
    Uses basic logic to guess a sender. Checks in order of:
    "from", "sender", "reply-to", "return-path"
    
    :param header: parsed header object
    """
    for field in ["from", "sender", "reply-to", "return-path"]:
        sender = header.get(field)
        if sender: 
            return sender
    return None


def get_recip_lst(header, domains):
    """
    Finds all the included recipients for the given client from 
    common header fields. Returns a list of address tuples.
    Perserves display names.
    
    :param header: parsed header object
    :param domains: list of client domains
    """
    fields_to_search = ['to', 'cc', 'bcc', 'delivered-to', 'reply-to']
    recip_lst = []
    if not domains and header['to']:
        recip_lst.extend(getaddresses(header.get_all('to')))
    elif domains:
        total_recip = []
        total_recip_emails = []
        for field in fields_to_search:
            if header[field]:
                total_recip.extend(getaddresses(header.get_all(field)))
        for dom in domains:
            esc_dom = re.escape(dom)
            client_dom_regex = re.compile(esc_dom, re.I)
            for x in total_recip:
                email = x[1]
                if client_dom_regex.search(email) \
                        and email not in total_recip_emails:
                    recip_lst.append(x)
                    total_recip_emails.append(email)
                else:
                    continue
    return recip_lst


def get_real_date(parsed_header):
    """
    Returns the datetime from the earliest received field
    in local system time.
    
    :param parsed_header: parsed header object
    """
    hop_one = (parsed_header['received']).split(';')
    hop_one_date = str(hop_one[1]).strip()
    parsed_date = du_parse(hop_one_date, fuzzy=True)
    parsed_date_in_localtime = parsed_date.astimezone()
    real_date = parsed_date_in_localtime.strftime("%a, %b %d, %Y %H:%M %Z")
    return real_date


def get_dmn_from_addy(address):
    """
    Returns a domain from an email address. Accepts strings and tuples.
    
    :param address: str or tuple containing email address
    """
    if isinstance(address, str):
        return address.split('@')[1] if "@" in address else None
    elif isinstance(address, tuple):
        return address[1].split('@')[1] if "@" in address[1] else None
    return None


def clean_subject(subject):
    """
    Decode and defang subject if necessary. 
    
    :param subject: subject header value
    """
    if subject: 
        decoded = str(decode_simple(subject))
        if ipv4_regex.search(decoded) \
                or ipv6_regex.search(decoded) \
                or domain_only_regex.search(decoded):
            return defang(decoded)
        else:
            return decoded
    else:
        return None


def get_reported_by(lst_of_recip):
    """
    Guesses the reporter to be the first address listed in the input.
    Returns None for any failure condition.
    
    :param lst_of_recip: list or single str of recipients
    """
    if lst_of_recip == [None] or lst_of_recip == None:
        return None
    elif isinstance(lst_of_recip, str):
        return lst_of_recip
    elif isinstance(lst_of_recip, list):
        return str(lst_of_recip[0])
    else:
        return None


#TODO: figure out where simplify_string needs called and implement
#TODO: change most direct header field calls to the .get() method
#TODO: ensure logic passes through None as failure value and handle before print
    # ensure functions intentionally return None for exceptions


def create_field_output(p_header, r_header, domains):
    fields_out = {}
    fields_out['received_time'] = get_real_date(p_header)
    fields_out['from'] = p_header['from']
    fields_out['from_name'] = get_name_from(fields_out['from'])
    fields_out['from_email'] = get_email_from(fields_out['from'])
    fields_out['from_dmn'] = get_dmn_from_addy(fields_out['from_email'])
    fields_out['found_sender'] = get_sender(p_header)
    fields_out['found_sender_name'] = get_name_from(fields_out['found_sender'])
    fields_out['found_sender_eml'] = get_email_from(fields_out['found_sender'])
    fields_out['found_sender_dmn'] = get_dmn_from_addy(fields_out['found_sender_eml'])
    fields_out['to'] = p_header['to']
    fields_out['to_name'] = get_name_from(fields_out['to'])
    fields_out['to_email'] = get_email_from(fields_out['to'])
    fields_out['known_recip_lst'] = get_recip_lst(p_header, domains)
    fields_out['known_recip_eml_lst'
               ] = [e[1] for e in fields_out['known_recip_lst']]
    fields_out['known_recip_str'] = emails_to_string(fields_out['known_recip_lst'])
    fields_out['known_recip_eml_str'] = emails_to_string(fields_out['known_recip_eml_lst'])
    fields_out['reported_by'] = get_reported_by(fields_out['known_recip_eml_lst'])
    fields_out['subject'] = p_header.get("subject")
    fields_out['date'] = p_header['date']
    fields_out['return_path'] = p_header['return-path']
    fields_out['origin_email'] = get_origin_email(p_header, r_header)
    fields_out['origin_email_dmn'] = get_dmn_from_addy(fields_out['origin_email'])
    fields_out['origin_ip'] = get_origin_ip(p_header)
    fields_out['reply_to'] = p_header['reply-to']
    fields_out['x_mailer'] = p_header['x-mailer']
    fields_out['user_agent'] = p_header['user-agent']
    fields_out['message_id'] = p_header['message-id']
    return fields_out

def sanitize_field_output(unclean_fields):
    clean_fields = unclean_fields.copy()
    clean_fields['from'] = decode_safe(clean_fields['from'])
    clean_fields['from_name'] = decode_safe(clean_fields['from_name'])
    clean_fields['from_email'] = decode_safe(clean_fields['from_email'])
    clean_fields['from_dmn'] = decode_safe(clean_fields['from_dmn'])
    clean_fields['found_sender'] = decode_safe(clean_fields['found_sender'])
    clean_fields['found_sender_name'] = decode_safe(clean_fields['found_sender_name'])
    clean_fields['found_sender_eml'] = decode_safe(clean_fields['found_sender_eml'])
    clean_fields['found_sender_dmn'] = decode_safe(clean_fields['found_sender_dmn'])
    clean_fields['known_recip_lst'] = decode_pretty(clean_fields['known_recip_lst'])
    clean_fields['known_recip_eml_lst'] = \
        decode_pretty(clean_fields['known_recip_eml_lst'])
    clean_fields['known_recip_str'] = decode_pretty(clean_fields['known_recip_str'])
    clean_fields['known_recip_eml_str'] = \
        decode_pretty(clean_fields['known_recip_eml_str'])
    clean_fields['subject'] = clean_subject(clean_fields['subject'])
    clean_fields['trunc_subject'] = truncate_str(clean_fields['subject'])
    clean_fields['to'] = decode_pretty(clean_fields['to'])
    clean_fields['return_path'] = defang(clean_fields['return_path'])
    clean_fields['origin_email'] = decode_safe(clean_fields['origin_email'])
    clean_fields['origin_email_dmn'] = decode_safe(clean_fields['origin_email_dmn'])
    clean_fields['origin_ip'] = defang(clean_fields['origin_ip'])
    clean_fields['reply_to'] = decode_safe(clean_fields['reply_to'])
    clean_fields['message_id'] = decode_pretty(clean_fields['message_id'])
    return clean_fields

# Aggregates the metadata fields into a list for printing.
def create_meta_out(fields_dict):
    metafields = []
    metafields.append('Primary Metadata')
    metafields.append('Sender: ' + fields_dict['found_sender']) 
    metafields.append('Recipient(s): ' + fields_dict['known_recip_eml_str'])
    metafields.append('Reported By: ' + fields_dict['reported_by'])
    metafields.append('Subject: ' + fields_dict['subject'])
    metafields.append('Date: ' + fields_dict['received_time'])
    metafields.append('\nContent')
    metafields.append('Attachment(s): N/A')
    metafields.append('Notable hyperlinks: N/A')
    metafields.append('\nAdditional Information (if available)')
    if fields_dict['return_path']:
        metafields.append('Return-Path: ' + fields_dict['return_path'])
    metafields.append('Originating Email: ' + fields_dict['origin_email'])
    metafields.append('Originating IP: ' + fields_dict['origin_ip'])
    if fields_dict['reply_to']:
        metafields.append('Reply-To: ' + fields_dict['reply_to'])
    if fields_dict['x_mailer']:
        metafields.append('X-Mailer: ' + fields_dict['x_mailer'])
    if fields_dict['user_agent']:
        metafields.append('User-Agent: ' + fields_dict['user_agent'])
    if fields_dict['message_id']:
        metafields.append('Message_ID: ' + fields_dict['message_id'])
    # metafields.append('Notable Search: ')
    # metafields.append('Search Time: ')
    # metafields.append('Link: ')
    return metafields