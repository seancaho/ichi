#! /usr/bin/env python3


from .extract import get_email_authresults, get_ip_received, \
    get_ip_xforefrontantispam, get_ip_receivedspf


def get_origin_email(header):
    """
    Makes a guess at the sender based on the following fields:
    Authentication-Results, Return-Path, Sender, From
    
    :param header: parsed header object
    """
    try:
        origin_email = ''
        if get_email_authresults(header):
            origin_email = get_email_authresults(header)
        elif header['return-path']:
            origin_email = header['return-path']
        elif header['sender']:
            origin_email = header['sender']
        elif header['from']:
            origin_email = header['from']
        else:
            origin_email = None
        return origin_email
    except TypeError:
        origin_email = None


def get_origin_ip(header):
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
    earliest_ipv4_in_hops = get_ip_received(header)

    # parse IP from X-Forefront-Antispam-Report
    ip_xforefront_antispam = get_ip_xforefrontantispam(header)
        
    # return the first 'client-ip' found from all Received-SPF records
    ip_all_rec_spf = get_ip_receivedspf(header)

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