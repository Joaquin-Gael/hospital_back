import inspect

from types import FunctionType

class BaseInterface:
    @classmethod
    def get_templated_methods(cls) -> list[str]:
        """
        Dada una lista de tuplas (name, kind, callable) devuelve una lista de tuplas
        (name, kind, signature_str)
        """
        templated = []
        for name, kind, func in cls.get_methods(return_bound=False):
            templated.append(f"method name:  {name} have {inspect.signature(func)}  # {kind} from {cls.__name__}")
        return templated
    
    @classmethod
    def get_methods(
        cls,
        include_private: bool = False,
        include_inherited: bool = False,
        return_bound: bool = False,
    ) -> list[tuple[str, str, FunctionType]]:
        """
        Devuelve una lista de tuplas (name, kind, callable)
        kind -> 'instancemethod' | 'staticmethod' | 'classmethod' | 'method_descriptor'
        - include_private: incluye métodos que empiezan con '_'
        - include_inherited: incluir métodos heredados (usa inspect.getmembers)
        - return_bound: si True hace getattr(cls, name) (devuelve métodos ligados al class/instance)
        """
        methods = []
        items = inspect.getmembers(cls) if include_inherited else cls.__dict__.items()

        for name, value in items:
            if not include_private and name.startswith("_"):
                continue

            kind = None
            func = None

            # staticmethod y classmethod están envueltos en descriptores dentro del dict de la clase
            if isinstance(value, staticmethod):
                kind = "staticmethod"
                func = value.__func__            # función real
            elif isinstance(value, classmethod):
                kind = "classmethod"
                func = value.__func__            # función real (primer arg será cls)
            elif inspect.isfunction(value):
                kind = "instancemethod"
                func = value                     # función definida en la clase
            elif inspect.ismethoddescriptor(value):
                kind = "method_descriptor"
                func = value
            else:
                # por ejemplo: property, int, str, etc -> ignoramos
                continue

            if return_bound:
                # getattr() resolverá descriptors: classmethod -> bound to class,
                # instancemethod (function) -> function (no ligado) cuando se accede desde la clase,
                # para métodos ligados a instancia usar getattr(instance, name)
                resolved = getattr(cls, name)
                methods.append((name, kind, resolved))
            else:
                methods.append((name, kind, func))

        return methods