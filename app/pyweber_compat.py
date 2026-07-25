"""Compatibility shims for pyweber 1.3.1 on Python 3.14+.

Python 3.14 stores function annotations as strings; pyweber OpenAPI code
calls annotation.__name__ and crashes. Patch before registering routes.
"""

from __future__ import annotations

import inspect
import logging

logger = logging.getLogger(__name__)


def apply_pyweber_compat() -> None:
    from pyweber.models.openapi import OpenApiProcessor
    from pyweber.models.response import Response
    from pyweber.pyweber.pyweber import Pyweber

    _orig_resolve = OpenApiProcessor.resolve_class_type.__func__
    _orig_prepare = OpenApiProcessor.prepare_callback_kwargs.__func__

    @classmethod
    def resolve_class_type(cls, parameter: inspect.Parameter):
        annotation = parameter.annotation
        if annotation is inspect.Parameter.empty:
            return "empty_class"
        if isinstance(annotation, str):
            name = annotation.rsplit(".", 1)[-1]
            if name in {"File", "bytes", "bytearray"}:
                return "file"
            if name == "Request":
                return "request"
            # primitives / unknown string annotations → path/query scalar
            return "empty_class"
        return _orig_resolve(cls, parameter)

    @classmethod
    def prepare_callback_kwargs(cls, callback, **kwargs):
        """Same as upstream, but safe when annotations are strings (Py 3.14)."""
        kwargs = dict(kwargs)
        all_callback_parameters = cls.get_callback_parameters(callback)
        kwd = {}

        for name, parameter in all_callback_parameters.items():
            class_resolved = cls.resolve_class_type(parameter)
            annotation = parameter.annotation

            if class_resolved == "file":
                if name in kwargs:
                    kwd[name] = kwargs.pop(name)[0]

            elif class_resolved in ["pydantic", "dataclass", "normal_class"]:
                if isinstance(annotation, str):
                    if name in kwargs:
                        kwd[name] = kwargs.pop(name)
                    continue
                parameters = {}
                for key in cls.get_callback_parameters(annotation).keys():
                    parameters[key] = kwargs.pop(key)
                kwd[name] = annotation(**parameters)

            elif class_resolved == "request":
                from pyweber.models.context import get_current_request

                request = kwargs.pop("request", None) or get_current_request()
                if request is None:
                    raise TypeError(
                        "Route handler requires a Request, but none is available."
                    )
                kwd[name] = request

            else:
                ann_name = None
                if annotation is not inspect.Parameter.empty and not isinstance(
                    annotation, str
                ):
                    ann_name = getattr(annotation, "__name__", None)

                mapping = cls.mapping_swagger_types()
                is_scalar = (
                    annotation is inspect.Parameter.empty
                    or isinstance(annotation, str)
                    or (ann_name in mapping if ann_name else True)
                )

                if not is_scalar and ann_name not in mapping:
                    # custom class instantiation path — skip for string annotations
                    if isinstance(annotation, type):
                        instance = annotation()
                        for key in getattr(instance, "__annotations__", {}):
                            if key in kwargs:
                                setattr(instance, key, kwargs.pop(key))
                        kwd[name] = instance
                    elif name in kwargs:
                        kwd[name] = kwargs.pop(name)
                else:
                    if parameter.kind not in [
                        inspect.Parameter.VAR_KEYWORD,
                        inspect.Parameter.VAR_POSITIONAL,
                    ]:
                        if name in kwargs:
                            kwd[name] = kwargs.pop(name)

        if kwargs:
            has_var_keyword = any(
                p.kind == inspect.Parameter.VAR_KEYWORD
                for p in all_callback_parameters.values()
            )
            has_var_positional = any(
                p.kind == inspect.Parameter.VAR_POSITIONAL
                for p in all_callback_parameters.values()
            )
            if has_var_keyword:
                var_kw_name = next(
                    n
                    for n, p in all_callback_parameters.items()
                    if p.kind == inspect.Parameter.VAR_KEYWORD
                )
                kwd[var_kw_name] = kwargs
            elif has_var_positional:
                var_pos_name = next(
                    n
                    for n, p in all_callback_parameters.items()
                    if p.kind == inspect.Parameter.VAR_POSITIONAL
                )
                kwd[var_pos_name] = list(kwargs.values())

        return kwd

    OpenApiProcessor.resolve_class_type = resolve_class_type
    OpenApiProcessor.prepare_callback_kwargs = prepare_callback_kwargs

    # Skip HTML handoff for Response objects (API JSON + cookies)
    _orig_handoff = Pyweber._should_register_handoff

    def _handoff_skip_api_response(self, template_result):
        if isinstance(getattr(template_result, "template", None), Response):
            return False
        return _orig_handoff(self, template_result)

    Pyweber._should_register_handoff = _handoff_skip_api_response
    logger.info("pyweber Python 3.14 compat patches applied")
