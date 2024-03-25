#! /usr/bin/env python3

# Proprietary and client information should never be shared. 
# Edit this file locally with necessary details.

# CONFIG OPTIONS 
# whether ichi requires user to hit return to submit header
quickness = True
# whether output is the entire macro or only the metafields
meta_only = False
# whether the output is put back on the clipboard
clip_output = True
# whether additional warnings are printed after macro
print_warnings = True

# PERSONAL INFORMATION
personal_info = {
    # This info relates to the company you work for
    # Replace the example info with your own
    "company": "Example Company",
    "cmp_abbr": "EC",
    "team": "Team Name",
    "tm_abbr": "EC TN",
                }

client_info = {
    # Replace the example values below for each client
    # Add a new line for every client company
    # Multiple domains can be added for a client as shown
    # Formatting must be matched exactly
    "Client Name 1": {
        "domains": ["gmail.com"],
                      },
    "Client Name 2": {
        "domains": ["example.com", "example2.com", "example3.com"],
                      },
    "Client Name 3": {
        "domains": ["fast.com"],
                      },
                }