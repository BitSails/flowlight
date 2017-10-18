import asyncio

from flowlight.core.command import Command
from flowlight.model.node import Node
from flowlight.model.machine import Machine
from flowlight.utils.executor import get_executor


class Group(Node):
    """ A group of multiple `Machine` and `Group`.
    """
    def __init__(self, nodes, name=None):
        Node.__init__(self, name)
        self._nodes = []
        self._nodes_map = {}
        for node in nodes:
            self.add(node)

    def enable_connection(self, **kwargs):
        for node in self.nodes():
            node.enable_connection(**kwargs)

    def add(self, node):
        if not isinstance(node, Node):
            host = name = node
            node = Machine(host, name)
            self._nodes_map[name] = node
        else:
            self._nodes_map[node.name] = node
        self._nodes.append(node)

    def nodes(self):
        return self._nodes

    def get(self, name):
        return self._nodes_map.get(name, None)

    def run(self, cmd):
        responses = get_executor().map(lambda node: node.run(cmd), self)
        return list(responses)

    def run_async(self, cmd, **kwargs):
        command = Command(cmd, **kwargs)
        tasks = []
        for node in self.nodes():
            tasks.append(node.run_async(command.cmd))
        response = yield from asyncio.gather(*tasks)
        return response

    def __iter__(self):
        return iter(self.nodes())
    
    def __getitem__(self, index):
        return self._nodes[index]

    def __repr__(self):
        return '<Group hosts=[{}]>'.format(','.join(map(str, self._nodes)))


class Cluster(Group):
    pass
