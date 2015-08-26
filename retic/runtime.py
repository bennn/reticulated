import inspect
from . import flags
from . import relations
from .rtypes import *
from .exc import UnknownTypeError, UnexpectedTypeError

if flags.PY_VERSION == 2:
    class getfullargspec(object):
        def __init__(self, f):
            self.args, self.varargs, self.varkw, self.defaults = \
                inspect.getargspec(f)
            self.kwonlyargs = []
            self.kwonlydefaults = None
            if hasattr(f, '__annotations__'):
                self.annotations = f.__annotations__
            else:
                self.annotations = {}
        def __iter__(self):
            yield self.args
            yield self.varargs
            yield self.varkw
            yield self.defaults
elif flags.PY_VERSION == 3:
    from inspect import getfullargspec

def retic_bindmethod(cls, receiver, attr):
    val = getattr(receiver, attr)
    if inspect.ismethod(val):
        return lambda *args: getattr(cls, attr)(receiver, *args)
    else: return val

if flags.INITIAL_ENVIRONMENT:
    def dyn(v):
        return v

### Python 2.7 annotation
def retic_typed(ty=None, error_function='retic_error'):
    def tyfn(fn):
        if tyinstance(ty, Function):
            spec = inspect.getargspec(fn)
            posargs = spec.args
            annotations = ty.froms.lenmatch(posargs)
            if annotations == None:
                error_function('Mismatch in number of positional arguments')
            annotations = dict(annotations)
            annotations['return'] = ty.to
            fn.__annotations__ = annotations
        elif tyinstance(ty, Class):
            pass
        else:
            error_function('Functions must be annotated with function types')
        return fn
    return tyfn

typed = retic_typed

def infer(k):
    return k

def noinfer(k):
    return k

def parameters(*k):
    return lambda x: x

def returns(k):
    return lambda x: x

def fields(k):
    return lambda x: x

def members(k):
    return lambda x: x


### Metaclass constructor for monotonic objects
def _monotonic(metaclass):
    class Monotonic(metaclass):
        monotonic_capable_class = True
    return Monotonic
Monotonic = _monotonic(type)

def has_type(val, ty):
    if tyinstance(ty, TypeVariable):
        return True
    elif tyinstance(ty, Self):
        return True
    elif tyinstance(ty, Dyn):
        return True
    elif tyinstance(ty, InferBottom):
        return False
    elif tyinstance(ty, Void):
        return val == None
    elif tyinstance(ty, Int):
        return isinstance(val, int) or (not flags.FLAT_PRIMITIVES and has_type(val, Bool))
    elif tyinstance(ty, Bytes):
        return isinstance(val, bytes)
    elif tyinstance(ty, Bool):
        return isinstance(val, bool)
    elif tyinstance(ty, Float):
        return isinstance(val, float) or (not flags.FLAT_PRIMITIVES and has_type(val, Int))
    elif tyinstance(ty, Complex):
        return isinstance(val, complex) or (not flags.FLAT_PRIMITIVES and has_type(val, Float))
    elif tyinstance(ty, String):
        return isinstance(val, str)
    elif tyinstance(ty, Function):
        if inspect.ismethod(val): # Only true for bound methods
            spec = getfullargspec(val)
            new_spec = inspect.FullArgSpec(spec.args[1:], spec.varargs, spec.varkw, 
                                           spec.defaults, spec.kwonlyargs, 
                                           spec.kwonlydefaults, spec.annotations)
            return func_has_type(new_spec, ty)
        elif inspect.isfunction(val): # Normal function
            return func_has_type(getfullargspec(val), ty)
        elif inspect.isclass(val): 
            if inspect.isfunction(val.__init__):
                spec = getfullargspec(val.__init__)
                new_spec = inspect.FullArgSpec(spec.args[1:], spec.varargs, spec.varkw, 
                                               spec.defaults, spec.kwonlyargs, 
                                               spec.kwonlydefaults, spec.annotations)
                return func_has_type(new_spec, ty)
            else: return True
        elif inspect.isbuiltin(val):
            return True
        elif hasattr(val, '__call__'):
            if inspect.isfunction(val.__call__):
                spec = getfullargspec(val.__call__)
                new_spec = inspect.FullArgSpec(spec.args[1:], spec.varargs, spec.varkw, 
                                               spec.defaults, spec.kwonlyargs, 
                                               spec.kwonlydefaults, spec.annotations)
                return func_has_type(new_spec, ty)
            else: return True
        elif callable(val):
            return True # No clue
        else: return False
    elif tyinstance(ty, List):
        return (isinstance(val, list)) and \
            all(map(lambda x: has_type(x, ty.type), val))
    elif tyinstance(ty, Set):
        return isinstance(val, set) and \
            all(map(lambda x: has_type(x, ty.type), val))
    elif tyinstance(ty, Dict):
        return isinstance(val, dict) and \
            all(map(lambda x: has_type(x, ty.keys), val.keys())) and \
            all(map(lambda x: has_type(x, ty.values), val.values()))
    elif tyinstance(ty, Tuple):
        return (isinstance(val, tuple) or isinstance(val, list)) \
            and len(ty.elements) == len(val) and \
            all(map(lambda p: has_type(p[0], p[1]), zip(val, ty.elements)))
    elif tyinstance(ty, Iterable):
        if (isinstance(val, tuple) or isinstance(val, list) or isinstance(val, set)) or iter(val) is not val:
            return all(map(lambda x: has_type(x, ty.type), val))
        elif isinstance(val, collections.Iterable):
            if hasattr(val, '__iter__'):
                return has_type(val.__iter__, Function([Dyn], Iterable(ty.type)))
            else: return True
        else: return False
    elif tyinstance(ty, Object):
        for k in ty.members:
            if not hasattr(val, k) or not has_type(getattr(val, k), ty.members[k]):
                return False
        return True
    elif tyinstance(ty, Class):
        for k in ty.members:
            if not hasattr(val, k) or not has_type(getattr(val, k), ty.members[k]):
                return False
        return isinstance(val, type)
    else: raise UnknownTypeError('Unknown type ', ty)

def has_shape(obj, dct):
    for k in dct:
        try: getattr(obj, k)
        except AttributeError:
            return False
    return True

def runtime_type(ty):
    try: 
        ty.static()
        return ty
    except AttributeError:
        return Dyn

def func_has_type(argspec, ty):
    if argspec.varargs != None or\
            argspec.varkw != None:
        return True
    if argspec.defaults == None:
        argset = ty.froms.lenmatch(argspec.args)
        if argset == None:
            return False
    else:
        for i in range(len(argspec.args),
                       len(argspec.args)-len(argspec.defaults)-1,-1):
            argset = ty.froms.lenmatch(argspec.args[:i])
            if argset != None:
                break
        if argset == None:
            return False
    if not hasattr(argspec, 'annotations'):
        return True
    for p, t in argset:
        if p in argspec.annotations and\
                not relations.subcompat(t, runtime_type(argspec.annotations[p])):
            return False
    if 'return' in argspec.annotations:
        return relations.subcompat(runtime_type(argspec.annotations['return']), ty.to)
    else:
        return True
