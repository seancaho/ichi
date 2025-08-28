#! /usr/bin/env python3

# creates the summary statement
def get_sum_state(output_dict):
    statement = (f"On {output_dict['received_time']}, ")
    if len(output_dict['known_recip_eml_lst']) > 1:
        count = len(output_dict['known_recip_eml_lst'])
        statement += (f"{count} users ")
    elif len(output_dict['known_recip_eml_lst']) == 1:
        statement += (f"{output_dict['known_recip']} ")
    else:
        statement += ("a user ")
    statement += (f'''received an email with the subject line, "{output_dict['subject']}"''')
    if output_dict['from_email']:
        statement += (f" from {output_dict['from_email']}.")
    elif output_dict['origin_email']:
        statement += (f" from {output_dict['origin_email']}.")
    else:
        statement += ('.')
    return statement

# assembles the full macro for output
def get_full_macro(statement, meta, raw_header, client, analyst):
    macro = (
f'''
Event Summary:
{statement}

Remediation & Mitigation Performed by {analyst['tm_abbr']}:
<List all actions taken and enumerate targets for each>

Remediation & Mitigation Outstanding (to be performed by {client}):
<List all additional actions that must be taken by {client}>

{meta}

Behaviors:

Impersonation / Spoofing
<Details of impersonation (individual, domain, actual spoofing, etc.)>

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