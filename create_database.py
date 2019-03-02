#! /usr/bin/env python

import xml.etree.ElementTree as ET
import sys
import re
import sqlite3

class DropEntry:
    def __init__(self, item, quantity, rarity, members_only):
        self._item = item
        self._quantity = quantity
        self._rarity = rarity
        self._members_only = members_only

    @property
    def item(self):
        return self._item

    @property
    def quantity(self):
        return self._quantity

    @property
    def rarity(self):
        return self._rarity

    @property
    def members_only(self):
        return self._members_only


class Monster:
    def __init__(self, name, drop_list, members_only, slayer_lvl, combat_lvls):
        self._drop_list = drop_list
        self._name = name
        self._members_only = members_only
        self._slayer_lvl = slayer_lvl
        self._combat_lvls = combat_lvls

    @property
    def name(self):
        return self._name

    @property
    def drop_list(self):
        return self._drop_list

    @property
    def members_only(self):
        return self._members_only

    @property
    def slayer_lvl(self):
        return self._slayer_lvl

    @property
    def combat_lvls(self):
        return self._combat_lvls



# Takes as input an XML file obtained from the Wiki export function
# and returns a tuple (item_names, monster_drops) where
# items_names is a list of all items in the drop table of any monster
# inlcuded in the export file and monster_drops is a dictionary mapping
# monster names to a list of items in their drop table. Items are
# 3-tuples (name, quantity, rarity)
def read_from_xml(xml_file):
    wiki_xml = ET.parse(wiki_data_file).getroot()
    xml_ns = { 'wiki_export': 'http://www.mediawiki.org/xml/export-0.10/' }

    item_names = set([])
    monsters = []

    members_pattern = re.compile(r".*\|\s*members\s*=\s*(yes|no).*", re.IGNORECASE)
    slayer_pattern = re.compile(r".*\|\s*slaylvl\d?\s*=\s*(\d+).*", re.IGNORECASE)
    combat_pattern = re.compile(r".*\|\s*combat\d?\s*=\s*(\d+).*", re.IGNORECASE)
    name_pattern = re.compile(r".*Name\s*=\s*(.*?)\s*[|}]")
    quantity_pattern = re.compile(r".*Quantity\s*=\s*(.*?)\s*[|}]")
    rarity_pattern = re.compile(r".*Rarity\s*=\s*(.*?)\s*[|}]")
    namenotes_pattern = re.compile(r".*Namenotes\s*=\s*{{\((.*?)\)}}\s*[|}]")

    for page in wiki_xml.findall('wiki_export:page', xml_ns):
        monster_name = page.find('wiki_export:title', xml_ns).text
        page_text = page.find('wiki_export:revision', xml_ns).find('wiki_export:text', xml_ns).text

        drop_list = []

        monster_members = False
        slayer_lvl = 1
        combat_lvls = []
        for line in page_text.split('\n'):
            members_match = members_pattern.match(line)
            if members_match:
                members = members_match.group(1).lower()
                monster_members = members == 'yes'

            slayer_match = slayer_pattern.match(line)
            if slayer_match:
                slayer_lvl = max(slayer_lvl, int(slayer_match.group(1)))

            combat_match = combat_pattern.match(line)
            if combat_match:
                combat_lvls.append(int(combat_match.group(1)))

            if "DropsLine" in line:
                name_match = name_pattern.match(line)
                quantity_match = quantity_pattern.match(line)
                rarity_match = rarity_pattern.match(line)
                if name_match is not None and quantity_match is not None and rarity_match is not None:
                    item_name = name_match.group(1)
                    item_quantity = quantity_match.group(1)
                    item_rarity = rarity_match.group(1)

                    if monster_members:
                        item_members = True
                    else:
                        namenotes_match = namenotes_pattern.match(line)
                        if namenotes_match is not None and namenotes_match.group(1).lower() == 'm':
                            item_members = True
                        else:
                            item_members = False

                    item_names.add(item_name)
                    drop_list.append(DropEntry(item_name, item_quantity, item_rarity, item_members))

        combat_lvls = list(set(combat_lvls))
        monsters.append(Monster(monster_name, drop_list, monster_members, slayer_lvl, combat_lvls))

    return (item_names, monsters)

def create_db_schema(conn):
    sql = '''
    CREATE TABLE monsters (
      monster_id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      members_only BOOLEAN NOT NULL CHECK (members_only IN (0, 1)),
      slayer_lvl INTEGER NOT NULL
    );

    CREATE TABLE monster_combat_lvls (
      monster_id INTEGER NOT NULL,
      combat_lvl INTEGER NOT NULL,

      FOREIGN KEY (monster_id) REFERENCES monsters(monster_id)
    );

    CREATE TABLE items (
      item_id INTEGER PRIMARY KEY AUTOINCREMENT, 
      name TEXT NOT NULL
    );

    CREATE TABLE monster_item_drops (
      monster_id INTEGER NOT NULL,
      item_id INTEGER NOT NULL,

      item_quantity TEXT NOT NULL,
      item_rarity TEXT NOT NULL,

      members_only BOOLEAN NOT NULL CHECK (members_only IN (0, 1)),

      FOREIGN KEY (monster_id) REFERENCES monsters(monster_id),
      FOREIGN KEY (item_id) REFERENCES items(item_id)
    );
    '''

    conn.executescript(sql)

def insert_items(conn, item_names):
    sql = '''
    INSERT INTO items (name) VALUES (?);
    '''
    for item in item_names:
        conn.execute(sql, (item,))

def insert_monsters(conn, monsters):
    sql_monster = '''
    INSERT INTO monsters (name, members_only, slayer_lvl) VALUES (?, ?, ?);
    '''

    sql_combat = '''
    INSERT INTO monster_combat_lvls (monster_id, combat_lvl) VALUES (?, ?);
    '''

    cur = conn.cursor()
    for m in monsters:
        cur.execute(sql_monster, (m.name, 1 if m.members_only else 0, m.slayer_lvl))
        monster_id = cur.lastrowid
        for c in m.combat_lvls:
            cur.execute(sql_combat, (monster_id, c))

def insert_drops(conn, monsters):
    sql = '''
    INSERT INTO monster_item_drops VALUES (
        (SELECT monster_id FROM monsters WHERE name = ?),
        (SELECT item_id FROM items WHERE name = ?),
        ?, ?, ?
    );
    '''

    for m in monsters:
        for drop in m.drop_list:
            conn.execute(sql, (m.name, drop.item, drop.quantity, drop.rarity, 1 if drop.members_only else 0))

def populate_db(conn, item_names, monsters):
    insert_items(conn, item_names)
    insert_monsters(conn, monsters)
    insert_drops(conn, monsters)

# Grab cmd line args
wiki_data_file = sys.argv[1]
db_file = sys.argv[2]

# Read from wiki xml file
(items, monsters) = read_from_xml(wiki_data_file)

# create db
conn = sqlite3.connect(db_file)
create_db_schema(conn)
populate_db(conn, items, monsters)
conn.commit()
conn.close()
