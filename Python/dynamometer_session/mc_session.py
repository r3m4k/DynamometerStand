# -*- coding: utf-8 -*-
"""Модуль контекстного менеджера сессии взаимодействия с МК."""

##########################################################


class McSession:
    """Объединяет декодер, источник байтов и контроллер в одну async-сессию."""

    def __init__(self, decoder, byte_source, controller):
        """Сохраняет компоненты сессии.

        Args:
            decoder: Декодер входящего потока байтов.
            byte_source: Источник байтов от МК.
            controller: Контроллер обмена командами и данными с GUI.
        """
        self.decoder = decoder
        self.byte_source = byte_source
        self.controller = controller

    async def __aenter__(self) -> "McSession":
        """Входит в контекст всех компонентов в порядке приёма данных."""
        await self.decoder.__aenter__()
        await self.byte_source.__aenter__()
        await self.controller.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Выходит из контекста компонентов в обратном порядке."""
        await self.controller.__aexit__(exc_type, exc_val, exc_tb)
        await self.byte_source.__aexit__(exc_type, exc_val, exc_tb)
        await self.decoder.__aexit__(exc_type, exc_val, exc_tb)
        return False
