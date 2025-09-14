from typing import Dict, Type, TypeVar, Callable, Any
from abc import ABC, abstractmethod

T = TypeVar('T')


class Container:
    """Container d'injection de dépendances simple et performant"""

    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}

    def register_singleton(self, interface: Type[T], implementation: Type[T]) -> None:
        """Enregistre un service en singleton"""
        self._services[interface] = implementation

    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Enregistre une factory pour créer des instances"""
        self._factories[interface] = factory

    def get(self, interface: Type[T]) -> T:
        """Récupère une instance du service demandé"""
        if interface in self._singletons:
            return self._singletons[interface]

        if interface in self._factories:
            instance = self._factories[interface]()
            self._singletons[interface] = instance
            return instance

        if interface in self._services:
            implementation = self._services[interface]
            # Résolution automatique des dépendances
            instance = self._create_instance(implementation)
            self._singletons[interface] = instance
            return instance

        raise ValueError(f"Service {interface.__name__} not registered")

    def _create_instance(self, cls: Type[T]) -> T:
        """Crée une instance en résolvant automatiquement les dépendances"""
        import inspect

        signature = inspect.signature(cls.__init__)
        params = {}

        for param_name, param in signature.parameters.items():
            if param_name == 'self':
                continue

            if param.annotation in self._services or param.annotation in self._factories:
                params[param_name] = self.get(param.annotation)
            elif param.default is not param.empty:
                params[param_name] = param.default

        return cls(**params)


# Instance globale du container
container = Container()