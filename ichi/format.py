#! /usr/bin/env python3

# Modules requiring installation

# Built-in modules
from email.header import decode_header, make_header
from email.utils import parseaddr, getaddresses, formataddr
import re

from .extract import get_rec_date
from .constants import ipv4_regex, ipv6_regex, domain_only_regex
from .analyze import get_origin_email, get_origin_ip


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


def get_email_from(field):
    """
    Gets the email portion of a header field, removing
    the display name.
    
    :param field: header field
    """
    emails = []
    addresses = getaddresses(field)
    
    if field is None:
        emails = None
    elif addresses and isinstance(addresses, list):
        for a in addresses:
            emails.append(a[-1])
    elif addresses and isinstance(addresses, str):
        emails.append(a)
    else:
        emails = None

    return emails


def get_name_from(field):
    """
    Gets the display name portion of a header field, removing
    the email.
    
    :param field: header field
    """
    names = []
    addresses = getaddresses(field)

    if field is None:
        names = None
    elif addresses and isinstance(addresses, list):
        for a in addresses:
            names.append(a[-1])
    elif addresses and isinstance(addresses, str):
        names.append(a)
    else:
        names = None

    return names


def emails_to_string(emails):
    """
    Turns a list of emails into a nicely formatted string.
    Can handle header tuples or email addresses. 
    Returns display names and emails.
    
    :param recip_lst: list of strings or tuples
    """
    out_str = None

    if emails is None:
        return None
    
    elif isinstance(emails, str):
        out_str = emails
    
    else:
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


def get_sender(header):
    """
    Uses basic logic to guess a sender. Checks in order of:
    "from", "sender", "reply-to", "return-path"
    
    :param header: parsed header object
    """
    for field in ["from", "sender", "reply-to", "return-path"]:
        sender = header.get_all(field)
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
    if lst_of_recip in [[None], [], None, ""]:
        return None
    elif isinstance(lst_of_recip, str):
        return lst_of_recip
    elif isinstance(lst_of_recip, list):
        return str(lst_of_recip[0])
    else:
        return None
    

def create_field_output(p_header, domains):
    fields = {}
    fields['received_time'] = get_rec_date(p_header)
    fields['from'] = p_header.get_all("from")
    fields['from_name'] = get_name_from(fields['from'])
    fields['from_email'] = get_email_from(fields['from'])
    fields['from_dmn'] = get_dmn_from_addy(fields['from_email'])
    fields['found_sender'] = get_sender(p_header)
    fields['found_sender_name'] = get_name_from(fields['found_sender'])
    fields['found_sender_eml'] = get_email_from(fields['found_sender'])
    fields['found_sender_dmn'] = get_dmn_from_addy(fields['found_sender_eml'])
    fields['to'] = p_header.get_all("to")
    fields['to_name'] = get_name_from(fields["to"])
    fields['to_email'] = get_email_from(fields['to'])
    fields['known_recip_lst'] = get_recip_lst(p_header, domains)
    fields['known_recip_eml_lst'
               ] = [e[1] for e in fields['known_recip_lst']]
    fields['known_recip_str'] = emails_to_string(fields['known_recip_lst'])
    fields['known_recip_eml_str'] = emails_to_string(fields['known_recip_eml_lst'])
    fields['reported_by'] = get_reported_by(fields['known_recip_eml_lst'])
    fields['subject'] = p_header.get("subject")
    fields['trunc_subject'] = truncate_str(fields['subject'])
    fields['date'] = p_header.get("date")
    fields['return_path'] = p_header.get("return-path")
    fields['origin_email'] = get_origin_email(p_header)
    fields['origin_email_dmn'] = get_dmn_from_addy(fields['origin_email'])
    fields['origin_ip'] = get_origin_ip(p_header)
    fields['reply_to'] = p_header.get("reply-to")
    fields['x_mailer'] = p_header.get("x-mailer")
    fields['user_agent'] = p_header.get("user-agent")
    fields['message_id'] = p_header.get("message-id")
    return fields

sanitize_rules = {
    "from": [decode_safe, emails_to_string],
    "from_name": [decode_safe, emails_to_string], 
    "from_email": [decode_safe, emails_to_string], 
    "from_dmn": [decode_safe], 
    "found_sender": [decode_safe, emails_to_string], 
    "found_sender_name": [decode_safe, emails_to_string], 
    "found_sender_eml": [decode_safe, emails_to_string],
    "found_sender_dmn": [decode_safe, emails_to_string],
    "reply_to": [decode_safe, emails_to_string],
    "origin_email": [decode_safe, emails_to_string],
    "origin_email_dmn": [decode_safe, emails_to_string],

    "known_recip_lst": [decode_pretty, emails_to_string],
    "known_recip_eml_lst": [decode_pretty, emails_to_string],
    "known_recip_str": [decode_pretty, emails_to_string],
    "known_recip_eml_str": [decode_pretty, emails_to_string],
    "reported_by": [decode_pretty, emails_to_string],
    "to": [decode_pretty, emails_to_string],
    "message_id": [decode_pretty],

    "return_path": [defang, emails_to_string],
    "origin_ip": [defang],

    "subject": [clean_subject], 
    "trunc_subject": [clean_subject]
}

def sanitize_field_output(fields):
    sanitized = {}

    for k, v in fields.items():
        rules = sanitize_rules.get(k)

        if not v:
            sanitized[k] = ""

        elif rules:
            formatted_value = v
            for r in rules:
                formatted_value = r(formatted_value)
            sanitized[k] = formatted_value

        else:
            sanitized[k] = (v)

    return sanitized