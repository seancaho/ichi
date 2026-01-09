#! /usr/bin/env python3

from rich.console import Console
from rich.theme import Theme

custom_theme = Theme({
    "info": "green",
    "warning": "bold yellow",
    "error": "bold red",
    "prompt.choices": "green"
})

console = Console(theme=custom_theme, highlight=False)