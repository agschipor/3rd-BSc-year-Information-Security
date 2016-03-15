import random as rand
import socket
import json
import traceback
import sys
import os
import time
import getpass
from crypto import AESCipher, DES3Cipher



HOST = "localhost"
PORT = 21212

ERR_SUCCESS = 'success'
ERR_SERVER_CONNECTION_FAILED = 'connection to server failed'
ERR_USER_NOT_EXISTS = 'this user doesn\'t exists'
ERR_USER_ALREADY_EXISTS = 'this user already exists'
ERR_DB_OPERATION_FAILED = 'db operation failed'
ERR_INVALID_COMBINATION = 'invalid user/password combination'
ERR_SOCK = 'socket error'
ERR_NO_AVAILABLE_SERVICES = 'no available services'
ERR_FILE= 'file error'
ERR_INVALID_SESSION = 'invalid session'
ERR_INVALID_SERVER_DATA = 'invalid server data/the data has been modified - FORBIDDEN'
ERR_INVALID_SESSION_KEY = 'invalid session key'
ERR_INVALID_DATA = 'invalid data found'
ERR_FORBIDDEN = 'forbidden'


COMM_CREATE = 'create'
COMM_EXIT = 'exit'
COMM_GET_KEY = 'get_key'
COMM_GET_SERVICES = 'get_services'
COMM_ACCESS_SERVICE = 'access_service'

OPTION_CREATE = 1
OPTION_ACCESS_SERVICE = 2
OPTION_EXIT = 3


MAIN_MENU = 'main_menu'
MENU_OPT = ['1', '2', '3']

ACCESS_RIGHT_OPT = ['r', 'w', 'rw']


def get_key(username):
    try:
        fd = open('keys', 'r')

        keys = json.load(fd)

        fd.close()
    except:
        print traceback.format_exc()
        return {'err': ERR_FILE}

    return keys[username]


def get_services(sock):
    sock.sendall(COMM_GET_SERVICES)
    services = json.loads(sock.recv(2048))

    if len(services) == 0:
        print "no services to start"
        return {'err': ERR_NO_AVAILABLE_SERVICES }

    return {'services': services}


def connect_to_socket(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))      
    except:
        sock.close()
        return {'err': ERR_SERVER_CONNECTION_FAILED}

    return {'sock': sock}


def get_service_to_access(services):
    services_no = len(services)

    counter = 0
    print '---------------------------'
    for service in services:
        print '%d. %s - %d' % (counter, service['name'], service['port'])
        counter += 1
    service = raw_input('\nService: ')
    print '---------------------------'
    while not service.isdigit() or (int(service) >= services_no or int(service) < 0):
        counter = 0
        print '---------------------------'
        for service in services:
            print '%d. %s - %d' % (counter, service['name'], service['port'])
            counter += 1
        service = raw_input('\nService: ')
        print '---------------------------'

    return int(service)


def access_service(sock):

    user_data = {}
    user_data['user'] = {}
    user_data['user']['username'] = raw_input('Username: ')


    services = get_services(sock)

    if 'err' in services:
        return services

    services = services['services']

    service_to_access = get_service_to_access(services)
    
    user_data['nonce'] = rand.random()
    user_data['service'] = service = services[service_to_access]
    user_data['user']['password'] = getpass.getpass()
    user_data['right'] = raw_input('Access right(r/w/rw): ')
    while user_data['right'] not in ACCESS_RIGHT_OPT:
        user_data['right'] = raw_input('Access right(r/w/rw): ')

    sock.sendall(COMM_ACCESS_SERVICE)
    sock.sendall(json.dumps(user_data))
    response = json.loads(sock.recv(1024))

    if 'err' in response:
        return response

    user_key = get_key(user_data['user']['username']).decode('hex')
    print 'kut: %s' % user_key
    aes_cipher = AESCipher(user_key)
    
    print 'response from server: %s' % str(response)
    user_response = json.loads(aes_cipher.decrypt_data(response['for_user'].decode('hex')))
    print 'decrypted response from server, for user: %s' % str(user_response)
    print 'k: %s' % user_response['key'].decode('hex')

    if user_response['nonce'] != user_data['nonce']:
        return {'err': ERR_INVALID_SESSION}

    if user_response['service'] != user_data['service']:
        return {'err': ERR_INVALID_SESSION}        

    des3_cipher = DES3Cipher(user_response['key'].decode('hex'))

    service_socket = connect_to_socket(HOST, service['port'])

    if 'err' in service_socket:
        return service_socket

    service_socket = service_socket['sock']

    timestamp = int(time.time())
    service_response = {}
    service_response['from_user'] = {}
    service_response['from_user']['user'] = user_data['user']
    service_response['from_user']['timestamp'] = timestamp
    service_response['from_user']['lifetime'] = user_response['lifetime']
    service_response['from_user'] = des3_cipher.encrypt_data(json.dumps(service_response['from_user'])).encode('hex')
    service_response['from_service'] = response['for_service']

    print 'send service respons: %s' % str(service_response)

    service_socket.sendall(COMM_ACCESS_SERVICE)
    service_socket.sendall(json.dumps(service_response))

    response = json.loads(service_socket.recv(1024))

    if 'err' in response:
        service_socket.close()
        return response

    print 'response from service: %s' % str(response)
    response = json.loads(des3_cipher.decrypt_data(response['for_user'].decode('hex')))
    print 'decrypted response from service: %s' % str(response)

    if response['timestamp'] != timestamp:
        return {'err': ERR_INVALID_SESSION}

    if response['lifetime'] != user_response['lifetime'] - 1:
        return {'err': ERR_FORBIDDEN}

    service_socket.sendall(COMM_EXIT)

    service_socket.close()

    return ERR_SUCCESS


def create_user(sock):
    user = {}
    user['username'] = raw_input('Username: ')
    user['password'] = getpass.getpass()
    user['security_level'] = rand.randrange(5)

    sock.sendall(COMM_CREATE)
    sock.sendall(json.dumps(user))
    response = json.loads(sock.recv(1024))

    if 'err' in response:
        return response

    try:
        fd = open('keys', 'r+')
        
        keys = json.load(fd)
        if user['username'] not in keys:
            keys[user['username']] = response['key']

        fd.seek(0)
        fd.write(json.dumps(keys))

        fd.close()
    except:
        print traceback.format_exc()
        return {'err': ERR_FILE}

    return ERR_SUCCESS


def get_menu_option(menu_type):
    print '\n---------------------------'
    print '1. Create user'
    print '2. Access service'
    print '3. Exit'
    option = raw_input('Option: ')
    print '---------------------------'
    return option


def get_option(menu_type):
    option = get_menu_option(menu_type)
    while option not in MENU_OPT or not option.isdigit():
        print option not in MENU_OPT, not option.isdigit()
        print "_________ no such option _________"
        option = get_menu_option(menu_type)

    option = int(option)

    return option


def print_error(reason):
    print '---------------------------------------------------'
    print 'Failed! Reason: %s' % reason
    print '---------------------------------------------------'


if __name__ == "__main__":
    sock = connect_to_socket(HOST, PORT)
    is_authentificated = False

    if 'err' in sock:
        print_error(sock['err'])
        sys.exit()

    sock = sock['sock']

    try:
        if not os.path.exists('keys'):
            fd = open('keys', 'wt')
            fd.write('{}')
            fd.close()
    except:
        print_error(ERR_FILE)
        sys.exit()

    while 1:
        option = get_option(MAIN_MENU)
    
        if option == OPTION_EXIT:
            sock.sendall(COMM_EXIT)
            break
        elif option == OPTION_ACCESS_SERVICE:
            return_value = access_service(sock)
            if 'err' in return_value:
                print_error(return_value['err'])
                continue
            print 'authentificated'
        elif option == OPTION_CREATE:
            return_value = create_user(sock)
            if return_value != ERR_SUCCESS:
                print_error(return_value['err'])
                continue
                
    sock.close()