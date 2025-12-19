#! /usr/bin/env python3

def get_warnings(fields_dict):
    """
    Creates a list of warnings based on header content that appears
    malicious or not standards compliant.
    
    :param fields_dict: dictionary of parsed fields
    """
    intro_warn = ('\n\nThe following errors or abnormalities '\
                    'were found in parsing this email header.'\
                    '\nYour output was likely affected.\n\n')
    warnings_lst = []
    if not fields_dict['to']:
        warnings_lst.append(
            "### No 'to' field included")
    elif not fields_dict['to_email']:
        warnings_lst.append(
            "### No email address included in the 'to' field")
    if not fields_dict['from']:
        warnings_lst.append(
            "### No 'from' field included")
    elif not fields_dict['from_email']:
        warnings_lst.append(
            "### No email address included in the 'from' field")
    if not fields_dict['date']:
        warnings_lst.append(
            "### No 'date' field included")
    if not fields_dict['known_recip_str']:
        warnings_lst.append(
            "### No email addresses with the specified client domain "\
            "were found in this email header. The original recipient "\
            "was likely included in an obfuscated way, e.g. BCC.")
    if fields_dict['subject'] == "<empty>":
        warnings_lst.append(
            "### The 'subject' field was blank or none was included")
    if not fields_dict['message_id']:
        warnings_lst.append(
            "### No 'message-id' field included")
    if not fields_dict['origin_email']:
        warnings_lst.append(
            "### Multiple expected fields related to the sender were "\
            "not found. This email is not standards compliant.")
    if warnings_lst:
        warnings_lst.insert(0, intro_warn)
        warnings_lst.append('\n\n')
    return warnings_lst