import random as rand
import socket
import json
import sys
import time
import SocketServer
import traceback
import os
from crypto import AESCipher, DES3Cipher



SERVER_HOST = "localhost"
SERVER_PORT = 21213

HOST = "localhost"

ERR_SUCCESS = 'success'
ERR_SERVER_CONNECTION_FAILED = 'connection to server failed'
ERR_SERVICE_ALREADY_EXISTS = 'this service already exists'
ERR_DB_OPERATION_FAILED = 'db operation failed'
ERR_INVALID_COMBINATION = 'invalid user/password combination'
ERR_SOCK = 'socket error'
ERR_FILE= 'file error'
ERR_INVALID_SERVER_DATA = 'invalid server data/the data has been modified - FORBIDDEN'
ERR_INVALID_SESSION_KEY = 'invalid session key'
ERR_INVALID_DATA = 'invalid data found'
ERR_PORT_ALREADY_EXISTS = 'this port is already used by another service'

COMM_CREATE = 'create'
COMM_START_SERVICE = 'start_service'
COMM_SERVICE_STARTED = 'service_started'
COMM_SERVICE_STOPPED = 'services_stopped'
COMM_ACCESS_SERVICE = 'access_service'
COMM_EXIT = 'exit'

OPTION_CREATE = 1
OPTION_START_SERVICE = 2
OPTION_EXIT = 3


MAIN_MENU = 'main_menu'
MENU_OPT = ['1', '2', '3']

STARTED_SERVICE_NAME = ''

class UserTCPConnectionHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        global STARTED_SERVICE_NAME
        while 1:
            try:
                command = self.request.recv(1024)  
            except:
                break
            
            if command == COMM_ACCESS_SERVICE:
                try:
                    data = json.loads(self.request.recv(1024))
                except:
                    break
                aes_cipher = AESCipher(get_key(STARTED_SERVICE_NAME).decode('hex'))
                print 'encrypted data: %s' % str(data)
                try:
                    from_server = json.loads(aes_cipher.decrypt_data(data['from_service'].decode('hex')))
                    print 'data from server: %s' % str(from_server)
                except:
                    print ERR_INVALID_SERVER_DATA
                    self.request.sendall(json.dumps({'err': ERR_INVALID_SERVER_DATA}))
                    break

                des3_cipher = DES3Cipher(from_server['key'].decode('hex'))

                try:
                    from_user = json.loads(des3_cipher.decrypt_data(data['from_user'].decode('hex')))
                    print 'data from user: %s' % str(from_user)
                except:
                    print ERR_INVALID_SESSION_KEY
                    self.request.sendall(json.dumps({'err': ERR_INVALID_SESSION_KEY}))
                    break


                try:
                    if from_user['user']['username'] != from_server['user']['username']:
                        print ERR_INVALID_DATA
                        self.request.sendall(json.dumps({'err': ERR_INVALID_DATA}))
                        break

                    if from_user['user']['password'] != from_server['user']['password']:
                        print ERR_INVALID_DATA
                        self.request.sendall(json.dumps({'err': ERR_INVALID_DATA}))
                        break
                    print 'passed identidy check'

                    if from_user['lifetime'] != from_server['lifetime']:
                        print ERR_INVALID_DATA
                        self.request.sendall(json.dumps({'err': ERR_INVALID_DATA}))
                        break
                    print 'passed lifetime check'

                    if int(time.time()) > from_server['lifetime']:
                        print ERR_INVALID_DATA
                        self.request.sendall(json.dumps({'err': ERR_INVALID_DATA}))
                        break
                    print 'passed key lifetime check'

                    if from_user['timestamp'] > from_server['lifetime']:
                        print ERR_INVALID_DATA
                        self.request.sendall(json.dumps({'err': ERR_INVALID_DATA}))
                        break
                    print 'passed timestamp validation'
                except:
                    print ERR_INVALID_DATA
                    self.request.sendall(json.dumps({'err': ERR_INVALID_DATA}))
                    break

                response = {}
                response['lifetime'] = from_server['lifetime'] - 1
                response['timestamp'] = from_user['timestamp']

                response = des3_cipher.encrypt_data(json.dumps(response)).encode('hex')
                self.request.sendall(json.dumps({'for_user': response}))

            elif command == COMM_EXIT:
                break

        self.request.close()


class Server(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass):
        SocketServer.TCPServer.__init__(\
        self,\
        server_address,\
        RequestHandlerClass)


def get_key(name):
    try:
        fd = open('skeys', 'r')

        keys = json.load(fd)

        fd.close()
    except:
        print traceback.format_exc()
        return {'err': ERR_FILE}

    return keys[name]


def start_service(sock):
    global STARTED_SERVICE_NAME

    sock.sendall(COMM_START_SERVICE)
    services = json.loads(sock.recv(2048))

    if services == ERR_DB_OPERATION_FAILED:
        return ERR_DB_OPERATION_FAILED
    elif len(services) == 0:
        print "no services to start"
        return ERR_SUCCESS

    service_to_start = get_service_to_start(services)

    service_server = Server((HOST, services[service_to_start]['port']), UserTCPConnectionHandler)

    try:
        print "< started service \'%s\' at port %d >" % (services[service_to_start]['name'], services[service_to_start]['port'])
        sock.sendall(COMM_SERVICE_STARTED)
        sock.sendall(json.dumps(services[service_to_start]))
        STARTED_SERVICE_NAME = services[service_to_start]['name']
        service_server.serve_forever()
    except KeyboardInterrupt:
        sock.sendall(COMM_SERVICE_STOPPED)
        sock.sendall(json.dumps(services[service_to_start]))
        return ERR_SUCCESS


def get_service_to_start(services):
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


def connect_to_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((SERVER_HOST, SERVER_PORT))      
    except:
        sock.close()
        return {'err': ERR_SERVER_CONNECTION_FAILED}

    return {'sock': sock}


def create_service(sock):
    service = {}
    service['name'] = raw_input('Name: ')
    service['port'] = raw_input('Port: ')
    while service['port'].isdigit() == False:
        service['port'] = raw_input('Port: ')
    service['port'] = int(service['port']) 
    service['security_level'] = rand.randrange(5)

    sock.sendall(COMM_CREATE)
    sock.sendall(json.dumps(service))
    response = json.loads(sock.recv(1024))

    if 'err' in response:
        return response

    try:
        fd = open('skeys', 'r+')
        
        keys = json.load(fd)
        if service['name'] not in keys:
            keys[service['name']] = response['key']

        fd.seek(0)
        fd.write(json.dumps(keys))

        fd.close()
    except:
        print traceback.format_exc()
        return {'err': ERR_FILE}

    return ERR_SUCCESS


def get_menu_option(menu_type):
    print '\n---------------------------'
    if menu_type == MAIN_MENU:
        print '1. Create service'
        print '2. Start service'
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
    sock = connect_to_socket()

    if 'err' in sock:
        print_error(sock['err'])
        sys.exit()

    sock = sock['sock']

    try:
        if not os.path.exists('skeys'):
            fd = open('skeys', 'wt')
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
        elif option == OPTION_START_SERVICE:
            return_value = start_service(sock)
            if return_value == ERR_DB_OPERATION_FAILED:
                print_error(return_value)
                continue
        elif option == OPTION_CREATE:
            return_value = create_service(sock)
            if 'err' in return_value:
                print_error(return_value['err'])
                continue
                
    sock.close()