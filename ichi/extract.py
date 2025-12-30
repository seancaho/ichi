#! /usr/bin/env python3

# Modules requiring installation
from dateutil.parser import parse as du_parse
from bs4 import BeautifulSoup, SoupStrainer

# Built-in modules
from .constants import ipv4_regex, rfc1918_regex, regex_smtpfrom
import re
import hashlib
from urllib.parse import urlsplit, parse_qs
from base64 import b64decode

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


def make_attachment_data(file):
    """
    Returns modeled information in a dictionary about an encoded file.
    
    :param file: str (encoded file)
    """
    payload = file.get_payload(decode=True)
    attachment_data = {
        "filename": file.get_filename(),
        "file_extension": make_extension(file.get_filename()),
        "content_type": file.get_content_type(),
        "size": len(payload),
        "content_transfer_encoding": file.get("Content-Transfer-Encoding"),
        "md5": hashlib.md5(payload).hexdigest(),
        "sha1": hashlib.sha1(payload).hexdigest(),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }

    return attachment_data


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
            attached.append(make_attachment_data(part))

        elif type in attachment_mimetypes:
            attached.append(make_attachment_data(part))
        
    return attached


def get_body(msg):
    """
    Returns parsed and decoded bodies as strings for html body
    and plaintext body included in the main email.
    
    :param msg: parsed email object
    """

    html_body = None
    plain_body = None

    html_body = msg.get_body(preferencelist=("html"))
    if html_body:
        html_body = html_body.get_content() 
    plain_body = msg.get_body(preferencelist=("plain"))
    if plain_body:
        plain_body = plain_body.get_content()

    return html_body, plain_body


def make_link_data(anchor):
    """
    Takes a parsed html object and returns structured data for the 
    link included in the anchor tag. 
    
    :param anchor: soup object
    """
    href = anchor.get("href")
    original = anchor.get("originalsrc")
    text = anchor.get_text(strip=True)
    safelink = None

    if original:
        rewritten = True
        url = original
        safelink = {
            "rewritten_url": href,
        }
    else:
        url = href
        rewritten = False

    try:
        split_url = urlsplit(url)
        path = url.split(split_url.hostname)[-1]
    except:
        path = None

    link_data = {
        "url": url,
        "domain": split_url.hostname,
        "scheme": split_url.scheme,
        "path": path,
        "display_text": text,
        "rewritten": rewritten,
        "safelink": safelink
    }

    return link_data
    

def make_mailto_data(mailto):
    """
    Takes a parsed html object and returns structured data for the 
    mailto emails included in the anchor tag. 
    
    :param mailto: soup object
    """
    url = mailto.get("href")
    split_url = urlsplit(url)
    full_params = parse_qs(split_url.query)

    recipients = set()
    recipients.add(split_url.path)

    for k,v in full_params:
        for i in v:
            recipients.add(i)

    mailto_data = {
        "url": url,
        "recipients": list(recipients)
    }

    return mailto_data


def make_imglink_data(img):
    """
    Takes a parsed html object and returns structured data for the 
    linked images included in the image tag. 
    
    :param img: soup object
    """
    src = img.get("src")

    split_url = urlsplit(src)

    link_data = {
        "url": src,
        "domain": split_url.hostname,
        "scheme": split_url.scheme,
    }
    return link_data


def make_embedded_data(embed):
    """
    Takes a parsed html object and returns structured data for the 
    embedded image object included in the image tag. 
    
    :param embed: soup object
    """
    src = embed.get("src")

    delimeters = r"[:;,]"
    split_src = re.split(delimeters, src)
    filetype, encoding, data = split_src[-3], split_src[-2], split_src[-1]
    extension = filetype.split("/")[-1]

    if encoding == "base64":
        decoded_data = b64decode(data)

    embed_data = {
        "file_extension": extension,
        "size": len(decoded_data),
        "encoding": encoding,
        "md5": hashlib.md5(decoded_data).hexdigest(),
        "sha1": hashlib.sha1(decoded_data).hexdigest(),
        "sha256": hashlib.sha256(decoded_data).hexdigest(),
    }
    return embed_data


def get_anchors(body):
    """
    Takes a parsed html body and further parses specific tags into
    structured data. Returns lists of entities.
    
    :param body: parsed email object
    """
    links = []
    mailto = []

    strainer = SoupStrainer(["a"])
    soup = BeautifulSoup(body, "html.parser", parse_only=strainer)
    anchors = soup.find_all("a")

    link_set = set()
    for a in anchors:
        testurla = a.get("href")
        testurlb = a.get("originalsrc")

        if testurla.startswith("mailto:"):
            mailto.append(make_mailto_data(a))

        elif testurlb:
            if testurlb not in link_set:
                links.append(make_link_data(a))
                link_set.add(testurlb)
        elif testurla and testurla not in link_set:
            links.append(make_link_data(a))
            link_set.add(testurla)            

    return links, mailto


def get_images(body):
    """
    Takes a parsed html body and further parses specific tags into
    structured data. Returns lists of entities.
    
    :param body: parsed email object
    """
    linked_images = []
    embedded_images = []

    strainer = SoupStrainer(["img"])
    soup = BeautifulSoup(body, "html.parser", parse_only=strainer)
    imgs = soup.find_all("img")      

    imglink_set = set()
    for i in imgs:
        src = i.get("src")

        if src.startswith("data:image"):
            embed_data = make_embedded_data(i)
            if embed_data["sha256"] not in imglink_set:
                embedded_images.append(embed_data)
                imglink_set.add(embed_data["sha256"])

        elif src.startswith("http"):
            if src not in imglink_set:
                linked_images.append(make_imglink_data(i))
                imglink_set.add(src)
                
    return linked_images, embedded_images