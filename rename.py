import re
import os
import io
import sys
import os.path as op
import argparse
import codecs
from glob import glob
import qbittorrentapi
from pathlib2 import Path
import requests

log_name=op.join(op.dirname(op.realpath(__file__)), 'log.txt')

# Episode Regular Expression Matching Rules
episode_rules = [r'(.*)\[(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)',
                 r'(.*)\[E(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)',
                 r'(.*)\[第(\d*\.*\d*)话(?:END)?\](.*)',
                 r'(.*)\[第(\d*\.*\d*)話(?:END)?\](.*)',
                 r'(.*)第(\d*\.*\d*)话(?:END)?(.*)',
                 r'(.*)第(\d*\.*\d*)話(?:END)?(.*)',
                 r'(.*)- (\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)? (.*)']
# Suffixs of files we are going to rename
suffixs = ['mp4', 'mkv', 'avi', 'mov', 'flv', 'rmvb', 'ass', 'idx']
sys.stdout = io.TextIOWrapper(buffer=sys.stdout.buffer,encoding='utf8')

# Parse the input arguments. You can whether input only root, or only path, or both root and name.
parser = argparse.ArgumentParser(description='Regular Expression Match')
parser.add_argument('--root', default='',
                    help='The root directory of the input file.')
parser.add_argument('--name', default='',
                    help='The file name of the input file.')
parser.add_argument('--path', default='',
                    help='The file full path of the input file.')
parser.add_argument('--hash', default='',
                    help='The torrent Hash value.')


def rename(root, name, hash):
    root = Path(root)

    for rule in episode_rules:
        matchObj = re.match(rule, name, re.I)
        if matchObj is not None:
            new_name = f'{matchObj.group(1)} E{matchObj.group(2)} {matchObj.group(3)}'
            # print(matchObj.group())
            # print(new_name)
            print(f'{name} -> {new_name}')
            with codecs.open(log_name, 'a+', 'utf-8') as f:
                # f.writelines(f'{name} -> {new_name}')
                print(f'{name} -> {new_name}', file=f)

            qb_rename(hash, str(name), str(new_name))
#            os.rename(str(root/name), str(root/new_name))
            #general_check(root, new_name)
            return
    #general_check(root, name)


def general_check(root, name):
    new_name = ' '.join(name.split())
    if new_name != name:
        print(f'{name} -> {new_name}')
        with codecs.open(log_name, 'a+', 'utf-8') as f:
            print(f'{name} -> {new_name}', file=f)
        os.rename(str(root/name), str(root/new_name))


def qb_rename(hash, old_path, new_path):
    qbt_client = qbittorrentapi.Client(host='192.168.31.10:8181', username='admin', password='adminadmin')
    try:
        qbt_client.auth_log_in()
    except qbittorrentapi.LoginFailed as e:
        print(e)
    qbt_client.torrents_rename_file(torrent_hash=hash, old_path=old_path, new_path=new_path)


if __name__ == "__main__":
    args = parser.parse_args()
    if op.isdir(args.path):
        args.root = args.path
        args.path = ''

    if args.name != '' and args.root != '':
        temp = str(args.root/args.name)
        if op.isdir(temp):
            args.root = temp
            args.name = ''

    if args.path != '':
        root, name = op.split(args.path)
        rename(root, name, args.hash)
    elif args.name != '' and args.root != '':
        rename(args.root, args.name, args.hash)
    elif args.root != '':
        files = []
        for suffix in suffixs:
            files.extend(Path(args.root).rglob('*.'+suffix))
            files.extend(Path(args.root).rglob('*.'+suffix.upper()))
        print(f'Total Files Number: {len(files)}')
        for path in files:
            root, name = op.split(path)
            rename(root, name, args.hash)
    else:
        print('Please input whether only root, or only path, or both root and name')
    # os.system('PAUSE')
    # for rule in episode_rules:
    #     matchObj = re.match(rule, name, re.I)
    #     if matchObj is not None:
    #         new_name = f'{matchObj.group(1)} E{matchObj.group(2)} {matchObj.group(3)}'
    #         # print(matchObj.group())
    #         # print(new_name)
    #         print(f'{name} -> {new_name}')
    #         with open(r'C:\Users\miracleyoo\Documents\Program\utorrent\log.txt', 'a+') as f:
    #             print(f'{name} -> {new_name}', file=f)

    #         os.rename(str(root/name), str(root/new_name))
    #         break