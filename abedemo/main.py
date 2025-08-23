#!usr/bin/env python
# -*- coding:utf-8 -*-
"""
@File: main
@Author: Ardenet
@Date: 2024/12/14 21:48:42
@Version: 1.0.0
@Description: 基于属性加密的车载互联网的访问控制机制Demo
"""
from charm.toolbox.pairinggroup import PairingGroup, ZR, G1, GT, pair
from hashlib import sha256

# 系统初始化
G = None
p = None
g = None
Q = None
e = None
Y = None

PK = {}
PubCA = {}
PubRSU = {}
S = {}
D = {}

class CA:
    def __init__(self):
        self.Key = []
        self._global_setup()
        self._setup()

    def _global_setup(self):
        global p, G, e, g, Q, Y
        G = PairingGroup("SS512")
        p = G.order()
        g = G.random(G1)
        Q = G.random(G1)
        self.y = G.random(ZR)
        self.gk = g**self.y
        e = pair
        Y = e(g, g)**self.y

    def _setup(self):
        global G, g, S, PubCA
        S = {"car", "policecar", "ambulance"}
        self.MkCA = {s: G.random(ZR) for s in S}
        PubCA.update({s: g**t_s for (s, t_s) in self.MkCA.items()})

    def _H_key(self, pseudonym, key):
        global p
        return int(sha256(pseudonym.encode()).hexdigest(), 16) % p

    def _keygen(self, i, node):
        """
        Generate a key for a pesudonym for a node
        """
        global Q, g, PK
        for pseudonym in node.pseudonyms:
            h_key = self._H_key(pseudonym, self.Key[i])
            PK[pseudonym] = g**h_key  # 公钥
            node.NodeSK[pseudonym] = self.gk * (Q**h_key)
            node.AttrSK[pseudonym].update({s: PK[pseudonym]**t_s for (s, t_s) in self.MkCA.items()})

    def add_nodes(self, N):
        for i, node in enumerate(N):
            self.Key.append("key" + str(i))
            self._keygen(i, node)


class RSU:
    def __init__(self, rsu_id, D_j):
        """
        Initialize RSU's public and secret keys
        """
        self.id = rsu_id
        self.D_j = D_j
        self._rsu_setup()

    def _rsu_setup(self):
        """
        Setup RSU's public and secret keys
        """
        global G, g, PubRSU
        self.MkRSU = {d: G.random(ZR) for d in self.D_j}
        PubRSU.update({self.id: {d: g**t_d for (d, t_d) in self.MkRSU.items()}})

    def _keygen(self, node):
        """
        Generate attribute private key set for each pseudonym of the node
        """
        global Q, g
        for pseudonyms in node.pseudonyms:
            node.AttrSK[pseudonyms].update({d: PK[pseudonyms]**t_d for (d, t_d) in self.MkRSU.items()})

    def enter(self, node, dynamic):
        """
        Node enters RSU's coverage area
        """
        node.rsu = self.id
        for attrs in dynamic.values():
            if not attrs.issubset(self.D_j):
                raise ValueError("Node's dynamic attributes do not match RSU's coverage area.\n" + "Node: " + node.pseudonyms + "\nDynamic Attrs: " + str(dynamic))
        node.dynamic = dynamic
        self._keygen(node)

class Node:
    def __init__(self, pseudonyms, satic):
        """
        Initialize node's public and secret keys
        """
        self.pseudonyms = pseudonyms
        self.static = satic
        self.dynamic = None
        self.rsu = None
        self.NodeSK = {}
        self.AttrSK = {pseudonym: {} for pseudonym in self.pseudonyms}

    def __str__(self) -> str:
        return "节点: {{\n    假名集: {}\n    静态属性: {}\n    动态属性: {}\n    所属RSU: {}\n}}".format(self.pseudonyms, self.static, self.dynamic, self.rsu)

    def encrypt(self, M, W):
        """
        Encrypt message under DNF policy
        """
        global G, g, Y, Q, S, D, PubCA, PubRSU
        r = G.random(ZR)
        C = M * Y**r
        C_b = g**r
        C_l_list = []
        for conjunction in W:
            PubAttr = G.init(G1, 1)
            for attr in conjunction:
                if attr in S:
                    PubAttr *= PubCA[attr]
                else:
                    attr_rsu = next((rsu_id for rsu_id, attrs in D.items() if attr in attrs), None)
                    if attr_rsu is None:
                        raise ValueError("Invalid attribute: " + attr + str(D))
                    PubAttr *= PubRSU[attr_rsu][attr]
            C_l = (Q * PubAttr) ** r
            C_l_list.append(C_l)
        return C, C_b, C_l_list

    def yield_lp(self, W):
        for idx, conjunction in enumerate(W):
            for pseudonym in self.pseudonyms:
                if conjunction.issubset(self.static[pseudonym] | self.dynamic[pseudonym]):
                    yield idx, pseudonym

    def decrypt(self, W, C, C_b, C_l_list):
        global PK, e
        l, pseudonym = next(((idx, pseudonym) for idx, conjunction in enumerate(W) for pseudonym in self.pseudonyms if conjunction.issubset(self.static[pseudonym] | self.dynamic[pseudonym])), (None, None))
        if l is None:
            return "Access denied"

        SecAttr = G.init(G1, 1)
        for attr in W[l]:
            SecAttr *= self.AttrSK[pseudonym][attr]
        K_l = self.NodeSK[pseudonym] * SecAttr
        decrypted = C * (e(PK[pseudonym], C_l_list[l]) / e(K_l, C_b))  # 解密消息
        return decrypted


class AccessControlSystem:
    def __init__(self):
        global D
        self.ca = CA()

        rsu1 = RSU("RSU1", {"Road1", "Lane1"})
        rsu2 = RSU("RSU2", {"Road2", "Lane2", "POS1"})
        self.RSUs = [rsu1, rsu2]
        for rsu in self.RSUs:
            D.update({rsu.id: rsu.D_j})

        node1 = Node(["bobcar"], {"bobcar": {"car"}})
        node2 = Node(["policebob", "officecar"], {"policebob": {"policecar"}, "officecar": {"car"}})
        node3 = Node(["policepeter"], {"policepeter": {"policecar"}})
        node4 = Node(["Ahospital51"], {"Ahospital51": {"ambulance"}})
        node5 = Node(["policealice"], {"policealice": {"policecar"}})
        self.Nodes = [node1, node2, node3, node4, node5]
        self.ca.add_nodes(self.Nodes)

    def develop(self):
        rsu0, rsu1 = self.RSUs
        node0, node1, node2, node3, node4 = self.Nodes
        # 模拟节点进入RSU的覆盖范围
        rsu0.enter(node0, {"bobcar": {"Road1"}})
        rsu0.enter(node1, {"policebob": {"Road1"}, "officecar": {"Road1"}})
        rsu0.enter(node2, {"policepeter": {"Lane1"}})
        rsu1.enter(node3, {"Ahospital51": {"Road2"}})
        rsu1.enter(node4, {"policealice": {"Lane2"}})


def test(Nodes):
    global G
    node0, node1, node2, node3, node4 = Nodes
    M = G.random(GT)
    W = [{"policecar", "Road1"}, {"ambulance"}]
    print("明文:", M)
    print("策略:", W)
    C, C_b, C_l_list = node0.encrypt(M, W)
    print("密文C：", C)
    print("密文C_b：", C_b)
    print("密文C_l：", C_l_list)

    # 测试四种情况
    # 1. 同一RSU中，符合标准
    decrypted_message1 = node1.decrypt(W, C, C_b, C_l_list)
    print("节点1解密后的消息：（符合访问标准）", decrypted_message1)

    # 2. 同一RSU中，不符合标准
    decrypted_message2 = node2.decrypt(W, C, C_b, C_l_list)
    print("节点2解密后的消息：（不符合访问标准）", decrypted_message2)

    # 3. 不同RSU中，符合标准
    decrypted_message3 = node3.decrypt(W, C, C_b, C_l_list)
    print("节点3解密后的消息（跨RSU, 符合标准）：", decrypted_message3)

    # 4. 不同RSU中，不符合标准
    decrypted_message4 = node4.decrypt(W, C, C_b, C_l_list)
    print("节点4解密后的消息（跨RSU，不符合标准）：", decrypted_message4)

def print_params(system):
    global S, D, PubCA, PubRSU, PK
    print("S:", S)
    print("D:", D)
    print("CA的公共参数：", PubCA)
    print("RSU的公共参数：", PubRSU)
    print("公钥：", PK)
    print("CA的私钥：", system.ca.MkCA)
    for i, rsu in enumerate(system.RSUs):
        print("RSU{}的私钥：{}".format(i, rsu.MkRSU))
    for i, node in enumerate(system.Nodes):
        print("节点{}的属性密钥：{}".format(i, node.AttrSK))
        print("节点{}的私钥：{}".format(i, node.NodeSK))
        print(str(node))


def main():
    global G
    system = AccessControlSystem()
    system.develop()

    print_params(system)

    # 测试
    test(system.Nodes)

if __name__ == "__main__":
    main()
