#! /usr/bin/env python3

# Modules requiring installation
from dateutil.parser import parse as du_parse

# Built-in modules
from .constants import ipv4_regex, rfc1918_regex, regex_smtpfrom
import re
import hashlib

def get_rec_date(header):
    """
    Returns the datetime from the latest received field
    in local system time.
    
    :param parsed_header: parsed header object
    """
    if header.get("received"):
        hop = header.get("received").split(';')
        hop_date = str(hop[1]).strip()
        parsed_date = du_parse(hop_date, fuzzy=True)
        local_parsed_date = parsed_date.astimezone()
        return local_parsed_date.strftime("%a, %b %d, %Y %H:%M %Z")
    else:
        return None


def get_ip_xforefrontantispam(header):
    """
    Returns the connecting IP (CIP) from an X-Forefront-Antispam-Report
    email header if one exists. Otherwise None. 
    
    learn.microsoft.com/en-us/defender-office-365/message-headers-eop-mdo
    
    :param header: parsed header object
    """
    field = header.get("X-Forefront-Antispam-Report")
    if field:
        return re.search(r'CIP:([^;]+)', field).group(1)
    else:
        return None


def get_ip_received(header):
    """
    Returns the earliest IPv4 found in the chain of Received records,
    if there is one. Otherwise returns None.
    
    :param header: parsed header object
    """
    earliest_ipv4 = None
    all_received = header.get_all("received")
    try:
        for hop in reversed(all_received):
            hop = hop.replace('\n', '').replace('\r', '')
            hop_withoutby = re.sub(r'by.*', '', hop, re.S)
            ips_found = ipv4_regex.findall(hop_withoutby)
            if len(ips_found) > 0:
                if rfc1918_regex.match(ips_found[-1]):
                    continue
                else:
                    earliest_ipv4 = ips_found[-1]
                    break
            elif not earliest_ipv4 and len(ips_found) == 0:
                continue
            elif earliest_ipv4 and len(ips_found) == 0:
                continue
        return earliest_ipv4
    except (AttributeError, TypeError):
        earliest_ipv4 = None


def get_ip_receivedspf(header):
    """
    Returns the client ip from the earliest Received-SPF record,
    or None if none exist. 
    
    :param header: parsed header object
    """
    client_ip_regex = re.compile(r'client-ip=([^;]+)', re.IGNORECASE)
    rec_spfs = header.get_all("received-spf")

    if rec_spfs:
        for rec in reversed(rec_spfs):
            m = client_ip_regex.search(rec)
            if m:
                ip = m.group(1).strip(' []')
                return ip
    else:
        return None


def get_email_authresults(header):
    """
    Returns the an email address found listed in the earliest 
    Authentication-Results field listed as smtp.mailfrom.
    
    :param header: parsed header object
    """
    results = header.get_all("authentication-results")

    if results:
        for r in results:
            smtpfrom = regex_smtpfrom.search(r)
            if smtpfrom:
                return smtpfrom.group(2)
    else:
        return None
    

def make_extension(name):
    name.split(".")
    if isinstance(name, list):
        return name[-1]
    else: 
        return name


def make_attachment(file):
    """
    Returns modeled information in a dictionary about an encoded file.
    
    :param file: str (encoded file)
    """
    payload = file.get_payload(decode=True)
    return {
    "filename": file.get_filename(),
    "file-extension": make_extension(file.get_filename()),
    "content-type": file.get_content_type(),
    "size": len(payload),
    "content-transfer-encoding": file.get("Content-Transfer-Encoding"),
    "md5": hashlib.md5(payload).hexdigest(),
    "sha1": hashlib.sha1(payload).hexdigest(),
    "sha256": hashlib.sha256(payload).hexdigest(),
                    }


def get_attachments(msg):
    """
    Returns list of objects with structured info for each included
    attachment. 
    
    :param msg: parsed email object
    """
    if msg.is_multipart() == False:
        return []
    
    attachment_mimetypes = [
        "image", 
        "audio", 
        "video", 
        "application"
        ]
    
    attached = []

    for part in msg.iter_parts():
        type = part.get_content_maintype()

        if part.is_attachment() == True:
            attached.append(make_attachment(part))

        elif type in attachment_mimetypes:
            attached.append(make_attachment(part))
        
    return attached