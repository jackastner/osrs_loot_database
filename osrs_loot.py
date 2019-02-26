#! /usr/bin/env python

import sys
import sqlite3
import csv
import argparse

def query_database(conn, **kwargs):
    result_columns = ['items.name', 'monsters.name', 'monster_item_drops.item_rarity', 'monster_item_drops.item_quantity']
    filters = []

    if kwargs['monster']:
        result_columns.remove('monsters.name')
        filters.append('monsters.name LIKE :monster')

    if kwargs['item']:
        result_columns.remove('items.name')
        filters.append('items.name LIKE :item')

    if kwargs['f2p']:
        filters.append('NOT monster_item_drops.members_only')

    if kwargs['slayer_lvl']:
        filters.append('monster.slayer_lvl <= :slayer_lvl')

    sql = f'''
    SELECT {', '.join(result_columns)}
    FROM monster_item_drops
    INNER JOIN monsters ON 
        monsters.monster_id = monster_item_drops.monster_id
    INNER JOIN items ON
        items.item_id = monster_item_drops.item_id
    { 'WHERE' if filters else ''} {' AND '.join(filters)}
    ORDER BY monster_item_drops.item_rarity
    '''

    return conn.execute(sql, kwargs)

def write_query_result(curr, outfile):
    query_writer = csv.writer(outfile)

    field_names = map(lambda t: t[0], curr.description)
    query_writer.writerow(field_names)

    query_writer.writerows(curr.fetchall())


def get_arguments():
    monster_or_item_warning = 'You must specifify either --monster OR --item.'
    parser = argparse.ArgumentParser(description='Query the OSRS loot database.', epilog=monster_or_item_warning)
    parser.add_argument('--monster', '-m', help='Search for items dropped by a monster.')
    parser.add_argument('--item', '-i', help='Search for monsters dropping an item.')
    parser.add_argument('--f2p', '-f', action='store_true', help='Restrict results to those available to free players.')
    parser.add_argument('--slayer-lvl', '-s', type=int, help='Restrict results to those available at a slayer level.')
    parser.add_argument('--database', '-d', help='Specify an alternate database file.')

    args = parser.parse_args()

    if not (args.monster or args.item):
        parser.error(monster_or_item_warning)

    return args

args = get_arguments()

database = args.database if args.database else 'loot_database.db'
conn = sqlite3.connect(database)

curr = query_database(conn, **vars(args));
write_query_result(curr, sys.stdout)

conn.commit()
conn.close()
