import paramiko
import xml.etree.ElementTree as ET
import typing
import stat
import re
from io import BytesIO
from netex import Netex
from zipfile import ZipFile
import gzip
import os
from datetime import datetime

def getNetexNL(secrets: dict={}, whitelist: list=None, options=None):
    if 'NL_username' not in secrets or 'NL_password' not in secrets:
        return
    
    host = "data.ndovloket.nl"
    port = 22
    username = secrets['NL_username']
    password = secrets['NL_password']

    latest_files = {}

    with paramiko.SSHClient() as client:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, port, username, password)

        with client.open_sftp() as sftp:
            for name in sftp.listdir('netex'):
                netex_folder = f'netex/{name}'
                if stat.S_ISDIR(sftp.stat(netex_folder).st_mode):

                    netex_type = 'data'
                    if name == 'test': continue
                    if name == 'enum': netex_type = 'enum'
                    if name == 'epiap': netex_type = 'enum'

                    netex_files = sftp.listdir_attr(netex_folder)
                    netex_files.sort(key = lambda f: f.st_mtime, reverse=True)

                    latest_predated_file = None

                    for f in netex_files:
                        netex_file = f'{netex_folder}/{f.filename}'

                        if stat.S_ISDIR(sftp.stat(netex_file).st_mode):
                            continue

                        if netex_type == 'data' and whitelist and not any(x in f.filename for x in whitelist):
                            continue

                        file_topic = ''

                        if not '_' in f.filename:
                            continue
                            # name_parts = re.split(r'_|-|\.', f.filename)

                        name_parts = re.split(r'_|\.', f.filename)

                        # No Netex delivery from the future
                        if len(name_parts) > 5:
                            # print(name_parts[4])
                            if re.fullmatch(r'\d{8}', name_parts[4]):
                                valid_from = datetime.strptime(name_parts[4], '%Y%m%d')
                                if valid_from > datetime.now():
                                    latest_predated_file = (file_topic, netex_file)
                                    continue
                            if re.fullmatch(r'\d{4}-\d{2}-\d{2}', name_parts[4]):
                                valid_from = datetime.strptime(name_parts[4], '%Y-%m-%d')
                                if valid_from > datetime.now():
                                    latest_predated_file = (file_topic, netex_file)
                                    continue

                        for name_part in name_parts:
                            if re.match('[a-zA-Z]', name_part):
                                file_topic += name_part

                        latest_files.setdefault(file_topic, netex_file)

                    if not file_topic in latest_files and latest_predated_file is not None:
                        latest_files.setdefault(latest_predated_file[0], latest_predated_file[1])


            for file in latest_files.values():
                print(f'Verwerken van {file}')
                io = BytesIO()
                sftp.getfo(file, io)
                io.seek(0)

                split_path = os.path.splitext(file)

                if split_path[1] == '.gz':
                    gzip_file = gzip.open(io, 'r')
                    content = gzip_file.read()
                    netex = Netex(str_content=content, options=options)
        


    