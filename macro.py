#! /usr/bin/env python3

# creates the summary statement
def get_sum_state(output_dict, trunc_instruct):
    # add the date
    statement = (f"On {output_dict['received_time']}, ")
    # add the recipient
    if len(output_dict['known_recip_eml_lst']) > 1:
        count = len(output_dict['known_recip_eml_lst'])
        statement += (f"{count} users ")
    elif len(output_dict['known_recip_eml_lst']) == 1:
        statement += (f"{output_dict['known_recip_eml_str']} ")
    else:
        statement += ("a user ")
    # add the subject
    if not trunc_instruct:
        statement += (f'''received an email with the subject line, '''
                      f'''"{output_dict['subject']}"''')
    elif trunc_instruct:
        statement += (f'''received an email with the subject line, '''
                      f'''"{output_dict['trunc_subject']}"''')        
    # add the from
    if output_dict['from_email']:
        if not trunc_instruct:
            statement += (f" from {output_dict['from_email']}.")
        elif trunc_instruct and len(output_dict['from_email']) > 75:
            statement += (f" from {output_dict['from_dmn']}.")
        else: 
            statement += (f" from {output_dict['from_email']}.")
    elif output_dict['origin_email']:
        if not trunc_instruct:
            statement += (f" from {output_dict['origin_email']}.")
        elif trunc_instruct and len(output_dict['origin_email']) > 75:
            statement += (f" from {output_dict['origin_email_dmn']}.")
        else:
            statement += (f" from {output_dict['origin_email']}.")
    else:
        statement += ('.')
    return statement

# assembles the full macro for output
def get_full_macro(statement, meta, raw_header, analyst):
    macro = (
f'''
Event Summary:
{statement}

Remediation & Mitigation Performed by {analyst['tm_abbr']}:
<List all actions taken and enumerate targets for each>

Remediation & Mitigation Outstanding (to be performed by client):
<List all additional actions that must be taken by client>

{meta}

Behaviors:

Analysis & Response

What is it and what happened?
{statement}

What did we learn from analysis?
<Results from analysis of headers.  Results from analysis of content (attachments and hyperlinks).  Have we seen anything like this before?  Is this part of or related to other activity? Is this related to known threats, actors, campaigns, etc.?>

What actions did we take during investigation?
- Analyzed email headers
- Investigated email contents
- Reviewed 30 day email context
- Remediated email

Raw Event
{raw_header}
'''
            )
    macro = macro.strip()
    return macro