#! /usr/bin/env python3

# Modules requiring installation
from dateutil.parser import parse as du_parse
from dateutil.tz import tzutc
from bs4 import BeautifulSoup, SoupStrainer

# Built-in modules
from .constants import ipv4_regex, rfc1918_regex, regex_smtpfrom
import re
import hashlib
from urllib.parse import urlsplit, parse_qs
from base64 import b64decode

authres_property = re.compile(
    r"\b[-a-zA-Z0-9\._\-#=]+\s?=\s?[-a-zA-Z0-9@:%\._\+~#=]+\b", 
    re.IGNORECASE)

authres_clientip = re.compile(
    r"sender\ ip\ is\ ([-a-zA-Z0-9@:%\._\+~#=]+)" # microsoft
    r"|domain\ of\ [-a-zA-Z0-9@:%\._\+~#=]+\ designates\ ([0-9a-fA-F\.\:]+)\ as", # google
    re.IGNORECASE)

def get_header_text(email):
    """
    Takes a parsed email object and returns only the headers as a 
    text block. 
    
    :param email: parsed email object
    """
    headers_lst = []
    for v,s in email.items():
        headers_lst.append(f"{v} {s}")
    header_str = "\n".join(headers_lst)
    return header_str


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
    name = name.split(".") if name else None
    if isinstance(name, list):
        return name[-1]
    else: 
        return name


def make_attachment_data(part):
    """
    Returns modeled information in a dictionary about an encoded file.
    
    :param part: str (encoded file)
    """
    if part.get_content_type() == "message/rfc822":
        payload = part.get_content().as_bytes()
    else:
        payload = part.get_payload(decode=True)
    attachment_data = {
        "filename": part.get_filename(),
        "file_extension": make_extension(part.get_filename()),
        "content_type": part.get_content_type(),
        "size": len(payload),
        "content_transfer_encoding": part["Content-Transfer-Encoding"],
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
    
    attachment_mimetypes = [
        "image", 
        "audio", 
        "video", 
        "application",
        "calendar",
        "csv",
        "font"
        ]
    
    attached = []

    if msg.get_content_disposition() == "attachment":
        attached.append(make_attachment_data(msg))

    def iterate_for_attachments(msg_part):
        for part in msg_part.iter_parts():
            maintype = part.get_content_maintype()
            subtype = part.get_content_subtype()

            if part.is_attachment() == True:
                attached.append(make_attachment_data(part))

            elif maintype in attachment_mimetypes or subtype in attachment_mimetypes:
                attached.append(make_attachment_data(part))

            elif maintype == "multipart":
                iterate_for_attachments(part)

    iterate_for_attachments(msg)
        
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

    for k,v in full_params.items():
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

    if not body:
        return links, mailto

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

    if not body:
        return linked_images, embedded_images

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


def normalize_date(gnarly_date):
    """
    Takes a raw datetime as a string. Makes minor efforts to normalize
    the data. Parses the string. Returns a normalized timestamp in UTC
    as a string.
    
    :param gnarly_date: raw datetime string
    """
    cleaned_date = re.sub(r"m=\+[0-9.]+(?=\s|$)", "", gnarly_date).strip()

    parsed_date = du_parse(cleaned_date, fuzzy=True)

    date_utc = parsed_date.astimezone(tzutc())

    tidy_date = date_utc.strftime("%Y-%m-%d %H:%M:%S %z")
    return tidy_date


def slice_remover(text, span, remove_delims=False):
    """
    Removes a delimited slice from a string.
    Returns:
        (remaining_text, removed_slice)

    Start and end indices should be for the delimiter.
    If indices are invalid, returns (original_text, "")
    Optionally, strips the delimiters from removed_slice
    
    :param text: string
    :param range: tuple of delimiter indices
    :param remove_delims: bool
    """
    t_length = len(text)
    s, e = span

    # end is exclusive
    # increment 1 to include last bound
    # set to end if appropriate
    e = e + 1 if e < t_length else None

    # adjust slice ends for remove_delims
    if remove_delims:
        slice_s = s + 1
        slice_e = e - 1
    else:
        slice_s = s
        slice_e = e
    
    if not (0 <= s <= e <= t_length):
        return text, ""       
    
    return text[:s].strip() + " " + text[e:].strip(), text[slice_s:slice_e]


def get_parenthetical_ranges(test, paren_type):
    """
    Finds the start and end indices of substrings enclosed by 
    parentheses within a string. Enclosure type, parentheses or 
    other, can be given in paren_type.
    Returns a list of tuples with start, end indices.
    Breaks and returns an empty array in case of failure. 
    
    :param test: string to test
    :param paren_type: tuple of start and end enclosure
    """
    open_p = []
    closed_p = []
    left = paren_type[0]
    right = paren_type[1]

    if test.count(left) != test.count(right):
        #TODO: good place for debugging - 
            # unbalanced parentheses in received
        return closed_p

    elif left == right:
        for i in range(len(test)):
            if test[i] == left and len(open_p) == 0:
                open_p.append((i,None))
            elif test[i] == left and len(open_p) > 0:
                open_set = open_p.pop(-1)
                closed_p.append((open_set[0], i))

    else:
        for i in range(len(test)):
            if test[i] == left:
                open_p.append((i,None))
            elif test[i] == right:
                if len(open_p) < 1:
                    #TODO: good place for debugging - 
                        # close parenthesis without open
                    closed_p = []
                    return closed_p
                open_set = open_p.pop(-1)
                closed_p.append((open_set[0], i))

    return closed_p


def make_received_data(field, field_n):
    """
    Takes a received field string and returns structured data.
    Returns a dictionary.
    
    :param field: str of field content
    :param field_n: str of field name
    """
    delims = {"from": None, 
              "by": None,
              "with": None,
              "id": None,
              "for": None,
              "via": None,
              ";": None,
              }
    assignments = {"from": "submitter", 
              "by": "receiver",
              "with": "type",
              "id": "id",
              "for": "for",
              "via": "via",
              ";": "time",
              }
    data = {"submitter": None, 
            "receiver": None,
            "type": None,
            "id": None,
            "for": None,
            "via": None,
            "time": None,
            }
    
    working_field = field

    # best effor to handle bad date separation
    day_match = (r"\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun)"
                 r"(?!.*\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b)"
                )
    date_match = (r"\s*(\d{4}-\d{1,2}-\d{1,2})"
                  r"(?!.*\b(\d{4}-\d{1,2}-\d{1,2})\b)"
                )
        
    date_delim = working_field.rfind(";")
    if date_delim == -1:
        working_field = re.sub(day_match, r"; \1", working_field)
        date_delim = working_field.rfind(";")
    if date_delim == -1:
        working_field = re.sub(date_match, r"; \1", working_field)
        date_delim = working_field.rfind(";")

    # set and remove date from working
    delims[";"] = date_delim
    date_slice = working_field[date_delim:].removeprefix(";").strip()
    data[assignments[";"]] = normalize_date(date_slice)
    working_field = working_field[:date_delim]

    # get parenthetical ranges for delimeter exlusion
    paren_ranges = []
    paren_types = [("(", ")"), ("[", "]"), ("'", "'"), ('"', '"')]
    for t in paren_types:
        if t[0] in working_field:
            paren_ranges.extend(get_parenthetical_ranges(working_field, t))

    # capture lists of delimiters outside of parentheticals
    for d in delims.keys():
        if d in working_field:
            # find all indices for the delimiter
            found_indices = []
            for match in re.finditer(rf"\b{re.escape(d)}\b", 
                                     working_field, 
                                     flags=re.IGNORECASE):

                found_indices.append(match.start())
            # keep only those indices that are not in a parenthetical
            good_indices = []
            for i in found_indices:
                index_is_valid = True
                for r in paren_ranges:
                    if r[0] <= i <= r[1]:
                        index_is_valid = False
                        break
                if index_is_valid:
                    good_indices.append(i)
            # if more than one index is found, take the left most
            if good_indices:
                delims[d] = min(good_indices) if good_indices else None
            else:
                delims[d] = None

    # check that slices are currently in order
    ordered = True
    last_value = 0
    for k,v in reversed(delims.items()):
        if v and v >= last_value:
            last_value = v
            ordered = False
    
    # slice field into data
    for k,v in reversed(delims.items()):
        if v is not None and k != ";":
            data_slice = working_field[v:].removeprefix(k).strip()
            data[assignments[k]] = data_slice
            if v != 0:
                working_field = working_field[:v]

    return data


authentication_properties = {
    # SPF + AUTH
    "smtp.mailfrom": "envelope_from",
    "smtp.auth": "authorization_identity",
    "smtp.helo": "smtp_greeting",

    # DKIM
    "header.d": "signing_domain",
    "header.i": "signing_identity",
    "header.a": "dkim_algorithm",
    "header.s": "dkim_selector",
    "header.b": "dkim_signature",

    # DMARC
    "action": "action",
    "header.from": "from_domain",
    "policy": "dmarc_policy",
    "disposition": "dmarc_disposition",
    "reason": "dmarc_reason",
}


def make_recspf_data(field, field_n):
    """
    Given a received-spf header field, fully parses the field
    and returns structured data in a dictionary.
    
    :param field: str of field content
    :param field_n: str of field name
    """
    data = {}
    recspf_properties = {
        "helo": "smtp_greeting",
        "client-ip": "client_ip",
        "receiver": "receiver",
        "envelope-from": "envelope_from"
    }

    data["verdict"] = field.partition(" ")[0]

    properties = re.findall(authres_property, field)

    for i in range(len(properties)):
        p = properties[i]
        ptype_end = p.find("=")
        pvalue_start = ptype_end + 1
        if p[:ptype_end] in recspf_properties.keys():
            data[recspf_properties[p[:ptype_end]]] = p[pvalue_start:]

    return data


def authresults_details(fragment):
    """
    Takes a fragment of an authentication-results header and parses
    the included elements. Returns a dictionary of structured data.
    
    :param fragment: str
    """
    data = {}
    
    # find commented ranges
    comment_bounds = ("(", ")")
    comment_locations = []
    comment_locations.extend(
        get_parenthetical_ranges(fragment, comment_bounds)
    )

    # remove a single comment
    # ignore if none or more than one
    if len(comment_locations) == 1:
        for c in comment_locations:
            fragment, comment = slice_remover(fragment, c, True)
        data["comments"] = comment

        # take tested IP from found comment
        if comment:
            ip_match = re.match(authres_clientip, comment)
            if ip_match:
                data["client_ip"] = ip_match.group(1)
    
    # find and assign data from method and properties
    # standard for methods, properties, and results:
    # https://datatracker.ietf.org/doc/html/rfc8601#section-2.5
    properties = re.findall(authres_property, fragment)

    for i in range(len(properties)):
        p = properties[i]
        ptype_end = p.find("=")
        pvalue_start = ptype_end + 1
        if i == 0:
            method = p[:ptype_end]
            if "/" in method:
                method_split = method.split("/")
                method = method_split[0]
                if len(method_split) == 2:
                    data["version"] = method_split[1]
            data["verdict"] = verdict = p[pvalue_start:]
        else:
            if p[:ptype_end] in authentication_properties.keys():
                data[authentication_properties[p[:ptype_end]]] = p[pvalue_start:]
    
    return method, verdict, data


def make_authresults_data(field, field_n):
    """
    Given an authentication-results header field, fully parses the field
    and returns structured data in a dictionary.
    
    :param field: str of field content
    :param field_n: str of field name
    """
    methods = [ "spf", "dkim", "dmarc", "iprev", "auth", "compauth"]

    data = {}

    # split the field into its components
    field_split = [i.strip() for i in field.split(";")]

    for e in range(len(field_split)):
        f = field_split[e]

        # make an authentication server record if the first element
        # appears to be one
        if e == 0 and "=" not in f:

            authserv_elements = f.split()

            for a in range(len(authserv_elements)):
                elem = authserv_elements[a]
                if elem.startswith("(") and elem.endswith(")"):
                    authserv_elements.pop(a)
            
            if len(authserv_elements) == 2:
                data["authenticator"] = authserv_elements[0]
                data["authenticator_version"] = authserv_elements[1]
            elif len(authserv_elements) == 1:
                data["authenticator"] = authserv_elements[0]

        # otherwise parse expected methods
        else:
            test_method = f[:f.find("=")]
            if "/" in test_method:
                test_method = test_method.split("/")[0]
            if test_method in methods:
                method_name, verdict, details = authresults_details(f)
                detail_label = method_name + "_details"
                data[detail_label] = details
                data[method_name] = verdict

    if field_n == "authentication-results-original":
        data["authentication_results_original"] = field_n
    else:
        data["authentication_results"] = field_n

    return data

antispam_elements = {
    "CIP": "src_ip",
    "PTR": "srcip_reversedns",
    "CTRY": "srcip_country",
    "LANG": "msg_language",
    "H": "helo_string",
    "DIR": "direction",
    "CAT": "threat_policy_category",
    "SCL": "spam_confidence_level",
    "SFV": "spam_filtering_action",
    "SFTY": "phishing_mark"
}

def make_antispam_report(field, field_n):

    data = {}

    # https://learn.microsoft.com/en-us/defender-office-365/message-headers-eop-mdo

    elements = field.split(";")

    for e in elements:
        partitioned = e.partition(":")

        if partitioned[2] and partitioned[0] in antispam_elements.keys():
            data[antispam_elements[partitioned[0]]] = partitioned[2]

    return data


# map primary extraction function to field name
extractors = {
    # "header-field": (parse_function, key_for_data)
    "authentication-results": (
        make_authresults_data, "authentication_results"),
    "authentication-results-original": (
        make_authresults_data, "authentication_results_original"),
    "received-spf": (
        make_recspf_data, "received_spf"),
    "received": (
        make_received_data, "received"),
    "x-forefront-antispam-report": (
        make_antispam_report, "antispam_report")
}


def build_hop_data(header):
    """
    Builds all fields related to a single hop in the header
    into structured data. Returns an array of dictionaries.
    
    :param header: parsed email object
    """
    hops = []

    field_count = 0
    hop_count = 0
    current_field_set = []

    working_hop = {}

    for k,v in reversed(header.items()):
        field = str.lower(k)

        value = " ".join(str(v).split())

        current_field_set.append({
            "field": field,
            "value": value,
            "position": field_count,
            })
        
        field_count += 1

        if field in extractors.keys():
            working_hop[extractors[field][1]] = extractors[field][0](value, field)

        if field == "received":
            working_hop["hop_index"] = hop_count
            working_hop["fields"] = current_field_set

            hops.append(working_hop)

            current_field_set = []
            working_hop = {}
            hop_count += 1

    return hops