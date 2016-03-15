import SocketServer
import sys
import db
import os
import hashlib
import json
import threading
import log
import random as rand
import time
from crypto import AESCipher


HOST = 'localhost'
USER_PORT = 21212
SERVICE_PORT = 21213
DB_CREDENTIALS = "host = '127.0.0.1' dbname = 'postgres' user = 'postgres' password = 'sec'"


COMM_CREATE = 'create'
COMM_EXIT = 'exit'
COMM_GET_KEY = 'get_key'
COMM_START_SERVICE = 'start_service'
COMM_SERVICE_STARTED = 'service_started'
COMM_SERVICE_STOPPED = 'services_stopped'
COMM_GET_SERVICES = 'get_services'
COMM_ACCESS_SERVICE = 'access_service'


ERR_USER_NOT_EXISTS = 'this user doesn\'t exists'
ERR_USER_ALREADY_EXISTS = 'this user already exists'
ERR_DB_OPERATION_FAILED = 'db operation failed'
ERR_INVALID_COMBINATION = 'invalid user/password combination'
ERR_SUCCESS = 'success'
ERR_SERVICE_ALREADY_EXISTS = 'this service already exists'
ERR_FORBIDDEN = 'forbidden'
ERR_PORT_ALREADY_EXISTS = 'this port is already used by another service'

STARTED_SERVICES = []


def calculate_md5(data):
    md5 = hashlib.md5()
    md5.update(data)
    hashcode = md5.hexdigest()

    return hashcode


class UserTCPConnectionHandler(SocketServer.BaseRequestHandler):
    isdb = db.InformationSecurityDB(DB_CREDENTIALS)
    def handle(self):
        global STARTED_SERVICES
        while 1:
            try:
                command = self.request.recv(1024)  
            except:
                break
            if command == COMM_CREATE:
                try:
                    user = self.request.recv(1024)
                except:
                    break
                user = json.loads(user)
                key = os.urandom(24).encode('hex')
                fake_test = self.isdb.get_user_key(user['username'])

                if fake_test == None:
                    log.info(db.get_last_error())        
                    self.request.sendall(json.dumps({'err': ERR_DB_OPERATION_FAILED}))
                    continue

                if len(fake_test) != 0:
                    log.info('user already exists: %s' % user['username'])
                    self.request.sendall(json.dumps({'err': ERR_USER_ALREADY_EXISTS}))
                    continue
                
                if isdb.insert_user(user['username'], calculate_md5(user['password']), user['security_level'], key) == False:
                    log.info(db.get_last_error())        
                    self.request.sendall(json.dumps({'err': ERR_DB_OPERATION_FAILED}))
                    continue

                services = isdb.get_all_services()

                if services == None:
                    log.info(db.get_last_error())        
                    self.request.sendall(json.dumps({'err': ERR_DB_OPERATION_FAILED}))
                    continue

                control_access_matrix = isdb.get_control_access_matrix()

                if control_access_matrix == None:
                    log.info(db.get_last_error())        
                    self.request.sendall(json.dumps({'err': ERR_DB_OPERATION_FAILED}))
                    continue            
                    
                control_access_matrix = json.loads(control_access_matrix[0]['matrix'])

                for service in services:
                    if user['security_level'] == service['security_level']:
                        val = rand.randrange(4)

                        if val == 0:
                            control_access_matrix['%s_%s' % (user['username'], service['name'])] = 'na'
                        elif val == 1:
                            control_access_matrix['%s_%s' % (user['username'], service['name'])] = 'r'
                        elif val == 2:
                            control_access_matrix['%s_%s' % (user['username'], service['name'])] = 'w'
                        else:
                            control_access_matrix['%s_%s' % (user['username'], service['name'])] = 'rw'


                if isdb.update_control_access_matrix(json.dumps(control_access_matrix)) == False:
                    log.info(db.get_last_error())        
                    self.request.sendall(json.dumps({'err': ERR_DB_OPERATION_FAILED}))
                    continue

                self.request.sendall(json.dumps({'key': key}))

            elif command == COMM_GET_SERVICES:
                self.request.sendall(json.dumps(STARTED_SERVICES))

            elif command == COMM_ACCESS_SERVICE:
                user_data = json.loads(self.request.recv(1024))
                database_user = isdb.get_user(user_data['user']['username'])

                if database_user == None:
                    log.info(db.get_last_error())
                    self.request.sendall(json.dumps({'err': ERR_INVALID_COMBINATION}))
                    continue

                if len(database_user) == 0:
                    self.request.sendall(json.dumps({'err': ERR_USER_NOT_EXISTS}))
                    continue

                service = isdb.get_service(user_data['service']['name'])

                if service == None:
                    log.info(db.get_last_error())
                    self.request.sendall(json.dumps({'err': ERR_INVALID_COMBINATION}))
                    continue               
                    
                service = service[0] 

                database_user = database_user[0]
                password = database_user['password'].replace('-', '')

                print 'user key: %s' % database_user['key'].decode('hex')
                user_aes_cipher = AESCipher(database_user['key'].decode('hex'))
                service_aes_cipher = AESCipher(service['key'].decode('hex'))

                if calculate_md5(user_data['user']['password']) != password:
                    self.request.sendall(json.dumps({'err': ERR_INVALID_COMBINATION}))
                    continue

                control_access_matrix = isdb.get_control_access_matrix()

                if control_access_matrix == None:
                    log.info(db.get_last_error())        
                    self.request.sendall(json.dumps({'err': ERR_DB_OPERATION_FAILED}))
                    continue        

                control_access_matrix = json.loads(control_access_matrix[0]['matrix'])

                has_right = False
                matrix_key = '%s_%s' % (user_data['user']['username'], service['name'])
                if matrix_key not in control_access_matrix:
                    if database_user['security_level'] > service['security_level']:
                        if user_data['right'] == 'r':
                            has_right = True
                    elif database_user['security_level'] < service['security_level']:
                        if user_data['right'] == 'w':
                            has_right = True
                elif user_data['right'] in control_access_matrix[matrix_key]:
                    has_right = True

                response = {}
                if has_right == True:
                    des_key1 = os.urandom(8)
                    des_key2 = os.urandom(8)
                    tdes_key = (des_key1 + des_key2).encode('hex')
                    print 'k: %s' % tdes_key
                    tdes_key_lifetime = int(time.time()) + 2 * 60 * 60
                    response['for_user'] = {}
                    response['for_service'] = {}
                    response_for_user = {}
                    response_for_user['key'] = tdes_key
                    response_for_user['nonce'] = user_data['nonce']
                    response_for_user['service'] = user_data['service']
                    response_for_user['lifetime'] = tdes_key_lifetime
                    response['for_user'] = user_aes_cipher.encrypt_data(json.dumps(response_for_user)).encode('hex')
                    response_for_service = {}
                    response_for_service['key'] = tdes_key
                    user = {}
                    user['username'] = user_data['user']['username']
                    user['password'] = user_data['user']['password']
                    response_for_service['user'] = user
                    response_for_service['lifetime'] = tdes_key_lifetime
                    response['for_service'] = service_aes_cipher.encrypt_data(json.dumps(response_for_service)).encode('hex')
                else:
                    response = {'err': ERR_FORBIDDEN}

                self.request.sendall(json.dumps(response))

            elif command == COMM_EXIT:
                break

        self.request.close()


class ServiceTCPConnectionHandler(SocketServer.BaseRequestHandler):
    isdb = db.InformationSecurityDB(DB_CREDENTIALS)
    def handle(self):
        while 1:
            global STARTED_SERVICES
            try:
                command = self.request.recv(1024)  
            except:
                break
            if command == COMM_CREATE:
                try:
                    service = json.loads(self.request.recv(1024))
                except:
                    break
                key = os.urandom(24).encode('hex')
                fake_name_test = self.isdb.get_service(service['name'])

                if fake_name_test == None:
                    log.info(db.get_last_error())        
                    self.request.sendall(json.dumps({'err': ERR_DB_OPERATION_FAILED}))
                    continue

                if len(fake_name_test) != 0:
                    log.info('service already exists: %s' % service['name'])
                    self.request.sendall(json.dumps({'err': ERR_SERVICE_ALREADY_EXISTS}))
                    continue

                fake_port_test = self.isdb.get_service_with_port(service['port'])

                if fake_port_test == None:
                    log.info(db.get_last_error())        
                    self.request.sendall(json.dumps({'err': ERR_DB_OPERATION_FAILED}))
                    continue

                if len(fake_port_test) != 0:
                    log.info('port already exists: %s' % service['name'])
                    self.request.sendall(json.dumps({'err': ERR_PORT_ALREADY_EXISTS}))
                    continue                
                
                if isdb.insert_service(service['name'], service['port'], service['security_level'], key) == False:
                    log.info(db.get_last_error())        
                    self.request.sendall(json.dumps({'err': ERR_DB_OPERATION_FAILED}))
                    continue


                users = isdb.get_all_users()

                if users == None:
                    log.info(db.get_last_error())        
                    self.request.sendall(json.dumps({'err': ERR_DB_OPERATION_FAILED}))
                    continue

                control_access_matrix = isdb.get_control_access_matrix()

                if control_access_matrix == None:
                    log.info(db.get_last_error())        
                    self.request.sendall(json.dumps({'err': ERR_DB_OPERATION_FAILED}))
                    continue            
                    
                control_access_matrix = json.loads(control_access_matrix[0]['matrix'])

                for user in users:
                    if user['security_level'] == service['security_level']:
                        val = rand.randrange(4)

                        if val == 0:
                            control_access_matrix['%s_%s' % (user['username'], service['name'])] = 'na'
                        elif val == 1:
                            control_access_matrix['%s_%s' % (user['username'], service['name'])] = 'r'
                        elif val == 2:
                            control_access_matrix['%s_%s' % (user['username'], service['name'])] = 'w'
                        else:
                            control_access_matrix['%s_%s' % (user['username'], service['name'])] = 'rw'

                if isdb.update_control_access_matrix(json.dumps(control_access_matrix)) == False:
                    log.info(db.get_last_error())        
                    self.request.sendall(json.dumps({'err': ERR_DB_OPERATION_FAILED}))
                    continue

                self.request.sendall(json.dumps({'key': key}))

            elif command == COMM_START_SERVICE:
                services = self.isdb.get_all_services()

                if services == None:
                    log.info(db.get_last_error())        
                    self.request.sendall(ERR_DB_OPERATION_FAILED)
                    continue

                for service in services:
                    del service['security_level']
                    del service['key']

                for started_service in STARTED_SERVICES:
                    if started_service in services:
                        services.remove(started_service)

                self.request.sendall(json.dumps(services))
            elif command == COMM_SERVICE_STARTED:
                STARTED_SERVICES.append(json.loads(self.request.recv(1024)))
                print 'Started services: %s' % str(STARTED_SERVICES)
            elif command == COMM_SERVICE_STOPPED:
                STARTED_SERVICES.remove(json.loads(self.request.recv(1024)))
                print 'Started services: %s' % str(STARTED_SERVICES)
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


if __name__ == "__main__":
    user_server = Server((HOST, USER_PORT), UserTCPConnectionHandler)
    service_server = Server((HOST, SERVICE_PORT), ServiceTCPConnectionHandler)
    isdb = db.InformationSecurityDB(DB_CREDENTIALS)

    if not isdb:
        print db.get_last_error()
        sys.exit()

    control_access_matrix = isdb.get_control_access_matrix()

    if control_access_matrix == None:
        print db.get_last_error()
        sys.exit()
    elif len(control_access_matrix) == 0:
        if isdb.insert_control_access_matrix(json.dumps({})) == False:
            print db.get_last_error()
            sys.exit()

    user_server_thread = threading.Thread(target=user_server.serve_forever)
    user_server_thread.daemon = True
    user_server_thread.start()

    service_server_thread = threading.Thread(target=service_server.serve_forever)
    service_server_thread.daemon = True
    service_server_thread.start()

    try:
        while 1:
            pass
    except KeyboardInterrupt:
        sys.exit(0)