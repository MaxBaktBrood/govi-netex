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
from epiap import Epiap

def getNetexNL(secrets: dict={}, whitelist: list=None):
    if 'NL_username' not in secrets or 'NL_password' not in secrets:
        return
    
    host = "data.ndovloket.nl"
    port = 22
    username = secrets['NL_username']
    password = secrets['NL_password']

    latest_data_files = {}
    latest_enum_files = {}
    latest_epiap_files = {}

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
                    if name == 'epiap': netex_type = 'epiap'

                    netex_files = sftp.listdir_attr(netex_folder)
                    netex_files.sort(key = lambda f: f.st_mtime, reverse=True)

                    for f in netex_files:
                        netex_file = f'{netex_folder}/{f.filename}'

                        if stat.S_ISDIR(sftp.stat(netex_file).st_mode):
                            continue

                        if netex_type == 'data' and whitelist and not any(x in f.filename for x in whitelist):
                            continue

                        file_topic = ''

                        for name_part in re.split(r'_|-|\.', f.filename):
                            if re.match('[a-zA-Z]', name_part):
                                file_topic += name_part

                        if netex_type == 'data':
                            latest_data_files.setdefault(file_topic, netex_file)
                        if netex_type == 'enum':
                            latest_enum_files.setdefault(file_topic, netex_file)
                        if netex_type == 'epiap':
                            latest_epiap_files.setdefault(file_topic, netex_file)

            epiap_list = []

            for file in latest_epiap_files.values():
                print(f'Verwerken van {file}')
                io = BytesIO()
                sftp.getfo(file, io)
                io.seek(0)

                split_path = os.path.splitext(file)

                if split_path[1] == '.gz':
                    gzip_file = gzip.open(io, 'r')
                    content = gzip_file.read().decode(encoding='utf-8')
                    epiap_list.append(content)

            epiap_list = list(map(lambda x: Epiap(str_content=x), epiap_list))

            enum_list = []

            for file in latest_enum_files.values():
                print(f'Verwerken van {file}')
                io = BytesIO()
                sftp.getfo(file, io)
                io.seek(0)

                split_path = os.path.splitext(file)

                if split_path[1] == '.gz':
                    gzip_file = gzip.open(io, 'r')
                    content = gzip_file.read()
                    enum_list.append(content)


            for file in latest_data_files.values():
                print(f'Verwerken van {file}')
                io = BytesIO()
                sftp.getfo(file, io)
                io.seek(0)

                split_path = os.path.splitext(file)

                if split_path[1] == '.gz':
                    gzip_file = gzip.open(io, 'r')
                    content = gzip_file.read()
                    netex = Netex(str_content=content, epiap_list=epiap_list, enum_list=enum_list)
        


    