from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import inspect
import time

from core import config
import asyncio
import inspect
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Callable, Dict, Generator, Optional


@dataclass
class RegisteredTool:
    name: str
    handler: Callable[..., Any]
    description: str = ""
    enabled: bool = True


class ToolExecutor:

    def __init__(self):
        self.tools: Dict[str, RegisteredTool] = {}


    # ==========================================
    # تسجيل أي أداة قابلة للاستدعاء
    # ==========================================

    def register_tool(
        self,
        name: str,
        handler: Callable[..., Any],
        description: str = "",
    ) -> None:

        if not callable(handler):
            raise TypeError(
                f"Tool '{name}' is not callable"
            )

        self.tools[name] = RegisteredTool(
            name=name,
            handler=handler,
            description=description,
            enabled=True,
        )


    # ==========================================
    # تعطيل أداة بدون حذفها
    # ==========================================

    def disable_tool(
        self,
        name: str,
    ) -> None:

        tool = self.tools.get(name)

        if tool is None:
            raise KeyError(
                f"Unknown tool: {name}"
            )

        tool.enabled = False


    # ==========================================
    # إعادة تفعيل أداة
    # ==========================================

    def enable_tool(
        self,
        name: str,
    ) -> None:

        tool = self.tools.get(name)

        if tool is None:
            raise KeyError(
                f"Unknown tool: {name}"
            )

        tool.enabled = True


    # ==========================================
    # الحصول على أداة
    # ==========================================

    def get_tool(
        self,
        name: str,
    ) -> RegisteredTool:

        tool = self.tools.get(name)

        if tool is None:
            raise KeyError(
                f"Unknown tool: {name}"
            )

        if not tool.enabled:
            raise RuntimeError(
                f"Tool disabled: {name}"
            )

        return tool


    # ==========================================
    # تنفيذ الأداة مهما كان نوعها
    # ==========================================

    async def call(
        self,
        name: str,
        *args,
        **kwargs,
    ) -> Any:

        tool = self.get_tool(name)

        handler = tool.handler

        return await self._execute_callable(
            handler,
            *args,
            **kwargs,
        )


    # ==========================================
    # المحرك العام
    # ==========================================

    async def _execute_callable(
        self,
        handler: Callable[..., Any],
        *args,
        **kwargs,
    ) -> Any:

        # --------------------------------------
        # 1. Async Generator Function
        # --------------------------------------

        if inspect.isasyncgenfunction(handler):

            generator = handler(
                *args,
                **kwargs,
            )

            return await self._consume_async_generator(
                generator
            )


        # --------------------------------------
        # 2. Generator Function
        # --------------------------------------

        if inspect.isgeneratorfunction(handler):

            generator = handler(
                *args,
                **kwargs,
            )

            return self._consume_generator(
                generator
            )


        # --------------------------------------
        # 3. Async Function / Coroutine Function
        # --------------------------------------

        if inspect.iscoroutinefunction(handler):

            result = await handler(
                *args,
                **kwargs,
            )

            return await self._normalize_result(
                result
            )


        # --------------------------------------
        # 4. Sync Function
        #
        # تشغيلها داخل Thread حتى لا توقف
        # Event Loop الرئيسي
        # --------------------------------------

        result = await asyncio.to_thread(
            handler,
            *args,
            **kwargs,
        )

        return await self._normalize_result(
            result
        )


    # ==========================================
    # فهم النتيجة التي رجعتها الأداة
    # ==========================================

    async def _normalize_result(
        self,
        result: Any,
    ) -> Any:

        # --------------------------------------
        # Awaitable / Coroutine returned
        # from another function
        # --------------------------------------

        if inspect.isawaitable(result):

            resolved = await result

            return await self._normalize_result(
                resolved
            )


        # --------------------------------------
        # Async Generator
        # --------------------------------------

        if inspect.isasyncgen(result):

            return await self._consume_async_generator(
                result
            )


        # --------------------------------------
        # Normal Generator
        # --------------------------------------

        if inspect.isgenerator(result):

            return self._consume_generator(
                result
            )


        # --------------------------------------
        # Async Iterator
        # --------------------------------------

        if hasattr(result, "__aiter__"):

            items = []

            async for item in result:
                items.append(item)

            return items


        # --------------------------------------
        # القيمة العادية
        # str / dict / list / int /
        # object / None / etc.
        # --------------------------------------

        return result


    # ==========================================
    # استهلاك Generator عادي
    # ==========================================

    def _consume_generator(
        self,
        generator: Generator,
    ) -> list:

        output = []

        for item in generator:
            output.append(item)

        return output


    # ==========================================
    # استهلاك Async Generator
    # ==========================================

    async def _consume_async_generator(
        self,
        generator: AsyncGenerator,
    ) -> list:

        output = []

        async for item in generator:
            output.append(item)

        return output
