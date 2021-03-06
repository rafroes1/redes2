import socket
import threading
import tkinter.messagebox
from tkinter import *
from Client.ClientHandler import ClientHandler
from Protocol.ProtocolPacker import ProtocolPacker


class ServerTCP(object):
    def __init__(self, master):
        self.frame = Frame(master)
        self.frame.pack()

        self.clientes = []
        self.nickList = []

        self.nickListBox = Listbox(self.frame, width=50)
        self.nickListBox.pack()

        self.removeButton = Button(self.frame, text='Remove', command=self.removeClient)
        self.removeButton.pack()

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('localhost', 6789))
        ##-------------------SET PUBLIC IP HERE -------------------##
        #self.server_socket.bind(('177.207.60.132', 6789))
        self.server_socket.listen(5)
        self.server_socket.setblocking(False)

        self.packer = ProtocolPacker('999', 'Servidor', '127.0.0.1', 6789)

        acptConn = threading.Thread(target=self.accCon)
        acptConn.daemon = True
        acptConn.start()

        keepListen = threading.Thread(target=self.listen)
        keepListen.daemon = True
        keepListen.start()



        print('Servidor rodando')


    def accCon(self):
        while True:
            try:
                conn, addr = self.server_socket.accept()
                conn.setblocking(False)

                recv_pkt = conn.recv(1024)
                id = self.packer.unpack(recv_pkt)[0]
                nick = self.packer.unpack(recv_pkt)[1]
                ip = self.packer.unpack(recv_pkt)[2]
                self.nickListBox.insert(END, nick+': '+ip)
                print(nick + ' conectado')
                hs = self.packer.unpack(recv_pkt)[4]

                if hs == '1':
                    newCliente = ClientHandler(id, nick, addr[0], addr[1], conn)
                    newCliente.setPubKey(self.packer.unpack(recv_pkt)[5])
                    self.clientes.append(newCliente)
                    self.svHandShake(conn)
                    self.clientConnected()
                else:
                    pass
            except:
                pass

    def listen(self):
        while True:
            if len(self.clientes) > 0:
                for ch in self.clientes:
                    try:
                        conn = ch.getConn()
                        packet = conn.recv(1024)
                        infos = self.packer.rsaUnpack(packet)
                        beg_msg = infos[5][0:3]
                        if beg_msg == '/d/':
                            #beg = infos[5].split('~')[0]
                            #private_nick = beg[3:len(beg)]
                            #self.privateMsg(private_nick, packet)

                            private_nick_list = infos[5].split('~')
                            private_nick_list[0] = private_nick_list[0][3:len(private_nick_list[0])]
                            private_nick_list.pop()
                            self.sendPrivateMsg(private_nick_list, packet)
                        elif beg_msg == '/e/':
                            for ch2 in self.clientes:
                                nick = ch2.getNick()
                                if nick == self.packer.rsaUnpack(packet)[1]:
                                    for i in self.nickListBox.size():
                                        if nick == self.nickListBox.get(i):
                                            self.nickListBox.delete(i, i)

                                    ch2.getConn().close()
                                    self.clientes.remove(ch2)
                        else:
                            self.broadcast(packet)
                    except:
                        pass

    def sendPrivateMsg(self, private_nick_list, packet):
        for ch in self.clientes:
            for client in private_nick_list:
                if ch.getNick() == client:
                    self.privateMsg(client, packet)

    def clientConnected(self, ):
        msg = '/c/'
        for ch in self.clientes:
            msg = msg + ch.getNick() + '~'
        for ch2 in self.clientes:
            try:
                conn = ch2.getConn()
                conn.send(self.packer.newPacket(msg))
            except:
                pass

    def privateMsg(self, nick, packet):
        for ch in self.clientes:
            try:
                if ch.getNick() == nick:
                    infos = self.packer.rsaUnpack(packet)
                    customPacket = self.packer.newCustomPacket(infos[0], infos[1], infos[2], infos[3], infos[4], infos[5], ch.getPubKey())
                    conn = ch.getConn()
                    conn.send(customPacket)
            except:
                self.clientes.remove(ch)

    def broadcast(self, packet):
        infos = self.packer.rsaUnpack(packet)
        nick = infos[1]
        for ch in self.clientes:
            try:
                if ch.getNick() != nick:
                    conn = ch.getConn()
                    customPacket = self.packer.newCustomPacket(infos[0], infos[1], infos[2], infos[3], infos[4], infos[5], ch.getPubKey())
                    conn.send(customPacket)
            except:
                self.clientes.remove(ch)

    def svHandShake(self, conn):
        conn.send(self.packer.newSvHandShakePacket())

    def getClients(self):
        if len(self.clientes) > 0:
            for i in self.clientes:
                clientsNicks = [i.getNick()]
            return clientsNicks
        else:
            return []

    def close(self):
        self.server_socket.close()
        sys.exit()

    def removeClient(self):
        answer = tkinter.messagebox.askquestion('Remoção de Cliente', 'Tem certeza que deseja remover o cliente?')
        if answer == 'yes':
            client_to_be_removed = str(self.nickListBox.get(self.nickListBox.curselection())).split(':')[0]
            for ch in self.clientes:
                if ch.getNick() == client_to_be_removed:
                    conn = ch.getConn()
                    conn.send(self.packer.newPacket('/r/'))
                    ch.getConn().close()
                    self.clientes.remove(ch)
            print(client_to_be_removed + ' foi removido do servidor')

            item = self.nickListBox.curselection()
            pos = 0
            for i in item:
                idx = int(i) - pos
                self.nickListBox.delete(idx, idx)
                pos = pos + 1