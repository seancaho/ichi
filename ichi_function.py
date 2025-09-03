#! /usr/bin/env python3

# Modules requiring installation
from dateutil.parser import parse
import getch
# Built-in modules
from email.header import decode_header, make_header
from email.utils import parseaddr, getaddresses, formataddr
import re
import subprocess

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
======

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
 
======

'''

ichi_instruct = '''
Copy your email header to the clipboard.
Press return to feed Ichi and begin.
'''

out_heading = ('\n\n======\n\nOUTPUT\n\n======\n\n')

# Sanitizes IPs, URLs, and Emails
def defang(defang_this):
    if defang_this:
        try:
            defang_working = defang_this.replace('.', '[.]')\
                                    .replace('@', '[@]')\
                                    .replace('http', '[hxxp]')
        except TypeError:
            defang_working = "_____This field could not be found_____"
    else:
        defang_working = defang_this
    return defang_working

# Decodes fields
def decode(decode_this):
    if decode_this: 
        if isinstance(decode_this, str):
            decode_working = ''
            try: 
                decode_working = str(make_header(decode_header(decode_this)))
                decode_working = decode_working.replace("\n", "")
            except TypeError:
                decode_working = "_____Error in field parsing_____"
        elif isinstance(decode_this, list):
            decode_working = []
            try:
                for i in decode_this:
                    if isinstance(i, str):
                        reformat = str(make_header(decode_header(i)))
                        reformat = reformat.replace("\n", "")
                        decode_working.append(reformat)
                    elif isinstance(i, tuple):
                        reformat = formataddr(i)
                        reformat = str(make_header(decode_header(reformat)))
                        reformat = reformat.replace("\n", "")
                        decode_working.append(reformat)
            except TypeError:
                decode_working = ["_____Error in field parsing_____", ]
    else: 
        decode_working = decode_this 
    return decode_working

# Decodes and sanitizes fields
def defang_decode(defang_decode_this):
    if defang_decode_this:
        try: 
            decode_working = str(make_header(decode_header(defang_decode_this)))
            defang_decode_working = decode_working.replace('.', '[.]')\
                                            .replace('@', '[@]')\
                                            .replace('http', '[hxxp]')\
                                            .replace(':', '[:]')
        except TypeError:
            defang_decode_working = "_____Error in field parsing_____"
    else:
        defang_decode_working = defang_decode_this
    return defang_decode_working

def truncate_str(long_str):
    trunc_length = 100
    try:
        if len(long_str) > 100:
            short_str = long_str[:97].rstrip() + "..."
            return short_str
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

# From a list, creates an aggregated string text block.
def str_from_lst(in_lst):
    linebreak = '\n'
    new_str = linebreak.join(in_lst)
    return new_str

# Gets an email from a name + email within a message field
def get_email_from(field_value):
    field_tuple = parseaddr(field_value)
    email = field_tuple[1]
    return email

# Gets a name from a name + email within a message field
def get_name_from(field_value):
    field_tuple = parseaddr(field_value)
    name = field_tuple[0]
    return name

# Pulls header from clipboard
# Validates that text was pasted as string
def capture_email_header():
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
    success_ms = ('\n\n### Success. That seems like an email header. ###\n')
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
                break
            elif re.match(r'^\s*$', user_direct_input, re.I):
                input(error_blank)
            elif not re.search(r'(from:\s.*)|(subject:\s.*)|(date:\s.*)', \
                                user_direct_input, re.I):
                input(error_type)
            elif not user_direct_input:
                input(error_content)
    return header_str_input

# Presents client domain options and gets selection
def get_client_name(client_info):
    instruct = ('\n\nUse a number to select client this ticket is for.\n'
                'Hit return to bypass.\n\n')
    client_name = 'CLIENT'
    error_type = ("\n\n### You have chosen... poorly. ###\n"
                  "### Use a number or return to bypass. ###")
    error_range = ("\n\n### Selection is outside the expected range. ###\n"
                    "### Use the number next to the desired client. ###")
    error_gen = "\n\n### Try that again. Something is wrong. ###"
    print('\n\n======\n\nCLIENT SELECTION\n\n======')
    for i in range(1, 6):
        try:
            print(instruct)
            key_lst = list(client_info.keys())
            for x in range(len(key_lst)):
                print(f"({x + 1}): {key_lst[x]}")
            client_select = getch.getch()
            if client_select == '\n':
                client_select = ''
            if not client_select:
                print('\n\n### Client selected: ' + client_name + '\n\n')
                break
            else:
                client_select_int = int(client_select) - 1
                if 0 <= client_select_int < len(key_lst):
                    client_name = key_lst[client_select_int]
                    print('\n\n### Client selected: ' + client_name + '\n\n')
                    break
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

# Gets the client domains from config; returns placeholder as necessary
def get_client_domains(client_name, info):
    client_domains = []
    if client_name == "CLIENT":
        client_domains = []
    else:
        client_domains = info[client_name]["domains"]
    return client_domains

# Attempts to find the origin IP from the received fields
# Currently only returns IPv4 addresses
def get_origin_ip(parsed_header):
    '''
    Most common fields for originating IP:
        X-Forefront-Antispam-Report # Microsoft
        Received-SPF # General
        Authentication-Results # General
        X-Originating-IP # Antiquated
    '''
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

# Shows the sender's intended appearance, not the origin addy
# Returns 'from', unless there isn't one
def get_sender(p_header):
    if p_header['from']:
        sender = p_header['from']
    elif p_header['sender']:
        sender = p_header['sender']
    elif p_header['reply-to']:
        sender = p_header['reply-to']
    elif p_header['return-path']:
        sender = p_header['return-path']
    else:
        sender = ("Sender could not be determined. ")
    return sender

# outputs a list of client recipients from the fields_to_search
def get_recip_lst(p_header, client_dom):
    fields_to_search = ['to', 'cc', 'bcc', 'delivered-to', 'reply-to']
    recip_lst = []
    if not client_dom and p_header['to']:
        recip_lst.extend(getaddresses(p_header.get_all('to')))
    elif client_dom:
        total_recip = []
        total_recip_emails = []
        for field in fields_to_search:
            if p_header[field]:
                total_recip.extend(getaddresses(p_header.get_all(field)))
        for dom in client_dom:
            esc_dom = re.escape(dom)
            client_dom_regex = re.compile(esc_dom, re.I)
            for x in total_recip:
                email = x[1]
                if client_dom_regex.search(email) and email not in total_recip_emails:
                    recip_lst.append(x)
                    total_recip_emails.append(email)
                else:
                    continue
    return recip_lst

# Take a list of field values (name, email) and return a list of emails
def get_recip_eml_lst(lst_of_recip):
    out_lst = []
    for fld_tuple in lst_of_recip:
        email = fld_tuple[1]
        out_lst.append(email)
    return out_lst

# turns the recipient list into a simple, print-ready string
def get_recip_str(recip_lst):
    out_str = ''
    for i in recip_lst:
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

# Pulls the date field from the earliest 'received' field.
def get_real_date(parsed_header):
    hop_one = (parsed_header['received']).split(';')
    hop_one_date = str(hop_one[1]).strip()
    parsed_date = parse(hop_one_date, fuzzy=True)
    parsed_date_in_localtime = parsed_date.astimezone()
    real_date = parsed_date_in_localtime.strftime("%a, %b %d, %Y %H:%M %Z")
    return real_date

# Get the subject field from the parsed header object
def get_subject(parsed_header):
    if parsed_header['subject']:
        original_subject = parsed_header['subject']
    else:
        original_subject = "<empty>"
    return original_subject

def get_dmn_from_addy(input_addy):
    if isinstance(input_addy, str):
        dmn = input_addy.split('@')[1]
    elif isinstance(input_addy, tuple):
        dmn = input_addy[1].split('@')[1]
    return dmn

# Sanitize any IPs, emails, or domains included in the subject line
# Or just decode the subject and return
def clean_subject(subj):
    cleaned_subject = ''
    decoded = decode(subj)
    if ipv4_regex.search(decoded) \
        or ipv6_regex.search(decoded) \
        or domain_only_regex.search(decoded):
        cleaned_subject = defang(decoded)
    else:
        cleaned_subject = decoded
    return cleaned_subject

def get_reported_by(lst_of_recip):
    if lst_of_recip == [None]:
        reported_by = ''
    elif len(lst_of_recip) == 1:
        if isinstance(lst_of_recip, list):
            reported_by = str(lst_of_recip[0])
        elif isinstance(lst_of_recip, str):
            reported_by = lst_of_recip
    else:
        reported_by = ''
    return reported_by

def recip_found_check(fields_dict):
    if not fields_dict['known_recip_str']:
        return False
    else: 
        return True
    
def manual_get_recip(fields_dict):
    instruct = ("\n\nNo corporate users were found in the header.\n"
                "Submit the user who reported this email.\n\n")
    error_type = ("\n\n### Something went wrong in this submission. ###\n")
    print("\n\n======\n\nRECIPIENT & REPORTED BY\n\n======")
    more_fields_dict = fields_dict
    for i in range(1, 6):
        try:
            print(instruct)
            user = input()
            if not user:
                break
            else:
                more_fields_dict['known_recip_str'] = user
                more_fields_dict['reported_by'] = user
                break
        except NameError:
            print(error_type)
        except ValueError:
            print(error_type)
    return more_fields_dict

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
    fields_out['known_recip_eml_lst'] = \
        get_recip_eml_lst(fields_out['known_recip_lst'])
    fields_out['known_recip_str'] = get_recip_str(fields_out['known_recip_lst'])
    fields_out['known_recip_eml_str'] = get_recip_str(fields_out['known_recip_eml_lst'])
    fields_out['reported_by'] = get_reported_by(fields_out['known_recip_eml_lst'])
    fields_out['subject'] = get_subject(p_header)
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
    clean_fields['from'] = defang_decode(clean_fields['from'])
    clean_fields['from_name'] = defang_decode(clean_fields['from_name'])
    clean_fields['from_email'] = defang_decode(clean_fields['from_email'])
    clean_fields['from_dmn'] = defang_decode(clean_fields['from_dmn'])
    clean_fields['found_sender'] = defang_decode(clean_fields['found_sender'])
    clean_fields['found_sender_name'] = defang_decode(clean_fields['found_sender_name'])
    clean_fields['found_sender_eml'] = defang_decode(clean_fields['found_sender_eml'])
    clean_fields['found_sender_dmn'] = defang_decode(clean_fields['found_sender_dmn'])
    clean_fields['known_recip_lst'] = decode(clean_fields['known_recip_lst'])
    clean_fields['known_recip_eml_lst'] = \
        decode(clean_fields['known_recip_eml_lst'])
    clean_fields['known_recip_str'] = decode(clean_fields['known_recip_str'])
    clean_fields['known_recip_eml_str'] = \
        decode(clean_fields['known_recip_eml_str'])
    clean_fields['subject'] = clean_subject(clean_fields['subject'])
    clean_fields['trunc_subject'] = truncate_str(clean_fields['subject'])
    clean_fields['to'] = decode(clean_fields['to'])
    clean_fields['return_path'] = defang(clean_fields['return_path'])
    clean_fields['origin_email'] = defang_decode(clean_fields['origin_email'])
    clean_fields['origin_email_dmn'] = defang_decode(clean_fields['origin_email_dmn'])
    clean_fields['origin_ip'] = defang(clean_fields['origin_ip'])
    clean_fields['reply_to'] = defang_decode(clean_fields['reply_to'])
    clean_fields['message_id'] = decode(clean_fields['message_id'])
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