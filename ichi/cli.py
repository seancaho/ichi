#! /usr/bin/env python3


from os import system
import typer
from rich import print
from rich.prompt import Prompt
from rich.table import Table
from os.path import isfile

from .console import console
from .input import email_from_file


def print_loop(links, mailto, attachments, linked_images, embedded_images, hops):
    while True:
        user_command = Prompt.ask("\nWhat else do you want to see?", choices=[
            "links", "attachments", "images", "hops", "full_model", "clear", "exit",
        ])
        nxt = user_command.lower()

        if nxt == "exit":
            console.print("\nExiting printer.", style="warning")
            break

        if nxt == "clear":
            system("clear")

        elif nxt == "links":

            if not links or len(links) == 0:
                console.print("No links to display.", style="info")

            else:
                console.print(f"Link quantity: {len(links)}")
                print(links)
                console.print(f"Mailto link quantity: {len(mailto)}")
                print(mailto)

        elif nxt == "attachments":

            if not attachments or len(attachments) == 0:
                console.print("No attachments to display.", style="info")

            else:
                console.print(f"Attachment quantity: {len(attachments)}")
                print(attachments)

        elif nxt == "images":

            if len(linked_images) == 0 and len(embedded_images) == 0:
                    console.print("No images to display.", style="info")

            else:
                console.print(f"Linked image quantity: {len(linked_images)}")
                print(linked_images)

                console.print(f"Embedded image quantity: {len(embedded_images)}")
                print(embedded_images)

        elif nxt == "hops":

            if not hops or len(hops) == 0:
                console.print("No hops to display.", style="info")

            else:
                console.print(f"Hop count: {len(hops)}")
                hop_table = Table(show_header=True, show_lines=True)

                recone = hops[0].get("received")
                columns = list(recone.keys())

                for k in recone.keys():
                    hop_table.add_column(str(k))

                for h in hops:
                    rec_fld = h.get("received")

                    row_cells = [str(rec_fld.get(col, "")) for col in columns]

                    hop_table.add_row(*row_cells)
    
                console.print(hop_table)

        elif nxt == "full_model":
            
            for h in hops:
                print(h)



def loader():

    path = ""

    while True:
        path = Prompt.ask("\nGive me another eml.")
        
        if path == "exit":
            console.print("\nExiting loader.", style="warning")
            break

        if isfile(path) and path.endswith(".eml"):
            
            return email_from_file(path)

        else:
            print("Couldn't find the specified file.")

    return None