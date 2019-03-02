#! /usr/bin/env python

import sys
import sqlite3
import csv
import argparse

# Constructs and executes a database query on conn as specified by kwargs.
# kwargs roughly correspond to the command line arguments for this program.
# You may provide any number of the kwargs but, it generaly makes sense to
# provide either monster or item (unless you want a dump of the whole database).
# kwargs:
#  monster: find drops of this monster.
#  item: find monsters dropping this item.
#  f2p: find only free to play drops.
#  slayer_lvl: limit monsters to those killable below this level.
def query_database(conn, **kwargs):

    # default lists of columns and filters.
    # kwargs will determine how these are modified.
    result_columns = [
            'monsters.name AS monster',
            'items.name AS item',
            'GROUP_CONCAT(CAST(monster_combat_lvls.combat_lvl AS TEXT),\',\') AS combat_lvls',
            'monster_item_drops.item_rarity AS rarity',
            'monster_item_drops.item_quantity AS quantity'
    ]
    filters = []
    havings = []

    # Modify query as specified by kwargs
    if kwargs['monster']:
        filters.append('monsters.name LIKE :monster')

    if kwargs['item']:
        filters.append('items.name LIKE :item')

    if kwargs['f2p']:
        filters.append('NOT monster_item_drops.members_only')

    if kwargs['slayer_lvl']:
        filters.append('monster.slayer_lvl <= :slayer_lvl')

    if kwargs['combat_lvl']:
        havings.append('(monster_combat_lvls.combat_lvl IS NULL OR MAX(monster_combat_lvls.combat_lvl) <= :combat_lvl)')

    # Construct and execute the SQL query.
    sql = f'''
    SELECT {', '.join(result_columns)}
    FROM monster_item_drops
    INNER JOIN monsters ON 
        monsters.monster_id = monster_item_drops.monster_id
    INNER JOIN items ON
        items.item_id = monster_item_drops.item_id
    LEFT JOIN monster_combat_lvls ON
        monster_combat_lvls.monster_id = monsters.monster_id
    { 'WHERE' if filters else ''} {' AND '.join(filters)}
    GROUP BY monsters.monster_id, items.item_id
    { 'HAVING' if havings else ''} {' AND '.join(havings)}
    ORDER BY monster_item_drops.item_rarity
    '''

    return conn.execute(sql, kwargs)

# Write to outfile the result of the query contained in the cursor.
# The output is formated as a CSV using pythons csv writer at
# default settings.
def write_query_result(curr, outfile):
    query_writer = csv.writer(outfile)

    # write a header row using the field names from the query
    field_names = map(lambda t: t[0], curr.description)
    query_writer.writerow(field_names)

    # write a row for each record in the query
    query_writer.writerows(curr.fetchall())

# Print the result of a query in a format suitable for a ItemDropTable on
# OSRS wiki.
def write_item_drops_lines(curr, outfile):
    field_names = list(map(lambda t: t[0], curr.description))
    monster = field_names.index('monster')
    combat = field_names.index('combat_lvls')
    quantity = field_names.index('quantity')
    rarity = field_names.index('rarity')

    print('==Dropping monsters==\n{{ItemDropsTableHead}}', file=outfile)
    for row in curr.fetchall():
        print(f'{{{{ItemDropsLine|Monster={row[monster]}|Combat={row[combat] if row[combat] else "N/A"}|Quantity={row[quantity]}|Rarity={row[rarity]}}}}}', file=outfile)


# Handle command line arguments using pythons ArgumentParser class
def get_arguments():
    #standard ArgumentParser setup
    parser = argparse.ArgumentParser(description='Query the OSRS loot database.')
    parser.add_argument('--monster', '-m', help='Search for items dropped by a monster.')
    parser.add_argument('--item', '-i', help='Search for monsters dropping an item.')
    parser.add_argument('--f2p', '-f', action='store_true', help='Restrict results to those available to free players.')
    parser.add_argument('--slayer-lvl', '-s', type=int, help='Restrict results to those available at a slayer level.')
    parser.add_argument('--combat-lvl', '-c', type=int, help='Restrict results to those below a combat level.')
    parser.add_argument('--database', '-d', help='Specify an alternate database file. (default loot_database.db)')
    parser.add_argument('--item-drops-line', action='store_true', help='Format output as OSRS Wiki ItemDropsLine template.')

    args = parser.parse_args()

    return args

args = get_arguments()

database = args.database if args.database else 'loot_database.db'
conn = sqlite3.connect(database)

curr = query_database(conn, **vars(args));


if args.item_drops_line:
    write_item_drops_lines(curr, sys.stdout)
else:
    write_query_result(curr, sys.stdout)

conn.commit()
conn.close()
