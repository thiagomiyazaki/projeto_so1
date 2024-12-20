#!/usr/bin/env python3
from __future__ import annotations
from typing import Sequence, List, Dict
from time import sleep
from random import randint as rint
from threading import Condition
import argparse
import threading
import datetime


class ContextManager:
    """
        distro_points_lock: variável de trava utilizada para evitar condições de corrida no acesso aos atributos
        distro_points: lista de objetos dos pontos de distribuição
        packages: lista de objetos de encomenda
        cars: lista de objetos dos carros
        shutdown: variável utilizada para determinar que o programa deve ser encerrado (finalizando as threads)
    """
    distro_points_lock = threading.Lock()
    distro_points: List[DistroPoint] = []
    packages: List[Package] = []
    cars: List[Car] = []
    qt_pkgs = 0
    shutdown = False

    @classmethod
    def create_objects(cls, qt_dpoints, qt_cars, qt_pkgs, capacity):
        # cria os objetos segundo os argumentos passados na invocação do programa
        cls.create_dpoints(qt_dpoints)
        cls.create_pkgs(qt_pkgs, qt_dpoints)
        cls.create_cars(qt_cars, qt_dpoints, capacity)

    @classmethod
    def start_threads(cls):
        # inicia as threads de pto de distribuição, encomendas e carros
        for dpoints in cls.distro_points:
            dpoints.start()

        for pkg in cls.packages:
            pkg.start()

        for car in cls.cars:
            car.start()

    @classmethod
    def create_dpoints(cls, qt_dpoints):
        # cria objetos de ptos de distribuicao
        for i in range(qt_dpoints):
            cls.distro_points.append(DistroPoint(f'DPoint_{i}'))

    @classmethod
    def create_pkgs(cls, qt_packages, qt_dpoints):
        # cria objetos encomenda - definindo seus pontos de origem, destino, e setando o horario de sua criacao
        for i in range(qt_packages):
            name = f'Package_{i}'
            src = rint(0, qt_dpoints-1)
            dest = rint(0, qt_dpoints-1)
            if src == dest:
                dest += 2
                dest = dest % qt_dpoints
            new_pkg = Package(name, f'Dpoint_{src}', f'Dpoint_{dest}')
            new_pkg.set_creation(datetime.datetime.now())
            cls.distro_points[src].outgoing_pkg.append(new_pkg)
            cls.packages.append(new_pkg)

    @classmethod
    def create_cars(cls, qt_cars, qt_dpoints, capacity):
        # cria os objetos carros e define o seu ponto de partida
        for i in range(qt_cars):
            # Car(self, name, capacity, cur_state)
            cls.cars.append(
                Car(f'Car_{i}', capacity, rint(0, qt_dpoints-1))
            )

    @classmethod
    def get_list_of_distro_points_size(cls):
        # retorna a quantidade de pontos de distribuição
        with cls.distro_points_lock:
            return len(cls.distro_points)

    @classmethod
    def get_distro_point_by_index(cls, index):
        # retorna um objeto ponto de distribuicao de acordo com seu index
        with cls.distro_points_lock:
            return cls.distro_points[index]

    @classmethod
    def check_termination(cls):
        # se a quantidade de encomenda entregues for igual à quantidade total de encomendas - terminar as threads
        def remaining_packages():
            # verifica se ainda há encomendas a serem entregues
            with cls.distro_points_lock:
                count = 0
                for dp in cls.distro_points:
                    count += len(dp.incoming_pkg)
                if count == cls.qt_pkgs:
                    return False
                return True

        while remaining_packages():
            pass

        cls.shutdown = True


class Car(threading.Thread):
    def __init__(self, name, capacity, cur_state):
        super().__init__()
        self.name = name
        self.packages: List[Package] = []
        self.capacity = capacity
        # cur_state: point it is in or travelling
        self.current_state = cur_state
        self.iteration = 0

    def run(self):
        while not ContextManager.shutdown:
            # visita o próximo ponto de distribuição
            self.visit_next()
            distro_point = ContextManager.get_distro_point_by_index(self.current_state)

            # checks if there is a package to be delivered here
            delivery = self.check_delivery()
            if delivery:
                print(f'{self.name=} delivering {delivery} to Dpoint_{self.current_state}')
                if distro_point.add_to_buffer('receive', car=self, pkg=delivery) == 'received':
                    delete_me = None
                    for i in range(len(self.packages)):
                        if delivery.get_name() == self.packages[i].get_name():
                            delete_me = i
                    delivery.set_arrival(datetime.datetime.now())
                    self.packages.pop(delete_me)

            # checks is there is room for more items, if so, get a package
            if len(self.packages) < self.capacity:
                new_pkg: Package | None = distro_point.add_to_buffer('hand', car=self)
                if new_pkg:
                    new_pkg.set_loaded(datetime.datetime.now())
                    new_pkg.set_car(self)
                    self.packages.append(new_pkg)
                    print(f'{self.name=} picking up {new_pkg}')

    # dado que o carro está no ponto de distribuição P, visita o ponto P+1 (desde que P+1 exista)
    def visit_next(self):
        print(f'{self.name=} departing from {self.current_state}')
        self.iteration = self.current_state + 1
        self.current_state = 'travelling'
        sleep(rint(1, 10)/10)
        # evita estourar e implementa a fila "circular"
        self.current_state = self.iteration % ContextManager.get_list_of_distro_points_size()
        print(f'{self.name=} going to {self.current_state}')
        sleep(0.1)

    # dado o ponto de distro atual P - verifica se existem pacotes no "porta-mala" que devem ser entregues em P
    def check_delivery(self):
        for pkg in self.packages:
            if f'Dpoint_{self.current_state}' == pkg.dest:
                return pkg
            else:
                return None


class Package(threading.Thread):
    def __init__(self, name, src, dest):
        super().__init__()
        self.name = name
        self.src = src
        self.dest = dest
        self.creation = None
        self.arrival = None
        self.loaded = None
        self.car = None

    def run(self):
        # fica esperando que o atributo arrival mude seu estado - caso mude, isto indica que o pacote foi entregue
        while self.arrival is None:
            sleep(1)
        print(f'!------ DELIVERED {self.name=} --------!')
        self.print_info()
        with open(f"{self.name}.txt", "w") as f:
            self.write_info(f)

    def set_arrival(self, timestamp):
        self.arrival = timestamp

    def set_loaded(self, timestamp):
        self.loaded = timestamp

    def set_creation(self, timestamp):
        self.creation = timestamp

    def set_car(self, car):
        self.car = car

    def departure(self):
        print(f"The package is leaving from {self.src} to {self.dest} inside {self.car}!")

    def get_name(self):
        return self.name

    def print_info(self):
        print(f'{self.src=}')
        print(f'{self.dest=}')
        print(f'{self.creation=}')
        print(f'{self.arrival=}')
        print(f'{self.loaded=}')
        print(f'{self.car=}')

    def write_info(self, f):
        f.write(f'!------ DELIVERED {self.name=} --------!\n')
        f.write(f'{self.src=}\n')
        f.write(f'{self.dest=}\n')
        f.write(f'{self.creation=}\n')
        f.write(f'{self.arrival=}\n')
        f.write(f'{self.loaded=}\n')
        f.write(f'{self.car=}\n')


class DistroPoint(threading.Thread):
    def __init__(self, name):
        super().__init__()
        self.name: str = name
        self.outgoing_pkg: List[Package] = []
        self.incoming_pkg: List[Package] = []
        self.request_buffer: List[Dict] = []
        self.condition = Condition()  # Use a Condition instead of a plain Lock

    def run(self):
        # fica lendo o buffer de requisições - assim que chega uma nvoa requisição ela deve ser lida e ao final da
        # leitura uma notificação deve ser enviada às threads que estão em wait no mesmo lock/condição
        while True and not ContextManager.shutdown:
            with self.condition:
                if self.request_buffer:
                    request = self.request_buffer[0]
                    if not request['processed']:
                        if request['type'] == 'hand' and self.outgoing_pkg:
                            # retorna um pacote para carregar no carro
                            request['result'] = self.outgoing_pkg.pop(0)
                            request['processed'] = True
                            # notifica que terminou de processar a requisição e que o processamento da thread parada
                            # pode continuar
                            self.condition.notify_all()
                        elif request['type'] == 'receive':
                            self.incoming_pkg.append(request['pkg'])
                            # confirma o recebimento do pacote
                            request['result'] = 'received'
                            request['processed'] = True
                            self.condition.notify_all()

    def receive_pkg(self, pkg):
        self.incoming_pkg.append(pkg)

    def hand_pkg(self, pkg):
        with self.condition:
            for item in self.outgoing_pkg:
                if pkg.get_name() == item.get_name():
                    return item

    # adiciona uma requisição ao buffer de requisições
    def add_to_buffer(self, req_type: object, car: Car, pkg: Package = None) -> None | str | Package:
        with self.condition:
            if req_type == 'hand' and not self.outgoing_pkg:
                return None
            request = {'type': req_type, 'car': car, 'pkg': pkg, 'result': None, 'processed': False}
            # request types: receive or hand
            self.request_buffer.append(request)
            while request['result'] is None:
                # enquanto a requisição não for processada, a thread deve esperar - apenas uma thread pode ser atendida
                # por vez
                self.condition.wait()
            result = request['result']
            for item in self.request_buffer[:]:
                if item == request:
                    self.request_buffer.remove(item)
            return result


def main(argv: Sequence[str] | None = None) -> int:
    # pega os argumentos da linha de comando
    parser = argparse.ArgumentParser(
        prog='project',
    )
    parser.add_argument(
        '-s',
        help='Distribution point',
    )
    parser.add_argument(
        '-c',
        help='Cars',
    )
    parser.add_argument(
        '-p',
        help='Packages',
    )
    parser.add_argument(
        '-a',
        help='Available space',
    )

    # coloca os argumentos nas variáveis
    args = parser.parse_args(argv)
    packages = int(args.p)
    cars = int(args.c)
    available_space = int(args.a)
    distro_points = int(args.s)
    print(f'{args=}')

    # passa os parâmetros para a criação dos objetos
    ContextManager.create_objects(distro_points, cars, packages, available_space)
    ContextManager.qt_pkgs = packages

    # inicia a thread que verifica se o programa deve terminar (indicando que as outras threads devem parar)
    thread = threading.Thread(target=ContextManager.check_termination)
    thread.start()

    # inicia as threads de Pontos de Distro, Carros e Encomendas
    ContextManager.start_threads()

    return 0


if __name__ == "__main__":
    SystemExit(main())
