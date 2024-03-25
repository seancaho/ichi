# Ichi Script
A ticketing utility for pulling and sanitizing key information from an email header. Named in honor of the number one pet. 

# Description
Ichi Script speeds up the ticket writing process by automating field extraction and output sanitization. It is not intended to be an analysis or investigation tool. Yet. 

Ichi was built to run in Terminal on Mac. With a little setup, this should be an extremely fast and straightforward means of interacting with Ichi.

Using Ichi Script is intended to be straightforward. Run Ichi Script from Terminal and follow the prompts to generate your ticket template.

Ichi receives primary input from the clipboard with a second input typed into Terminal. Ichi then parses the required fields and returns sanitized output. Ichi's output should be ready to copy/paste into final documentation. The script relies heavily on Python's email package for parsing and building email headers.

# Warning

All Ichi Script outputs should be checked for accuracy and safety prior to submission to a client. 

# Options
Within the ichi_config.py file, there are multiple "Config Options" that will enable you to customize the outputs of ichi_script.py and make the script run more quickly once you understand its process. 

All config options are booleans and should only ever be set to "True" or "False". 

Adjusting other elements within ichi_config.py may break the script. 

# Setup
Ichi Script is built in Python3 and is intended to run in Terminal on Mac. To use Ichi Script most effectively, you will need to: 

1. Install Python3
2. Download Ichi Script
3. Install dependencies
4. Create an alias to easily run Ichi Script

## 1. Install Python3
Good guides to installing Python3 have already been created. The linked repo here includes clear instructions for installing Python on multiple platforms. 

[Install Python3 by PackeTsar](https://github.com/PackeTsar/Install-Python/)

## 2. Download Ichi Script
All files included in Ichi Script should live in the same directory and no file names should ever be modified. 

Move all Ichi Script files into a directory where they can permanently live on your machine. You will not need to access this file often. For example, create something like a `code` directory in your `Documents` folder. 
```
mkdir ~/Documents/code
```
Then move the ichi folder and all contents into that directory. 
```
mv ~/Downloads/ichi /Documents/code/
```
Or just use Finder and do this the easy way. ;) 

Ichi Script will likely be updated from time to time. When updated files are sent, simply replace the files in the ichi directory with the updated versions.

## 3. Install Required Packages
The majority of dependencies that Ichi Script relies on are part of the standard library. Packages not in the standard library that need to be added to your local machine are listed at the top of the files in Ichi Script and aggregated in requirements.txt. 

To add the packages, after installing Python3, move into the ichi directory:
```
cd ~/Documents/code/ichi
``` 

And then run the following commands: 
```
pip3 install -r requirements.txt
``` 

## 4. Create an alias to easily run Ichi Script 
Creating an alias will make it fast and simple to use Ichi Script. An alias creates a shortcut to execute a command in Terminal. So rather than having to type something like this every time you want to use Ichi:
```
python3 python3 /Users/<your_username>/Documents/code/ichi/ichi_script.py
```
Instead, if you create an alias, you can just use:
```
ichi
```
To create an alias, we'll modify your `.bash_profile`. In Terminal, move to your home directory.
```
cd ~/
```
Then use Nano to edit the `.bash_profile` file.
```
nano .bash_profile
```
Add the following lines to the bottom of your `.bash_profile`. Be sure to change the path included to match the location and name you gave to the ichi_script.py file you created in step 3. 
```
# ALIASES
alias ichi='python3 /Users/<your_username>/Documents/code/ichi/ichi_script.py'
```
When you are finished, save your changes and exit Nano `Ctrl+X` then `Y`. Completely quit and restart Terminal to reload your `.bash_profile`. 

You should now be able to type `ichi` in Terminal to run Ichi Script.