This project organizes information on item drops from the
[OSRS Wiki](https://oldschool.runescape.wiki/) using a SQLite database
to enable more detailed queries than are a possible using the website.
The primary problem this solves is determining what monsters drop a specific
item. The OSRS Wiki has mostly complete drop tables for monsters in the game
but, the tables for items are often completely missing of seriously incomplete.
This tool collects the drop tables for all monsters and uses this information
to generate tables of dropping monsters for any item.

The included python script implements some basic database queries but, complicated
queries can be done by running SQL queries directly on the database file.

## Updating the Database
The script `create_database.py` is used to create an updated version
of the database from a dump of OSRS Wiki pages.

  `./create_database.py wiki_dump.xml loot_database.db`

This command will overwrite the default database with an updated
databsae contructed from `wiki_dump.xml`. If you want to, you can
specify an alternate output file for the new database.

To obtain a fresh dump of OSRS Wiki pages, go to
oldschool.runescape.wiki/w/Special:Export and use "Add pages from category"
to add the categories "Monsters" and "Hunter creatures" then click the "Export"
button.
