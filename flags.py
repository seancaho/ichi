#! /usr/bin/env python3

# Creates a list of warnings for the analyzed header
def get_warnings(fields_dict):
    intro_warn = ('\n\n======\n\nWARNINGS\n\n======'\
                  '\n\nThe following errors or abnormalities '\
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
    if warnings_lst:
        warnings_lst.insert(0, intro_warn)
        warnings_lst.append('\n\n')
    warn_out = str_from_lst(warnings_lst)
    return warn_out

# From a list, creates an aggregated string text block.
def str_from_lst(in_list):
    linebreak = '\n'
    new_str = linebreak.join(in_list)
    return new_str