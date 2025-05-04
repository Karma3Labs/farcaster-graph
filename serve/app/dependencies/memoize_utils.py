from typing import Tuple, Any, Dict

from memoize.key import KeyExtractor


class EncodedMethodNameAndArgsExcludedKeyExtractor(KeyExtractor):
    """Encodes method name, args & kwargs to string and uses that as cache entry key.
    This KeyExtractor is class-centric and creates same keys for all objects of the same type.
    You can exclude args and kwargs by setting 'skip_args' and 'skip_kwargs' flags.

    Note: If wrapped function is a method (has 'self' as first positional arg) you may want to exclude 'self' from key
    by setting 'skip_first_arg_as_self' flag.
    For static methods of ordinary functions flag should be set to 'False'.

    Warning: uses method name only, so be cautious and do not wrap methods of different classes with the same names
    while using same store and 'skip_first_arg_as_self' set to False."""

    def __init__(
        self,
        skip_first_arg_as_self=False,
        skip_args: list[int] = [],
        skip_kwargs: list[str] = [],
    ) -> None:
        self._skip_first_arg_as_self = skip_first_arg_as_self
        self._skip_args = skip_args
        self._skip_kwargs = skip_kwargs

    def format_key(
        self, method_reference, call_args: Tuple[Any, ...], call_kwargs: Dict[str, Any]
    ) -> str:
        if self._skip_args:
            call_args = [
                arg for i, arg in enumerate(call_args) if i not in self._skip_args
            ]
        if self._skip_kwargs:
            call_kwargs = {
                k: v for k, v in call_kwargs.items() if k not in self._skip_kwargs
            }
        if self._skip_first_arg_as_self:
            call_args.pop(0)

        return str(
            (
                method_reference.__name__,
                call_args,
                call_kwargs,
            )
        )

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return (
            f"{self.__class__}"
            f"[skip_first_arg_as_self={self._skip_first_arg_as_self}]"
            f"[skip_args={self._skip_args}]"
        )
